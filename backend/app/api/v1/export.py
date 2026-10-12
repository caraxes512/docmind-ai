"""Export endpoints — Markdown/HTML/PDF export of a documentation version."""

from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.export import ExportDownloadResponse, ExportInitiatedResponse, ExportRequest
from app.services.export_service import ExportService, get_export_service

router = APIRouter(tags=["export"])


@router.post(
    "/documentation/versions/{version_id}/export",
    response_model=ExportInitiatedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def export_version(
    version_id: UUID,
    body: ExportRequest,
    current_user: User = Depends(get_current_user),
    service: ExportService = Depends(get_export_service),
) -> ExportInitiatedResponse:
    task = await service.start_export(current_user.id, version_id, body.format, body.doc_types)
    return ExportInitiatedResponse(task_id=task.id)


@router.get("/exports/{export_id}/download", response_model=ExportDownloadResponse)
async def get_export_download(
    export_id: UUID,
    current_user: User = Depends(get_current_user),
    service: ExportService = Depends(get_export_service),
) -> ExportDownloadResponse:
    """Returns a pre-signed, time-limited URL rather than streaming the file
    body — keeps the API process free of large binary payloads."""
    return await service.get_download(current_user.id, export_id)
