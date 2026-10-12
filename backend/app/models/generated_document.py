"""GeneratedDocument model — one document (README, API docs, etc.) for a version.

A unique constraint on (version_id, doc_type) enforces "one document of
each type per version" — the service layer decides whether to create a new
DocumentationVersion (full regen) or attach to the existing current version
(incremental regen of a subset of doc types).
"""

import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import DocumentStatus, DocumentType

if TYPE_CHECKING:
    from app.models.documentation_version import DocumentationVersion
    from app.models.review_result import ReviewResult


class GeneratedDocument(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "generated_documents"
    __table_args__ = (UniqueConstraint("version_id", "doc_type", name="uq_version_doc_type"),)

    version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documentation_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    doc_type: Mapped[DocumentType] = mapped_column(
        SAEnum(DocumentType, name="document_type"), nullable=False
    )
    # Markdown source of truth; HTML/PDF are derived at export time, not stored
    content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[DocumentStatus] = mapped_column(
        SAEnum(DocumentStatus, name="document_status"),
        default=DocumentStatus.GENERATING,
        nullable=False,
        index=True,
    )

    version: Mapped["DocumentationVersion"] = relationship(back_populates="documents")
    review_result: Mapped[Optional["ReviewResult"]] = relationship(
        back_populates="document", uselist=False, cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<GeneratedDocument id={self.id} type={self.doc_type}>"
