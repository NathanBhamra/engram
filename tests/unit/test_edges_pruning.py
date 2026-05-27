"""Tests for v0.5.2 blanket-tag pruning + IDF weighting in edge derivation.

These cover the behaviour change that took the live corpus from 6993 edges
to 674: blanket tags (those present on more than ``blanket_tag_threshold``
of the corpus) are projected out before pairing, and remaining shared tags
contribute IDF-weighted Jaccard rather than raw Jaccard.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from engram.config import load_config
from engram.core.db import open_and_migrate
from engram.viz import edges as edges_mod


def _add(
    conn: sqlite3.Connection, node_id: str, *, tags: str = "", body: str = "x"
) -> None:
    conn.execute(
        "INSERT INTO nodes (id, path, title, body, node_type, tags, ttl_days) "
        "VALUES (?, ?, ?, ?, 'fact', ?, 14)",
        (node_id, f"{node_id}.md", node_id, body, tags),
    )
    conn.commit()


def _seed_corpus_with_blanket(conn: sqlite3.Connection, *, n: int = 30) -> None:
    """Seed `n` nodes all carrying the blanket tag ``meta``, plus a few
    semantic tags so we have something to compare against."""
    for i in range(n):
        # half the corpus carries "alpha", a few carry "rare"
        tags = ["meta"]
        if i % 2 == 0:
            tags.append("alpha")
        if i < 3:
            tags.append("rare")
        _add(conn, f"n{i:03d}", tags=",".join(tags))


@pytest.fixture()
def conn(tmp_path: Path) -> sqlite3.Connection:
    return open_and_migrate(tmp_path / "engram.db")


# --- blanket-tag detection ---------------------------------------------------


def test_blanket_tag_detected_above_threshold(conn: sqlite3.Connection) -> None:
    """A tag on >30% of the corpus (default threshold) is flagged blanket."""
    _seed_corpus_with_blanket(conn, n=30)  # "meta" on 100% > 30%
    blanket = edges_mod.compute_blanket_tags(conn)
    assert "meta" in blanket
    assert "alpha" in blanket  # 15/30 = 50%, above 30% default
    assert "rare" not in blanket  # 3/30 = 10% — semantic


def test_blanket_heuristic_disabled_on_small_corpus(
    conn: sqlite3.Connection,
) -> None:
    """Below _BLANKET_TAG_MIN_CORPUS nodes, no auto-blanketing fires."""
    # 10 nodes all sharing "meta" — would be 100% but corpus is too small
    for i in range(10):
        _add(conn, f"s{i}", tags="meta,alpha")
    blanket = edges_mod.compute_blanket_tags(conn)
    assert "meta" not in blanket
    assert "alpha" not in blanket


def test_explicit_excludes_apply_regardless_of_corpus_size(
    tmp_path: Path,
) -> None:
    """``[edges].exclude_tags`` from config always blacklists a tag, even on
    a tiny corpus where auto-blanketing wouldn't fire."""
    conn = open_and_migrate(tmp_path / "engram.db")
    for i in range(5):
        _add(conn, f"x{i}", tags="meta,real")

    cfg_path = tmp_path / "engram.toml"
    cfg_path.write_text(
        '[edges]\nexclude_tags = ["meta"]\n', encoding="utf-8"
    )
    config = load_config(str(cfg_path))

    blanket = edges_mod.compute_blanket_tags(conn, config=config)
    assert "meta" in blanket
    assert "real" not in blanket


# --- edge derivation with pruning -------------------------------------------


def test_blanket_tag_does_not_create_edges(conn: sqlite3.Connection) -> None:
    """Two nodes sharing ONLY a blanket tag get no edge."""
    _seed_corpus_with_blanket(conn, n=30)
    # n001 (tags: meta) and n003 (tags: meta) share only "meta"
    # After blanket pruning their tag sets are empty → no pairing
    edges = edges_mod.derive_shared_tag_edges(conn)
    pairs = {(s, t) for s, t, _, _ in edges}
    assert ("n001", "n003") not in pairs


def test_semantic_tag_survives_blanket_pruning(conn: sqlite3.Connection) -> None:
    """Two nodes sharing a semantic ``rare`` tag (3/30 = 10%) DO get an edge,
    even though they also share the ``meta`` blanket tag."""
    _seed_corpus_with_blanket(conn, n=30)
    # n000 has [meta, alpha, rare], n002 has [meta, alpha, rare]
    edges = edges_mod.derive_shared_tag_edges(conn)
    pairs = {(s, t) for s, t, _, _ in edges}
    assert ("n000", "n002") in pairs


def test_idf_weighting_ranks_rare_tags_higher(conn: sqlite3.Connection) -> None:
    """A pair linked by a rare tag should have higher weight than a pair
    linked by a common (but not blanket) tag, with all else equal.

    Each test node also carries a unique tag so the IDF-weighted Jaccard
    denominator isn't degenerate (single-tag pairs always score 1.0
    regardless of IDF — the differentiation appears once unions differ).
    """
    # 6/24 = 25% — below 30% blanket cutoff, so "common" survives
    for i in range(6):
        _add(conn, f"c{i}", tags=f"common,uniq_c{i}")
    # filler to grow corpus so percentages stay sensible
    for i in range(16):
        _add(conn, f"f{i}", tags=f"filler,uniq_f{i}")
    # 2/24 = 8% — clearly rare, with own unique tags
    _add(conn, "r1", tags="rare2,uniq_r1")
    _add(conn, "r2", tags="rare2,uniq_r2")

    edges = edges_mod.derive_shared_tag_edges(conn)
    by_pair = {(s, t): w for s, t, _, w in edges}

    w_common = by_pair.get(("c0", "c1"))
    w_rare = by_pair.get(("r1", "r2"))
    assert w_common is not None, "common-tag pair should produce an edge"
    assert w_rare is not None, "rare-tag pair should produce an edge"
    assert w_rare > w_common, (
        f"IDF should weight rarer tags higher: "
        f"rare={w_rare:.3f} common={w_common:.3f}"
    )


def test_config_threshold_can_be_raised_to_keep_more_tags(
    tmp_path: Path,
) -> None:
    """Raising ``blanket_tag_threshold`` to 0.6 lets 50%-frequency tags survive."""
    conn = open_and_migrate(tmp_path / "engram.db")
    for i in range(30):
        tags = ["meta"]  # 100% — always blanket regardless
        if i % 2 == 0:
            tags.append("alpha")  # 50% — would be blanket at 0.30
        _add(conn, f"t{i:03d}", tags=",".join(tags))

    # Default 0.30 — alpha is blanketed
    blanket_default = edges_mod.compute_blanket_tags(conn)
    assert "alpha" in blanket_default

    cfg_path = tmp_path / "engram.toml"
    cfg_path.write_text(
        "[edges]\nblanket_tag_threshold = 0.60\n", encoding="utf-8"
    )
    config = load_config(str(cfg_path))
    blanket_raised = edges_mod.compute_blanket_tags(conn, config=config)
    assert "meta" in blanket_raised  # still blanket at 100%
    assert "alpha" not in blanket_raised  # 50% survives at 0.60 threshold
