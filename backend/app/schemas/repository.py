"""Repository schemas: upload, clone, read, file listing."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.enums import (
    FileIndexStatus,
    ProgrammingLanguage,
    RepositorySourceType,
    RepositoryStatus,
)
from app.schemas.common import ORMBase


class RepositoryCloneRequest(BaseModel):
    """Used for both public clone and private (OAuth-authorized) clone —
    the service layer decides which code path based on whether the URL
    resolves to a repo the user's GitHub token can access privately."""

    github_url: str = Field(..., examples=["https://github.com/octocat/Hello-World"])
    branch: Optional[str] = Field(None, description="Defaults to the repo's default branch")


class RepositoryRead(ORMBase):
    id: uuid.UUID
    project_id: uuid.UUID
    source_type: RepositorySourceType
    github_url: Optional[str] = None
    default_branch: Optional[str] = None
    latest_commit_hash: Optional[str] = None
    status: RepositoryStatus
    status_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class RepositoryFileRead(ORMBase):
    id: uuid.UUID
    file_path: str
    language: ProgrammingLanguage
    size_bytes: int
    index_status: FileIndexStatus


class UploadInitiatedResponse(BaseModel):
    """Returned immediately on ZIP upload / clone request — ingestion runs
    as a background task, tracked via the embedded task_id."""

    repository: RepositoryRead
    task_id: uuid.UUID
