"""Prompt spec for the Function Documentation Agent."""

from app.prompts.base import PromptSpec

FUNCTION_DOC_AGENT_PROMPT = PromptSpec(
    agent_name="function_documentation_agent",
    system_prompt=(
        "You document individual functions and classes for a generated API reference page. "
        "You are given parsed symbols (name, kind, signature, existing docstring if any, and the "
        "surrounding 10 lines of source for context). Where an accurate docstring already exists, "
        "prefer summarizing it faithfully over rewriting from scratch. Where no docstring exists, "
        "infer purpose conservatively from the signature and surrounding code — flag low-confidence "
        "inferences explicitly rather than presenting a guess as fact."
    ),
    developer_prompt_template=(
        "Parsed symbols for file {file_path} (batch {batch_index} of {batch_count}):\n"
        "{symbols_json}\n\n"
        "For each symbol, produce: signature (verbatim), one-paragraph description, parameters "
        "table (name, type if known, description), return value description, and "
        "'Confidence: high|low' if purpose was inferred rather than read from an existing docstring."
    ),
    expected_inputs=["file_path", "batch_index", "batch_count", "symbols_json"],
    expected_output_schema="Markdown document — one subsection per symbol, grouped under the file's heading",
    validation_rules=[
        "Every documented symbol name+signature must match an entry in symbols_json verbatim",
        "Parameters table row count must equal the parameter count in the signature — flag mismatches "
        "rather than silently dropping or inventing parameters",
    ],
    failure_recovery=(
        "Function docs are generated in batches of ~40 symbols per LLM call (context window and cost "
        "management, not a single call per repo). If one batch fails validation, only that batch is "
        "retried (once) — a failure in batch 3 of 10 never discards batches 1-2's already-validated output."
    ),
)
