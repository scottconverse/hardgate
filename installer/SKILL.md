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

> **(U4) Bootstrap-conflict warning.** If you are installing a gate on the **context-mode** plugin (or any other tool that intercepts Bash) AND that tool is already running as a hard gate in this session, the installer's own discovery commands will be blocked by the existing gate. The cleanest path is to **run the installer in a fresh session where the target gate is not yet active**. The `ctx_execute` workaround below handles soft/advisory installs but is fragile against a fully-active blocking gate.

Run these commands (use ctx_execute if context-mode is loaded, Bash if not):

```bash
echo "=== PLUGINS ==="
# (B3) Walk ~/.claude/plugins/ directly — the old `marketplaces/` subpath
# only catches Cowork-marketplace installs and misses CLI/manual installs.
ls ~/.claude/plugins/ 2>/dev/null || echo "(none)"
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

**Deriving RULE_NUMBER:**

Run this before writing any artifacts to get the next available Hard Rule number:

```python
import re, pathlib
text = pathlib.Path('~/.claude/CLAUDE.md').expanduser().read_text(encoding='utf-8', errors='replace')
nums = [int(n) for n in re.findall(r'Hard Rule (\d+)', text)]
rule_number = max(nums) + 1 if nums else 1
print(f"Next Hard Rule number: {rule_number}")
```

If the file is empty or has no Hard Rules, start at 1. Use the printed number as `{{RULE_NUMBER}}` throughout all artifacts.

**Custom deliverables? (X2 — for SKILL targets that gate `git push` only):** Ask the user:

> "Does this project's deliverable structure match the standard hardgate pattern (UML diagram, README in 4 formats, USER-MANUAL in 3 formats, docs/index.html, Discussions seed)? If not, I'll write a `.claude/deliverables.json` tailored to your project structure."

If the user says **no** (or describes a different structure):
- Write `.claude/deliverables.json` using this schema:
  ```json
  {
    "version": 1,
    "required": [
      { "name": "Description", "glob": "alt1|alt2|alt3", "optional": false }
    ]
  }
  ```
- `glob` is a `|`-delimited alternates string — split on `|`, each fed to `glob.glob(recursive=True)`, first file match wins.
- `"optional": true` → WARN on stderr, does not block.
- Malformed config fails closed — gate exits 2 and refuses to push until fixed or deleted.

If the user says **yes**, skip this step — hardcoded checks apply when `.claude/deliverables.json` is absent.

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

After creating backups, prune old ones — keep the 3 most recent per base file:

```bash
for base in ".claude/settings.json" "$HOME/.claude/settings.json" "$HOME/.claude/CLAUDE.md" "./CLAUDE.md"; do
  mapfile -t old < <(ls -t "${base}.bak-"* 2>/dev/null | tail -n +4)
  [ ${#old[@]} -gt 0 ] && rm -f "${old[@]}"
done
```

---

### Step 4: Write all 7 artifacts

Generate and write each artifact IN ORDER. Write each to disk immediately — do not batch, do not wait, do not describe what you plan to write.

**REMINDER: Hook scripts and hook wiring go in PROJECT-LEVEL `.claude/`, not user-level `~/.claude/`.**

---

#### ARTIFACT 1: Hook script (PROJECT-LEVEL)

Create `.claude/hooks/<target>-gate.py` (the logic) and `.claude/hooks/<target>-gate.sh` (thin wrapper) in the **project directory**. Make the .sh executable.

The .sh wrapper must use `$CLAUDE_PROJECT_DIR`. **(B7)** Quote the variable alone, not the whole path — this matches Anthropic's documented hook examples:
```bash
#!/usr/bin/env bash
exec python3 "$CLAUDE_PROJECT_DIR"/.claude/hooks/<target>-gate.py
```

**For PLUGIN targets**, the .py script must:
- Read JSON from stdin
- Check `tool_name` is "Bash" (exit 0 if not)
- Tokenize the command into sub-commands (split on ;, |, &&, ||)
- Strip leading env-var assignments, sudo/env/command/exec/time/nohup wrappers, and path prefixes from each verb
- Check if the verb matches the FORBIDDEN set
- **(D2) Detect shell-c bypass:** if the verb is `sh|bash|zsh|dash|ash|ksh` and the next token is `-c`, recursively re-tokenize the `-c` argument using `shlex.split()` and apply the same forbidden-verb check. Cap recursion at depth 2. **Fail-closed** on unparseable `-c` arguments — block the call rather than letting it through.
- **(D2) Detect interpreter inline-code bypass:** if the verb is `python|python2|python3|perl|ruby|node|deno|php` and the args contain the inline-code flag (`-c` for python/php, `-e`/`--eval` for perl/ruby/node, `eval` for deno), block outright. There is no reliable way to statically analyze arbitrary inline code, so the only safe action is refuse.
- If match: print `[HARD-RULE-{{RULE_NUMBER}}] BLOCKED by {{RULE_NAME}}` to stderr, exit 2
- If no match: exit 0 silently
- Fail-open on outer JSON parsing errors: if `sys.stdin` cannot be parsed at all, exit 0. Fail-closed only applies to the inner `-c` argument re-parsing.

Reference tokenizer constants:

```python
SHELL_INTERPRETERS = {"sh", "bash", "zsh", "dash", "ash", "ksh"}
SCRIPT_INTERPRETERS = {
    "python":  ("-c",),
    "python2": ("-c",),
    "python3": ("-c",),
    "perl":    ("-e",),
    "ruby":    ("-e",),
    "node":    ("-e", "--eval"),
    "deno":    ("eval",),
    "php":     ("-r",),
}
MAX_SHELL_C_DEPTH = 2
```

**For SKILL targets**, the .py script must:
- Read JSON from stdin
- Check if the command matches GATE_COMMANDS (git push, git commit, gh release, etc.)
- **(X1) Resolve the project root from the git repo the user is actually pushing from**, NOT from `$CLAUDE_PROJECT_DIR` directly. The session's `$CLAUDE_PROJECT_DIR` is fixed at session start and points at the Cowork session root, not the sub-project being pushed. Use this resolution order:
  1. Parse a leading `cd <path> && ...` from the command string. Handles double-quoted, single-quoted, and bareword paths. This is the most common pattern Claude Code uses to navigate into a sub-project before running git.
  2. Use `tool_input.cwd` if a test harness or wrapper provides it (the real Bash tool payload does NOT include this field, but tests may inject it).
  3. Fall back to `os.getcwd()` of the hook process — which equals the session's project dir.
  4. From whichever cwd was chosen, run `git rev-parse --show-toplevel` to find the actual repo root.
  5. If not in a git repo, fall back to `$CLAUDE_PROJECT_DIR`, then `os.getcwd()`.
- If match: check for required deliverables relative to the resolved project root
- If any missing: print blocked message listing missing items AND the resolved project root to stderr, exit 2
- If all present: exit 0

Reference implementation:

```python
import os, re, subprocess

# Parse a leading `cd <path> && ...` from the command string.
# Handles "double quoted", 'single quoted', and bareword paths.
_LEADING_CD = re.compile(
    r'^\s*cd\s+(?:--\s+)?(?:"([^"]+)"|\'([^\']+)\'|(\S+))\s*(?:&&|;|$)'
)

def detect_cwd_from_payload(payload):
    ti = payload.get("tool_input") or {}
    if ti.get("cwd"):
        return ti["cwd"]
    cmd = ti.get("command") or ""
    m = _LEADING_CD.match(cmd)
    if m:
        path = m.group(1) or m.group(2) or m.group(3)
        path = os.path.expandvars(os.path.expanduser(path))
        if os.path.isdir(path):
            return path
    return os.getcwd()

def find_project_root(payload):
    cwd = detect_cwd_from_payload(payload)
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=cwd, capture_output=True, text=True, timeout=5,
        )
        if r.returncode == 0:
            top = r.stdout.strip()
            if top and os.path.isdir(top):
                return top
    except Exception:
        pass
    return os.environ.get("CLAUDE_PROJECT_DIR") or cwd or "."


def check_override_marker(rule_num: int) -> None:
    """Time-limited single-use override marker check (X4).

    The model creates .claude/hardgate-override-rule-N with str(time.time())
    as content when the human types 'override rule N'. Valid markers (<60s)
    grant a one-time bypass. Stale or corrupt markers are deleted silently.
    """
    marker = (
        pathlib.Path(os.environ.get("CLAUDE_PROJECT_DIR", "."))
        / ".claude"
        / f"hardgate-override-rule-{rule_num}"
    )
    if not marker.exists():
        return
    try:
        age = time.time() - float(marker.read_text().strip())
        marker.unlink()
        if age < 60:
            sys.stderr.write(
                f"[HARD-RULE-{rule_num}] Override marker valid (age={age:.1f}s < 60s). "
                f"One-time bypass granted.\n"
            )
            sys.exit(0)
        sys.stderr.write(
            f"[HARD-RULE-{rule_num}] Override marker EXPIRED (age={age:.1f}s >= 60s). "
            f"Marker deleted. Type 'override rule {rule_num}' again to re-arm.\n"
        )
    except Exception:
        try:
            marker.unlink()
        except Exception:
            pass
```

In `main()`, call `check_override_marker({{RULE_NUMBER}})` immediately after the Bash-only guard and before command parsing:

```python
    if payload.get("tool_name") != "Bash":
        sys.exit(0)

    check_override_marker({{RULE_NUMBER}})   # X4: time-limited override bypass

    cmd = ...  # rest of your command extraction
```

Add `import pathlib, time` to the imports block.

**Override UX protocol (X4):** When the human types "override rule {{RULE_NUMBER}}":
1. Write `str(time.time())` to `.claude/hardgate-override-rule-{{RULE_NUMBER}}` in the project's `.claude/` directory.
2. Immediately say: "Override armed. Marker expires in 60 seconds — issuing the gated command now."
3. Execute the gated command as the **very next tool call** — no other tool calls in between.
4. If any other tool call occurs before the gated command (analysis, file reads, etc.), re-warn the user and ask for a fresh "override rule {{RULE_NUMBER}}". The marker will likely have expired.

Document this in the Hard Rule block (Artifact 4) so the model knows the protocol in future sessions.

**For SHORTCUT targets**: exit 0 with a reminder on stderr (nag only, not blocking).

After writing both files: `chmod +x .claude/hooks/<target>-gate.sh`

**Unit test immediately after writing** (assert exit code, do not just echo it):
```bash
HG_TEST_OUTPUT=$(python3 .claude/hooks/<target>-gate.py <<< '{"tool_name":"Bash","tool_input":{"command":"<FORBIDDEN_COMMAND>"}}' 2>&1)
HG_TEST_EXIT=$?
[ "$HG_TEST_EXIT" = "2" ] || { echo "GATE UNIT TEST FAILED (exit=$HG_TEST_EXIT) — install cannot proceed"; echo "$HG_TEST_OUTPUT"; exit 1; }
echo "UNIT TEST PASSED: $HG_TEST_OUTPUT"
```
Must return EXIT: 2 with the HARD-RULE marker. If not, fix before proceeding.

**Save for Step 7:** Note the exact content of `$HG_TEST_OUTPUT` and `$HG_TEST_EXIT`. Step 7 will write both verbatim to `.claude/hardgate-install-log.md` and display them in the completion report.

---

#### ARTIFACT 1.5: Stop-check hook (SKILL targets only)

**(B1) For SKILL targets, also create `.claude/hooks/<target>-stop-check.sh` and `.claude/hooks/<target>-stop-check.py`.** This is the script the Stop hook in Artifact 2 wires up. Without this artifact, the Stop hook entry points at a non-existent file and silently fails — the deliverable check at end-of-turn never runs.

The .sh wrapper:
```bash
#!/usr/bin/env bash
exec python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/<target>-stop-check.py"
```

The .py script must:
- Read JSON from stdin (Stop hook payload contains `last_assistant_message` and `stop_hook_active`)
- If `stop_hook_active` is true, exit 0 immediately (prevents infinite loops where the stop-check itself triggers another Stop event)
- Inspect `last_assistant_message` for push/release/publish intent signals (e.g., regex on `git\s+push|gh\s+release\s+create|npm\s+publish|python3?\s+-m\s+build`)
- If no intent detected, exit 0
- If intent detected, resolve the project root using the **same X1 git-root logic from Artifact 1** (do not use `$CLAUDE_PROJECT_DIR` directly)
- Verify the same deliverables that Artifact 1's PreToolUse gate verifies
- If any are missing, output `{"decision": "block", "reason": "Hard Rule {{RULE_NUMBER}}: missing deliverables: <list>"}` on stdout and exit 0 (Stop hooks block via JSON `decision`, not exit code)
- If all deliverables present, exit 0

After writing both files: `chmod +x .claude/hooks/<target>-stop-check.sh`

**Unit test the stop-check too:**
```bash
RESULT=$(python3 .claude/hooks/<target>-stop-check.py <<< '{"stop_hook_active":false,"last_assistant_message":"now i will git push origin main"}' 2>&1)
EXIT=$?
[ "$EXIT" = "0" ] || { echo "STOP-CHECK UNIT TEST FAILED (exit=$EXIT) — install cannot proceed"; echo "$RESULT"; exit 1; }
echo "STOP-CHECK UNIT TEST PASSED: $RESULT"
```

The stop-check should produce a `{"decision":"block",...}` JSON message on stdout if deliverables are missing. Visually confirm the output contains either `block` (deliverables missing) or is empty (deliverables satisfied).

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
          "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/<target>-gate.sh",
          "if": "<JS regex — see below>"
        }]
      }
    ]
  }
}
```

**(B7)** Quote the variable alone, not the whole path. Both forms are functionally equivalent in POSIX shells, but variable-only quoting matches Anthropic's documented hook examples and is the convention to follow.

**(D1) `if` field — pre-filter hook launches:** The `if` value is a JavaScript expression evaluated against the tool payload. When it is falsy, the hook script is never launched — avoids a Python process spawn for every `git add`, `mkdir`, etc. Build the regex from the FORBIDDEN or GATED list:

**For PLUGIN targets** (e.g., context-mode — blocks forbidden read verbs):
```json
"if": "tool_input.command && /\\bcat\\b|\\bhead\\b|\\btail\\b|\\bgrep\\b|\\brg\\b|\\bfind\\b|git\\s+(log|diff|show|blame)|\\bpytest\\b|\\bjest\\b|npm\\s+test|docker.*(logs|compose)|\\bjournalctl\\b|\\bdmesg\\b|\\bls\\b.*-[la]/.test(tool_input.command)"
```

**For SKILL targets** (e.g., coder-ui-qa-test — blocks push/release until deliverables exist):
```json
"if": "tool_input.command && /git\\s+push|gh\\s+release\\s+create|npm\\s+publish|python3?\\s+-m\\s+build/.test(tool_input.command)"
```

The regex should be a union of every verb pattern the Python gate checks. When in doubt, be permissive — a false negative (gate runs unnecessarily) is safe; a false positive (gate silently skipped for a forbidden command) is a security hole.

For SKILL targets, also add a Stop hook (same B7 quoting style):
```json
"Stop": [{
  "hooks": [{
    "type": "command",
    "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/<target>-stop-check.sh"
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

The .sh wrapper (same B7 quoting style):
```bash
#!/usr/bin/env bash
exec python3 "$CLAUDE_PROJECT_DIR"/.claude/hooks/<target>-session-start.py
```

Make executable. Add to `.claude/settings.json` (PROJECT-LEVEL) under `SessionStart`:
```json
"SessionStart": [{
  "hooks": [{
    "type": "command",
    "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/<target>-session-start.sh"
  }]
}]
```

---

#### ARTIFACT 7: Memory file

Derive the memory directory path deterministically from `$CLAUDE_PROJECT_DIR`. Claude Code encodes the project path by replacing each `:`, `/`, and `\` with a single `-`.

```python
import os, re, pathlib
project_dir = os.environ.get('CLAUDE_PROJECT_DIR', '')
encoded = re.sub(r'[:/\\]', '-', project_dir)
memory_dir = pathlib.Path.home() / '.claude' / 'projects' / encoded / 'memory'
memory_dir.mkdir(parents=True, exist_ok=True)
print(memory_dir)
```

Or in Bash (if Python is unavailable):
```bash
encoded=$(python3 -c "import os,re; p=os.environ.get('CLAUDE_PROJECT_DIR',''); print(re.sub(r'[:/\\\\]','-',p))")
memory_dir="$HOME/.claude/projects/${encoded}/memory"
mkdir -p "$memory_dir"
```

Create `${memory_dir}/{{TARGET}}-gate.md` with a summary of the gate.

---

### Step 5: Verify all 7 artifacts exist

Run a single verification pass:

```bash
echo "=== ARTIFACT CHECK ==="

# Derive memory dir deterministically (B4)
ENCODED=$(python3 -c "import os,re; p=os.environ.get('CLAUDE_PROJECT_DIR',''); print(re.sub(r'[:/\\\\]','-',p))")
MEMORY_DIR="$HOME/.claude/projects/${ENCODED}/memory"

echo "1.  Hook script:      " && ls -la .claude/hooks/{{TARGET}}-gate.sh .claude/hooks/{{TARGET}}-gate.py || { echo "ARTIFACT 1 MISSING — gate .sh and .py not found"; exit 1; }

# B1: stop-check is required for SKILL targets only — skip for plugin/shortcut.
if [ "{{TARGET_TYPE}}" = "skill" ]; then
  echo "1.5 Stop-check:       " && ls -la .claude/hooks/{{TARGET}}-stop-check.sh .claude/hooks/{{TARGET}}-stop-check.py || { echo "ARTIFACT 1.5 MISSING — stop-check scripts not found"; exit 1; }
fi

echo "2.  Project settings: " && python3 -c "import json; d=json.load(open('.claude/settings.json')); print('hooks:', list(d.get('hooks',{}).keys()))" || { echo "ARTIFACT 2 MISSING — .claude/settings.json not found or malformed"; exit 1; }

echo "3.  User permissions: " && python3 -c "import json,pathlib; d=json.loads(pathlib.Path.home().joinpath('.claude/settings.json').read_text()); print('permissions:', len(d.get('permissions',{}).get('allow',[])),'allow entries')" || { echo "ARTIFACT 3 MISSING — ~/.claude/settings.json not found or malformed"; exit 1; }

# D5: derive count and assert exactly 1 occurrence (missing = 0, collision = >1)
count4=$(grep -c "Hard Rule {{RULE_NUMBER}}" ~/.claude/CLAUDE.md 2>/dev/null || echo 0)
[ "$count4" -ge 1 ] || { echo "ARTIFACT 4 MISSING — Hard Rule {{RULE_NUMBER}} not found in ~/.claude/CLAUDE.md"; exit 1; }
[ "$count4" -eq 1 ] || { echo "ARTIFACT 4 COLLISION: found ${count4} occurrences of 'Hard Rule {{RULE_NUMBER}}' in ~/.claude/CLAUDE.md — expected exactly 1"; exit 1; }
echo "4.  Global CLAUDE.md: Hard Rule {{RULE_NUMBER}} present (${count4} occurrence)"

# Artifact 5 is intentionally soft: user may not be in a project directory
echo "5.  Project CLAUDE.md:" && grep -c "Hard Rule {{RULE_NUMBER}}" ./CLAUDE.md 2>/dev/null || echo "(no project CLAUDE.md — OK if not in a project dir)"

echo "6.  SessionStart:     " && ls -la .claude/hooks/{{TARGET}}-session-start.sh .claude/hooks/{{TARGET}}-session-start.py || { echo "ARTIFACT 6 MISSING — session-start scripts not found"; exit 1; }

echo "7.  Memory file:      " && ls "${MEMORY_DIR}/{{TARGET}}-gate.md" || { echo "ARTIFACT 7 MISSING — ${MEMORY_DIR}/{{TARGET}}-gate.md not found"; exit 1; }

echo "=== ALL ARTIFACTS VERIFIED ==="
```

If ANY artifact is missing, fix it before proceeding. Do not skip.

---

### Step 6: Behavioral test — MANDATORY

**You MUST restart the session before testing.** Hooks load at session start. A new session has no memory of this installation, so you cannot just say "run behavioral tests" — CC won't know what you mean.

**Generate a paste-ready test prompt** and **(U1) write it to disk** so the user can find it after the restart wipes the previous session's transcript from view. The file goes at `.claude/hardgate-test-prompt.txt`, project-level.

Build the prompt from this template, filling in the actual commands for the target(s) you just gated:

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

Write the filled-in prompt to `.claude/hardgate-test-prompt.txt`, then tell the user:

> Gate installed. Test prompt saved to `.claude/hardgate-test-prompt.txt`.
>
> 1. Restart the Code tab.
> 2. Open `.claude/hardgate-test-prompt.txt` in the new session.
> 3. Paste its contents into the new session as a message to me.
> 4. I'll run the tests and report a pass/fail table.

**Fill in real commands based on the target type:**

For a context-mode plugin gate:
- Forbidden: `cat README.md` — uses a file guaranteed to exist in any project, no system-file restrictions
- Allowed: `git add .`
- False positive: `TMP=$(mktemp -d) && mkdir "$TMP/cat-shaped-dir" && rm -rf "$TMP"` — exercises the `mkdir <path-containing-cat>` over-match path, then self-cleans. Avoids leaving an unowned `/tmp/cat-pics-test` directory behind

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

Also append this report to `.claude/hardgate-install-log.md` (create if it doesn't exist):

```python
import datetime, pathlib

log_path = pathlib.Path('.claude/hardgate-install-log.md')
timestamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

# HG_TEST_EXIT and HG_TEST_OUTPUT captured from Artifact 1 unit test
entry = f"""
## [{timestamp}] HARD GATE INSTALLED: {{TARGET_NAME}}

**Rule:** Hard Rule {{RULE_NUMBER}} — {{RULE_NAME}}
**Type:** [plugin/skill/shortcut]

### Artifacts written
1. .claude/hooks/{{TARGET}}-gate.sh + .py
2. .claude/settings.json (PreToolUse hook added)
3. ~/.claude/settings.json (permissions updated)
4. ~/.claude/CLAUDE.md (Hard Rule {{RULE_NUMBER}})
5. <project>/CLAUDE.md (Hard Rule {{RULE_NUMBER}})
6. .claude/hooks/{{TARGET}}-session-start.sh + .py
7. ~/.claude/projects/.../memory/{{TARGET}}-gate.md

### Unit test result (D4)
Exit code: {HG_TEST_EXIT}
Output:
{HG_TEST_OUTPUT}
"""

with log_path.open('a', encoding='utf-8') as f:
    f.write(entry)
print(f"Install log updated: {log_path}")
```

Replace `{HG_TEST_EXIT}` and `{HG_TEST_OUTPUT}` with the actual values captured in Artifact 1. Display the unit test output verbatim in the completion report shown to the user.

---

## WHAT THIS SKILL DOES NOT DO

- It does not design systems. It installs gates.
- It does not ask "should I also do X?" It does the 7 artifacts and tests them.
- It does not produce architecture documents, taxonomies, or analyses.
- It does not offer to defer to another session or task.

If you find yourself writing more than 2 sentences of analysis at any point, you have gone off track. Write a file instead.
