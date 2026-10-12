"""Prompt spec for AI-generated release notes."""

from app.prompts.base import PromptSpec

RELEASE_NOTES_PROMPT = PromptSpec(
    agent_name="release_notes_generator",
    system_prompt=(
        "You write release notes for end users of a software product, grouping commits into "
        "'Features', 'Fixes', and 'Other Changes' sections based on their Conventional Commits "
        "type prefix where present (feat/fix/chore/etc), or content inference where absent. "
        "Omit internal-only changes (CI config, formatting) from user-facing notes unless no "
        "other changes exist for that release."
    ),
    developer_prompt_template=(
        "Range: {from_tag} to {to_tag}\n\nCommit messages:\n{commit_messages}\n\n"
        "Write release notes in Markdown with 'Features', 'Fixes', and 'Other Changes' headings "
        "(omit any section with nothing to list)."
    ),
    expected_inputs=["from_tag", "to_tag", "commit_messages"],
    expected_output_schema="Markdown document",
    validation_rules=[
        "every bullet point must correspond to at least one commit message in the input — "
        "no summarizing across commits into a claim not traceable to any single one",
    ],
    failure_recovery=(
        "On empty/degenerate output: fall back to a flat, ungrouped bullet list of all commit "
        "messages verbatim — worse formatting is preferable to missing entries in a release note."
    ),
)
