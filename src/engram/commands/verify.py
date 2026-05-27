"""``engram verify`` — record verification of a node."""

from __future__ import annotations

import datetime as _dt

import click

from engram.commands._shared import resolve_paths


@click.command("verify")
@click.argument("node_id")
@click.option("--evidence", required=True, help="Evidence string (URL, ticket, commit, quote).")
@click.option("--ticket", "jira_ticket", default=None, help="Optional Jira ticket reference.")
@click.pass_context
def verify(ctx: click.Context, node_id: str, evidence: str, jira_ticket: str | None) -> None:
    """Mark NODE_ID as verified with evidence."""
    _, conn, _, _ = resolve_paths(ctx)
    try:
        row = conn.execute("SELECT id FROM nodes WHERE id = ?", (node_id,)).fetchone()
        if row is None:
            raise click.ClickException(f"unknown node id: {node_id}")
        now = _dt.datetime.now(_dt.UTC).isoformat()
        with conn:
            conn.execute(
                "UPDATE nodes SET verified_on = ?, quarantined = 0 WHERE id = ?",
                (now, node_id),
            )
            conn.execute(
                "INSERT INTO provenance (node_id, entry_type, jira_ticket, evidence) "
                "VALUES (?, 'verified', ?, ?)",
                (node_id, jira_ticket, evidence),
            )
    finally:
        conn.close()
    click.echo(f"Verified {node_id} at {now}")
