"""Smoke tests for repository scaffolding."""

from __future__ import annotations

import subprocess
import sys

from click.testing import CliRunner

from engram import __version__
from engram.cli import main


def test_version_constant_is_semver() -> None:
    # Accept "MAJOR.MINOR.PATCH" plus an optional PEP 440 dev/pre/post suffix
    # (e.g. "0.3.0.dev0", "1.0.0rc1", "0.2.0.post1").
    import re

    assert re.fullmatch(
        r"\d+\.\d+\.\d+(\.(dev|post)\d+|(a|b|rc)\d+)?",
        __version__,
    ), f"Unexpected version string: {__version__!r}"


def test_cli_version_flag_prints_version() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_cli_help_lists_all_commands() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    for name in ("store", "recall", "verify", "list-stale", "rebuild", "view", "audit", "doctor"):
        assert name in result.output


def test_module_invocation_runs() -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "engram", "--version"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert __version__ in proc.stdout
