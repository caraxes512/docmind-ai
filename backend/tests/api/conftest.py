"""API-tier fixtures.

These tests exercise routing, status codes, request/response schema
validation, and auth enforcement — NOT real business logic (that's the
service layer's job, covered by its own unit tests, and real DB behavior,
covered by tests/integration/). Service dependencies are overridden with
Mocks via FastAPI's dependency_overrides, which is the standard,
recommended way to unit-test route wiring in isolation from what the
service methods actually do.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.core.security import create_access_token
from app.main import app
from app.models.user import User


@pytest.fixture
def mock_user() -> User:
    now = datetime.now(timezone.utc)
    user = User(
        id=uuid.uuid4(), email="test@example.com", full_name="Test User",
        is_active=True, hashed_password="irrelevant-for-api-tests",
        created_at=now, updated_at=now,
    )
    return user


@pytest.fixture
def client(mock_user) -> TestClient:
    app.dependency_overrides[get_current_user] = lambda: mock_user
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers(mock_user) -> dict:
    token = create_access_token(mock_user.id)
    return {"Authorization": f"Bearer {token}"}
