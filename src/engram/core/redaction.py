"""Redaction of secrets, paths and identifiers before storage.

This module is *fail-closed*: if any built-in or configured pattern raises
during compilation or matching, :func:`redact` re-raises and the caller is
expected to abort the store. We never silently degrade redaction.

The default pattern set is intentionally narrow — broad regexes produce
more harm than good. Users add corpus-specific rules via
``[redaction] extra_patterns`` in ``engram.toml``.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Built-in patterns. Each is ``(name, regex, replacement)``. Order matters:
# more specific patterns first.
# ---------------------------------------------------------------------------

_BUILTIN_PATTERNS: tuple[tuple[str, str, str], ...] = (
    # JWT-shaped tokens (three dot-separated base64url segments, header is
    # almost always at least 16 chars). Match before generic base64 to win.
    (
        "jwt",
        r"\beyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\b",
        "[REDACTED:JWT]",
    ),
    # GitHub-style fine-grained PATs and classic tokens.
    (
        "github_token",
        r"\b(?:ghp|gho|ghu|ghs|ghr|github_pat)_[A-Za-z0-9_]{20,}\b",
        "[REDACTED:GH_TOKEN]",
    ),
    # AWS access key ID.
    (
        "aws_access_key",
        r"\bAKIA[0-9A-Z]{16}\b",
        "[REDACTED:AWS_KEY]",
    ),
    # Atlassian account IDs (24-char hex with optional ':' prefix segments).
    (
        "atlassian_account_id",
        r"\b[0-9a-f]{6}:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
        "[REDACTED:ATLASSIAN_ID]",
    ),
    # Windows user paths under \Users\<name>\ — strip the user segment but
    # keep the relative tail so the note remains intelligible.
    (
        "windows_user_path",
        r"([A-Za-z]:\\Users\\)[^\\\s\"']+",
        r"\1[USER]",
    ),
    # Unix home paths.
    (
        "unix_home_path",
        r"/home/[^/\s\"']+",
        "/home/[USER]",
    ),
    # Authorisation header values (``Bearer <token>``).
    (
        "bearer_token",
        r"(?i)\b(authorization|bearer)\s*[:=]?\s*\S+",
        r"\1: [REDACTED:BEARER]",
    ),
    # Generic high-entropy hex strings ≥ 32 chars (often API keys).
    (
        "long_hex",
        r"\b[A-Fa-f0-9]{32,}\b",
        "[REDACTED:HEX]",
    ),
)


@dataclass(frozen=True)
class RedactionRule:
    """A single compiled redaction rule."""

    name: str
    pattern: re.Pattern[str]
    replacement: str


@dataclass(frozen=True)
class RedactionReport:
    """What :func:`redact` did. Useful for audit logs and tests."""

    text: str
    hits: dict[str, int]  # rule name -> number of substitutions

    @property
    def total(self) -> int:
        """Total number of redactions across all rules."""
        return sum(self.hits.values())


def compile_rules(extra_patterns: Iterable[str] = ()) -> list[RedactionRule]:
    """Compile the built-in rules plus any user-supplied regexes.

    Parameters
    ----------
    extra_patterns
        Iterable of raw regex strings. Each is wrapped with a generic
        ``[REDACTED:USER-N]`` replacement and added after the built-ins.

    Returns
    -------
    list[RedactionRule]
        Ready-to-use compiled rules in evaluation order.

    Raises
    ------
    re.error
        If any pattern fails to compile. Callers must treat this as fatal.
    """
    rules: list[RedactionRule] = []
    for name, pattern, replacement in _BUILTIN_PATTERNS:
        rules.append(RedactionRule(name, re.compile(pattern), replacement))
    for idx, pattern in enumerate(extra_patterns, start=1):
        rules.append(
            RedactionRule(
                name=f"user-{idx}",
                pattern=re.compile(pattern),
                replacement=f"[REDACTED:USER-{idx}]",
            )
        )
    return rules


def redact(text: str, rules: Iterable[RedactionRule] | None = None) -> RedactionReport:
    """Apply ``rules`` to ``text`` and return the cleaned text plus a report.

    If ``rules`` is ``None``, the default built-in rules are used.

    Notes
    -----
    Each rule is applied to the whole text in sequence, with later rules
    seeing the output of earlier ones. The hit count uses :func:`re.subn`
    so it reflects the *number of substitutions actually made*.
    """
    active_rules = list(rules) if rules is not None else compile_rules()
    hits: dict[str, int] = {}
    current = text
    for rule in active_rules:
        current, n = rule.pattern.subn(rule.replacement, current)
        if n:
            hits[rule.name] = hits.get(rule.name, 0) + n
    return RedactionReport(text=current, hits=hits)
