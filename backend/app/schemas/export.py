"""Export schemas — Markdown/HTML/PDF export of a documentation version."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.enums import DocumentType, ExportFormat
from app.schemas.common import ORMBase


class ExportRequest(BaseModel):
    format: ExportFormat
    doc_types: Optional[list[DocumentType]] = None  # omitted = export all docs in the version


class ExportInitiatedResponse(BaseModel):
    task_id: uuid.UUID


class ExportDownloadResponse(ORMBase):
    """Returned once the export Task succeeds — a pre-signed, time-limited
    URL to the generated file in object storage rather than streaming the
    (potentially large, PDF-rendered) file through the API process."""

    download_url: str
    expires_at: datetime
    format: ExportFormat
