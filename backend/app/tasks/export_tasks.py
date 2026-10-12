"""Export Celery task — renders a documentation version and stores the
result, making it available via ExportService.get_download. All three
formats (Markdown, HTML, PDF) are fully implemented as of Step 11 — PDF
needs WeasyPrint's system libraries (see backend/Dockerfile), which is
why render_export imports weasyprint lazily rather than at module load.
"""

import asyncio
import logging
import uuid

from app.agents.export_agent import render_export
from app.db.session import AsyncSessionLocal
from app.models.documentation_version import DocumentationVersion
from app.models.enums import ExportFormat, TaskStatus
from app.repositories.task_repository import TaskRepository
from app.services.storage_service import get_file_storage
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

_EXTENSION_MAP = {ExportFormat.MARKDOWN: "md", ExportFormat.HTML: "html", ExportFormat.PDF: "pdf"}


async def _run_export(
    version_id: str, task_id: str, export_format: str, doc_types: list[str] | None
) -> None:
    async with AsyncSessionLocal() as db:
        task_repository = TaskRepository(db)
        storage = get_file_storage()

        await task_repository.update_progress(
            uuid.UUID(task_id), progress=10, status=TaskStatus.RUNNING
        )
        await db.commit()

        try:
            # Owner check is skipped here deliberately: the Task row itself was
            # only created after ExportService.start_export already verified
            # ownership at the HTTP layer — this worker trusts the Task exists
            # because of that prior check, not because it re-derives user_id here.
            version = await db.get(DocumentationVersion, uuid.UUID(version_id))
            documents = {
                doc.doc_type.value: doc.content
                for doc in version.documents
                if doc_types is None or doc.doc_type.value in doc_types
            }

            fmt = ExportFormat(export_format)
            rendered_bytes = render_export(documents, fmt)

            export_path = f"exports/{version_id}.{_EXTENSION_MAP[fmt]}"
            await storage.save(export_path, rendered_bytes)

            await task_repository.update_progress(
                uuid.UUID(task_id), progress=100, status=TaskStatus.SUCCEEDED
            )
            await db.commit()
        except NotImplementedError as exc:
            logger.info("Export stopped (format not yet supported): %s", exc)
            await task_repository.mark_failed(uuid.UUID(task_id), str(exc))
            await db.commit()
        except Exception as exc:  # noqa: BLE001
            logger.exception("Export task failed unexpectedly")
            await task_repository.mark_failed(uuid.UUID(task_id), str(exc))
            await db.commit()


@celery_app.task(name="export.render", bind=True, max_retries=2)
def export_documentation_task(
    self, version_id: str, task_id: str, export_format: str, doc_types: list[str] | None = None
) -> None:
    asyncio.run(_run_export(version_id, task_id, export_format, doc_types))
