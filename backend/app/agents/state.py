"""Shared state schema for the documentation generation graph.

Keys written by exactly one node (repository_summary, parsed_symbols) are
plain fields — LangGraph overwrites them, which is correct since only one
node ever produces them. Keys written by multiple parallel branches
(generated_documents, diagrams, errors) use `Annotated[..., reducer]` so
LangGraph merges concurrent writes instead of one branch clobbering
another — this is the mechanic that makes the fan-out/fan-in pattern safe.
"""

import operator
from typing import Annotated, Optional, TypedDict

from app.models.enums import DocumentType


def _merge_dicts(left: dict, right: dict) -> dict:
    """Reducer for parallel branches that each contribute one or more keys
    to the same dict (e.g. two doc-generation agents each add their own
    DocumentType key to `generated_documents`)."""
    merged = dict(left)
    merged.update(right)
    return merged


class RepositorySummary(TypedDict):
    languages: list[str]
    has_database: bool
    has_api_endpoints: bool
    has_frontend: bool
    entry_points: list[str]
    dependency_manifest_paths: list[str]


class ParsedSymbols(TypedDict):
    """Keyed by file_path -> list of symbol dicts, each
    {"kind": "class"|"function", "name": str, "start_line": int, "end_line": int,
     "docstring": str | None, "signature": str | None}."""

    symbols_by_file: dict[str, list[dict]]
    api_routes: list[
        dict
    ]  # [{"method": "GET", "path": "/users/{id}", "file_path": ..., "line": ...}]
    db_models: list[dict]  # [{"name": "User", "fields": [...], "file_path": ...}]


class AgentError(TypedDict):
    agent_name: str
    message: str
    retryable: bool


class UsageLogEntry(TypedDict):
    """One LLM call's cost-relevant metadata. Accumulated across the graph
    run and persisted by the Celery task at the end (see
    app/tasks/documentation_tasks.py) — agents stay DB-free; only the task
    layer, which already has a session, writes these to LLMUsageLog rows.
    """

    agent_name: str
    model: str
    input_tokens: int
    output_tokens: int


class DocumentationGraphState(TypedDict):
    # --- inputs, set once before graph.ainvoke() ---
    repository_id: str
    commit_hash: str
    task_id: str
    doc_types_requested: Optional[list[DocumentType]]  # None = "all applicable"
    is_incremental: bool
    changed_file_paths: list[str]  # only meaningful when is_incremental=True

    # --- populated by Repository Analyzer Agent ---
    repository_summary: Optional[RepositorySummary]

    # --- populated by Parser Agent ---
    parsed_symbols: Optional[ParsedSymbols]

    # --- populated by the parallel doc-generation agents (merged) ---
    generated_documents: Annotated[
        dict[str, str], _merge_dicts
    ]  # DocumentType.value -> markdown content
    diagrams: Annotated[dict[str, str], _merge_dicts]  # diagram name -> mermaid source

    # --- populated by Documentation Reviewer Agent ---
    review_results: Annotated[
        dict[str, dict], _merge_dicts
    ]  # DocumentType.value -> {score, issues}

    # --- accumulated across any node that fails ---
    errors: Annotated[list[AgentError], operator.add]

    # --- accumulated across any node that calls the LLM ---
    usage_log: Annotated[list[UsageLogEntry], operator.add]
