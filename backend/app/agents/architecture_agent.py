"""Architecture Agent — produces the Architecture doc and a structured
`diagram_request` consumed by the Diagram Agent (same fan-out level, but
Diagram Agent depends on this agent's output for component diagrams, so
the Orchestrator sequences Architecture -> Diagram for that specific
diagram type while other diagram types depend only on Parser Agent's
db_models directly)."""

import json
import logging

from app.agents.state import AgentError, DocumentationGraphState, UsageLogEntry
from app.llm.base import LLMMessage, LLMProvider
from app.models.enums import DocumentType
from app.prompts import ARCHITECTURE_AGENT_PROMPT

logger = logging.getLogger(__name__)


def _build_folder_structure(symbols_by_file: dict[str, list[dict]]) -> str:
    folder_counts: dict[str, int] = {}
    for path in symbols_by_file:
        folder = path.rsplit("/", 1)[0] if "/" in path else "."
        folder_counts[folder] = folder_counts.get(folder, 0) + 1
    return "\n".join(f"{folder} ({count} files)" for folder, count in sorted(folder_counts.items()))


async def run_architecture_agent(state: DocumentationGraphState, llm: LLMProvider) -> dict:
    summary = state["repository_summary"]
    parsed = state["parsed_symbols"]
    folder_structure = _build_folder_structure(parsed["symbols_by_file"])

    # Cross-module import graph is built by a lightweight static analysis pass
    # over parsed import statements — deferred to Step 9 alongside the parser;
    # empty here degrades gracefully per the prompt's failure_recovery.
    import_graph: dict = {}

    developer_prompt = ARCHITECTURE_AGENT_PROMPT.render_developer_prompt(
        repository_summary_json=json.dumps(summary),
        folder_structure=folder_structure,
        import_graph_json=json.dumps(import_graph),
    )

    errors: list[AgentError] = []
    usage_log: list[UsageLogEntry] = []
    for attempt in range(2):
        try:
            response = await llm.generate(
                messages=[
                    LLMMessage(role="system", content=ARCHITECTURE_AGENT_PROMPT.system_prompt),
                    LLMMessage(role="user", content=developer_prompt),
                ],
                temperature=0.2,
                response_format_json=True,
            )
            usage_log.append(
                UsageLogEntry(
                    agent_name=ARCHITECTURE_AGENT_PROMPT.agent_name,
                    model=response.model,
                    input_tokens=response.input_tokens,
                    output_tokens=response.output_tokens,
                )
            )
            parsed_response = json.loads(response.content)
            content = parsed_response["content"]
            diagram_request = parsed_response.get("diagram_request", {"nodes": [], "edges": []})

            update: dict = {
                "generated_documents": {DocumentType.ARCHITECTURE_DOCS.value: content},
                "errors": errors,
                "usage_log": usage_log,
            }
            # Stashing the diagram request under a reserved diagrams key prefix so the
            # Diagram Agent node (run after this one for the component diagram type) can read it.
            update["diagrams"] = {"_architecture_diagram_request": json.dumps(diagram_request)}
            return update
        except (json.JSONDecodeError, KeyError) as exc:
            logger.warning("architecture_agent parse failure (attempt %d): %s", attempt, exc)
            errors.append(
                AgentError(
                    agent_name=ARCHITECTURE_AGENT_PROMPT.agent_name,
                    message=str(exc),
                    retryable=attempt == 0,
                )
            )
            developer_prompt += "\n\nYour previous response was not valid JSON matching the schema."

    return {"errors": errors, "usage_log": usage_log}
