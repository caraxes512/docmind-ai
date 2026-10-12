"""Prompt spec for the Documentation Reviewer Agent — the fan-in node that
reviews all generated documents and assigns a quality score."""

from app.prompts.base import PromptSpec

REVIEWER_AGENT_PROMPT = PromptSpec(
    agent_name="documentation_reviewer_agent",
    system_prompt=(
        "You are a documentation quality reviewer. You are strict but fair: you flag concrete, "
        "specific problems (a broken-looking internal link, a parameter mentioned in prose but "
        "missing from a table, a claim with no supporting evidence in the source material) rather "
        "than generic style feedback. You assign a 0-100 quality score per document based on "
        "completeness, internal consistency, and the presence of concrete examples."
    ),
    developer_prompt_template=(
        "Document type: {doc_type}\n"
        "Document content:\n{document_content}\n\n"
        "Cross-reference material available for consistency checks (parsed symbols / API routes / "
        "db models relevant to this doc type):\n{cross_reference_json}\n\n"
        "Return a JSON object: {{score: number 0-100, issues: [{{type: string, location: string|null, "
        "severity: 'low'|'medium'|'high', description: string}}]}}. Valid issue types: "
        "missing_documentation, broken_link, inconsistent_description, outdated_api, missing_parameter, "
        "missing_example."
    ),
    expected_inputs=["doc_type", "document_content", "cross_reference_json"],
    expected_output_schema="JSON: {score: number, issues: ReviewIssue[]}",
    validation_rules=[
        "score must be between 0 and 100 inclusive",
        "issue.type must be one of the six enumerated values — unrecognized types are coerced to "
        "'inconsistent_description' with the original type appended to the description",
        "A document under 100 characters is auto-scored 0 with a single missing_documentation issue, "
        "bypassing the LLM call entirely (cost optimization for a case with an obvious answer)",
    ],
    failure_recovery=(
        "On JSON parse failure: retry once. On second failure: persist score=0 with a single "
        "missing_documentation issue (severity=high, description='Automated review could not complete "
        "for this document; requires manual review') — reuses the existing six issue types rather than "
        "introducing a seventh, and the description text is what distinguishes 'review failed' from a "
        "genuinely reviewed-and-scored-zero document in the UI and in quality trend reporting."
    ),
)
