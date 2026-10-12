"""Prompt spec for the README Agent."""

from app.prompts.base import PromptSpec

README_AGENT_PROMPT = PromptSpec(
    agent_name="readme_agent",
    system_prompt=(
        "You are a technical writer generating a README.md for an open-source project. "
        "Write for a developer encountering this repository for the first time. Be accurate: "
        "only describe features, commands, and configuration that are directly evidenced in the "
        "provided repository summary and parsed symbols — never invent commands, package names, "
        "or environment variables that don't appear in the input. Prefer concrete, copy-pasteable "
        "shell commands over vague instructions."
    ),
    developer_prompt_template=(
        "Repository summary:\n{repository_summary_json}\n\n"
        "Detected entry points: {entry_points}\n"
        "Detected dependency manifests: {dependency_manifest_paths}\n"
        "Top-level parsed symbols (first 40, for feature inference only — do not enumerate all in the README):\n"
        "{symbol_sample_json}\n\n"
        "Generate a complete README.md with these sections in order: Title + one-line description, "
        "Features (bulleted, inferred from entry points/routes/modules), Installation, Usage, "
        "Configuration (env vars found in .env.example if provided), Contributing (short pointer to "
        "CONTRIBUTING.md), License (state 'See LICENSE file' — do not invent a license name)."
    ),
    expected_inputs=[
        "repository_summary_json",
        "entry_points",
        "dependency_manifest_paths",
        "symbol_sample_json",
    ],
    expected_output_schema="Markdown document (not JSON) — full README.md content as a single string",
    validation_rules=[
        "Reject output containing installation commands referencing a package manager not present "
        "in dependency_manifest_paths (e.g. `poetry install` when only requirements.txt exists)",
        "Reject output shorter than 200 characters (indicates a degenerate/refused generation)",
        "Strip any code fence wrapping the entire document (model sometimes wraps full markdown in ```markdown)",
    ],
    failure_recovery=(
        "On validation failure: retry once with the specific violated rule appended to the developer "
        "prompt as a correction note. On second failure: persist the best available draft with "
        "DocumentStatus=FAILED and surface the validation error via the Task's error_message so a human "
        "can inspect it in the Documentation Editor rather than silently blocking the whole generation run."
    ),
)
