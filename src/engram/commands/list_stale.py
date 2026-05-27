"""``engram list-stale`` — list past-TTL nodes."""

from __future__ import annotations

import click

from engram.commands._shared import resolve_paths


@click.command("list-stale")
@click.option(
    "--type",
    "node_type",
    type=click.Choice(["fact", "pattern", "decision", "reference"]),
    default=None,
    help="Filter by node type.",
)
@click.option("--quarantine", is_flag=True, default=False, help="Only show quarantined nodes.")
@click.pass_context
def list_stale(ctx: click.Context, node_type: str | None, quarantine: bool) -> None:
    """List nodes past their TTL."""
    _, conn, _, _ = resolve_paths(ctx)
    try:
        sql = """
            SELECT id, title, node_type, ttl_days, verified_on, quarantined,
                   CAST(julianday('now') - julianday(verified_on) AS INTEGER) AS age_days
              FROM nodes
             WHERE verified_on IS NOT NULL
               AND (julianday('now') - julianday(verified_on)) > ttl_days
        """
        params: list[object] = []
        if node_type is not None:
            sql += " AND node_type = ?"
            params.append(node_type)
        if quarantine:
            sql += " AND quarantined = 1"
        sql += " ORDER BY age_days DESC"
        rows = conn.execute(sql, params).fetchall()
    finally:
        conn.close()

    if not rows:
        click.echo("No stale nodes.")
        return
    for row in rows:
        flag = "Q" if row["quarantined"] else " "
        click.echo(
            f"{flag} {row['id']}  age={row['age_days']}d  ttl={row['ttl_days']}d  "
            f"type={row['node_type']}  {row['title']}"
        )
