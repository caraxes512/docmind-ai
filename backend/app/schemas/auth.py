"""Authentication schemas: password auth + GitHub OAuth + JWT tokens."""

from pydantic import BaseModel, EmailStr, Field

from app.schemas.user import UserRead


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str | None = Field(None, max_length=255)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class RegisterResponse(BaseModel):
    user: UserRead
    tokens: TokenPair


class GitHubOAuthCallbackRequest(BaseModel):
    """Sent by the frontend after GitHub redirects back with a `code`."""

    code: str
    state: str
