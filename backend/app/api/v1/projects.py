"""Project CRUD endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.deps import Pagination, get_current_user, get_pagination
from app.models.user import User
from app.schemas.common import Page
from app.schemas.project import ProjectCreate, ProjectRead, ProjectUpdate
from app.services.project_service import ProjectService, get_project_service

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
async def create_project(
    body: ProjectCreate,
    current_user: User = Depends(get_current_user),
    service: ProjectService = Depends(get_project_service),
) -> ProjectRead:
    project = await service.create(current_user.id, body.name, body.description)
    return ProjectRead.model_validate(project)


@router.get("", response_model=Page[ProjectRead])
async def list_projects(
    pagination: Pagination = Depends(get_pagination),
    current_user: User = Depends(get_current_user),
    service: ProjectService = Depends(get_project_service),
) -> Page[ProjectRead]:
    projects, total = await service.list_for_user(current_user.id, pagination)
    return Page(
        items=[ProjectRead.model_validate(p) for p in projects],
        total=total,
        limit=pagination.limit,
        offset=pagination.offset,
    )


@router.get("/{project_id}", response_model=ProjectRead)
async def get_project(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    service: ProjectService = Depends(get_project_service),
) -> ProjectRead:
    project = await service.get(current_user.id, project_id)
    return ProjectRead.model_validate(project)


@router.patch("/{project_id}", response_model=ProjectRead)
async def update_project(
    project_id: UUID,
    body: ProjectUpdate,
    current_user: User = Depends(get_current_user),
    service: ProjectService = Depends(get_project_service),
) -> ProjectRead:
    project = await service.update(current_user.id, project_id, body.name, body.description)
    return ProjectRead.model_validate(project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    service: ProjectService = Depends(get_project_service),
) -> None:
    await service.delete(current_user.id, project_id)
