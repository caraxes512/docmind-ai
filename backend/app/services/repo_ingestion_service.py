"""Repository ingestion service — ZIP upload and GitHub clone (public and
private, via OAuth). Both source types converge on the same extraction/scan
logic (`_extract_and_scan`) since a GitHub clone, under the hood, is just a
zipball downloaded from GitHub's API instead of uploaded by the user —
reusing Step 5's zip-slip/zip-bomb-protected extraction rather than
maintaining a second code path for "the other" way a repo's bytes arrive.
"""

import uuid
from pathlib import Path

from fastapi import Depends, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import ValidationError
from app.db.session import get_db
from app.models.enums import RepositorySourceType, RepositoryStatus, TaskType
from app.models.repository import Repository
from app.models.repository_file import RepositoryFile
from app.models.task import Task
from app.repositories.project_repository import ProjectRepository
from app.repositories.repository_file_repository import RepositoryFileRepository
from app.repositories.repository_repository import RepositoryRepository
from app.repositories.task_repository import TaskRepository
from app.repositories.user_repository import UserRepository
from app.api.deps import Pagination
from app.services.auth_service import get_decrypted_github_token
from app.services.github_client import GitHubClient, get_github_client, parse_github_url
from app.services.language_detection import detect_language, is_excluded_path
from app.services.storage_service import FileStorage, get_file_storage
from app.services.zip_extraction import validate_and_extract_zip


class RepositoryIngestionService:
    def __init__(
        self, db: AsyncSession, storage: FileStorage, github_client: GitHubClient | None = None
    ):
        self.db = db
        self.storage = storage
        self.github_client = github_client or get_github_client()
        self.project_repo = ProjectRepository(db)
        self.repository_repo = RepositoryRepository(db)
        self.file_repo = RepositoryFileRepository(db)
        self.task_repo = TaskRepository(db)
        self.user_repo = UserRepository(db)

    async def _extract_and_scan(
        self, repository_id: uuid.UUID, storage_path: str, zip_bytes: bytes
    ) -> None:
        settings = get_settings()
        destination_dir = Path(settings.LOCAL_STORAGE_ROOT) / storage_path
        extracted_files = validate_and_extract_zip(zip_bytes, destination_dir)

        scan_rows = []
        for extracted in extracted_files:
            if is_excluded_path(extracted.file_path):
                continue
            scan_rows.append(
                {
                    "file_path": extracted.file_path,
                    "language": detect_language(extracted.file_path),
                    "content_hash": extracted.content_hash,
                    "size_bytes": extracted.size_bytes,
                }
            )

        await self.file_repo.bulk_upsert_scan_results(repository_id, scan_rows)
        await self.repository_repo.update_status(repository_id, RepositoryStatus.SCANNING)

    async def _enqueue_ingestion(self, user_id: uuid.UUID, repository_id: uuid.UUID) -> Task:
        task = await self.task_repo.create(
            user_id=user_id, task_type=TaskType.REPOSITORY_INGESTION, repository_id=repository_id
        )
        await self.db.commit()

        # Enqueued after commit so the worker never picks up a task pointing
        # at a not-yet-committed row.
        from app.tasks.repository_ingestion_tasks import continue_ingestion_pipeline_task

        continue_ingestion_pipeline_task.delay(str(repository_id), str(task.id))
        return task

    async def upload_zip(
        self, user_id: uuid.UUID, project_id: uuid.UUID, file: UploadFile
    ) -> tuple[Repository, Task]:
        settings = get_settings()
        await self.project_repo.get_owned(user_id, project_id)  # ownership check

        if not file.filename or not file.filename.lower().endswith(".zip"):
            raise ValidationError("Uploaded file must be a .zip archive")

        content = await file.read()
        if len(content) > settings.MAX_UPLOAD_SIZE_BYTES:
            raise ValidationError(
                f"Uploaded file ({len(content)} bytes) exceeds the {settings.MAX_UPLOAD_SIZE_BYTES} byte limit"
            )

        repository = await self.repository_repo.create(
            project_id=project_id,
            source_type=RepositorySourceType.ZIP_UPLOAD,
            storage_path="",  # filled in below once we have the DB-assigned id
        )
        storage_path = f"repositories/{repository.id}"
        repository.storage_path = storage_path
        await self.db.flush()

        await self._extract_and_scan(repository.id, storage_path, content)
        task = await self._enqueue_ingestion(user_id, repository.id)
        await self.db.refresh(repository)
        return repository, task

    async def clone_github(
        self, user_id: uuid.UUID, project_id: uuid.UUID, github_url: str, branch: str | None
    ) -> tuple[Repository, Task]:
        await self.project_repo.get_owned(user_id, project_id)  # ownership check

        owner, repo_name = parse_github_url(github_url)

        # Use the user's linked GitHub token if they have one — enables
        # private repo access and raises GitHub's unauthenticated rate limit.
        # A public repo clones fine without one; a private repo without one
        # will fail with a clear 404 from GitHubClient (GitHub's API doesn't
        # distinguish "private" from "doesn't exist" for unauthenticated
        # requests, which is itself the correct behavior — it doesn't leak
        # the existence of private repos).
        user = await self.user_repo.get_by_id(user_id)
        access_token = get_decrypted_github_token(user) if user else None

        resolved_branch = branch or await self.github_client.get_default_branch(
            owner, repo_name, access_token
        )
        commit_sha = await self.github_client.get_latest_commit_sha(
            owner, repo_name, resolved_branch, access_token
        )
        zip_bytes = await self.github_client.download_repository_zipball(
            owner, repo_name, resolved_branch, access_token
        )

        source_type = (
            RepositorySourceType.GITHUB_PRIVATE_OAUTH
            if access_token
            else RepositorySourceType.GITHUB_PUBLIC
        )
        repository = await self.repository_repo.create(
            project_id=project_id,
            source_type=source_type,
            storage_path="",
            github_url=github_url,
            default_branch=resolved_branch,
        )
        storage_path = f"repositories/{repository.id}"
        repository.storage_path = storage_path
        await self.repository_repo.set_latest_commit_hash(repository.id, commit_sha)
        await self.db.flush()

        # GitHub's zipball wraps the repo in a single top-level directory
        # named "{repo}-{sha}/" — strip it so file_path values match what a
        # ZIP upload would produce (repo-root-relative), keeping downstream
        # scanning/parsing source-agnostic.
        stripped_bytes = _strip_zipball_root_directory(zip_bytes)

        await self._extract_and_scan(repository.id, storage_path, stripped_bytes)
        task = await self._enqueue_ingestion(user_id, repository.id)
        await self.db.refresh(repository)
        return repository, task

    async def list_for_project(
        self, user_id: uuid.UUID, project_id: uuid.UUID, pagination: Pagination
    ) -> tuple[list[Repository], int]:
        await self.project_repo.get_owned(user_id, project_id)
        return await self.repository_repo.list_for_project(
            user_id, project_id, pagination.limit, pagination.offset
        )

    async def get(self, user_id: uuid.UUID, repository_id: uuid.UUID) -> Repository:
        return await self.repository_repo.get_owned(user_id, repository_id)

    async def delete(self, user_id: uuid.UUID, repository_id: uuid.UUID) -> None:
        repository = await self.repository_repo.get_owned(user_id, repository_id)
        await self.storage.delete_tree(repository.storage_path)
        await self.repository_repo.delete(user_id, repository_id)
        await self.db.commit()

    async def list_files(
        self, user_id: uuid.UUID, repository_id: uuid.UUID, pagination: Pagination
    ) -> tuple[list[RepositoryFile], int]:
        return await self.repository_repo.list_files(
            user_id, repository_id, pagination.limit, pagination.offset
        )


def _strip_zipball_root_directory(zip_bytes: bytes) -> bytes:
    """Re-zips GitHub's archive with its single top-level '{repo}-{sha}/'
    directory prefix removed from every entry name."""
    import io
    import zipfile

    source = zipfile.ZipFile(io.BytesIO(zip_bytes))
    names = source.namelist()
    if not names:
        return zip_bytes

    # GitHub always wraps in exactly one top-level dir; derive its name from
    # the first entry rather than assuming a specific format.
    root_prefix = names[0].split("/", 1)[0] + "/"

    output_buffer = io.BytesIO()
    with zipfile.ZipFile(output_buffer, "w", zipfile.ZIP_DEFLATED) as output_zip:
        for info in source.infolist():
            if not info.filename.startswith(root_prefix):
                continue  # defensive — shouldn't happen given GitHub's consistent format
            new_name = info.filename[len(root_prefix) :]
            if not new_name:
                continue  # the root directory entry itself
            output_zip.writestr(new_name, source.read(info.filename))

    return output_buffer.getvalue()


def get_repository_ingestion_service(
    db: AsyncSession = Depends(get_db),
    storage: FileStorage = Depends(get_file_storage),
) -> RepositoryIngestionService:
    return RepositoryIngestionService(db, storage)
