"""Unit tests for app.parsing.python_ast_parser.

Logic verified against these exact assertions during Step 9 development
via a manual harness (pytest wasn't installable in that sandbox either) —
see the Step 9 summary for the raw run output. Formalized here as the
tests that should run in CI once dependencies are installed.
"""

import pytest

from app.parsing.python_ast_parser import extract_python_symbols

pytestmark = pytest.mark.unit


def test_class_detected():
    symbols = extract_python_symbols("class Foo:\n    pass\n")
    classes = [s for s in symbols if s["kind"] == "class"]
    assert len(classes) == 1
    assert classes[0]["name"] == "Foo"


def test_orm_model_emits_both_class_and_db_model_symbols(sample_python_file_content):
    symbols = extract_python_symbols(sample_python_file_content)
    user_symbols = [s for s in symbols if s["name"] == "User"]
    assert {s["kind"] for s in user_symbols} == {"class", "db_model"}


def test_db_model_captures_orm_fields(sample_python_file_content):
    symbols = extract_python_symbols(sample_python_file_content)
    db_model = next(s for s in symbols if s["name"] == "User" and s["kind"] == "db_model")
    field_names = {f["name"] for f in db_model["fields"]}
    assert field_names == {"id", "email"}


def test_method_inside_class_tagged_as_method_not_function(sample_python_file_content):
    symbols = extract_python_symbols(sample_python_file_content)
    display_name = next(s for s in symbols if s["name"] == "display_name")
    assert display_name["kind"] == "method"


def test_top_level_function_tagged_as_function():
    source = "def helper(x, y):\n    return x + y\n"
    symbols = extract_python_symbols(source)
    helper = next(s for s in symbols if s["name"] == "helper")
    assert helper["kind"] == "function"


def test_nested_closure_not_extracted():
    """Nested functions inside a function body aren't documentation-worthy
    on their own and are deliberately not visited."""
    source = "def outer(x):\n    def inner():\n        return x\n    return inner()\n"
    symbols = extract_python_symbols(source)
    assert "inner" not in {s["name"] for s in symbols}


def test_fastapi_route_decorator_detected(sample_python_file_content):
    symbols = extract_python_symbols(sample_python_file_content)
    route = next(s for s in symbols if s["name"] == "get_user")
    assert route["kind"] == "api_route"
    assert route["http_method"] == "GET"
    assert route["route_path"] == "/users/{user_id}"


@pytest.mark.parametrize(
    "decorator,expected_method",
    [
        ("@router.get('/x')", "GET"),
        ("@router.post('/x')", "POST"),
        ("@app.put('/x')", "PUT"),
        ("@app.delete('/x')", "DELETE"),
    ],
)
def test_route_methods_detected_correctly(decorator, expected_method):
    source = f"{decorator}\ndef handler():\n    pass\n"
    symbols = extract_python_symbols(source)
    route = next(s for s in symbols if s["name"] == "handler")
    assert route["http_method"] == expected_method


def test_docstring_captured(sample_python_file_content):
    symbols = extract_python_symbols(sample_python_file_content)
    route = next(s for s in symbols if s["name"] == "get_user")
    assert route["docstring"] == "Fetch a user by id."


def test_non_orm_class_has_no_db_model_symbol():
    source = "class PlainClass:\n    def method(self):\n        pass\n"
    symbols = extract_python_symbols(source)
    assert not any(s["kind"] == "db_model" for s in symbols)


def test_raises_syntax_error_on_unparseable_content():
    with pytest.raises(SyntaxError):
        extract_python_symbols("def broken(:\n")
