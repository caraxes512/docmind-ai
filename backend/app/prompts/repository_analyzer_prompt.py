"""Prompt spec for the Repository Analyzer Agent.

This agent runs first and its output (RepositorySummary) drives every
downstream routing decision — whether Database Docs Agent runs at all,
which languages the Parser Agent should expect, etc. It receives a
pre-computed file tree + dependency manifest contents (extracted
deterministically before this LLM call — the agent reasons over structure,
it doesn't re-discover files itself).
"""

from app.prompts.base import PromptSpec

REPOSITORY_ANALYZER_PROMPT = PromptSpec(
    agent_name="repository_analyzer",
    system_prompt=(
        "You are a senior software architect performing an initial reconnaissance pass over "
        "an unfamiliar codebase. Your job is to classify the repository's technology stack and "
        "structural characteristics from its file tree and manifest files. You do not read full "
        "source files — only the file tree, dependency manifests (package.json, requirements.txt, "
        "pyproject.toml, pom.xml, go.mod), and configuration files (docker-compose.yml, .env.example) "
        "provided to you. Be conservative: only report a characteristic (e.g. 'has_database') if "
        "there is direct evidence in the provided files, not inference from project naming."
    ),
    developer_prompt_template=(
        "Repository file tree (paths only, truncated to depth 4):\n{file_tree}\n\n"
        "Dependency manifest contents:\n{manifest_contents}\n\n"
        "Configuration files found:\n{config_file_contents}\n\n"
        "Return a JSON object matching the RepositorySummary schema exactly."
    ),
    expected_inputs=["file_tree", "manifest_contents", "config_file_contents"],
    expected_output_schema=(
        "JSON: {languages: string[], has_database: bool, has_api_endpoints: bool, "
        "has_frontend: bool, entry_points: string[], dependency_manifest_paths: string[]}"
    ),
    validation_rules=[
        "languages must be a non-empty list; unrecognized files count toward 'unknown', never omitted silently",
        "has_database=true requires at least one matched ORM/driver dependency (e.g. sqlalchemy, prisma, mongoose) "
        "or a docker-compose service named like a DB engine — reject the claim otherwise and log a validation warning",
        "entry_points must be paths that actually appear in file_tree — any path not in the input tree is stripped",
    ],
    failure_recovery=(
        "On JSON parse failure: retry once with a corrective system message appending "
        "'Your previous response was not valid JSON. Return ONLY the JSON object, no prose.' "
        "On second failure: fall back to a deterministic heuristic classifier (file-extension "
        "histogram + known manifest filename matching) and mark the summary as `low_confidence=true` "
        "in metadata so the Orchestrator can surface a warning in the UI rather than silently proceeding."
    ),
)
