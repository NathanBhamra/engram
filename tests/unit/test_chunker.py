"""Tests for :mod:`engram.core.chunker`."""

from __future__ import annotations

from engram.core.chunker import chunk


def test_empty_returns_nothing() -> None:
    assert chunk("") == []


def test_no_headers_single_chunk() -> None:
    out = chunk("Just a sentence with no markdown structure to split on at all.")
    assert len(out) == 1
    assert out[0].headers == ()


def test_header_split_produces_one_per_section() -> None:
    text = "# A\nfirst section body here\n\n# B\nsecond section body here"
    out = chunk(text)
    titles = [c.title for c in out]
    assert "A" in titles
    assert "B" in titles


def test_code_fence_kept_atomic() -> None:
    body = "```python\n" + "x = 1\n" * 400 + "```\n"
    text = f"# Code section\n\n{body}\n"
    out = chunk(text, target_chunk_size=200, chunk_overlap=20)
    fence_starts = sum(c.text.count("```") for c in out)
    assert fence_starts % 2 == 0, "code fence was split"


def test_oversized_section_falls_back_to_recursive() -> None:
    text = "# Big\n\n" + ("paragraph one. " * 200) + "\n\n" + ("paragraph two. " * 200)
    out = chunk(text, target_chunk_size=300, chunk_overlap=20)
    assert len(out) > 1
    assert all(c.headers == ("Big",) for c in out)


def test_title_falls_back_to_first_line_when_no_header() -> None:
    out = chunk("First meaningful line.\nSecond line that follows.")
    assert out[0].title.startswith("First")
