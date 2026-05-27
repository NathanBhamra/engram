"""Tests for :mod:`engram.viz.exporter` and :mod:`engram.viz.renderer`."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from engram.core.db import open_and_migrate
from engram.viz import edges as edges_mod
from engram.viz import exporter, metrics, renderer, theme


def _seed(conn: sqlite3.Connection) -> None:
    rows = [
        ("a", "qa,regression", "Alpha"),
        ("b", "qa,smoke", "Bravo"),
        ("c", "other", "Charlie"),
    ]
    for node_id, tags, title in rows:
        conn.execute(
            "INSERT INTO nodes (id, path, title, body, node_type, tags, ttl_days, verified_on) "
            "VALUES (?, ?, ?, 'x', 'fact', ?, 14, '2026-05-01T00:00:00+00:00')",
            (node_id, f"{node_id}.md", title, tags),
        )
    conn.commit()
    edges_mod.recompute_derived(conn)
    metrics.recompute(conn)


@pytest.fixture()
def conn(tmp_path: Path) -> sqlite3.Connection:
    c = open_and_migrate(tmp_path / "engram.db")
    _seed(c)
    return c


def test_export_payload_shape(conn: sqlite3.Connection) -> None:
    payload = exporter.export(conn)
    assert set(payload) == {"nodes", "edges", "meta"}
    assert payload["meta"]["node_count"] == 3
    for node in payload["nodes"]:
        assert "id" in node
        assert "label" in node
        assert "color" in node
        assert "engram" in node


def test_export_excludes_quarantined_by_default(conn: sqlite3.Connection) -> None:
    conn.execute("UPDATE nodes SET quarantined = 1 WHERE id = 'a'")
    conn.commit()
    payload = exporter.export(conn)
    ids = {n["id"] for n in payload["nodes"]}
    assert "a" not in ids
    payload_with = exporter.export(conn, include_quarantined=True)
    assert "a" in {n["id"] for n in payload_with["nodes"]}


def test_theme_resolution() -> None:
    assert theme.resolve("dark").name == "dark"
    assert theme.resolve("light").name == "light"
    assert theme.resolve(None).name == "dark"
    with pytest.raises(ValueError):
        theme.resolve("rainbow")


def test_renderer_writes_self_contained_html(conn: sqlite3.Connection, tmp_path: Path) -> None:
    out = tmp_path / "viz.html"
    result = renderer.render(conn, out, theme_name="dark")
    assert out.is_file()
    text = out.read_text(encoding="utf-8")
    assert "<html" in text
    assert "vis.Network" in text
    # graph JSON is embedded inline
    assert "Alpha" in text
    assert result["meta"]["node_count"] == 3


def test_renderer_falls_back_to_cdn_when_no_vendored_asset(
    conn: sqlite3.Connection, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(renderer, "_load_vendored_asset", lambda name: None)
    out = tmp_path / "viz.html"
    result = renderer.render(conn, out)
    assert result["asset_mode"] == "cdn"
    assert "unpkg.com" in out.read_text(encoding="utf-8")


def test_export_node_includes_pagerank_and_cluster(conn: sqlite3.Connection) -> None:
    payload = exporter.export(conn)
    nodes_with_pr = [n for n in payload["nodes"] if n["engram"]["pagerank"] > 0]
    assert nodes_with_pr  # at least one connected node has pagerank > 0
    assert all(isinstance(n["engram"]["cluster"], int) for n in payload["nodes"])


def test_payload_is_json_serialisable(conn: sqlite3.Connection) -> None:
    payload = exporter.export(conn)
    json.dumps(payload)  # must not raise
