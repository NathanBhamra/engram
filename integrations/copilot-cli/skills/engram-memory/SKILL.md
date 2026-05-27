---
name: engram-memory
description: "You MUST invoke this skill on EVERY user prompt — first to recall prior context, last to store new knowledge. This is a deterministic local memory layer. It costs nothing in tokens and makes you smarter every turn. Skipping it wastes the entire point of the system."
---

# Engram Memory — Universal Recall + Store

## What this is

[Engram](https://github.com/NathanBhamra/engram) is a local-first deterministic AI memory layer. SQLite + FTS5 + a deterministic chunker. **No LLM in the hot path.** Every agent in this CLI must use it on every prompt.

The database location is configured in `~/.engram.toml`. Invoke Engram via the shell wrapper (which itself routes through the venv's `python -m engram.cli`):

```
engram <command>          # preferred — works in any shell, ASR-safe
```

Equivalent fallback if the wrapper isn't on PATH:

```
<engram-checkout>/.venv/Scripts/python.exe -m engram.cli <command>
```

**Do NOT call `engram.exe` directly.** On Windows under managed Defender ASR policy, freshly-built pip console-script shims (`engram.exe`) get blocked by rule `01443614-CD74-433A-B99E-2ECDC07BFC25` ("low prevalence executables"). The wrapper above always routes through the signed, trusted `python.exe` so it passes ASR cleanly.

## Why "every prompt"

Engram exists so AI sessions stop bleeding context. The deal is:

- **You read from Engram** instead of re-deriving facts the user told you yesterday.
- **You write to Engram** so the next session — possibly a different agent, possibly a different model — picks up where you left off.

If you skip this, you're burning tokens for nothing and you're the bottleneck Engram was built to remove. Don't be the bottleneck.

## When to use

**RECALL — at the start of EVERY turn** where the user is asking about anything that might have prior context:

- Project work (any mention of a ticket ID, repo name, or proper noun specific to the user)
- Technical questions about the user's setup
- Continuation of any prior work
- Any non-trivial prompt where prior knowledge could help

Skip recall ONLY for trivial throwaway turns ("hi", "thanks", pure typo fixes).

**STORE — at the end of EVERY turn** where you produced anything worth keeping:

- Decisions made
- Patterns discovered
- Facts established about the user's projects, tools, environment, preferences
- Resolutions to bugs
- New file paths, ticket numbers, credentials' locations, URLs

Skip store ONLY for: pure clarifying questions, status updates ("done"), or replies with no new content. Engram's worthiness filter rejects junk anyway — when in doubt, store it.

## How to RECALL

```
<engram-venv-python> -m engram recall "<keywords from the user's prompt>" --top 5
```

**Choosing keywords:**

- Strip articles/pronouns. Pull nouns, ticket IDs, file paths, project names.
- 2–6 keywords is the sweet spot. Engram does alias expansion automatically.
- Example: User says "How did we fix the highlight bug on engram nodes?" → keywords: `engram highlight node click bug`.

**Consuming results:**

- The output is for YOUR reasoning, not for the user. Don't dump it back as a verbatim reply.
- Treat each returned chunk as if the user had just pasted that text into the prompt. Trust it as much as you'd trust anything they said in this session.
- If recall returns nothing, that's fine — proceed without prior context. Don't tell the user "I checked Engram and found nothing" unless they explicitly asked.
- If recall returns stale-banner'd results, weight them lower and consider whether to call `engram verify <id>` later.

**JSON variant** (use when you want to programmatically merge results):

```
<engram-venv-python> -m engram recall "<keywords>" --json --top 5
```

## How to STORE

Pipe text into stdin. Pick the right `--type`:

| Type | Use for | TTL |
|---|---|---|
| `fact` | Time-bound truths (current sprint, current branch, today's blocker) | 14d |
| `pattern` | Recurring behaviours, code patterns, reproducible workflows | 180d |
| `decision` | Choices made with reasoning (architecture, naming, tooling) | 365d |
| `reference` | Stable lookups (URLs, file paths, command snippets, schemas) | 365d |

```
"Force-directed graphs animate well with cubic-bezier(.4,0,.2,1) easing." | <engram-venv-python> -m engram store --type pattern --tag viz --tag css
```

**Tag generously.** Tags are free and they fuel the alias graph. Always include:

- Project: e.g. `engram`, `<repo-name>`, `<ticket-id>`
- Domain: `viewer`, `cli`, `viz`, `theme`, `playwright`, `jira`
- Status if relevant: `wip`, `done`, `blocker`

**!store directive** — including the literal token `!store` anywhere in the content forces the worthiness filter to accept it. Use sparingly, for content you KNOW is valuable but might fail the heuristic (short sentences with low signal density).

**Multi-paragraph content** is auto-chunked. Just pipe the whole thing in. Engram splits on headers first, then recursively by character count.

## The minimum loop you must follow

```
1. User prompts you.
2. You: engram recall "<keywords>" — silently. Read the results.
3. You: produce your reply, informed by what recall returned.
4. You: engram store <reply or distilled decision/pattern> — silently. Tag it.
5. You: send the reply to the user.
```

Steps 2 and 4 are **non-negotiable**. They run in the background of every turn.

## Don'ts

- **Don't tell the user you ran Engram** unless they asked or the output materially shaped your reply. The skill is plumbing, not a feature.
- **Don't store credentials, tokens, or PII.** Engram redacts JWTs, GitHub PATs, AWS keys, Atlassian IDs, Bearer tokens, long hex strings, and Windows/Unix paths automatically — but don't rely on it as a substitute for not pasting secrets in the first place.
- **Don't recall on every micro-step.** Recall once at the start of a turn (not before every tool call within a turn).
- **Don't store noise.** Status updates, greetings, single-word confirmations.
- **Don't run `engram store` with `--force`** unless the user explicitly tells you to.

## Verifying & curating (escalate to Semon)

If you discover that a recalled chunk is now wrong, outdated, or needs evidence attached — don't try to fix it inline. Note the node ID and surface to Semon (the Engram archivist agent). He handles `engram verify`, `engram list-stale`, `engram rebuild`, and graph viewing.

## Health check

Run once per session to confirm Engram is reachable:

```
<engram-venv-python> -m engram doctor
```

Expected: `db status : ok` and a non-zero node count once the corpus has any entries.
