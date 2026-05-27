# Install

## Requirements

- Windows, macOS, or Linux
- Python 3.11 or newer
- About 50 MB of disk space for the venv and viewer assets

Engram has no admin-level dependencies and is intended to install entirely
inside a user-scope virtualenv.

## One-command (Windows / PowerShell)

```powershell
git clone https://github.com/engram/engram.git
cd engram
.\scripts\bootstrap.ps1
```

The bootstrap script:

1. Locates a Python 3.11+ interpreter (PATH, then `py` launcher, then the
   per-user install under `%LOCALAPPDATA%\Programs\Python\`).
2. Creates `.venv\` next to the repository root.
3. Installs Engram in editable mode with `dev` and `docs` extras.
4. Vendors the viewer JavaScript into `src/engram/viz/assets/`.
5. Runs the test suite as a smoke check.

If the test suite passes, Engram is ready.

## Manual setup

If you prefer to drive each step yourself:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip wheel setuptools
pip install -e ".[dev,docs]"
.\scripts\vendor-assets.ps1
engram --version
```

## Corporate proxy

If `pip install` fails because of a proxy, configure it once:

```powershell
$env:HTTP_PROXY  = 'http://proxy:8080'
$env:HTTPS_PROXY = 'http://proxy:8080'
pip install -e ".[dev,docs]"
```

The Phase 2 embeddings extra (`engram[embeddings]`) downloads model weights
from Hugging Face on first run. If your proxy blocks that, leave embeddings
disabled — Engram's default FTS5 path is fully featured without them.

## Verifying

```powershell
engram --version
engram doctor
```

The first command should print `engram 0.1.0` (or higher). The second runs
diagnostics and reports the configuration source, database path, schema
version, and FTS5 health.
