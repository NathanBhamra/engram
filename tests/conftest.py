"""Shared pytest fixtures."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from engram.core.db import open_and_migrate


@pytest.fixture
def tmp_db(tmp_path: Path) -> Iterator[Path]:
    """Yield a path to a fresh, migrated SQLite database."""
    db_path = tmp_path / "engram.db"
    conn = open_and_migrate(db_path)
    conn.close()
    yield db_path
