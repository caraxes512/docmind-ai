"""Git integration service — AI-generated commit messages, PR descriptions,
release notes, and changelogs. Each is a single synchronous LLM call (no
multi-agent graph, no persistence beyond usage logging) — these are
stateless text transforms, not artifacts that need versioning or review.
"""

import json
import logging
import uuid

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.llm.base import LLMMessage, LLMProvider
from app.llm.openai_provider import get_llm_provider
from app.prompts import (
    CHANGELOG_PROMPT,
    COMMIT_MESSAGE_PROMPT,
    PR_DESCRIPTION_PROMPT,
    RELEASE_NOTES_PROMPT,
)
from app.prompts.base import PromptSpec
from app.repositories.usage_log_repository import UsageLogRepository

logger = logging.getLogger(__name__)


class GitIntegrationService:
    def __init__(self, db: AsyncSession, llm: LLMProvider | None = None):
        self.db = db
        self.llm = llm or get_llm_provider()
        self.usage_log_repo = UsageLogRepository(db)

    async def _log_usage(
        self, response_model: str, prompt: PromptSpec, input_tokens: int, output_tokens: int
    ) -> None:
        await self.usage_log_repo.bulk_insert(
            None,
            [
                {
                    "agent_name": prompt.agent_name,
                    "model": response_model,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                }
            ],
        )
        await self.db.commit()

    async def generate_commit_message(
        self, user_id: uuid.UUID, diff: str
    ) -> tuple[str, str | None]:
        developer_prompt = COMMIT_MESSAGE_PROMPT.render_developer_prompt(diff=diff)
        try:
            response = await self.llm.generate(
                messages=[
                    LLMMessage(role="system", content=COMMIT_MESSAGE_PROMPT.system_prompt),
                    LLMMessage(role="user", content=developer_prompt),
                ],
                temperature=0.2,
                response_format_json=True,
            )
            await self._log_usage(
                response.model, COMMIT_MESSAGE_PROMPT, response.input_tokens, response.output_tokens
            )
            data = json.loads(response.content)
            subject = data["subject"][:72].rstrip(".")
            return subject, data.get("body")
        except (json.JSONDecodeError, KeyError) as exc:
            logger.warning("commit_message_generator failed, using fallback: %s", exc)
            return "chore: update files", None

    async def generate_pr_description(
        self,
        user_id: uuid.UUID,
        base_branch: str,
        head_branch: str,
        diff: str,
        commit_messages: list[str],
    ) -> tuple[str, str]:
        developer_prompt = PR_DESCRIPTION_PROMPT.render_developer_prompt(
            base_branch=base_branch,
            head_branch=head_branch,
            commit_messages="\n".join(f"- {m}" for m in commit_messages),
            diff=diff,
        )
        try:
            response = await self.llm.generate(
                messages=[
                    LLMMessage(role="system", content=PR_DESCRIPTION_PROMPT.system_prompt),
                    LLMMessage(role="user", content=developer_prompt),
                ],
                temperature=0.3,
                response_format_json=True,
            )
            await self._log_usage(
                response.model, PR_DESCRIPTION_PROMPT, response.input_tokens, response.output_tokens
            )
            data = json.loads(response.content)
            return data["title"], data["description"]
        except (json.JSONDecodeError, KeyError) as exc:
            logger.warning("pr_description_generator failed, using fallback: %s", exc)
            title = commit_messages[0] if commit_messages else "Update"
            description = (
                "\n".join(f"- {m}" for m in commit_messages) or "No commit messages provided."
            )
            return title, description

    async def generate_release_notes(
        self, user_id: uuid.UUID, from_tag: str, to_tag: str, commit_messages: list[str]
    ) -> str:
        developer_prompt = RELEASE_NOTES_PROMPT.render_developer_prompt(
            from_tag=from_tag,
            to_tag=to_tag,
            commit_messages="\n".join(f"- {m}" for m in commit_messages),
        )
        response = await self.llm.generate(
            messages=[
                LLMMessage(role="system", content=RELEASE_NOTES_PROMPT.system_prompt),
                LLMMessage(role="user", content=developer_prompt),
            ],
            temperature=0.3,
        )
        await self._log_usage(
            response.model, RELEASE_NOTES_PROMPT, response.input_tokens, response.output_tokens
        )
        content = response.content.strip()
        if not content:
            # per failure_recovery: flat bullet list fallback for degenerate output
            content = "\n".join(f"- {m}" for m in commit_messages)
        return content

    async def generate_changelog_entry(
        self, user_id: uuid.UUID, version: str, commit_messages: list[str]
    ) -> str:
        developer_prompt = CHANGELOG_PROMPT.render_developer_prompt(
            version=version,
            commit_messages="\n".join(f"- {m}" for m in commit_messages),
        )
        for attempt in range(2):
            response = await self.llm.generate(
                messages=[
                    LLMMessage(role="system", content=CHANGELOG_PROMPT.system_prompt),
                    LLMMessage(role="user", content=developer_prompt),
                ],
                temperature=0.2,
            )
            await self._log_usage(
                response.model, CHANGELOG_PROMPT, response.input_tokens, response.output_tokens
            )
            content = response.content.strip()
            if content.startswith(f"## [{version}]") or content.startswith("## ["):
                return content
            developer_prompt += (
                f"\n\nYour previous response must start with exactly '## [{version}]'."
            )

        # per failure_recovery: deterministic fallback preserving all commit messages
        bullets = "\n".join(f"- {m}" for m in commit_messages)
        return f"## [{version}]\n\n### Changed\n{bullets}"


def get_git_integration_service(db: AsyncSession = Depends(get_db)) -> GitIntegrationService:
    return GitIntegrationService(db)
