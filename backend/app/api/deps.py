"""Shared FastAPI dependencies used across all v1 routers.

NOTE: `get_current_user` queries the User table directly for now. Once the
repository pattern lands in Step 5, this delegates to
`UserRepository.get_by_id` instead — kept here as a direct query today so
the API contract (Step 3) doesn't hard-depend on service-layer code that
doesn't exist yet.
"""

import uuid
from dataclasses import dataclass
from typing import Optional

from fastapi import Depends, Query, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import UnauthorizedError
from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
# auto_error=False: returns None instead of raising when no/invalid header is
# present, used only by the GitHub OAuth login endpoint, which must work for
# both "sign in with GitHub" (no token yet) and "link GitHub" (already logged in).
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


async def get_current_user(
    request: Request,
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    user_id = decode_token(token, expected_type="access")
    if user_id is None:
        raise UnauthorizedError("Invalid or expired access token")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise UnauthorizedError("User not found or inactive")

    # Read by RequestLoggingMiddleware and RateLimitMiddleware so both can
    # key off the authenticated user rather than falling back to client IP.
    request.state.user_id = str(user.id)

    return user


async def get_current_user_id(current_user: User = Depends(get_current_user)) -> uuid.UUID:
    """Lightweight variant for handlers that only need the id (avoids
    implying the full User object is used, keeps intent explicit)."""
    return current_user.id


async def get_current_user_id_optional(
    token: Optional[str] = Depends(oauth2_scheme_optional),
) -> Optional[uuid.UUID]:
    """Returns the user id if a valid access token was provided, else None
    — never raises. Used only by the GitHub OAuth login endpoint, which
    must serve both logged-out ("sign in with GitHub") and logged-in
    ("link GitHub from Settings") callers through the same route.
    """
    if token is None:
        return None
    return decode_token(token, expected_type="access")


@dataclass
class Pagination:
    limit: int
    offset: int


def get_pagination(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> Pagination:
    return Pagination(limit=limit, offset=offset)
