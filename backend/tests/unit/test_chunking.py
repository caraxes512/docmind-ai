"""Unit tests for app.rag.chunking."""

import pytest

from app.rag.chunking import MAX_CHUNK_CHARS, chunk_file

pytestmark = pytest.mark.unit


def test_no_symbols_short_file_becomes_single_chunk():
    content = "def x(): pass\n" * 3
    chunks = chunk_file(content, [])
    assert len(chunks) == 1
    assert chunks[0].symbol_name is None


def test_no_symbols_tiny_content_produces_no_chunks():
    """Below MIN_CHUNK_CHARS, not worth its own embedding."""
    assert chunk_file("x=1", []) == []


def test_no_symbols_oversized_file_splits_into_sliding_windows():
    content = "a" * (MAX_CHUNK_CHARS * 3)
    chunks = chunk_file(content, [])
    assert len(chunks) > 1
    assert all(len(c.content) <= MAX_CHUNK_CHARS for c in chunks)


def test_sliding_window_covers_full_content():
    content = "a" * (MAX_CHUNK_CHARS * 3)
    chunks = chunk_file(content, [])
    overlap = 200
    total_span_covered = (len(chunks) - 1) * (MAX_CHUNK_CHARS - overlap) + len(chunks[-1].content)
    assert total_span_covered >= len(content)


def _realistic_line(i: int) -> str:
    return f"    print('this is a realistic line of code number {i} in the function body')"


def test_symbol_aware_chunking_produces_one_chunk_per_symbol():
    source_lines = [_realistic_line(i) for i in range(1, 21)]
    source = "\n".join(source_lines)
    symbols = [
        {"name": "func_a", "start_line": 1, "end_line": 5},
        {"name": "func_b", "start_line": 6, "end_line": 20},
    ]
    chunks = chunk_file(source, symbols)
    assert len(chunks) == 2
    assert {c.symbol_name for c in chunks} == {"func_a", "func_b"}


def test_symbol_chunk_line_range_matches_symbol():
    source_lines = [_realistic_line(i) for i in range(1, 21)]
    source = "\n".join(source_lines)
    symbols = [{"name": "func_a", "start_line": 1, "end_line": 5}]
    chunks = chunk_file(source, symbols)
    assert chunks[0].start_line == 1
    assert chunks[0].end_line == 5


def test_symbol_chunk_content_matches_exact_line_range():
    source_lines = [_realistic_line(i) for i in range(1, 21)]
    source = "\n".join(source_lines)
    symbols = [{"name": "func_a", "start_line": 1, "end_line": 5}]
    chunks = chunk_file(source, symbols)
    # Compare line-by-line, NOT via .strip() on the whole block — strip()
    # only trims the first/last line's edges, not each line's indentation.
    assert chunks[0].content.splitlines() == source_lines[0:5]


def test_symbol_below_min_chunk_chars_is_skipped():
    tiny_symbols = [{"name": "tiny", "start_line": 1, "end_line": 1}]
    assert chunk_file("x", tiny_symbols) == []


def test_oversized_symbol_splits_but_retains_symbol_name():
    big_source = "realistic_line_of_code_content\n" * 1000
    symbols = [{"name": "huge_func", "start_line": 1, "end_line": 1000}]
    chunks = chunk_file(big_source, symbols)
    assert len(chunks) > 1
    assert all(c.symbol_name == "huge_func" for c in chunks)
