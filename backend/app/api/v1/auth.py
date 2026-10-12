"""Authentication endpoints: register, login, refresh, current user, GitHub OAuth."""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, status
from fastapi.responses import RedirectResponse

from app.api.deps import get_current_user, get_current_user_id_optional
from app.models.user import User
from app.schemas.auth import (
    GitHubOAuthCallbackRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    TokenPair,
)
from app.schemas.user import UserRead, UserUpdate
from app.services.auth_service import AuthService, get_auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    service: AuthService = Depends(get_auth_service),
) -> RegisterResponse:
    user, tokens = await service.register(body.email, body.password, body.full_name)
    return RegisterResponse(user=UserRead.model_validate(user), tokens=tokens)


@router.post("/login", response_model=TokenPair)
async def login(
    body: LoginRequest,
    service: AuthService = Depends(get_auth_service),
) -> TokenPair:
    _, tokens = await service.login(body.email, body.password)
    return tokens


@router.post("/refresh", response_model=TokenPair)
async def refresh(
    body: RefreshRequest,
    service: AuthService = Depends(get_auth_service),
) -> TokenPair:
    return await service.refresh(body.refresh_token)


@router.get("/me", response_model=UserRead)
async def get_me(current_user: User = Depends(get_current_user)) -> UserRead:
    return UserRead.model_validate(current_user)


@router.patch("/me", response_model=UserRead)
async def update_me(
    body: UserUpdate,
    current_user: User = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
) -> UserRead:
    updated_user = await service.update_profile(current_user.id, body.full_name)
    return UserRead.model_validate(updated_user)


@router.get("/github/login")
async def github_login(
    current_user_id: Optional[uuid.UUID] = Depends(get_current_user_id_optional),
    service: AuthService = Depends(get_auth_service),
) -> RedirectResponse:
    """Redirects the browser to GitHub's OAuth consent screen. Used by the
    logged-out 'Sign in with GitHub' button, which needs no Authorization
    header (a plain link navigation is enough)."""
    url = await service.get_github_authorize_url(current_user_id)
    return RedirectResponse(url)


@router.get("/github/authorize-url")
async def github_authorize_url(
    current_user: User = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
) -> dict:
    """JSON variant for the logged-in 'Connect GitHub' flow (Settings page).
    A full-page browser navigation can't carry an Authorization header, so
    the frontend calls this as a normal authenticated fetch() first to get
    a URL with the current user's id already embedded in its state token,
    THEN navigates the browser to that URL — the actual OAuth redirect
    itself never needs to carry auth."""
    url = await service.get_github_authorize_url(current_user.id)
    return {"url": url}


@router.post("/github/callback", response_model=RegisterResponse)
async def github_callback(
    body: GitHubOAuthCallbackRequest,
    service: AuthService = Depends(get_auth_service),
) -> RegisterResponse:
    user, tokens = await service.handle_github_callback(body.code, body.state)
    return RegisterResponse(user=UserRead.model_validate(user), tokens=tokens)
