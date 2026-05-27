"""``engram rebuild`` — recompute the index from notes on disk."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import click

from engram.commands._shared import resolve_paths
from engram.core import notes as notes_mod


@click.command("rebuild")
@click.option(
    "--full",
    is_flag=True,
    default=False,
    help="Drop and rebuild every node row from notes on disk.",
)
@click.pass_context
def rebuild(ctx: click.Context, full: bool) -> None:
    """Rebuild derived index data."""
    _, conn, _, notes_dir = resolve_paths(ctx)
    try:
        if full:
            _full_rebuild(conn, notes_dir)
        _quarantine_past_ttl(conn)
    finally:
        conn.close()
    click.echo("Rebuild complete.")


def _full_rebuild(conn: sqlite3.Connection, notes_dir: Path) -> None:
    loaded = notes_mod.iter_notes(notes_dir)
    with conn:
        conn.execute("DELETE FROM nodes")
    for note in loaded:
        rel_path = f"{note.id}.md"
        tag_csv = ",".join(note.tags)
        verified_on = note.verified_on.isoformat() if note.verified_on else None
        with conn:
            conn.execute(
                """
                INSERT INTO nodes (id, path, title, body, node_type, tags, ttl_days, verified_on)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    note.id,
                    rel_path,
                    note.title,
                    note.body,
                    note.node_type,
                    tag_csv,
                    note.ttl_days,
                    verified_on,
                ),
            )
    click.echo(f"Loaded {len(loaded)} notes from disk.")


def _quarantine_past_ttl(conn: sqlite3.Connection) -> None:
    """Auto-quarantine nodes more than ``auto_quarantine_after_days`` past TTL."""
    with conn:
        cur = conn.execute(
            """
            UPDATE nodes
               SET quarantined = 1
             WHERE verified_on IS NOT NULL
               AND (julianday('now') - julianday(verified_on)) > (ttl_days + 30)
               AND quarantined = 0
            """,
        )
    if cur.rowcount:
        click.echo(f"Quarantined {cur.rowcount} long-stale node(s).")
