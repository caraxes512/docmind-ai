"""DocumentationVersion model — an immutable snapshot marker tied to a commit.

Each time documentation is (re)generated, we create a new version row
(incrementing version_number) and flip `is_current` on the previous version
to False. Individual GeneratedDocument rows attach to a version — for an
incremental regeneration, unaffected doc types are copied by reference
(new GeneratedDocument row pointing at the same content, same version) so
history stays queryable without duplicating unchanged content payloads
unnecessarily. (Content de-duplication itself happens at the service layer
via content-hash comparison before insert.)
"""

import uuid
from typing import TYPE_CHECKING, List

from sqlalchemy import Boolean, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.generated_document import GeneratedDocument
    from app.models.repository import Repository


class DocumentationVersion(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "documentation_versions"
    __table_args__ = (
        UniqueConstraint("repository_id", "version_number", name="uq_repo_version_number"),
    )

    repository_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    commit_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    repository: Mapped["Repository"] = relationship(back_populates="documentation_versions")
    documents: Mapped[List["GeneratedDocument"]] = relationship(
        back_populates="version", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<DocumentationVersion id={self.id} v={self.version_number}>"
