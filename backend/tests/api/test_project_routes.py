"""API tests for /api/v1/projects — routing, status codes, auth
enforcement, and schema validation, with the service layer mocked out."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.models.project import Project

pytestmark = pytest.mark.api


def _fake_project(**overrides) -> Project:
    now = datetime.now(timezone.utc)
    defaults = dict(
        id=uuid.uuid4(), user_id=uuid.uuid4(), name="Test Project", description="A test project",
        created_at=now, updated_at=now,
    )
    defaults.update(overrides)
    project = Project(**{k: v for k, v in defaults.items() if k not in ("id",)})
    project.id = defaults["id"]
    project.repository_count = 0
    return project


def test_create_project_requires_authentication(client):
    client.app.dependency_overrides.clear()  # remove the auth override for this one test
    response = client.post("/api/v1/projects", json={"name": "X"})
    assert response.status_code == 401


def test_create_project_returns_201_with_valid_payload(client):
    with patch("app.services.project_service.ProjectService.create", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = _fake_project(name="My Project")
        response = client.post("/api/v1/projects", json={"name": "My Project"})
    assert response.status_code == 201
    assert response.json()["name"] == "My Project"


def test_create_project_rejects_empty_name(client):
    response = client.post("/api/v1/projects", json={"name": ""})
    assert response.status_code == 422  # Pydantic min_length=1 validation


def test_create_project_rejects_missing_name(client):
    response = client.post("/api/v1/projects", json={})
    assert response.status_code == 422


def test_list_projects_returns_page_envelope(client):
    with patch("app.services.project_service.ProjectService.list_for_user", new_callable=AsyncMock) as mock_list:
        mock_list.return_value = ([_fake_project(), _fake_project()], 2)
        response = client.get("/api/v1/projects")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert len(body["items"]) == 2
    assert body["limit"] == 20  # default page size


def test_get_project_not_found_returns_404(client):
    from app.core.exceptions import NotFoundError
    with patch("app.services.project_service.ProjectService.get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = NotFoundError("Project not found")
        response = client.get(f"/api/v1/projects/{uuid.uuid4()}")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_get_project_rejects_malformed_uuid(client):
    response = client.get("/api/v1/projects/not-a-uuid")
    assert response.status_code == 422


def test_delete_project_returns_204(client):
    with patch("app.services.project_service.ProjectService.delete", new_callable=AsyncMock):
        response = client.delete(f"/api/v1/projects/{uuid.uuid4()}")
    assert response.status_code == 204
