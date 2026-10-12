"""Import every model here so that Base.metadata is fully populated when
Alembic's env.py does `from app.models import Base` for autogenerate.

Order doesn't matter for SQLAlchemy resolution (relationships use string
references + TYPE_CHECKING imports), but we group by dependency depth for
readability.
"""

from app.models.base import Base
from app.models.user import User
from app.models.project import Project
from app.models.repository import Repository
from app.models.repository_file import RepositoryFile
from app.models.parsed_symbol import ParsedSymbol
from app.models.embedding import Embedding
from app.models.documentation_version import DocumentationVersion
from app.models.generated_document import GeneratedDocument
from app.models.review_result import ReviewResult
from app.models.chat import Chat
from app.models.message import Message
from app.models.task import Task
from app.models.audit_log import AuditLog
from app.models.llm_usage_log import LLMUsageLog

__all__ = [
    "Base",
    "User",
    "Project",
    "Repository",
    "RepositoryFile",
    "ParsedSymbol",
    "Embedding",
    "DocumentationVersion",
    "GeneratedDocument",
    "ReviewResult",
    "Chat",
    "Message",
    "Task",
    "AuditLog",
    "LLMUsageLog",
]
