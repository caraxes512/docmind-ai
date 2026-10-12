"""Documentation endpoints: generation, incremental regeneration, current
docs, version history, single-document read/edit, and review."""

from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.documentation import (
    DocumentationVersionRead,
    DocumentUpdateRequest,
    GenerateDocumentationRequest,
    GeneratedDocumentRead,
    RegenerateDocumentationRequest,
    ReviewResultRead,
)
from app.schemas.task import TaskRead
from app.services.documentation_service import DocumentationService, get_documentation_service

router = APIRouter(tags=["documentation"])


@router.post(
    "/repositories/{repository_id}/documentation/generate",
    response_model=TaskRead,
    status_code=status.HTTP_202_ACCEPTED,
)
async def generate_documentation(
    repository_id: UUID,
    body: GenerateDocumentationRequest,
    current_user: User = Depends(get_current_user),
    service: DocumentationService = Depends(get_documentation_service),
) -> TaskRead:
    task = await service.generate(current_user.id, repository_id, body.doc_types)
    return TaskRead.model_validate(task)


@router.post(
    "/repositories/{repository_id}/documentation/regenerate",
    response_model=TaskRead,
    status_code=status.HTTP_202_ACCEPTED,
)
async def regenerate_documentation(
    repository_id: UUID,
    body: RegenerateDocumentationRequest,
    current_user: User = Depends(get_current_user),
    service: DocumentationService = Depends(get_documentation_service),
) -> TaskRead:
    task = await service.regenerate(
        current_user.id, repository_id, body.doc_types, body.force_full_regeneration
    )
    return TaskRead.model_validate(task)


@router.get("/repositories/{repository_id}/documentation", response_model=DocumentationVersionRead)
async def get_current_documentation(
    repository_id: UUID,
    current_user: User = Depends(get_current_user),
    service: DocumentationService = Depends(get_documentation_service),
) -> DocumentationVersionRead:
    version = await service.get_current_version(current_user.id, repository_id)
    return DocumentationVersionRead.model_validate(version)


@router.get(
    "/repositories/{repository_id}/documentation/versions",
    response_model=list[DocumentationVersionRead],
)
async def list_documentation_versions(
    repository_id: UUID,
    current_user: User = Depends(get_current_user),
    service: DocumentationService = Depends(get_documentation_service),
) -> list[DocumentationVersionRead]:
    versions = await service.list_versions(current_user.id, repository_id)
    return [DocumentationVersionRead.model_validate(v) for v in versions]


@router.get(
    "/repositories/{repository_id}/documentation/versions/{version_id}",
    response_model=DocumentationVersionRead,
)
async def get_documentation_version(
    repository_id: UUID,
    version_id: UUID,
    current_user: User = Depends(get_current_user),
    service: DocumentationService = Depends(get_documentation_service),
) -> DocumentationVersionRead:
    version = await service.get_version(current_user.id, version_id)
    return DocumentationVersionRead.model_validate(version)


@router.get("/documentation/{document_id}", response_model=GeneratedDocumentRead)
async def get_document(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    service: DocumentationService = Depends(get_documentation_service),
) -> GeneratedDocumentRead:
    document = await service.get_document(current_user.id, document_id)
    return GeneratedDocumentRead.model_validate(document)


@router.patch("/documentation/{document_id}", response_model=GeneratedDocumentRead)
async def update_document(
    document_id: UUID,
    body: DocumentUpdateRequest,
    current_user: User = Depends(get_current_user),
    service: DocumentationService = Depends(get_documentation_service),
) -> GeneratedDocumentRead:
    document = await service.update_document(current_user.id, document_id, body.content)
    return GeneratedDocumentRead.model_validate(document)


@router.post("/documentation/{document_id}/review", response_model=ReviewResultRead)
async def review_document(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    service: DocumentationService = Depends(get_documentation_service),
) -> ReviewResultRead:
    """Synchronously runs the Documentation Reviewer Agent against a single
    document. Kept synchronous (not a Task) since review of one document is
    a single, bounded LLM call — unlike full-repo generation."""
    result = await service.trigger_review(current_user.id, document_id)
    return ReviewResultRead.model_validate(result)
