import uuid
from typing import Optional

from sqlalchemy import func, select

from app.core.exceptions import NotFoundError
from app.models.enums import RepositorySourceType, RepositoryStatus
from app.models.project import Project
from app.models.repository import Repository
from app.models.repository_file import RepositoryFile
from app.repositories.base import BaseRepository


class RepositoryRepository(BaseRepository):
    """Ownership for a Repository is indirect (via its parent Project), so
    every scoped query here joins through Project.user_id rather than
    assuming Repository carries its own user_id column — this mirrors the
    Step 2 schema exactly (Repository has no user_id FK)."""

    async def create(
        self,
        project_id: uuid.UUID,
        source_type: RepositorySourceType,
        storage_path: str,
        github_url: Optional[str] = None,
        default_branch: Optional[str] = None,
    ) -> Repository:
        repository = Repository(
            project_id=project_id,
            source_type=source_type,
            storage_path=storage_path,
            github_url=github_url,
            default_branch=default_branch,
            status=RepositoryStatus.PENDING,
        )
        self.db.add(repository)
        await self.db.flush()
        return repository

    async def get_owned(self, user_id: uuid.UUID, repository_id: uuid.UUID) -> Repository:
        result = await self.db.execute(
            select(Repository)
            .join(Project, Repository.project_id == Project.id)
            .where(Repository.id == repository_id, Project.user_id == user_id)
        )
        repository = result.scalar_one_or_none()
        if repository is None:
            raise NotFoundError(f"Repository {repository_id} not found")
        return repository

    async def list_for_project(
        self, user_id: uuid.UUID, project_id: uuid.UUID, limit: int, offset: int
    ) -> tuple[list[Repository], int]:
        base_filter = (
            select(Repository)
            .join(Project, Repository.project_id == Project.id)
            .where(Repository.project_id == project_id, Project.user_id == user_id)
        )
        count_result = await self.db.execute(
            select(func.count()).select_from(base_filter.subquery())
        )
        total = count_result.scalar_one()

        result = await self.db.execute(
            base_filter.order_by(Repository.created_at.desc()).limit(limit).offset(offset)
        )
        return list(result.scalars().all()), total

    async def update_status(
        self,
        repository_id: uuid.UUID,
        status: RepositoryStatus,
        status_message: Optional[str] = None,
    ) -> None:
        result = await self.db.execute(select(Repository).where(Repository.id == repository_id))
        repository = result.scalar_one_or_none()
        if repository is None:
            raise NotFoundError(f"Repository {repository_id} not found")
        repository.status = status
        if status_message is not None:
            repository.status_message = status_message
        await self.db.flush()

    async def set_latest_commit_hash(self, repository_id: uuid.UUID, commit_hash: str) -> None:
        result = await self.db.execute(select(Repository).where(Repository.id == repository_id))
        repository = result.scalar_one_or_none()
        if repository is None:
            raise NotFoundError(f"Repository {repository_id} not found")
        repository.latest_commit_hash = commit_hash
        await self.db.flush()

    async def delete(self, user_id: uuid.UUID, repository_id: uuid.UUID) -> None:
        repository = await self.get_owned(user_id, repository_id)
        await self.db.delete(repository)
        await self.db.flush()

    async def list_files(
        self, user_id: uuid.UUID, repository_id: uuid.UUID, limit: int, offset: int
    ) -> tuple[list[RepositoryFile], int]:
        await self.get_owned(user_id, repository_id)  # raises NotFoundError if not owned

        count_result = await self.db.execute(
            select(func.count())
            .select_from(RepositoryFile)
            .where(RepositoryFile.repository_id == repository_id)
        )
        total = count_result.scalar_one()

        result = await self.db.execute(
            select(RepositoryFile)
            .where(RepositoryFile.repository_id == repository_id)
            .order_by(RepositoryFile.file_path)
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all()), total
