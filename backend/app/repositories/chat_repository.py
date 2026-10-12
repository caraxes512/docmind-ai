import uuid
from typing import Optional

from sqlalchemy import select

from app.core.exceptions import NotFoundError
from app.models.chat import Chat
from app.models.enums import MessageRole
from app.models.message import Message
from app.models.project import Project
from app.models.repository import Repository
from app.repositories.base import BaseRepository


class ChatRepository(BaseRepository):
    async def _assert_repository_owned(self, user_id: uuid.UUID, repository_id: uuid.UUID) -> None:
        result = await self.db.execute(
            select(Repository.id)
            .join(Project, Repository.project_id == Project.id)
            .where(Repository.id == repository_id, Project.user_id == user_id)
        )
        if result.scalar_one_or_none() is None:
            raise NotFoundError(f"Repository {repository_id} not found")

    async def create_chat(
        self, user_id: uuid.UUID, repository_id: uuid.UUID, title: Optional[str]
    ) -> Chat:
        await self._assert_repository_owned(user_id, repository_id)
        chat = Chat(repository_id=repository_id, user_id=user_id, title=title)
        self.db.add(chat)
        await self.db.flush()
        return chat

    async def list_chats(self, user_id: uuid.UUID, repository_id: uuid.UUID) -> list[Chat]:
        await self._assert_repository_owned(user_id, repository_id)
        result = await self.db.execute(
            select(Chat)
            .where(Chat.repository_id == repository_id, Chat.user_id == user_id)
            .order_by(Chat.updated_at.desc())
        )
        return list(result.scalars().all())

    async def get_owned(self, user_id: uuid.UUID, chat_id: uuid.UUID) -> Chat:
        result = await self.db.execute(
            select(Chat).where(Chat.id == chat_id, Chat.user_id == user_id)
        )
        chat = result.scalar_one_or_none()
        if chat is None:
            raise NotFoundError(f"Chat {chat_id} not found")
        return chat

    async def list_messages(self, user_id: uuid.UUID, chat_id: uuid.UUID) -> list[Message]:
        await self.get_owned(user_id, chat_id)
        result = await self.db.execute(
            select(Message).where(Message.chat_id == chat_id).order_by(Message.created_at)
        )
        return list(result.scalars().all())

    async def add_message(
        self, chat_id: uuid.UUID, role: MessageRole, content: str, citations: Optional[list] = None
    ) -> Message:
        message = Message(chat_id=chat_id, role=role, content=content, citations=citations or [])
        self.db.add(message)
        await self.db.flush()
        return message
