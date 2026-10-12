"""Documentation service. Version/document reads, listing, and manual
editing are fully implemented via DocumentationRepository. `generate` and
`regenerate` enqueue real Celery tasks (which stop at the LLM call boundary
until Step 7's file/manifest wiring reaches parser_agent in Step 9).
`trigger_review` is fully implemented — a single-document review doesn't
need the full graph, just the Reviewer Agent's logic directly.
"""

import uuid

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.reviewer_agent import review_single_document
from app.db.session import get_db
from app.llm.openai_provider import get_llm_provider
from app.models.documentation_version import DocumentationVersion
from app.models.enums import DocumentType, SymbolKind, TaskType
from app.models.generated_document import GeneratedDocument
from app.models.review_result import ReviewResult
from app.models.task import Task
from app.repositories.documentation_repository import DocumentationRepository
from app.repositories.parsed_symbol_repository import ParsedSymbolRepository
from app.repositories.repository_repository import RepositoryRepository
from app.repositories.task_repository import TaskRepository
from app.repositories.usage_log_repository import UsageLogRepository


class DocumentationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.doc_repo = DocumentationRepository(db)
        self.repository_repo = RepositoryRepository(db)
        self.task_repo = TaskRepository(db)
        self.usage_log_repo = UsageLogRepository(db)
        self.parsed_symbol_repo = ParsedSymbolRepository(db)

    async def generate(
        self, user_id: uuid.UUID, repository_id: uuid.UUID, doc_types: list[DocumentType] | None
    ) -> Task:
        await self.repository_repo.get_owned(user_id, repository_id)  # ownership check

        task = await self.task_repo.create(
            user_id=user_id,
            task_type=TaskType.FULL_DOCUMENTATION_GENERATION,
            repository_id=repository_id,
        )
        await self.db.commit()

        from app.tasks.documentation_tasks import generate_documentation_task

        generate_documentation_task.delay(
            str(repository_id),
            str(task.id),
            [d.value for d in doc_types] if doc_types else None,
            False,
        )
        return task

    async def regenerate(
        self,
        user_id: uuid.UUID,
        repository_id: uuid.UUID,
        doc_types: list[DocumentType] | None,
        force_full: bool,
    ) -> Task:
        await self.repository_repo.get_owned(user_id, repository_id)

        task = await self.task_repo.create(
            user_id=user_id,
            task_type=TaskType.INCREMENTAL_REGENERATION,
            repository_id=repository_id,
        )
        await self.db.commit()

        from app.tasks.documentation_tasks import generate_documentation_task

        generate_documentation_task.delay(
            str(repository_id),
            str(task.id),
            [d.value for d in doc_types] if doc_types else None,
            not force_full,
        )
        return task

    async def get_current_version(
        self, user_id: uuid.UUID, repository_id: uuid.UUID
    ) -> DocumentationVersion:
        return await self.doc_repo.get_current_version(user_id, repository_id)

    async def list_versions(
        self, user_id: uuid.UUID, repository_id: uuid.UUID
    ) -> list[DocumentationVersion]:
        return await self.doc_repo.list_versions(user_id, repository_id)

    async def get_version(self, user_id: uuid.UUID, version_id: uuid.UUID) -> DocumentationVersion:
        return await self.doc_repo.get_version_owned(user_id, version_id)

    async def get_document(self, user_id: uuid.UUID, document_id: uuid.UUID) -> GeneratedDocument:
        return await self.doc_repo.get_document_owned(user_id, document_id)

    async def update_document(
        self, user_id: uuid.UUID, document_id: uuid.UUID, content: str
    ) -> GeneratedDocument:
        document = await self.doc_repo.update_document_content(user_id, document_id, content)
        await self.db.commit()
        return document

    async def trigger_review(self, user_id: uuid.UUID, document_id: uuid.UUID) -> ReviewResult:
        document = await self.doc_repo.get_document_owned(user_id, document_id)

        # As of Step 9: real cross-reference data, read from ParsedSymbol
        # rows persisted during ingestion — this was a known gap flagged in
        # Step 7 (cross_reference={} then, since nothing was queryable yet).
        cross_reference = await self._build_cross_reference(
            document.doc_type.value, document.version.repository_id
        )

        review_data, usage_log, _errors = await review_single_document(
            doc_type=document.doc_type.value,
            content=document.content,
            cross_reference=cross_reference,
            llm=get_llm_provider(),
        )

        review_result = await self.doc_repo.upsert_review_result(
            document_id, review_data["score"], review_data["issues"]
        )
        await self.usage_log_repo.bulk_insert(None, usage_log)
        await self.db.commit()
        return review_result

    async def _build_cross_reference(self, doc_type: str, repository_id: uuid.UUID) -> dict:
        if doc_type not in ("api_docs", "database_docs"):
            return {}

        rows = await self.parsed_symbol_repo.get_all_for_repository(repository_id)
        if doc_type == "api_docs":
            return {
                "api_routes": [
                    {
                        "method": r.http_method,
                        "path": r.route_path,
                        "file_path": r.repository_file.file_path,
                    }
                    for r in rows
                    if r.kind == SymbolKind.API_ROUTE
                ]
            }
        return {
            "db_models": [
                {
                    "name": r.name,
                    "fields": r.fields_json or [],
                    "file_path": r.repository_file.file_path,
                }
                for r in rows
                if r.kind == SymbolKind.DB_MODEL
            ]
        }


def get_documentation_service(db: AsyncSession = Depends(get_db)) -> DocumentationService:
    return DocumentationService(db)
