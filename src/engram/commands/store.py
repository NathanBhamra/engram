"""``engram store`` — write a node into the index."""

from __future__ import annotations

import sys
from pathlib import Path

import click

from engram.commands._shared import resolve_paths
from engram.core import storage


@click.command("store")
@click.option(
    "--file",
    "file_path",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Read input from FILE instead of stdin.",
)
@click.option(
    "--type",
    "node_type",
    type=click.Choice(["fact", "pattern", "decision", "reference"]),
    default="fact",
    show_default=True,
    help="Node type.",
)
@click.option("--tag", "tags", multiple=True, help="Tag (repeatable).")
@click.option("--session", "session_id", default=None, help="Originating session ID.")
@click.option(
    "--force", is_flag=True, default=False, help="Bypass the worthiness filter (use sparingly)."
)
@click.pass_context
def store(
    ctx: click.Context,
    file_path: Path | None,
    node_type: str,
    tags: tuple[str, ...],
    session_id: str | None,
    force: bool,
) -> None:
    """Store text from --file or stdin as one or more nodes."""
    text = file_path.read_text(encoding="utf-8") if file_path is not None else sys.stdin.read()
    if not text.strip():
        raise click.ClickException("nothing to store (input was empty)")

    config, conn, _, notes_dir = resolve_paths(ctx)
    try:
        outcome = storage.run(
            text=text,
            node_type=node_type,
            tags=tags,
            config=config,
            conn=conn,
            notes_dir=notes_dir,
            session_id=session_id,
            force=force,
        )
    finally:
        conn.close()

    click.echo(f"Stored {outcome.store_count} chunk(s); rejected {outcome.reject_count}.")
    for note in outcome.stored:
        click.echo(f"  + {note.id}  {note.title}")
    for title, reason in outcome.rejected:
        click.echo(f"  - {title}  ({reason})")
    if outcome.redactions:
        click.echo(f"Redactions: {dict(outcome.redactions)}")
