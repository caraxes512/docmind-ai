"""Repository parsing tests for app.parsing.tree_sitter_parser.

VERIFICATION NOTE: `extract_symbols_from_file`'s dispatch logic (routing
.py to the AST parser, unsupported extensions to an empty result) is
verified below without needing real Tree-sitter grammars. The actual
JS/TS/Java/C++/Go extraction via Tree-sitter queries is NOT exercised
here — it requires `tree-sitter-language-pack` and real grammars, neither
installable in the sandbox this suite was written in. Once dependencies
are installed, add fixture files under tests/fixtures/sample_repos/ per
language and assert against real extracted symbols before trusting the
Tree-sitter path in production; see tree_sitter_parser.py's own docstring
for the same caveat.
"""

import pytest

from app.parsing.tree_sitter_parser import extract_symbols_from_file

pytestmark = pytest.mark.parsing


def test_python_files_delegate_to_ast_parser(sample_python_file_content):
    """`.py` files never touch Tree-sitter at all — routed entirely to
    python_ast_parser.py (see that module's docstring for why)."""
    result = extract_symbols_from_file("app/models.py", sample_python_file_content)
    names = {s["name"] for s in result["symbols"]}
    assert "User" in names
    assert "display_name" in names
    assert len(result["api_routes"]) == 1
    assert result["api_routes"][0]["method"] == "GET"


def test_python_db_models_surfaced_separately_from_symbols(sample_python_file_content):
    result = extract_symbols_from_file("app/models.py", sample_python_file_content)
    assert len(result["db_models"]) == 1
    assert result["db_models"][0]["name"] == "User"
    # db_model isn't duplicated into the general `symbols` list
    assert not any(s.get("kind") == "db_model" for s in result["symbols"])


@pytest.mark.parametrize("path", ["README.md", "config.yaml", "no_extension", "data.json"])
def test_unsupported_file_types_return_empty_result(path):
    result = extract_symbols_from_file(path, "irrelevant content")
    assert result == {"symbols": [], "api_routes": [], "db_models": []}


@pytest.mark.skip(
    reason="Requires tree-sitter-language-pack and real grammars — not installable in this "
    "sandbox. Enable once dependencies are available; add sample_repos fixtures per language."
)
@pytest.mark.parametrize(
    "path,grammar",
    [
        ("src/index.ts", "typescript"),
        ("src/App.jsx", "javascript"),
        ("Main.java", "java"),
        ("lib.cpp", "cpp"),
        ("main.go", "go"),
    ],
)
def test_non_python_languages_extract_functions_and_classes(path, grammar):
    """Placeholder for real Tree-sitter verification — see module docstring."""
    raise NotImplementedError
