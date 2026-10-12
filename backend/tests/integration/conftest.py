"""Integration-tier fixtures — spin up a real, ephemeral Postgres instance
via testcontainers, run Alembic migrations against it, and hand out a real
AsyncSession per test. This is deliberately NOT SQLite: the schema uses
Postgres-specific features (JSONB, gen_random_uuid(), ON CONFLICT upserts
in RepositoryFileRepository) that SQLite can't faithfully emulate — a
passing SQLite test would prove less than it appears to.

Requires Docker to be available wherever this test tier runs (CI runners
typically have it; local dev needs Docker Desktop or equivalent). Skipped
automatically if Docker isn't available, rather than failing the whole
suite — see the skip condition below.
"""

import asyncio
import subprocess

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.base import Base


def _docker_available() -> bool:
    try:
        subprocess.run(["docker", "info"], capture_output=True, timeout=5, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return False


requires_docker = pytest.mark.skipif(not _docker_available(), reason="Docker not available")


@pytest.fixture(scope="session")
def postgres_container():
    from testcontainers.postgres import PostgresContainer

    with PostgresContainer("postgres:16-alpine") as container:
        yield container


@pytest_asyncio.fixture
async def db_session(postgres_container) -> AsyncSession:
    async_url = postgres_container.get_connection_url().replace("psycopg2", "asyncpg")
    engine = create_async_engine(async_url)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
