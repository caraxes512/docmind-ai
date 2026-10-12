"""Documentation generation, versioning, and review schemas."""

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.enums import DocumentStatus, DocumentType
from app.schemas.common import ORMBase


class GenerateDocumentationRequest(BaseModel):
    """Full generation request. `doc_types` empty/omitted means "all
    applicable types" (the Orchestrator Agent decides which agents apply,
    e.g. skipping Database Documentation Agent if no DB schema is found)."""

    doc_types: Optional[List[DocumentType]] = None


class RegenerateDocumentationRequest(BaseModel):
    """Incremental regeneration. If `doc_types` is omitted, the service
    layer regenerates only the doc types whose source files changed since
    the current version's commit_hash (determined via RepositoryFile.index_status)."""

    doc_types: Optional[List[DocumentType]] = None
    force_full_regeneration: bool = Field(
        False, description="If true, ignores change detection and regenerates everything"
    )


class ReviewIssue(BaseModel):
    type: str = Field(..., examples=["missing_example", "broken_link", "outdated_api"])
    location: Optional[str] = None
    severity: str = Field(..., examples=["low", "medium", "high"])
    description: str


class ReviewResultRead(ORMBase):
    id: uuid.UUID
    quality_score: float
    issues: List[ReviewIssue]
    created_at: datetime


class GeneratedDocumentRead(ORMBase):
    id: uuid.UUID
    doc_type: DocumentType
    content: str
    status: DocumentStatus
    created_at: datetime
    updated_at: datetime
    review_result: Optional[ReviewResultRead] = None


class GeneratedDocumentSummary(ORMBase):
    """Lightweight variant for list views — omits `content` to keep
    the documentation dashboard listing cheap to fetch."""

    id: uuid.UUID
    doc_type: DocumentType
    status: DocumentStatus
    updated_at: datetime


class DocumentationVersionRead(ORMBase):
    id: uuid.UUID
    version_number: int
    commit_hash: str
    is_current: bool
    created_at: datetime
    documents: List[GeneratedDocumentSummary] = []


class DocumentUpdateRequest(BaseModel):
    """Manual edit from the Documentation Editor page."""

    content: str = Field(..., min_length=1)
