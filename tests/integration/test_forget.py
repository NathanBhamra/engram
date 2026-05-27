"""Tests for ``engram forget`` — the single-node curation primitive."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from click.testing import CliRunner

from engram.cli import main


def _runner(tmp_path: Path) -> tuple[CliRunner, Path]:
    cfg = tmp_path / "engram.toml"
    cfg.write_text(
        f'[paths]\ndb = "{(tmp_path / "engram.db").as_posix()}"\n'
        f'notes_dir = "{(tmp_path / "notes").as_posix()}"\n',
        encoding="utf-8",
    )
    return CliRunner(), cfg


def _seed_node(runner: CliRunner, cfg: Path, text: str, *extra: str) -> str:
    """Autostore a chunk and return the created node id."""
    in_file = cfg.parent / f"in-{abs(hash(text))}.txt"
    in_file.write_text(text, encoding="utf-8")
    r = runner.invoke(
        main,
        ["--config", str(cfg), "autostore", "--file", str(in_file), "--json", *extra],
        catch_exceptions=False,
    )
    assert r.exit_code == 0, r.output
    payload = json.loads(r.output)
    ids = payload["stored_ids"]
    assert ids, f"expected at least one stored id, got {payload}"
    return ids[0]


def _db(cfg: Path) -> sqlite3.Connection:
    db_path = cfg.parent / "engram.db"
    return sqlite3.connect(db_path)


def test_forget_deletes_node_and_audits(tmp_path: Path) -> None:
    runner, cfg = _runner(tmp_path)
    body = (
        "Decision: use Engram autostore in PROJ-9001. See "
        "https://example.com/spec and /tmp/spec.md for details."
    )
    nid = _seed_node(runner, cfg, body, "--tag", "engram", "--tag", "decision")

    r = runner.invoke(
        main,
        ["--config", str(cfg), "forget", nid, "--yes", "--reason", "test cleanup"],
        catch_exceptions=False,
    )
    assert r.exit_code == 0, r.output
    assert f"Forgot {nid}" in r.output

    conn = _db(cfg)
    try:
        gone = conn.execute("SELECT 1 FROM nodes WHERE id = ?", (nid,)).fetchone()
        assert gone is None, "node row should be deleted"

        audit = conn.execute(
            "SELECT payload FROM audit_log WHERE op = 'node_forget' ORDER BY id DESC LIMIT 1"
        ).fetchone()
        assert audit is not None
        payload = json.loads(audit[0])
        assert payload["id"] == nid
        assert payload["reason"] == "test cleanup"
    finally:
        conn.close()

    note = tmp_path / "notes" / f"{nid}.md"
    assert not note.exists(), "on-disk note should also be removed"


def test_forget_dry_run_changes_nothing(tmp_path: Path) -> None:
    runner, cfg = _runner(tmp_path)
    body = "Pattern: spinner wait helper. See /src/utils/spinner.ts in PROJ-12345."
    nid = _seed_node(runner, cfg, body, "--tag", "pattern")

    r = runner.invoke(
        main,
        ["--config", str(cfg), "forget", nid, "--dry-run"],
        catch_exceptions=False,
    )
    assert r.exit_code == 0
    assert "dry-run" in r.output

    conn = _db(cfg)
    try:
        still_there = conn.execute("SELECT 1 FROM nodes WHERE id = ?", (nid,)).fetchone()
        assert still_there is not None, "dry-run must not delete the row"
    finally:
        conn.close()

    note = tmp_path / "notes" / f"{nid}.md"
    assert note.exists(), "dry-run must not remove the note file"


def test_forget_unknown_id_errors_cleanly(tmp_path: Path) -> None:
    runner, cfg = _runner(tmp_path)
    r = runner.invoke(
        main,
        ["--config", str(cfg), "forget", "does-not-exist", "--yes"],
        catch_exceptions=False,
    )
    assert r.exit_code != 0
    assert "No node with id" in r.output


def test_forget_prompt_abort_keeps_node(tmp_path: Path) -> None:
    runner, cfg = _runner(tmp_path)
    body = (
        "Reference: the engram-memory SKILL.md lives at "
        "integrations/copilot-cli/skills/engram-memory/SKILL.md and is the "
        "canonical agent contract for recall and autostore behaviour."
    )
    nid = _seed_node(runner, cfg, body, "--tag", "reference")

    r = runner.invoke(
        main,
        ["--config", str(cfg), "forget", nid],
        input="n\n",
        catch_exceptions=False,
    )
    assert r.exit_code == 1
    assert "Aborted" in r.output

    conn = _db(cfg)
    try:
        still_there = conn.execute("SELECT 1 FROM nodes WHERE id = ?", (nid,)).fetchone()
        assert still_there is not None
    finally:
        conn.close()
