"""Chat service. Chat/message CRUD (Step 5) plus, as of Step 9, `ask` —
retrieval-augmented generation via QdrantRetriever + the Chat Agent."""

import uuid

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.chat_agent import run_chat_agent
from app.db.session import get_db
from app.llm.openai_provider import get_llm_provider
from app.models.chat import Chat
from app.models.enums import MessageRole
from app.models.message import Message
from app.rag.retriever import QdrantRetriever
from app.rag.vector_store import get_vector_store
from app.repositories.chat_repository import ChatRepository
from app.repositories.usage_log_repository import UsageLogRepository


class ChatService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.chat_repo = ChatRepository(db)
        self.usage_log_repo = UsageLogRepository(db)
        self.llm = get_llm_provider()
        self.retriever = QdrantRetriever(get_vector_store(), self.llm)

    async def create_chat(
        self, user_id: uuid.UUID, repository_id: uuid.UUID, title: str | None
    ) -> Chat:
        chat = await self.chat_repo.create_chat(user_id, repository_id, title)
        await self.db.commit()
        return chat

    async def list_chats(self, user_id: uuid.UUID, repository_id: uuid.UUID) -> list[Chat]:
        return await self.chat_repo.list_chats(user_id, repository_id)

    async def get_chat(self, user_id: uuid.UUID, chat_id: uuid.UUID) -> Chat:
        return await self.chat_repo.get_owned(user_id, chat_id)

    async def list_messages(self, user_id: uuid.UUID, chat_id: uuid.UUID) -> list[Message]:
        return await self.chat_repo.list_messages(user_id, chat_id)

    async def ask(
        self, user_id: uuid.UUID, chat_id: uuid.UUID, content: str
    ) -> tuple[Message, Message]:
        chat = await self.chat_repo.get_owned(user_id, chat_id)

        # The user's question is persisted regardless of whether generation
        # succeeds — per the Chat Agent's failure_recovery, a question should
        # never be silently lost even if the assistant can't answer.
        user_message = await self.chat_repo.add_message(chat.id, MessageRole.USER, content)
        await self.db.commit()

        history = await self.chat_repo.list_messages(user_id, chat_id)
        conversation_history = [
            {"role": m.role.value, "content": m.content}
            for m in history[-10:]  # last 10 turns of context
        ]

        try:
            answer_text, cited_chunks, usage_log = await run_chat_agent(
                repository_id=str(chat.repository_id),
                conversation_history=conversation_history,
                user_question=content,
                retriever=self.retriever,
                llm=self.llm,
            )
            citations = [
                {
                    "file_path": c.file_path,
                    "start_line": c.start_line,
                    "end_line": c.end_line,
                    "similarity_score": c.similarity_score,
                }
                for c in cited_chunks
            ]
        except Exception:  # noqa: BLE001 -- per Chat Agent's failure_recovery: degrade gracefully, don't 500
            answer_text = "I couldn't generate an answer right now — please try again."
            citations = []
            usage_log = []

        assistant_message = await self.chat_repo.add_message(
            chat.id, MessageRole.ASSISTANT, answer_text, citations
        )
        await self.usage_log_repo.bulk_insert(None, usage_log)
        await self.db.commit()

        return user_message, assistant_message


def get_chat_service(db: AsyncSession = Depends(get_db)) -> ChatService:
    return ChatService(db)
