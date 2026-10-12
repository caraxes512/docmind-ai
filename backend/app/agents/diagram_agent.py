"""Diagram Generator Agent — renders Mermaid diagrams from structured
relationship data. Produces multiple diagrams (ER, component, and
optionally class/sequence) as separate keys in `diagrams`, merged via the
state's dict reducer alongside the Architecture Agent's own diagrams write."""

import json
import logging
import re

from app.agents.state import AgentError, DocumentationGraphState, UsageLogEntry
from app.agents._generation_helpers import _strip_wrapping_code_fence
from app.llm.base import LLMMessage, LLMProvider
from app.prompts import DIAGRAM_AGENT_PROMPT

logger = logging.getLogger(__name__)

_VALID_DIAGRAM_HEADERS = re.compile(
    r"^\s*(flowchart|graph|classDiagram|erDiagram|sequenceDiagram)\b", re.IGNORECASE
)


def _validate_mermaid(content: str) -> list[str]:
    first_line = content.strip().splitlines()[0] if content.strip() else ""
    if not _VALID_DIAGRAM_HEADERS.match(first_line):
        return [f"first line '{first_line}' is not a recognized Mermaid diagram type declaration"]
    return []


async def _generate_one_diagram(
    diagram_type: str, structured_input: dict, llm: LLMProvider
) -> tuple[str | None, list[AgentError], list[UsageLogEntry]]:
    developer_prompt = DIAGRAM_AGENT_PROMPT.render_developer_prompt(
        diagram_type=diagram_type,
        structured_input_json=json.dumps(structured_input),
    )
    errors: list[AgentError] = []
    usage_log: list[UsageLogEntry] = []

    for attempt in range(2):
        response = await llm.generate(
            messages=[
                LLMMessage(role="system", content=DIAGRAM_AGENT_PROMPT.system_prompt),
                LLMMessage(role="user", content=developer_prompt),
            ],
            temperature=0.1,
        )
        usage_log.append(
            UsageLogEntry(
                agent_name=DIAGRAM_AGENT_PROMPT.agent_name,
                model=response.model,
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
            )
        )
        content = _strip_wrapping_code_fence(response.content)
        violations = _validate_mermaid(content)

        if not violations:
            return content, errors, usage_log

        errors.append(
            AgentError(
                agent_name=DIAGRAM_AGENT_PROMPT.agent_name,
                message="; ".join(violations),
                retryable=attempt == 0,
            )
        )
        developer_prompt += "\n\nYour previous response had invalid Mermaid syntax: " + "; ".join(
            violations
        )

    return None, errors, usage_log


async def run_diagram_agent(state: DocumentationGraphState, llm: LLMProvider) -> dict:
    parsed = state["parsed_symbols"]
    diagrams: dict[str, str] = {}
    errors: list[AgentError] = []
    usage_log: list[UsageLogEntry] = []

    # ER diagram — only if the repository has DB models
    if parsed["db_models"]:
        content, err, usage = await _generate_one_diagram(
            "erDiagram", {"models": parsed["db_models"]}, llm
        )
        errors.extend(err)
        usage_log.extend(usage)
        if content:
            diagrams["er_diagram"] = content
        else:
            # graceful degradation per failure_recovery: skip diagram, don't fail the branch
            pass

    # Component diagram — driven by the Architecture Agent's diagram_request,
    # read from the merged `diagrams` state under the reserved key it wrote.
    architecture_request_raw = state.get("diagrams", {}).get("_architecture_diagram_request")
    if architecture_request_raw:
        structured = json.loads(architecture_request_raw)
        content, err, usage = await _generate_one_diagram("graph TD", structured, llm)
        errors.extend(err)
        usage_log.extend(usage)
        if content:
            diagrams["component_diagram"] = content

    return {"diagrams": diagrams, "errors": errors, "usage_log": usage_log}
