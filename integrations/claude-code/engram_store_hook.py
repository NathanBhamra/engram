#!/usr/bin/env python3
"""Claude Code Stop hook for Engram.

Reads the hook JSON payload from stdin, locates the conversation transcript,
extracts the last assistant message, and pipes it through `engram store`.
Engram's worthiness filter is responsible for rejecting low-signal content,
so this hook deliberately stores eagerly.

Install: see ./README.md
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Final

_PYTHON: Final = os.environ.get("ENGRAM_PYTHON") or shutil.which("python") or "python"
_MIN_LEN: Final = int(os.environ.get("ENGRAM_STORE_MIN_CHARS", "120"))


def _read_transcript(path: str | None) -> str:
    if not path:
        return ""
    p = Path(path)
    if not p.exists():
        return ""
    try:
        return p.read_text(encoding="utf-8")
    except OSError:
        return ""


def _last_assistant_message(transcript: str) -> str:
    # Claude Code transcripts are JSONL with {"role": "...", "content": "..."}.
    last = ""
    for line in transcript.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if entry.get("role") == "assistant":
            content = entry.get("content")
            if isinstance(content, str):
                last = content
            elif isinstance(content, list):
                # content blocks; concatenate text blocks
                parts = [
                    blk.get("text", "")
                    for blk in content
                    if isinstance(blk, dict) and blk.get("type") == "text"
                ]
                last = "\n\n".join(p for p in parts if p)
    return last


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0

    transcript_path = payload.get("transcript_path")
    session_id = payload.get("session_id") or ""
    text = _last_assistant_message(_read_transcript(transcript_path))

    if not text or len(text) < _MIN_LEN:
        return 0

    cmd = [_PYTHON, "-m", "engram", "store", "--type", "pattern", "--tag", "claude-code"]
    if session_id:
        cmd.extend(["--session", session_id])

    try:
        subprocess.run(
            cmd,
            input=text,
            text=True,
            capture_output=True,
            timeout=15,
            check=False,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
