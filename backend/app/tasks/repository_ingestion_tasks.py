"""Celery task continuing repository ingestion after the synchronous scan
(Step 5) completes: per-file parsing (Tree-sitter/AST), chunking, embedding,
and vector storage -- the "Code Parsing -> AST Generation -> Chunking ->
Embedding Generation -> Vector Storage" stages from Step 1's pipeline.

Operates on whatever RepositoryFile rows are PENDING or STALE (see
RepositoryFileRepository.list_stale_or_pending) rather than "all files" --
this is what makes a fresh upload (everything PENDING) and an incremental
re-index (only changed files STALE) the same code path.

AI agent execution (documentation generation) is a separate, user-triggered
Task, not auto-chained here -- see documentation_tasks.py.
"""

import asyncio
import logging
import uuid

from app.db.session import AsyncSessionLocal
from app.llm.openai_provider import get_llm_provider
from app.models.enums import FileIndexStatus, RepositoryStatus, TaskStatus
from app.models.repository import Repository
from app.parsing.tree_sitter_parser import extract_symbols_from_file
from app.rag.chunking import chunk_file
from app.rag.embeddings import embed_chunks
from app.rag.vector_store import get_vector_store, new_point_id
from app.repositories.embedding_repository import EmbeddingRepository
from app.repositories.parsed_symbol_repository import ParsedSymbolRepository
from app.repositories.repository_file_repository import RepositoryFileRepository
from app.repositories.repository_repository import RepositoryRepository
from app.repositories.task_repository import TaskRepository
from app.services.storage_service import get_file_storage
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

# Symbol kinds chunked as their own embeddable unit. api_route/db_model are
# metadata VIEWS over an underlying function/class symbol (same source
# range), not separate ranges of their own -- chunking them too would
# double-embed the same source text under two different symbol_name tags.
_CHUNKABLE_KINDS = {"class", "function", "method"}


async def _process_one_file(
    repository_id: uuid.UUID,
    repository_storage_path: str,
    file_row,
    storage,
    llm,
    vector_store,
    parsed_symbol_repo: ParsedSymbolRepository,
    embedding_repo: EmbeddingRepository,
) -> None:
    raw_bytes = await storage.read(f"{repository_storage_path}/{file_row.file_path}")
    content = raw_bytes.decode("utf-8", errors="replace")

    try:
        extracted = extract_symbols_from_file(file_row.file_path, content)
    except Exception as exc:  # noqa: BLE001 -- one bad file (incl. SyntaxError) must not abort the batch
        logger.warning("Failed to parse %s: %s", file_row.file_path, exc)
        extracted = {"symbols": [], "api_routes": [], "db_models": []}

    # Persist structured symbols (Postgres) -- tagged with kind so
    # ParsedSymbolRepository can store api_route/db_model rows alongside
    # class/function/method rows in the same table.
    symbol_rows = list(extracted["symbols"])
    for route in extracted["api_routes"]:
        symbol_rows.append(
            {
                "kind": "api_route",
                "name": f"{route['method']} {route['path']}",
                "start_line": route.get("line", 1),
                "end_line": route.get("line", 1),
                "http_method": route["method"],
                "route_path": route["path"],
            }
        )
    for model in extracted["db_models"]:
        symbol_rows.append(
            {
                "kind": "db_model",
                "name": model["name"],
                "start_line": 1,
                "end_line": 1,
                "fields": model.get("fields", []),
            }
        )
    await parsed_symbol_repo.replace_for_file(file_row.id, symbol_rows)

    # Chunk + embed + store vectors -- only class/function/method kinds
    # define a source range worth embedding as its own unit.
    chunkable_symbols = [s for s in extracted["symbols"] if s["kind"] in _CHUNKABLE_KINDS]
    chunks = chunk_file(content, chunkable_symbols)
    embedded_chunks = await embed_chunks(chunks, llm)

    await vector_store.delete_for_file(str(repository_id), file_row.file_path)

    points = []
    embedding_rows = []
    for i, ec in enumerate(embedded_chunks):
        point_id = new_point_id()
        payload = {
            "repository_id": str(repository_id),
            "file_path": file_row.file_path,
            "start_line": ec.chunk.start_line,
            "end_line": ec.chunk.end_line,
            "symbol_name": ec.chunk.symbol_name,
            "content": ec.chunk.content,
        }
        points.append({"id": point_id, "vector": ec.vector, "payload": payload})
        embedding_rows.append(
            {
                "chunk_index": i,
                "chunk_text": ec.chunk.content,
                "vector_id": point_id,
                "metadata_json": payload,
            }
        )

    await vector_store.upsert(points)
    await embedding_repo.replace_for_file(file_row.id, embedding_rows)


async def _continue_ingestion_pipeline(repository_id: str, task_id: str) -> None:
    async with AsyncSessionLocal() as db:
        repo_repository = RepositoryRepository(db)
        file_repository = RepositoryFileRepository(db)
        parsed_symbol_repo = ParsedSymbolRepository(db)
        embedding_repo = EmbeddingRepository(db)
        task_repository = TaskRepository(db)

        repo_uuid = uuid.UUID(repository_id)
        repository = await db.get(Repository, repo_uuid)

        await task_repository.update_progress(
            uuid.UUID(task_id), progress=10, status=TaskStatus.RUNNING
        )
        await repo_repository.update_status(repo_uuid, RepositoryStatus.PARSING)
        await db.commit()

        storage = get_file_storage()
        llm = get_llm_provider()
        vector_store = get_vector_store()

        try:
            await vector_store.ensure_collection()

            files_to_process = await file_repository.list_stale_or_pending(repo_uuid)
            total = len(files_to_process)

            for index, file_row in enumerate(files_to_process):
                try:
                    await _process_one_file(
                        repo_uuid,
                        repository.storage_path,
                        file_row,
                        storage,
                        llm,
                        vector_store,
                        parsed_symbol_repo,
                        embedding_repo,
                    )
                    file_row.index_status = FileIndexStatus.INDEXED
                    file_row.last_indexed_commit_hash = repository.latest_commit_hash
                except Exception as exc:  # noqa: BLE001 -- one file's embedding failure shouldn't abort the repo
                    logger.warning("Failed to index %s: %s", file_row.file_path, exc)
                    continue

                await db.commit()
                progress = 10 + int(85 * (index + 1) / max(total, 1))
                await task_repository.update_progress(uuid.UUID(task_id), progress=progress)
                await db.commit()

            await repo_repository.update_status(repo_uuid, RepositoryStatus.READY)
            await task_repository.update_progress(
                uuid.UUID(task_id), progress=100, status=TaskStatus.SUCCEEDED
            )
            await db.commit()

        except Exception as exc:  # noqa: BLE001
            logger.exception("Ingestion pipeline failed for repository %s", repository_id)
            await task_repository.mark_failed(uuid.UUID(task_id), str(exc))
            await repo_repository.update_status(
                repo_uuid, RepositoryStatus.FAILED, status_message=str(exc)
            )
            await db.commit()


@celery_app.task(name="repository_ingestion.continue_pipeline", bind=True, max_retries=3)
def continue_ingestion_pipeline_task(self, repository_id: str, task_id: str) -> None:
    asyncio.run(_continue_ingestion_pipeline(repository_id, task_id))
