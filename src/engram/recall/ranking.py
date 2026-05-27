"""Staleness-aware re-ranking and result selection."""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass

from engram.recall.fts import Hit


@dataclass(frozen=True)
class RankedHit:
    """A :class:`Hit` plus the post-staleness adjusted score and age."""

    hit: Hit
    score: float  # lower is better, like BM25
    age_days: int | None
    past_ttl: bool


def _parse_dt(value: str | None) -> _dt.datetime | None:
    if not value:
        return None
    try:
        return _dt.datetime.fromisoformat(value)
    except ValueError:
        return None


def rerank(
    hits: list[Hit],
    *,
    now: _dt.datetime | None = None,
    past_ttl_multiplier: float = 0.5,
) -> list[RankedHit]:
    """Adjust BM25 scores by staleness and re-sort.

    Past-TTL nodes have their *effective rank-quality* multiplied by
    ``past_ttl_multiplier``. Because BM25 here is "smaller is better", we
    achieve that by dividing the score (a 0.5 multiplier on quality = a 2×
    multiplier on the BM25 magnitude).
    """
    now = now or _dt.datetime.now(_dt.UTC)
    if now.tzinfo is None:
        now = now.replace(tzinfo=_dt.UTC)
    ranked: list[RankedHit] = []
    for hit in hits:
        verified = _parse_dt(hit.verified_on)
        if verified is not None and verified.tzinfo is None:
            verified = verified.replace(tzinfo=_dt.UTC)
        age_days = (now - verified).days if verified is not None else None
        past_ttl = age_days is not None and age_days > hit.ttl_days
        score = hit.bm25
        if past_ttl:
            # bm25 returns negative numbers in SQLite; "worse" means closer to 0
            # or positive. Dividing by a fraction < 1 increases magnitude (more
            # negative) for already-good matches — which actually *boosts* them.
            # We want to *demote* stale hits, so we instead scale toward 0 by
            # multiplying by the multiplier.
            score = score * past_ttl_multiplier
        ranked.append(RankedHit(hit=hit, score=score, age_days=age_days, past_ttl=past_ttl))
    # BM25 in SQLite is negative; smaller (more negative) is a better match.
    ranked.sort(key=lambda r: r.score)
    return ranked


def select(
    ranked: list[RankedHit],
    *,
    top_n: int,
    token_budget: int,
    chars_per_token: int = 4,
) -> list[RankedHit]:
    """Pick the top ``top_n`` ranked hits that fit within ``token_budget``.

    Token estimation uses a simple ``len(text) / chars_per_token`` heuristic.
    """
    budget_chars = token_budget * chars_per_token
    spent = 0
    out: list[RankedHit] = []
    for entry in ranked:
        if len(out) >= top_n:
            break
        chunk_chars = len(entry.hit.body)
        if spent + chunk_chars > budget_chars and out:
            break
        out.append(entry)
        spent += chunk_chars
    return out


def stale_banner(age_days: int | None, ttl_days: int) -> str:
    """Render the user-visible staleness banner for a recalled hit."""
    if age_days is None:
        return "[unverified — no recorded verification]"
    if age_days > ttl_days:
        return f"[STALE — verified {age_days}d ago; TTL was {ttl_days}d]"
    return f"[verified {age_days}d ago, ttl {ttl_days}d]"
