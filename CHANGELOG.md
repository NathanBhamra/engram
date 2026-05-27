# Changelog

All notable changes to Engram will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.4.0] - 2026-05-27

### Added

- **3D viewer** — new `engram view --3d` flag renders a WebGL knowledge graph
  to `viz-3d.html` using `3d-force-graph` + Three.js with `UnrealBloomPass`
  bloom, optional edge particles, and orbit / fit / reset camera presets.
- **Auto-named clusters** — clusters are now labelled from their most
  distinctive tags using a TF-IDF-style score (`tf × log((N+1)/(1+df))`),
  with a title-keyword fallback when a cluster has no tags. Names appear in
  cluster filter chips, the colour legend, the hover tooltip, and the
  selection info card across both viewers. `metrics.cluster_labels()` is
  the new public helper; `cluster_counts()` now returns a `label` field.
- **Cross-viewer mode pill** — the brand row in each viewer shows a single
  pill that switches to the other mode (2D ↔ 3D); the 3D viewer also
  carries a pulsing **BETA** badge so it's clear the WebGL viewer is WIP.
- **Shared design language** — the 3D viewer's sidebar, panels, filter
  sections, watermark, version footer, and chip styling now match the
  2D viewer pixel for pixel; both viewers share the same CSS variables,
  glassmorphism skin, collapsible sections, and stats-grid layout.
- **Three-pinned-version policy** — `static-3d.html.jinja` pins
  `three@0.184.0` in its importmap to match what `3d-force-graph@1.73.4`
  bundles, preventing `UnrealBloomPass` from blowing up on version drift.

### Changed

- **Public-repo scrub** — README example, plugin manifest, skill, agent
  doc, and test fixtures rewritten to remove all internal/company strings
  (project keys, runner names, internal tooling) so the public repo reads
  as a generic open-source project.
- **Sidebar stats** — the 3D viewer's stats grid moved out of a
  collapsible section and now sits at the top of the sidebar to match
  the 2D viewer.

### Notes

- 61/61 tests passing.
- No new runtime dependencies (3D viewer is CDN-only at runtime).

## [0.3.0] - 2026-05-27

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

[Unreleased]: https://github.com/NathanBhamra/engram/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/NathanBhamra/engram/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/NathanBhamra/engram/releases/tag/v0.3.0
