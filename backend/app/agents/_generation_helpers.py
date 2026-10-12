"""Shared helper for agents that produce a single Markdown document via one
LLM call with a validate-and-retry-once policy. Agents whose output needs
JSON parsing (Diagram, Reviewer) or batching (Function Docs) don't use this
directly but follow the same retry shape inline.
"""

import logging
from typing import Callable

from app.agents.state import AgentError, UsageLogEntry
from app.llm.base import LLMMessage, LLMProvider
from app.prompts.base import PromptSpec

logger = logging.getLogger(__name__)


def _strip_wrapping_code_fence(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines[-1].strip() == "```":
            lines = lines[1:-1]
        else:
            lines = lines[1:]
        return "\n".join(lines).strip()
    return stripped


async def generate_markdown_document(
    prompt: PromptSpec,
    llm: LLMProvider,
    developer_prompt: str,
    validators: list[Callable[[str], list[str]]],
) -> tuple[str | None, list[AgentError], list[UsageLogEntry]]:
    """Runs the standard generate -> strip fences -> validate -> retry-once
    flow. `validators` are functions taking the candidate content and
    returning a list of violation messages (empty list = passes).

    Returns (content_or_none, errors, usage_log). content is None only if
    both attempts fail validation, in which case errors describes why.
    Usage is recorded for every attempt, including ones that fail semantic
    validation — a validation failure still cost real tokens and should
    show up in cost reporting, not just successful generations.
    """
    errors: list[AgentError] = []
    usage_log: list[UsageLogEntry] = []
    current_prompt = developer_prompt

    for attempt in range(2):
        response = await llm.generate(
            messages=[
                LLMMessage(role="system", content=prompt.system_prompt),
                LLMMessage(role="user", content=current_prompt),
            ],
            temperature=0.2,
        )
        usage_log.append(
            UsageLogEntry(
                agent_name=prompt.agent_name,
                model=response.model,
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
            )
        )
        content = _strip_wrapping_code_fence(response.content)
        violations = [v for validator in validators for v in validator(content)]

        if not violations:
            return content, errors, usage_log

        logger.warning(
            "%s validation failed (attempt %d): %s", prompt.agent_name, attempt, violations
        )
        errors.append(
            AgentError(
                agent_name=prompt.agent_name, message="; ".join(violations), retryable=attempt == 0
            )
        )
        current_prompt = (
            developer_prompt + "\n\nYour previous response violated: " + "; ".join(violations)
        )

    return None, errors, usage_log
