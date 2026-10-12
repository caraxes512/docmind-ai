"""Embedding generation — batches chunk text through the LLM provider's
embed() method. Batching matters because embedding APIs cap how many
input strings a single request accepts; a repository with thousands of
chunks must not be sent as one call.
"""

from dataclasses import dataclass

from app.llm.base import LLMProvider
from app.rag.chunking import Chunk

EMBEDDING_BATCH_SIZE = 100


@dataclass
class EmbeddedChunk:
    chunk: Chunk
    vector: list[float]


async def embed_chunks(chunks: list[Chunk], llm: LLMProvider) -> list[EmbeddedChunk]:
    if not chunks:
        return []

    embedded: list[EmbeddedChunk] = []
    for batch_start in range(0, len(chunks), EMBEDDING_BATCH_SIZE):
        batch = chunks[batch_start : batch_start + EMBEDDING_BATCH_SIZE]
        vectors = await llm.embed([c.content for c in batch])
        embedded.extend(
            EmbeddedChunk(chunk=chunk, vector=vector) for chunk, vector in zip(batch, vectors)
        )

    return embedded
