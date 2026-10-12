"""Prompt spec for AI-generated changelog entries (Keep a Changelog format)."""

from app.prompts.base import PromptSpec

CHANGELOG_PROMPT = PromptSpec(
    agent_name="changelog_generator",
    system_prompt=(
        "You write a single changelog entry following the Keep a Changelog convention: "
        "a version heading, then 'Added', 'Changed', 'Fixed', 'Removed' subsections as "
        "applicable (omit empty ones), each a terse bullet list derived from commit messages."
    ),
    developer_prompt_template=(
        "Version: {version}\n\nCommit messages:\n{commit_messages}\n\n"
        "Return the changelog entry in Markdown, starting with '## [{version}]'."
    ),
    expected_inputs=["version", "commit_messages"],
    expected_output_schema="Markdown document, starting with a '## [version]' heading",
    validation_rules=[
        "output must start with '## [' — reject and retry if the model wrapped it in prose instead",
    ],
    failure_recovery=(
        "On validation failure: retry once with the exact required heading format quoted back. "
        "On second failure: emit '## [{version}]\\n\\n### Changed\\n' followed by raw commit "
        "messages as bullets — degrades formatting quality, not availability."
    ),
)
