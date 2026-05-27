"""Tests for :mod:`engram.recall.ranking`."""

from __future__ import annotations

import datetime as _dt

from engram.recall.fts import Hit
from engram.recall.ranking import rerank, select, stale_banner


def _hit(
    *,
    node_id: str = "n",
    bm25: float = -5.0,
    verified_on: str | None = None,
    ttl_days: int = 14,
    body: str = "x" * 400,
) -> Hit:
    return Hit(
        node_id=node_id,
        title="t",
        body=body,
        node_type="fact",
        tags=(),
        bm25=bm25,
        verified_on=verified_on,
        ttl_days=ttl_days,
        quarantined=False,
    )


def test_past_ttl_demotes_score() -> None:
    now = _dt.datetime(2026, 1, 1, tzinfo=_dt.UTC)
    old = (now - _dt.timedelta(days=100)).isoformat()
    fresh = (now - _dt.timedelta(days=1)).isoformat()
    ranked = rerank(
        [
            _hit(node_id="old", bm25=-10.0, verified_on=old, ttl_days=14),
            _hit(node_id="new", bm25=-9.0, verified_on=fresh, ttl_days=14),
        ],
        now=now,
    )
    assert ranked[0].hit.node_id == "new"
    stale = next(r for r in ranked if r.hit.node_id == "old")
    assert stale.past_ttl is True


def test_select_respects_top_n() -> None:
    hits = [_hit(node_id=f"n{i}") for i in range(5)]
    ranked = rerank(hits)
    out = select(ranked, top_n=2, token_budget=10_000)
    assert len(out) == 2


def test_select_respects_token_budget() -> None:
    big = _hit(node_id="big", body="x" * 5000)
    small = _hit(node_id="small", body="x" * 100, bm25=-4.0)
    ranked = rerank([big, small])
    out = select(ranked, top_n=10, token_budget=200)
    assert len(out) == 1


def test_stale_banner_phrases() -> None:
    assert "STALE" in stale_banner(100, 14)
    assert "verified" in stale_banner(5, 14)
    assert "unverified" in stale_banner(None, 14)
