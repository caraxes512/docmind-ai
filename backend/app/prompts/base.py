"""Shared prompt specification structure.

Every agent's prompt is defined as a `PromptSpec` instance rather than a
bare string. This forces each agent's prompt design to explicitly address:
system framing, the per-call developer/task prompt template, the expected
input contract, the expected output contract (usually JSON schema-shaped
for reliable parsing), validation rules the caller must apply post-hoc,
and a failure-recovery strategy — rather than leaving these as tribal
knowledge scattered across agent code.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class PromptSpec:
    agent_name: str
    system_prompt: str
    developer_prompt_template: str  # .format(**kwargs) at call time
    expected_inputs: list[str]
    expected_output_schema: str  # human-readable description of the JSON/Markdown shape
    validation_rules: list[str]
    failure_recovery: str

    def render_developer_prompt(self, **kwargs) -> str:
        return self.developer_prompt_template.format(**kwargs)
