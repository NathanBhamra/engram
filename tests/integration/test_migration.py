"""Database migration tests."""

from __future__ import annotations

from pathlib import Path

from engram.core.db import connect, migrate, open_and_migrate


def test_migrate_brings_fresh_db_to_current(tmp_path: Path) -> None:
    db = tmp_path / "engram.db"
    conn = connect(db)
    applied = migrate(conn)
    assert applied, "Expected at least one migration to be applied on a fresh db"
    row = conn.execute("SELECT MAX(version) AS v FROM schema_version").fetchone()
    assert row["v"] >= 1
    conn.close()


def test_migrate_is_idempotent(tmp_path: Path) -> None:
    db = tmp_path / "engram.db"
    conn = open_and_migrate(db)
    second = migrate(conn)
    assert second == [], "Re-running migrations should be a no-op"
    conn.close()


def test_fts5_table_is_queryable(tmp_path: Path) -> None:
    db = tmp_path / "engram.db"
    conn = open_and_migrate(db)
    result = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='nodes_fts'"
    ).fetchone()
    assert result is not None
    conn.execute("SELECT * FROM nodes_fts WHERE nodes_fts MATCH 'anything' LIMIT 1").fetchall()
    conn.close()


def test_foreign_keys_enabled(tmp_path: Path) -> None:
    db = tmp_path / "engram.db"
    conn = open_and_migrate(db)
    fk = conn.execute("PRAGMA foreign_keys").fetchone()[0]
    assert fk == 1
    conn.close()
