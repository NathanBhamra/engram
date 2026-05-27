# Engram

A self-sufficient, local-first, deterministic memory layer for AI sessions,
paired with a force-directed graph viewer for the knowledge it accumulates.

The AI is dumb plumbing. Engram does the chunking, indexing, ranking, and
visualisation. No subscriptions, no cloud calls, no LLM in the storage path.

## Where to start

If you are **new to Engram**, work through the getting-started guide in
order. It takes about ten minutes.

- [Install](getting-started/install.md)
- [Your first `store`](getting-started/first-store.md)
- [Your first `recall`](getting-started/first-recall.md)
- [View the graph](getting-started/viewing-the-graph.md)

If you want to **understand the design** before using it, read:

- [Why deterministic?](concepts/why-deterministic.md)
- [Nodes and edges](concepts/nodes-and-edges.md)
- [Recall ranking](concepts/recall-ranking.md)
- [Staleness](concepts/staleness.md)

If you are **integrating with an AI tool**:

- [Copilot CLI and Claude Code](advanced/ai-integration.md)

## Project status

Alpha. Phase 0 (foundations) is on disk; Phase 1 (the working CLI) is in
progress. See [`CHANGELOG.md`](https://github.com/engram/engram/blob/main/CHANGELOG.md)
for what's shipped.
