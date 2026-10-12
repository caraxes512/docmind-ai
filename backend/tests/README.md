# Testing

```bash
pip install -e ".[dev]" --break-system-packages
pytest                          # everything runnable without Docker
pytest -m unit                  # pure logic, no I/O
pytest -m agents                # agent nodes, FakeLLMProvider, no real API calls
pytest -m parsing               # repository parsing (see caveat below)
pytest -m api                   # FastAPI routes, service layer mocked, no DB
pytest -m integration           # real Postgres via testcontainers — needs Docker
pytest --cov=app --cov-report=term-missing
```

## Test tiers

| Tier | What it covers | Dependencies | Real DB? |
|---|---|---|---|
| `unit` | Parsers, chunking, embeddings batching, zip-slip/zip-bomb security, encryption, URL parsing | stdlib + `cryptography` | No |
| `agents` | Agent node logic — retries, validation, fallbacks, routing | `FakeLLMProvider` (in `conftest.py`) | No |
| `parsing` | Repository parsing dispatch | Python parts: none. Tree-sitter parts: `tree-sitter-language-pack` | No |
| `api` | Route wiring, status codes, auth enforcement, schema validation | `fastapi`, service layer mocked via `dependency_overrides` | No |
| `integration` | Repository-layer behavior against real Postgres — ownership scoping, the PENDING/STALE/INDEXED incremental-reindex logic (uses a real `ON CONFLICT` upsert, not portable to SQLite) | `testcontainers`, Docker | **Yes** |

## Honest verification status (as of Step 10)

This project was built in a sandbox with no network access, so most of
these test files were **never actually run against the real `pytest`
executable** — `pytest`, `fastapi`, `sqlalchemy`, `langgraph`, `openai`,
`qdrant-client`, and `tree-sitter-language-pack` all failed to install.
What follows is exactly what was and wasn't verified, so nobody mistakes
"written carefully" for "proven to work":

**Actually executed, with real assertions, via a manual harness** (not
pytest itself, but the identical underlying function calls the pytest
files above make):
- `test_python_ast_parser.py` — 11/11
- `test_dependency_extractor.py` — 9/9
- `test_chunking.py` — 11/11
- `test_embeddings.py` — 6/6
- `test_zip_extraction.py` — 10/10, including real crafted zip-slip and
  zip-bomb payloads (this one matters — it's security-critical code that
  had never been executed before this step)
- `test_language_detection.py` — 19/19
- `test_security_and_github.py`'s encryption tests — verified against the
  real `cryptography` library (happened to be present in the sandbox);
  the URL-parsing tests — verified against the real regex
- `test_repo_analyzer_agent.py`, `test_reviewer_agent.py`,
  `test_diagram_agent.py`, `test_generation_helpers.py`,
  `test_graph_routing.py` — 23/23 combined, via `sys.modules` stubbing to
  bypass the SQLAlchemy/LangGraph install requirement
- `test_tree_sitter_parser.py`'s dispatch logic (not the actual
  Tree-sitter grammar parsing) — 10/10

**Written correctly against documented APIs and framework conventions,
but never executed, because the required package couldn't be installed:**
- `tests/api/*` — needs a real `fastapi` install to confirm
  `TestClient` + `dependency_overrides` behave as written
- `tests/integration/*` — needs Docker + `testcontainers` + a real
  `asyncpg`/SQLAlchemy async engine
- The skipped Tree-sitter grammar-parsing tests in
  `test_tree_sitter_parser.py` — needs real grammars per language

If you're picking this project up: run `pytest -m "unit or agents or
parsing"` first as a fast sanity check requiring nothing but `pip
install`, then `pytest -m api` once you confirm `fastapi` imports cleanly,
then `pytest -m integration` last, since it's the slowest and needs Docker.
