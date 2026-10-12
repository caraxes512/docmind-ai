"""Integration test for RepositoryFileRepository.bulk_upsert_scan_results
-- the PENDING/STALE/INDEXED classification is the mechanism the entire
"Incremental Documentation" requirement depends on, and it uses a real
Postgres ON CONFLICT upsert (not portable to SQLite), so this genuinely
needs the real-DB tier rather than a unit test with a fake session.
"""

import pytest

from app.models.enums import FileIndexStatus, ProgrammingLanguage, RepositorySourceType
from app.repositories.project_repository import ProjectRepository
from app.repositories.repository_file_repository import RepositoryFileRepository
from app.repositories.repository_repository import RepositoryRepository
from app.repositories.user_repository import UserRepository
from tests.integration.conftest import requires_docker

pytestmark = [pytest.mark.integration, requires_docker]


@pytest.fixture
async def repository(db_session):
    user_repo = UserRepository(db_session)
    project_repo = ProjectRepository(db_session)
    repo_repo = RepositoryRepository(db_session)

    user = await user_repo.create(email="owner@example.com", hashed_password="x")
    project = await project_repo.create(user.id, "Test Project", None)
    repository = await repo_repo.create(
        project.id, RepositorySourceType.ZIP_UPLOAD, storage_path="repositories/test"
    )
    await db_session.commit()
    return repository


async def test_new_files_marked_pending(db_session, repository):
    file_repo = RepositoryFileRepository(db_session)
    await file_repo.bulk_upsert_scan_results(repository.id, [
        {"file_path": "main.py", "language": ProgrammingLanguage.PYTHON, "content_hash": "abc123", "size_bytes": 100},
    ])
    await db_session.commit()

    stale_or_pending = await file_repo.list_stale_or_pending(repository.id)
    assert len(stale_or_pending) == 1
    assert stale_or_pending[0].index_status == FileIndexStatus.PENDING


async def test_unchanged_file_on_rescan_stays_indexed_not_reflagged(db_session, repository):
    file_repo = RepositoryFileRepository(db_session)

    # First scan
    await file_repo.bulk_upsert_scan_results(repository.id, [
        {"file_path": "main.py", "language": ProgrammingLanguage.PYTHON, "content_hash": "abc123", "size_bytes": 100},
    ])
    await db_session.commit()

    # Simulate: file was already indexed (as the ingestion pipeline would do after embedding)
    files = await file_repo.list_all_for_repository(repository.id)
    files[0].index_status = FileIndexStatus.INDEXED
    await db_session.commit()

    # Re-scan with IDENTICAL content hash — should stay INDEXED, not reset to PENDING/STALE
    await file_repo.bulk_upsert_scan_results(repository.id, [
        {"file_path": "main.py", "language": ProgrammingLanguage.PYTHON, "content_hash": "abc123", "size_bytes": 100},
    ])
    await db_session.commit()

    stale_or_pending = await file_repo.list_stale_or_pending(repository.id)
    assert stale_or_pending == []  # nothing needs re-indexing


async def test_changed_file_content_hash_marked_stale(db_session, repository):
    file_repo = RepositoryFileRepository(db_session)

    await file_repo.bulk_upsert_scan_results(repository.id, [
        {"file_path": "main.py", "language": ProgrammingLanguage.PYTHON, "content_hash": "abc123", "size_bytes": 100},
    ])
    await db_session.commit()

    files = await file_repo.list_all_for_repository(repository.id)
    files[0].index_status = FileIndexStatus.INDEXED
    await db_session.commit()

    # Re-scan with a DIFFERENT content hash — this file changed since last index
    await file_repo.bulk_upsert_scan_results(repository.id, [
        {"file_path": "main.py", "language": ProgrammingLanguage.PYTHON, "content_hash": "def456", "size_bytes": 150},
    ])
    await db_session.commit()

    stale_or_pending = await file_repo.list_stale_or_pending(repository.id)
    assert len(stale_or_pending) == 1
    assert stale_or_pending[0].index_status == FileIndexStatus.STALE
    assert stale_or_pending[0].content_hash == "def456"


async def test_unrelated_files_unaffected_by_one_files_change(db_session, repository):
    """The core incremental-regeneration promise: changing one file must
    not mark every other file as needing re-work."""
    file_repo = RepositoryFileRepository(db_session)

    await file_repo.bulk_upsert_scan_results(repository.id, [
        {"file_path": "main.py", "language": ProgrammingLanguage.PYTHON, "content_hash": "hash_a", "size_bytes": 100},
        {"file_path": "utils.py", "language": ProgrammingLanguage.PYTHON, "content_hash": "hash_b", "size_bytes": 50},
    ])
    await db_session.commit()

    files = await file_repo.list_all_for_repository(repository.id)
    for f in files:
        f.index_status = FileIndexStatus.INDEXED
    await db_session.commit()

    # Only main.py changes
    await file_repo.bulk_upsert_scan_results(repository.id, [
        {"file_path": "main.py", "language": ProgrammingLanguage.PYTHON, "content_hash": "hash_a_changed", "size_bytes": 120},
        {"file_path": "utils.py", "language": ProgrammingLanguage.PYTHON, "content_hash": "hash_b", "size_bytes": 50},
    ])
    await db_session.commit()

    stale_or_pending = await file_repo.list_stale_or_pending(repository.id)
    assert len(stale_or_pending) == 1
    assert stale_or_pending[0].file_path == "main.py"
