"""Prompt spec for the Diagram Generator Agent.

Consumes structured `diagram_request` notes from the Architecture Agent
(and, for ER diagrams, db_models from the Parser Agent) rather than raw
source — diagram generation is a rendering/formatting task once the
relationships are known, not a discovery task.
"""

from app.prompts.base import PromptSpec

DIAGRAM_AGENT_PROMPT = PromptSpec(
    agent_name="diagram_generator_agent",
    system_prompt=(
        "You convert structured relationship data into valid Mermaid.js diagram syntax. You do not "
        "invent nodes or relationships beyond what is given in the input. You know Mermaid syntax for "
        "flowchart, classDiagram, erDiagram, sequenceDiagram, and component-style graph diagrams "
        "(using `graph TD`/`graph LR` with subgraphs for containment). Always validate that your "
        "output starts with a valid Mermaid diagram type declaration."
    ),
    developer_prompt_template=(
        "Diagram type requested: {diagram_type}\n"
        "Input structure:\n{structured_input_json}\n\n"
        "Produce ONLY the Mermaid diagram source (no markdown code fence, no prose before or after). "
        "Use sentence-case labels. Keep node labels under 40 characters — truncate long names to a "
        "meaningful short form rather than omitting nodes."
    ),
    expected_inputs=["diagram_type", "structured_input_json"],
    expected_output_schema="Raw Mermaid.js source as plain text (first line is the diagram type declaration)",
    validation_rules=[
        "First non-empty line must match one of: flowchart, graph, classDiagram, erDiagram, sequenceDiagram",
        "Every node/entity referenced in an edge/relationship line must be declared as a node — "
        "orphan edges are stripped before persisting",
        "Reject output containing markdown code fences (```) — strip if present rather than failing outright",
    ],
    failure_recovery=(
        "On invalid Mermaid syntax (checked via a lightweight regex/parse validation, not a full "
        "Mermaid parser): retry once with the specific syntax violation quoted back to the model. "
        "On second failure: fall back to a plain bullet-list textual description of the same "
        "relationships instead of a diagram, so the documentation page never shows a broken diagram block."
    ),
)
