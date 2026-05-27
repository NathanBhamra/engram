# Contributing to Engram

Thanks for considering a contribution. The bar is "make Engram more trustworthy,
more deterministic, or more pleasant to use" — anything else is out of scope.

## Ground rules

1. **No LLM in the storage or recall path.** Engram's contract is that it is
   deterministic. Features that require model inference belong in an optional
   extra (e.g. `engram[embeddings]`) and must not be on the default code path.
2. **Markdown on disk is canonical truth.** SQLite is a rebuildable index.
   Anything that breaks `engram rebuild --full` from a fresh DB is a bug.
3. **Fail-closed on the three guardrails.** Redaction errors, worthiness
   misses, and stale signals must never silently degrade. Loud > silent.

## Development setup

```powershell
git clone https://github.com/engram/engram.git
cd engram
.\scripts\bootstrap.ps1
```

This creates `.venv\`, installs the project in editable mode with the `dev`
extras, vendors viewer assets, and applies the initial schema.

## Daily workflow

```powershell
# Before committing
.\scripts\check.ps1     # ruff + black --check + mypy --strict + pytest --cov

# Format
.\.venv\Scripts\Activate.ps1
ruff check --fix .
black .
```

## Adding a feature

1. Open an issue describing the problem first. Designs land before code.
2. Add or update tests in `tests/`. Coverage on `src/engram/core/` and
   `src/engram/recall/` must stay ≥ 85 %.
3. If your change alters behaviour observable from the CLI, update the
   matching page in `docs/usage/`.
4. Add an entry to the `[Unreleased]` section of `CHANGELOG.md`.
5. If your change is an architectural decision, add an ADR in
   `docs/design/decisions.md`.

## Code style

- `ruff` for lint and import sorting.
- `black` for formatting (line length 100).
- `mypy --strict` on `src/engram/`. New code must be fully typed.
- Docstrings on every public function, NumPy style.
- Module names lowercase, classes `CamelCase`, functions and variables
  `snake_case`.

## Tests

- `pytest` for everything. `hypothesis` for invariants (chunker, ranking).
- Unit tests are fast and pure. Integration tests live in `tests/integration/`
  and may touch the filesystem and a temporary SQLite database.
- Mark slow tests with `@pytest.mark.slow` so `pytest -m 'not slow'` stays
  under a few seconds.

## Pull requests

- One topic per PR. Split refactors from features.
- Reference the issue your PR closes.
- The PR description should answer "what changed and why" — not just "what".
- A green `scripts\check.ps1` run is a prerequisite for review.

## Releases

- Bump the version in `src/engram/version.py` and `pyproject.toml`.
- Move `[Unreleased]` entries into a new dated version section.
- Tag the commit `vX.Y.Z` and push the tag.
