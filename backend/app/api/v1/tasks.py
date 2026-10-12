"""Task (async job) endpoints — progress polling and cancellation."""

from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.task import TaskRead
from app.services.task_service import TaskService, get_task_service

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=list[TaskRead])
async def list_tasks(
    current_user: User = Depends(get_current_user),
    service: TaskService = Depends(get_task_service),
) -> list[TaskRead]:
    tasks = await service.list_for_user(current_user.id)
    return [TaskRead.model_validate(t) for t in tasks]


@router.get("/{task_id}", response_model=TaskRead)
async def get_task(
    task_id: UUID,
    current_user: User = Depends(get_current_user),
    service: TaskService = Depends(get_task_service),
) -> TaskRead:
    task = await service.get(current_user.id, task_id)
    return TaskRead.model_validate(task)


@router.post("/{task_id}/cancel", response_model=TaskRead, status_code=status.HTTP_200_OK)
async def cancel_task(
    task_id: UUID,
    current_user: User = Depends(get_current_user),
    service: TaskService = Depends(get_task_service),
) -> TaskRead:
    task = await service.cancel(current_user.id, task_id)
    return TaskRead.model_validate(task)
