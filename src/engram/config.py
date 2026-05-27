"""Configuration loading for Engram.

Configuration is layered: built-in defaults are overridden by ``engram.toml``
discovered alongside the invocation, which is overridden by ``--config`` if
supplied. The resulting :class:`Config` is a frozen dataclass so command
implementations can rely on attribute access without runtime mutation.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DEFAULTS: dict[str, Any] = {
    "paths": {
        "db": "engram.db",
        "notes_dir": "notes",
        "viz_out": "viz.html",
    },
    "redaction": {
        "extra_patterns": [],
        "fail_closed": True,
    },
    "worthiness": {
        "min_signals": 1,
        "min_word_count": 8,
    },
    "stale": {
        "ttl_fact": 14,
        "ttl_pattern": 180,
        "ttl_decision": 365,
        "ttl_reference": 365,
        "past_ttl_rank_multiplier": 0.5,
        "auto_quarantine_after_days": 30,
    },
    "recall": {
        "top_n": 3,
        "token_budget": 1000,
        "expand_aliases": True,
    },
    "chunker": {
        "target_chunk_size": 1200,
        "chunk_overlap": 100,
    },
    "viz": {
        "theme": "dark",
        "alpha_decay": 0.05,
        "velocity_decay": 0.4,
        "many_body_strength": -300,
        "edge_colours": {
            "wiki-link": "#88c0d0",
            "co-recall": "#a3be8c",
            "shared-tag": "#ebcb8b",
            "manual": "#bf616a",
        },
    },
    "embeddings": {
        "enabled": False,
        "model": "BAAI/bge-small-en-v1.5",
        "rrf_k": 60,
    },
}


@dataclass(frozen=True)
class Config:
    """Resolved Engram configuration.

    Attributes are nested dictionaries with the same shape as ``engram.toml``.
    Use :meth:`get` for safe nested access with a default.
    """

    raw: dict[str, Any] = field(default_factory=dict)
    source: Path | None = None

    def get(self, *keys: str, default: Any = None) -> Any:
        """Return ``raw[k1][k2]...`` or ``default`` if any key is missing."""
        node: Any = self.raw
        for k in keys:
            if not isinstance(node, dict) or k not in node:
                return default
            node = node[k]
        return node


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge ``override`` into a copy of ``base``."""
    out = dict(base)
    for key, value in override.items():
        if key in out and isinstance(out[key], dict) and isinstance(value, dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def discover_config(explicit: str | None = None) -> Path | None:
    """Return the path Engram should load, or ``None`` if there is no file."""
    if explicit is not None:
        path = Path(explicit)
        if not path.is_file():
            raise FileNotFoundError(f"--config path not found: {path}")
        return path

    for candidate in (Path.cwd() / "engram.toml", Path.home() / ".engram.toml"):
        if candidate.is_file():
            return candidate
    return None


def load_config(explicit: str | None = None) -> Config:
    """Load configuration from disk, layered on top of :data:`DEFAULTS`."""
    source = discover_config(explicit)
    if source is None:
        return Config(raw=DEFAULTS, source=None)

    with source.open("rb") as fh:
        user_raw = tomllib.load(fh)

    merged = _deep_merge(DEFAULTS, user_raw)
    return Config(raw=merged, source=source)
