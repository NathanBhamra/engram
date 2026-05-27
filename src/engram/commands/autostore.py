"""``engram autostore`` — per-turn auto-store hook.

This is the command Engram-aware agents should invoke at the end of every
meaningful turn. It's a thin wrapper around ``engram store`` with three
opinionated changes that make it safe to call unconditionally:

1. Always succeeds (exit code 0) whether the content is stored or rejected.
   Agents and wrapper scripts can pipe blindly without error handling.
2. Quiet by default — nothing on stdout unless ``--verbose`` is set, so it
   never clutters agent output. Pass ``--json`` for machine-readable results.
3. Always audit-logs the verdict (accept or reject) with the full signal
   breakdown, so the operator can review the filter's decisions weekly.

The worthiness filter still does the gating; this command just removes the
ceremony around invoking it.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from engram.commands._shared import resolve_paths
from engram.core import storage


@click.command("autostore")
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
    help="Node type if content is accepted.",
)
@click.option("--tag", "tags", multiple=True, help="Tag (repeatable).")
@click.option("--session", "session_id", default=None, help="Originating session ID.")
@click.option(
    "--force", is_flag=True, default=False,
    help="Bypass the worthiness filter. Use only when you KNOW the content is valuable.",
)
@click.option("--verbose", is_flag=True, default=False, help="Print the verdict to stdout.")
@click.option("--json", "as_json", is_flag=True, default=False, help="Emit JSON result on stdout.")
@click.pass_context
def autostore(
    ctx: click.Context,
    file_path: Path | None,
    node_type: str,
    tags: tuple[str, ...],
    session_id: str | None,
    force: bool,
    verbose: bool,
    as_json: bool,
) -> None:
    """Pipe a turn's content through Engram. Filter decides; audit log records."""
    text = file_path.read_text(encoding="utf-8") if file_path is not None else sys.stdin.read()
    if not text.strip():
        # Empty input is never an error in autostore mode — agents may pipe blanks.
        if as_json:
            click.echo(json.dumps({"stored": 0, "rejected": 0, "skipped": "empty input"}))
        elif verbose:
            click.echo("(empty input — nothing to autostore)")
        return

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

    if as_json:
        click.echo(json.dumps({
            "stored": outcome.store_count,
            "rejected": outcome.reject_count,
            "stored_ids": [n.id for n in outcome.stored],
            "rejected_reasons": [{"title": t, "reason": r} for t, r in outcome.rejected],
            "redactions": dict(outcome.redactions),
        }))
    elif verbose:
        click.echo(
            f"autostore: {outcome.store_count} stored, {outcome.reject_count} rejected"
        )
        for note in outcome.stored:
            click.echo(f"  + {note.id}  {note.title}")
        for title, reason in outcome.rejected:
            click.echo(f"  - {title}  ({reason})")
    # Exit 0 unconditionally — never let autostore fail a calling script.
