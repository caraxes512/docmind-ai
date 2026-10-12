"""Repository chat (RAG Q&A) schemas."""

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.enums import MessageRole
from app.schemas.common import ORMBase


class ChatCreate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)


class ChatRead(ORMBase):
    id: uuid.UUID
    repository_id: uuid.UUID
    title: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class Citation(BaseModel):
    file_path: str
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    similarity_score: float = Field(..., ge=0.0, le=1.0)


class MessageCreate(BaseModel):
    """User's question. The assistant's reply is generated synchronously
    within the same request (RAG retrieval + LLM call is fast enough,
    typically 2-6s, to not warrant a background task — unlike doc
    generation which touches every file)."""

    content: str = Field(..., min_length=1, max_length=4000)


class MessageRead(ORMBase):
    id: uuid.UUID
    role: MessageRole
    content: str
    citations: List[Citation] = []
    created_at: datetime


class AskResponse(BaseModel):
    """Response to POST /chats/{id}/messages — includes both the stored
    user message and the generated assistant message."""

    user_message: MessageRead
    assistant_message: MessageRead
