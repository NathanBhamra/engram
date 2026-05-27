"""End-to-end: store some text, recall it back through the public API."""

from __future__ import annotations

from pathlib import Path

from engram.config import DEFAULTS, Config
from engram.core import storage
from engram.core.db import open_and_migrate
from engram.recall import fts, ranking


def test_store_then_recall_round_trip(tmp_path: Path) -> None:
    db_path = tmp_path / "engram.db"
    notes_dir = tmp_path / "notes"
    conn = open_and_migrate(db_path)
    config = Config(raw=DEFAULTS, source=None)

    body = (
        "# How to run the test suite\n\n"
        "Use `make test` from the project root to run the full regression suite.\n"
        "See ticket PROJ-1024 for the original requirement.\n"
        "Docs live at https://example.com/engram-docs.\n"
    )

    outcome = storage.run(
        text=body,
        node_type="reference",
        tags=("test", "regression"),
        config=config,
        conn=conn,
        notes_dir=notes_dir,
        session_id="test",
    )
    assert outcome.store_count >= 1

    hits = fts.search(conn, "test suite make", expand_aliases=False)
    assert hits, "expected at least one recall hit"

    ranked = ranking.rerank(hits)
    top = ranking.select(ranked, top_n=3, token_budget=1000)
    assert top[0].hit.title.startswith("How to run")

    note_files = list(notes_dir.glob("*.md"))
    assert note_files, "store should have written a markdown note to disk"
    conn.close()
