"""Graph metrics: degree, Louvain communities, PageRank.

Computed metrics are written back to the ``nodes`` table so the exporter can
read them with a single SELECT and the viewer can colour/size accordingly.

The functions tolerate empty graphs and graphs with no edges.
"""

from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING, Any, cast

import community as community_louvain
import networkx as nx

if TYPE_CHECKING:
    from engram.config import Config


def _build_graph(conn: sqlite3.Connection) -> nx.Graph:
    """Build an undirected NetworkX graph from the current node/edge tables."""
    graph: nx.Graph = nx.Graph()
    for row in conn.execute("SELECT id FROM nodes WHERE quarantined = 0").fetchall():
        graph.add_node(row["id"])
    for row in conn.execute(
        "SELECT source_id, target_id, weight FROM edges"
    ).fetchall():
        if graph.has_node(row["source_id"]) and graph.has_node(row["target_id"]):
            graph.add_edge(
                row["source_id"],
                row["target_id"],
                weight=row["weight"] or 1.0,
            )
    return graph


def _louvain(graph: nx.Graph) -> dict[str, int]:
    """Run Louvain community detection. Returns ``{node_id: cluster_int}``."""
    if graph.number_of_nodes() == 0:
        return {}
    return cast(dict[str, int], community_louvain.best_partition(graph))


def recompute(conn: sqlite3.Connection) -> dict[str, int]:
    """Recompute degree, cluster_id, pagerank for every node.

    Returns
    -------
    dict[str, int]
        Summary stats: ``{"nodes": ..., "edges": ..., "clusters": ...}``.
    """
    graph = _build_graph(conn)
    degrees = dict(graph.degree())
    clusters = _louvain(graph)
    pagerank: dict[str, float] = {}
    if graph.number_of_nodes() > 0:
        pagerank = cast(dict[str, float], nx.pagerank(graph, weight="weight"))

    with conn:
        for node_id in graph.nodes:
            conn.execute(
                "UPDATE nodes SET degree = ?, cluster_id = ?, pagerank = ? WHERE id = ?",
                (
                    int(degrees.get(node_id, 0)),
                    int(clusters.get(node_id, 0)),
                    float(pagerank.get(node_id, 0.0)),
                    node_id,
                ),
            )

    return {
        "nodes": graph.number_of_nodes(),
        "edges": graph.number_of_edges(),
        "clusters": len(set(clusters.values())) if clusters else 0,
    }


def graph_stats(conn: sqlite3.Connection) -> dict[str, Any]:
    """Return small summary stats for the sidebar without recomputing."""
    nodes = conn.execute(
        "SELECT COUNT(*) AS n FROM nodes WHERE quarantined = 0"
    ).fetchone()["n"]
    edges = conn.execute("SELECT COUNT(*) AS n FROM edges").fetchone()["n"]
    clusters = conn.execute(
        "SELECT COUNT(DISTINCT cluster_id) AS n FROM nodes WHERE quarantined = 0"
    ).fetchone()["n"]
    stale = conn.execute(
        "SELECT COUNT(*) AS n FROM nodes "
        "WHERE verified_on IS NOT NULL "
        "AND (julianday('now') - julianday(verified_on)) > ttl_days"
    ).fetchone()["n"]
    return {"nodes": nodes, "edges": edges, "clusters": clusters, "stale": stale}


def tag_counts(conn: sqlite3.Connection, limit: int = 20) -> list[dict[str, Any]]:
    """Return the top ``limit`` tags by node-count for the active (non-quarantined) graph.

    Tags are stored as a comma-separated string on each node row. We split in
    SQL by recursively peeling off the first comma-delimited segment.
    """
    rows = conn.execute(
        "SELECT tags FROM nodes WHERE quarantined = 0 AND tags IS NOT NULL AND tags <> ''"
    ).fetchall()
    from collections import Counter

    counter: Counter[str] = Counter()
    for row in rows:
        tags = row["tags"] if isinstance(row, sqlite3.Row) else row[0]
        if not tags:
            continue
        for tag in str(tags).split(","):
            t = tag.strip()
            if t:
                counter[t] += 1
    return [
        {"tag": tag, "count": count}
        for tag, count in counter.most_common(limit)
    ]


def cluster_counts(
    conn: sqlite3.Connection, *, config: "Config | None" = None
) -> list[dict[str, Any]]:
    """Return per-cluster node counts for the active (non-quarantined) graph.

    Sorted by count desc. Each entry is ``{"cluster": int, "count": int,
    "label": str}``. ``label`` is auto-derived from the most distinctive tags
    in the cluster (see :func:`cluster_labels`); falls back to ``"cluster N"``
    when no tags are present.
    """
    rows = conn.execute(
        "SELECT cluster_id AS cid, COUNT(*) AS n "
        "FROM nodes WHERE quarantined = 0 "
        "GROUP BY cluster_id ORDER BY n DESC, cid ASC"
    ).fetchall()
    labels = cluster_labels(conn, config=config)
    return [
        {
            "cluster": int(row["cid"] if row["cid"] is not None else 0),
            "count": int(row["n"]),
            "label": labels.get(
                int(row["cid"] if row["cid"] is not None else 0),
                f"cluster {int(row['cid'] if row['cid'] is not None else 0)}",
            ),
        }
        for row in rows
    ]


def cluster_labels(
    conn: sqlite3.Connection,
    *,
    per_cluster: int = 2,
    config: "Config | None" = None,
) -> dict[int, str]:
    """Derive a human-readable name for each cluster from its node content.

    Uses a TF-IDF-style score per tag: how concentrated a tag is in this
    cluster versus the rest of the graph. Picks the top ``per_cluster`` tags
    and joins them with " · ". Blanket tags (those excluded by the edge
    deriver — meta/structural tags like ``via-semon`` or ``engram``) are
    skipped here too so cluster names surface *semantic* signal. When a
    cluster has no usable semantic tags, falls back to the most distinctive
    word from its node titles.

    Returns ``{cluster_id: label}``. Clusters with no usable signal are
    omitted; callers should fall back to ``f"cluster {cid}"``.
    """
    from collections import Counter, defaultdict
    from math import log
    import re as _re

    # Stay aligned with edge derivation: exclude the same blanket tags.
    from engram.viz import edges as _edges_mod

    blanket = _edges_mod.compute_blanket_tags(conn, config=config)

    rows = conn.execute(
        "SELECT cluster_id AS cid, tags, title "
        "FROM nodes WHERE quarantined = 0"
    ).fetchall()
    if not rows:
        return {}

    cluster_tags: dict[int, Counter[str]] = defaultdict(Counter)
    cluster_sizes: Counter[int] = Counter()
    cluster_titles: dict[int, list[str]] = defaultdict(list)
    tag_doc_freq: Counter[str] = Counter()

    for row in rows:
        cid_raw = row["cid"] if isinstance(row, sqlite3.Row) else row[0]
        if cid_raw is None:
            continue
        cid = int(cid_raw)
        cluster_sizes[cid] += 1
        title = (row["title"] if isinstance(row, sqlite3.Row) else row[2]) or ""
        if title:
            cluster_titles[cid].append(str(title))
        tags_raw = row["tags"] if isinstance(row, sqlite3.Row) else row[1]
        if not tags_raw:
            continue
        seen: set[str] = set()
        for tag in str(tags_raw).split(","):
            t = tag.strip().lower()
            if not t or t in blanket:
                continue
            cluster_tags[cid][t] += 1
            if t not in seen:
                tag_doc_freq[t] += 1
                seen.add(t)

    total_clusters = max(1, len(cluster_sizes))
    labels: dict[int, str] = {}

    # Stopwords for title fallback. Includes common markup leftovers, generic
    # filler words, and the user's name (which is everywhere and meaningless
    # as a cluster identifier on its own).
    stop = {
        "the", "a", "an", "and", "or", "of", "to", "in", "on", "for",
        "with", "is", "are", "be", "this", "that", "it", "as", "by",
        "at", "from", "but", "not", "no", "if", "so", "do", "does",
        "overview", "history", "checkpoint", "session", "added", "section",
        "note", "notes", "summary", "user", "users", "nathan", "said",
        "use", "used", "using", "via", "new", "old", "more", "than",
        "you", "your", "his", "her", "they", "them", "our", "we",
    }
    _word_re = _re.compile(r"[A-Za-z][A-Za-z0-9_\-]+")

    def _title_words(titles: list[str], n: int) -> list[str]:
        """Extract the n most distinctive non-stopword tokens from titles."""
        wc: Counter[str] = Counter()
        for title in titles:
            for tok in _word_re.findall(title.lower()):
                if tok in stop or len(tok) < 3 or len(tok) > 24:
                    continue
                wc[tok] += 1
        return [w for w, _ in wc.most_common(n)]

    for cid, size in cluster_sizes.items():
        tag_scores: list[tuple[str, float]] = []
        for tag, count in cluster_tags[cid].items():
            tf = count / size
            idf = log((total_clusters + 1) / (1 + tag_doc_freq[tag])) + 1.0
            tag_scores.append((tag, tf * idf))
        tag_scores.sort(key=lambda x: (-x[1], x[0]))
        picked = [t for t, _ in tag_scores[:per_cluster]]

        if not picked:
            # No semantic tag survived blanket-pruning.
            if size == 1 and cluster_titles[cid]:
                # Singleton: most honest label is the node's own title,
                # truncated. Beats inventing a tag-style name from one title.
                title = cluster_titles[cid][0].strip()
                if len(title) > 40:
                    title = title[:37].rstrip() + "…"
                if title:
                    labels[cid] = title
                continue
            picked = _title_words(cluster_titles[cid], per_cluster)

        if picked:
            labels[cid] = " · ".join(picked)

    return labels
