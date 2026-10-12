"""Integration tests for ProjectRepository — real Postgres, real
transactions, real ownership-scoping queries."""

import pytest

from app.core.exceptions import NotFoundError
from app.repositories.project_repository import ProjectRepository
from app.repositories.user_repository import UserRepository
from tests.integration.conftest import requires_docker

pytestmark = [pytest.mark.integration, requires_docker]


@pytest.fixture
async def user(db_session):
    user_repo = UserRepository(db_session)
    created = await user_repo.create(email="owner@example.com", hashed_password="x", full_name="Owner")
    await db_session.commit()
    return created


async def test_create_and_get_owned_project(db_session, user):
    repo = ProjectRepository(db_session)
    created = await repo.create(user.id, "My Project", "A description")
    await db_session.commit()

    fetched = await repo.get_owned(user.id, created.id)
    assert fetched.name == "My Project"
    assert fetched.description == "A description"


async def test_get_owned_raises_not_found_for_wrong_user(db_session, user):
    import uuid
    repo = ProjectRepository(db_session)
    created = await repo.create(user.id, "My Project", None)
    await db_session.commit()

    other_user_id = uuid.uuid4()
    with pytest.raises(NotFoundError):
        await repo.get_owned(other_user_id, created.id)


async def test_get_owned_raises_not_found_for_nonexistent_project(db_session, user):
    import uuid
    repo = ProjectRepository(db_session)
    with pytest.raises(NotFoundError):
        await repo.get_owned(user.id, uuid.uuid4())


async def test_list_for_user_returns_only_that_users_projects(db_session, user):
    repo = ProjectRepository(db_session)
    user_repo = UserRepository(db_session)
    other_user = await user_repo.create(email="other@example.com", hashed_password="x")
    await db_session.commit()

    await repo.create(user.id, "Mine 1", None)
    await repo.create(user.id, "Mine 2", None)
    await repo.create(other_user.id, "Theirs", None)
    await db_session.commit()

    projects, total = await repo.list_for_user(user.id, limit=10, offset=0)
    assert total == 2
    assert {p.name for p in projects} == {"Mine 1", "Mine 2"}


async def test_update_only_changes_provided_fields(db_session, user):
    repo = ProjectRepository(db_session)
    created = await repo.create(user.id, "Original Name", "Original description")
    await db_session.commit()

    updated = await repo.update(user.id, created.id, name="New Name", description=None)
    await db_session.commit()

    assert updated.name == "New Name"
    assert updated.description == "Original description"  # None means "don't change" — see service layer


async def test_delete_removes_project(db_session, user):
    repo = ProjectRepository(db_session)
    created = await repo.create(user.id, "To Delete", None)
    await db_session.commit()

    await repo.delete(user.id, created.id)
    await db_session.commit()

    with pytest.raises(NotFoundError):
        await repo.get_owned(user.id, created.id)
