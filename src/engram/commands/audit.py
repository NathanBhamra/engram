"""``engram audit`` — view the audit log."""

from __future__ import annotations

import json

import click

from engram.commands._shared import resolve_paths


@click.command("audit")
@click.option("--op", default=None, help="Filter by operation name (store, store_reject, recall, ...).")
@click.option("--since", default=None, help="ISO date; show entries on or after.")
@click.option("--tail", type=int, default=50, show_default=True, help="Number of entries to show.")
@click.option("--pretty", is_flag=True, default=False,
              help="Human-readable output with parsed signals + verdicts.")
@click.option("--json", "as_json", is_flag=True, default=False,
              help="Emit each entry as a JSON object on its own line.")
@click.pass_context
def audit(ctx: click.Context, op: str | None, since: str | None, tail: int,
          pretty: bool, as_json: bool) -> None:
    """Show recent audit log entries.

    Use ``--pretty`` for human review of autostore decisions:
    each entry renders as one line with the verdict, signal kinds, and a
    short reason. Use ``--json`` for scripted analysis.
    """
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

    if as_json:
        for row in rows:
            try:
                payload = json.loads(row["payload"]) if row["payload"] else {}
            except (TypeError, ValueError):
                payload = {"raw": row["payload"]}
            click.echo(json.dumps({"id": row["id"], "ts": row["ts"], "op": row["op"], **payload}))
        return

    if pretty:
        for row in rows:
            try:
                p = json.loads(row["payload"]) if row["payload"] else {}
            except (TypeError, ValueError):
                p = {}
            verdict = p.get("verdict", "")
            reason = p.get("reason", "")
            signals = p.get("signals") or {}
            kinds = [k for k, v in signals.items() if v]
            wc = p.get("word_count", "")
            tags = ",".join(p.get("tags", []) or [])
            title = (p.get("title") or p.get("id") or "")[:50]
            mark = {"store": "+", "store_reject": "-"}.get(row["op"], " ")
            click.echo(
                f"{row['ts']}  {mark} {verdict:<6} {row['op']:<12} "
                f"wc={wc:<4} kinds=[{','.join(kinds)}]  tags=[{tags}]  {title}"
            )
            if reason:
                click.echo(f"    reason: {reason}")
        return

    for row in rows:
        click.echo(f"{row['ts']}  {row['op']:<12}  {row['payload']}")
