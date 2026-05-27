"""SQLite -> vis-network JSON exporter."""

from __future__ import annotations

import datetime as _dt
import sqlite3
from typing import Any

from engram.viz import theme as theme_mod


def _is_past_ttl(verified_on: str | None, ttl_days: int) -> tuple[bool, int | None]:
    if not verified_on:
        return False, None
    try:
        dt = _dt.datetime.fromisoformat(verified_on)
    except ValueError:
        return False, None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=_dt.UTC)
    age_days = (_dt.datetime.now(_dt.UTC) - dt).days
    return age_days > ttl_days, age_days


def export(
    conn: sqlite3.Connection,
    *,
    theme: theme_mod.Theme | None = None,
    include_quarantined: bool = False,
) -> dict[str, Any]:
    """Return a vis-network compatible ``{nodes, edges, meta}`` payload."""
    theme = theme or theme_mod.DARK

    node_sql = (
        "SELECT id, title, body, node_type, tags, degree, cluster_id, pagerank, "
        "       verified_on, ttl_days, quarantined "
        "FROM nodes"
    )
    if not include_quarantined:
        node_sql += " WHERE quarantined = 0"

    nodes: list[dict[str, Any]] = []
    for row in conn.execute(node_sql).fetchall():
        past_ttl, age_days = _is_past_ttl(row["verified_on"], row["ttl_days"])
        if row["quarantined"]:
            colour = theme.quarantine_colour
        elif past_ttl:
            colour = theme.stale_colour
        else:
            colour = theme.node_colours.get(row["node_type"], theme.foreground)
        body = (row["body"] or "").strip()
        nodes.append(
            {
                "id": row["id"],
                "label": row["title"],
                "title": _node_tooltip(row, past_ttl, age_days),
                "color": {
                    "background": "rgba(28,28,30,0.92)",
                    "border": colour,
                    "highlight": {
                        "background": colour,
                        "border": "#ffffff",
                    },
                    "hover": {
                        "background": "rgba(28,28,30,0.92)",
                        "border": colour,
                    },
                },
                "font": {
                    "color": "#ffffff",
                    "size": 13,
                    "face": 'Inter, -apple-system, "SF Pro Text", system-ui, sans-serif',
                },
                "engram": {
                    "title": row["title"],
                    "body": body,
                    "type": row["node_type"],
                    "tags": (row["tags"] or "").split(",") if row["tags"] else [],
                    "degree": int(row["degree"] or 0),
                    "pagerank": float(row["pagerank"] or 0.0),
                    "cluster": row["cluster_id"],
                    "verified_on": row["verified_on"],
                    "ttl_days": int(row["ttl_days"]),
                    "past_ttl": past_ttl,
                    "age_days": age_days,
                },
            }
        )

    edges: list[dict[str, Any]] = []
    for row in conn.execute(
        "SELECT id, source_id, target_id, edge_type, weight FROM edges"
    ).fetchall():
        edges.append(
            {
                "id": row["id"],
                "from": row["source_id"],
                "to": row["target_id"],
                "color": {"color": theme.edge_colours.get(row["edge_type"], "#777")},
                "width": _edge_width(row["edge_type"], float(row["weight"] or 1.0)),
                "engram": {
                    "type": row["edge_type"],
                    "weight": float(row["weight"] or 1.0),
                },
            }
        )

    return {
        "nodes": nodes,
        "edges": edges,
        "meta": {
            "node_count": len(nodes),
            "edge_count": len(edges),
            "exported_at": _dt.datetime.now(_dt.UTC).isoformat(),
            "theme": theme.name,
        },
    }


def _edge_width(edge_type: str, weight: float) -> float:
    """Scale edge weight to a sensible visible width."""
    if edge_type == "co-recall":
        return min(1.0 + weight * 0.3, 6.0)
    if edge_type == "shared-tag":
        return 0.5 + weight * 4.0  # weight is 0..1 jaccard
    if edge_type == "wiki-link":
        return 2.0
    return 1.5  # manual


def _node_tooltip(row: sqlite3.Row, past_ttl: bool, age_days: int | None) -> str:
    """Plain-text tooltip shown on hover (rich detail lives in the side panel)."""
    tags = (row["tags"] or "").replace(",", ", ")
    lines = [
        str(row["title"]),
        f"type: {row['node_type']}   degree: {row['degree']}",
        f"tags: {tags or '-'}",
    ]
    if age_days is not None:
        if past_ttl:
            lines.append(f"STALE — verified {age_days}d ago (ttl {row['ttl_days']}d)")
        else:
            lines.append(f"verified {age_days}d ago")
    else:
        lines.append("unverified")
    return "\n".join(lines)
