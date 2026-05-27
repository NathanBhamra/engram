"""Derive graph edges from node content and recall history.

Edges in Engram are *derived*, not authored. Three sources:

- **shared-tag** — two nodes have ≥1 tag in common (weight = jaccard).
- **co-recall** — two nodes were returned by the same query (weight = count).
- **wiki-link** — node body explicitly references another node id via the
  ``[[node-id]]`` syntax (weight = 1.0).
- **manual** — added by hand through :func:`add_manual_edge`.

The derived sources are computed deterministically from the database. Calling
:func:`recompute_derived` is idempotent: it wipes the derived edge rows and
re-inserts the current truth.
"""

from __future__ import annotations

import re
import sqlite3
from collections import defaultdict
from collections.abc import Iterable

_WIKI_LINK_RE = re.compile(r"\[\[([a-z0-9][a-z0-9\-]+)\]\]")

# Edges below this weight are dropped to keep the graph from drowning in noise.
_MIN_SHARED_TAG_WEIGHT = 0.05
_MIN_CO_RECALL_COUNT = 2


def _split_tags(csv: str | None) -> set[str]:
    if not csv:
        return set()
    return {t.strip() for t in csv.split(",") if t.strip()}


def derive_shared_tag_edges(conn: sqlite3.Connection) -> list[tuple[str, str, str, float]]:
    """Return ``(source, target, 'shared-tag', weight)`` for every node pair."""
    rows = conn.execute("SELECT id, tags FROM nodes WHERE quarantined = 0").fetchall()
    by_id: dict[str, set[str]] = {row["id"]: _split_tags(row["tags"]) for row in rows}
    ids = sorted(by_id)
    out: list[tuple[str, str, str, float]] = []
    for i, a in enumerate(ids):
        tags_a = by_id[a]
        if not tags_a:
            continue
        for b in ids[i + 1 :]:
            tags_b = by_id[b]
            if not tags_b:
                continue
            shared = tags_a & tags_b
            if not shared:
                continue
            union = tags_a | tags_b
            weight = len(shared) / len(union)
            if weight >= _MIN_SHARED_TAG_WEIGHT:
                out.append((a, b, "shared-tag", weight))
    return out


def derive_co_recall_edges(conn: sqlite3.Connection) -> list[tuple[str, str, str, float]]:
    """Return ``(source, target, 'co-recall', weight)`` for nodes co-recalled."""
    rows = conn.execute(
        "SELECT query, node_id FROM co_recall_log WHERE query IS NOT NULL AND node_id IS NOT NULL"
    ).fetchall()
    by_query: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        by_query[row["query"]].add(row["node_id"])

    pair_counts: dict[tuple[str, str], int] = defaultdict(int)
    for nodes in by_query.values():
        ordered = sorted(nodes)
        for i, a in enumerate(ordered):
            for b in ordered[i + 1 :]:
                pair_counts[(a, b)] += 1

    return [
        (a, b, "co-recall", float(count))
        for (a, b), count in pair_counts.items()
        if count >= _MIN_CO_RECALL_COUNT
    ]


def derive_wiki_link_edges(conn: sqlite3.Connection) -> list[tuple[str, str, str, float]]:
    """Return ``(source, target, 'wiki-link', 1.0)`` for explicit ``[[id]]`` refs."""
    rows = conn.execute(
        "SELECT id, body FROM nodes WHERE quarantined = 0 AND body LIKE '%[[%'"
    ).fetchall()
    known_ids = {row["id"] for row in conn.execute("SELECT id FROM nodes").fetchall()}
    out: list[tuple[str, str, str, float]] = []
    for row in rows:
        source = row["id"]
        for match in _WIKI_LINK_RE.finditer(row["body"]):
            target = match.group(1)
            if target == source or target not in known_ids:
                continue
            out.append((source, target, "wiki-link", 1.0))
    return out


def _insert_edges(
    conn: sqlite3.Connection, edges: Iterable[tuple[str, str, str, float]]
) -> int:
    inserted = 0
    with conn:
        for source, target, edge_type, weight in edges:
            cur = conn.execute(
                "INSERT OR IGNORE INTO edges (source_id, target_id, edge_type, weight) "
                "VALUES (?, ?, ?, ?)",
                (source, target, edge_type, weight),
            )
            inserted += cur.rowcount or 0
    return inserted


def recompute_derived(conn: sqlite3.Connection) -> dict[str, int]:
    """Wipe non-manual edges and recompute from current node content.

    Returns
    -------
    dict[str, int]
        ``{edge_type: count}`` reflecting how many rows were inserted.
    """
    with conn:
        conn.execute("DELETE FROM edges WHERE edge_type != 'manual'")

    counts: dict[str, int] = {}
    counts["shared-tag"] = _insert_edges(conn, derive_shared_tag_edges(conn))
    counts["co-recall"] = _insert_edges(conn, derive_co_recall_edges(conn))
    counts["wiki-link"] = _insert_edges(conn, derive_wiki_link_edges(conn))
    return counts


def add_manual_edge(
    conn: sqlite3.Connection, source: str, target: str, weight: float = 1.0
) -> None:
    """Insert a manual edge. Idempotent on ``(source, target, 'manual')``."""
    with conn:
        conn.execute(
            "INSERT OR IGNORE INTO edges (source_id, target_id, edge_type, weight) "
            "VALUES (?, ?, 'manual', ?)",
            (source, target, weight),
        )
