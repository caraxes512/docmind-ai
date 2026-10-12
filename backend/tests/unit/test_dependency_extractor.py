"""Unit tests for app.parsing.dependency_extractor."""

import pytest

from app.parsing.dependency_extractor import (
    extract_dependencies,
    parse_package_json,
    parse_pyproject_toml,
    parse_requirements_txt,
)

pytestmark = pytest.mark.unit


REQUIREMENTS_TXT = """
# a comment
fastapi>=0.115,<1.0
sqlalchemy==2.0.36
-r other-requirements.txt
uvicorn[standard]>=0.32

celery[redis]>=5.4
"""


def test_requirements_txt_skips_comments_and_flags():
    deps = parse_requirements_txt(REQUIREMENTS_TXT)
    names = {d["name"] for d in deps}
    assert names == {"fastapi", "sqlalchemy", "uvicorn", "celery"}


def test_requirements_txt_captures_version_constraint():
    deps = parse_requirements_txt(REQUIREMENTS_TXT)
    fastapi_dep = next(d for d in deps if d["name"] == "fastapi")
    assert fastapi_dep["version_constraint"] == ">=0.115,<1.0"


PACKAGE_JSON = """{
  "name": "frontend",
  "dependencies": {"next": "^14.2.15", "react": "^18.3.1"},
  "devDependencies": {"typescript": "^5.6.3"}
}"""


def test_package_json_extracts_deps_and_dev_deps():
    deps = parse_package_json(PACKAGE_JSON)
    assert {d["name"] for d in deps} == {"next", "react", "typescript"}


def test_package_json_captures_version_string():
    deps = parse_package_json(PACKAGE_JSON)
    next_dep = next(d for d in deps if d["name"] == "next")
    assert next_dep["version_constraint"] == "^14.2.15"


def test_package_json_malformed_returns_empty_not_raises():
    assert parse_package_json("{not valid json") == []


POETRY_PYPROJECT = """
[tool.poetry]
name = "docmind-ai-backend"

[tool.poetry.dependencies]
python = "^3.12"
fastapi = ">=0.115"
sqlalchemy = "^2.0.36"

[tool.poetry.dev-dependencies]
pytest = "^8.3"
"""


def test_pyproject_poetry_style_excludes_python_itself():
    deps = parse_pyproject_toml(POETRY_PYPROJECT)
    names = {d["name"] for d in deps}
    assert names == {"fastapi", "sqlalchemy", "pytest"}
    assert "python" not in names


PEP621_PYPROJECT = """
[project]
name = "docmind-ai-backend"
dependencies = [
    "fastapi>=0.115",
    "sqlalchemy>=2.0.36",
]
"""


def test_pyproject_pep621_style_extracts_array_deps():
    deps = parse_pyproject_toml(PEP621_PYPROJECT)
    assert {d["name"] for d in deps} == {"fastapi", "sqlalchemy"}


def test_extract_dependencies_dispatches_by_filename():
    deps = extract_dependencies("backend/requirements.txt", REQUIREMENTS_TXT)
    assert {d["name"] for d in deps} == {"fastapi", "sqlalchemy", "uvicorn", "celery"}


def test_extract_dependencies_unsupported_manifest_returns_empty():
    assert extract_dependencies("go.mod", "module example.com/foo\ngo 1.21") == []
