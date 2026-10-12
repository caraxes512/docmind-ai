"""Shared pytest fixtures. Test tiers (see pytest.ini markers):

- unit: pure logic, no I/O — python_ast_parser, dependency_extractor,
  chunking, embeddings batching, zip_extraction security, security utils.
  These run with zero external dependencies beyond stdlib + cryptography.
- agents: agent node functions driven by FakeLLMProvider — no real OpenAI
  calls, no DB, no LangGraph execution (individual node functions are
  plain async functions and are tested directly, not through the compiled
  graph — graph wiring itself is covered by tests/agents/test_graph_routing.py
  which tests the routing function in isolation, also without LangGraph).
- api: FastAPI TestClient against the real app with service-layer
  dependencies overridden (fastapi.testclient + app.dependency_overrides) —
  tests routing, status codes, auth enforcement, schema validation. Does
  NOT hit a real database.
- integration: real Postgres required. See tests/integration/README.md.
"""

import uuid
from dataclasses import dataclass, field
from typing import AsyncIterator

import pytest

from app.llm.base import LLMMessage, LLMProvider, LLMResponse


@dataclass
class FakeLLMProvider(LLMProvider):
    """Scriptable fake used throughout unit/agents tests. Queue responses
    via `responses`; each call to generate() pops the next one. Raises
    AssertionError (not IndexError) if more calls happen than scripted —
    a clearer failure message when a test's call-count assumption is wrong.
    """

    responses: list[str] = field(default_factory=list)
    embedding_dimension: int = 8
    calls: list[list[LLMMessage]] = field(default_factory=list)

    async def generate(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        response_format_json: bool = False,
    ) -> LLMResponse:
        self.calls.append(messages)
        if not self.responses:
            raise AssertionError(
                f"FakeLLMProvider.generate() called but no more responses were queued "
                f"(call #{len(self.calls)})"
            )
        content = self.responses.pop(0)
        return LLMResponse(content=content, input_tokens=42, output_tokens=17, model="fake-model")

    async def stream(
        self, messages: list[LLMMessage], *, temperature: float = 0.2, max_tokens: int = 4096
    ) -> AsyncIterator[str]:
        yield "unused-in-tests"

    async def embed(self, texts: list[str]) -> list[list[float]]:
        # Deterministic pseudo-embedding (length-derived), not semantically
        # meaningful — sufficient for tests that check batching/plumbing,
        # not tests that check actual retrieval relevance.
        return [[float(len(t) % 97)] * self.embedding_dimension for t in texts]


@pytest.fixture
def fake_llm() -> FakeLLMProvider:
    return FakeLLMProvider()


@pytest.fixture
def sample_repository_id() -> str:
    return str(uuid.uuid4())


@pytest.fixture
def sample_python_file_content() -> str:
    return '''
from fastapi import APIRouter
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base

router = APIRouter()


class User(Base):
    """A user account."""
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column()

    def display_name(self) -> str:
        """Returns a friendly display name."""
        return self.email


@router.get("/users/{user_id}")
async def get_user(user_id: int):
    """Fetch a user by id."""
    return {"id": user_id}
'''
