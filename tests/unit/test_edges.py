"""Tests for :mod:`engram.viz.edges`."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from engram.core.db import open_and_migrate
from engram.viz import edges as edges_mod


def _add_node(conn: sqlite3.Connection, node_id: str, *, tags: str = "", body: str = "x") -> None:
    conn.execute(
        "INSERT INTO nodes (id, path, title, body, node_type, tags, ttl_days) "
        "VALUES (?, ?, ?, ?, 'fact', ?, 14)",
        (node_id, f"{node_id}.md", node_id, body, tags),
    )
    conn.commit()


@pytest.fixture()
def conn(tmp_path: Path) -> sqlite3.Connection:
    return open_and_migrate(tmp_path / "engram.db")


def test_shared_tag_edges_built(conn: sqlite3.Connection) -> None:
    _add_node(conn, "a", tags="qa,regression")
    _add_node(conn, "b", tags="qa,smoke")
    _add_node(conn, "c", tags="other")
    edges = edges_mod.derive_shared_tag_edges(conn)
    pairs = {(s, t) for s, t, _, _ in edges}
    assert ("a", "b") in pairs
    assert ("a", "c") not in pairs


def test_co_recall_edges_require_min_count(conn: sqlite3.Connection) -> None:
    _add_node(conn, "a")
    _add_node(conn, "b")
    _add_node(conn, "c")
    for query in ("q1", "q2"):
        conn.execute(
            "INSERT INTO co_recall_log (query, node_id) VALUES (?, 'a'), (?, 'b')",
            (query, query),
        )
    # 'c' only co-occurs once → must be filtered out.
    conn.execute("INSERT INTO co_recall_log (query, node_id) VALUES ('q3', 'a'), ('q3', 'c')")
    conn.commit()
    edges = edges_mod.derive_co_recall_edges(conn)
    pairs = {(s, t) for s, t, _, _ in edges}
    assert ("a", "b") in pairs
    assert ("a", "c") not in pairs


def test_wiki_link_edges_resolve_only_known_ids(conn: sqlite3.Connection) -> None:
    _add_node(conn, "alpha", body="see [[beta]] and also [[ghost]]")
    _add_node(conn, "beta")
    edges = edges_mod.derive_wiki_link_edges(conn)
    pairs = {(s, t) for s, t, _, _ in edges}
    assert ("alpha", "beta") in pairs
    assert ("alpha", "ghost") not in pairs


def test_recompute_derived_is_idempotent(conn: sqlite3.Connection) -> None:
    _add_node(conn, "a", tags="qa")
    _add_node(conn, "b", tags="qa")
    counts1 = edges_mod.recompute_derived(conn)
    counts2 = edges_mod.recompute_derived(conn)
    assert counts1 == counts2


def test_add_manual_edge_is_preserved_by_recompute(conn: sqlite3.Connection) -> None:
    _add_node(conn, "a")
    _add_node(conn, "b")
    edges_mod.add_manual_edge(conn, "a", "b")
    edges_mod.recompute_derived(conn)
    row = conn.execute(
        "SELECT edge_type FROM edges WHERE source_id='a' AND target_id='b'"
    ).fetchone()
    assert row["edge_type"] == "manual"
