# hardgate — offline installer

This archive installs hardgate's three files into `~/.claude/`:

```
~/.claude/skills/hard-gate-installer/SKILL.md
~/.claude/commands/hard-gate.md
~/.claude/commands/disable-gate.md
```

## Requirements

- Claude Desktop (with Cowork enabled) or Claude Code CLI
- Any paid Claude plan (Pro, Max, Team, Enterprise)
- `bash` (Mac / Linux / git-bash on Windows) OR PowerShell 5.1+ (Windows)

## Install

### Mac / Linux / git-bash

```bash
bash install.sh
```

### Windows (PowerShell)

```powershell
.\install.ps1
```

If PowerShell blocks the script, allow it for this session only:

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

## What it does

1. Creates `~/.claude/skills/hard-gate-installer/` and `~/.claude/commands/` if they don't exist.
2. **Backs up** any existing `SKILL.md`, `hard-gate.md`, or `disable-gate.md` at those paths with a timestamp suffix. Nothing is overwritten without a backup.
3. Copies the three files into place.
4. Prints the install paths and the next steps.

## After install

1. **Restart Claude Code** (or Cowork's Code tab). Slash commands and skills load at session start.
2. **Type `/hard-gate`** in a new session. The installer will discover your installed plugins, skills, and commands and ask which one to gate.

## Uninstall

Delete the three installed files:

```bash
rm ~/.claude/skills/hard-gate-installer/SKILL.md
rm ~/.claude/commands/hard-gate.md
rm ~/.claude/commands/disable-gate.md
```

To remove an installed gate from a specific project, use `/disable-gate <name>` inside that project's session. That's a separate operation from uninstalling hardgate itself.

## Documentation

- Landing page: https://scottconverse.github.io/hardgate/
- Source repo: https://github.com/scottconverse/hardgate
- Full user manual: https://github.com/scottconverse/hardgate/blob/main/USER-MANUAL.md

MIT License — © 2026 Scott Converse
