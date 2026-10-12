"""Task service — full implementation. Cancellation revokes the underlying
Celery task (best-effort SIGTERM to the worker) in addition to updating
the Task row, so a long-running generation actually stops rather than
just being marked cancelled while continuing to burn LLM budget."""

import uuid

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.task import Task
from app.repositories.task_repository import TaskRepository
from app.tasks.celery_app import celery_app


class TaskService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.task_repo = TaskRepository(db)

    async def get(self, user_id: uuid.UUID, task_id: uuid.UUID) -> Task:
        return await self.task_repo.get_owned(user_id, task_id)

    async def list_for_user(self, user_id: uuid.UUID) -> list[Task]:
        return await self.task_repo.list_for_user(user_id)

    async def cancel(self, user_id: uuid.UUID, task_id: uuid.UUID) -> Task:
        task = await self.task_repo.get_owned(user_id, task_id)  # ownership check
        if task.celery_task_id:
            celery_app.control.revoke(task.celery_task_id, terminate=True, signal="SIGTERM")

        cancelled_task = await self.task_repo.mark_cancelled(user_id, task_id)
        await self.db.commit()
        return cancelled_task


def get_task_service(db: AsyncSession = Depends(get_db)) -> TaskService:
    return TaskService(db)
