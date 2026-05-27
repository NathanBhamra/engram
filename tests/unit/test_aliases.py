"""Tests for :mod:`engram.core.aliases`."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from engram.core import aliases
from engram.core.db import open_and_migrate


@pytest.fixture()
def conn(tmp_path: Path) -> sqlite3.Connection:
    db = tmp_path / "engram.db"
    return open_and_migrate(db)


def test_add_inserts_pairs(conn: sqlite3.Connection) -> None:
    n = aliases.add(conn, "aristotle", "philosopher", "stagirite")
    assert n == 2
    assert ("aristotle", "philosopher") in aliases.list_all(conn)
    assert ("aristotle", "stagirite") in aliases.list_all(conn)


def test_add_normalises_case_and_skips_self(conn: sqlite3.Connection) -> None:
    n = aliases.add(conn, "FOO", "foo", "BAR")
    assert n == 1
    assert ("foo", "bar") in aliases.list_all(conn)


def test_add_rejects_short_canonical(conn: sqlite3.Connection) -> None:
    with pytest.raises(ValueError):
        aliases.add(conn, "a", "alpha")


def test_expand_bidirectional(conn: sqlite3.Connection) -> None:
    aliases.add(conn, "aristotle", "philosopher")
    result = aliases.expand(conn, ["philosopher", "unknown"])
    assert "aristotle" in result["philosopher"]
    assert result["unknown"] == {"unknown"}


def test_remove_deletes(conn: sqlite3.Connection) -> None:
    aliases.add(conn, "foo", "bar")
    assert aliases.remove(conn, "foo", "bar") == 1
    assert aliases.list_all(conn) == []
