"""Application settings (pydantic-settings) — full version.

Supersedes the Step 2 stub. All values are environment-driven; defaults
below are safe-for-local-dev only. As of Step 11, `_validate_production_
secrets` actually enforces this — the app refuses to boot with a default
JWT_SECRET_KEY or ENCRYPTION_KEY when ENVIRONMENT=production, rather than
silently running insecurely (which was the real risk of leaving this as a
comment-only warning through Steps 2-10).
"""

from functools import lru_cache
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEV_FERNET_KEY = "Q0hBTkdFX01FX0lOX0VOVl8zMl9CWVRFU19LRVkhIQ=="
_INSECURE_DEFAULTS = {
    "CHANGE_ME_IN_ENV",
    "CHANGE_ME_IN_ENV_FERNET_KEY_MUST_BE_32B64B",
    _DEV_FERNET_KEY,
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    ENVIRONMENT: Literal["local", "staging", "production"] = "local"

    # --- Database ---
    POSTGRES_USER: str = "docmind"
    POSTGRES_PASSWORD: str = "docmind"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "docmind"

    # --- Redis (Celery broker/backend + rate limiting) ---
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    # --- JWT ---
    JWT_SECRET_KEY: str = "CHANGE_ME_IN_ENV"

    # Fernet key (32 url-safe base64-encoded bytes) used to encrypt GitHub
    # OAuth tokens at rest (User.github_access_token_encrypted). Generate a
    # real one with: python -c "from cryptography.fernet import Fernet;
    # print(Fernet.generate_key().decode())"
    ENCRYPTION_KEY: str = _DEV_FERNET_KEY

    # --- GitHub OAuth (Step 8) ---
    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""
    GITHUB_OAUTH_REDIRECT_URI: str = "http://localhost:3000/auth/github/callback"

    # --- LLM provider (Step 7) ---
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str | None = None
    LLM_MODEL: str = "gpt-4o-mini"
    EMBEDDING_MODEL: str = "text-embedding-3-large"

    # --- Vector store (Step 9) ---
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_COLLECTION_NAME: str = "docmind_embeddings"

    # --- File storage ---
    STORAGE_BACKEND: Literal["local", "s3"] = "local"
    LOCAL_STORAGE_ROOT: str = "/var/docmind/storage"
    S3_BUCKET_NAME: str = ""
    S3_REGION: str = "us-east-1"

    # --- Upload limits (security — see app/services/zip_extraction.py) ---
    MAX_UPLOAD_SIZE_BYTES: int = 200 * 1024 * 1024  # 200MB compressed
    MAX_EXTRACTED_SIZE_BYTES: int = 2 * 1024 * 1024 * 1024  # 2GB uncompressed — zip-bomb guard
    MAX_EXTRACTED_FILE_COUNT: int = 50_000

    # --- Rate limiting ---
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = 60
    RATE_LIMIT_LLM_REQUESTS_PER_MINUTE: int = 10  # stricter limit on AI-calling endpoints

    # --- CORS ---
    # pydantic-settings parses List[str] fields from an env var by JSON-
    # decoding the raw string (no custom validator needed) — so
    # CORS_ALLOWED_ORIGINS='["https://app.example.com"]' in .env works,
    # but CORS_ALLOWED_ORIGINS=https://app.example.com (bare, no brackets)
    # does NOT. This is pydantic-settings' documented default behavior for
    # complex-typed fields, not a gap in this app's config — noted here
    # because it's an easy mistake when hand-writing a production .env.
    CORS_ALLOWED_ORIGINS: list[str] = ["http://localhost:3000"]

    @model_validator(mode="after")
    def _validate_production_secrets(self) -> "Settings":
        if self.ENVIRONMENT != "production":
            return self

        insecure = [
            name
            for name, value in (
                ("JWT_SECRET_KEY", self.JWT_SECRET_KEY),
                ("ENCRYPTION_KEY", self.ENCRYPTION_KEY),
            )
            if value in _INSECURE_DEFAULTS
        ]
        if insecure:
            raise ValueError(
                f"Refusing to start with ENVIRONMENT=production while these settings still "
                f"have insecure default values: {', '.join(insecure)}. Set real secrets via "
                f"environment variables or a secrets manager before deploying."
            )
        if self.OPENAI_API_KEY == "":
            raise ValueError("OPENAI_API_KEY must be set when ENVIRONMENT=production.")
        return self

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        """Sync DSN — used by Alembic (env.py)."""
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def REDIS_URL(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    @property
    def CELERY_BROKER_URL(self) -> str:
        return self.REDIS_URL

    @property
    def CELERY_RESULT_BACKEND(self) -> str:
        return self.REDIS_URL


@lru_cache
def get_settings() -> Settings:
    return Settings()
