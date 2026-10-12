import uuid

from app.models.llm_usage_log import LLMUsageLog
from app.repositories.base import BaseRepository


class UsageLogRepository(BaseRepository):
    async def bulk_insert(self, task_id: uuid.UUID | None, entries: list[dict]) -> None:
        """`entries`: [{"agent_name": ..., "model": ..., "input_tokens": ...,
        "output_tokens": ...}], typically the graph state's accumulated
        `usage_log` list. A single bulk insert rather than one row per
        entry avoids N round-trips for a run that might touch 8+ agents."""
        if not entries:
            return
        self.db.add_all(
            [
                LLMUsageLog(
                    task_id=task_id,
                    agent_name=entry["agent_name"],
                    model=entry["model"],
                    input_tokens=entry["input_tokens"],
                    output_tokens=entry["output_tokens"],
                )
                for entry in entries
            ]
        )
        await self.db.flush()
