"""README Agent — generates README.md from repository summary + a sample
of top-level symbols. Runs as a parallel branch after Parser Agent."""

import json
from typing import Callable

from app.agents.state import DocumentationGraphState
from app.agents._generation_helpers import generate_markdown_document
from app.llm.base import LLMProvider
from app.models.enums import DocumentType
from app.prompts import README_AGENT_PROMPT


def _validate_package_manager_consistency(manifest_paths: list[str]) -> Callable:
    def _validator(content: str) -> list[str]:
        violations = []
        has_poetry = any(p.endswith("pyproject.toml") for p in manifest_paths)
        has_pip = any(p.endswith("requirements.txt") for p in manifest_paths)
        if "poetry install" in content and not has_poetry:
            violations.append("references `poetry install` without a pyproject.toml manifest")
        if "pip install -r requirements.txt" in content and not has_pip:
            violations.append("references requirements.txt without one present")
        return violations

    return _validator


def _validate_min_length(content: str) -> list[str]:
    return ["README content is suspiciously short (<200 chars)"] if len(content) < 200 else []


async def run_readme_agent(
    state: DocumentationGraphState,
    llm: LLMProvider,
) -> dict:
    summary = state["repository_summary"]
    parsed = state["parsed_symbols"]

    sample_symbols = {path: syms[:5] for path, syms in list(parsed["symbols_by_file"].items())[:20]}

    developer_prompt = README_AGENT_PROMPT.render_developer_prompt(
        repository_summary_json=json.dumps(summary),
        entry_points=", ".join(summary["entry_points"]) or "none detected",
        dependency_manifest_paths=", ".join(summary["dependency_manifest_paths"]),
        symbol_sample_json=json.dumps(sample_symbols),
    )

    content, errors, usage_log = await generate_markdown_document(
        prompt=README_AGENT_PROMPT,
        llm=llm,
        developer_prompt=developer_prompt,
        validators=[
            _validate_min_length,
            _validate_package_manager_consistency(summary["dependency_manifest_paths"]),
        ],
    )

    update: dict = {"errors": errors, "usage_log": usage_log}
    if content is not None:
        update["generated_documents"] = {DocumentType.README.value: content}
    return update
