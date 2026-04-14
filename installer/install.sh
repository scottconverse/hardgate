#!/usr/bin/env bash
# hardgate installer — bash (Mac / Linux / git-bash on Windows)
# Places SKILL.md, hard-gate.md, and disable-gate.md under ~/.claude/

set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Resolve ~/.claude on all platforms
if [[ -n "${HOME:-}" ]]; then
    CLAUDE_HOME="$HOME/.claude"
elif [[ -n "${USERPROFILE:-}" ]]; then
    CLAUDE_HOME="$USERPROFILE/.claude"
else
    echo "hardgate installer: cannot locate home directory (HOME and USERPROFILE both unset)" >&2
    exit 1
fi

SKILL_DIR="$CLAUDE_HOME/skills/hard-gate-installer"
COMMANDS_DIR="$CLAUDE_HOME/commands"

echo "hardgate installer"
echo "=================="
echo "  Target: $CLAUDE_HOME"
echo ""

# Refuse if source files missing
for f in SKILL.md hard-gate.md disable-gate.md; do
    if [[ ! -f "$SCRIPT_DIR/$f" ]]; then
        echo "ERROR: missing source file $SCRIPT_DIR/$f" >&2
        echo "       Run this script from the unpacked installer directory." >&2
        exit 2
    fi
done

# Create directories
mkdir -p "$SKILL_DIR"
mkdir -p "$COMMANDS_DIR"

# Back up any existing files
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
backup_if_exists() {
    local f="$1"
    if [[ -f "$f" ]]; then
        cp "$f" "$f.bak-$TIMESTAMP"
        echo "  backed up: $f -> $f.bak-$TIMESTAMP"
    fi
}
backup_if_exists "$SKILL_DIR/SKILL.md"
backup_if_exists "$COMMANDS_DIR/hard-gate.md"
backup_if_exists "$COMMANDS_DIR/disable-gate.md"

# Install
cp "$SCRIPT_DIR/SKILL.md"        "$SKILL_DIR/SKILL.md"
cp "$SCRIPT_DIR/hard-gate.md"    "$COMMANDS_DIR/hard-gate.md"
cp "$SCRIPT_DIR/disable-gate.md" "$COMMANDS_DIR/disable-gate.md"

echo ""
echo "Installed:"
echo "  $SKILL_DIR/SKILL.md"
echo "  $COMMANDS_DIR/hard-gate.md"
echo "  $COMMANDS_DIR/disable-gate.md"
echo ""
echo "Next steps:"
echo "  1. Restart Claude Code / Cowork's Code tab."
echo "  2. Type /hard-gate to install your first gate."
echo ""
echo "Documentation: https://scottconverse.github.io/hardgate/"
