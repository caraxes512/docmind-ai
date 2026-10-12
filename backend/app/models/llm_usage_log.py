"""LLMUsageLog model — one row per LLM call, for cost observability.

Added in Step 7 (not Step 2) deliberately: it wasn't clear until agents
actually started calling an LLM exactly what shape this should take (e.g.
whether to key off Task or Repository). Tying it to Task — nullable, since
not every LLM call happens inside a tracked Task (a future ad-hoc "explain
this snippet" endpoint might not) — was the right call once Step 4-7's
agent/task structure existed to inform it. Retrofitting the schema as
understanding solidifies, rather than guessing upfront in Step 2, is the
better trade here.

No `updated_at` — append-only, like AuditLog.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKeyMixin


class LLMUsageLog(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "llm_usage_logs"

    task_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True, index=True
    )
    agent_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<LLMUsageLog agent={self.agent_name} in={self.input_tokens} out={self.output_tokens}>"
        )
