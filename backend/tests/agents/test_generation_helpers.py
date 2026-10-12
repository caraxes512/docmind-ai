"""Tests for app.agents._generation_helpers — shared by README, API Docs,
and Database Docs agents."""

import pytest

from app.agents._generation_helpers import _strip_wrapping_code_fence, generate_markdown_document
from app.prompts import README_AGENT_PROMPT

pytestmark = pytest.mark.agents


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("```markdown\nHello\n```", "Hello"),
        ("```\nHello\n```", "Hello"),
        ("Hello", "Hello"),
        ("```markdown\nHello", "Hello"),  # unterminated fence -- still stripped from the front
    ],
)
def test_strip_wrapping_code_fence(raw, expected):
    assert _strip_wrapping_code_fence(raw) == expected


async def test_succeeds_on_first_attempt_when_validators_pass(fake_llm):
    fake_llm.responses = ["a perfectly fine document body that is long enough"]
    content, errors, usage = await generate_markdown_document(
        prompt=README_AGENT_PROMPT, llm=fake_llm, developer_prompt="write something", validators=[],
    )
    assert content == "a perfectly fine document body that is long enough"
    assert errors == []
    assert len(usage) == 1


async def test_retries_once_on_validation_failure_then_succeeds(fake_llm):
    fake_llm.responses = ["short", "this is now a sufficiently long piece of markdown content"]

    def min_length(content: str) -> list[str]:
        return ["too short"] if len(content) < 30 else []

    content, errors, usage = await generate_markdown_document(
        prompt=README_AGENT_PROMPT, llm=fake_llm, developer_prompt="write something", validators=[min_length],
    )
    assert content is not None
    assert len(errors) == 1  # the failed first attempt
    assert len(usage) == 2  # usage recorded for both attempts


async def test_returns_none_after_two_failed_validation_attempts(fake_llm):
    fake_llm.responses = ["short", "still short"]

    def min_length(content: str) -> list[str]:
        return ["too short"] if len(content) < 30 else []

    content, errors, usage = await generate_markdown_document(
        prompt=README_AGENT_PROMPT, llm=fake_llm, developer_prompt="write something", validators=[min_length],
    )
    assert content is None
    assert len(errors) == 2
