# /disable-gate — Remove an installed hard gate

Target to remove: $ARGUMENTS

If no target specified, list installed gates:
```bash
ls .claude/hooks/*-gate.sh 2>/dev/null | sed 's/.*\///' | sed 's/-gate\.sh//'
```
Ask which one to remove.

## Removal steps (execute in order):

1. **Back up project settings.json**: `cp .claude/settings.json .claude/settings.json.bak-$(date +%Y%m%d-%H%M%S)`
2. **Remove hook scripts**: Delete `.claude/hooks/<target>-gate.sh`, `.claude/hooks/<target>-gate.py`, `.claude/hooks/<target>-session-start.sh`, `.claude/hooks/<target>-session-start.py`, `.claude/hooks/<target>-stop-check.sh`, and `.claude/hooks/<target>-stop-check.py` (if they exist — stop-check files only exist for skill targets)
3. **Remove project settings.json hook entries**: Remove `PreToolUse`, `Stop`, and `SessionStart` entries that reference the deleted scripts from `.claude/settings.json`. Use python3 for safe JSON editing. Do NOT remove the permissions block. **(B6)** Earlier versions of this script also said to remove `PostToolUse` entries; that was incorrect — hardgate has never installed `PostToolUse` hooks, so there is nothing to remove there.
4. **Remove CLAUDE.md rule**: Find and remove the Hard Rule block for this target from `~/.claude/CLAUDE.md`. Do NOT remove other rules or renumber them.
5. **Remove project CLAUDE.md rule**: Same, if a project CLAUDE.md exists.
6. **Remove memory file**: Delete `~/.claude/projects/*/memory/<target>-gate.md`
7. **Do NOT remove permissions**: Leave `~/.claude/settings.json` permissions.allow entries intact — removing them could break other things.

## Safety:

Before asking for confirmation, show the user exactly what will be removed.

**a) JSON hook entries to be removed from `.claude/settings.json`:**

```python
import json, pathlib

settings_path = pathlib.Path('.claude/settings.json')
target = '<TARGET>'  # fill in actual target name
if settings_path.exists():
    d = json.loads(settings_path.read_text())
    hooks = d.get('hooks', {})
    found = {}
    for event, entries in hooks.items():
        matching = [e for e in entries if isinstance(e, dict) and
                    target in json.dumps(e)]
        if matching:
            found[event] = matching
    if found:
        print(f"Will remove from .claude/settings.json hooks:")
        for event, entries in found.items():
            print(f"  {event}: {len(entries)} entry/entries referencing '{target}'")
            for e in entries:
                print(f"    {json.dumps(e)}")
    else:
        print(f"No hook entries found for '{target}' in .claude/settings.json")
else:
    print(".claude/settings.json not found")
```

**b) Hard Rule block to be removed from `~/.claude/CLAUDE.md`:**

```python
import re, pathlib

claude_md = pathlib.Path('~/.claude/CLAUDE.md').expanduser()
target = '<TARGET>'  # fill in actual target name
if claude_md.exists():
    text = claude_md.read_text(encoding='utf-8', errors='replace')
    pattern = rf'(### Hard Rule \d+[^\n]*\n(?:(?!### Hard Rule )[\s\S])*)'
    blocks = re.findall(pattern, text)
    matching = [b for b in blocks if target.lower() in b.lower()]
    if matching:
        print("Will remove this block from ~/.claude/CLAUDE.md:")
        print("---")
        print(matching[0][:600])
        print("---")
    else:
        print(f"No Hard Rule block found mentioning '{target}' in ~/.claude/CLAUDE.md")
else:
    print("~/.claude/CLAUDE.md not found")
```

Show both outputs to the user, then ask: **"Confirm removal of the `<TARGET>` gate? (yes/no)"**

Do not proceed unless the user types `yes`.

- Protected targets that require extra confirmation (ask twice): `context-mode`, `coder-ui-qa-test`
- After removal, remind user to restart Claude Code / Cowork.
