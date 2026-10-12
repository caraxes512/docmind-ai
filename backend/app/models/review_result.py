"""ReviewResult model — output of the Documentation Reviewer Agent.

Kept separate from GeneratedDocument (1:1) so review runs can be re-executed
independently of regenerating content, and so we can report on documentation
quality trends over time via simple aggregate queries without touching the
(potentially large) content column.
"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.generated_document import GeneratedDocument


class ReviewResult(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "review_results"

    generated_document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("generated_documents.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    quality_score: Mapped[float] = mapped_column(Float, nullable=False)  # 0.0 - 100.0

    # structured list of issues, e.g.:
    # [{"type": "missing_example", "location": "line 42", "severity": "medium"}, ...]
    issues: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    document: Mapped["GeneratedDocument"] = relationship(back_populates="review_result")

    def __repr__(self) -> str:
        return f"<ReviewResult id={self.id} score={self.quality_score}>"
