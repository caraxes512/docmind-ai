"""Repository endpoints: ZIP upload, GitHub clone, reads, file listing.

Creation endpoints nest under /projects/{project_id}/repositories since a
repository cannot exist without a parent project. All other operations are
flat (/repositories/{id}) once the caller has the id.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile, status

from app.api.deps import Pagination, get_current_user, get_pagination
from app.models.user import User
from app.schemas.common import Page
from app.schemas.repository import (
    RepositoryCloneRequest,
    RepositoryFileRead,
    RepositoryRead,
    UploadInitiatedResponse,
)
from app.services.repo_ingestion_service import (
    RepositoryIngestionService,
    get_repository_ingestion_service,
)

router = APIRouter(tags=["repositories"])

MAX_UPLOAD_SIZE_BYTES = (
    200 * 1024 * 1024
)  # 200MB — enforced in the service layer (streamed, not buffered)


@router.post(
    "/projects/{project_id}/repositories/upload",
    response_model=UploadInitiatedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_repository(
    project_id: UUID,
    file: UploadFile = File(..., description="A .zip archive of the repository"),
    current_user: User = Depends(get_current_user),
    service: RepositoryIngestionService = Depends(get_repository_ingestion_service),
) -> UploadInitiatedResponse:
    repository, task = await service.upload_zip(current_user.id, project_id, file)
    return UploadInitiatedResponse(
        repository=RepositoryRead.model_validate(repository), task_id=task.id
    )


@router.post(
    "/projects/{project_id}/repositories/clone",
    response_model=UploadInitiatedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def clone_repository(
    project_id: UUID,
    body: RepositoryCloneRequest,
    current_user: User = Depends(get_current_user),
    service: RepositoryIngestionService = Depends(get_repository_ingestion_service),
) -> UploadInitiatedResponse:
    """Handles both public clones and private clones (via the user's stored
    GitHub OAuth token) — the service layer determines which path applies."""
    repository, task = await service.clone_github(
        current_user.id, project_id, body.github_url, body.branch
    )
    return UploadInitiatedResponse(
        repository=RepositoryRead.model_validate(repository), task_id=task.id
    )


@router.get("/projects/{project_id}/repositories", response_model=Page[RepositoryRead])
async def list_repositories(
    project_id: UUID,
    pagination: Pagination = Depends(get_pagination),
    current_user: User = Depends(get_current_user),
    service: RepositoryIngestionService = Depends(get_repository_ingestion_service),
) -> Page[RepositoryRead]:
    repos, total = await service.list_for_project(current_user.id, project_id, pagination)
    return Page(
        items=[RepositoryRead.model_validate(r) for r in repos],
        total=total,
        limit=pagination.limit,
        offset=pagination.offset,
    )


@router.get("/repositories/{repository_id}", response_model=RepositoryRead)
async def get_repository(
    repository_id: UUID,
    current_user: User = Depends(get_current_user),
    service: RepositoryIngestionService = Depends(get_repository_ingestion_service),
) -> RepositoryRead:
    repository = await service.get(current_user.id, repository_id)
    return RepositoryRead.model_validate(repository)


@router.delete("/repositories/{repository_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_repository(
    repository_id: UUID,
    current_user: User = Depends(get_current_user),
    service: RepositoryIngestionService = Depends(get_repository_ingestion_service),
) -> None:
    await service.delete(current_user.id, repository_id)


@router.get("/repositories/{repository_id}/files", response_model=Page[RepositoryFileRead])
async def list_repository_files(
    repository_id: UUID,
    pagination: Pagination = Depends(get_pagination),
    current_user: User = Depends(get_current_user),
    service: RepositoryIngestionService = Depends(get_repository_ingestion_service),
) -> Page[RepositoryFileRead]:
    files, total = await service.list_files(current_user.id, repository_id, pagination)
    return Page(
        items=[RepositoryFileRead.model_validate(f) for f in files],
        total=total,
        limit=pagination.limit,
        offset=pagination.offset,
    )
