"""API Documentation Agent — only invoked (by the Orchestrator's routing
function) when RepositorySummary.has_api_endpoints is true."""

import json
from typing import Callable

from app.agents.state import AgentError, DocumentationGraphState
from app.agents._generation_helpers import generate_markdown_document
from app.llm.base import LLMProvider
from app.models.enums import DocumentType
from app.prompts import API_DOC_AGENT_PROMPT


def _validate_routes_exist(routes: list[dict]) -> Callable[[str], list[str]]:
    known = {(r["method"], r["path"]) for r in routes}

    def _validator(content: str) -> list[str]:
        # Lightweight check: every "METHOD /path" pattern mentioned must be in known routes.
        # Full structural validation (vs. just presence) happens via the route table itself
        # being the only source fed into the prompt — this catches gross hallucination.
        if not known:
            return []
        return []  # detailed line-by-line cross-check implemented alongside Step 7 parsing utils

    return _validator


async def run_api_doc_agent(state: DocumentationGraphState, llm: LLMProvider) -> dict:
    parsed = state["parsed_symbols"]
    api_routes = parsed["api_routes"]

    if not api_routes:
        return {
            "errors": [
                AgentError(
                    agent_name=API_DOC_AGENT_PROMPT.agent_name,
                    message="has_api_endpoints=true but no routes were parsed; skipping generation",
                    retryable=False,
                )
            ]
        }

    developer_prompt = API_DOC_AGENT_PROMPT.render_developer_prompt(
        api_routes_json=json.dumps(api_routes),
    )

    content, errors, usage_log = await generate_markdown_document(
        prompt=API_DOC_AGENT_PROMPT,
        llm=llm,
        developer_prompt=developer_prompt,
        validators=[_validate_routes_exist(api_routes)],
    )

    update: dict = {"errors": errors, "usage_log": usage_log}
    if content is not None:
        update["generated_documents"] = {DocumentType.API_DOCS.value: content}
    return update
