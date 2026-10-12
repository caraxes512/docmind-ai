"""Function Documentation Agent — documents classes/functions in batches
of ~40 symbols per LLM call to stay within context limits and so a single
batch's validation failure doesn't discard already-validated batches."""

import json

from app.agents.state import AgentError, DocumentationGraphState, UsageLogEntry
from app.agents._generation_helpers import _strip_wrapping_code_fence
from app.llm.base import LLMMessage, LLMProvider
from app.models.enums import DocumentType
from app.prompts import FUNCTION_DOC_AGENT_PROMPT

BATCH_SIZE = 40


def _flatten_symbols(symbols_by_file: dict[str, list[dict]]) -> list[tuple[str, dict]]:
    flat = []
    for file_path, symbols in symbols_by_file.items():
        for symbol in symbols:
            flat.append((file_path, symbol))
    return flat


def _batch(items: list, size: int) -> list[list]:
    return [items[i : i + size] for i in range(0, len(items), size)]


async def run_function_doc_agent(state: DocumentationGraphState, llm: LLMProvider) -> dict:
    parsed = state["parsed_symbols"]
    flat_symbols = _flatten_symbols(parsed["symbols_by_file"])

    if not flat_symbols:
        return {}

    batches = _batch(flat_symbols, BATCH_SIZE)
    sections: list[str] = []
    errors: list[AgentError] = []
    usage_log: list[UsageLogEntry] = []

    for batch_index, batch in enumerate(batches):
        file_path = batch[0][
            0
        ]  # symbols within a batch may span files; grouped loosely by first file
        symbols_json = json.dumps([s for _, s in batch])

        developer_prompt = FUNCTION_DOC_AGENT_PROMPT.render_developer_prompt(
            file_path=file_path,
            batch_index=batch_index + 1,
            batch_count=len(batches),
            symbols_json=symbols_json,
        )

        try:
            response = await llm.generate(
                messages=[
                    LLMMessage(role="system", content=FUNCTION_DOC_AGENT_PROMPT.system_prompt),
                    LLMMessage(role="user", content=developer_prompt),
                ],
                temperature=0.1,
            )
            usage_log.append(
                UsageLogEntry(
                    agent_name=FUNCTION_DOC_AGENT_PROMPT.agent_name,
                    model=response.model,
                    input_tokens=response.input_tokens,
                    output_tokens=response.output_tokens,
                )
            )
            content = _strip_wrapping_code_fence(response.content)

            documented_names = {s["name"] for _, s in batch}
            # cheap sanity check per validation_rules: at least one known symbol name must appear
            if not any(name in content for name in documented_names):
                raise ValueError("no expected symbol names found in output")

            sections.append(content)
        except Exception as exc:  # noqa: BLE001
            errors.append(
                AgentError(
                    agent_name=FUNCTION_DOC_AGENT_PROMPT.agent_name,
                    message=f"batch {batch_index + 1}/{len(batches)} failed: {exc}",
                    retryable=True,
                )
            )
            continue  # per failure_recovery: only this batch is lost, not prior batches

    update: dict = {"errors": errors, "usage_log": usage_log}
    if sections:
        update["generated_documents"] = {
            DocumentType.FUNCTION_DOCS.value: "\n\n---\n\n".join(sections)
        }
    return update
