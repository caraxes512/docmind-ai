"""Chunking strategy for RAG embedding.

Symbol-aware chunking (one chunk per class/function/method) is preferred
over fixed-size sliding windows: a chunk boundary that splits a function
in half produces an embedding that represents neither half well, and
retrieval quality suffers. Symbol boundaries come from ParsedSymbol rows
(Tree-sitter/AST output), computed once at ingestion — this module just
consumes them, it doesn't parse anything itself.

Fallback to sliding-window chunking applies to: files with no extracted
symbols (config files, markdown, plain text), and any single symbol whose
body exceeds MAX_CHUNK_CHARS (an unusually long function/class still needs
splitting, or the embedding input would be truncated by the provider).
"""

from dataclasses import dataclass

MAX_CHUNK_CHARS = 6000  # conservative w.r.t. typical embedding model context limits
MIN_CHUNK_CHARS = 40  # a fragment shorter than this isn't worth its own embedding
SLIDING_WINDOW_OVERLAP_CHARS = 200


@dataclass
class Chunk:
    content: str
    start_line: int
    end_line: int
    symbol_name: str | None  # None for sliding-window fallback chunks


def _split_oversized_text(text: str, start_line: int) -> list[Chunk]:
    """Sliding-window split for text exceeding MAX_CHUNK_CHARS, preserving
    approximate line numbers by counting newlines consumed so far."""
    chunks: list[Chunk] = []
    position = 0
    while position < len(text):
        window = text[position : position + MAX_CHUNK_CHARS]
        window_start_line = start_line + text[:position].count("\n")
        window_end_line = window_start_line + window.count("\n")
        chunks.append(
            Chunk(
                content=window,
                start_line=window_start_line,
                end_line=window_end_line,
                symbol_name=None,
            )
        )
        position += MAX_CHUNK_CHARS - SLIDING_WINDOW_OVERLAP_CHARS
    return chunks


def chunk_file(content: str, symbols: list[dict]) -> list[Chunk]:
    """`symbols`: list of {"name": str, "start_line": int, "end_line": int}
    for top-level classes/functions/methods in this file (from ParsedSymbol
    rows) — NOT filtered to a specific kind; callers pass whichever symbol
    kinds they want chunked as their own unit (typically class/function/
    method, excluding api_route/db_model, which are metadata views over
    the same underlying function/class symbols, not separate source ranges).
    """
    lines = content.splitlines(keepends=True)
    total_lines = len(lines)

    if not symbols:
        if len(content.strip()) < MIN_CHUNK_CHARS:
            return []
        if len(content) <= MAX_CHUNK_CHARS:
            return [Chunk(content=content, start_line=1, end_line=total_lines, symbol_name=None)]
        return _split_oversized_text(content, start_line=1)

    chunks: list[Chunk] = []
    sorted_symbols = sorted(symbols, key=lambda s: s["start_line"])

    for symbol in sorted_symbols:
        # Lines are 1-indexed in ParsedSymbol; slice is 0-indexed and end-exclusive.
        start_idx = max(0, symbol["start_line"] - 1)
        end_idx = min(total_lines, symbol["end_line"])
        symbol_text = "".join(lines[start_idx:end_idx])

        if len(symbol_text.strip()) < MIN_CHUNK_CHARS:
            continue

        if len(symbol_text) <= MAX_CHUNK_CHARS:
            chunks.append(
                Chunk(
                    content=symbol_text,
                    start_line=symbol["start_line"],
                    end_line=symbol["end_line"],
                    symbol_name=symbol["name"],
                )
            )
        else:
            oversized_chunks = _split_oversized_text(symbol_text, start_line=symbol["start_line"])
            for c in oversized_chunks:
                c.symbol_name = symbol["name"]
            chunks.extend(oversized_chunks)

    return chunks
