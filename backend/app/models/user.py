"""User account model.

Supports both password-based auth and GitHub OAuth. `github_access_token`
is stored encrypted at the application layer (via a SQLAlchemy TypeDecorator
wired to our KMS/Fernet key in app.core.security) — never store OAuth tokens
in plaintext, since they grant repo read access on the user's behalf.
"""

from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.audit_log import AuditLog
    from app.models.chat import Chat
    from app.models.project import Project
    from app.models.task import Task


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    hashed_password: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)

    # GitHub OAuth
    github_id: Mapped[Optional[str]] = mapped_column(
        String(64), unique=True, index=True, nullable=True
    )
    github_username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    github_access_token_encrypted: Mapped[Optional[str]] = mapped_column(
        String(2048), nullable=True
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    projects: Mapped[List["Project"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )
    chats: Mapped[List["Chat"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    tasks: Mapped[List["Task"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    audit_logs: Mapped[List["AuditLog"]] = relationship(back_populates="user")

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email}>"
