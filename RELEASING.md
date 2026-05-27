# Releasing Engram

This is the canonical checklist for cutting a new version of Engram.
Follow it top-to-bottom. **Do not skip steps**, even small ones — every
step on this list is here because it was forgotten at least once.

## 0. Decide the version

Engram follows [SemVer](https://semver.org/spec/v2.0.0.html):

- **MAJOR** — breaking CLI / config / schema changes
- **MINOR** — new commands, new viewer features, new flags
- **PATCH** — bugfixes, internal refactors, docs

## 1. Update version in two places

```powershell
# src/engram/version.py
__version__ = "X.Y.Z"

# pyproject.toml
version = "X.Y.Z"
```

Both must match. Anything that reads `engram.version.__version__` (the
viewer footer, `--version` flag, `engram audit` headers) picks up the
single source of truth automatically. Anything that reads
`pyproject.toml` (pip, build tools) uses the other.

## 2. Update CHANGELOG.md

- Add `## [X.Y.Z] - YYYY-MM-DD` block above the previous release
- Group entries under `### Added`, `### Changed`, `### Fixed`,
  `### Removed`, `### Notes` (Keep a Changelog convention)
- Update the link references at the bottom:
  - `[Unreleased]` should point to `compare/vX.Y.Z...HEAD`
  - Add `[X.Y.Z]` line pointing to `compare/vPREV...vX.Y.Z`

## 3. Run the full test suite

```powershell
cd C:\Users\bhamran0\engram
.\.venv\Scripts\python.exe -m pytest -x -q
```

Must be **all green** before tagging. No exceptions.

## 4. Re-render the viewer HTMLs

**This is the step that's been forgotten three times.** The viewer
footer hardcodes the version at *render time*, not at *page-load time*,
so bumping the version without re-rendering leaves stale viz.html
files in `engram-data/` showing the old version.

```powershell
cd C:\Users\bhamran0\engram-data
& C:\Users\bhamran0\engram\.venv\Scripts\python.exe -m engram.cli view
& C:\Users\bhamran0\engram\.venv\Scripts\python.exe -m engram.cli view --3d
```

Use `--no-recompute` if you only want to refresh the HTML without
re-deriving edges. Without the flag, edges are recomputed (correct for
release builds — they should reflect current logic).

Verify by opening `viz.html` and checking the footer reads `engram
vX.Y.Z`.

## 5. Commit on a feature branch

```powershell
cd C:\Users\bhamran0\engram
git checkout -b vX.Y.Z-<short-name>
git add -A
git commit -m "vX.Y.Z — <one-line summary>

<body explaining what shipped, grouped by file/area>

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

## 6. Merge to main and tag

```powershell
git checkout main
git merge --no-ff vX.Y.Z-<short-name> -m "Merge vX.Y.Z — <summary>"
git tag -a vX.Y.Z -m "vX.Y.Z — <summary>"
```

## 7. Push (requires explicit user authorisation)

Nathan's standing rule: **no pushes without explicit authorisation per
release.** Confirm before pushing:

```powershell
git push origin main
git push origin vX.Y.Z
```

## 8. Dogfood: autostore the release fact

```powershell
"Engram vX.Y.Z shipped <date>. <one-paragraph what + where + why>." `
  | engram-autostore --tag engram --tag release --tag vX.Y.Z --verbose
```

One fact per call (v0.5.1 discipline rule). If multiple facts need
storing (e.g. release + design decision + next-version plan), make
multiple `autostore` calls.

## 9. Update plan.md status table

Mark the new version `✅ Done` in the Status table in plan.md and
add a row for the next planned version.

## 10. Close any release-tracking todos

```sql
UPDATE todos SET status='done' WHERE title LIKE '%vX.Y.Z%';
```

---

## Why no automation yet?

A future `engram release X.Y.Z` command should mechanise steps 1–4 and
parts of 5–6 so this checklist becomes shorter. Tracked for v0.6.x.
Until then, **read this file every release** — it exists because the
manual checklist is the only line of defence against forgetting a step.
