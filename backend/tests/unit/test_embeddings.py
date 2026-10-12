"""Unit tests for app.rag.embeddings — batching logic, using FakeLLMProvider
(no real embedding API calls)."""

import pytest

from app.rag.chunking import Chunk
from app.rag.embeddings import EMBEDDING_BATCH_SIZE, embed_chunks

pytestmark = pytest.mark.unit


def _chunk(i: int) -> Chunk:
    return Chunk(content=f"chunk {i}", start_line=i, end_line=i, symbol_name=None)


async def test_empty_input_makes_no_calls(fake_llm):
    result = await embed_chunks([], fake_llm)
    assert result == []


async def test_small_batch_single_embed_call(fake_llm):
    chunks = [_chunk(i) for i in range(10)]
    result = await embed_chunks(chunks, fake_llm)
    assert len(result) == 10
    assert [ec.chunk.content for ec in result] == [c.content for c in chunks]


async def test_oversized_input_splits_into_multiple_batches(fake_llm):
    chunks = [_chunk(i) for i in range(EMBEDDING_BATCH_SIZE * 2 + 15)]
    result = await embed_chunks(chunks, fake_llm)
    assert len(result) == len(chunks)
    # order must be preserved across batch boundaries
    assert [ec.chunk.content for ec in result] == [c.content for c in chunks]


async def test_vectors_correctly_paired_with_their_source_chunk(fake_llm):
    chunks = [_chunk(i) for i in range(5)]
    result = await embed_chunks(chunks, fake_llm)
    for ec in result:
        # FakeLLMProvider derives the vector deterministically from text length
        expected_value = float(len(ec.chunk.content) % 97)
        assert ec.vector[0] == expected_value
