import uuid

from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload

from app.models.enums import SymbolKind
from app.models.parsed_symbol import ParsedSymbol
from app.models.repository_file import RepositoryFile
from app.repositories.base import BaseRepository


class ParsedSymbolRepository(BaseRepository):
    async def replace_for_file(self, repository_file_id: uuid.UUID, symbols: list[dict]) -> None:
        """Deletes existing symbols for this file and inserts the fresh set
        — simpler and safer than diffing old vs. new symbol-by-symbol for
        a file that's being re-parsed because it changed. `symbols` shape
        matches ExtractedSymbols['symbols'] from tree_sitter_parser.py plus
        api_routes/db_models tagged with kind=API_ROUTE/DB_MODEL."""
        await self.db.execute(
            delete(ParsedSymbol).where(ParsedSymbol.repository_file_id == repository_file_id)
        )

        for s in symbols:
            self.db.add(
                ParsedSymbol(
                    repository_file_id=repository_file_id,
                    kind=SymbolKind(s["kind"]),
                    name=s["name"],
                    start_line=s["start_line"],
                    end_line=s["end_line"],
                    signature=s.get("signature"),
                    docstring=s.get("docstring"),
                    http_method=s.get("http_method"),
                    route_path=s.get("route_path"),
                    fields_json=s.get("fields"),
                )
            )
        await self.db.flush()

    async def get_all_for_repository(self, repository_id: uuid.UUID) -> list[ParsedSymbol]:
        """Used by documentation_tasks.py to assemble ParsedSymbols for the
        generation graph — a fast DB read instead of re-parsing."""
        result = await self.db.execute(
            select(ParsedSymbol)
            .join(RepositoryFile, ParsedSymbol.repository_file_id == RepositoryFile.id)
            .options(selectinload(ParsedSymbol.repository_file))
            .where(RepositoryFile.repository_id == repository_id)
        )
        return list(result.scalars().all())
