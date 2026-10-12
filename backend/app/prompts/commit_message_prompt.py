"""Prompt spec for AI-generated commit messages. A single, cheap LLM call —
no multi-agent graph needed, unlike full documentation generation."""

from app.prompts.base import PromptSpec

COMMIT_MESSAGE_PROMPT = PromptSpec(
    agent_name="commit_message_generator",
    system_prompt=(
        "You write git commit messages following the Conventional Commits style "
        "(type(scope): subject) where the type is evident from the diff. Subject line under "
        "72 characters, imperative mood ('add' not 'added'). Only describe what the diff "
        "actually changes — never infer intent or business context not visible in the code."
    ),
    developer_prompt_template=(
        "Diff:\n{diff}\n\n"
        'Return JSON: {{"subject": string (<=72 chars), "body": string|null '
        "(only if the change needs more explanation than the subject allows, else null)}}"
    ),
    expected_inputs=["diff"],
    expected_output_schema="JSON: {subject: string, body: string|null}",
    validation_rules=[
        "subject must be <= 72 characters — truncate the LLM's output defensively even if it ignores the instruction",
        "subject must not end with a period, per Conventional Commits style",
    ],
    failure_recovery=(
        "On JSON parse failure: retry once. On second failure: fall back to a generic "
        "'chore: update files' subject with body=null rather than blocking the user's workflow — "
        "a mediocre auto-generated message they can edit is better than no message at all."
    ),
)
