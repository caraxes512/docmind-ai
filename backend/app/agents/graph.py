"""Builds the compiled LangGraph StateGraph for documentation generation.

This module IS the "Orchestrator Agent" at the mechanical level — routing
functions here decide which doc-generation agents run based on
RepositorySummary and the caller's requested doc_types, replacing what a
naive design might implement as a wasteful extra LLM call. `app.agents.
orchestrator.Orchestrator` (a thin class) is the public-facing entry point
that callers (DocumentationService) actually use.

Simplification acknowledged: the Diagram Agent only runs when the
Architecture Agent runs, since component-diagram generation depends on the
Architecture Agent's `diagram_request` output. A repository requesting
only an ER diagram without Architecture docs would need this decoupled —
flagged as a Step 7 refinement rather than solved with a more complex
conditional-Send() graph now, which would add complexity ahead of having
a real usage pattern to justify it.
"""

from functools import partial

from langgraph.graph import END, StateGraph

from app.agents.api_doc_agent import run_api_doc_agent
from app.agents.architecture_agent import run_architecture_agent
from app.agents.database_doc_agent import run_database_doc_agent
from app.agents.diagram_agent import run_diagram_agent
from app.agents.function_doc_agent import run_function_doc_agent
from app.agents.parser_agent import run_parser_agent
from app.agents.readme_agent import run_readme_agent
from app.agents.repo_analyzer_agent import run_repository_analyzer_agent
from app.agents.reviewer_agent import run_reviewer_agent
from app.agents.state import DocumentationGraphState
from app.llm.base import LLMProvider
from app.models.enums import DocumentType


def _wanted(doc_types_requested: list[DocumentType] | None, doc_type: DocumentType) -> bool:
    return doc_types_requested is None or doc_type in doc_types_requested


def route_after_parser(state: DocumentationGraphState) -> list[str]:
    """Conditional fan-out — the core of the Orchestrator's routing logic."""
    summary = state["repository_summary"]
    requested = state.get("doc_types_requested")
    branches: list[str] = []

    if _wanted(requested, DocumentType.README):
        branches.append("readme_agent")
    if _wanted(requested, DocumentType.FUNCTION_DOCS):
        branches.append("function_doc_agent")
    if _wanted(requested, DocumentType.ARCHITECTURE_DOCS) or _wanted(
        requested, DocumentType.DIAGRAM
    ):
        branches.append("architecture_agent")
    if summary["has_api_endpoints"] and _wanted(requested, DocumentType.API_DOCS):
        branches.append("api_doc_agent")
    if summary["has_database"] and _wanted(requested, DocumentType.DATABASE_DOCS):
        branches.append("database_doc_agent")

    return branches or ["reviewer_agent"]  # nothing applicable — skip straight to (trivial) review


def build_documentation_graph(
    llm: LLMProvider,
    precomputed_symbols,
    file_tree: list[str],
    manifest_contents: str,
    config_file_contents: str,
):
    """Compiles the graph with runtime dependencies (LLM provider, pre-
    fetched context) closed over each node — keeps node functions
    themselves dependency-free and unit-testable with plain dicts.

    `precomputed_symbols` (a ParsedSymbols dict) replaces what used to be
    `file_paths`/`read_file_content` as of Step 9 — parsing happens once
    during ingestion now, not on every generation run (see
    app/agents/parser_agent.py's docstring for the full rationale).
    """

    graph = StateGraph(DocumentationGraphState)

    graph.add_node(
        "repository_analyzer_agent",
        partial(
            run_repository_analyzer_agent,
            llm=llm,
            file_tree=file_tree,
            manifest_contents=manifest_contents,
            config_file_contents=config_file_contents,
        ),
    )
    graph.add_node(
        "parser_agent",
        partial(run_parser_agent, precomputed_symbols=precomputed_symbols),
    )
    graph.add_node("readme_agent", partial(run_readme_agent, llm=llm))
    graph.add_node("api_doc_agent", partial(run_api_doc_agent, llm=llm))
    graph.add_node("function_doc_agent", partial(run_function_doc_agent, llm=llm))
    graph.add_node("architecture_agent", partial(run_architecture_agent, llm=llm))
    graph.add_node("diagram_agent", partial(run_diagram_agent, llm=llm))
    graph.add_node("database_doc_agent", partial(run_database_doc_agent, llm=llm))
    graph.add_node("reviewer_agent", partial(run_reviewer_agent, llm=llm))

    graph.set_entry_point("repository_analyzer_agent")
    graph.add_edge("repository_analyzer_agent", "parser_agent")

    graph.add_conditional_edges(
        "parser_agent",
        route_after_parser,
        {
            "readme_agent": "readme_agent",
            "api_doc_agent": "api_doc_agent",
            "function_doc_agent": "function_doc_agent",
            "architecture_agent": "architecture_agent",
            "database_doc_agent": "database_doc_agent",
            "reviewer_agent": "reviewer_agent",
        },
    )

    # Independent branches join directly at the reviewer.
    graph.add_edge("readme_agent", "reviewer_agent")
    graph.add_edge("api_doc_agent", "reviewer_agent")
    graph.add_edge("function_doc_agent", "reviewer_agent")
    graph.add_edge("database_doc_agent", "reviewer_agent")

    # Architecture -> Diagram is a sequential dependency, not a parallel branch (see module docstring).
    graph.add_edge("architecture_agent", "diagram_agent")
    graph.add_edge("diagram_agent", "reviewer_agent")

    graph.add_edge("reviewer_agent", END)

    return graph.compile()
