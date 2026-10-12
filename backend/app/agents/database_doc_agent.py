"""Database Documentation Agent — only invoked (by the Orchestrator's
routing function) when RepositorySummary.has_database is true."""

import json

from app.agents.state import DocumentationGraphState
from app.agents._generation_helpers import generate_markdown_document
from app.llm.base import LLMProvider
from app.models.enums import DocumentType
from app.prompts import DATABASE_DOC_AGENT_PROMPT


def _validate_min_length(content: str) -> list[str]:
    return ["database docs content is suspiciously short (<50 chars)"] if len(content) < 50 else []


async def run_database_doc_agent(state: DocumentationGraphState, llm: LLMProvider) -> dict:
    parsed = state["parsed_symbols"]
    db_models = parsed["db_models"]

    if not db_models:
        # Per failure_recovery: static note, no LLM call, avoids hallucinating a schema.
        note = (
            "Database usage detected via dependency manifest, but no ORM model definitions "
            "were found to document automatically."
        )
        return {"generated_documents": {DocumentType.DATABASE_DOCS.value: note}}

    developer_prompt = DATABASE_DOC_AGENT_PROMPT.render_developer_prompt(
        db_models_json=json.dumps(db_models),
    )

    content, errors, usage_log = await generate_markdown_document(
        prompt=DATABASE_DOC_AGENT_PROMPT,
        llm=llm,
        developer_prompt=developer_prompt,
        validators=[_validate_min_length],
    )

    update: dict = {"errors": errors, "usage_log": usage_log}
    if content is not None:
        update["generated_documents"] = {DocumentType.DATABASE_DOCS.value: content}
    return update
