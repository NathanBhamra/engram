# Engram

> *"The engram is the enduring change which the stimulus leaves behind in
> the organism — the trace that makes recall possible."*
> — Richard Semon, *Die Mneme*, 1904 (paraphrased)

A **self-sufficient, local-first, deterministic memory layer** for AI sessions,
paired with a force-directed graph viewer for the knowledge it accumulates.

The AI is dumb plumbing. Engram does the chunking, indexing, ranking, and
visualisation. No subscriptions, no cloud calls, no LLM in the storage path.

## Why

| Problem                                | Engram                                            |
| -------------------------------------- | ------------------------------------------------ |
| AI sessions are amnesiac               | `recall` injects relevant prior knowledge        |
| Re-research wastes tokens              | Deterministic index returns answers in < 200 ms  |
| Knowledge dies in chat history         | Stored as plain markdown, git-versionable        |
| No way to *see* what you know          | A live, navigable graph                          |
| Stale facts go silently wrong          | TTLs + loud-stale banners + verification flow    |

## Install

Requires Python 3.11+.

```powershell
git clone https://github.com/engram/engram.git
cd engram
.\scripts\bootstrap.ps1
```

This creates a virtualenv in `.venv\`, installs Engram in editable mode with
all dev dependencies, vendors the viewer JS, and applies the initial schema.

## First run

```powershell
# Store a note from stdin
"The QA section tag for Activity Investigation is ACTIVITY_INVESTIGATION." | engram store --type fact --tag jira --tag qa

# Recall it later
engram recall "activity investigation section tag"

# See your knowledge graph
engram view --open
```

## Documentation

The full documentation lives in [`docs/`](docs/) and is built with
`mkdocs-material`:

```powershell
.\scripts\make-docs.ps1
```

Key entry points:

- [Why deterministic?](docs/concepts/why-deterministic.md)
- [Concepts: nodes and edges](docs/concepts/nodes-and-edges.md)
- [CLI reference](docs/usage/cli-reference.md)
- [Architecture](ARCHITECTURE.md)

## Status

Alpha. See [`CHANGELOG.md`](CHANGELOG.md) for what's shipped.

## Licence

[MIT](LICENSE).
