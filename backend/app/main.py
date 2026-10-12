"""FastAPI application factory — full version.

Middleware order matters: Starlette applies middleware in reverse of the
order added (last added = outermost). We want, from outermost to
innermost: CORS -> request logging -> rate limiting -> router. That means
adding them router-adjacent first: rate limit, then logging, then CORS.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.db.session import engine
from app.middleware.logging import RequestLoggingMiddleware
from app.middleware.rate_limit import RateLimitMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()  # closes the connection pool cleanly on shutdown


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="DocMind AI",
        description="AI-enhanced documentation generator",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)
    app.include_router(api_router, prefix="/api/v1")

    return app


app = create_app()
