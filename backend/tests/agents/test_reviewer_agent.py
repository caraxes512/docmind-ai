"""Tests for app.agents.reviewer_agent."""

import json

import pytest

from app.agents.reviewer_agent import MIN_REVIEWABLE_LENGTH, review_single_document

pytestmark = pytest.mark.agents


async def test_score_clamped_to_valid_range_when_llm_returns_out_of_bounds(fake_llm):
    fake_llm.responses = [json.dumps({"score": 150, "issues": []})]
    result, usage, errors = await review_single_document("readme", "x" * 200, {}, fake_llm)
    assert result["score"] == 100
    assert len(fake_llm.calls) == 1


async def test_negative_score_clamped_to_zero(fake_llm):
    fake_llm.responses = [json.dumps({"score": -50, "issues": []})]
    result, _, _ = await review_single_document("readme", "x" * 200, {}, fake_llm)
    assert result["score"] == 0


async def test_short_content_short_circuits_without_llm_call(fake_llm):
    short_content = "x" * (MIN_REVIEWABLE_LENGTH - 1)
    result, usage, errors = await review_single_document("readme", short_content, {}, fake_llm)
    assert len(fake_llm.calls) == 0  # cost optimization: obvious case skips the LLM entirely
    assert result["score"] == 0
    assert result["issues"][0]["type"] == "missing_documentation"


async def test_json_parse_failure_produces_graceful_fallback_result(fake_llm):
    fake_llm.responses = ["not valid json"]
    result, usage, errors = await review_single_document("readme", "x" * 200, {}, fake_llm)
    assert result["score"] == 0
    assert "requires manual review" in result["issues"][0]["description"]
    assert len(errors) == 1


async def test_cross_reference_data_is_passed_through_to_the_prompt(fake_llm):
    """Doesn't assert on prompt string content directly (brittle), just
    confirms the call happened with cross_reference data present — the
    developer_prompt rendering itself is covered by PromptSpec's own
    render_developer_prompt, tested separately."""
    fake_llm.responses = [json.dumps({"score": 80, "issues": []})]
    cross_ref = {"api_routes": [{"method": "GET", "path": "/users"}]}
    await review_single_document("api_docs", "x" * 200, cross_ref, fake_llm)
    sent_content = fake_llm.calls[0][1].content  # [0]=system, [1]=user message
    assert "/users" in sent_content
