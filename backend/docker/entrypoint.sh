#!/bin/bash
set -euo pipefail

# Only the api/worker roles need migrations applied; running this from
# every container (api, worker, beat if added later) is safe because
# Alembic's upgrade is idempotent, but we skip it for anything invoked
# with an explicit non-serving command (e.g. a one-off shell) to avoid
# surprising a debugging session with an unwanted migration run.
if [[ "${1:-}" == "uvicorn" || "${1:-}" == "celery" ]]; then
  echo "[entrypoint] Waiting for database..."
  # A short retry loop rather than a fixed sleep — Postgres in
  # docker-compose can take a few seconds to accept connections after its
  # own container reports "started," and a fixed sleep is either too
  # short (flaky) or wastefully long (slow every cold start).
  for i in $(seq 1 30); do
    if python -c "
import sys
from app.core.config import get_settings
import psycopg2
try:
    psycopg2.connect(get_settings().SQLALCHEMY_DATABASE_URI.replace('postgresql+psycopg2', 'postgresql'))
except Exception:
    sys.exit(1)
" 2>/dev/null; then
      echo "[entrypoint] Database is ready."
      break
    fi
    echo "[entrypoint] Database not ready yet (attempt $i/30)..."
    sleep 2
  done

  echo "[entrypoint] Running database migrations..."
  alembic upgrade head
fi

exec "$@"
