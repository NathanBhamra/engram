"""``engram usage`` — corpus size, token estimates, and notional cost-savings.

This is a deliberately rough accounting view. The goal is to make the value of
the corpus visible at a glance: "how much knowledge is in here, and what would
it have cost to keep re-deriving it from chat?"

Token estimation uses the industry rule-of-thumb of ~4 characters per token for
English prose. Pricing is configurable via flags so the figures stay current as
model pricing changes.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import click

from engram.config import load_config
from engram.core.db import connect

CHARS_PER_TOKEN = 4.0


def _estimate_tokens(chars: int) -> int:
    return int(round(chars / CHARS_PER_TOKEN))


def _fmt_bytes(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.1f} {unit}" if unit != "B" else f"{n} B"
        n /= 1024  # type: ignore[assignment]
    return f"{n:.1f} GB"


@click.command("usage")
@click.option("--input-price", type=float, default=15.0, show_default=True,
              help="$/million input tokens (Opus 4.x list price).")
@click.option("--output-price", type=float, default=75.0, show_default=True,
              help="$/million output tokens (Opus 4.x list price).")
@click.option("--json", "as_json", is_flag=True, help="Emit machine-readable JSON.")
@click.pass_context
def usage(ctx: click.Context, input_price: float, output_price: float, as_json: bool) -> None:
    """Report corpus size, token estimates, and notional cost-savings."""
    config = load_config(ctx.obj.get("config_path") if ctx.obj else None)
    db_path = Path(config.get("paths", "db", default="engram.db"))

    if not db_path.is_file():
        click.secho("No database yet. Run any write command to initialise.", fg="yellow")
        ctx.exit(1)

    conn = connect(db_path)
    try:
        row = conn.execute(
            """
            SELECT COUNT(*)                                              AS nodes,
                   COALESCE(SUM(LENGTH(body)), 0)                        AS body_chars,
                   COALESCE(SUM(LENGTH(title)), 0)                       AS title_chars,
                   COALESCE(SUM(LENGTH(COALESCE(tags, ''))), 0)          AS tag_chars,
                   COALESCE(SUM(LENGTH(path)), 0)                        AS path_chars
            FROM nodes
            WHERE quarantined = 0
            """
        ).fetchone()
        edges = conn.execute("SELECT COUNT(*) AS n FROM edges").fetchone()["n"]
        by_type = conn.execute(
            "SELECT node_type, COUNT(*) AS n FROM nodes WHERE quarantined = 0 "
            "GROUP BY node_type ORDER BY n DESC"
        ).fetchall()
        try:
            db_bytes = db_path.stat().st_size
        except OSError:
            db_bytes = 0
    finally:
        conn.close()

    nodes = row["nodes"]
    body_chars = row["body_chars"]
    total_chars = body_chars + row["title_chars"] + row["tag_chars"]
    body_tokens = _estimate_tokens(body_chars)
    total_tokens = _estimate_tokens(total_chars)
    mean_tokens = (body_tokens // nodes) if nodes else 0

    # Hypothetical cost — what it would notionally cost to re-derive this body
    # from chat. Bracketed as input-replay and output-generation views; the
    # truth is somewhere between (or above, once you count the system prompt
    # baseline per turn).
    cost_in = body_tokens / 1_000_000 * input_price
    cost_out = body_tokens / 1_000_000 * output_price

    if as_json:
        click.echo(json.dumps({
            "nodes": nodes,
            "edges": edges,
            "by_type": {r["node_type"]: r["n"] for r in by_type},
            "body_chars": body_chars,
            "total_chars": total_chars,
            "body_tokens_estimate": body_tokens,
            "total_tokens_estimate": total_tokens,
            "mean_tokens_per_node": mean_tokens,
            "db_bytes": db_bytes,
            "pricing": {"input_per_m": input_price, "output_per_m": output_price},
            "notional_cost_usd": {"as_input": round(cost_in, 4), "as_output": round(cost_out, 4)},
            "chars_per_token_assumption": CHARS_PER_TOKEN,
        }, indent=2))
        return

    click.secho("engram usage", bold=True)
    click.echo(f"  nodes        : {nodes}")
    click.echo(f"  edges        : {edges}")
    if by_type:
        breakdown = ", ".join(f"{r['node_type']} {r['n']}" for r in by_type)
        click.echo(f"  by type      : {breakdown}")
    click.echo(f"  db on disk   : {_fmt_bytes(db_bytes)}")
    click.echo(f"  body chars   : {body_chars:,}")
    click.echo(f"  total chars  : {total_chars:,}   (body + title + tags)")
    click.secho("\nestimated tokens (~4 chars/token):", bold=True)
    click.echo(f"  body tokens  : ~{body_tokens:,}")
    click.echo(f"  total tokens : ~{total_tokens:,}")
    click.echo(f"  mean / node  : ~{mean_tokens}")
    click.secho(
        f"\nnotional cost to re-derive body from chat "
        f"(@ ${input_price:g}/M in, ${output_price:g}/M out):",
        bold=True,
    )
    click.echo(f"  as input replay : ${cost_in:.4f}")
    click.echo(f"  as output gen   : ${cost_out:.4f}")
    click.secho(
        "\nNote: figures are rough. Tokeniser varies by model; pricing changes.",
        fg="yellow",
    )
