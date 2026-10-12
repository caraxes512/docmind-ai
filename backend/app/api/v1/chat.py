"""Repository chat (RAG Q&A) endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.chat import AskResponse, ChatCreate, ChatRead, MessageCreate, MessageRead
from app.services.chat_service import ChatService, get_chat_service

router = APIRouter(tags=["chat"])


@router.post(
    "/repositories/{repository_id}/chats",
    response_model=ChatRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_chat(
    repository_id: UUID,
    body: ChatCreate,
    current_user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
) -> ChatRead:
    chat = await service.create_chat(current_user.id, repository_id, body.title)
    return ChatRead.model_validate(chat)


@router.get("/repositories/{repository_id}/chats", response_model=list[ChatRead])
async def list_chats(
    repository_id: UUID,
    current_user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
) -> list[ChatRead]:
    chats = await service.list_chats(current_user.id, repository_id)
    return [ChatRead.model_validate(c) for c in chats]


@router.get("/chats/{chat_id}", response_model=ChatRead)
async def get_chat(
    chat_id: UUID,
    current_user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
) -> ChatRead:
    chat = await service.get_chat(current_user.id, chat_id)
    return ChatRead.model_validate(chat)


@router.get("/chats/{chat_id}/messages", response_model=list[MessageRead])
async def list_messages(
    chat_id: UUID,
    current_user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
) -> list[MessageRead]:
    messages = await service.list_messages(current_user.id, chat_id)
    return [MessageRead.model_validate(m) for m in messages]


@router.post(
    "/chats/{chat_id}/messages", response_model=AskResponse, status_code=status.HTTP_201_CREATED
)
async def ask(
    chat_id: UUID,
    body: MessageCreate,
    current_user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
) -> AskResponse:
    user_message, assistant_message = await service.ask(current_user.id, chat_id, body.content)
    return AskResponse(
        user_message=MessageRead.model_validate(user_message),
        assistant_message=MessageRead.model_validate(assistant_message),
    )
