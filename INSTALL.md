# Quick Install

Download the latest release from [GitHub Releases](https://github.com/scottconverse/hardgate/releases/latest), then run:

**macOS / Linux:**
```bash
bash install.sh
```

**Windows (PowerShell):**
```powershell
pwsh -File install.ps1
```

Restart the Code tab, then type `/hard-gate`. It discovers your installed plugins, skills, and commands, asks which one to gate, writes 7 enforcement artifacts, and runs a behavioral test.

<details>
<summary>Manual install (alternative)</summary>

Copy three files from this repo:

```
~/.claude/skills/hard-gate-installer/SKILL.md   ← from this repo's SKILL.md
~/.claude/commands/hard-gate.md                  ← from this repo's hard-gate.md
~/.claude/commands/disable-gate.md               ← from this repo's disable-gate.md
```

```bash
mkdir -p ~/.claude/skills/hard-gate-installer
mkdir -p ~/.claude/commands
```

</details>
