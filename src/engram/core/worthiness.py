"""Decide whether a candidate chunk earns a place in the index.

The worthiness filter is the second of Engram's three guardrails. It rejects
conversational noise so the corpus stays high-signal. The rule is simple:
a chunk earns storage if it carries enough *signals* — concrete artefacts
like URLs, file paths, identifiers, or structured lists — or if the user
explicitly forces storage with a ``!store`` directive.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum


class Verdict(StrEnum):
    """Outcome of a worthiness check."""

    STORE = "store"
    REJECT = "reject"
    FORCE = "force"  # explicit !store override; stored regardless of signals


@dataclass(frozen=True)
class WorthinessReport:
    """Detailed breakdown of why a chunk was accepted or rejected."""

    verdict: Verdict
    signals: dict[str, int]
    word_count: int
    reason: str

    @property
    def total_signals(self) -> int:
        """Number of distinct signal kinds detected (not raw match count)."""
        return sum(1 for v in self.signals.values() if v > 0)


# ---------------------------------------------------------------------------
# Signal regexes. Each detects a *concrete artefact* — something that would
# be worth recalling later.
# ---------------------------------------------------------------------------

_SIGNALS: dict[str, re.Pattern[str]] = {
    "url": re.compile(r"https?://\S+"),
    "file_path": re.compile(r"(?:[A-Za-z]:\\|/[A-Za-z]+/)[^\s\"']{2,}"),
    "ticket": re.compile(r"\b[A-Z][A-Z0-9]{1,9}-\d{1,6}\b"),
    "identifier": re.compile(r"\b[A-Z][A-Z0-9_]{3,}\b"),  # ALL_CAPS constants/tags
    "command": re.compile(r"`[^`\n]{3,}`"),  # inline code
    "fenced_code": re.compile(r"```[a-zA-Z0-9_+\-]*\n.+?\n```", re.DOTALL),
    "structured_list": re.compile(
        r"(?m)^\s*(?:[-*+]|\d+\.)\s+\S.+(?:\n\s*(?:[-*+]|\d+\.)\s+\S.+){2,}"
    ),
    "table": re.compile(r"(?m)^\s*\|.+\|\s*\n\s*\|[\s\-:|]+\|"),
}

_FORCE_MARKER = re.compile(r"(?i)(?:^|\s)!store\b")


def check(
    text: str,
    *,
    min_signals: int = 1,
    min_word_count: int = 8,
) -> WorthinessReport:
    """Decide whether ``text`` should be stored.

    Parameters
    ----------
    text
        The candidate chunk *after* redaction.
    min_signals
        Minimum distinct signal kinds the chunk must carry to be stored
        without an explicit force directive.
    min_word_count
        Below this word count, the chunk is rejected regardless of signals
        (unless force-stored).

    Returns
    -------
    WorthinessReport
        The verdict plus diagnostic breakdown.

    Examples
    --------
    >>> check("ok").verdict
    <Verdict.REJECT: 'reject'>
    >>> r = check("!store Engram stores notes at C:/Users/x/engram/notes/")
    >>> r.verdict
    <Verdict.FORCE: 'force'>
    """
    signals = {name: len(pat.findall(text)) for name, pat in _SIGNALS.items()}
    word_count = len(text.split())
    distinct = sum(1 for v in signals.values() if v > 0)

    if _FORCE_MARKER.search(text):
        return WorthinessReport(
            verdict=Verdict.FORCE,
            signals=signals,
            word_count=word_count,
            reason="explicit !store directive",
        )

    if word_count < min_word_count:
        return WorthinessReport(
            verdict=Verdict.REJECT,
            signals=signals,
            word_count=word_count,
            reason=f"too short ({word_count} words < {min_word_count})",
        )

    if distinct < min_signals:
        return WorthinessReport(
            verdict=Verdict.REJECT,
            signals=signals,
            word_count=word_count,
            reason=f"insufficient signals ({distinct} kinds < {min_signals})",
        )

    return WorthinessReport(
        verdict=Verdict.STORE,
        signals=signals,
        word_count=word_count,
        reason=f"{distinct} signal kind(s) detected",
    )
