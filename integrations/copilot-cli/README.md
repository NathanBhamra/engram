# Engram × GitHub Copilot CLI

A Copilot CLI plugin scaffold that ships two pieces:

- **`engram-memory` skill** — auto-invoked on every prompt to recall prior
  context and store new knowledge. The autonomic loop.
- **`Semon` agent** — explicit archivist for curated memory work (verify,
  list-stale, rebuild, seed corpus, view graph).

Drop the contents of this directory into your Copilot CLI plugins folder to
wire any Copilot-CLI agent into Engram. The layout is:

```
engram-personal/
├── .claude-plugin/
│   └── plugin.json
├── skills/
│   └── engram-memory/
│       └── SKILL.md
├── agents/
│   └── semon.agent.md
└── README.md
```

## Install

1. Clone Engram and bootstrap:

   ```powershell
   git clone https://github.com/NathanBhamra/engram.git
   cd engram
   .\scripts\bootstrap.ps1
   ```

2. Create `~/.engram.toml` so Engram can be invoked from any directory:

   ```toml
   [paths]
   db = "C:/Users/YOU/engram-data/engram.db"
   notes_dir = "C:/Users/YOU/engram-data/notes"
   ```

3. Copy the plugin scaffold into your Copilot CLI plugins directory:

   ```powershell
   # Adjust to your Copilot CLI install location.
   $plug = "$env:USERPROFILE\.copilot\installed-plugins\engram-personal"
   New-Item -ItemType Directory -Force -Path "$plug\.claude-plugin","$plug\skills\engram-memory","$plug\agents" | Out-Null
   # Then drop SKILL.md and semon.agent.md from this repo into the respective folders.
   ```

4. Restart Copilot CLI. The skill auto-loads and Semon shows up in the
   agent list.

## How it works

Both the skill and the agent shell out to:

```
<engram-venv-python> -m engram <command>
```

…which is why the `~/.engram.toml` config and the Engram data directory are
the only state Copilot CLI needs to share with Engram. Nothing else couples
them.

## See also

- [Claude Code integration](../claude-code/) — UserPromptSubmit + Stop hooks
  for the same recall+store loop in Claude Code.
