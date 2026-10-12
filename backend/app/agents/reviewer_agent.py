"""Documentation Reviewer Agent — the fan-in node. Runs once all parallel
doc-generation branches have completed, reviewing each generated document
independently and assigning a quality score + issue list.

`review_single_document` is factored out so DocumentationService.trigger_review
(a one-off, single-document review triggered from the UI) reuses the exact
same logic as the graph's fan-in node, rather than duplicating the
call/validate/score-clamping behavior in two places.
"""

import json
import logging

from app.agents.state import AgentError, DocumentationGraphState, UsageLogEntry
from app.llm.base import LLMMessage, LLMProvider
from app.prompts import REVIEWER_AGENT_PROMPT

logger = logging.getLogger(__name__)

MIN_REVIEWABLE_LENGTH = 100


def _cross_reference_for(doc_type: str, parsed_symbols: dict) -> dict:
    """Selects the relevant slice of parsed_symbols to ground the review
    (e.g. API Docs review cross-checks against api_routes, not db_models).
    Returns {} for doc types with no natural cross-reference (README, etc.)
    — the reviewer still runs, just without structural grounding."""
    if doc_type == "api_docs":
        return {"api_routes": parsed_symbols.get("api_routes", [])}
    if doc_type == "database_docs":
        return {"db_models": parsed_symbols.get("db_models", [])}
    return {}


async def review_single_document(
    doc_type: str, content: str, cross_reference: dict, llm: LLMProvider
) -> tuple[dict, list[UsageLogEntry], list[AgentError]]:
    """Returns ({"score": float, "issues": [...]}, usage_log, errors)."""
    usage_log: list[UsageLogEntry] = []
    errors: list[AgentError] = []

    if len(content) < MIN_REVIEWABLE_LENGTH:
        # Cost optimization per validation_rules: obvious case skips the LLM call entirely.
        return (
            {
                "score": 0,
                "issues": [
                    {
                        "type": "missing_documentation",
                        "location": None,
                        "severity": "high",
                        "description": "Document content is too short to represent meaningful documentation.",
                    }
                ],
            },
            usage_log,
            errors,
        )

    developer_prompt = REVIEWER_AGENT_PROMPT.render_developer_prompt(
        doc_type=doc_type,
        document_content=content,
        cross_reference_json=json.dumps(cross_reference),
    )

    try:
        response = await llm.generate(
            messages=[
                LLMMessage(role="system", content=REVIEWER_AGENT_PROMPT.system_prompt),
                LLMMessage(role="user", content=developer_prompt),
            ],
            temperature=0.0,
            response_format_json=True,
        )
        usage_log.append(
            UsageLogEntry(
                agent_name=REVIEWER_AGENT_PROMPT.agent_name,
                model=response.model,
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
            )
        )
        result = json.loads(response.content)
        score = max(0, min(100, result.get("score", 0)))
        return {"score": score, "issues": result.get("issues", [])}, usage_log, errors
    except (json.JSONDecodeError, KeyError) as exc:
        logger.warning("reviewer_agent failed for %s: %s", doc_type, exc)
        errors.append(
            AgentError(
                agent_name=REVIEWER_AGENT_PROMPT.agent_name, message=str(exc), retryable=False
            )
        )
        return (
            {
                "score": 0,
                "issues": [
                    {
                        "type": "missing_documentation",
                        "location": None,
                        "severity": "high",
                        "description": "Automated review could not complete for this document; requires manual review.",
                    }
                ],
            },
            usage_log,
            errors,
        )


async def run_reviewer_agent(state: DocumentationGraphState, llm: LLMProvider) -> dict:
    documents = state["generated_documents"]
    parsed = state["parsed_symbols"]
    review_results: dict[str, dict] = {}
    all_errors: list[AgentError] = []
    all_usage: list[UsageLogEntry] = []

    for doc_type, content in documents.items():
        if doc_type.startswith("_"):
            continue  # skip internal scratch keys like _architecture_diagram_request

        cross_reference = _cross_reference_for(doc_type, parsed)
        result, usage_log, errors = await review_single_document(
            doc_type, content, cross_reference, llm
        )
        review_results[doc_type] = result
        all_usage.extend(usage_log)
        all_errors.extend(errors)

    return {"review_results": review_results, "errors": all_errors, "usage_log": all_usage}
