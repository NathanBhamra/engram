# Architecture Decision Records

Decision records are append-only. Each entry captures the context, the
decision, and the consequences. Never edit a past entry — supersede it
with a new one.

## ADR-001 — Engram shall not call an LLM in its storage or recall path

**Date:** 2025-11-12
**Status:** Accepted

**Context.** Engram exists to reduce the token cost of AI sessions. The
naive way to build a "knowledge memory" is to ask a model to extract
facts, embed them, and re-rank retrievals against the query.

**Decision.** Storage, indexing, ranking, and retrieval are all pure code.
Embeddings are an *optional* layer (`engram[embeddings]`), and even when
enabled they are fused with BM25 via Reciprocal Rank Fusion rather than
replacing it.

**Consequences.** We accept reduced semantic recall in exchange for zero
per-query cost, sub-200 ms latency, full reproducibility, and a transparent
failure mode.

---

## ADR-002 — Markdown on disk is the canonical store; SQLite is the index

**Date:** 2025-11-12
**Status:** Accepted

**Context.** A pure-DB store loses portability and makes corruption
catastrophic.

**Decision.** Every node is a markdown file with YAML frontmatter under
`notes/`. The SQLite database under `engram.db` is a rebuildable index;
`engram rebuild --full` regenerates it from the notes directory.

**Consequences.** Users can `git diff` their knowledge. Index corruption
is a routine recovery, not a data-loss event.

---

## ADR-003 — Python is the implementation language

**Date:** 2025-11-12
**Status:** Accepted

**Context.** Node.js, .NET 8, and Java 25 were all available on the
target workstation; Python was being installed via the company portal.

**Decision.** Python 3.11+, distributed via `pyproject.toml` with a `src/`
layout.

**Consequences.** We get `langchain-text-splitters`, `networkx`,
`mkdocs-material`, and the optional `fastembed` / `sqlite-vec` stack
without writing them ourselves. The bootstrap script is responsible for
locating the per-user Python install on Windows.

---

## ADR-004 — Three guardrails (redaction, worthiness, loud-stale) are MVP-blocking

**Date:** 2025-11-12
**Status:** Accepted

**Context.** A senior-QA design review (Dave) identified three failure
modes that would make Engram a liability if shipped without them:
secrets leaking into the index, conversational noise polluting recall,
and silent stale facts producing confidently wrong answers.

**Decision.** All three are implemented as part of Phase 1 (the MVP),
not as a post-MVP hardening pass.

**Consequences.** Phase 1 is bigger than it would otherwise be. Phase 1
also produces a product that is safe to use, rather than a demo that is
not.
