import uuid
from typing import Optional

from sqlalchemy import func, select

from app.core.exceptions import NotFoundError
from app.models.project import Project
from app.models.repository import Repository
from app.repositories.base import BaseRepository


class ProjectRepository(BaseRepository):
    async def create(self, user_id: uuid.UUID, name: str, description: Optional[str]) -> Project:
        project = Project(user_id=user_id, name=name, description=description)
        self.db.add(project)
        await self.db.flush()
        return project

    async def list_for_user(
        self, user_id: uuid.UUID, limit: int, offset: int
    ) -> tuple[list[Project], int]:
        count_result = await self.db.execute(
            select(func.count()).select_from(Project).where(Project.user_id == user_id)
        )
        total = count_result.scalar_one()

        result = await self.db.execute(
            select(Project)
            .where(Project.user_id == user_id)
            .order_by(Project.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all()), total

    async def get_owned(self, user_id: uuid.UUID, project_id: uuid.UUID) -> Project:
        result = await self.db.execute(
            select(Project).where(Project.id == project_id, Project.user_id == user_id)
        )
        project = result.scalar_one_or_none()
        if project is None:
            raise NotFoundError(f"Project {project_id} not found")
        return project

    async def count_repositories(self, project_id: uuid.UUID) -> int:
        result = await self.db.execute(
            select(func.count()).select_from(Repository).where(Repository.project_id == project_id)
        )
        return result.scalar_one()

    async def update(
        self,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
        name: Optional[str],
        description: Optional[str],
    ) -> Project:
        project = await self.get_owned(user_id, project_id)
        if name is not None:
            project.name = name
        if description is not None:
            project.description = description
        await self.db.flush()
        return project

    async def delete(self, user_id: uuid.UUID, project_id: uuid.UUID) -> None:
        project = await self.get_owned(user_id, project_id)
        await self.db.delete(project)
        await self.db.flush()
