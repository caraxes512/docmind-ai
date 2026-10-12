"""Structured request logging middleware.

Emits one JSON log line per request with request_id, method, path, status,
duration, and user_id (when available) — the fields called out in Step 1's
cross-cutting concerns as needed for tracing across async job boundaries
(the same request_id is threaded into Task creation so a Celery task's
logs can be correlated back to the HTTP request that triggered it).
"""

import json
import logging
import time
import uuid

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("docmind.request")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        start = time.monotonic()

        response = await call_next(request)

        duration_ms = round((time.monotonic() - start) * 1000, 2)
        log_payload = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
            "user_id": getattr(request.state, "user_id", None),
        }
        logger.info(json.dumps(log_payload))

        response.headers["X-Request-ID"] = request_id
        return response
