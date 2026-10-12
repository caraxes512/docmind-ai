"""Git integration schemas — AI-generated commit messages, PR descriptions,
release notes, and changelogs. These are synchronous, single-LLM-call
endpoints (no multi-agent graph needed), unlike full documentation
generation."""

from typing import List, Optional

from pydantic import BaseModel, Field


class CommitMessageRequest(BaseModel):
    diff: str = Field(..., description="Unified diff (git diff output) to summarize")


class CommitMessageResponse(BaseModel):
    subject: str = Field(..., max_length=72)
    body: Optional[str] = None


class PRDescriptionRequest(BaseModel):
    base_branch: str
    head_branch: str
    diff: str
    commit_messages: List[str] = Field(default_factory=list)


class PRDescriptionResponse(BaseModel):
    title: str
    description: str  # Markdown, includes a "What changed" + "Why" structure


class ReleaseNotesRequest(BaseModel):
    from_tag: str
    to_tag: str
    commit_messages: List[str]


class ReleaseNotesResponse(BaseModel):
    content: str  # Markdown


class ChangelogEntryRequest(BaseModel):
    version: str
    commit_messages: List[str]


class ChangelogResponse(BaseModel):
    content: str  # Markdown, formatted per Keep a Changelog convention
