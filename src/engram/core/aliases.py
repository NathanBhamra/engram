"""Alias expansion. A learned vocabulary that bridges keyword gaps.

The alias table maps a *canonical* token to one or more equivalent tokens.
At recall time, each query token is expanded with its known aliases (and
reverse aliases) and the expanded set is ORed into the FTS query. This is
the deterministic substitute for semantic similarity.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable

# Tokens of length <2 are not useful as alias keys (false positives explode).
_MIN_TOKEN_LEN = 2


def add(conn: sqlite3.Connection, canonical: str, *alias_values: str) -> int:
    """Add aliases for a canonical token. Returns the number of rows inserted."""
    canonical_norm = canonical.lower().strip()
    if len(canonical_norm) < _MIN_TOKEN_LEN:
        raise ValueError(f"canonical token too short: {canonical!r}")
    inserted = 0
    with conn:
        for alias in alias_values:
            alias_norm = alias.lower().strip()
            if len(alias_norm) < _MIN_TOKEN_LEN or alias_norm == canonical_norm:
                continue
            cur = conn.execute(
                "INSERT OR IGNORE INTO aliases (canonical, alias) VALUES (?, ?)",
                (canonical_norm, alias_norm),
            )
            inserted += cur.rowcount or 0
    return inserted


def remove(conn: sqlite3.Connection, canonical: str, alias: str) -> int:
    """Remove a single alias pair. Returns the number of rows deleted."""
    with conn:
        cur = conn.execute(
            "DELETE FROM aliases WHERE canonical = ? AND alias = ?",
            (canonical.lower().strip(), alias.lower().strip()),
        )
    return cur.rowcount or 0


def expand(conn: sqlite3.Connection, tokens: Iterable[str]) -> dict[str, set[str]]:
    """Return ``{token: {synonyms}}`` for each token (synonyms include itself).

    Both directions are followed: if ``aristotle ↔ philosopher`` is registered,
    expanding either token yields both.
    """
    out: dict[str, set[str]] = {}
    for raw in tokens:
        token = raw.lower().strip()
        if len(token) < _MIN_TOKEN_LEN:
            continue
        synonyms = {token}
        rows = conn.execute(
            "SELECT alias FROM aliases WHERE canonical = ? "
            "UNION SELECT canonical FROM aliases WHERE alias = ?",
            (token, token),
        ).fetchall()
        for row in rows:
            synonyms.add(row[0])
        out[token] = synonyms
    return out


def list_all(conn: sqlite3.Connection) -> list[tuple[str, str]]:
    """Return every ``(canonical, alias)`` pair, sorted."""
    return [
        (row[0], row[1])
        for row in conn.execute(
            "SELECT canonical, alias FROM aliases ORDER BY canonical, alias"
        ).fetchall()
    ]
