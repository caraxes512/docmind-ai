"""Export service — full implementation, including get_download (closed
in Step 11 — see Task model's docstring for why export_version_id/
export_format live there)."""

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.models.enums import DocumentType, ExportFormat, TaskStatus, TaskType
from app.models.task import Task
from app.repositories.documentation_repository import DocumentationRepository
from app.repositories.task_repository import TaskRepository
from app.schemas.export import ExportDownloadResponse
from app.services.storage_service import FileStorage, get_file_storage

_EXTENSION_MAP = {ExportFormat.MARKDOWN: "md", ExportFormat.HTML: "html", ExportFormat.PDF: "pdf"}
_DOWNLOAD_URL_TTL_SECONDS = 3600


class ExportService:
    def __init__(self, db: AsyncSession, storage: FileStorage):
        self.db = db
        self.storage = storage
        self.doc_repo = DocumentationRepository(db)
        self.task_repo = TaskRepository(db)

    async def start_export(
        self,
        user_id: uuid.UUID,
        version_id: uuid.UUID,
        format: ExportFormat,
        doc_types: list[DocumentType] | None,
    ) -> Task:
        version = await self.doc_repo.get_version_owned(user_id, version_id)  # ownership check

        task = await self.task_repo.create(
            user_id=user_id,
            task_type=TaskType.EXPORT,
            export_version_id=version.id,
            export_format=format,
        )
        await self.db.commit()

        from app.tasks.export_tasks import export_documentation_task

        export_documentation_task.delay(
            str(version.id),
            str(task.id),
            format.value,
            [d.value for d in doc_types] if doc_types else None,
        )
        return task

    async def get_download(
        self, user_id: uuid.UUID, export_id: uuid.UUID
    ) -> ExportDownloadResponse:
        """`export_id` is the Task id returned by start_export."""
        task = await self.task_repo.get_owned(user_id, export_id)

        if task.status != TaskStatus.SUCCEEDED:
            raise NotFoundError(f"Export {export_id} is not ready (status={task.status.value})")
        if task.export_version_id is None or task.export_format is None:
            # Defensive — shouldn't happen for a genuine EXPORT task created via
            # start_export, but a malformed/legacy row shouldn't 500.
            raise NotFoundError(f"Export {export_id} is missing its target version/format")

        extension = _EXTENSION_MAP[task.export_format]
        export_path = f"exports/{task.export_version_id}.{extension}"

        download_url = await self.storage.get_download_url(export_path, _DOWNLOAD_URL_TTL_SECONDS)
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=_DOWNLOAD_URL_TTL_SECONDS)

        return ExportDownloadResponse(
            download_url=download_url,
            expires_at=expires_at,
            format=task.export_format,
        )


def get_export_service(
    db: AsyncSession = Depends(get_db),
    storage: FileStorage = Depends(get_file_storage),
) -> ExportService:
    return ExportService(db, storage)
