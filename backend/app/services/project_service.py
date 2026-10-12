"""Project service — full implementation via ProjectRepository."""

import uuid

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import Pagination
from app.db.session import get_db
from app.models.project import Project
from app.repositories.project_repository import ProjectRepository


class ProjectService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.project_repo = ProjectRepository(db)

    async def create(self, user_id: uuid.UUID, name: str, description: str | None) -> Project:
        project = await self.project_repo.create(user_id, name, description)
        await self.db.commit()
        return project

    async def list_for_user(
        self, user_id: uuid.UUID, pagination: Pagination
    ) -> tuple[list[Project], int]:
        projects, total = await self.project_repo.list_for_user(
            user_id, pagination.limit, pagination.offset
        )
        # repository_count is populated here (not by the ORM relationship) to
        # avoid loading every Repository row just to count them per project.
        for project in projects:
            project.repository_count = await self.project_repo.count_repositories(project.id)
        return projects, total

    async def get(self, user_id: uuid.UUID, project_id: uuid.UUID) -> Project:
        project = await self.project_repo.get_owned(user_id, project_id)
        project.repository_count = await self.project_repo.count_repositories(project.id)
        return project

    async def update(
        self, user_id: uuid.UUID, project_id: uuid.UUID, name: str | None, description: str | None
    ) -> Project:
        project = await self.project_repo.update(user_id, project_id, name, description)
        await self.db.commit()
        return project

    async def delete(self, user_id: uuid.UUID, project_id: uuid.UUID) -> None:
        await self.project_repo.delete(user_id, project_id)
        await self.db.commit()


def get_project_service(db: AsyncSession = Depends(get_db)) -> ProjectService:
    return ProjectService(db)
