"""Tests for :mod:`engram.viz.metrics`."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from engram.core.db import open_and_migrate
from engram.viz import edges as edges_mod
from engram.viz import metrics


def _add_node(conn: sqlite3.Connection, node_id: str, *, tags: str = "") -> None:
    conn.execute(
        "INSERT INTO nodes (id, path, title, body, node_type, tags, ttl_days) "
        "VALUES (?, ?, ?, 'x', 'fact', ?, 14)",
        (node_id, f"{node_id}.md", node_id, tags),
    )
    conn.commit()


@pytest.fixture()
def conn(tmp_path: Path) -> sqlite3.Connection:
    return open_and_migrate(tmp_path / "engram.db")


def test_recompute_on_empty_graph(conn: sqlite3.Connection) -> None:
    stats = metrics.recompute(conn)
    assert stats == {"nodes": 0, "edges": 0, "clusters": 0}


def test_recompute_writes_degree_and_pagerank(conn: sqlite3.Connection) -> None:
    _add_node(conn, "a", tags="qa")
    _add_node(conn, "b", tags="qa")
    _add_node(conn, "c", tags="qa")
    edges_mod.recompute_derived(conn)  # builds shared-tag triangle
    stats = metrics.recompute(conn)
    assert stats["nodes"] == 3
    row = conn.execute("SELECT degree, pagerank, cluster_id FROM nodes WHERE id='a'").fetchone()
    assert row["degree"] >= 1
    assert row["pagerank"] > 0
    assert row["cluster_id"] is not None


def test_graph_stats_returns_dict(conn: sqlite3.Connection) -> None:
    _add_node(conn, "a")
    stats = metrics.graph_stats(conn)
    assert stats["nodes"] == 1
    assert "edges" in stats
    assert "stale" in stats
