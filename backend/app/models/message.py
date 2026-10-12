"""Message model — one turn in a Chat.

`citations` stores the RAG source attributions (file paths + line ranges +
similarity score) used to construct the assistant's answer, so the frontend
can render "Sources" alongside each response without re-querying Qdrant.
"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import MessageRole

if TYPE_CHECKING:
    from app.models.chat import Chat


class Message(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "messages"

    chat_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chats.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[MessageRole] = mapped_column(
        SAEnum(MessageRole, name="message_role"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # e.g. [{"file_path": "app/auth.py", "start_line": 10, "end_line": 40, "score": 0.87}]
    citations: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    chat: Mapped["Chat"] = relationship(back_populates="messages")

    def __repr__(self) -> str:
        return f"<Message id={self.id} role={self.role}>"
