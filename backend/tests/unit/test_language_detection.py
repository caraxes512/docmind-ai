"""Unit tests for app.services.language_detection."""

import pytest

from app.services.language_detection import detect_language, is_excluded_path

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "path,expected_language",
    [
        ("app/main.py", "python"),
        ("src/index.ts", "typescript"),
        ("src/App.tsx", "typescript"),
        ("src/index.js", "javascript"),
        ("src/App.jsx", "javascript"),
        ("Main.java", "java"),
        ("main.go", "go"),
        ("lib.cpp", "cpp"),
        ("lib.hpp", "cpp"),
        ("README.md", "unknown"),
        ("no_extension_file", "unknown"),
    ],
)
def test_detect_language_by_extension(path, expected_language):
    assert detect_language(path).value == expected_language


@pytest.mark.parametrize(
    "path",
    [
        "node_modules/react/index.js",
        "backend/.venv/lib/python3.12/site.py",
        "frontend/.next/cache/x.js",
        ".git/config",
        "backend/__pycache__/main.cpython-312.pyc",
    ],
)
def test_excluded_paths_detected(path):
    assert is_excluded_path(path) is True


@pytest.mark.parametrize("path", ["app/main.py", "src/index.ts", "README.md"])
def test_normal_paths_not_excluded(path):
    assert is_excluded_path(path) is False
