"""Declarative base and reusable mixins for all ORM models.

Design notes:
- We use UUID primary keys (not auto-increment ints) so IDs are safe to
  expose in URLs/APIs without leaking sequence/count information, and so
  IDs can be generated client-side or in distributed workers without a
  round-trip to the DB.
- `TimestampMixin` centralizes created_at/updated_at so every table gets
  consistent, timezone-aware auditing for free.
- `server_default=func.now()` (not a Python-side default) ensures the
  timestamp is assigned by Postgres at insert time, which stays correct
  even under bulk inserts or when multiple app servers have clock drift.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Shared declarative base for all models."""

    pass


class UUIDPrimaryKeyMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),  # requires pgcrypto extension
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
