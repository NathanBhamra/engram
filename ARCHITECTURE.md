# Architecture

This document explains *why* Engram is shaped the way it is. For the *what*,
see the [`docs/`](docs/) directory.

## One-paragraph summary

Engram is a deterministic memory layer for AI sessions. Markdown files on disk
are the canonical truth; SQLite (with FTS5) is a rebuildable index. The AI
calls two CLI commands — `engram store` and `engram recall` — and a force-directed
graph viewer renders the accumulated knowledge. There is no LLM in the storage
or recall path.

## High-level diagram

```
                    +-----------------------------+
                    |        AI session           |
                    | (Copilot CLI / Claude Code) |
                    +--------------+--------------+
                                   |
                  recall "<terms>" |   store < response
                                   v
              +------------------------------------+
              |             engram CLI              |
              |   (click + python stdlib + FTS5)   |
              +---+---------+--------+---------+---+
                  |         |        |         |
              redact   chunker   recall.fts  viz.exporter
                  |         |        |         |
                  v         v        v         v
          +----------------------------------------+
          |         markdown notes/  (truth)       |
          |         engram.db         (index)       |
          +----------------------------------------+
                                   |
                                   v
                       +---------------------+
                       |  static viz.html    |
                       |  (vis-network)      |
                       +---------------------+
```

## Why deterministic

The premise of Engram is that AI sessions waste tokens on rediscovery. If the
solution to that problem itself requires an LLM, the cure is the disease.
Therefore:

- **Chunking** uses `langchain-text-splitters`' rule-based splitter.
- **Indexing** uses SQLite FTS5 with BM25 ranking.
- **Retrieval** uses keyword expansion via an alias table.
- **Embeddings** are an *optional* phase, gated on corporate-proxy
  connectivity, and only used in a Reciprocal Rank Fusion alongside BM25.

## Why SQLite

- Zero installation; ships with Python.
- FTS5 with BM25 is built in and battle-tested.
- The whole index is a single file you can copy, version, or delete.
- `sqlite-vec` provides vector search in the same file when we need it.

## Why markdown on disk

- Humans can read and edit notes without Engram running.
- Git is the only versioning we need.
- The index is always rebuildable from the notes — there is no "lost data"
  failure mode.

## The three guardrails

These are not features; they are correctness requirements without which
Engram would be a liability.

1. **Redaction before chunking.** Strip filesystem paths, secrets, account
   IDs before they ever reach storage. Fail-closed: if redaction errors,
   refuse to store.
2. **Store-worthiness filter.** Reject conversational noise. A chunk earns
   storage only if it carries at least one of: URL, file path, identifier,
   structured list, or explicit user `!store` directive.
3. **Loud-stale signals.** Every recalled node carries `[verified N days
   ago]` in output. Past-TTL nodes get BM25 rank halved and a quarantine
   flag. The AI integration layer requires the banner be echoed.

## The `nodes` / `edges` model

- A **node** is a single markdown file with YAML frontmatter (id, type, tags,
  ttl_days, verified_on) and a body. Every chunk becomes one node.
- An **edge** is a typed relationship: `wiki-link`, `co-recall`,
  `shared-tag`, or `manual`. Stored in a real table, not implicit.

This lets the graph viewer treat edges as first-class objects (colour by
type, weight by recency) instead of inferring them at render time.

## What lives where

| Concern                   | Module                          |
| ------------------------- | ------------------------------- |
| CLI surface               | `engram.cli`, `engram.commands.*` |
| Storage primitives        | `engram.core.db`, `schema/`      |
| Pre-storage pipeline      | `engram.core.redaction`, `engram.core.worthiness`, `engram.core.chunker` |
| Index / retrieval         | `engram.recall.fts`, `engram.recall.ranking` |
| Graph algorithms          | `engram.core.graph`              |
| Visualisation             | `engram.viz.*`                   |
| AI integration helpers    | `engram.integrations.*`          |

## Migration strategy

The DB has a `schema_version` table from day one. Every schema change ships
as `src/engram/core/schema/NNN_<description>.sql`. `engram.core.db.migrate()`
applies any unapplied files in order and updates the version row. There is
no in-place schema editing.

## Decision records

Significant design decisions are recorded as ADRs in
[`docs/design/decisions.md`](docs/design/decisions.md). Future contributors
should append rather than rewrite.
