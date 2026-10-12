"""RepositoryFile model — one row per source file discovered in a repository.

`content_hash` (SHA-256 of file bytes) is the single source of truth for
change detection: on re-sync, we diff hashes against the prior version
rather than relying on mtimes, which are unreliable across clone/zip
extraction and can produce false positives/negatives.

A composite unique constraint on (repository_id, file_path) ensures we
never duplicate a file row across re-scans — re-scans upsert in place and
bump content_hash / index_status instead.
"""

import uuid
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import BigInteger, Enum as SAEnum, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import FileIndexStatus, ProgrammingLanguage

if TYPE_CHECKING:
    from app.models.embedding import Embedding
    from app.models.parsed_symbol import ParsedSymbol
    from app.models.repository import Repository


class RepositoryFile(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "repository_files"
    __table_args__ = (
        UniqueConstraint("repository_id", "file_path", name="uq_repository_file_path"),
    )

    repository_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    file_path: Mapped[str] = mapped_column(String(2048), nullable=False)
    language: Mapped[ProgrammingLanguage] = mapped_column(
        SAEnum(ProgrammingLanguage, name="programming_language"),
        default=ProgrammingLanguage.UNKNOWN,
        nullable=False,
    )
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

    # commit hash as-of the last time this file was successfully embedded
    last_indexed_commit_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    index_status: Mapped[FileIndexStatus] = mapped_column(
        SAEnum(FileIndexStatus, name="file_index_status"),
        default=FileIndexStatus.PENDING,
        nullable=False,
        index=True,
    )

    repository: Mapped["Repository"] = relationship(back_populates="files")
    embeddings: Mapped[List["Embedding"]] = relationship(
        back_populates="repository_file", cascade="all, delete-orphan"
    )
    parsed_symbols: Mapped[List["ParsedSymbol"]] = relationship(
        back_populates="repository_file", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<RepositoryFile id={self.id} path={self.file_path}>"
