import uuid

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.models.enums import FileIndexStatus
from app.models.repository_file import RepositoryFile
from app.repositories.base import BaseRepository


class RepositoryFileRepository(BaseRepository):
    async def bulk_upsert_scan_results(self, repository_id: uuid.UUID, files: list[dict]) -> None:
        """`files`: [{"file_path": ..., "language": ..., "content_hash": ...,
        "size_bytes": ...}]. Files whose content_hash changed vs. the
        existing row are marked STALE (change detection for incremental
        regeneration); brand-new files are inserted as PENDING.

        Uses Postgres's INSERT ... ON CONFLICT (upsert) on the
        (repository_id, file_path) unique constraint from Step 2, rather
        than a select-then-branch loop — avoids N+1 queries for large repos.
        """
        if not files:
            return

        # First, snapshot existing hashes so we know which rows are "changed" vs "new" post-upsert.
        existing_result = await self.db.execute(
            select(RepositoryFile.file_path, RepositoryFile.content_hash).where(
                RepositoryFile.repository_id == repository_id
            )
        )
        existing_hashes = {path: content_hash for path, content_hash in existing_result.all()}

        rows = []
        for f in files:
            previous_hash = existing_hashes.get(f["file_path"])
            is_new = previous_hash is None
            is_changed = previous_hash is not None and previous_hash != f["content_hash"]
            status = (
                FileIndexStatus.PENDING
                if is_new
                else FileIndexStatus.STALE
                if is_changed
                else FileIndexStatus.INDEXED  # unchanged — leave as previously indexed
            )
            rows.append(
                {
                    "repository_id": repository_id,
                    "file_path": f["file_path"],
                    "language": f["language"],
                    "content_hash": f["content_hash"],
                    "size_bytes": f["size_bytes"],
                    "index_status": status,
                }
            )

        stmt = pg_insert(RepositoryFile).values(rows)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_repository_file_path",
            set_={
                "content_hash": stmt.excluded.content_hash,
                "size_bytes": stmt.excluded.size_bytes,
                "language": stmt.excluded.language,
                "index_status": stmt.excluded.index_status,
            },
        )
        await self.db.execute(stmt)
        await self.db.flush()

    async def list_stale_or_pending(self, repository_id: uuid.UUID) -> list[RepositoryFile]:
        """Used by the incremental regeneration path (Step 7/9) to determine
        which files actually need re-parsing/re-embedding."""
        result = await self.db.execute(
            select(RepositoryFile).where(
                RepositoryFile.repository_id == repository_id,
                RepositoryFile.index_status.in_([FileIndexStatus.PENDING, FileIndexStatus.STALE]),
            )
        )
        return list(result.scalars().all())

    async def list_all_for_repository(self, repository_id: uuid.UUID) -> list[RepositoryFile]:
        """Unpaginated — used internally by the generation pipeline to build
        the full file tree for the Repository Analyzer Agent, not exposed
        via the paginated /repositories/{id}/files API endpoint."""
        result = await self.db.execute(
            select(RepositoryFile).where(RepositoryFile.repository_id == repository_id)
        )
        return list(result.scalars().all())
