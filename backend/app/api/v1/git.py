"""Git integration endpoints — AI-generated commit messages, PR descriptions,
release notes, and changelogs."""

from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.git import (
    ChangelogEntryRequest,
    ChangelogResponse,
    CommitMessageRequest,
    CommitMessageResponse,
    PRDescriptionRequest,
    PRDescriptionResponse,
    ReleaseNotesRequest,
    ReleaseNotesResponse,
)
from app.services.git_service import GitIntegrationService, get_git_integration_service

router = APIRouter(prefix="/repositories/{repository_id}/git", tags=["git"])


@router.post("/commit-message", response_model=CommitMessageResponse)
async def generate_commit_message(
    repository_id: UUID,
    body: CommitMessageRequest,
    current_user: User = Depends(get_current_user),
    service: GitIntegrationService = Depends(get_git_integration_service),
) -> CommitMessageResponse:
    subject, message_body = await service.generate_commit_message(current_user.id, body.diff)
    return CommitMessageResponse(subject=subject, body=message_body)


@router.post("/pr-description", response_model=PRDescriptionResponse)
async def generate_pr_description(
    repository_id: UUID,
    body: PRDescriptionRequest,
    current_user: User = Depends(get_current_user),
    service: GitIntegrationService = Depends(get_git_integration_service),
) -> PRDescriptionResponse:
    title, description = await service.generate_pr_description(
        current_user.id, body.base_branch, body.head_branch, body.diff, body.commit_messages
    )
    return PRDescriptionResponse(title=title, description=description)


@router.post("/release-notes", response_model=ReleaseNotesResponse)
async def generate_release_notes(
    repository_id: UUID,
    body: ReleaseNotesRequest,
    current_user: User = Depends(get_current_user),
    service: GitIntegrationService = Depends(get_git_integration_service),
) -> ReleaseNotesResponse:
    content = await service.generate_release_notes(
        current_user.id, body.from_tag, body.to_tag, body.commit_messages
    )
    return ReleaseNotesResponse(content=content)


@router.post("/changelog", response_model=ChangelogResponse)
async def generate_changelog_entry(
    repository_id: UUID,
    body: ChangelogEntryRequest,
    current_user: User = Depends(get_current_user),
    service: GitIntegrationService = Depends(get_git_integration_service),
) -> ChangelogResponse:
    content = await service.generate_changelog_entry(
        current_user.id, body.version, body.commit_messages
    )
    return ChangelogResponse(content=content)
