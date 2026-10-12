"""File storage abstraction (Strategy pattern, mirroring the LLM provider
approach from Step 4). `LocalFileStorage` is fully implemented for local
development; `S3FileStorage` is the production path, stubbed here since it
needs the actual deployment's bucket/IAM setup (Step 11)."""

import shutil
from abc import ABC, abstractmethod
from pathlib import Path

import aioboto3

from app.core.config import get_settings


class FileStorage(ABC):
    @abstractmethod
    async def save(self, relative_path: str, content: bytes) -> str:
        """Writes content, returns the storage-backend-specific path/key
        to persist in the DB (e.g. Repository.storage_path)."""
        raise NotImplementedError

    @abstractmethod
    async def read(self, path: str) -> bytes:
        raise NotImplementedError

    @abstractmethod
    async def delete_tree(self, path: str) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_download_url(self, path: str, expires_in_seconds: int = 3600) -> str:
        """Returns a URL the frontend can fetch directly (pre-signed for
        S3; a signed, time-limited app route for local storage)."""
        raise NotImplementedError


class LocalFileStorage(FileStorage):
    def __init__(self, root: str | None = None):
        self.root = Path(root or get_settings().LOCAL_STORAGE_ROOT)
        self.root.mkdir(parents=True, exist_ok=True)

    def _resolve(self, relative_path: str) -> Path:
        """Resolves relative_path under root and asserts the result stays
        within root — the same zip-slip class of bug applies here if a
        caller ever passes a path containing '..' segments."""
        resolved = (self.root / relative_path).resolve()
        if not str(resolved).startswith(str(self.root.resolve())):
            raise ValueError(f"Resolved path {resolved} escapes storage root {self.root}")
        return resolved

    async def save(self, relative_path: str, content: bytes) -> str:
        full_path = self._resolve(relative_path)
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_bytes(content)
        return relative_path

    async def read(self, path: str) -> bytes:
        return self._resolve(path).read_bytes()

    async def delete_tree(self, path: str) -> None:
        full_path = self._resolve(path)
        if full_path.exists():
            shutil.rmtree(full_path) if full_path.is_dir() else full_path.unlink()

    async def get_download_url(self, path: str, expires_in_seconds: int = 3600) -> str:
        # Local disk has no equivalent to an S3 pre-signed URL. This is an
        # intentional local/dev-only limitation, not a deferred TODO — any
        # real deployment sets STORAGE_BACKEND=s3 (fully implemented below)
        # and never reaches this path. A local dev server that specifically
        # needs to test the export-download flow can add a short-lived,
        # signed static-file route as a dev-only convenience if needed.
        raise NotImplementedError(
            "Local storage has no pre-signed URL equivalent — set STORAGE_BACKEND=s3 "
            "for any deployment that needs the export download flow to work."
        )


class S3FileStorage(FileStorage):
    """S3-backed storage — the production path. Uses boto3's async-wrapped
    client via aioboto3 rather than the sync boto3 client directly, since
    every other I/O path in this app (DB, HTTP calls, other storage ops)
    is async, and blocking the event loop on sync S3 calls would stall
    every other concurrent request the same worker is handling.
    """

    def __init__(self, bucket_name: str, region: str):
        self.bucket_name = bucket_name
        self.region = region
        self._session = aioboto3.Session()

    async def save(self, relative_path: str, content: bytes) -> str:
        async with self._session.client("s3", region_name=self.region) as s3:
            await s3.put_object(Bucket=self.bucket_name, Key=relative_path, Body=content)
        return relative_path

    async def read(self, path: str) -> bytes:
        async with self._session.client("s3", region_name=self.region) as s3:
            response = await s3.get_object(Bucket=self.bucket_name, Key=path)
            async with response["Body"] as stream:
                return await stream.read()

    async def delete_tree(self, path: str) -> None:
        """S3 has no real directories — 'deleting a tree' means listing and
        batch-deleting every object under the prefix. Paginated since a
        large repository could have more objects than a single list_objects_v2
        call returns (1000 max per page)."""
        async with self._session.client("s3", region_name=self.region) as s3:
            paginator = s3.get_paginator("list_objects_v2")
            async for page in paginator.paginate(Bucket=self.bucket_name, Prefix=path):
                contents = page.get("Contents", [])
                if not contents:
                    continue
                await s3.delete_objects(
                    Bucket=self.bucket_name,
                    Delete={"Objects": [{"Key": obj["Key"]} for obj in contents]},
                )

    async def get_download_url(self, path: str, expires_in_seconds: int = 3600) -> str:
        async with self._session.client("s3", region_name=self.region) as s3:
            return await s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": path},
                ExpiresIn=expires_in_seconds,
            )


def get_file_storage() -> FileStorage:
    settings = get_settings()
    if settings.STORAGE_BACKEND == "s3":
        return S3FileStorage(settings.S3_BUCKET_NAME, settings.S3_REGION)
    return LocalFileStorage(settings.LOCAL_STORAGE_ROOT)
