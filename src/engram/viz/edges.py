"""Derive graph edges from node content and recall history.

Edges in Engram are *derived*, not authored. Three sources:

- **shared-tag** — two nodes have ≥1 tag in common. Weight uses
  IDF-weighted Jaccard: rare tags dominate, blanket tags barely count.
  Tags appearing on more than ``edges.blanket_tag_threshold`` of the
  corpus are *excluded entirely* — they're metadata, not semantic links.
- **co-recall** — two nodes were returned by the same query (weight = count).
- **wiki-link** — node body explicitly references another node id via the
  ``[[node-id]]`` syntax (weight = 1.0).
- **manual** — added by hand through :func:`add_manual_edge`.

The derived sources are computed deterministically from the database. Calling
:func:`recompute_derived` is idempotent: it wipes the derived edge rows and
re-inserts the current truth.
"""

from __future__ import annotations

import math
import re
import sqlite3
from collections import Counter, defaultdict
from collections.abc import Iterable

from engram.config import Config

_WIKI_LINK_RE = re.compile(r"\[\[([a-z0-9][a-z0-9\-]+)\]\]")

# Edges below this weight are dropped to keep the graph from drowning in noise.
_MIN_SHARED_TAG_WEIGHT = 0.05
_MIN_CO_RECALL_COUNT = 2

# Tags appearing on more than this fraction of the corpus are treated as
# blanket metadata, not semantic links, and excluded from edge derivation.
_DEFAULT_BLANKET_TAG_THRESHOLD = 0.30
# Below this corpus size (in nodes), the blanket-tag heuristic is disabled —
# small corpora legitimately have tags on most nodes.
_BLANKET_TAG_MIN_CORPUS = 20


def _split_tags(csv: str | None) -> set[str]:
    if not csv:
        return set()
    return {t.strip() for t in csv.split(",") if t.strip()}


def _build_tag_stats(
    by_id: dict[str, set[str]],
    blanket_threshold: float,
    explicit_excludes: frozenset[str],
) -> tuple[frozenset[str], dict[str, float]]:
    """Return ``(blanket_tags, idf_by_tag)`` for the live corpus.

    ``blanket_tags`` are tags that should be skipped entirely during edge
    derivation (too common to be informative, or explicitly excluded).
    ``idf_by_tag`` maps every *retained* tag to ``log(N / df)`` for use as
    its weight contribution.
    """
    df: Counter[str] = Counter()
    for tags in by_id.values():
        for t in tags:
            df[t] += 1
    n_nodes = len(by_id)

    blanket: set[str] = set(explicit_excludes)
    if n_nodes >= _BLANKET_TAG_MIN_CORPUS:
        cap = max(2, int(n_nodes * blanket_threshold))
        for tag, freq in df.items():
            if freq > cap:
                blanket.add(tag)

    idf: dict[str, float] = {}
    for tag, freq in df.items():
        if tag in blanket:
            continue
        # +1 smoothing prevents idf=0 for tags on every retained node.
        idf[tag] = math.log((n_nodes + 1) / (freq + 1)) + 1.0
    return frozenset(blanket), idf


def derive_shared_tag_edges(
    conn: sqlite3.Connection,
    *,
    blanket_threshold: float = _DEFAULT_BLANKET_TAG_THRESHOLD,
    explicit_excludes: Iterable[str] = (),
) -> list[tuple[str, str, str, float]]:
    """Return ``(source, target, 'shared-tag', weight)`` for every node pair.

    Weight is an IDF-weighted Jaccard over the *retained* tags only:
    blanket tags (appearing on more than ``blanket_threshold`` of the corpus)
    are excluded entirely. This prevents one popular tag (e.g. a provenance
    marker on 80% of nodes) from gluing the whole graph into one cluster.
    """
    rows = conn.execute("SELECT id, tags FROM nodes WHERE quarantined = 0").fetchall()
    by_id: dict[str, set[str]] = {row["id"]: _split_tags(row["tags"]) for row in rows}
    blanket, idf = _build_tag_stats(
        by_id, blanket_threshold, frozenset(explicit_excludes)
    )

    # Project each node's tag set down to the retained vocabulary.
    retained: dict[str, set[str]] = {
        nid: tags - blanket for nid, tags in by_id.items()
    }

    ids = sorted(retained)
    out: list[tuple[str, str, str, float]] = []
    for i, a in enumerate(ids):
        tags_a = retained[a]
        if not tags_a:
            continue
        for b in ids[i + 1 :]:
            tags_b = retained[b]
            if not tags_b:
                continue
            shared = tags_a & tags_b
            if not shared:
                continue
            union = tags_a | tags_b
            shared_mass = sum(idf[t] for t in shared)
            union_mass = sum(idf[t] for t in union)
            if union_mass <= 0:
                continue
            weight = shared_mass / union_mass
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


def compute_blanket_tags(
    conn: sqlite3.Connection, *, config: Config | None = None
) -> frozenset[str]:
    """Return the set of tags treated as "blanket" (too common to be a link).

    Same rules and config knobs as :func:`recompute_derived`. Exposed so that
    other parts of the viewer (cluster naming, etc.) can stay aligned with the
    edge derivation logic instead of duplicating the threshold heuristic.
    """
    blanket_threshold = _DEFAULT_BLANKET_TAG_THRESHOLD
    explicit_excludes: Iterable[str] = ()
    if config is not None:
        blanket_threshold = float(
            config.get("edges", "blanket_tag_threshold", default=blanket_threshold)
        )
        explicit_excludes = tuple(
            config.get("edges", "exclude_tags", default=()) or ()
        )

    by_id: dict[str, set[str]] = {}
    for row in conn.execute(
        "SELECT id, tags FROM nodes WHERE quarantined = 0"
    ).fetchall():
        by_id[row["id"]] = _split_tags(row["tags"])

    blanket, _idf = _build_tag_stats(
        by_id, blanket_threshold, frozenset(explicit_excludes)
    )
    return blanket


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


def recompute_derived(
    conn: sqlite3.Connection, *, config: Config | None = None
) -> dict[str, int]:
    """Wipe non-manual edges and recompute from current node content.

    Returns
    -------
    dict[str, int]
        ``{edge_type: count}`` reflecting how many rows were inserted.
    """
    blanket_threshold = _DEFAULT_BLANKET_TAG_THRESHOLD
    explicit_excludes: Iterable[str] = ()
    if config is not None:
        blanket_threshold = float(
            config.get("edges", "blanket_tag_threshold", default=blanket_threshold)
        )
        explicit_excludes = tuple(
            config.get("edges", "exclude_tags", default=()) or ()
        )

    with conn:
        conn.execute("DELETE FROM edges WHERE edge_type != 'manual'")

    counts: dict[str, int] = {}
    counts["shared-tag"] = _insert_edges(
        conn,
        derive_shared_tag_edges(
            conn,
            blanket_threshold=blanket_threshold,
            explicit_excludes=explicit_excludes,
        ),
    )
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
