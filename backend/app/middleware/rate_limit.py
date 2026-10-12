"""Redis-backed sliding-window rate limiting.

Keyed by (user_id if authenticated, else client IP) + route group, since
unauthenticated endpoints (login, register) need their own limit to
prevent credential-stuffing, separate from the general per-user limit.
LLM-calling routes (documentation generation, chat) get a stricter limit
(RATE_LIMIT_LLM_REQUESTS_PER_MINUTE) since they're the expensive ones —
enforced by checking the request path against a small prefix list rather
than annotating every route individually.
"""

import time

import redis.asyncio as redis
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import get_settings
from app.core.security import decode_token
from app.schemas.common import ErrorDetail, ErrorResponse

_LLM_ROUTE_PREFIXES = (
    "/api/v1/repositories/",  # covers .../documentation/generate, .../documentation/regenerate
    "/api/v1/chats/",
)


def _resolve_identity(request: Request) -> str:
    """Decodes the JWT directly (rather than relying on request.state.user_id
    from get_current_user) because this middleware runs BEFORE router
    dependency resolution — get_current_user hasn't executed yet at this
    point in the request lifecycle, so its state wouldn't be available even
    though both handle "the same" concern. Falls back to client IP for
    unauthenticated routes or invalid/missing tokens (those still get
    limited, just bucketed by IP instead)."""
    auth_header = request.headers.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        token = auth_header[7:]
        user_id = decode_token(token, expected_type="access")
        if user_id is not None:
            return str(user_id)
    return request.client.host if request.client else "unknown"


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        settings = get_settings()
        self._redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
        self._general_limit = settings.RATE_LIMIT_REQUESTS_PER_MINUTE
        self._llm_limit = settings.RATE_LIMIT_LLM_REQUESTS_PER_MINUTE

    def _is_llm_route(self, path: str) -> bool:
        return path.startswith(_LLM_ROUTE_PREFIXES) and (
            path.endswith("/generate") or path.endswith("/regenerate") or path.endswith("/messages")
        )

    async def dispatch(self, request: Request, call_next) -> Response:
        identity = _resolve_identity(request)

        is_llm_route = self._is_llm_route(request.url.path)
        limit = self._llm_limit if is_llm_route else self._general_limit
        bucket_key = (
            f"ratelimit:{'llm' if is_llm_route else 'general'}:{identity}:{int(time.time() // 60)}"
        )

        try:
            current_count = await self._redis.incr(bucket_key)
            if current_count == 1:
                await self._redis.expire(bucket_key, 60)

            if current_count > limit:
                # Returned directly (not raised) — exceptions raised here, before
                # call_next() reaches the router, bypass FastAPI's registered
                # DocMindException handler (that handler sits on ExceptionMiddleware,
                # which wraps the router but not user-added middleware upstream of
                # it). Constructing the same ErrorResponse shape here keeps the
                # response format consistent without relying on handler ordering.
                return JSONResponse(
                    status_code=429,
                    content=ErrorResponse(
                        error=ErrorDetail(
                            code="rate_limit_exceeded",
                            message=f"Rate limit exceeded ({limit} requests/minute for this route group). Try again shortly.",
                        )
                    ).model_dump(),
                )
        except (redis.RedisError, OSError):
            # Fail open if Redis is unreachable (e.g. during API tests or Redis outages)
            pass

        return await call_next(request)
