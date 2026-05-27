"""Tests for the ``engram autostore`` command and the audit-log invariants."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from engram.cli import main


def _runner(tmp_path: Path) -> tuple[CliRunner, Path]:
    """Build a Click runner with an isolated config + db under tmp_path."""
    cfg = tmp_path / "engram.toml"
    cfg.write_text(
        f'[paths]\ndb = "{(tmp_path / "engram.db").as_posix()}"\n'
        f'notes_dir = "{(tmp_path / "notes").as_posix()}"\n',
        encoding="utf-8",
    )
    return CliRunner(), cfg


def _autostore(runner: CliRunner, cfg: Path, text: str, *extra: str) -> tuple[int, str]:
    """Run autostore with text via --file (avoids stdin pipe flakiness on Windows)."""
    in_file = cfg.parent / "in.txt"
    in_file.write_text(text, encoding="utf-8")
    result = runner.invoke(
        main,
        ["--config", str(cfg), "autostore", "--file", str(in_file), *extra],
        catch_exceptions=False,
    )
    return result.exit_code, result.output


def test_autostore_rejects_junk_but_exits_zero(tmp_path: Path) -> None:
    runner, cfg = _runner(tmp_path)
    code, out = _autostore(runner, cfg, "ok", "--verbose")
    assert code == 0, "autostore must never fail the caller, even on rejection"
    assert "0 stored" in out and "1 rejected" in out


def test_autostore_stores_signal_rich_content(tmp_path: Path) -> None:
    runner, cfg = _runner(tmp_path)
    body = (
        "Engram v0.5.0 ships autostore. Source at /home/test/engram/cli.py. "
        "See https://example.com/engram for docs. Tracking ticket PROJ-12345."
    )
    code, out = _autostore(runner, cfg, body, "--tag", "engram", "--verbose")
    assert code == 0
    assert "1 stored" in out


def test_autostore_empty_input_is_a_noop(tmp_path: Path) -> None:
    runner, cfg = _runner(tmp_path)
    code, out = _autostore(runner, cfg, "", "--verbose")
    assert code == 0
    assert "empty input" in out


def test_autostore_json_output_is_parseable(tmp_path: Path) -> None:
    runner, cfg = _runner(tmp_path)
    code, out = _autostore(runner, cfg, "too short", "--json")
    assert code == 0
    payload = json.loads(out.strip().splitlines()[-1])
    assert payload["stored"] == 0
    assert payload["rejected"] == 1
    assert payload["rejected_reasons"][0]["title"]


def test_autostore_writes_reject_to_audit_log(tmp_path: Path) -> None:
    runner, cfg = _runner(tmp_path)
    _autostore(runner, cfg, "ok", "--tag", "smoke")
    result = runner.invoke(
        main, ["--config", str(cfg), "audit", "--op", "store_reject", "--json"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    last = json.loads(result.output.strip().splitlines()[-1])
    assert last["op"] == "store_reject"
    assert last["verdict"] == "reject"
    assert "signals" in last and "word_count" in last
    assert last["tags"] == ["smoke"]


def test_autostore_force_flag_bypasses_filter(tmp_path: Path) -> None:
    runner, cfg = _runner(tmp_path)
    code, out = _autostore(runner, cfg, "ok ok ok", "--force", "--verbose")
    assert code == 0
    assert "1 stored" in out


def test_audit_pretty_renders_kinds_and_reason(tmp_path: Path) -> None:
    runner, cfg = _runner(tmp_path)
    _autostore(runner, cfg, "ok", "--tag", "review-me")
    result = runner.invoke(
        main, ["--config", str(cfg), "audit", "--tail", "5", "--pretty"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert "reject" in result.output
    assert "review-me" in result.output
    assert "reason:" in result.output
