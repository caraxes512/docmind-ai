# syntax=docker/dockerfile:1

# --- Stage 1: builder — installs dependencies into a venv, keeps build
# tools (gcc, etc.) out of the final image entirely ---
FROM python:3.12-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY pyproject.toml ./
# Installing just the dependency graph before copying app/ so this layer
# stays cached across code changes that don't touch dependencies.
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

# --- Stage 2: runtime — slim image, only what's needed to run ---
FROM python:3.12-slim AS runtime

# System libraries required by:
#  - weasyprint (PDF export, Step 11): cairo, pango, gdk-pixbuf
#  - psycopg2 (if not using the -binary wheel path): libpq
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 libpangocairo-1.0-0 libcairo2 libgdk-pixbuf-2.0-0 \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --shell /bin/bash docmind
WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY . .
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh \
    && mkdir -p /var/docmind/storage \
    && chown -R docmind:docmind /app /var/docmind/storage

USER docmind

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

ENTRYPOINT ["/entrypoint.sh"]
# Default command — overridden by docker-compose for the celery-worker
# service (same image, different CMD), keeping one Dockerfile for both
# rather than near-duplicate build definitions.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
