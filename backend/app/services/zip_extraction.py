"""Secure ZIP extraction for uploaded repositories.

Two distinct attack classes are guarded against here, both checked BEFORE
any file is written to disk (fail closed, not fail-and-cleanup):

1. Zip-slip (path traversal): a malicious archive entry named e.g.
   "../../etc/cron.d/evil" that, if naively joined with the extraction
   directory, writes outside it. Guarded via `_is_safe_member_path`.

2. Zip-bomb (decompression bomb): a small compressed file that expands to
   an enormous size (or an enormous number of files), exhausting disk or
   memory. Guarded via `MAX_EXTRACTED_SIZE_BYTES` / `MAX_EXTRACTED_FILE_COUNT`,
   checked against the archive's *declared* uncompressed sizes before
   extracting anything, not measured after the fact.
"""

import hashlib
import io
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from app.core.config import get_settings
from app.core.exceptions import RepositoryProcessingError


@dataclass
class ExtractedFileInfo:
    file_path: str  # relative, forward-slash, POSIX-style path
    size_bytes: int
    content_hash: str


def _is_safe_member_path(member_name: str) -> bool:
    """Rejects absolute paths, paths containing '..' segments, and paths
    that resolve outside a hypothetical extraction root — checked purely
    lexically against the archive-internal name, before any real
    filesystem path is constructed."""
    if member_name.startswith("/") or member_name.startswith("\\"):
        return False
    posix_path = PurePosixPath(member_name)
    return ".." not in posix_path.parts


def validate_and_extract_zip(zip_bytes: bytes, destination_dir: Path) -> list[ExtractedFileInfo]:
    """Validates the archive against size/count/path-safety limits, then
    extracts it into `destination_dir` (must already exist and be empty).
    Raises RepositoryProcessingError on any violation — callers should not
    attempt partial recovery, per the ingestion service's failure handling.
    """
    settings = get_settings()

    try:
        zip_file = zipfile.ZipFile(io.BytesIO(zip_bytes))
    except zipfile.BadZipFile as exc:
        raise RepositoryProcessingError("Uploaded file is not a valid ZIP archive") from exc

    infolist = zip_file.infolist()

    if len(infolist) > settings.MAX_EXTRACTED_FILE_COUNT:
        raise RepositoryProcessingError(
            f"Archive contains {len(infolist)} entries, exceeding the limit of "
            f"{settings.MAX_EXTRACTED_FILE_COUNT}"
        )

    total_declared_size = sum(info.file_size for info in infolist)
    if total_declared_size > settings.MAX_EXTRACTED_SIZE_BYTES:
        raise RepositoryProcessingError(
            f"Archive's declared uncompressed size ({total_declared_size} bytes) exceeds the limit of "
            f"{settings.MAX_EXTRACTED_SIZE_BYTES} bytes — possible zip bomb"
        )

    for info in infolist:
        if info.is_dir():
            continue
        if not _is_safe_member_path(info.filename):
            raise RepositoryProcessingError(
                f"Archive entry '{info.filename}' has an unsafe path (path traversal attempt)"
            )

    destination_dir.mkdir(parents=True, exist_ok=True)
    extracted: list[ExtractedFileInfo] = []

    for info in infolist:
        if info.is_dir():
            continue

        target_path = destination_dir / info.filename
        target_path.parent.mkdir(parents=True, exist_ok=True)

        with zip_file.open(info) as source, open(target_path, "wb") as target:
            hasher = hashlib.sha256()
            bytes_written = 0
            while chunk := source.read(1024 * 1024):
                bytes_written += len(chunk)
                # Defense in depth: re-check actual bytes written against the limit
                # even though we validated declared sizes above (declared sizes in
                # a crafted zip header can lie about the true decompressed size).
                if bytes_written > settings.MAX_EXTRACTED_SIZE_BYTES:
                    raise RepositoryProcessingError(
                        "Actual decompressed size exceeded the configured limit during extraction"
                    )
                hasher.update(chunk)
                target.write(chunk)

        extracted.append(
            ExtractedFileInfo(
                file_path=info.filename,
                size_bytes=bytes_written,
                content_hash=hasher.hexdigest(),
            )
        )

    return extracted
