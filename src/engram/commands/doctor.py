"""``engram doctor`` — diagnostics for schema, FTS5, broken links, orphan files."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import click

from engram.config import load_config
from engram.core.db import connect, migrate
from engram.version import __version__


@click.command("doctor")
@click.pass_context
def doctor(ctx: click.Context) -> None:
    """Run diagnostic checks and print a health report.

    Phase 0 ships the structural checks: Python version, configuration source,
    database existence, schema version, FTS5 availability. Phase 1 adds
    broken-link detection and orphaned-file reconciliation.
    """
    config = load_config(ctx.obj.get("config_path") if ctx.obj else None)

    click.secho(f"engram {__version__}", bold=True)
    click.echo(f"  config source : {config.source or '(defaults only)'}")

    db_path_value = config.get("paths", "db", default="engram.db")
    db_path = Path(db_path_value)
    click.echo(f"  db path       : {db_path.resolve()}")

    if not db_path.is_file():
        click.secho(
            "  db status     : not yet created (run any write command to initialise)", fg="yellow"
        )
        return

    try:
        conn = connect(db_path)
    except sqlite3.Error as exc:
        click.secho(f"  db status     : ERROR ({exc})", fg="red")
        ctx.exit(3)

    try:
        applied = migrate(conn)
        if applied:
            click.echo(f"  migrations    : applied {len(applied)} new ({', '.join(applied)})")
        version_row = conn.execute(
            "SELECT COALESCE(MAX(version), 0) AS v FROM schema_version"
        ).fetchone()
        click.echo(f"  schema version: {version_row['v']}")

        fts_ok = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='nodes_fts'"
        ).fetchone()
        click.echo(f"  fts5 table    : {'present' if fts_ok else 'MISSING'}")

        node_count = conn.execute("SELECT COUNT(*) AS n FROM nodes").fetchone()["n"]
        edge_count = conn.execute("SELECT COUNT(*) AS n FROM edges").fetchone()["n"]
        click.echo(f"  nodes / edges : {node_count} / {edge_count}")
    finally:
        conn.close()
