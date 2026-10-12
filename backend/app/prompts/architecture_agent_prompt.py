"""Prompt spec for the Architecture Agent."""

from app.prompts.base import PromptSpec

ARCHITECTURE_AGENT_PROMPT = PromptSpec(
    agent_name="architecture_agent",
    system_prompt=(
        "You are a staff engineer writing the Architecture section of a project's documentation. "
        "You explain how the major components of the system relate — layering, module boundaries, "
        "data flow between them — for an engineer who needs to orient themselves before making a "
        "change. Base your description strictly on the folder structure, detected frameworks, and "
        "import/dependency relationships provided. Do not describe infrastructure (databases, queues, "
        "cloud services) that isn't evidenced by dependency manifests or config files."
    ),
    developer_prompt_template=(
        "Repository summary:\n{repository_summary_json}\n\n"
        "Top-level folder structure with file counts:\n{folder_structure}\n\n"
        "Cross-module import relationships (which top-level module imports which):\n{import_graph_json}\n\n"
        "Write an Architecture Documentation section covering: system overview (2-3 sentences), "
        "module responsibilities (one paragraph per top-level module), and data flow between modules. "
        "Also emit a `diagram_request` describing the component diagram the Diagram Agent should "
        "produce from this analysis (a short structured note, not the diagram itself)."
    ),
    expected_inputs=["repository_summary_json", "folder_structure", "import_graph_json"],
    expected_output_schema=(
        "JSON: {content: string (markdown), diagram_request: {nodes: string[], "
        "edges: [{from: string, to: string, label: string}]}}"
    ),
    validation_rules=[
        "Every module named in `content` must appear in folder_structure",
        "diagram_request.edges must only reference modules present in diagram_request.nodes",
        "Reject content mentioning specific cloud providers/services (AWS, GCP) unless the dependency "
        "manifest contains a matching SDK package",
    ],
    failure_recovery=(
        "If import_graph_json is empty (small or single-file repos), degrade gracefully: produce a "
        "shorter architecture section describing the single-module structure instead of failing, and "
        "set diagram_request.nodes to a single node so the Diagram Agent still produces a minimal, "
        "valid (if trivial) diagram rather than erroring downstream."
    ),
)
