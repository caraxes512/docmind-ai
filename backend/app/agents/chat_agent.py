"""Repository Chat Agent. Structured as a tiny two-node graph (retrieve ->
generate) rather than a plain function, so retrieval and generation stay
independently testable and the retrieval step can be swapped (e.g. hybrid
BM25+vector search added later) without touching prompt logic.

Full wiring against the Qdrant-backed retriever lands in Step 9 — RAG
Pipeline; this file defines the generation step and citation extraction
against whatever retriever is injected.
"""

import json
import re
from dataclasses import dataclass
from typing import Protocol

from app.llm.base import LLMMessage, LLMProvider
from app.prompts import CHAT_AGENT_PROMPT
from app.agents.state import UsageLogEntry


@dataclass
class RetrievedChunk:
    file_path: str
    start_line: int
    end_line: int
    content: str
    similarity_score: float


class Retriever(Protocol):
    async def retrieve(
        self, repository_id: str, query: str, top_k: int = 8
    ) -> list[RetrievedChunk]: ...


_NO_MATCH_RESPONSE = (
    "I couldn't find any code in this repository related to your question. "
    "Try rephrasing, or confirm the feature you're asking about actually exists in this codebase."
)


def _extract_sources_section(answer_text: str) -> tuple[str, list[str]]:
    """Splits the model's answer from its trailing 'Sources' list, per the
    prompt's expected_output_schema."""
    match = re.search(r"\n\s*Sources?:?\s*\n(.+)$", answer_text, re.IGNORECASE | re.DOTALL)
    if not match:
        return answer_text.strip(), []

    body = answer_text[: match.start()].strip()
    sources_block = match.group(1)
    paths = re.findall(r"[\w./\-]+\.\w+", sources_block)
    return body, paths


async def run_chat_agent(
    repository_id: str,
    conversation_history: list[dict],
    user_question: str,
    retriever: Retriever,
    llm: LLMProvider,
) -> tuple[str, list[RetrievedChunk], list[UsageLogEntry]]:
    """Returns (answer_text, cited_chunks, usage_log). cited_chunks is the
    subset of retrieved chunks whose file_path was actually referenced in
    the 'Sources' section — used to populate Message.citations. usage_log
    is empty when no LLM call was made (the no-match short-circuit below)."""

    chunks = await retriever.retrieve(repository_id, user_question, top_k=8)

    if not chunks:
        return _NO_MATCH_RESPONSE, [], []

    developer_prompt = CHAT_AGENT_PROMPT.render_developer_prompt(
        conversation_history=json.dumps(conversation_history),
        retrieved_chunks_json=json.dumps([c.__dict__ for c in chunks]),
        user_question=user_question,
    )

    response = await llm.generate(
        messages=[
            LLMMessage(role="system", content=CHAT_AGENT_PROMPT.system_prompt),
            LLMMessage(role="user", content=developer_prompt),
        ],
        temperature=0.2,
    )
    usage_log = [
        UsageLogEntry(
            agent_name=CHAT_AGENT_PROMPT.agent_name,
            model=response.model,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
        )
    ]

    answer_text, cited_paths = _extract_sources_section(response.content)
    cited_paths_set = set(cited_paths)
    cited_chunks = [c for c in chunks if c.file_path in cited_paths_set]

    return answer_text, cited_chunks, usage_log
