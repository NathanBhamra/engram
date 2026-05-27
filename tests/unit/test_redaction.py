"""Tests for :mod:`engram.core.redaction`."""

from __future__ import annotations

import re

import pytest

from engram.core import redaction


def test_jwt_redacted() -> None:
    text = "token: eyJabcdefghij.eyJabcdefghij.signaturepartlongenough"
    out = redaction.redact(text)
    assert "eyJ" not in out.text
    assert out.hits.get("jwt") == 1


def test_github_token_redacted() -> None:
    text = "key=ghp_" + "A" * 30
    out = redaction.redact(text)
    assert "[REDACTED:GH_TOKEN]" in out.text
    assert out.hits.get("github_token") == 1


def test_aws_access_key_redacted() -> None:
    text = "id=AKIAIOSFODNN7EXAMPLE here"
    out = redaction.redact(text)
    assert "[REDACTED:AWS_KEY]" in out.text


def test_atlassian_id_redacted() -> None:
    text = "owner 712020:be6e34cc-57b6-4a0d-bd06-a0b7b2ab6c11 is the user"
    out = redaction.redact(text)
    assert "[REDACTED:ATLASSIAN_ID]" in out.text


def test_windows_user_path_keeps_tail() -> None:
    text = r"see C:\Users\bhamran0\engram\notes for files"
    out = redaction.redact(text)
    assert r"C:\Users\[USER]" in out.text
    assert "bhamran0" not in out.text


def test_unix_home_path_redacted() -> None:
    text = "see /home/alice/code for files"
    out = redaction.redact(text)
    assert "/home/[USER]" in out.text
    assert "alice" not in out.text


def test_long_hex_redacted() -> None:
    text = "checksum " + "a" * 40
    out = redaction.redact(text)
    assert "[REDACTED:HEX]" in out.text


def test_clean_text_unchanged() -> None:
    text = "Engram stores notes as markdown."
    out = redaction.redact(text)
    assert out.text == text
    assert out.hits == {}


def test_user_extra_patterns_compile_and_apply() -> None:
    rules = redaction.compile_rules(extra_patterns=[r"\bsecret-\w+\b"])
    out = redaction.redact("the secret-foo is hidden", rules)
    assert "[REDACTED:USER-1]" in out.text


def test_fail_closed_on_bad_user_pattern() -> None:
    with pytest.raises(re.error):
        redaction.compile_rules(extra_patterns=[r"("])  # unbalanced paren
