"""Centralized exception hierarchy.

Every domain error raised anywhere in the service layer inherits from
`DocMindException`. A single FastAPI exception handler (registered in
app.main) maps these to HTTP responses using `ErrorResponse`, so routers
never need try/except blocks around service calls — errors bubble up and
get a consistent JSON shape automatically.
"""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.schemas.common import ErrorDetail, ErrorResponse


class DocMindException(Exception):
    """Base class for all domain-level errors."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "docmind_error"

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class NotFoundError(DocMindException):
    status_code = status.HTTP_404_NOT_FOUND
    code = "not_found"


class AlreadyExistsError(DocMindException):
    status_code = status.HTTP_409_CONFLICT
    code = "already_exists"


class UnauthorizedError(DocMindException):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "unauthorized"


class ForbiddenError(DocMindException):
    status_code = status.HTTP_403_FORBIDDEN
    code = "forbidden"


class ValidationError(DocMindException):
    status_code = 422
    code = "validation_error"


class RateLimitExceededError(DocMindException):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    code = "rate_limit_exceeded"


class RepositoryProcessingError(DocMindException):
    """Raised by the ingestion pipeline — parsing, cloning, extraction failures."""

    status_code = 422
    code = "repository_processing_error"


class AgentExecutionError(DocMindException):
    """Raised when a LangGraph agent node fails after exhausting retries."""

    status_code = status.HTTP_502_BAD_GATEWAY
    code = "agent_execution_error"


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DocMindException)
    async def handle_docmind_exception(request: Request, exc: DocMindException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                error=ErrorDetail(code=exc.code, message=exc.message)
            ).model_dump(),
        )
