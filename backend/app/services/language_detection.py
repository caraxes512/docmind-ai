"""Deterministic language detection by file extension. Kept separate from
the Tree-sitter parser (app/parsing/tree_sitter_parser.py) since this runs
during the fast, synchronous-feeling scan step (Step 5), well before
Tree-sitter parsing happens (Step 9) — it only needs to classify, not parse.
"""

from app.models.enums import ProgrammingLanguage

_EXTENSION_MAP: dict[str, ProgrammingLanguage] = {
    "py": ProgrammingLanguage.PYTHON,
    "js": ProgrammingLanguage.JAVASCRIPT,
    "jsx": ProgrammingLanguage.JAVASCRIPT,
    "mjs": ProgrammingLanguage.JAVASCRIPT,
    "ts": ProgrammingLanguage.TYPESCRIPT,
    "tsx": ProgrammingLanguage.TYPESCRIPT,
    "java": ProgrammingLanguage.JAVA,
    "cpp": ProgrammingLanguage.CPP,
    "cc": ProgrammingLanguage.CPP,
    "cxx": ProgrammingLanguage.CPP,
    "hpp": ProgrammingLanguage.CPP,
    "h": ProgrammingLanguage.CPP,
    "go": ProgrammingLanguage.GO,
}

# Paths under these directories are excluded from scanning entirely (vendored
# deps, build artifacts, VCS metadata) — never hashed, never counted toward
# RepositoryFile rows, regardless of extension.
EXCLUDED_DIR_SEGMENTS = {
    "node_modules",
    ".git",
    "__pycache__",
    "dist",
    "build",
    ".venv",
    "venv",
    "vendor",
    ".next",
    "target",
    ".mypy_cache",
    ".pytest_cache",
}


def detect_language(file_path: str) -> ProgrammingLanguage:
    if "." not in file_path:
        return ProgrammingLanguage.UNKNOWN
    ext = file_path.rsplit(".", 1)[-1].lower()
    return _EXTENSION_MAP.get(ext, ProgrammingLanguage.UNKNOWN)


def is_excluded_path(file_path: str) -> bool:
    parts = set(file_path.split("/"))
    return bool(parts & EXCLUDED_DIR_SEGMENTS)
