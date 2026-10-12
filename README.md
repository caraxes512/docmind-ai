# DocMind AI

AI-powered documentation generator that analyzes an entire repository — structure, dependencies,
APIs, database models — and produces documentation via a multi-agent LangGraph pipeline, backed by a
RAG-powered chat interface for asking questions about the codebase directly.

## Quickstart

```bash
cp .env.example .env   # fill in JWT_SECRET_KEY, ENCRYPTION_KEY, OPENAI_API_KEY at minimum
docker compose up --build
```

Then visit http://localhost:3000. Full instructions, including required environment variables and
production deployment options, are in [`DEPLOYMENT.md`](./DEPLOYMENT.md).

## Architecture

```
frontend/    Next.js 14 (App Router) + TypeScript + Tailwind — blueprint/schematic design system
backend/     FastAPI + SQLAlchemy (async) + Celery — modular monolith, repository pattern
  app/agents/     LangGraph multi-agent orchestration (11 agents + routing)
  app/rag/        Chunking, embeddings, Qdrant vector store, retrieval
  app/parsing/    Tree-sitter (JS/TS/Java/C++/Go) + Python AST (primary for .py)
  app/services/   Business logic — ingestion, GitHub OAuth, storage, git AI features
  tests/          unit / agents / api / integration / parsing tiers — see tests/README.md
```

**Stack**: Python 3.12, FastAPI, SQLAlchemy 2.0, PostgreSQL, Redis, Celery, LangGraph, Qdrant,
Next.js 14, React 18, TypeScript, Tailwind CSS.

**Key design decisions** (each explained in-depth where implemented):
- Modular monolith over microservices for this scale — clear internal boundaries, single deploy unit
- Multi-agent generation via LangGraph: fan-out for independent doc types, fan-in at the Reviewer Agent
- Parsing/chunking/embedding happens once at ingestion (persisted), not re-run on every generation —
  this is what makes incremental regeneration and Reviewer Agent cross-referencing actually work
- Qdrant chosen specifically for payload-filtered incremental re-indexing (repository_id + file_path
  filtering), not just as "a vector database"
- GitHub cloning reuses the same zip-slip/zip-bomb-protected extraction path as manual upload — a
  repository's bytes arrive the same way regardless of source

## Development

This project was built incrementally across 11 explicit steps (architecture → schema → API design →
AI agent design → backend → frontend → AI integration → GitHub integration → RAG pipeline → testing →
deployment), each with its own design rationale, trade-offs, and — where the code could actually be
executed — real verification rather than just syntax-checking. See `tests/README.md` for exactly
what was and wasn't verified, tier by tier, and `DEPLOYMENT.md`'s closing section for the same
honesty applied to the project as a whole.

```bash
# Backend
cd backend && pip install -e ".[dev]" --break-system-packages
pytest -m "unit or agents or parsing"    # fast tier, no external services
ruff check app && ruff format app

# Frontend
cd frontend && npm install
npm run lint && npm run typecheck
```

Pre-commit hooks (`.pre-commit-config.yaml`) run ruff, eslint, and prettier automatically —
`pre-commit install` once per clone.

## License

This project is licensed under the [MIT License](LICENSE).
