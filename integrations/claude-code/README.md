# Engram × Claude Code

Auto-recall and auto-store hooks for [Claude Code](https://claude.ai/code).
Mirrors the behaviour of the Copilot CLI [engram-memory](../copilot-cli/) skill.

## What it does

- **`UserPromptSubmit`** — before every prompt is sent to Claude, runs
  `engram recall` against keywords pulled from the prompt and injects the
  result as additional context.
- **`Stop`** — after every Claude response, pipes the last assistant message
  into `engram store`. Engram's worthiness filter decides what to keep.

Both hooks fail silently — if Engram isn't installed or times out, Claude Code
continues as if the hooks weren't there. They never block your session.

## Install

1. **Make sure `engram` is on your PATH or set `ENGRAM_PYTHON`:**

   ```powershell
   # If you cloned Engram and use the venv:
   $env:ENGRAM_PYTHON = "C:\path\to\engram\.venv\Scripts\python.exe"
   ```

2. **Merge `settings.example.json` into your Claude Code settings:**

   ```powershell
   # Global, all projects:
   notepad $env:USERPROFILE\.claude\settings.json

   # Or per-project:
   notepad .claude\settings.json
   ```

   Adjust the `command` paths to point at where you cloned Engram.

3. **Restart Claude Code.** The hooks fire on the next prompt.

## Verify

After a few prompts, check that nodes are being created:

```powershell
engram doctor
engram audit --op store --since 1d
```

You should see new nodes tagged `claude-code`.

## Tuning

Environment variables (set them before launching Claude Code):

| Variable | Default | Effect |
|---|---|---|
| `ENGRAM_PYTHON` | `python` on PATH | Which Python interpreter runs engram |
| `ENGRAM_RECALL_TOP` | `5` | Max chunks injected by `UserPromptSubmit` |
| `ENGRAM_RECALL_BUDGET` | `1500` | Token budget for `UserPromptSubmit` |
| `ENGRAM_STORE_MIN_CHARS` | `120` | Skip storing responses shorter than this |

## Safety

- Hooks **never raise** — `engram recall` / `engram store` failures are
  swallowed silently to avoid breaking Claude Code sessions.
- Engram's redaction layer strips Windows user paths, JWTs, GitHub PATs,
  AWS keys, Atlassian IDs, Bearer tokens, and long hex strings before
  anything hits SQLite.
- If you don't want a particular response stored, append `!nostore` anywhere
  in your prompt and the hook will skip it. *(Roadmap — not yet implemented.)*

## See also

- [Copilot CLI integration](../copilot-cli/) — equivalent setup for users on
  the GitHub Copilot CLI.
- [Architecture](../../ARCHITECTURE.md) — how the redaction / worthiness /
  chunking pipeline works.
