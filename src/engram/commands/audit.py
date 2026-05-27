"""``engram audit`` — view the audit log."""

from __future__ import annotations

import click

from engram.commands._shared import resolve_paths


@click.command("audit")
@click.option("--op", default=None, help="Filter by operation name (store, recall, ...).")
@click.option("--since", default=None, help="ISO date; show entries on or after.")
@click.option("--tail", type=int, default=50, show_default=True, help="Number of entries to show.")
@click.pass_context
def audit(ctx: click.Context, op: str | None, since: str | None, tail: int) -> None:
    """Show recent audit log entries."""
    _, conn, _, _ = resolve_paths(ctx)
    try:
        sql = "SELECT id, ts, op, payload FROM audit_log WHERE 1=1"
        params: list[object] = []
        if op is not None:
            sql += " AND op = ?"
            params.append(op)
        if since is not None:
            sql += " AND ts >= ?"
            params.append(since)
        sql += " ORDER BY id DESC LIMIT ?"
        params.append(tail)
        rows = conn.execute(sql, params).fetchall()
    finally:
        conn.close()

    if not rows:
        click.echo("(no matching audit entries)")
        return
    for row in rows:
        click.echo(f"{row['ts']}  {row['op']:<10}  {row['payload']}")
