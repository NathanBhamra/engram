"""``engram forget`` — delete a single node by id (curation primitive)."""

from __future__ import annotations

import json

import click

from engram.commands._shared import resolve_paths


@click.command("forget")
@click.argument("node_id")
@click.option(
    "--reason",
    default=None,
    help="Why this node is being removed. Recorded in the audit log.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Show what would be deleted without changing anything.",
)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    default=False,
    help="Skip the confirmation prompt.",
)
@click.pass_context
def forget(
    ctx: click.Context,
    node_id: str,
    reason: str | None,
    dry_run: bool,
    yes: bool,
) -> None:
    """Delete one node (and its on-disk note) by ID.

    Use this when a node is wrong, misleading, or was stored in error —
    a polluting smoke-test paste, an outdated fact, a mis-attributed
    ticket reference. Edges referencing the node are removed via the
    schema's ON DELETE CASCADE.

    The deletion is recorded to the audit log as ``op=node_forget`` with
    the id, title, tags, and optional reason — so curation actions are
    themselves traceable.
    """
    _, conn, _, notes_dir = resolve_paths(ctx)
    try:
        row = conn.execute(
            "SELECT id, title, tags, node_type, length(body) AS n FROM nodes WHERE id = ?",
            (node_id,),
        ).fetchone()
        if row is None:
            raise click.ClickException(f"No node with id {node_id!r}.")

        nid, title, tags, ntype, body_len = row
        click.echo(f"id     : {nid}")
        click.echo(f"title  : {title}")
        click.echo(f"type   : {ntype}")
        click.echo(f"tags   : {tags}")
        click.echo(f"body   : {body_len} chars")

        if dry_run:
            click.echo("(dry-run — no changes made)")
            return

        if not yes and not click.confirm("Forget this node?", default=False):
            click.echo("Aborted.")
            ctx.exit(1)

        payload = {
            "id": nid,
            "title": title,
            "tags": [t for t in (tags or "").split(",") if t],
            "node_type": ntype,
            "reason": reason or "",
        }
        with conn:
            conn.execute("DELETE FROM nodes WHERE id = ?", (nid,))
            conn.execute(
                "INSERT INTO audit_log (op, payload) VALUES (?, ?)",
                ("node_forget", json.dumps(payload)),
            )

        note_path = notes_dir / f"{nid}.md"
        removed_note = False
        if note_path.exists():
            note_path.unlink()
            removed_note = True

        click.echo(f"Forgot {nid}. Note file removed: {removed_note}.")
    finally:
        conn.close()
