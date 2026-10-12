"""Prompt spec for the Database Documentation Agent. Only invoked when
RepositorySummary.has_database is true."""

from app.prompts.base import PromptSpec

DATABASE_DOC_AGENT_PROMPT = PromptSpec(
    agent_name="database_documentation_agent",
    system_prompt=(
        "You document a database schema for engineers who need to understand table structure and "
        "relationships without reading ORM source directly. You are given parsed model/table "
        "definitions (field names, types, constraints, foreign keys) extracted by the Parser Agent. "
        "Document only fields and relationships present in the input."
    ),
    developer_prompt_template=(
        "Detected database models:\n{db_models_json}\n\n"
        "For each model, produce: table name, field list (name, type, constraints), and "
        "relationships to other models (foreign keys, one-to-many, many-to-many where determinable "
        "from the ORM's relationship declarations). Note any field-level indexes or unique "
        "constraints found in the input."
    ),
    expected_inputs=["db_models_json"],
    expected_output_schema="Markdown document — one section per model/table",
    validation_rules=[
        "Every field documented must exist verbatim in db_models_json for that model",
        "A relationship may only be documented if both referenced models appear in db_models_json",
    ],
    failure_recovery=(
        "If db_models_json is empty despite has_database=true (e.g. a raw-SQL-only codebase with no "
        "ORM models to statically parse), skip LLM generation and instead emit a short static note: "
        "'Database usage detected via dependency manifest, but no ORM model definitions were found "
        "to document automatically.' — avoids hallucinating a schema from nothing."
    ),
)
