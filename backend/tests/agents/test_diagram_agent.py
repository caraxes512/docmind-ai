"""Tests for app.agents.diagram_agent — Mermaid syntax validation and the
generate-validate-retry flow."""

import pytest

from app.agents.diagram_agent import _generate_one_diagram, _validate_mermaid

pytestmark = pytest.mark.agents


@pytest.mark.parametrize(
    "source",
    [
        "erDiagram\n  USER ||--o{ ORDER : places",
        "graph TD\n  A --> B",
        "flowchart LR\n  A --> B",
        "classDiagram\n  class Foo",
        "sequenceDiagram\n  A->>B: hello",
    ],
)
def test_valid_mermaid_diagrams_pass_validation(source):
    assert _validate_mermaid(source) == []


@pytest.mark.parametrize(
    "source",
    [
        "not a diagram at all",
        "```mermaid\nerDiagram\n```",  # code fence should have been stripped upstream, not present here
        "",
    ],
)
def test_invalid_mermaid_diagrams_fail_validation(source):
    assert len(_validate_mermaid(source)) == 1


async def test_generate_one_diagram_retries_once_on_invalid_syntax_then_succeeds(fake_llm):
    fake_llm.responses = ["this is not mermaid", "erDiagram\n  A ||--o{ B : has"]
    content, errors, usage = await _generate_one_diagram("erDiagram", {"models": []}, fake_llm)
    assert content == "erDiagram\n  A ||--o{ B : has"
    assert len(fake_llm.calls) == 2
    assert len(errors) == 1  # the first (failed) attempt is recorded


async def test_generate_one_diagram_gives_up_after_two_failures(fake_llm):
    fake_llm.responses = ["invalid", "still invalid"]
    content, errors, usage = await _generate_one_diagram("erDiagram", {"models": []}, fake_llm)
    assert content is None
    assert len(fake_llm.calls) == 2
    assert len(errors) == 2
