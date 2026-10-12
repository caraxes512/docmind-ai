"""Auth service — registration, login, token refresh, and GitHub OAuth
(both as a login method and as account-linking for private repo access)."""

import uuid

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import AlreadyExistsError, UnauthorizedError
from app.core.security import (
    create_access_token,
    create_oauth_state_token,
    create_refresh_token,
    decode_token,
    decrypt_secret,
    encrypt_secret,
    hash_password,
    verify_oauth_state_token,
    verify_password,
)
from app.db.session import get_db
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import TokenPair
from app.services.github_client import GitHubClient, get_github_client


def get_decrypted_github_token(user: User) -> str | None:
    """Standalone (not an AuthService method) so callers that only need
    this — like RepositoryIngestionService.clone_github — don't need to
    construct an unrelated service just to decrypt a field."""
    if not user.github_access_token_encrypted:
        return None
    return decrypt_secret(user.github_access_token_encrypted)


class AuthService:
    def __init__(self, db: AsyncSession, github_client: GitHubClient | None = None):
        self.db = db
        self.user_repo = UserRepository(db)
        self.github_client = github_client or get_github_client()

    def _issue_tokens(self, user: User) -> TokenPair:
        return TokenPair(
            access_token=create_access_token(user.id),
            refresh_token=create_refresh_token(user.id),
        )

    async def register(
        self, email: str, password: str, full_name: str | None
    ) -> tuple[User, TokenPair]:
        existing = await self.user_repo.get_by_email(email)
        if existing is not None:
            raise AlreadyExistsError(f"An account with email {email} already exists")

        user = await self.user_repo.create(
            email=email, hashed_password=hash_password(password), full_name=full_name
        )
        await self.db.commit()
        return user, self._issue_tokens(user)

    async def login(self, email: str, password: str) -> tuple[User, TokenPair]:
        user = await self.user_repo.get_by_email(email)
        if user is None or user.hashed_password is None:
            raise UnauthorizedError("Invalid email or password")
        if not verify_password(password, user.hashed_password):
            raise UnauthorizedError("Invalid email or password")
        if not user.is_active:
            raise UnauthorizedError("Account is inactive")

        return user, self._issue_tokens(user)

    async def refresh(self, refresh_token: str) -> TokenPair:
        user_id = decode_token(refresh_token, expected_type="refresh")
        if user_id is None:
            raise UnauthorizedError("Invalid or expired refresh token")

        user = await self.user_repo.get_by_id(user_id)
        if user is None or not user.is_active:
            raise UnauthorizedError("User not found or inactive")

        return self._issue_tokens(user)

    async def update_profile(self, user_id: uuid.UUID, full_name: str | None) -> User:
        user = await self.user_repo.get_by_id(user_id)
        if user is None:
            raise UnauthorizedError("User not found")
        if full_name is not None:
            user.full_name = full_name
        await self.db.commit()
        return user

    async def get_github_authorize_url(self, current_user_id: uuid.UUID | None) -> str:
        """`current_user_id` is threaded through the CSRF state token itself
        (see create_oauth_state_token) — present when a logged-in user is
        linking GitHub from Settings, absent for "Sign in with GitHub"."""
        settings = get_settings()
        state = create_oauth_state_token(current_user_id)
        return self.github_client.get_authorize_url(state, settings.GITHUB_OAUTH_REDIRECT_URI)

    async def handle_github_callback(self, code: str, state: str) -> tuple[User, TokenPair]:
        settings = get_settings()
        is_valid_state, linked_user_id = verify_oauth_state_token(state)
        if not is_valid_state:
            raise UnauthorizedError(
                "GitHub OAuth state token is invalid or expired — please try connecting again"
            )

        access_token = await self.github_client.exchange_code_for_token(
            code, settings.GITHUB_OAUTH_REDIRECT_URI
        )
        github_user = await self.github_client.get_authenticated_user(access_token)
        encrypted_token = encrypt_secret(access_token)

        if linked_user_id is not None:
            # Linking flow: attach GitHub identity to the already-logged-in user.
            user = await self.user_repo.get_by_id(linked_user_id)
            if user is None:
                raise UnauthorizedError("The account linking this GitHub identity no longer exists")
        else:
            # Login/signup flow: find-or-create by GitHub id.
            user = await self.user_repo.get_by_github_id(github_user.github_id)
            if user is None:
                # A GitHub login might match an existing email/password account
                # by email — link instead of creating a duplicate, if so.
                if github_user.email:
                    user = await self.user_repo.get_by_email(github_user.email)
                if user is None:
                    user = await self.user_repo.create(
                        email=github_user.email or f"{github_user.login}@users.noreply.github.com",
                        hashed_password=None,
                        full_name=github_user.login,
                    )

        user.github_id = github_user.github_id
        user.github_username = github_user.login
        user.github_access_token_encrypted = encrypted_token
        if not user.avatar_url and github_user.avatar_url:
            user.avatar_url = github_user.avatar_url
        await self.db.commit()

        return user, self._issue_tokens(user)

    def get_decrypted_github_token(self, user: User) -> str | None:
        return get_decrypted_github_token(user)


def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    return AuthService(db)
