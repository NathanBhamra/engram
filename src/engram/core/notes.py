"""Markdown-on-disk I/O. Notes are the canonical store; SQLite is an index."""

from __future__ import annotations

import datetime as _dt
import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import frontmatter

# Allowed node types. Mirrors the CHECK constraint in 001_initial.sql.
NODE_TYPES = ("fact", "pattern", "decision", "reference")

_SLUG_RE = re.compile(r"[^a-z0-9]+")


@dataclass(frozen=True)
class Note:
    """A persisted note. The canonical form is a markdown file on disk."""

    id: str
    title: str
    body: str
    node_type: str
    tags: tuple[str, ...]
    ttl_days: int
    verified_on: _dt.datetime | None = None
    superseded_by: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def path_within(self, notes_dir: Path) -> Path:
        """Resolve the on-disk path for this note inside ``notes_dir``."""
        return notes_dir / f"{self.id}.md"


def slug(title: str, *, max_len: int = 40) -> str:
    """Produce a filesystem-safe slug from a title."""
    base = _SLUG_RE.sub("-", title.lower()).strip("-")
    return base[:max_len] or "untitled"


def make_id(title: str, body: str) -> str:
    """Stable per-content node ID — slug + short body hash.

    The hash makes the id deterministic for a given (title, body) pair, so
    re-storing the same content does not produce a duplicate file.
    """
    digest = hashlib.sha1(body.encode("utf-8"), usedforsecurity=False).hexdigest()[:8]
    return f"{slug(title)}-{digest}"


def write(note: Note, notes_dir: Path) -> Path:
    """Write ``note`` to ``notes_dir/<id>.md`` and return the path."""
    notes_dir.mkdir(parents=True, exist_ok=True)
    metadata: dict[str, Any] = {
        "id": note.id,
        "title": note.title,
        "type": note.node_type,
        "tags": list(note.tags),
        "ttl_days": note.ttl_days,
    }
    if note.verified_on is not None:
        metadata["verified_on"] = note.verified_on.isoformat()
    if note.superseded_by is not None:
        metadata["superseded_by"] = note.superseded_by
    metadata.update(note.extra)

    post = frontmatter.Post(content=note.body, **metadata)
    path = note.path_within(notes_dir)
    path.write_text(frontmatter.dumps(post), encoding="utf-8")
    return path


def read(path: Path) -> Note:
    """Read a note back from a markdown file.

    Raises
    ------
    ValueError
        If required frontmatter keys are missing or the node type is invalid.
    """
    post = frontmatter.load(path)
    meta = post.metadata
    missing = [key for key in ("id", "title", "type", "ttl_days") if key not in meta]
    if missing:
        raise ValueError(f"{path}: missing frontmatter keys: {missing}")
    if meta["type"] not in NODE_TYPES:
        raise ValueError(f"{path}: invalid node type {meta['type']!r}")
    verified_on = meta.get("verified_on")
    if isinstance(verified_on, str):
        verified_on = _dt.datetime.fromisoformat(verified_on)
    elif isinstance(verified_on, _dt.date) and not isinstance(verified_on, _dt.datetime):
        verified_on = _dt.datetime.combine(verified_on, _dt.time.min)

    raw_tags = meta.get("tags") or ()
    if not isinstance(raw_tags, list | tuple):
        raise ValueError(f"{path}: 'tags' must be a list, got {type(raw_tags).__name__}")
    return Note(
        id=str(meta["id"]),
        title=str(meta["title"]),
        body=post.content,
        node_type=str(meta["type"]),
        tags=tuple(str(t) for t in raw_tags),
        ttl_days=int(str(meta["ttl_days"])),
        verified_on=verified_on if isinstance(verified_on, _dt.datetime) else None,
        superseded_by=(
            str(meta["superseded_by"]) if meta.get("superseded_by") is not None else None
        ),
        extra={
            k: v
            for k, v in meta.items()
            if k not in {"id", "title", "type", "tags", "ttl_days", "verified_on", "superseded_by"}
        },
    )


def iter_notes(notes_dir: Path) -> list[Note]:
    """Read every ``.md`` file under ``notes_dir``."""
    if not notes_dir.is_dir():
        return []
    return [read(p) for p in sorted(notes_dir.glob("*.md"))]
