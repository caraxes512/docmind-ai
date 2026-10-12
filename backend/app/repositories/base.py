"""Base repository — shared session handling. Concrete repositories add
model-specific, ownership-scoped query methods rather than exposing
generic `filter(**kwargs)` methods, so every call site is explicit about
what it's fetching and how it's scoped."""

from sqlalchemy.ext.asyncio import AsyncSession


class BaseRepository:
    def __init__(self, db: AsyncSession):
        self.db = db
