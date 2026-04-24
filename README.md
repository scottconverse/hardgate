# Hardgate

**Make Claude Code actually follow the rules.**

Hardgate installs 7-layer enforcement on any plugin, skill, or slash command in Claude Code so it physically cannot be ignored. Not advisory. Not "please remember to do this." A real `exit 2` that blocks the tool call before it executes.

Built for **Cowork** (Claude Desktop's Code tab). Also works in Claude Code CLI.

---

## The Problem

Claude Code ignores rules. You write a skill that says "always use context-mode tools instead of raw Bash." You put it in CLAUDE.md. You add it as a Hard Rule. Claude Code follows it for a while, then quietly stops — especially in long sessions when the rule scrolls out of attention, or when it's rushing to finish.

Skills, CLAUDE.md rules, and slash commands are all **advisory**. The model reads them and *chooses* to comply. Under pressure, it chooses not to.

Hardgate makes compliance non-optional by installing enforcement at 7 different locations, including a **PreToolUse hook** that intercepts the forbidden action and returns `exit 2` — which physically prevents the tool call from executing. The model doesn't get to choose. The harness blocks it.

---

## What It Does

When you run `/hard-gate`, it:

1. Discovers your installed plugins, skills, and slash commands
2. Asks which one you want to enforce
3. Classifies the target (plugin, skill, or shortcut)
4. Extracts the enforcement parameters automatically
5. Writes **7 artifacts** across 3 enforcement levels
6. Runs a behavioral test to prove it works
7. Reports results

The 7 artifacts, by enforcement level:

| Level | What | Where | Purpose |
|-------|------|-------|---------|
| **3 — Blocking** | Hook script (.sh + .py) | `.claude/hooks/` | Intercepts forbidden tool calls, exits 2 to block |
| **3 — Blocking** | settings.json hook wiring | `.claude/settings.json` | Tells Claude Code to run the hook on matching events |
| **3 — Blocking** | Permissions | `~/.claude/settings.json` | Ensures replacement tools are allowed |
| **2 — Reminder** | SessionStart hook | `.claude/hooks/` | Announces the gate is active at the start of every session |
| **2 — Reminder** | Memory file | `~/.claude/projects/.../memory/` | Per-turn reminder that survives context compaction |
| **1 — Advisory** | Global CLAUDE.md rule | `~/.claude/CLAUDE.md` | Gives the model refusal language and protocol text |
| **1 — Advisory** | Project CLAUDE.md rule | `<project>/CLAUDE.md` | Same, scoped to the project |

Level 3 is the one that matters. The model cannot bypass a hook that returns `exit 2`. Levels 1 and 2 exist so the model knows *why* it's being blocked and *what to do instead* — without those, it would just keep retrying the blocked action.

---

## Canonical templates

For commonly-used gates, hardgate ships reference implementations under `templates/` that can be copied directly into a project's `.claude/hooks/` — skipping the full `/hard-gate` installer flow when you just want a known-good gate.

- **[`templates/commit-size-gate/`](templates/commit-size-gate/)** — reference implementation for Rule 11 (Commit-Size Acknowledgment Gate). Blocks `git commit` when the staged diff exceeds `THRESHOLD` (default 800 lines) and the message lacks one of the allowed bracketed tag tokens; 60-second `override rule 11` one-shot pressure valve. See [`templates/commit-size-gate/README.md`](templates/commit-size-gate/README.md) for install steps, settings.json wiring, and the verification recipe.

Each template is byte-identical to a validated production deployment and covered by its own pytest smoke test under `tests/`.

---

## Requirements

- **Claude Desktop** with Cowork enabled (Windows or Mac), or **Claude Code CLI**
- A Claude Pro, Max, Team, or Enterprise plan
- Python 3 on PATH (for the gate scripts)
- The target you want to enforce must already be installed (plugin enabled, skill in `~/.claude/skills/`, etc.)

---

## Install

Download the latest release zip and run the installer for your platform:

**macOS / Linux:**
```bash
curl -L https://github.com/scottconverse/hardgate/releases/latest/download/hardgate-v1.1.0.zip -o hardgate.zip
unzip hardgate.zip -d hardgate
cd hardgate
bash install.sh
```

**Windows (PowerShell):**
```powershell
Invoke-WebRequest -Uri "https://github.com/scottconverse/hardgate/releases/latest/download/hardgate-v1.1.0.zip" -OutFile hardgate.zip
Expand-Archive hardgate.zip -DestinationPath hardgate
pwsh -File hardgate\install.ps1
```

The installer copies SKILL.md and the two slash commands to `~/.claude/` automatically.

### After install

Restart the Code tab (or Claude Code CLI), then type `/hard-gate`. You should see a discovery list of your installed plugins, skills, and commands, followed by "Which one do you want to gate?"

<details>
<summary>Manual install (alternative)</summary>

Place these three files from this repo:

| File | Destination |
|------|-------------|
| `SKILL.md` | `~/.claude/skills/hard-gate-installer/SKILL.md` |
| `hard-gate.md` | `~/.claude/commands/hard-gate.md` |
| `disable-gate.md` | `~/.claude/commands/disable-gate.md` |

```bash
mkdir -p ~/.claude/skills/hard-gate-installer
mkdir -p ~/.claude/commands
```

Then create each file with the contents from this repo.

</details>

---

## Usage

### Install a gate

```
/hard-gate
```

No arguments: discovers targets and asks you to pick.

```
/hard-gate context-mode
```

With argument: skips discovery, gates the named target immediately.

The installer will:
- Classify the target (plugin → blocks Bash commands; skill → blocks git push until deliverables exist; shortcut → nag-only reminder)
- Ask you to confirm the enforcement plan in 2-3 sentences
- Write all 7 artifacts
- Give you a **paste-ready test prompt** to verify the gate works

### After install: verify the gate

The installer finishes by giving you a test prompt to copy. The flow is:

1. The installer writes all artifacts and says "Restart the Code tab now, then paste this:"
2. You restart the Code tab
3. You paste the test prompt into the new session
4. CC runs the test commands (tries the forbidden action, tries an allowed action, tries a false-positive edge case)
5. CC reports a pass/fail table

**Why you need to paste a prompt:** A new session has no memory of the installation. CC won't know what "run behavioral tests" means. The paste-ready prompt tells the new session exactly what commands to run and what to expect.

Example test prompt (for a context-mode gate):
```
Test the hardgate hooks installed in this project. Run these commands
via Bash and report what happens for each:

1. cat README.md — should be BLOCKED by HARD-RULE-10
2. git add . — should execute normally, no HARD-RULE marker
3. TMP=$(mktemp -d) && mkdir "$TMP/cat-shaped-dir" && rm -rf "$TMP" — should execute normally (no over-match)

Report a table: Test | Expected | Actual | Pass/Fail
Do not fix anything if a test fails. Just report.
```

### Remove a gate

```
/disable-gate
```

No arguments: lists installed gates and asks which to remove.

```
/disable-gate context-mode
```

With argument: removes the named gate after confirmation. Backs up before deleting.

---

## How It Works — By Target Type

### Plugin gates (e.g., context-mode)

**What's blocked:** Bash commands that should go through the plugin's MCP tools instead. For context-mode, this means `cat`, `grep`, `git log`, `pytest`, `ls -la`, and anything else that produces large output.

**What's allowed:** Write operations (`git add`, `git commit`, `git push`, `mkdir`, `rm`, `mv`, `cp`, `chmod`) and navigation (`cd`, `pwd`, `echo`).

**How it blocks:** A Python tokenizer parses the Bash command into sub-commands, strips env-var prefixes and path prefixes from each verb, and checks against a forbidden set. If the verb matches, it returns `exit 2` with a `[HARD-RULE-N] BLOCKED` message on stderr. Claude Code sees the error and cannot proceed with that tool call.

### Skill gates (e.g., coder-ui-qa-test / mandatory deliverables)

**What's blocked:** `git push`, `gh release create`, `npm publish`, or `python -m build` when required deliverables are missing from the project directory.

**What's allowed:** The same commands succeed once all required deliverables exist on disk.

**How it blocks:** The hook checks for the existence of required files (README, USER-MANUAL, docs/index.html, UML diagrams, etc.) relative to `$CLAUDE_PROJECT_DIR`. If any are missing, it returns `exit 2` with a list of what's missing.

### Shortcut gates

**What's blocked:** Nothing — shortcuts can't be hard-gated because there's no tool call to intercept for "the user could have used a slash command but typed words instead."

**What happens instead:** A Level 2 nag on stderr reminds the model to use the shortcut when it detects the manual pattern. Advisory only.

---

## Critical: Cowork Compatibility

**User-level hooks (`~/.claude/settings.json` hooks block, `~/.claude/hooks/`) do NOT fire in Cowork's Code tab.** This is a known platform limitation ([GitHub issue #27398](https://github.com/anthropics/claude-code/issues/27398)). Only **project-level** hooks fire.

Hardgate handles this automatically — all hook scripts and wiring go to project-level `.claude/` paths using `$CLAUDE_PROJECT_DIR`. You don't need to configure anything.

If you're using Claude Code CLI (not Cowork), hooks fire from both user and project level. Hardgate's project-level approach works in both environments.

---

## Per-Project Gates

Gates install at the project level, meaning they apply to whatever directory Cowork's Code tab is pointed at. By default, that's your main working directory (e.g., `~/Desktop/Claude`).

If you want different gates for a sub-project:

1. Open a session in the sub-project directory (tell CC to `cd` into it)
2. Run `/hard-gate` from there
3. The artifacts install into the sub-project's `.claude/` directory

Gates from parent and child directories **stack** — both fire. A sub-project can add stricter rules on top of the parent's gates.

---

## Files Reference

```
~/.claude/
  skills/
    hard-gate-installer/
      SKILL.md              ← The installer skill (reads targets, writes artifacts)
  commands/
    hard-gate.md            ← /hard-gate slash command
    disable-gate.md         ← /disable-gate slash command

<your-project>/
  .claude/
    settings.json           ← Hook wiring (PreToolUse, SessionStart)
    hooks/
      <target>-gate.sh      ← Thin bash wrapper
      <target>-gate.py      ← Gate logic (tokenizer, pattern matching)
      <target>-session-start.sh  ← SessionStart wrapper
      <target>-session-start.py  ← Emits additionalContext JSON
```

---

## Troubleshooting

**Gate doesn't fire after install:**
Restart the Code tab. Hooks load at session start, not mid-session.

**Gate blocks everything / blocks nothing:**
Run the unit test manually:
```bash
python3 .claude/hooks/<target>-gate.py <<< '{"tool_name":"Bash","tool_input":{"command":"cat /etc/hosts"}}' 2>&1 ; echo "EXIT: $?"
```
Should return `EXIT: 2` with the BLOCKED marker for forbidden commands, `EXIT: 0` for allowed ones.

**False positives (e.g., `mkdir /tmp/cat-pics` blocked):**
The gate tokenizes commands and checks the verb, not substrings. If you're seeing false positives, the tokenizer has a bug — file an issue with the exact command that was incorrectly blocked.

**SessionStart announcement missing:**
The SessionStart hook isn't emitting context for the new session. Both of these JSON output formats are valid and either will work:

```json
{"additionalContext": "..."}
```

```json
{"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "..."}}
```

Hardgate uses the flat (top-level) form because that matches Anthropic's documented examples and works in both Claude Code CLI and Cowork. If you switched to the nested `hookSpecificOutput` form and it isn't firing, double-check the `hookEventName` field is exactly `"SessionStart"` (case-sensitive). If you switched to the flat form and it isn't firing, make sure the `.py` script is actually emitting JSON on stdout and exiting 0 — try running it manually and inspecting the output.

**Hooks work in CLI but not in Cowork:**
Make sure hooks are in project-level `.claude/`, not user-level `~/.claude/`. User-level hooks don't fire in Cowork.

---

## Background

This tool exists because Claude Code treats every instruction — CLAUDE.md rules, skill protocols, slash command templates — as advisory text that the model can choose to follow or ignore. Under time pressure, long context, or ambiguous instructions, it ignores them. This is especially problematic for:

- **Token-saving plugins** (like context-mode) that require routing commands through MCP tools instead of raw Bash
- **Quality gates** (like mandatory deliverables) that require specific artifacts before pushing
- **Process compliance** (like TDD workflows) that require specific steps in a specific order

Hardgate was built after spending two days watching Claude Code ignore a context-mode plugin that was designed to save 60-80% of context window consumption. The plugin was installed, enabled, documented in CLAUDE.md as a "non-negotiable hard rule," and Claude Code still defaulted to raw Bash for everything.

The only mechanism in Claude Code's architecture that guarantees compliance is a **PreToolUse hook that returns exit code 2**. Everything else is persuasion. Hardgate automates the installation of that mechanism.

---

## License

MIT

---

## Author

Scott Converse — [github.com/scottconverse](https://github.com/scottconverse)
