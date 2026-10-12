"""OpenAI implementation of LLMProvider.

Retry/backoff here handles TRANSPORT-level failures (rate limits, timeouts,
transient 5xxs) — a different concern from the semantic-validation retries
already implemented in each agent (app/agents/*.py), which handle "the call
succeeded but the content was wrong." Both layers retry independently:
a request can fail transport-wise, get retried here, succeed, and then
still fail semantic validation and get retried again one layer up.
"""

import asyncio
import logging
import random
from typing import AsyncIterator

from openai import APIConnectionError, APITimeoutError, AsyncOpenAI, RateLimitError

from app.core.config import get_settings
from app.llm.base import LLMMessage, LLMProvider, LLMResponse

logger = logging.getLogger(__name__)

_MAX_TRANSPORT_RETRIES = 3
_BASE_BACKOFF_SECONDS = 1.5


class OpenAIProvider(LLMProvider):
    def __init__(self, model: str | None = None, api_key: str | None = None):
        settings = get_settings()
        self.model = model or settings.LLM_MODEL
        self.embedding_model = settings.EMBEDDING_MODEL
        resolved_key = api_key or settings.OPENAI_API_KEY
        if not resolved_key:
            # Fail loudly and early rather than letting the SDK raise an
            # opaque auth error deep inside a Celery task's stack trace.
            raise RuntimeError(
                "OPENAI_API_KEY is not configured. Set it in .env before running any agent."
            )
        client_kwargs: dict[str, str] = {"api_key": resolved_key}
        if settings.OPENAI_BASE_URL:
            client_kwargs["base_url"] = settings.OPENAI_BASE_URL
        self._client = AsyncOpenAI(**client_kwargs)

    async def _with_transport_retry(self, coro_factory):
        last_exception: Exception | None = None
        for attempt in range(_MAX_TRANSPORT_RETRIES):
            try:
                return await coro_factory()
            except (RateLimitError, APITimeoutError, APIConnectionError) as exc:
                last_exception = exc
                # Exponential backoff with jitter — jitter avoids every
                # concurrent worker retrying on the exact same schedule and
                # re-colliding on the rate limit they just hit.
                delay = _BASE_BACKOFF_SECONDS * (2**attempt) + random.uniform(0, 0.5)
                logger.warning(
                    "OpenAI transport error (attempt %d/%d), retrying in %.1fs: %s",
                    attempt + 1,
                    _MAX_TRANSPORT_RETRIES,
                    delay,
                    exc,
                )
                await asyncio.sleep(delay)
        assert last_exception is not None
        raise last_exception

    async def generate(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        response_format_json: bool = False,
    ) -> LLMResponse:
        formatted_messages = [{"role": m.role, "content": m.content} for m in messages]
        if response_format_json:
            has_json_word = any("json" in (m["content"] or "").lower() for m in formatted_messages)
            if not has_json_word and formatted_messages:
                formatted_messages[-1]["content"] += "\n\nRespond in valid JSON format."

        async def call():
            return await self._client.chat.completions.create(
                model=self.model,
                messages=formatted_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"} if response_format_json else None,
            )

        response = await self._with_transport_retry(call)
        choice = response.choices[0]
        usage = response.usage

        return LLMResponse(
            content=choice.message.content or "",
            input_tokens=usage.prompt_tokens if usage else 0,
            output_tokens=usage.completion_tokens if usage else 0,
            model=response.model,
        )

    async def stream(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        # Streaming responses aren't retried transport-wise the same way as
        # generate() — once tokens have started flowing to the client
        # (Chat Agent's SSE/WebSocket consumer), restarting from scratch
        # would duplicate partial output. A transport failure mid-stream
        # instead propagates to the caller, which is expected to end the
        # turn gracefully (see Chat Agent's failure_recovery in Step 4).
        stream = await self._client.chat.completions.create(
            model=self.model,
            messages=[{"role": m.role, "content": m.content} for m in messages],
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content if chunk.choices else None
            if delta:
                yield delta

    async def embed(self, texts: list[str]) -> list[list[float]]:
        async def call():
            return await self._client.embeddings.create(model=self.embedding_model, input=texts)

        response = await self._with_transport_retry(call)
        return [item.embedding for item in response.data]


def get_llm_provider() -> LLMProvider:
    """Factory — swap the returned type to change providers app-wide."""
    return OpenAIProvider()
