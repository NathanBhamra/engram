"""Shared helpers for command implementations."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import click

from engram.config import Config, load_config
from engram.core.db import open_and_migrate


def resolve_paths(ctx: click.Context) -> tuple[Config, sqlite3.Connection, Path, Path]:
    """Load config, open the DB, ensure the notes dir exists.

    Returns
    -------
    (config, connection, db_path, notes_dir)
    """
    config = load_config(ctx.obj.get("config_path") if ctx.obj else None)
    base = config.source.parent if config.source else Path.cwd()
    db_path = (base / config.get("paths", "db", default="engram.db")).resolve()
    notes_dir = (base / config.get("paths", "notes_dir", default="notes")).resolve()
    notes_dir.mkdir(parents=True, exist_ok=True)
    conn = open_and_migrate(db_path)
    return config, conn, db_path, notes_dir
