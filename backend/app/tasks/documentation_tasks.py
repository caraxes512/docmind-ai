"""Celery task for documentation generation/regeneration.

As of Step 9, `parsed_symbols` is read from Postgres (ParsedSymbol rows
written during ingestion) rather than left empty -- this is the change
that finally lets the generation graph run past parser_agent end-to-end.
Manifest/config file context (for the Repository Analyzer Agent) was
already wired for real in Step 7.
"""

import asyncio
import logging
import uuid

from app.agents.orchestrator import Orchestrator
from app.agents.state import ParsedSymbols
from app.db.session import AsyncSessionLocal
from app.llm.openai_provider import get_llm_provider
from app.models.enums import DocumentStatus, DocumentType, SymbolKind, TaskStatus
from app.models.generated_document import GeneratedDocument
from app.models.repository import Repository
from app.repositories.documentation_repository import DocumentationRepository
from app.repositories.parsed_symbol_repository import ParsedSymbolRepository
from app.repositories.repository_file_repository import RepositoryFileRepository
from app.repositories.task_repository import TaskRepository
from app.repositories.usage_log_repository import UsageLogRepository
from app.services.storage_service import get_file_storage
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

_MANIFEST_FILENAMES = {"requirements.txt", "package.json", "pyproject.toml", "pom.xml", "go.mod"}
_CONFIG_FILENAMES = {"docker-compose.yml", "docker-compose.yaml", ".env.example", "Dockerfile"}


def _build_parsed_symbols(rows) -> ParsedSymbols:
    """Converts flat ParsedSymbol ORM rows (Postgres) into the ParsedSymbols
    shape the generation graph's state expects (see app/agents/state.py)."""
    symbols_by_file: dict[str, list[dict]] = {}
    api_routes: list[dict] = []
    db_models: list[dict] = []

    for row in rows:
        file_path = row.repository_file.file_path

        if row.kind in (SymbolKind.CLASS, SymbolKind.FUNCTION, SymbolKind.METHOD):
            symbols_by_file.setdefault(file_path, []).append(
                {
                    "kind": row.kind.value,
                    "name": row.name,
                    "start_line": row.start_line,
                    "end_line": row.end_line,
                    "signature": row.signature,
                    "docstring": row.docstring,
                }
            )
        elif row.kind == SymbolKind.API_ROUTE:
            api_routes.append(
                {
                    "method": row.http_method,
                    "path": row.route_path,
                    "file_path": file_path,
                    "line": row.start_line,
                }
            )
        elif row.kind == SymbolKind.DB_MODEL:
            db_models.append(
                {"name": row.name, "fields": row.fields_json or [], "file_path": file_path}
            )

    return ParsedSymbols(
        symbols_by_file=symbols_by_file, api_routes=api_routes, db_models=db_models
    )


async def _build_repository_context(repository_id: uuid.UUID, db) -> dict:
    """Assembles real inputs for the graph: file tree + manifest/config
    contents (for Repository Analyzer Agent) and precomputed parsed
    symbols (for Parser Agent — a DB read now, not a re-parse)."""
    storage = get_file_storage()
    file_repo = RepositoryFileRepository(db)
    parsed_symbol_repo = ParsedSymbolRepository(db)

    repository = await db.get(Repository, repository_id)
    files = await file_repo.list_all_for_repository(repository_id)
    file_tree = [f.file_path for f in files]

    manifest_parts: list[str] = []
    config_parts: list[str] = []

    for f in files:
        basename = f.file_path.rsplit("/", 1)[-1]
        if basename not in _MANIFEST_FILENAMES and basename not in _CONFIG_FILENAMES:
            continue
        try:
            raw = await storage.read(f"{repository.storage_path}/{f.file_path}")
            text = raw.decode("utf-8", errors="replace")
        except Exception as exc:  # noqa: BLE001 -- a single unreadable manifest shouldn't abort analysis
            logger.warning(
                "Could not read %s for repository %s: %s", f.file_path, repository_id, exc
            )
            text = ""
        target = manifest_parts if basename in _MANIFEST_FILENAMES else config_parts
        target.append(f"--- {f.file_path} ---\n{text}")

    symbol_rows = await parsed_symbol_repo.get_all_for_repository(repository_id)

    return {
        "file_tree": file_tree,
        "manifest_contents": "\n\n".join(manifest_parts),
        "config_file_contents": "\n\n".join(config_parts),
        "precomputed_symbols": _build_parsed_symbols(symbol_rows),
        "commit_hash": repository.latest_commit_hash or "",
    }


async def _run_generation(
    repository_id: str,
    task_id: str,
    doc_types: list[str] | None,
    is_incremental: bool,
) -> None:
    async with AsyncSessionLocal() as db:
        task_repository = TaskRepository(db)
        documentation_repository = DocumentationRepository(db)
        usage_log_repository = UsageLogRepository(db)

        await task_repository.update_progress(
            uuid.UUID(task_id), progress=5, status=TaskStatus.RUNNING
        )
        await db.commit()

        try:
            context = await _build_repository_context(uuid.UUID(repository_id), db)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to build repository context for %s", repository_id)
            await task_repository.mark_failed(
                uuid.UUID(task_id), f"Failed to read repository files: {exc}"
            )
            await db.commit()
            return

        orchestrator = Orchestrator(llm=get_llm_provider())
        requested = [DocumentType(d) for d in doc_types] if doc_types else None

        try:
            final_state = await orchestrator.generate_documentation(
                repository_id=repository_id,
                commit_hash=context["commit_hash"],
                task_id=task_id,
                doc_types_requested=requested,
                precomputed_symbols=context["precomputed_symbols"],
                file_tree=context["file_tree"],
                manifest_contents=context["manifest_contents"],
                config_file_contents=context["config_file_contents"],
                is_incremental=is_incremental,
            )

            await usage_log_repository.bulk_insert(
                uuid.UUID(task_id), final_state.get("usage_log", [])
            )
            await db.commit()

            if not final_state.get("generated_documents"):
                raise RuntimeError(
                    "Graph produced no documents — repository may not have been fully ingested yet "
                    "(check the repository's ingestion Task status)"
                )

            version = await documentation_repository.create_version(
                uuid.UUID(repository_id), commit_hash=context["commit_hash"]
            )
            for doc_type_value, content in final_state["generated_documents"].items():
                if doc_type_value.startswith("_"):
                    continue
                db.add(
                    GeneratedDocument(
                        version_id=version.id,
                        doc_type=DocumentType(doc_type_value),
                        content=content,
                        status=DocumentStatus.COMPLETE,
                    )
                )

            diagrams = {
                k: v for k, v in final_state.get("diagrams", {}).items() if not k.startswith("_")
            }
            if diagrams:
                diagram_doc_content = "\n\n".join(
                    f"## {name.replace('_', ' ').title()}\n\n```mermaid\n{source}\n```"
                    for name, source in diagrams.items()
                )
                db.add(
                    GeneratedDocument(
                        version_id=version.id,
                        doc_type=DocumentType.DIAGRAM,
                        content=diagram_doc_content,
                        status=DocumentStatus.COMPLETE,
                    )
                )

            await db.commit()
            await task_repository.update_progress(
                uuid.UUID(task_id), progress=100, status=TaskStatus.SUCCEEDED
            )
            await db.commit()
        except Exception as exc:  # noqa: BLE001 -- task-level catch-all, error persisted for visibility
            logger.exception("Documentation generation task failed unexpectedly")
            await task_repository.mark_failed(uuid.UUID(task_id), str(exc))
            await db.commit()


@celery_app.task(name="documentation.generate", bind=True, max_retries=2)
def generate_documentation_task(
    self,
    repository_id: str,
    task_id: str,
    doc_types: list[str] | None = None,
    is_incremental: bool = False,
) -> None:
    asyncio.run(_run_generation(repository_id, task_id, doc_types, is_incremental))
