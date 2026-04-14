# Hardgate User Manual

**Version 1.0** · Scott Converse · MIT License

Hardgate installs 7-location enforcement on any Claude Code plugin, skill, or slash command so Claude Code **physically cannot ignore it**. It works in Claude Code CLI and in Claude Desktop's Cowork Code tab.

This manual has three sections:

1. **End-User Guide** — how to install and use hardgate day-to-day
2. **Technical User Guide** — command reference, file paths, troubleshooting
3. **Architectural Overview** — how the enforcement model works, with UML

---

## 1. End-User Guide

### What problem does this solve?

Claude Code treats rules as advisory. You tell it "always use context-mode instead of raw Bash" — it complies for a while, then quietly stops, especially in long sessions or under time pressure. Skills, CLAUDE.md, and slash commands are all text the model *chooses* to follow. Hardgate replaces persuasion with a real `exit 2` that blocks the tool call before it runs.

### Installing hardgate

Hardgate itself is three files:

| File | Destination |
|------|-------------|
| `SKILL.md` | `~/.claude/skills/hard-gate-installer/SKILL.md` |
| `hard-gate.md` | `~/.claude/commands/hard-gate.md` |
| `disable-gate.md` | `~/.claude/commands/disable-gate.md` |

Copy them manually, or paste this into a Claude Code session:

```
mkdir -p ~/.claude/skills/hard-gate-installer ~/.claude/commands
```

Then create each file from this repo. Restart the Code tab.

### Installing your first gate

In the Code tab, type:

```
/hard-gate
```

Hardgate will:

1. Discover your installed plugins, skills, and slash commands
2. Ask which one you want to enforce
3. Classify it (plugin · skill · shortcut) and extract parameters
4. Ask you to confirm the enforcement plan in 2–3 sentences
5. Write all 7 artifacts
6. Give you a **paste-ready behavioral test prompt**
7. Tell you to restart the Code tab and paste the prompt

After restart, paste the test prompt. Claude Code runs the forbidden command (should be blocked), an allowed command (should work), and a false-positive edge case (should not over-match). You get a pass/fail table.

### Removing a gate

```
/disable-gate
```

Lists installed gates and asks which to remove. Or `/disable-gate <name>` to skip straight to removal. Hardgate backs up `settings.json` before editing, and does not remove permissions (they may be used by other plugins).

### Day-to-day use

You don't interact with gates directly. They fire silently when Claude Code attempts a forbidden action. When one fires, Claude Code sees a `[HARD-RULE-N] BLOCKED` message on stderr and re-routes through the allowed path (e.g., MCP tools instead of raw Bash).

---

## 2. Technical User Guide

### Requirements

- Claude Desktop (Windows or Mac) with Cowork enabled, OR Claude Code CLI
- Claude Pro, Max, Team, or Enterprise plan
- Python 3 on PATH (hook scripts are Python)
- The target you want to enforce must already be installed

### Command reference

```
/hard-gate [target]
```

Install a gate. Without arguments, runs discovery. With a target name, skips discovery.

```
/disable-gate [target]
```

Remove a gate. Without arguments, lists installed gates. With a target name, removes directly after confirmation.

### File layout after installation

```
~/.claude/
  skills/hard-gate-installer/SKILL.md     # the installer
  commands/hard-gate.md                   # /hard-gate
  commands/disable-gate.md                # /disable-gate
  CLAUDE.md                               # Hard Rule N appended (advisory)

<project>/.claude/
  settings.json                           # PreToolUse + SessionStart wiring
  hooks/<target>-gate.sh                  # bash wrapper
  hooks/<target>-gate.py                  # tokenizer + gate logic
  hooks/<target>-session-start.sh         # SessionStart wrapper
  hooks/<target>-session-start.py         # emits additionalContext JSON
  plans/                                  # required for Rule 11 plan gate

~/.claude/projects/<project>/memory/<target>-gate.md   # persistent reminder
```

### Cowork compatibility — CRITICAL

User-level hooks (`~/.claude/settings.json` hooks block, `~/.claude/hooks/`) **do not fire in Cowork's Code tab**. This is a known platform limitation. Hardgate handles this automatically: all hook scripts and wiring go into project-level `.claude/` using `$CLAUDE_PROJECT_DIR`.

If you write a hook by hand and place it under `~/.claude/`, it will silently do nothing in Cowork.

### How hooks are bound to a session

Hooks are bound to the session's `$CLAUDE_PROJECT_DIR`, which is set when the session starts. **Changing directories with `cd` does NOT change which project's hooks fire.** If you open a session in `~/Desktop/Claude` and `cd` into a sub-project, the parent's hooks still apply to every Bash call.

To get different gate behavior in a sub-project, open a new Claude Code / Cowork session rooted at the sub-project directory.

### Gate behavior by target type

| Target type | What's blocked | What's allowed |
|---|---|---|
| **Plugin** (e.g., context-mode) | Bash verbs that the plugin replaces (`cat`, `grep`, `git log`, `pytest`, `ls -la`) | Write ops (`git add`, `git commit`, `git push`, `mkdir`, `rm`, `mv`) and navigation |
| **Skill** (e.g., coder-ui-qa-test) | `git push`, `gh release create`, `npm publish`, `python -m build` when required deliverables are missing from `$CLAUDE_PROJECT_DIR` | Everything once deliverables exist |
| **Shortcut** | Nothing — shortcuts can't be hard-gated (no tool call to intercept). SessionStart nag only. | All |

### Unit testing a gate

After installation, you can test the gate script directly without restarting:

```
python3 .claude/hooks/<target>-gate.py <<< '{"tool_name":"Bash","tool_input":{"command":"cat /etc/hosts"}}'
echo "exit=$?"
```

- Should return `exit=2` with the `[HARD-RULE-N] BLOCKED` marker for forbidden commands
- Should return `exit=0` silently for allowed commands

### Behavioral testing

Unit tests prove the script logic is correct. **Behavioral tests prove the harness actually fires it.** The difference matters: a correct script can still be silently skipped if `settings.json` wiring is wrong or if the session was started before the hook was wired.

Behavioral testing requires a session restart. Hardgate gives you a paste-ready test prompt after installation. Paste it into the new session; Claude Code will try the forbidden command, an allowed command, and an edge case, and report pass/fail.

### Troubleshooting

**Gate doesn't fire:** Restart the Code tab. Hooks load at session start.

**Gate blocks everything / nothing:** Run the unit test. If the script works but the gate doesn't fire, check `.claude/settings.json` wiring and path quoting.

**False positives (e.g., `mkdir /tmp/cat-pics` blocked):** The tokenizer should strip path prefixes before checking the verb. If it's matching on substring, file a bug with the exact command.

**SessionStart announcement missing:** The `.py` script must emit `{"additionalContext": "..."}` at the top level of stdout, not nested.

**Works in CLI but not Cowork:** Make sure hooks are in project-level `.claude/`, not user-level `~/.claude/`.

### Override and bypass

Every gate has an override. For hardgate's own install of the coder-ui-qa-test gate, the human must type the literal phrase `override rule 9` in chat, and the model may then temporarily disable the hook. Never silently work around a gate — if you're tempted to `mv hook.sh hook.sh.disabled` without an explicit override, that's a bug in your workflow.

For the superpowers plan gate, a one-off bypass is `touch .claude/plans/_adhoc.md`. The gate checks existence, not content, but the bypass file is visible in `git status`.

---

## 3. Architectural Overview

### The three enforcement levels

Hardgate writes artifacts at three levels, each with a different mechanism and failure mode.

**Level 1 — Advisory.** Text in `CLAUDE.md` (global and project). The model reads these every turn and *chooses* to comply. Failure mode: quietly ignored under pressure. Useful for refusal language and "why" — without it, the model hits a blocked tool call and has no idea what to do instead.

**Level 2 — Reminder.** SessionStart hooks emit `additionalContext` JSON on the first turn; memory files are injected per-turn. Failure mode: scrolls out of attention in long sessions. Useful for keeping the rule visible so the advisory layer stays active.

**Level 3 — Blocking.** PreToolUse hooks return `exit 2`. The Claude Code harness enforces this at the tool-call boundary — the model doesn't get to choose. Failure mode: only fails if the hook script has a bug or if the wiring is wrong. This is the layer that actually works.

The advisory and reminder layers exist to keep the model from thrashing when the blocking layer fires. Without them, Claude Code would retry the blocked command repeatedly without understanding why.

### The 7 artifacts

```
Level 3 (blocking)
  1. .claude/hooks/<target>-gate.sh + .py
  2. .claude/settings.json hooks.PreToolUse[Bash]
  3. ~/.claude/settings.json permissions.allow (for plugin targets)

Level 2 (reminder)
  6. .claude/hooks/<target>-session-start.sh + .py (+ settings.json wiring)
  7. ~/.claude/projects/<project>/memory/<target>-gate.md

Level 1 (advisory)
  4. ~/.claude/CLAUDE.md Hard Rule N
  5. <project>/CLAUDE.md Hard Rule N
```

Numbering follows the install order in `SKILL.md`, not enforcement level.

### Architecture diagram

See `docs/architecture.mmd` for the full Mermaid source. The runtime enforcement path is:

```
Claude Code attempts Bash
  └─> PreToolUse hook (.sh wrapper)
       └─> Python tokenizer
            ├─ strip env-var and path prefixes from each sub-command
            ├─ check verb against forbidden set
            ├─ match    -> stderr: [HARD-RULE-N] BLOCKED, exit 2
            └─ no match -> exit 0, tool proceeds
```

The tokenizer is the load-bearing piece. Naive substring matching causes false positives (`mkdir /tmp/cat-pics` would match `cat`). Proper tokenization splits on `;`, `|`, `&&`, `||`, strips env-var assignments (`FOO=bar cmd`) and path prefixes (`/usr/bin/cat` → `cat`), then checks the resulting verb.

### Why 7 locations and not 1?

In theory, a single PreToolUse hook is enough. In practice, without the advisory and reminder layers, the model has no context for the block and will retry indefinitely or complain that the tool is broken. The full 7-location install is the minimum viable set that keeps both the harness and the model aligned on the same rule.

### Known limitations

- **Cowork user-level hooks silently fail** — everything must be project-scoped.
- **Hooks are bound to `$CLAUDE_PROJECT_DIR`, not cwd** — sub-projects need their own session.
- **Shortcut gates are advisory-only** — there's no tool call to intercept when a user types words instead of a slash command.
- **The plan gate (Hard Rule 11) and deliverables gate (Hard Rule 9) use project paths** — deliverables in a sub-repo are not visible to a parent session's gate, so the parent blocks pushes for sub-repos. This is by design.

### License and author

MIT License. Copyright © 2026 Scott Converse. See `LICENSE`.
