import uuid
from typing import Optional

from sqlalchemy import select

from app.core.exceptions import NotFoundError
from app.models.enums import ExportFormat, TaskStatus, TaskType
from app.models.task import Task
from app.repositories.base import BaseRepository


class TaskRepository(BaseRepository):
    async def create(
        self,
        user_id: uuid.UUID,
        task_type: TaskType,
        repository_id: Optional[uuid.UUID] = None,
        celery_task_id: Optional[str] = None,
        export_version_id: Optional[uuid.UUID] = None,
        export_format: Optional[ExportFormat] = None,
    ) -> Task:
        task = Task(
            user_id=user_id,
            repository_id=repository_id,
            task_type=task_type,
            celery_task_id=celery_task_id,
            status=TaskStatus.QUEUED,
            export_version_id=export_version_id,
            export_format=export_format,
        )
        self.db.add(task)
        await self.db.flush()
        return task

    async def get_owned(self, user_id: uuid.UUID, task_id: uuid.UUID) -> Task:
        result = await self.db.execute(
            select(Task).where(Task.id == task_id, Task.user_id == user_id)
        )
        task = result.scalar_one_or_none()
        if task is None:
            raise NotFoundError(f"Task {task_id} not found")
        return task

    async def list_for_user(self, user_id: uuid.UUID) -> list[Task]:
        result = await self.db.execute(
            select(Task).where(Task.user_id == user_id).order_by(Task.created_at.desc()).limit(100)
        )
        return list(result.scalars().all())

    async def update_progress(
        self, task_id: uuid.UUID, progress: int, status: Optional[TaskStatus] = None
    ) -> None:
        result = await self.db.execute(select(Task).where(Task.id == task_id))
        task = result.scalar_one_or_none()
        if task is None:
            raise NotFoundError(f"Task {task_id} not found")
        task.progress = progress
        if status is not None:
            task.status = status
        await self.db.flush()

    async def mark_failed(self, task_id: uuid.UUID, error_message: str) -> None:
        result = await self.db.execute(select(Task).where(Task.id == task_id))
        task = result.scalar_one_or_none()
        if task is None:
            raise NotFoundError(f"Task {task_id} not found")
        task.status = TaskStatus.FAILED
        task.error_message = error_message
        await self.db.flush()

    async def mark_cancelled(self, user_id: uuid.UUID, task_id: uuid.UUID) -> Task:
        task = await self.get_owned(user_id, task_id)
        task.status = TaskStatus.CANCELLED
        await self.db.flush()
        return task
