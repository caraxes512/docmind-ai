"""ParsedSymbol model — added in Step 9.

This is the persistence fix for two things flagged as gaps in earlier
steps: (1) Step 4's parser_agent would have re-parsed the entire repo on
every documentation generation run, wasteful and contradicting the
"Incremental Documentation" requirement; (2) Step 7's Reviewer Agent had
no persisted api_routes/db_models to cross-reference against. Parsing now
happens once per file during ingestion (or re-ingestion of changed files),
written here, and read back by the generation graph — never re-derived.

One row per symbol (class/function/method/api_route/db_model). Kind-
specific fields (http_method, route_path for API routes; fields_json for
DB models) are nullable columns rather than separate subtype tables —
five kinds with mostly-overlapping shape didn't justify table-per-subtype
normalization at this scale.
"""

import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import SymbolKind

if TYPE_CHECKING:
    from app.models.repository_file import RepositoryFile


class ParsedSymbol(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "parsed_symbols"

    repository_file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repository_files.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    kind: Mapped[SymbolKind] = mapped_column(
        SAEnum(SymbolKind, name="symbol_kind"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    start_line: Mapped[int] = mapped_column(Integer, nullable=False)
    end_line: Mapped[int] = mapped_column(Integer, nullable=False)
    signature: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    docstring: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # kind == API_ROUTE only
    http_method: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    route_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # kind == DB_MODEL only: [{"name": "email", "type": "String", "constraints": [...]}, ...]
    fields_json: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)

    repository_file: Mapped["RepositoryFile"] = relationship(back_populates="parsed_symbols")

    def __repr__(self) -> str:
        return f"<ParsedSymbol kind={self.kind} name={self.name}>"
