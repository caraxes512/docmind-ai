import uuid

from sqlalchemy import delete

from app.models.embedding import Embedding
from app.repositories.base import BaseRepository


class EmbeddingRepository(BaseRepository):
    async def replace_for_file(self, repository_file_id: uuid.UUID, entries: list[dict]) -> None:
        """`entries`: [{"chunk_index": int, "chunk_text": str, "vector_id": str,
        "metadata_json": dict}]. Deletes existing rows for this file first —
        same rationale as ParsedSymbolRepository.replace_for_file, and it
        must run in the same transaction as VectorStore.delete_for_file so
        Postgres and Qdrant never disagree about which chunks currently
        exist for a re-embedded file.
        """
        await self.db.execute(
            delete(Embedding).where(Embedding.repository_file_id == repository_file_id)
        )

        for e in entries:
            self.db.add(
                Embedding(
                    repository_file_id=repository_file_id,
                    chunk_index=e["chunk_index"],
                    chunk_text=e["chunk_text"],
                    vector_id=e["vector_id"],
                    metadata_json=e["metadata_json"],
                )
            )
        await self.db.flush()
