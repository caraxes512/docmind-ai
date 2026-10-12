"""API tests for /api/v1/auth."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.core.exceptions import AlreadyExistsError, UnauthorizedError
from app.models.user import User
from app.schemas.auth import TokenPair

pytestmark = pytest.mark.api


def _tokens() -> TokenPair:
    return TokenPair(access_token="fake-access", refresh_token="fake-refresh")


def test_register_returns_201_with_user_and_tokens(client, mock_user):
    with patch("app.services.auth_service.AuthService.register", new_callable=AsyncMock) as mock_register:
        mock_register.return_value = (mock_user, _tokens())
        response = client.post(
            "/api/v1/auth/register",
            json={"email": "new@example.com", "password": "supersecure123"},
        )
    assert response.status_code == 201
    body = response.json()
    assert body["tokens"]["access_token"] == "fake-access"
    assert body["user"]["email"] == mock_user.email


def test_register_rejects_short_password(client):
    response = client.post(
        "/api/v1/auth/register", json={"email": "new@example.com", "password": "short"}
    )
    assert response.status_code == 422  # min_length=8


def test_register_duplicate_email_returns_409(client):
    with patch("app.services.auth_service.AuthService.register", new_callable=AsyncMock) as mock_register:
        mock_register.side_effect = AlreadyExistsError("An account with this email already exists")
        response = client.post(
            "/api/v1/auth/register", json={"email": "exists@example.com", "password": "supersecure123"}
        )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "already_exists"


def test_login_invalid_credentials_returns_401(client):
    with patch("app.services.auth_service.AuthService.login", new_callable=AsyncMock) as mock_login:
        mock_login.side_effect = UnauthorizedError("Invalid email or password")
        response = client.post(
            "/api/v1/auth/login", json={"email": "wrong@example.com", "password": "wrongpassword"}
        )
    assert response.status_code == 401


def test_get_me_returns_current_user(client, mock_user):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 200
    assert response.json()["email"] == mock_user.email


def test_get_me_requires_authentication(client):
    client.app.dependency_overrides.clear()
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_update_me_patches_full_name(client, mock_user):
    updated_user = mock_user
    updated_user.full_name = "New Name"
    with patch("app.services.auth_service.AuthService.update_profile", new_callable=AsyncMock) as mock_update:
        mock_update.return_value = updated_user
        response = client.patch("/api/v1/auth/me", json={"full_name": "New Name"})
    assert response.status_code == 200
    assert response.json()["full_name"] == "New Name"
