"""Storage pipeline: redaction → chunking → worthiness → notes + index."""

from __future__ import annotations

import datetime as _dt
import json
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from engram.config import Config
from engram.core import chunker, notes, redaction, worthiness


@dataclass
class StoreOutcome:
    """What :func:`run` did. One entry per chunk evaluated."""

    stored: list[notes.Note] = field(default_factory=list)
    rejected: list[tuple[str, str]] = field(default_factory=list)  # (chunk_title, reason)
    redactions: dict[str, int] = field(default_factory=dict)

    @property
    def store_count(self) -> int:
        return len(self.stored)

    @property
    def reject_count(self) -> int:
        return len(self.rejected)


_TTL_BY_TYPE_KEY = {
    "fact": "ttl_fact",
    "pattern": "ttl_pattern",
    "decision": "ttl_decision",
    "reference": "ttl_reference",
}


def run(
    *,
    text: str,
    node_type: str,
    tags: tuple[str, ...],
    config: Config,
    conn: sqlite3.Connection,
    notes_dir: Path,
    session_id: str | None = None,
    force: bool = False,
) -> StoreOutcome:
    """Run the full store pipeline. Returns a structured outcome."""
    outcome = StoreOutcome()

    # 1. Redact (fail-closed).
    rules = redaction.compile_rules(config.get("redaction", "extra_patterns", default=[]))
    report = redaction.redact(text, rules)
    outcome.redactions = report.hits
    clean_text = report.text

    # 2. Chunk.
    chunks = chunker.chunk(
        clean_text,
        target_chunk_size=config.get("chunker", "target_chunk_size", default=1200),
        chunk_overlap=config.get("chunker", "chunk_overlap", default=100),
    )

    # 3. Worthiness, then write each accepted chunk.
    min_signals = config.get("worthiness", "min_signals", default=1)
    min_words = config.get("worthiness", "min_word_count", default=8)
    ttl_days = config.get("stale", _TTL_BY_TYPE_KEY[node_type], default=14)

    for piece in chunks:
        verdict = worthiness.check(piece.text, min_signals=min_signals, min_word_count=min_words)
        if not force and verdict.verdict.name == "REJECT":
            outcome.rejected.append((piece.title, verdict.reason))
            continue
        note = notes.Note(
            id=notes.make_id(piece.title, piece.text),
            title=piece.title,
            body=piece.text,
            node_type=node_type,
            tags=tags,
            ttl_days=ttl_days,
            verified_on=_dt.datetime.now(_dt.UTC),
        )
        notes.write(note, notes_dir)
        _upsert(conn, note)
        _audit(
            conn,
            "store",
            {
                "id": note.id,
                "session": session_id,
                "verdict": verdict.verdict.value,
                "signals": verdict.signals,
                "redactions": report.hits,
            },
        )
        outcome.stored.append(note)

    return outcome


def _upsert(conn: sqlite3.Connection, note: notes.Note) -> None:
    """Insert or update a node row. Idempotent on ``id``."""
    rel_path = f"{note.id}.md"
    tag_csv = ",".join(note.tags)
    verified_on = note.verified_on.isoformat() if note.verified_on else None
    with conn:
        conn.execute(
            """
            INSERT INTO nodes (id, path, title, body, node_type, tags, ttl_days, verified_on)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                title        = excluded.title,
                body         = excluded.body,
                node_type    = excluded.node_type,
                tags         = excluded.tags,
                ttl_days     = excluded.ttl_days,
                verified_on  = excluded.verified_on,
                updated_at   = CURRENT_TIMESTAMP
            """,
            (
                note.id,
                rel_path,
                note.title,
                note.body,
                note.node_type,
                tag_csv,
                note.ttl_days,
                verified_on,
            ),
        )


def _audit(conn: sqlite3.Connection, op: str, payload: dict[str, object]) -> None:
    """Append an entry to the audit log."""
    with conn:
        conn.execute(
            "INSERT INTO audit_log (op, payload) VALUES (?, ?)",
            (op, json.dumps(payload, default=str)),
        )
