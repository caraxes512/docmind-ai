"""Unit tests for app.services.zip_extraction — the zip-slip and zip-bomb
protections from Step 5. These are security-critical and were, notably,
never actually executed against a crafted malicious archive until this
step — written correctly in Step 5 based on careful reasoning, but "I
reasoned carefully" and "I verified it rejects a real attack payload" are
different confidence levels, and this closes that gap.
"""

import zipfile
from io import BytesIO
from pathlib import Path

import pytest

from app.core.exceptions import RepositoryProcessingError
from app.services.zip_extraction import validate_and_extract_zip

pytestmark = pytest.mark.unit


def _build_zip(entries: dict[str, bytes]) -> bytes:
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in entries.items():
            zf.writestr(name, content)
    return buffer.getvalue()


def test_valid_archive_extracts_successfully(tmp_path: Path):
    archive = _build_zip({"README.md": b"# Hello", "src/main.py": b"print('hi')"})
    result = validate_and_extract_zip(archive, tmp_path / "extracted")
    file_paths = {f.file_path for f in result}
    assert file_paths == {"README.md", "src/main.py"}


def test_extracted_content_hash_is_correct_sha256(tmp_path: Path):
    import hashlib
    content = b"print('hello world')"
    archive = _build_zip({"main.py": content})
    result = validate_and_extract_zip(archive, tmp_path / "extracted")
    assert result[0].content_hash == hashlib.sha256(content).hexdigest()


def test_rejects_invalid_zip_bytes(tmp_path: Path):
    with pytest.raises(RepositoryProcessingError, match="not a valid ZIP"):
        validate_and_extract_zip(b"this is not a zip file at all", tmp_path / "extracted")


# --- Zip-slip (path traversal) ---

def test_rejects_parent_directory_traversal(tmp_path: Path):
    archive = _build_zip({"../../etc/passwd": b"malicious"})
    with pytest.raises(RepositoryProcessingError, match="unsafe path"):
        validate_and_extract_zip(archive, tmp_path / "extracted")


def test_rejects_absolute_path_entry(tmp_path: Path):
    archive = _build_zip({"/etc/passwd": b"malicious"})
    with pytest.raises(RepositoryProcessingError, match="unsafe path"):
        validate_and_extract_zip(archive, tmp_path / "extracted")


def test_rejects_traversal_buried_in_a_deeper_path(tmp_path: Path):
    """A traversal attempt doesn't have to be at the start of the path —
    'src/../../outside/evil' also escapes the extraction root."""
    archive = _build_zip({"src/../../outside/evil.sh": b"malicious"})
    with pytest.raises(RepositoryProcessingError, match="unsafe path"):
        validate_and_extract_zip(archive, tmp_path / "extracted")


def test_traversal_check_runs_before_any_file_is_written(tmp_path: Path):
    """Fail-closed: a malicious entry anywhere in the archive aborts the
    WHOLE extraction, not just that one entry — verified by confirming a
    benign file earlier in the same archive was never written to disk."""
    destination = tmp_path / "extracted"
    archive = _build_zip({"innocent.txt": b"fine", "../escape.txt": b"malicious"})
    with pytest.raises(RepositoryProcessingError):
        validate_and_extract_zip(archive, destination)
    assert not (destination / "innocent.txt").exists()


# --- Zip-bomb (decompression bomb) ---

def test_rejects_archive_exceeding_declared_size_limit(tmp_path: Path, monkeypatch):
    from app.core.config import get_settings
    get_settings.cache_clear()
    monkeypatch.setenv("MAX_EXTRACTED_SIZE_BYTES", "100")
    get_settings.cache_clear()

    archive = _build_zip({"big.txt": b"x" * 1000})
    with pytest.raises(RepositoryProcessingError, match="zip bomb|exceeds the limit"):
        validate_and_extract_zip(archive, tmp_path / "extracted")

    get_settings.cache_clear()


def test_rejects_archive_exceeding_file_count_limit(tmp_path: Path, monkeypatch):
    from app.core.config import get_settings
    get_settings.cache_clear()
    monkeypatch.setenv("MAX_EXTRACTED_FILE_COUNT", "5")
    get_settings.cache_clear()

    archive = _build_zip({f"file_{i}.txt": b"x" for i in range(10)})
    with pytest.raises(RepositoryProcessingError, match="exceeding the limit"):
        validate_and_extract_zip(archive, tmp_path / "extracted")

    get_settings.cache_clear()


def test_directory_entries_are_skipped_not_extracted_as_files(tmp_path: Path):
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr(zipfile.ZipInfo("src/"), "")  # explicit directory entry
        zf.writestr("src/main.py", b"content")
    result = validate_and_extract_zip(buffer.getvalue(), tmp_path / "extracted")
    assert {f.file_path for f in result} == {"src/main.py"}
