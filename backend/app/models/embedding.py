"""Embedding model — metadata pointer to a chunk's vector in Qdrant.

We deliberately do NOT store the raw vector in Postgres. `vector_id` is the
Qdrant point ID (a UUID we control), and `metadata_json` mirrors the payload
we attach in Qdrant (file_path, language, symbol names, start/end line) so
we can reconstruct citations without a round-trip to the vector store when
just listing/auditing embeddings.

Rationale for splitting storage this way: Postgres remains the relational
source of truth (easy joins, transactions, backups); Qdrant is optimized
for ANN search and payload filtering at scale. Keeping both in sync is
handled by the RAG indexing service (upsert to Qdrant, then write this row,
in that order, so a crash never leaves an orphaned Postgres row pointing at
a missing vector).
"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.repository_file import RepositoryFile


class Embedding(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "embeddings"

    repository_file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repository_files.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)

    # Qdrant point id (UUID string) — the actual vector lives in Qdrant
    vector_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)

    # mirrors the Qdrant payload for fast local inspection / citation building
    metadata_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    repository_file: Mapped["RepositoryFile"] = relationship(back_populates="embeddings")

    def __repr__(self) -> str:
        return f"<Embedding id={self.id} chunk_index={self.chunk_index}>"
