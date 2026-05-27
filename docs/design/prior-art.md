# Prior art

Engram sits in a crowded field. Here is an honest comparison.

## mem0

LLM-based memory: extracts "memories" from conversation via a model, then
re-ranks them on recall with another model. Slick API, hosted SaaS.

**Why we are not it:** the model in the storage path defeats the
token-saving premise. Engram's recall is free per query; mem0's is not.

## Letta (formerly MemGPT)

Agent framework with a memory abstraction. Tightly coupled to the agent
loop; the memory is not portable across tools.

**Why we are not it:** Engram is a *passive* memory you can talk to from
any tool. We do not want to own the agent.

## txtai

Embeddings-first deterministic semantic search in SQLite. The closest
prior art architecturally.

**Why we are different:** Engram is opinionated about storage hygiene
(the three guardrails), node typing, edge typing, staleness, and the
graph view. txtai is a search engine; Engram is a memory.

## Graphiti

LLM-extracted temporal knowledge graph with neo4j storage.

**Why we are not it:** neo4j is not a per-user install on a work laptop,
and the LLM extractor is what we are explicitly avoiding.

## Obsidian and obsidian-graphify

Personal markdown notebook with a graph view. Inspiration for our viewer
aesthetic.

**Why we are different:** Obsidian is a notes app; the graph view is a
visual feature. Engram is a memory-recall service that happens to have a
graph view. Obsidian has no `recall` API.

## Acknowledgements

Every project above informed Engram's design. The credit list, in
chronological order: txtai (deterministic SQLite search), Obsidian
(markdown-as-truth, graph-as-feature), mem0 (made the memory category
mainstream), Letta (typed memory tiers), Graphiti (temporal edges).
