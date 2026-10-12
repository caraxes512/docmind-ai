"""Aggregates all v1 routers under a single APIRouter, mounted at /api/v1
in app.main. Keeping this separate from main.py means versioning to v2
later is just adding a sibling package + one new include_router call."""

from fastapi import APIRouter

from app.api.v1 import auth, chat, documentation, export, git, health, projects, repositories, tasks

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(projects.router)
api_router.include_router(repositories.router)
api_router.include_router(documentation.router)
api_router.include_router(chat.router)
api_router.include_router(export.router)
api_router.include_router(tasks.router)
api_router.include_router(git.router)
