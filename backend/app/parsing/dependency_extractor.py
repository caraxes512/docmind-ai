"""Dependency extraction from manifest files. Pure text parsing — the
"Dependency Extraction" pipeline stage from Step 1, run during ingestion
alongside language detection, before Tree-sitter/AST parsing.
"""

import json
import re
from typing import TypedDict


class Dependency(TypedDict):
    name: str
    version_constraint: str  # raw constraint string, e.g. "^4.2.0", ">=2.0,<3.0"; "" if unspecified


_REQUIREMENTS_LINE = re.compile(r"^\s*([A-Za-z0-9._-]+)\s*(\[[^\]]*\])?\s*([<>=!~].*)?\s*(?:#.*)?$")


def parse_requirements_txt(content: str) -> list[Dependency]:
    dependencies: list[Dependency] = []
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("-"):
            continue  # skip blanks, comments, and pip flags like -r/--index-url
        match = _REQUIREMENTS_LINE.match(stripped)
        if match:
            name, _extras, constraint = match.groups()
            dependencies.append(
                Dependency(name=name, version_constraint=(constraint or "").strip())
            )
    return dependencies


def parse_package_json(content: str) -> list[Dependency]:
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return []

    dependencies: list[Dependency] = []
    for section in ("dependencies", "devDependencies"):
        for name, version in (data.get(section) or {}).items():
            dependencies.append(Dependency(name=name, version_constraint=str(version)))
    return dependencies


_PYPROJECT_POETRY_LINE = re.compile(r'^\s*([A-Za-z0-9._-]+)\s*=\s*["\']?([^"\'\n]*)["\']?\s*$')
_PYPROJECT_PEP621_ENTRY = re.compile(r'^\s*"([A-Za-z0-9._-]+)\s*([<>=!~,.\d\s]*)"\s*,?\s*$')


def parse_pyproject_toml(content: str) -> list[Dependency]:
    """Handles both Poetry-style ([tool.poetry.dependencies] key = "constraint")
    and PEP 621-style (dependencies = ["name>=1.0", ...]) sections, without a
    full TOML parser — a small, deliberate scope limit: nested tables, arrays
    of inline tables, and other TOML features are not handled. Good enough
    for the common cases; a real TOML library is a low-risk upgrade later
    if a repository's pyproject.toml uses more exotic syntax.
    """
    dependencies: list[Dependency] = []
    lines = content.splitlines()

    in_poetry_deps_section = False
    in_pep621_deps_array = False

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("[tool.poetry.dependencies]") or stripped.startswith(
            "[tool.poetry.dev-dependencies]"
        ):
            in_poetry_deps_section = True
            continue
        if stripped.startswith("[") and in_poetry_deps_section:
            in_poetry_deps_section = False

        if in_poetry_deps_section:
            match = _PYPROJECT_POETRY_LINE.match(stripped)
            if match and match.group(1) != "python":  # python itself isn't a dependency
                dependencies.append(
                    Dependency(name=match.group(1), version_constraint=match.group(2))
                )
            continue

        if re.match(r"^\s*dependencies\s*=\s*\[", stripped):
            in_pep621_deps_array = True
            continue
        if in_pep621_deps_array:
            if "]" in stripped:
                in_pep621_deps_array = False
            match = _PYPROJECT_PEP621_ENTRY.match(stripped)
            if match:
                dependencies.append(
                    Dependency(name=match.group(1), version_constraint=match.group(2).strip())
                )

    return dependencies


def extract_dependencies(filename: str, content: str) -> list[Dependency]:
    """Dispatches to the right parser based on filename. Unsupported
    manifest types (go.mod, pom.xml) return an empty list rather than
    raising — dependency extraction quality varies by ecosystem, and a
    partial result is preferable to failing the whole ingestion pipeline."""
    basename = filename.rsplit("/", 1)[-1]
    if basename == "requirements.txt":
        return parse_requirements_txt(content)
    if basename == "package.json":
        return parse_package_json(content)
    if basename == "pyproject.toml":
        return parse_pyproject_toml(content)
    return []
