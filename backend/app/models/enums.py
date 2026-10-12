"""Centralized enum definitions shared across ORM models and Pydantic schemas.

Keeping enums in one module (rather than inline per-model) avoids circular
imports between models that reference the same status vocabulary (e.g. Task
and Repository both need a processing status).
"""

import enum


class RepositorySourceType(str, enum.Enum):
    ZIP_UPLOAD = "zip_upload"
    GITHUB_PUBLIC = "github_public"
    GITHUB_PRIVATE_OAUTH = "github_private_oauth"


class RepositoryStatus(str, enum.Enum):
    PENDING = "pending"
    SCANNING = "scanning"
    PARSING = "parsing"
    EMBEDDING = "embedding"
    READY = "ready"
    FAILED = "failed"


class ProgrammingLanguage(str, enum.Enum):
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    JAVA = "java"
    CPP = "cpp"
    GO = "go"
    UNKNOWN = "unknown"


class FileIndexStatus(str, enum.Enum):
    PENDING = "pending"
    INDEXED = "indexed"
    STALE = "stale"  # content changed since last embedding
    EXCLUDED = "excluded"  # e.g. binary, vendored, gitignored


class DocumentType(str, enum.Enum):
    README = "readme"
    INSTALLATION_GUIDE = "installation_guide"
    SETUP_GUIDE = "setup_guide"
    FOLDER_STRUCTURE = "folder_structure"
    API_DOCS = "api_docs"
    CLASS_DOCS = "class_docs"
    FUNCTION_DOCS = "function_docs"
    ARCHITECTURE_DOCS = "architecture_docs"
    DATABASE_DOCS = "database_docs"
    DEPLOYMENT_GUIDE = "deployment_guide"
    CONTRIBUTION_GUIDE = "contribution_guide"
    FAQ = "faq"
    DIAGRAM = "diagram"


class DocumentStatus(str, enum.Enum):
    GENERATING = "generating"
    COMPLETE = "complete"
    FAILED = "failed"
    STALE = "stale"  # source version superseded, not yet regenerated


class TaskType(str, enum.Enum):
    REPOSITORY_INGESTION = "repository_ingestion"
    FULL_DOCUMENTATION_GENERATION = "full_documentation_generation"
    INCREMENTAL_REGENERATION = "incremental_regeneration"
    DOCUMENTATION_REVIEW = "documentation_review"
    EXPORT = "export"


class TaskStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class MessageRole(str, enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ExportFormat(str, enum.Enum):
    MARKDOWN = "markdown"
    HTML = "html"
    PDF = "pdf"


class SymbolKind(str, enum.Enum):
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"
    API_ROUTE = "api_route"
    DB_MODEL = "db_model"
