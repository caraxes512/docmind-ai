"""Repository model — a single codebase (ZIP upload or GitHub clone).

`latest_commit_hash` and `status` together drive the incremental-reindexing
requirement: when a new webhook/sync detects a different commit hash, only
files whose content_hash differs get marked STALE and re-processed.
"""

import uuid
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import RepositorySourceType, RepositoryStatus

if TYPE_CHECKING:
    from app.models.chat import Chat
    from app.models.documentation_version import DocumentationVersion
    from app.models.project import Project
    from app.models.repository_file import RepositoryFile


class Repository(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "repositories"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    source_type: Mapped[RepositorySourceType] = mapped_column(
        SAEnum(RepositorySourceType, name="repository_source_type"), nullable=False
    )
    github_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    default_branch: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, default="main"
    )
    latest_commit_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)

    # Path within our object storage where the extracted repo tree lives
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False)

    status: Mapped[RepositoryStatus] = mapped_column(
        SAEnum(RepositoryStatus, name="repository_status"),
        default=RepositoryStatus.PENDING,
        nullable=False,
        index=True,
    )
    status_message: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)

    project: Mapped["Project"] = relationship(back_populates="repositories")
    files: Mapped[List["RepositoryFile"]] = relationship(
        back_populates="repository", cascade="all, delete-orphan"
    )
    documentation_versions: Mapped[List["DocumentationVersion"]] = relationship(
        back_populates="repository", cascade="all, delete-orphan"
    )
    chats: Mapped[List["Chat"]] = relationship(
        back_populates="repository", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Repository id={self.id} status={self.status}>"
