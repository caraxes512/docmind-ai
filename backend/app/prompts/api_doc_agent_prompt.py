"""Prompt spec for the API Documentation Agent. Only invoked when
RepositorySummary.has_api_endpoints is true."""

from app.prompts.base import PromptSpec

API_DOC_AGENT_PROMPT = PromptSpec(
    agent_name="api_documentation_agent",
    system_prompt=(
        "You are documenting the HTTP API surface of a codebase for other engineers who will "
        "integrate with it. You are given a structured list of detected routes (method, path, "
        "handler file/line, and the handler's parsed signature/docstring where available). Document "
        "only routes present in the input. If a route's request/response shape cannot be determined "
        "from the signature or docstring, state 'not statically determinable' rather than guessing "
        "field names."
    ),
    developer_prompt_template=(
        "Detected API routes:\n{api_routes_json}\n\n"
        "For each route, produce a section with: HTTP method + path, short description (from "
        "docstring if present, otherwise inferred from handler name), path/query parameters, "
        "request body shape (if determinable), response shape (if determinable), and example "
        "curl command. Group routes by their top-level path segment."
    ),
    expected_inputs=["api_routes_json"],
    expected_output_schema="Markdown document — one section per route, grouped by resource",
    validation_rules=[
        "Every documented route's method+path must exist verbatim in api_routes_json — no invented endpoints",
        "curl examples must use the exact path from input, with path params shown as <param_name> placeholders",
    ],
    failure_recovery=(
        "If api_routes_json is empty despite has_api_endpoints=true (a Parser Agent/Analyzer "
        "disagreement), skip generation, log an AgentError with retryable=false, and let the "
        "Orchestrator mark this doc type as 'not_applicable' rather than producing an empty document."
    ),
)
