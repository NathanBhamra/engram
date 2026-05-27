"""Tests for :mod:`engram.core.worthiness`."""

from __future__ import annotations

from engram.core.worthiness import Verdict, check


def test_too_short_rejected() -> None:
    report = check("ok")
    assert report.verdict is Verdict.REJECT
    assert "too short" in report.reason


def test_url_signal_accepted() -> None:
    report = check("See the docs at https://example.com/engram for setup details.")
    assert report.verdict is Verdict.STORE
    assert report.signals["url"] >= 1


def test_ticket_signal_accepted() -> None:
    report = check("Bug MIL-12345 reproduces only on Friday afternoons sometimes.")
    assert report.verdict is Verdict.STORE
    assert report.signals["ticket"] >= 1


def test_file_path_signal_accepted() -> None:
    report = check(r"Config lives at C:\Users\foo\engram.toml under the project root.")
    assert report.verdict is Verdict.STORE


def test_force_directive_bypasses_filters() -> None:
    report = check("!store nothing here")
    assert report.verdict is Verdict.FORCE


def test_structured_list_signal() -> None:
    report = check("Steps:\n- one alpha\n- two bravo\n- three charlie")
    assert report.signals["structured_list"] >= 1
    assert report.verdict is Verdict.STORE


def test_no_signals_rejected() -> None:
    text = "this is just some conversational chatter with no actionable content here ok"
    report = check(text)
    assert report.verdict is Verdict.REJECT
    assert "insufficient signals" in report.reason
