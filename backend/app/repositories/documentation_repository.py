import uuid

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError
from app.models.documentation_version import DocumentationVersion
from app.models.generated_document import GeneratedDocument
from app.models.project import Project
from app.models.repository import Repository
from app.models.review_result import ReviewResult
from app.repositories.base import BaseRepository


class DocumentationRepository(BaseRepository):
    async def _assert_repository_owned(self, user_id: uuid.UUID, repository_id: uuid.UUID) -> None:
        result = await self.db.execute(
            select(Repository.id)
            .join(Project, Repository.project_id == Project.id)
            .where(Repository.id == repository_id, Project.user_id == user_id)
        )
        if result.scalar_one_or_none() is None:
            raise NotFoundError(f"Repository {repository_id} not found")

    async def get_current_version(
        self, user_id: uuid.UUID, repository_id: uuid.UUID
    ) -> DocumentationVersion:
        await self._assert_repository_owned(user_id, repository_id)
        result = await self.db.execute(
            select(DocumentationVersion)
            .options(selectinload(DocumentationVersion.documents))
            .where(
                DocumentationVersion.repository_id == repository_id,
                DocumentationVersion.is_current.is_(True),
            )
        )
        version = result.scalar_one_or_none()
        if version is None:
            raise NotFoundError(f"No current documentation version for repository {repository_id}")
        return version

    async def list_versions(
        self, user_id: uuid.UUID, repository_id: uuid.UUID
    ) -> list[DocumentationVersion]:
        await self._assert_repository_owned(user_id, repository_id)
        result = await self.db.execute(
            select(DocumentationVersion)
            .options(selectinload(DocumentationVersion.documents))
            .where(DocumentationVersion.repository_id == repository_id)
            .order_by(DocumentationVersion.version_number.desc())
        )
        return list(result.scalars().all())

    async def get_version_owned(
        self, user_id: uuid.UUID, version_id: uuid.UUID
    ) -> DocumentationVersion:
        result = await self.db.execute(
            select(DocumentationVersion)
            .join(Repository, DocumentationVersion.repository_id == Repository.id)
            .join(Project, Repository.project_id == Project.id)
            .options(selectinload(DocumentationVersion.documents))
            .where(DocumentationVersion.id == version_id, Project.user_id == user_id)
        )
        version = result.scalar_one_or_none()
        if version is None:
            raise NotFoundError(f"Documentation version {version_id} not found")
        return version

    async def create_version(
        self, repository_id: uuid.UUID, commit_hash: str
    ) -> DocumentationVersion:
        """Creates the next version number for this repository and demotes
        the previous current version — done inside one transaction by the
        caller (service layer) so this never leaves two versions marked current."""
        result = await self.db.execute(
            select(DocumentationVersion).where(
                DocumentationVersion.repository_id == repository_id,
                DocumentationVersion.is_current.is_(True),
            )
        )
        previous_current = result.scalar_one_or_none()
        next_version_number = 1
        if previous_current is not None:
            previous_current.is_current = False
            next_version_number = previous_current.version_number + 1

        version = DocumentationVersion(
            repository_id=repository_id,
            version_number=next_version_number,
            commit_hash=commit_hash,
            is_current=True,
        )
        self.db.add(version)
        await self.db.flush()
        return version

    async def get_document_owned(
        self, user_id: uuid.UUID, document_id: uuid.UUID
    ) -> GeneratedDocument:
        result = await self.db.execute(
            select(GeneratedDocument)
            .join(DocumentationVersion, GeneratedDocument.version_id == DocumentationVersion.id)
            .join(Repository, DocumentationVersion.repository_id == Repository.id)
            .join(Project, Repository.project_id == Project.id)
            .options(
                selectinload(GeneratedDocument.review_result),
                selectinload(GeneratedDocument.version),
            )
            .where(GeneratedDocument.id == document_id, Project.user_id == user_id)
        )
        document = result.scalar_one_or_none()
        if document is None:
            raise NotFoundError(f"Document {document_id} not found")
        return document

    async def update_document_content(
        self, user_id: uuid.UUID, document_id: uuid.UUID, content: str
    ) -> GeneratedDocument:
        document = await self.get_document_owned(user_id, document_id)
        document.content = content
        await self.db.flush()
        return document

    async def upsert_review_result(
        self, document_id: uuid.UUID, quality_score: float, issues: list[dict]
    ) -> ReviewResult:
        """A document has at most one ReviewResult (Step 2's 1:1 constraint).
        Re-triggering review replaces the prior result rather than
        accumulating history — review history isn't a tracked requirement,
        unlike documentation version history."""
        result = await self.db.execute(
            select(ReviewResult).where(ReviewResult.generated_document_id == document_id)
        )
        existing = result.scalar_one_or_none()

        if existing is not None:
            existing.quality_score = quality_score
            existing.issues = issues
            await self.db.flush()
            return existing

        review_result = ReviewResult(
            generated_document_id=document_id, quality_score=quality_score, issues=issues
        )
        self.db.add(review_result)
        await self.db.flush()
        return review_result
