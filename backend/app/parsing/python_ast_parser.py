"""Python AST-based symbol extraction.

Per Step 1's design: Python AST is used as the PRIMARY mechanism for .py
files, not merely a "secondary validator" as originally sketched — since
Python's stdlib `ast` module handles decorators, type hints, and nested
classes/functions more precisely than a generic Tree-sitter grammar would,
and it requires no external grammar dependency at all. Tree-sitter
(tree_sitter_parser.py) handles the other five languages, where no
equivalent stdlib AST exists.
"""

import ast
from typing import Optional, TypedDict

# Decorator name fragments that indicate an HTTP route in common Python
# web frameworks (FastAPI, Flask, Django REST Framework's @api_view).
_ROUTE_DECORATOR_METHODS = {
    "get": "GET",
    "post": "POST",
    "put": "PUT",
    "patch": "PATCH",
    "delete": "DELETE",
    "route": "GET",  # Flask's @app.route defaults to GET
}

# Base class name fragments indicating an ORM model (checked by substring,
# since the actual base could be imported/aliased many ways: `Base`,
# `db.Model`, `models.Model`).
_ORM_BASE_HINTS = {"Base", "Model"}


class ExtractedSymbol(TypedDict):
    kind: str
    name: str
    start_line: int
    end_line: int
    signature: Optional[str]
    docstring: Optional[str]
    http_method: Optional[str]
    route_path: Optional[str]
    fields: Optional[list]


def _get_decorator_name(decorator: ast.expr) -> str:
    """Returns the dotted name of a decorator, e.g. 'app.get' from
    `@app.get("/users")`, or 'staticmethod' from `@staticmethod`."""
    if isinstance(decorator, ast.Call):
        return _get_decorator_name(decorator.func)
    if isinstance(decorator, ast.Attribute):
        base = _get_decorator_name(decorator.value)
        return f"{base}.{decorator.attr}" if base else decorator.attr
    if isinstance(decorator, ast.Name):
        return decorator.id
    return ""


def _get_decorator_first_string_arg(decorator: ast.expr) -> Optional[str]:
    if isinstance(decorator, ast.Call) and decorator.args:
        first_arg = decorator.args[0]
        if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
            return first_arg.value
    return None


def _build_signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    args = [a.arg for a in node.args.args]
    prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
    return f"{prefix} {node.name}({', '.join(args)})"


def _extract_route_from_decorators(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> Optional[tuple[str, str]]:
    for decorator in node.decorator_list:
        dotted = _get_decorator_name(decorator)
        method_fragment = dotted.rsplit(".", 1)[-1].lower()
        if method_fragment in _ROUTE_DECORATOR_METHODS:
            path = _get_decorator_first_string_arg(decorator) or ""
            return _ROUTE_DECORATOR_METHODS[method_fragment], path
    return None


def _extract_orm_fields(class_node: ast.ClassDef) -> Optional[list[dict]]:
    """Looks for `name = Column(...)`-shaped or `name: Mapped[...] =
    mapped_column(...)`-shaped class-body assignments — covers both
    classic SQLAlchemy Column() declarations and 2.0-style Mapped columns."""
    is_orm_model = any(
        (isinstance(base, ast.Name) and base.id in _ORM_BASE_HINTS)
        or (isinstance(base, ast.Attribute) and base.attr in _ORM_BASE_HINTS)
        for base in class_node.bases
    )
    if not is_orm_model:
        return None

    fields = []
    for item in class_node.body:
        field_name = None
        if (
            isinstance(item, ast.Assign)
            and len(item.targets) == 1
            and isinstance(item.targets[0], ast.Name)
        ):
            field_name = item.targets[0].id
        elif isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
            field_name = item.target.id

        if field_name and not field_name.startswith("_") and field_name != "__tablename__":
            fields.append({"name": field_name})

    return fields if fields else None


class _SymbolVisitor(ast.NodeVisitor):
    """Tracks whether we're currently inside a class body, so a function
    defined there is tagged 'method' rather than 'function' — ast.walk()
    alone can't make this distinction since it has no parent context.
    """

    def __init__(self) -> None:
        self.symbols: list[ExtractedSymbol] = []
        self._class_depth = 0

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.symbols.append(
            ExtractedSymbol(
                kind="class",
                name=node.name,
                start_line=node.lineno,
                end_line=getattr(node, "end_lineno", node.lineno),
                signature=f"class {node.name}",
                docstring=ast.get_docstring(node),
                http_method=None,
                route_path=None,
                fields=None,
            )
        )

        orm_fields = _extract_orm_fields(node)
        if orm_fields is not None:
            self.symbols.append(
                ExtractedSymbol(
                    kind="db_model",
                    name=node.name,
                    start_line=node.lineno,
                    end_line=getattr(node, "end_lineno", node.lineno),
                    signature=None,
                    docstring=None,
                    http_method=None,
                    route_path=None,
                    fields=orm_fields,
                )
            )

        self._class_depth += 1
        self.generic_visit(node)
        self._class_depth -= 1

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        route = _extract_route_from_decorators(node)
        is_method = self._class_depth > 0
        self.symbols.append(
            ExtractedSymbol(
                kind="api_route" if route else ("method" if is_method else "function"),
                name=node.name,
                start_line=node.lineno,
                end_line=getattr(node, "end_lineno", node.lineno),
                signature=_build_signature(node),
                docstring=ast.get_docstring(node),
                http_method=route[0] if route else None,
                route_path=route[1] if route else None,
                fields=None,
            )
        )
        # Deliberately not calling self.generic_visit(node) here — a nested
        # function/closure defined inside this one's body isn't
        # documentation-worthy on its own, and skipping the descent is what
        # keeps it out of the symbol list (NodeVisitor only recurses into
        # a node's children when generic_visit is called for it).

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function(node)


def extract_python_symbols(content: str) -> list[ExtractedSymbol]:
    """Parses Python source and returns classes, functions, methods, API
    routes (detected via decorator), and DB models (detected via ORM base
    class + Column/mapped_column-shaped assignments) as a flat symbol list.
    Raises SyntaxError on unparseable content — caller (parser orchestration
    in the ingestion task) catches this per-file so one bad file doesn't
    abort the whole repository's parse.
    """
    tree = ast.parse(content)
    visitor = _SymbolVisitor()
    visitor.visit(tree)
    return visitor.symbols
