"""Graph metrics: degree, Louvain communities, PageRank.

Computed metrics are written back to the ``nodes`` table so the exporter can
read them with a single SELECT and the viewer can colour/size accordingly.

The functions tolerate empty graphs and graphs with no edges.
"""

from __future__ import annotations

import sqlite3
from typing import Any, cast

import community as community_louvain
import networkx as nx


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
