"""Markdown-aware chunker.

The chunker prefers semantic boundaries (markdown headers) over arbitrary
character counts. Fenced code blocks are always kept atomic — a chunker
that splits a code fence has produced something worse than useless.

Strategy, in order:

1. **Header split** — if the text has any ``#``-prefixed headers, split on
   them (each chunk is the header + everything until the next header of
   the same or shallower level).
2. **Recursive character split** — for header sections that exceed the
   target size, fall back to ``RecursiveCharacterTextSplitter`` (paragraph
   → line → sentence → word).
3. **Code-fence atomicity** — at every step, if a candidate cut falls
   inside a ``` ``` ``` block, the cut is moved to the block's boundary.

The chunker is deliberately *not* aware of the source language or the
embedding model — it produces text chunks; downstream code decides what
to index.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)


@dataclass(frozen=True)
class Chunk:
    """A single chunk of text plus metadata recovered from its header path."""

    text: str
    headers: tuple[str, ...]  # ordered from H1 to Hn; empty if no header context

    @property
    def title(self) -> str:
        """The most-specific header, or the first non-blank line as a fallback."""
        if self.headers:
            return self.headers[-1]
        for line in self.text.splitlines():
            stripped = line.strip().lstrip("#").strip()
            if stripped:
                return stripped[:120]
        return "(untitled)"


_HEADER_LEVELS: list[tuple[str, str]] = [
    ("#", "h1"),
    ("##", "h2"),
    ("###", "h3"),
    ("####", "h4"),
]


_CODE_FENCE = re.compile(r"```")


def _has_unbalanced_fence(text: str) -> bool:
    """True if ``text`` contains an odd number of ``` markers."""
    return len(_CODE_FENCE.findall(text)) % 2 == 1


def _glue_split_fences(pieces: list[str]) -> list[str]:
    """Repair pieces that were split mid-code-fence.

    If ``pieces[i]`` has an unbalanced fence, it is concatenated with
    subsequent pieces until balance is restored or the list ends.
    """
    glued: list[str] = []
    buffer = ""
    for piece in pieces:
        if buffer:
            buffer = buffer + "\n" + piece
            if not _has_unbalanced_fence(buffer):
                glued.append(buffer)
                buffer = ""
        elif _has_unbalanced_fence(piece):
            buffer = piece
        else:
            glued.append(piece)
    if buffer:
        # Final stranded fence — emit as-is rather than lose content.
        glued.append(buffer)
    return glued


def chunk(
    text: str,
    *,
    target_chunk_size: int = 1200,
    chunk_overlap: int = 100,
) -> list[Chunk]:
    """Split ``text`` into header-aware, code-fence-safe chunks.

    Parameters
    ----------
    text
        The full input markdown.
    target_chunk_size
        Soft upper bound on chunk character length. Header-only chunks may
        exceed this if their body has no internal structure to split on,
        in which case the recursive splitter activates.
    chunk_overlap
        Characters of overlap when the recursive splitter activates.

    Returns
    -------
    list[Chunk]
        One :class:`Chunk` per resulting piece, with headers preserved.
    """
    text = text.strip()
    if not text:
        return []

    splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=_HEADER_LEVELS,
        strip_headers=False,
    )
    header_docs = splitter.split_text(text)

    if not header_docs:
        # No headers at all → treat the whole text as one anonymous chunk and
        # let the recursive splitter decide whether to subdivide it.
        return _recursive_fallback(text, (), target_chunk_size, chunk_overlap)

    chunks: list[Chunk] = []
    for doc in header_docs:
        headers = tuple(
            doc.metadata[key]
            for _, key in _HEADER_LEVELS
            if key in doc.metadata and doc.metadata[key]
        )
        body = doc.page_content
        if len(body) <= target_chunk_size and not _has_unbalanced_fence(body):
            chunks.append(Chunk(text=body, headers=headers))
            continue
        chunks.extend(_recursive_fallback(body, headers, target_chunk_size, chunk_overlap))
    return chunks


def _recursive_fallback(
    text: str,
    headers: tuple[str, ...],
    target_chunk_size: int,
    chunk_overlap: int,
) -> list[Chunk]:
    """Split ``text`` with the recursive character splitter, preserving fences."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=target_chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    pieces = splitter.split_text(text)
    pieces = _glue_split_fences(pieces)
    return [Chunk(text=piece.strip(), headers=headers) for piece in pieces if piece.strip()]
