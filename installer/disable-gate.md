# /disable-gate — Remove an installed hard gate

Target to remove: $ARGUMENTS

If no target specified, list installed gates:
```bash
ls .claude/hooks/*-gate.sh 2>/dev/null | sed 's/.*\///' | sed 's/-gate\.sh//'
```
Ask which one to remove.

## Removal steps (execute in order):

1. **Back up project settings.json**: `cp .claude/settings.json .claude/settings.json.bak-$(date +%Y%m%d-%H%M%S)`
2. **Remove hook scripts**: Delete `.claude/hooks/<target>-gate.sh`, `.claude/hooks/<target>-gate.py`, `.claude/hooks/<target>-session-start.sh`, `.claude/hooks/<target>-session-start.py`, and `.claude/hooks/<target>-stop-check.sh` (if they exist)
3. **Remove project settings.json hook entries**: Remove PreToolUse, PostToolUse, Stop, and SessionStart entries that reference the deleted scripts from `.claude/settings.json`. Use python3 for safe JSON editing. Do NOT remove the permissions block.
4. **Remove CLAUDE.md rule**: Find and remove the Hard Rule block for this target from `~/.claude/CLAUDE.md`. Do NOT remove other rules or renumber them.
5. **Remove project CLAUDE.md rule**: Same, if a project CLAUDE.md exists.
6. **Remove memory file**: Delete `~/.claude/projects/*/memory/<target>-gate.md`
7. **Do NOT remove permissions**: Leave `~/.claude/settings.json` permissions.allow entries intact — removing them could break other things.

## Safety:
- Ask for confirmation before deleting anything. Show what will be deleted first.
- Protected targets that require extra confirmation: context-mode, coder-ui-qa-test
- After removal, remind user to restart Claude Code / Cowork.
