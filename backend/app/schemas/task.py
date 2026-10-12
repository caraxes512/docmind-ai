"""Async job (Task) schemas — progress polling, cancellation."""

import uuid
from datetime import datetime
from typing import Optional

from app.models.enums import TaskStatus, TaskType
from app.schemas.common import ORMBase


class TaskRead(ORMBase):
    id: uuid.UUID
    task_type: TaskType
    status: TaskStatus
    progress: int
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
