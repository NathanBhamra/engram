"""``engram recall`` — return ranked relevant chunks for a query."""

from __future__ import annotations

import json
import sqlite3

import click

from engram.commands._shared import resolve_paths
from engram.recall import fts, ranking


@click.command("recall")
@click.argument("query")
@click.option("--top", "top_n", type=int, default=None, help="Maximum chunks to return.")
@click.option(
    "--budget",
    "token_budget",
    type=int,
    default=None,
    help="Approximate token budget across returned chunks.",
)
@click.option(
    "--json", "as_json", is_flag=True, default=False, help="Emit JSON instead of formatted text."
)
@click.option(
    "--include-stale",
    is_flag=True,
    default=False,
    help="Include past-TTL or quarantined nodes in results.",
)
@click.pass_context
def recall(
    ctx: click.Context,
    query: str,
    top_n: int | None,
    token_budget: int | None,
    as_json: bool,
    include_stale: bool,
) -> None:
    """Recall nodes matching QUERY."""
    config, conn, _, _ = resolve_paths(ctx)
    top_n = top_n if top_n is not None else config.get("recall", "top_n", default=3)
    token_budget = (
        token_budget
        if token_budget is not None
        else config.get("recall", "token_budget", default=1000)
    )
    expand_aliases = config.get("recall", "expand_aliases", default=True)

    try:
        hits = fts.search(
            conn,
            query,
            limit=top_n * 5,
            include_stale=include_stale,
            expand_aliases=expand_aliases,
        )
        _log_recall(conn, query, hits)
    finally:
        conn.close()

    ranked = ranking.rerank(hits)
    selected = ranking.select(ranked, top_n=top_n, token_budget=token_budget)

    if as_json:
        click.echo(
            json.dumps(
                [
                    {
                        "id": r.hit.node_id,
                        "title": r.hit.title,
                        "body": r.hit.body,
                        "type": r.hit.node_type,
                        "tags": list(r.hit.tags),
                        "bm25": r.hit.bm25,
                        "score": r.score,
                        "age_days": r.age_days,
                        "past_ttl": r.past_ttl,
                        "ttl_days": r.hit.ttl_days,
                    }
                    for r in selected
                ],
                indent=2,
            )
        )
        return

    if not selected:
        click.echo(f"No results for: {query}")
        return

    for r in selected:
        banner = ranking.stale_banner(r.age_days, r.hit.ttl_days)
        click.echo(f"## {r.hit.title}  {banner}")
        click.echo(
            f"   id={r.hit.node_id}  type={r.hit.node_type}  " f"tags={','.join(r.hit.tags) or '-'}"
        )
        click.echo("")
        click.echo(r.hit.body)
        click.echo("")
        click.echo("---")


def _log_recall(conn: sqlite3.Connection, query: str, hits: list[fts.Hit]) -> None:
    """Record this recall in the co-recall log so co-recall edges can form."""
    if not hits:
        return
    with conn:
        for hit in hits:
            conn.execute(
                "INSERT INTO co_recall_log (node_id, query) VALUES (?, ?)",
                (hit.node_id, query),
            )
