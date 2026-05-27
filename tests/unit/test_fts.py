"""Tests for :mod:`engram.recall.fts` query construction."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from engram.core import aliases
from engram.core.db import open_and_migrate
from engram.recall import fts


@pytest.fixture()
def conn(tmp_path: Path) -> sqlite3.Connection:
    return open_and_migrate(tmp_path / "engram.db")


def test_tokenise_strips_stopwords() -> None:
    assert fts.tokenise("the QUICK brown fox") == ["quick", "brown", "fox"]


def test_build_match_expression_simple() -> None:
    expr = fts.build_match_expression("engram storage", expand_aliases=False)
    assert "engram" in expr
    assert "storage" in expr
    assert " AND " in expr


def test_build_match_expression_empty_for_stopwords_only() -> None:
    assert fts.build_match_expression("the and of") == ""


def test_alias_expansion_adds_or_clauses(conn: sqlite3.Connection) -> None:
    aliases.add(conn, "engram", "memex")
    expr = fts.build_match_expression("engram", conn=conn, expand_aliases=True)
    assert "engram" in expr
    assert "memex" in expr
    assert " OR " in expr


def test_search_returns_inserted_node(conn: sqlite3.Connection) -> None:
    conn.execute(
        "INSERT INTO nodes (id, path, title, body, node_type, ttl_days) "
        "VALUES (?, ?, ?, ?, 'fact', 14)",
        (
            "foo-1",
            "foo-1.md",
            "Foo",
            "the quick brown fox jumps over the lazy dog",
        ),
    )
    conn.commit()
    hits = fts.search(conn, "brown fox", expand_aliases=False)
    assert len(hits) == 1
    assert hits[0].node_id == "foo-1"
