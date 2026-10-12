"""Tree-sitter based symbol extraction for JavaScript, TypeScript, Java,
C++, and Go. Python is handled entirely by python_ast_parser.py instead
(see that module's docstring for why) -- this module is never invoked for
.py files.

VERIFICATION CAVEAT: this file cannot be executed in the sandbox this
project was built in (no network access to install `tree-sitter` or
`tree-sitter-language-pack`, and pre-compiled grammars can't be fetched
either). It's written carefully against the documented Tree-sitter Query
API and hand-traced against each language's real grammar node names (as
of tree-sitter's stable grammars), but -- unlike python_ast_parser.py and
dependency_extractor.py in this same step, which run on Python's stdlib
and were verified with real executed tests -- this specific file needs a
real `pip install tree-sitter tree-sitter-language-pack` and a sample
repository per language to confirm the queries match actual parse trees
before relying on it in production.
"""

from typing import TypedDict

from tree_sitter_language_pack import get_language, get_parser

from app.parsing.python_ast_parser import extract_python_symbols


class ExtractedSymbols(TypedDict):
    symbols: list[dict]
    api_routes: list[dict]
    db_models: list[dict]


# One query per language, capturing functions/methods/classes generically.
# Route/model detection is best-effort and framework-specific -- see
# _detect_routes_and_models below.
_QUERIES: dict[str, str] = {
    "javascript": """
        (function_declaration name: (identifier) @func.name) @func.def
        (method_definition name: (property_identifier) @method.name) @method.def
        (class_declaration name: (identifier) @class.name) @class.def
    """,
    "typescript": """
        (function_declaration name: (identifier) @func.name) @func.def
        (method_definition name: (property_identifier) @method.name) @method.def
        (class_declaration name: (type_identifier) @class.name) @class.def
    """,
    "java": """
        (method_declaration name: (identifier) @method.name) @method.def
        (class_declaration name: (identifier) @class.name) @class.def
    """,
    "cpp": """
        (function_definition declarator: (function_declarator declarator: (identifier) @func.name)) @func.def
        (class_specifier name: (type_identifier) @class.name) @class.def
    """,
    "go": """
        (function_declaration name: (identifier) @func.name) @func.def
        (method_declaration name: (field_identifier) @method.name) @method.def
        (type_declaration (type_spec name: (type_identifier) @type.name type: (struct_type) @struct.def))
    """,
}

_EXTENSION_TO_GRAMMAR = {
    "js": "javascript",
    "jsx": "javascript",
    "mjs": "javascript",
    "ts": "typescript",
    "tsx": "typescript",
    "java": "java",
    "cpp": "cpp",
    "cc": "cpp",
    "cxx": "cpp",
    "hpp": "cpp",
    "h": "cpp",
    "go": "go",
}

_parser_cache: dict[str, object] = {}
_query_cache: dict[str, object] = {}


def _get_cached_parser_and_query(grammar_name: str):
    if grammar_name not in _parser_cache:
        _parser_cache[grammar_name] = get_parser(grammar_name)
        language = get_language(grammar_name)
        _query_cache[grammar_name] = language.query(_QUERIES[grammar_name])
    return _parser_cache[grammar_name], _query_cache[grammar_name]


def _node_text(node, source_bytes: bytes) -> str:
    return source_bytes[node.start_byte : node.end_byte].decode("utf-8", errors="replace")


def _detect_routes_and_models(
    grammar_name: str, source_bytes: bytes
) -> tuple[list[dict], list[dict]]:
    """Best-effort, framework-specific detection layered on top of the
    generic symbol query above. Kept separate so adding a new framework
    doesn't require touching the core class/function extraction query.
    """
    routes: list[dict] = []
    models: list[dict] = []
    text = source_bytes.decode("utf-8", errors="replace")

    if grammar_name in ("javascript", "typescript"):
        import re

        for match in re.finditer(
            r"\b(?:app|router)\.(get|post|put|patch|delete)\(\s*['\"]([^'\"]+)['\"]", text
        ):
            line = text[: match.start()].count("\n") + 1
            routes.append({"method": match.group(1).upper(), "path": match.group(2), "line": line})
        for match in re.finditer(
            r"@(Get|Post|Put|Patch|Delete)\(\s*['\"]?([^'\")]*)['\"]?\)", text
        ):
            line = text[: match.start()].count("\n") + 1
            routes.append({"method": match.group(1).upper(), "path": match.group(2), "line": line})

    elif grammar_name == "java":
        import re

        for match in re.finditer(
            r"@(GetMapping|PostMapping|PutMapping|PatchMapping|DeleteMapping)\(\s*(?:value\s*=\s*)?['\"]([^'\"]*)['\"]",
            text,
        ):
            method = match.group(1).replace("Mapping", "").upper()
            line = text[: match.start()].count("\n") + 1
            routes.append({"method": method, "path": match.group(2), "line": line})

    elif grammar_name == "go":
        import re

        for match in re.finditer(
            r"\b\w+\.(GET|POST|PUT|PATCH|DELETE)\(\s*['\"]([^'\"]+)['\"]", text
        ):
            line = text[: match.start()].count("\n") + 1
            routes.append({"method": match.group(1), "path": match.group(2), "line": line})
        for match in re.finditer(
            r"type\s+(\w+)\s+struct\s*{[^}]*gorm\.Model[^}]*}", text, re.DOTALL
        ):
            models.append({"name": match.group(1), "fields": []})

    return routes, models


def _extract_non_python_symbols(
    file_path: str, content: str, grammar_name: str
) -> ExtractedSymbols:
    parser, query = _get_cached_parser_and_query(grammar_name)
    source_bytes = content.encode("utf-8")
    tree = parser.parse(source_bytes)

    symbols: list[dict] = []
    captures = query.captures(tree.root_node)

    if isinstance(captures, dict):
        capture_items = [(name, node) for name, nodes in captures.items() for node in nodes]
    else:
        capture_items = [(name, node) for node, name in captures]

    defs_by_range: dict[tuple[int, int], dict] = {}
    for name, node in capture_items:
        if name.endswith(".def"):
            key = (node.start_byte, node.end_byte)
            kind = name.split(".")[0]
            defs_by_range.setdefault(key, {"kind": kind, "node": node})
        elif name.endswith(".name"):
            for (start, end), entry in defs_by_range.items():
                if start <= node.start_byte and node.end_byte <= end:
                    entry["name_node"] = node
                    break

    kind_map = {"func": "function", "method": "method", "class": "class"}
    for entry in defs_by_range.values():
        name_node = entry.get("name_node")
        if name_node is None:
            continue
        def_node = entry["node"]
        symbols.append(
            {
                "kind": kind_map[entry["kind"]],
                "name": _node_text(name_node, source_bytes),
                "start_line": def_node.start_point[0] + 1,
                "end_line": def_node.end_point[0] + 1,
                "signature": None,
                "docstring": None,
            }
        )

    api_routes, db_models = _detect_routes_and_models(grammar_name, source_bytes)
    for route in api_routes:
        route["file_path"] = file_path
    for model in db_models:
        model["file_path"] = file_path

    return ExtractedSymbols(symbols=symbols, api_routes=api_routes, db_models=db_models)


def extract_symbols_from_file(file_path: str, content: str) -> ExtractedSymbols:
    """Parses a single file's content and returns its structural symbols.
    Language is inferred from `file_path`'s extension. Unsupported
    languages return empty results rather than raising.
    """
    ext = file_path.rsplit(".", 1)[-1].lower() if "." in file_path else ""

    if ext == "py":
        symbols = extract_python_symbols(content)
        return ExtractedSymbols(
            symbols=[s for s in symbols if s["kind"] in ("class", "function", "method")],
            api_routes=[
                {
                    "method": s["http_method"],
                    "path": s["route_path"],
                    "file_path": file_path,
                    "line": s["start_line"],
                }
                for s in symbols
                if s["kind"] == "api_route"
            ],
            db_models=[
                {"name": s["name"], "fields": s["fields"], "file_path": file_path}
                for s in symbols
                if s["kind"] == "db_model"
            ],
        )

    grammar_name = _EXTENSION_TO_GRAMMAR.get(ext)
    if grammar_name is None:
        return ExtractedSymbols(symbols=[], api_routes=[], db_models=[])

    return _extract_non_python_symbols(file_path, content, grammar_name)
