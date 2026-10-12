"""Security utilities: password hashing, JWT issuance/verification,
secret-at-rest encryption, and OAuth CSRF state tokens.

Access tokens are short-lived (default 15 min) and carry only `sub` (user
id) and `exp` — no roles/permissions embedded, since this app has no
role-based access beyond "is this user the owner of this resource", which
is checked against the DB per-request rather than trusted from the token.
Refresh tokens are long-lived and opaque to authorization logic; they only
mint new access tokens via /auth/refresh.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from cryptography.fernet import Fernet, InvalidToken
from jose import JWTError, jwt
import bcrypt

from app.core.config import get_settings

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 30
OAUTH_STATE_EXPIRE_MINUTES = 10  # generous enough for a human to complete the GitHub consent screen


def hash_password(password: str) -> str:
    pwd_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    pwd_bytes = plain_password.encode("utf-8")[:72]
    return bcrypt.checkpw(pwd_bytes, hashed_password.encode("utf-8"))


def _create_token(subject: uuid.UUID, expires_delta: timedelta, token_type: str) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=ALGORITHM)


def create_access_token(user_id: uuid.UUID) -> str:
    return _create_token(user_id, timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES), "access")


def create_refresh_token(user_id: uuid.UUID) -> str:
    return _create_token(user_id, timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS), "refresh")


def decode_token(token: str, expected_type: str = "access") -> Optional[uuid.UUID]:
    """Returns the user id encoded in the token, or None if invalid/expired/
    wrong type. Callers (api/deps.py) turn None into an UnauthorizedError."""
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None

    if payload.get("type") != expected_type:
        return None

    subject = payload.get("sub")
    if subject is None:
        return None

    try:
        return uuid.UUID(subject)
    except ValueError:
        return None


# --- Secret-at-rest encryption (GitHub OAuth tokens) ---


def _fernet() -> Fernet:
    settings = get_settings()
    return Fernet(settings.ENCRYPTION_KEY.encode())


def encrypt_secret(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt_secret(ciphertext: str) -> Optional[str]:
    """Returns None (rather than raising) on a corrupted/wrong-key
    ciphertext — callers treat this the same as "no token stored", which
    is the safe default (falls back to unauthenticated GitHub API access
    rather than crashing the request)."""
    try:
        return _fernet().decrypt(ciphertext.encode()).decode()
    except InvalidToken:
        return None


# --- OAuth CSRF state token ---
#
# Stateless: encodes an optional user_id (present when a logged-in user is
# linking GitHub from Settings; absent for a "Sign in with GitHub" flow) and
# a short expiry, signed with the same JWT secret. No server-side session
# table needed — the token IS the state, verified on the callback leg.


def create_oauth_state_token(user_id: Optional[uuid.UUID]) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "type": "oauth_state",
        "uid": str(user_id) if user_id else None,
        "iat": now,
        "exp": now + timedelta(minutes=OAUTH_STATE_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=ALGORITHM)


def verify_oauth_state_token(token: str) -> tuple[bool, Optional[uuid.UUID]]:
    """Returns (is_valid, linked_user_id_or_None)."""
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return False, None

    if payload.get("type") != "oauth_state":
        return False, None

    uid_raw = payload.get("uid")
    return True, (uuid.UUID(uid_raw) if uid_raw else None)
