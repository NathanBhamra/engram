"""FTS5-backed keyword retrieval with alias expansion."""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass

from engram.core import aliases as alias_table

# Tokens that contribute nothing to ranking.
_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "and",
        "or",
        "but",
        "if",
        "of",
        "to",
        "in",
        "on",
        "at",
        "for",
        "by",
        "with",
        "as",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "this",
        "that",
        "those",
        "these",
        "it",
        "its",
        "i",
        "you",
        "we",
        "they",
        "he",
        "she",
    }
)

# Word-ish tokens, including hyphens and underscores common in identifiers.
_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_\-]{1,}")

# Characters FTS5 treats specially within a MATCH query.
_FTS_SPECIAL = re.compile(r'["()*+\-:^]')


@dataclass(frozen=True)
class Hit:
    """A single recall result."""

    node_id: str
    title: str
    body: str
    node_type: str
    tags: tuple[str, ...]
    bm25: float
    verified_on: str | None
    ttl_days: int
    quarantined: bool


def tokenise(query: str) -> list[str]:
    """Split a free-text query into FTS-friendly content tokens."""
    return [
        match.group(0).lower()
        for match in _TOKEN_RE.finditer(query)
        if match.group(0).lower() not in _STOPWORDS
    ]


def build_match_expression(
    query: str,
    *,
    conn: sqlite3.Connection | None = None,
    expand_aliases: bool = True,
) -> str:
    """Turn a free-text query into an FTS5 ``MATCH`` expression.

    The result is a parenthesised OR-of-ORs: each input token contributes a
    group of ``token OR alias OR ...`` joined by ``AND`` across groups, so
    *every* user token must be represented somehow in the matched row.

    Parameters
    ----------
    query
        The free-text query string.
    conn
        Optional DB connection. Required if ``expand_aliases`` is true.
    expand_aliases
        When true, each token is expanded via the aliases table.
    """
    tokens = tokenise(query)
    if not tokens:
        return ""

    if expand_aliases and conn is not None:
        expansion_map = alias_table.expand(conn, tokens)
    else:
        expansion_map = {t: {t} for t in tokens}

    groups: list[str] = []
    for token in tokens:
        synonyms = sorted(expansion_map.get(token, {token}))
        escaped = [_quote_for_fts(s) for s in synonyms]
        groups.append("(" + " OR ".join(escaped) + ")")
    return " AND ".join(groups)


def _quote_for_fts(token: str) -> str:
    """Wrap a token in double quotes if it contains FTS special characters."""
    if _FTS_SPECIAL.search(token):
        # FTS5 supports phrase queries with double quotes; embedded quotes are
        # doubled per SQLite quoting rules.
        return '"' + token.replace('"', '""') + '"'
    return token


def search(
    conn: sqlite3.Connection,
    query: str,
    *,
    limit: int = 25,
    include_stale: bool = False,
    expand_aliases: bool = True,
) -> list[Hit]:
    """Run an FTS5 search and return raw hits ordered by BM25 (best first).

    Stale ranking and TTL filtering are *not* applied here; that lives in
    :mod:`engram.recall.ranking` so callers can compose differently.
    """
    expression = build_match_expression(query, conn=conn, expand_aliases=expand_aliases)
    if not expression:
        return []

    sql = """
        SELECT n.id, n.title, n.body, n.node_type, n.tags,
               bm25(nodes_fts) AS bm25, n.verified_on, n.ttl_days, n.quarantined
          FROM nodes_fts
          JOIN nodes n ON n.rowid = nodes_fts.rowid
         WHERE nodes_fts MATCH ?
    """
    if not include_stale:
        sql += " AND n.quarantined = 0"
    sql += " ORDER BY bm25 ASC LIMIT ?"

    rows = conn.execute(sql, (expression, limit)).fetchall()
    return [
        Hit(
            node_id=row["id"],
            title=row["title"],
            body=row["body"],
            node_type=row["node_type"],
            tags=tuple((row["tags"] or "").split(",")) if row["tags"] else (),
            bm25=float(row["bm25"]),
            verified_on=row["verified_on"],
            ttl_days=int(row["ttl_days"]),
            quarantined=bool(row["quarantined"]),
        )
        for row in rows
    ]
