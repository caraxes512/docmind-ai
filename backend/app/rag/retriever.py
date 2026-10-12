"""Retriever — the concrete implementation of the `Retriever` protocol
that app/agents/chat_agent.py declared back in Step 4 (retrieve() ->
list[RetrievedChunk]). Embeds the query, searches Qdrant filtered by
repository_id, and maps results back to the shape the Chat Agent expects.
"""

from app.agents.chat_agent import RetrievedChunk
from app.llm.base import LLMProvider
from app.rag.vector_store import VectorStore

SIMILARITY_THRESHOLD = 0.5  # below this, a match is likely noise, not signal


class QdrantRetriever:
    def __init__(self, vector_store: VectorStore, llm: LLMProvider):
        self.vector_store = vector_store
        self.llm = llm

    async def retrieve(
        self, repository_id: str, query: str, top_k: int = 8
    ) -> list[RetrievedChunk]:
        query_vectors = await self.llm.embed([query])
        query_vector = query_vectors[0]

        results = await self.vector_store.search(query_vector, repository_id, top_k)

        chunks = []
        for r in results:
            if r.score < SIMILARITY_THRESHOLD:
                continue
            payload = r.payload
            chunks.append(
                RetrievedChunk(
                    file_path=payload.get("file_path", "unknown"),
                    start_line=payload.get("start_line", 0),
                    end_line=payload.get("end_line", 0),
                    content=payload.get("content", ""),
                    similarity_score=r.score,
                )
            )
        return chunks
