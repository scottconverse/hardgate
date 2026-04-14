# Quick Install

## Step 1: Copy three files

```
~/.claude/skills/hard-gate-installer/SKILL.md   ← from this repo's SKILL.md
~/.claude/commands/hard-gate.md                  ← from this repo's hard-gate.md
~/.claude/commands/disable-gate.md               ← from this repo's disable-gate.md
```

Or paste this into a Claude Code / Cowork session:

```
mkdir -p ~/.claude/skills/hard-gate-installer
mkdir -p ~/.claude/commands
```

Then tell Claude: "Create these three files with the following contents:" and paste each file.

## Step 2: Restart the Code tab

## Step 3: Type `/hard-gate`

It discovers your installed plugins, skills, and commands, asks which one to gate, writes 7 enforcement artifacts, and runs a behavioral test.

That's it.
