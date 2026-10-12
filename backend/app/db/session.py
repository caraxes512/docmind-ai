"""Async database session management.

We use SQLAlchemy's async engine (asyncpg driver) since FastAPI routes are
async — a sync engine here would block the event loop under load. Session
lifecycle is scoped per-request via the `get_db` dependency, which also
guarantees rollback-on-exception so a failed request never leaves a
half-committed transaction.
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

settings = get_settings()

# NOTE: settings.SQLALCHEMY_DATABASE_URI currently returns a psycopg2 (sync)
# DSN for Alembic's benefit (Step 2). The async engine below swaps the
# driver to asyncpg — both point at the same database.
_ASYNC_DATABASE_URL = settings.SQLALCHEMY_DATABASE_URI.replace(
    "postgresql+psycopg2", "postgresql+asyncpg"
)

engine = create_async_engine(_ASYNC_DATABASE_URL, pool_pre_ping=True, pool_size=10, max_overflow=20)

AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
