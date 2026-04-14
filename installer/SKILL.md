---
name: hard-gate-installer
description: "Install 7-location enforcement hard gates for plugins, skills, or shortcuts so Claude Code physically cannot ignore them. Use when: 'install a hard gate', 'enforce X', 'stop ignoring X', 'make X mandatory', 'gate X', 'hard gate on X'. Produces hook scripts, settings.json wiring, CLAUDE.md rules, session-start injections, and memory files — then runs behavioral tests to prove enforcement works."
---

# Hard Gate Installer

You are installing an enforcement gate across 7 locations so Claude Code **physically cannot ignore** a specific plugin, skill, or shortcut. This is not advisory. You produce real files with real exit codes that block real tool calls.

---

## CRITICAL: COWORK COMPATIBILITY

**User-level hooks (`~/.claude/settings.json` hooks block, `~/.claude/hooks/`) DO NOT FIRE in Cowork's Code tab.** This is a known platform limitation. Only **project-level** hooks fire in Cowork.

Therefore: ALL hook scripts and hook wiring MUST go in the **project directory**:
- Hook scripts → `.claude/hooks/` (project-level, NOT `~/.claude/hooks/`)
- Hook wiring → `.claude/settings.json` (project-level, NOT `~/.claude/settings.json`)
- Hook commands must use `"$CLAUDE_PROJECT_DIR"` for paths

Advisory artifacts (CLAUDE.md rules, permissions, memory files) can use user-level paths — those are text the model reads, not hooks the harness executes.

**If you put hooks in `~/.claude/`, they will silently fail in Cowork. Do not do this.**

---

## NON-NEGOTIABLE RULES FOR THIS SKILL

1. **No analysis without artifacts.** Every step produces a file or a config edit. If you are writing prose that does not end up in a file, stop.
2. **No "should I do this?" questions.** The user invoked this skill. The answer is yes. Do it.
3. **No partial installation.** All 7 locations get written. If any fails, fix it before moving on.
4. **No declaring done without a behavioral test.** The gate is not installed until you have tried the forbidden action and confirmed it was blocked.
5. **Back up before editing.** Before touching any existing file, copy it to `<filename>.bak-<timestamp>`. No exceptions.
6. **All hook scripts and wiring go in project-level `.claude/`, never user-level `~/.claude/`.** See COWORK COMPATIBILITY above.

---

## THE 7 ENFORCEMENT LOCATIONS

| # | Location | File path | Enforcement level |
|---|----------|-----------|-------------------|
| 1 | **Hook script** | `.claude/hooks/<target>-gate.sh` + `.py` (PROJECT-LEVEL) | Level 3 — blocks tool calls via exit 2 |
| 2 | **settings.json hook wiring** | `.claude/settings.json` (PROJECT-LEVEL hooks block) | Level 3 — activates the hook script |
| 3 | **settings.json permissions** | `~/.claude/settings.json` (USER-LEVEL permissions block) | Level 3 — ensures replacement tools callable |
| 4 | **Global CLAUDE.md** | `~/.claude/CLAUDE.md` | Level 1 — advisory, loaded every session |
| 5 | **Project CLAUDE.md** | `<repo>/CLAUDE.md` or `<repo>/.claude/CLAUDE.md` | Level 1 — advisory, project-scoped |
| 6 | **SessionStart hook** | `.claude/hooks/<target>-session-start.sh` + `.py` (PROJECT-LEVEL) + `.claude/settings.json` wiring | Level 2 — first-turn context injection |
| 7 | **Memory file** | `~/.claude/projects/<project>/memory/<target>-gate.md` | Level 2 — persistent per-turn reminder |

---

## PROTOCOL — EXECUTE THESE STEPS IN ORDER

### Step 0: Discover installed targets

Run these commands (use ctx_execute if context-mode is loaded, Bash if not):

```bash
echo "=== PLUGINS ==="
ls ~/.claude/plugins/marketplaces/ 2>/dev/null || echo "(none)"
cat ~/.claude/settings.json 2>/dev/null | grep -A1 enabledPlugins | head -20

echo "=== SKILLS ==="
ls ~/.claude/skills/ 2>/dev/null || echo "(none in ~/.claude/skills/)"

echo "=== SLASH COMMANDS ==="
ls ~/.claude/commands/ 2>/dev/null || echo "(none)"

echo "=== EXISTING PROJECT HOOKS ==="
cat .claude/settings.json 2>/dev/null | python3 -c "import json,sys; d=json.load(sys.stdin); [print(f'  {k}: {len(v)} entries') for k,v in d.get('hooks',{}).items()]" 2>/dev/null || echo "(none)"
```

Present results to the user as a numbered list. Ask: **"Which one do you want to gate?"**

If the user already named the target, skip this and proceed.

---

### Step 1: Classify the target

Read the target's files to determine its type:

- **Plugin** → has MCP tools (ctx_*, mcp__*, etc.). Evidence: appears in enabledPlugins, has a manifest or tool registration.
- **Skill** → has a SKILL.md with rules/protocols/deliverables. Evidence: directory in ~/.claude/skills/ or a session skills path.
- **Shortcut** → is a .md file in ~/.claude/commands/. Evidence: file exists at that path.

Tell the user in ONE sentence: "This is a [plugin/skill/shortcut]. Enforcement shape: [one-line summary]. Proceeding."

---

### Step 2: Extract parameters

Read the target's files (SKILL.md, README, manifest, command file). Extract:

**For plugins:**
- REPLACEMENT_TOOLS: What MCP tools does the plugin provide? List them.
- FORBIDDEN_PATTERNS: What native Bash commands do these tools replace? Build a regex.
- ALLOWED_PATTERNS: What Bash commands should still pass through? Build a regex.
- RULE_NUMBER: Next available Hard Rule number in CLAUDE.md.
- RULE_NAME: Short name for the rule (e.g., "Context-Mode Hard Gate").

**For skills:**
- REQUIRED_DELIVERABLES: What files/artifacts does the skill require before push/commit?
- REQUIRED_PROCESS: What process steps does the skill mandate? (for Stop hook and reminders)
- GATE_COMMANDS: What commands should be blocked until deliverables exist? (usually: git push, git commit, gh release)
- RULE_NUMBER: Next available Hard Rule number.
- RULE_NAME: Short name.

**For shortcuts:**
- TASK_DESCRIPTION: What task does this shortcut handle?
- MANUAL_PATTERN: What would doing it manually look like? (for SessionStart warning)
- RULE_NUMBER: Next available Hard Rule number.
- RULE_NAME: Short name.

Confirm with the user in 2-3 sentences what you found. Example: "I'll block [X] and require [Y]. [Z] will still work normally. Correct?"

Proceed on confirmation.

---

### Step 3: Back up existing files

Before ANY edits:

```bash
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
cp .claude/settings.json .claude/settings.json.bak-$TIMESTAMP 2>/dev/null || true
cp ~/.claude/settings.json ~/.claude/settings.json.bak-$TIMESTAMP 2>/dev/null || true
cp ~/.claude/CLAUDE.md ~/.claude/CLAUDE.md.bak-$TIMESTAMP 2>/dev/null || true
```

If a project CLAUDE.md exists, back that up too.

---

### Step 4: Write all 7 artifacts

Generate and write each artifact IN ORDER. Write each to disk immediately — do not batch, do not wait, do not describe what you plan to write.

**REMINDER: Hook scripts and hook wiring go in PROJECT-LEVEL `.claude/`, not user-level `~/.claude/`.**

---

#### ARTIFACT 1: Hook script (PROJECT-LEVEL)

Create `.claude/hooks/<target>-gate.py` (the logic) and `.claude/hooks/<target>-gate.sh` (thin wrapper) in the **project directory**. Make the .sh executable.

The .sh wrapper must use `$CLAUDE_PROJECT_DIR`:
```bash
#!/usr/bin/env bash
exec python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/<target>-gate.py"
```

**For PLUGIN targets**, the .py script must:
- Read JSON from stdin
- Check `tool_name` is "Bash" (exit 0 if not)
- Tokenize the command into sub-commands (split on ;, |, &&, ||)
- Strip leading env-var assignments and path prefixes from each verb
- Check if the verb matches the FORBIDDEN set
- If match: print `[HARD-RULE-{{RULE_NUMBER}}] BLOCKED by {{RULE_NAME}}` to stderr, exit 2
- If no match: exit 0 silently
- Fail-open: if JSON parsing fails, exit 0

**For SKILL targets**, the .py script must:
- Read JSON from stdin
- Check if the command matches GATE_COMMANDS (git push, git commit, gh release, etc.)
- If match: check for required deliverables relative to `CLAUDE_PROJECT_DIR`
- If any missing: print blocked message listing missing items to stderr, exit 2
- If all present: exit 0

**For SHORTCUT targets**: exit 0 with a reminder on stderr (nag only, not blocking).

After writing both files: `chmod +x .claude/hooks/<target>-gate.sh`

**Unit test immediately after writing:**
```bash
python3 .claude/hooks/<target>-gate.py <<< '{"tool_name":"Bash","tool_input":{"command":"<FORBIDDEN_COMMAND>"}}' 2>&1 ; echo "EXIT: $?"
```
Must return EXIT: 2 with the HARD-RULE marker. If not, fix before proceeding.

---

#### ARTIFACT 2: settings.json hook wiring (PROJECT-LEVEL)

Read the current `.claude/settings.json` (PROJECT-LEVEL). Add the PreToolUse hook entry to the `hooks` block. If no `hooks` block exists, create one.

**All hook commands MUST use `$CLAUDE_PROJECT_DIR` paths:**

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [{
          "type": "command",
          "command": "\"$CLAUDE_PROJECT_DIR/.claude/hooks/<target>-gate.sh\""
        }]
      }
    ]
  }
}
```

For SKILL targets, also add a Stop hook:
```json
"Stop": [{
  "hooks": [{
    "type": "command",
    "command": "\"$CLAUDE_PROJECT_DIR/.claude/hooks/<target>-stop-check.sh\""
  }]
}]
```

IMPORTANT: Do NOT overwrite existing entries (like permissions). MERGE the hooks block into the existing file. Use `python3` for safe JSON manipulation.

---

#### ARTIFACT 3: settings.json permissions (USER-LEVEL)

**For PLUGIN targets only:** Add the plugin's MCP tool permissions to `~/.claude/settings.json` `permissions.allow` if not already present. This stays at user level because permissions load from user settings even in Cowork.

**For SKILL and SHORTCUT targets:** Usually no permission changes needed.

---

#### ARTIFACT 4: Global CLAUDE.md rule

Read `~/.claude/CLAUDE.md`. Find the last numbered Hard Rule. Add the next one.

**Template for all target types:**

```markdown
### Hard Rule {{RULE_NUMBER}} — {{RULE_NAME}}

**This rule is non-negotiable. Do not skip it. Do not work around it.**

{{RULE_BODY}}

**REFUSAL TEMPLATE — use this exact language when tempted to skip:**
"I need to use {{TARGET_NAME}} for this operation. {{REFUSAL_REASON}}"

**IF {{TARGET_NAME}} IS UNAVAILABLE:**
State clearly: "{{TARGET_NAME}} is not responding. I cannot proceed with {{GATED_OPERATIONS}} until it is restored." Do NOT fall back to the ungated path.
```

---

#### ARTIFACT 5: Project CLAUDE.md rule

If the user is in a project directory, add the same rule to the project-level CLAUDE.md. If no project CLAUDE.md exists, create one with just this rule.

---

#### ARTIFACT 6: SessionStart hook (PROJECT-LEVEL)

Create `.claude/hooks/<target>-session-start.py` and `.claude/hooks/<target>-session-start.sh` in the **project directory**.

The .py script emits top-level `{"additionalContext": "..."}` JSON on stdout. Exit 0.

The .sh wrapper:
```bash
#!/usr/bin/env bash
exec python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/<target>-session-start.py"
```

Make executable. Add to `.claude/settings.json` (PROJECT-LEVEL) under `SessionStart`:
```json
"SessionStart": [{
  "hooks": [{
    "type": "command",
    "command": "\"$CLAUDE_PROJECT_DIR/.claude/hooks/<target>-session-start.sh\""
  }]
}]
```

---

#### ARTIFACT 7: Memory file

Find the current project's memory directory:
```bash
ls -d ~/.claude/projects/*/memory/ 2>/dev/null | head -5
```

Create `~/.claude/projects/<project>/memory/<target>-gate.md` with a summary of the gate.

---

### Step 5: Verify all 7 artifacts exist

Run a single verification pass:

```bash
echo "=== ARTIFACT CHECK ==="
echo "1. Hook script:      " && ls -la .claude/hooks/{{TARGET}}-gate.sh .claude/hooks/{{TARGET}}-gate.py
echo "2. Project settings: " && python3 -c "import json; d=json.load(open('.claude/settings.json')); print('hooks:', list(d.get('hooks',{}).keys()))"
echo "3. User permissions: " && python3 -c "import json; d=json.load(open('$HOME/.claude/settings.json')); print('permissions:', len(d.get('permissions',{}).get('allow',[])),'allow entries')"
echo "4. Global CLAUDE.md: " && grep -c "Hard Rule {{RULE_NUMBER}}" ~/.claude/CLAUDE.md
echo "5. Project CLAUDE.md:" && grep -c "Hard Rule {{RULE_NUMBER}}" ./CLAUDE.md 2>/dev/null || echo "(no project CLAUDE.md)"
echo "6. SessionStart:     " && ls -la .claude/hooks/{{TARGET}}-session-start.sh
echo "7. Memory file:      " && ls ~/.claude/projects/*/memory/{{TARGET}}-gate.md 2>/dev/null || echo "(memory file location TBD)"
```

If ANY artifact is missing, fix it before proceeding. Do not skip.

---

### Step 6: Behavioral test — MANDATORY

**You MUST restart the session before testing.** Hooks load at session start. A new session has no memory of this installation, so you cannot just say "run behavioral tests" — CC won't know what you mean.

**Generate a paste-ready test prompt.** Build it from this template, filling in the actual commands for the target(s) you just gated. Give it to the user with this message:

"Gate installed. Restart the Code tab now, then paste this into the new session:"

```
Test the hardgate hooks installed in this project. Run these commands
via Bash and report what happens for each:

1. [FORBIDDEN_COMMAND_1] — should be BLOCKED by HARD-RULE-[N]
2. [FORBIDDEN_COMMAND_2 if multiple gates] — should be BLOCKED by HARD-RULE-[N]
3. [ALLOWED_COMMAND] — should execute normally, no HARD-RULE marker
4. [FALSE_POSITIVE_COMMAND] — should execute normally (no over-match)

Report a table: Test | Expected | Actual | Pass/Fail
Do not fix anything if a test fails. Just report.
```

**Fill in real commands based on the target type:**

For a context-mode plugin gate:
- Forbidden: `cat /etc/hosts`
- Allowed: `git add .`
- False positive: `mkdir /tmp/cat-pics-test`

For a deliverables skill gate:
- Forbidden: `git push origin main`
- Allowed: `git status`
- False positive: `echo "push notification sent"`

For a superpowers plan gate:
- Forbidden: `git commit -m "test"`
- Allowed: `git status`
- False positive: `echo "commit message ready"`

**After the user reports back:**

If all tests pass → proceed to Step 7.
If any test fails → diagnose and fix, re-test. Do not declare done.

---

### Step 7: Completion report

After all tests pass, produce this summary:

```
HARD GATE INSTALLED: {{TARGET_NAME}}
Rule: Hard Rule {{RULE_NUMBER}} — {{RULE_NAME}}
Type: [plugin/skill/shortcut]

Artifacts written (PROJECT-LEVEL hooks — Cowork compatible):
  1. ✅ .claude/hooks/{{TARGET}}-gate.sh + .py
  2. ✅ .claude/settings.json (PreToolUse hook added)
  3. ✅ ~/.claude/settings.json (permissions updated)  [or N/A]
  4. ✅ ~/.claude/CLAUDE.md (Hard Rule {{RULE_NUMBER}})
  5. ✅ <project>/CLAUDE.md (Hard Rule {{RULE_NUMBER}})
  6. ✅ .claude/hooks/{{TARGET}}-session-start.sh + .py
  7. ✅ ~/.claude/projects/.../memory/{{TARGET}}-gate.md

Behavioral tests:
  Positive (forbidden blocked): PASS — [details]
  Negative (allowed works):     PASS — [details]
  False-positive (no over-match): PASS — [details]

ACTIVATION: Restart Claude Code / Cowork to load the new hooks.
To remove this gate later: /disable-gate {{TARGET}}
```

---

## WHAT THIS SKILL DOES NOT DO

- It does not design systems. It installs gates.
- It does not ask "should I also do X?" It does the 7 artifacts and tests them.
- It does not produce architecture documents, taxonomies, or analyses.
- It does not offer to defer to another session or task.

If you find yourself writing more than 2 sentences of analysis at any point, you have gone off track. Write a file instead.
