"""Task model — tracks an async Celery job for progress/cancellation/retry.

`celery_task_id` links to the underlying Celery task for cancellation
(celery.control.revoke) without exposing Celery internals to the API layer.
`progress` is a 0-100 integer updated by the worker via periodic
`self.update_state` calls proxied into this row (through a lightweight
polling endpoint or WebSocket push — decided in Step 5/6).

`export_version_id`/`export_format` are nullable and only meaningful for
TaskType.EXPORT rows — added in Step 11 to close a gap flagged back in
Step 5: ExportService.get_download couldn't map a Task id back to which
version/format was actually exported without storing it somewhere. A
dedicated Export table was considered and rejected as overkill for two
extra nullable columns on a row that already carries task-type-specific
context (repository_id is the same pattern, nullable and type-specific).
"""

import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import ExportFormat, TaskStatus, TaskType

if TYPE_CHECKING:
    from app.models.user import User


class Task(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "tasks"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # nullable because some tasks (e.g. export) may target a doc version, not a repo directly
    repository_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    task_type: Mapped[TaskType] = mapped_column(SAEnum(TaskType, name="task_type"), nullable=False)
    celery_task_id: Mapped[Optional[str]] = mapped_column(
        String(155), nullable=True, unique=True, index=True
    )

    status: Mapped[TaskStatus] = mapped_column(
        SAEnum(TaskStatus, name="task_status"),
        default=TaskStatus.QUEUED,
        nullable=False,
        index=True,
    )
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)

    # TaskType.EXPORT only — see module docstring.
    export_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documentation_versions.id", ondelete="CASCADE"),
        nullable=True,
    )
    export_format: Mapped[Optional[ExportFormat]] = mapped_column(
        SAEnum(ExportFormat, name="task_export_format"), nullable=True
    )

    user: Mapped["User"] = relationship(back_populates="tasks")

    def __repr__(self) -> str:
        return f"<Task id={self.id} type={self.task_type} status={self.status}>"
