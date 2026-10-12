"""Qdrant vector store wrapper.

VERIFICATION CAVEAT: like tree_sitter_parser.py, this cannot be executed
in this sandbox (no network to install `qdrant-client` or run a Qdrant
instance). Written against the documented AsyncQdrantClient API; needs a
real Qdrant instance to confirm before production use.

Payload filtering by repository_id (and file_path, for targeted deletes)
is the mechanism that makes incremental re-indexing possible -- this was
the entire reason Qdrant was chosen over FAISS/ChromaDB back in Step 1.
"""

import uuid
from dataclasses import dataclass

from qdrant_client import AsyncQdrantClient, models

from app.core.config import get_settings

EMBEDDING_DIMENSIONS = 3072  # text-embedding-3-large (set in openai_provider.py)


@dataclass
class VectorSearchResult:
    point_id: str
    score: float
    payload: dict


class VectorStore:
    def __init__(self):
        settings = get_settings()
        self._client = AsyncQdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)
        self._collection_name = settings.QDRANT_COLLECTION_NAME

    async def ensure_collection(self) -> None:
        """Idempotent -- safe to call before every write, cheap no-op if
        the collection already exists with matching config."""
        collections = await self._client.get_collections()
        if any(c.name == self._collection_name for c in collections.collections):
            return
        await self._client.create_collection(
            collection_name=self._collection_name,
            vectors_config=models.VectorParams(
                size=EMBEDDING_DIMENSIONS, distance=models.Distance.COSINE
            ),
        )

    async def delete_for_file(self, repository_id: str, file_path: str) -> None:
        """Deletes all existing points for one file -- called before
        re-embedding a changed file, so a re-index never leaves stale
        vectors from the file's previous content alongside the new ones."""
        await self._client.delete(
            collection_name=self._collection_name,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="repository_id", match=models.MatchValue(value=repository_id)
                        ),
                        models.FieldCondition(
                            key="file_path", match=models.MatchValue(value=file_path)
                        ),
                    ]
                )
            ),
        )

    async def upsert(self, points: list[dict]) -> None:
        """`points`: [{"id": str, "vector": list[float], "payload": dict}].
        payload must include at minimum repository_id and file_path for
        filtering (delete_for_file, search) to work."""
        if not points:
            return
        await self._client.upsert(
            collection_name=self._collection_name,
            points=[
                models.PointStruct(id=p["id"], vector=p["vector"], payload=p["payload"])
                for p in points
            ],
        )

    async def search(
        self, query_vector: list[float], repository_id: str, top_k: int = 8
    ) -> list[VectorSearchResult]:
        results = await self._client.search(
            collection_name=self._collection_name,
            query_vector=query_vector,
            query_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="repository_id", match=models.MatchValue(value=repository_id)
                    ),
                ]
            ),
            limit=top_k,
        )
        return [
            VectorSearchResult(point_id=str(r.id), score=r.score, payload=r.payload or {})
            for r in results
        ]


def new_point_id() -> str:
    return str(uuid.uuid4())


def get_vector_store() -> VectorStore:
    return VectorStore()
