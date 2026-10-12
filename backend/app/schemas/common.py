"""Shared schema primitives reused across all resource schemas."""

from typing import Generic, List, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class ORMBase(BaseModel):
    """Base for schemas that read directly from SQLAlchemy ORM instances."""

    model_config = ConfigDict(from_attributes=True)


class Page(BaseModel, Generic[T]):
    """Standard cursor-free pagination envelope.

    We use offset/limit (not cursor-based) deliberately: every listing
    endpoint in this API is scoped to a single user's resources (their
    projects, their repositories), where result sets are small (tens to
    low hundreds), so cursor complexity isn't justified. If any endpoint's
    result set grows unbounded (e.g. audit logs at scale), it gets cursor
    pagination as a targeted exception, not a blanket rule.
    """

    items: List[T]
    total: int = Field(..., description="Total number of items matching the query")
    limit: int
    offset: int


class ErrorDetail(BaseModel):
    code: str = Field(..., description="Machine-readable error code, e.g. 'repository_not_found'")
    message: str = Field(..., description="Human-readable error message")


class ErrorResponse(BaseModel):
    """Uniform error envelope returned by the centralized exception handler
    (app.core.exceptions) for every non-2xx response."""

    error: ErrorDetail
