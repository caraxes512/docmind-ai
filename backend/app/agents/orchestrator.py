"""Orchestrator -- the class other layers (DocumentationService, Celery
tasks) actually call. Wraps `build_documentation_graph` and translates
between the service layer's plain arguments and the graph's typed state,
so nothing outside `app.agents` needs to know LangGraph is involved at all.
"""

from app.agents.graph import build_documentation_graph
from app.agents.state import DocumentationGraphState, ParsedSymbols
from app.llm.base import LLMProvider
from app.models.enums import DocumentType


class Orchestrator:
    def __init__(self, llm: LLMProvider):
        self.llm = llm

    async def generate_documentation(
        self,
        *,
        repository_id: str,
        commit_hash: str,
        task_id: str,
        doc_types_requested: list[DocumentType] | None,
        precomputed_symbols: ParsedSymbols,
        file_tree: list[str],
        manifest_contents: str,
        config_file_contents: str,
        is_incremental: bool = False,
        changed_file_paths: list[str] | None = None,
    ) -> DocumentationGraphState:
        """Runs the full generation graph and returns the final state,
        which the caller (DocumentationService) persists as a new
        DocumentationVersion + GeneratedDocument rows + ReviewResult rows.

        `precomputed_symbols` comes from Postgres (ParsedSymbol rows written
        during ingestion — see Step 9), not from re-parsing here. For
        incremental regeneration, the caller is responsible for
        pre-filtering `doc_types_requested` to the affected subset before
        calling this — the graph itself always runs a full pass over
        whatever it's given; "incremental" is a caller-side input-narrowing
        decision, not graph-internal branching.
        """
        compiled_graph = build_documentation_graph(
            llm=self.llm,
            precomputed_symbols=precomputed_symbols,
            file_tree=file_tree,
            manifest_contents=manifest_contents,
            config_file_contents=config_file_contents,
        )

        initial_state: DocumentationGraphState = {
            "repository_id": repository_id,
            "commit_hash": commit_hash,
            "task_id": task_id,
            "doc_types_requested": doc_types_requested,
            "is_incremental": is_incremental,
            "changed_file_paths": changed_file_paths or [],
            "repository_summary": None,
            "parsed_symbols": None,
            "generated_documents": {},
            "diagrams": {},
            "review_results": {},
            "errors": [],
            "usage_log": [],
        }

        final_state = await compiled_graph.ainvoke(initial_state)
        return final_state
