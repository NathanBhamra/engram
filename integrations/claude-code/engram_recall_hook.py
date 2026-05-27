#!/usr/bin/env python3
"""Claude Code UserPromptSubmit hook for Engram.

Reads the hook JSON payload from stdin, extracts the prompt text, runs
`engram recall` against it, and emits the recall output back to Claude Code
so that it is prepended to the prompt context.

Install: see ./README.md
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from typing import Final

_PYTHON: Final = os.environ.get("ENGRAM_PYTHON") or shutil.which("python") or "python"
_TOP: Final = os.environ.get("ENGRAM_RECALL_TOP", "5")
_BUDGET: Final = os.environ.get("ENGRAM_RECALL_BUDGET", "1500")


def _extract_keywords(prompt: str) -> str:
    # Naive but deterministic: keep words 3+ chars, drop common stop words.
    stop = {
        "the", "and", "for", "with", "that", "this", "from", "into", "your",
        "you", "are", "but", "not", "have", "has", "was", "were", "what",
        "how", "why", "when", "where", "who", "can", "will", "would", "should",
        "tell", "about", "explain", "show", "give", "let", "lets", "please",
        "could", "ask", "want", "need", "say", "said", "get", "got", "make",
        "made", "use", "used", "using", "any", "all", "some", "more", "most",
        "less", "much", "many", "still", "just", "also", "too", "very", "well",
        "now", "then", "here", "there", "than", "them", "they", "their",
    }
    words = [w.strip(".,!?:;\"'()[]{}").lower() for w in prompt.split()]
    keywords = [w for w in words if len(w) >= 3 and w not in stop]
    # Cap to ~8 keywords. FTS5 uses AND by default so fewer is better.
    return " ".join(keywords[:8])


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0  # silent failure — never break the user's session

    prompt = (payload.get("prompt") or "").strip()
    if not prompt or len(prompt) < 8:
        return 0

    query = _extract_keywords(prompt)
    if not query:
        return 0

    try:
        result = subprocess.run(
            [_PYTHON, "-m", "engram", "recall", query, "--top", _TOP, "--budget", _BUDGET],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return 0

    body = (result.stdout or "").strip()
    if not body or "No matches" in body:
        return 0

    print("<engram-recall>")
    print("# Prior context from Engram (your local memory)")
    print(body)
    print("</engram-recall>")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
