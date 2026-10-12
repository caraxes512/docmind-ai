"""LLM provider abstraction.

Every agent depends on `LLMProvider`, never on `openai` directly. This is
what makes "OpenAI GPT-5.5, abstract provider layer to allow Gemini/Claude
later" (from the project brief) an actual architectural property rather
than a comment — swapping providers means writing one new subclass and
changing a single factory function, with zero changes to any of the 10
agent implementations.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, AsyncIterator, Optional


@dataclass
class LLMMessage:
    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass
class LLMResponse:
    content: str
    input_tokens: int
    output_tokens: int
    model: str
    # raw_tool_calls populated only for providers/calls that use structured
    # tool-calling instead of plain JSON-in-text (kept provider-agnostic
    # by normalizing to this shape in each subclass)
    raw_tool_calls: Optional[list[dict[str, Any]]] = None


class LLMProvider(ABC):
    """Strategy interface every concrete provider (OpenAI, Anthropic,
    Gemini) implements identically, so agent code only ever talks to this
    interface."""

    @abstractmethod
    async def generate(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        response_format_json: bool = False,
    ) -> LLMResponse:
        """Single-shot completion. `response_format_json=True` requests the
        provider's structured-output mode where available; agents that set
        this always also validate the result against a Pydantic model
        before trusting it (see each agent's `validation_rules`)."""
        raise NotImplementedError

    @abstractmethod
    async def stream(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        """Token-stream variant, used by the Chat Agent so the frontend can
        render partial answers instead of waiting for full completion."""
        raise NotImplementedError

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Batch embedding call, used exclusively by the RAG indexing
        service (Step 9) — kept on this interface rather than a separate
        one since embedding-model choice is also provider-specific."""
        raise NotImplementedError
