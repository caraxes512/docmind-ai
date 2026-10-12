"""Tests for app.agents.repo_analyzer_agent, using FakeLLMProvider.

Behavior verified via manual harness during Step 7 development (retry-
then-fallback call counts, usage tracking); formalized here.
"""

import json

import pytest

from app.agents.repo_analyzer_agent import _heuristic_fallback, _validate_summary, run_repository_analyzer_agent

pytestmark = pytest.mark.agents


async def test_successful_analysis_returns_repository_summary(fake_llm):
    fake_llm.responses = [json.dumps({
        "languages": ["python"], "has_database": True, "has_api_endpoints": True,
        "has_frontend": False, "entry_points": ["app/main.py"],
        "dependency_manifest_paths": ["requirements.txt"],
    })]
    result = await run_repository_analyzer_agent(
        {"doc_types_requested": None}, fake_llm,
        file_tree=["app/main.py", "requirements.txt"],
        manifest_contents="sqlalchemy", config_file_contents="",
    )
    assert result["repository_summary"]["has_database"] is True
    assert len(fake_llm.calls) == 1


async def test_records_usage_on_success(fake_llm):
    fake_llm.responses = [json.dumps({
        "languages": ["python"], "has_database": False, "has_api_endpoints": False,
        "has_frontend": False, "entry_points": [], "dependency_manifest_paths": [],
    })]
    result = await run_repository_analyzer_agent(
        {"doc_types_requested": None}, fake_llm, file_tree=[], manifest_contents="", config_file_contents="",
    )
    assert len(result["usage_log"]) == 1
    assert result["usage_log"][0]["input_tokens"] == 42


async def test_retries_once_then_falls_back_on_repeated_invalid_json(fake_llm):
    fake_llm.responses = ["not json", "still not json"]
    result = await run_repository_analyzer_agent(
        {"doc_types_requested": None}, fake_llm,
        file_tree=["app/main.py"], manifest_contents="", config_file_contents="",
    )
    assert len(fake_llm.calls) == 2  # exactly one retry, then fallback -- no third attempt
    assert "repository_summary" in result
    assert len(result["errors"]) == 1
    assert len(result["usage_log"]) == 2  # usage recorded even for failed attempts


def test_heuristic_fallback_detects_python_and_database():
    fallback = _heuristic_fallback(["app/main.py", "requirements.txt"], "sqlalchemy==2.0\nfastapi")
    assert fallback["has_database"] is True
    assert fallback["languages"] == ["python"]


def test_heuristic_fallback_conservative_without_db_dependency():
    fallback = _heuristic_fallback(["app/main.py"], "flask")
    assert fallback["has_database"] is False


def test_validate_summary_strips_entry_points_not_in_file_tree():
    raw = {"languages": ["python"], "entry_points": ["main.py", "ghost.py"]}
    summary = _validate_summary(raw, file_tree=["main.py"])
    assert summary["entry_points"] == ["main.py"]
