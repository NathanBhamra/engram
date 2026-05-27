"""SQLite connection management and schema migrations.

Engram stores all index data in a single SQLite database. The database is
*rebuildable*: markdown notes on disk are canonical, and any corruption is
recovered with ``engram rebuild --full``.

The migration runner is intentionally minimal: each migration is a single
``.sql`` file under :mod:`engram.core.schema` whose filename starts with a
zero-padded version number (``001_initial.sql``, ``002_embeddings.sql``,
...). The runner applies any file whose version is newer than the recorded
``schema_version`` row, in order, in a single transaction per file.
"""

from __future__ import annotations

import re
import sqlite3
from collections.abc import Iterable
from importlib import resources
from importlib.resources.abc import Traversable
from pathlib import Path
from typing import cast

SCHEMA_PACKAGE = "engram.core.schema"
_MIGRATION_RE = re.compile(r"^(\d{3})_.+\.sql$")


def connect(db_path: str | Path) -> sqlite3.Connection:
    """Open a SQLite connection with sensible Engram defaults.

    Foreign keys are enabled, WAL is requested (no-op if already set), and
    rows are returned as :class:`sqlite3.Row` for ergonomic column access.
    """
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def _current_version(conn: sqlite3.Connection) -> int:
    """Return the highest applied migration version, or ``0`` if none."""
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'"
    ).fetchone()
    if row is None:
        return 0
    row = conn.execute("SELECT COALESCE(MAX(version), 0) AS v FROM schema_version").fetchone()
    return cast(int, row["v"])


def _discover_migrations() -> list[tuple[int, str, str]]:
    """Return ``(version, filename, sql)`` triples sorted by version."""
    migrations: list[tuple[int, str, str]] = []
    files: Iterable[Traversable] = resources.files(SCHEMA_PACKAGE).iterdir()
    for entry in files:
        name = entry.name
        match = _MIGRATION_RE.match(name)
        if match is None:
            continue
        version = int(match.group(1))
        sql = entry.read_text(encoding="utf-8")
        migrations.append((version, name, sql))
    migrations.sort(key=lambda triple: triple[0])
    return migrations


def migrate(conn: sqlite3.Connection) -> list[str]:
    """Apply any outstanding migrations.

    Returns
    -------
    list[str]
        The names of migration files applied during this call (empty if the
        database was already up to date).
    """
    applied_now: list[str] = []
    current = _current_version(conn)
    for version, name, sql in _discover_migrations():
        if version <= current:
            continue
        with conn:
            conn.executescript(sql)
            # 001_initial.sql inserts its own version row; later migrations
            # should also INSERT into schema_version, but we belt-and-braces
            # it here so partial scripts don't leave the DB in an undeclared
            # version state.
            conn.execute("INSERT OR IGNORE INTO schema_version (version) VALUES (?)", (version,))
        applied_now.append(name)
    return applied_now


def open_and_migrate(db_path: str | Path) -> sqlite3.Connection:
    """Convenience: open a connection and ensure schema is current."""
    conn = connect(db_path)
    migrate(conn)
    return conn
