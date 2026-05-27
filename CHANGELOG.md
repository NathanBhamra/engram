# Changelog

All notable changes to Engram will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Repository scaffolding: `pyproject.toml`, `src/` layout, `mkdocs-material` docs skeleton.
- Initial SQLite schema (`001_initial.sql`) with versioned migrations.
- CLI skeleton with `--version` and registered subcommand placeholders.
- Bootstrap script (`scripts/bootstrap.ps1`) and check script (`scripts/check.ps1`).
- MIT licence, README, CONTRIBUTING, ARCHITECTURE.
- **Phase 1 MVP CLI** — `store`, `recall`, `verify`, `list-stale`, `audit`,
  `rebuild`, `doctor` commands fully wired end-to-end.
- **Core modules**: `redaction` (8 built-in patterns, fail-closed),
  `worthiness` (8 signal types + `!store` force), `chunker` (header-aware,
  code-fence-atomic), `notes` (markdown-on-disk frontmatter I/O),
  `aliases` (bidirectional query expansion), `storage` (orchestrator).
- **Recall pipeline**: `fts` (FTS5 BM25 with alias expansion) +
  `ranking` (past-TTL demotion, token-budget selection, stale banners).
- **Tests**: 46 unit + integration tests covering redaction, worthiness,
  chunker (incl. code-fence atomicity), aliases, FTS query construction,
  ranking, and an end-to-end store→recall round trip.
- **Phase 2 MVP Viewer** — `engram view` command renders a self-contained
  HTML knowledge graph using vis-network.
- **Viz modules**: `edges` (shared-tag jaccard ≥ 0.05, co-recall count ≥ 2,
  `[[wiki-link]]` extraction, manual edges preserved), `metrics` (NetworkX
  degree / Louvain communities / PageRank, written back to `nodes` table),
  `theme` (dark + light palettes, degree-and-pagerank node sizing),
  `exporter` (SQLite → vis-network JSON with stale colour overlay and
  per-edge-type width scaling), `renderer` (Jinja2 + vendored
  `vis-network.min.js`, CDN fallback).
- **Viewer UI**: sidebar with graph stats, legend, search and selection
  detail panel; barnesHut physics tuned for readability; dark theme default.
- **Vendored asset**: `vis-network 9.1.9` (672 KB) shipped inline so the
  generated HTML is fully offline-capable.
- **Tests**: +15 new Phase 2 tests (edges derivation, metrics recompute,
  exporter shape + quarantine filter, renderer HTML emission, CDN
  fallback). Total now 61 passing.
- **scipy** added to dependencies (required by NetworkX's PageRank).

[Unreleased]: https://github.com/engram/engram/compare/HEAD...HEAD
