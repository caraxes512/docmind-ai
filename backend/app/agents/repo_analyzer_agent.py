"""Repository Analyzer Agent — first node in the documentation graph.

Consumes a pre-built file tree + manifest contents (assembled by the
ingestion service before the graph runs, not by this agent) and produces
the RepositorySummary that every downstream routing decision depends on.
"""

import json
import logging

from app.agents.state import AgentError, DocumentationGraphState, RepositorySummary, UsageLogEntry
from app.llm.base import LLMMessage, LLMProvider
from app.prompts import REPOSITORY_ANALYZER_PROMPT

logger = logging.getLogger(__name__)

_KNOWN_DB_DEPENDENCIES = {
    "sqlalchemy",
    "psycopg2",
    "asyncpg",
    "prisma",
    "mongoose",
    "pymongo",
    "django",
    "typeorm",
    "sequelize",
    "gorm",
    "hibernate",
}


def _validate_summary(raw: dict, file_tree: list[str]) -> RepositorySummary:
    languages = raw.get("languages") or ["unknown"]
    entry_points = [p for p in raw.get("entry_points", []) if p in file_tree]

    return RepositorySummary(
        languages=languages,
        has_database=bool(raw.get("has_database", False)),
        has_api_endpoints=bool(raw.get("has_api_endpoints", False)),
        has_frontend=bool(raw.get("has_frontend", False)),
        entry_points=entry_points,
        dependency_manifest_paths=raw.get("dependency_manifest_paths", []),
    )


async def run_repository_analyzer_agent(
    state: DocumentationGraphState,
    llm: LLMProvider,
    file_tree: list[str],
    manifest_contents: str,
    config_file_contents: str,
) -> dict:
    """Returns a partial state update: {"repository_summary": ...} or
    {"errors": [...]} on unrecoverable failure (heuristic fallback still
    populates repository_summary — see failure_recovery in the prompt spec)."""

    prompt = REPOSITORY_ANALYZER_PROMPT
    developer_prompt = prompt.render_developer_prompt(
        file_tree="\n".join(
            file_tree[:2000]
        ),  # cap for context size; deeper trees are summarized upstream
        manifest_contents=manifest_contents,
        config_file_contents=config_file_contents,
    )
    usage_log: list[UsageLogEntry] = []

    for attempt in range(2):
        try:
            response = await llm.generate(
                messages=[
                    LLMMessage(role="system", content=prompt.system_prompt),
                    LLMMessage(role="user", content=developer_prompt),
                ],
                temperature=0.0,
                response_format_json=True,
            )
            usage_log.append(
                UsageLogEntry(
                    agent_name=prompt.agent_name,
                    model=response.model,
                    input_tokens=response.input_tokens,
                    output_tokens=response.output_tokens,
                )
            )
            raw = json.loads(response.content)
            summary = _validate_summary(raw, file_tree)
            return {"repository_summary": summary, "usage_log": usage_log}
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            logger.warning("repository_analyzer_agent parse failure (attempt %d): %s", attempt, exc)
            developer_prompt += (
                "\n\nYour previous response was not valid JSON matching the schema. "
                "Return ONLY the JSON object, no prose."
            )

    # Both attempts failed — deterministic heuristic fallback (see failure_recovery)
    logger.error("repository_analyzer_agent falling back to heuristic classification")
    fallback = _heuristic_fallback(file_tree, manifest_contents)
    return {
        "repository_summary": fallback,
        "usage_log": usage_log,
        "errors": [
            AgentError(
                agent_name=prompt.agent_name,
                message="LLM classification failed twice; used heuristic fallback (low confidence)",
                retryable=False,
            )
        ],
    }


def _heuristic_fallback(file_tree: list[str], manifest_contents: str) -> RepositorySummary:
    ext_counts: dict[str, int] = {}
    for path in file_tree:
        if "." in path:
            ext = path.rsplit(".", 1)[-1]
            ext_counts[ext] = ext_counts.get(ext, 0) + 1

    ext_to_lang = {
        "py": "python",
        "js": "javascript",
        "ts": "typescript",
        "java": "java",
        "go": "go",
        "cpp": "cpp",
    }
    languages = sorted({ext_to_lang[e] for e in ext_counts if e in ext_to_lang}) or ["unknown"]

    manifest_lower = manifest_contents.lower()
    has_database = any(dep in manifest_lower for dep in _KNOWN_DB_DEPENDENCIES)

    return RepositorySummary(
        languages=languages,
        has_database=has_database,
        has_api_endpoints=False,  # conservative — heuristic can't reliably detect this
        has_frontend="package.json" in "\n".join(file_tree)
        and ("tsx" in ext_counts or "jsx" in ext_counts),
        entry_points=[],
        dependency_manifest_paths=[
            p
            for p in file_tree
            if p.endswith(
                ("requirements.txt", "package.json", "pyproject.toml", "pom.xml", "go.mod")
            )
        ],
    )
