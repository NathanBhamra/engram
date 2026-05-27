# Why deterministic?

The premise of Engram is that AI sessions waste tokens on rediscovery.

If the cure for that requires another model call, the cure is the disease.
Every retrieval that requires inference adds latency, cost, and a fresh
source of stochasticity. So Engram's storage and recall paths are pure code:
rule-based chunking, BM25 ranking, an alias table for query expansion. The
optional embeddings layer is gated behind a config flag and a connectivity
test, and even when enabled it only refines a result set that BM25 already
produced — it cannot save a query that keyword search misses.

This has consequences.

## What you give up

- **No semantic-only matches.** "Aristotle" and "philosopher" will not match
  unless one is in the alias table or both happen to share a tag.
- **No paraphrase tolerance.** "Sectional tagging" will not match the note
  about `@SECTION` unless the alias is registered.
- **No conversational re-ranking.** If a recall returns three results and
  the user is really asking about the second, Engram will not infer that.

## What you gain

- **Reproducibility.** The same query against the same database returns
  the same nodes in the same order, forever.
- **Auditability.** Every step of the pipeline — what was redacted, what
  was filtered, what was ranked — is inspectable in the audit log.
- **Latency under 200 ms.** No model load, no network call, no GPU.
- **Cost: zero per query.** The only cost is the disk space the SQLite
  file occupies.
- **Failure modes you can debug.** If recall misses, the cause is one of:
  the document was not stored; the worthiness filter rejected it; the
  query terms do not appear; an alias is missing. All four are fixable
  without retraining anything.

## When you should not use Engram

- You want a model that can answer questions *about* your notes (a RAG
  chatbot). Engram returns chunks; it does not answer.
- Your corpus is fundamentally about meaning rather than identifiers,
  URLs, and structured facts (e.g. a poetry collection).
- You want recommendations rather than recall.

For those, you want a different tool. Engram is a memory, not a brain.
