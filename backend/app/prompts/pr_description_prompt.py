"""Prompt spec for AI-generated pull request descriptions."""

from app.prompts.base import PromptSpec

PR_DESCRIPTION_PROMPT = PromptSpec(
    agent_name="pr_description_generator",
    system_prompt=(
        "You write pull request descriptions for a technical reviewer audience. Structure: "
        "a one-line title, then a 'What changed' section (concrete, from the diff) and a 'Why' "
        "section (inferred from commit messages if they explain motivation, otherwise omitted "
        "rather than invented). Never claim testing was done unless test file changes are visible "
        "in the diff."
    ),
    developer_prompt_template=(
        "Base branch: {base_branch}\nHead branch: {head_branch}\n\n"
        "Commit messages:\n{commit_messages}\n\n"
        "Diff:\n{diff}\n\n"
        'Return JSON: {{"title": string, "description": string (markdown)}}'
    ),
    expected_inputs=["base_branch", "head_branch", "commit_messages", "diff"],
    expected_output_schema="JSON: {title: string, description: string (markdown)}",
    validation_rules=[
        "description must not contain the literal phrase 'tests pass' or similar testing claims "
        "unless the diff includes changes under a path containing 'test'",
    ],
    failure_recovery=(
        "On JSON parse failure: retry once. On second failure: fall back to title = the first "
        "commit message's subject line, description = a flat bullet list of all commit messages — "
        "always produces something usable, never blocks PR creation."
    ),
)
