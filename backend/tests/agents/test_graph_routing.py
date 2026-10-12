"""Tests for app.agents.graph.route_after_parser — the conditional fan-out
logic that IS the Orchestrator's decision-making at the mechanical level
(see graph.py's module docstring)."""

import pytest

from app.agents.graph import route_after_parser
from app.models.enums import DocumentType

pytestmark = pytest.mark.agents


def _state(summary_overrides=None, doc_types_requested=None):
    summary = {
        "languages": ["python"], "has_database": False, "has_api_endpoints": False,
        "has_frontend": False, "entry_points": [], "dependency_manifest_paths": [],
    }
    summary.update(summary_overrides or {})
    return {"repository_summary": summary, "doc_types_requested": doc_types_requested}


def test_no_api_no_database_skips_those_agents():
    branches = route_after_parser(_state())
    assert "api_doc_agent" not in branches
    assert "database_doc_agent" not in branches
    assert "readme_agent" in branches
    assert "function_doc_agent" in branches
    assert "architecture_agent" in branches


def test_has_api_endpoints_includes_api_doc_agent():
    branches = route_after_parser(_state({"has_api_endpoints": True}))
    assert "api_doc_agent" in branches


def test_has_database_includes_database_doc_agent():
    branches = route_after_parser(_state({"has_database": True}))
    assert "database_doc_agent" in branches


def test_explicit_doc_types_requested_narrows_branches():
    branches = route_after_parser(_state(
        {"has_api_endpoints": True, "has_database": True},
        doc_types_requested=[DocumentType.README],
    ))
    assert branches == ["readme_agent"]


def test_diagram_only_request_still_routes_through_architecture_agent():
    """Diagram generation depends on Architecture Agent's output (see
    graph.py's module docstring on the Diagram/Architecture coupling)."""
    branches = route_after_parser(_state(doc_types_requested=[DocumentType.DIAGRAM]))
    assert branches == ["architecture_agent"]


def test_empty_result_falls_back_to_reviewer_agent_directly():
    """If nothing applies (e.g. a doc type requested that isn't in the
    routable set), route straight to review rather than an empty no-op branch."""
    branches = route_after_parser(_state(doc_types_requested=[DocumentType.FAQ]))
    assert branches == ["reviewer_agent"]
