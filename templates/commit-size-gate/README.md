# commit-size-gate — canonical template

A project-level PreToolUse hook that blocks `git commit` when the staged diff
exceeds `THRESHOLD` lines (insertions + deletions, ignoring binary files) and
the commit message does not contain one of the allowed literal bracketed tag
tokens. Intent: keep commits small and reviewable; when a change is genuinely
large, force explicit acknowledgment via a tag rather than silent bloat.

This is the canonical reference implementation for the rule installed as
**Hard Rule 11 — Commit-Size Acknowledgment Gate** in `~/.claude/CLAUDE.md`.

## Allowed tag tokens

Literal bracketed match only — substrings like "the MVP flow" do NOT satisfy:

```
[MVP]  [LARGE-CHANGE]  [REFACTOR]  [INITIAL]  [MERGE]  [REVERT]
[SCOPE-EXPANSION: <reason>]
```

## Tunables (top of `commit-size-gate.py`)

- `THRESHOLD = 800` — staged insertions + deletions
- `OVERRIDE_WINDOW_SECONDS = 60` — `override rule 11` one-shot bypass window

## Bypass surfaces (fail-open, by design)

The hook does **not** fire on:

- `git commit --amend` — final message not reliably parseable at PreToolUse
- `git commit -F <file>` — message lives in a file the hook can't read safely
- editor commits (no `-m` flag) — message comes from `$EDITOR` post-hook
- any exception in the script — fail-open so a hook bug never locks the user out

If you amend into a large commit, self-police with the tag on the next real
`-m` commit.

## Pressure valve

The user says the literal phrase `override rule 11`. Claude (or the user)
writes the current timestamp to:

- `$CLAUDE_PROJECT_DIR/.claude/hardgate-override-rule-11` (project-level), or
- `$HOME/.claude/hardgate-override-rule-11` (user-level)

The hook reads the marker, confirms `mtime < OVERRIDE_WINDOW_SECONDS`, deletes
it, and allows the next `git commit` through once.

## Install

From the project root:

```bash
mkdir -p .claude/hooks
cp /path/to/hardgate/templates/commit-size-gate/commit-size-gate.py            .claude/hooks/
cp /path/to/hardgate/templates/commit-size-gate/commit-size-gate.sh            .claude/hooks/
cp /path/to/hardgate/templates/commit-size-gate/commit-size-session-start.py   .claude/hooks/
cp /path/to/hardgate/templates/commit-size-gate/commit-size-session-start.sh   .claude/hooks/
```

Then wire into `.claude/settings.json` (merge with any existing `hooks` block):

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {"type": "command", "command": "\"$CLAUDE_PROJECT_DIR/.claude/hooks/commit-size-gate.sh\""}
        ]
      }
    ],
    "SessionStart": [
      {
        "hooks": [
          {"type": "command", "command": "\"$CLAUDE_PROJECT_DIR/.claude/hooks/commit-size-session-start.sh\""}
        ]
      }
    ]
  }
}
```

## Verify post-install (4 behavioral tests)

Seed two throwaway repos: one with `>THRESHOLD` staged lines, one with a small
staged diff. For each of the four tests below, pipe a PreToolUse JSON payload
to `commit-size-gate.py` with `CLAUDE_PROJECT_DIR` pointed at the appropriate
seed repo:

| # | Staged diff | Commit message | Expected |
|---|---|---|---|
| 1 | 900 lines | `"big change"` (no tag) | **BLOCK** (exit 2) |
| 2 | 900 lines | `"[MVP] big change"` | **ALLOW** (exit 0) |
| 3 | 25 lines | `"tiny fix"` (no tag) | **ALLOW** (exit 0) |
| 4 | 900 lines | `"fixed a bug with the MVP flow"` (substring, no brackets) | **BLOCK** (exit 2) |

Test 4 proves the literal-bracketed-token regex is working; if substring
matching were active, test 4 would have allowed.

## Validation provenance

This template is the exact file set deployed and behaviorally verified in:

- `scottconverse/civiccore` — validation project (`.claude/` gitignored, local-only)
- `scottconverse/patentforgelocal` — commit `007e924`, repo-shared
- `scottconverse/productteam` (via `productteam-v2` working copy) — commit `76333aa`, repo-shared

Also wired (local-only, `.claude/` gitignored) in `scottconverse/civicrecords-ai`.

All four behavioral tests above passed 12/12 across the three active projects
during rollout. Hook constants and regexes are byte-identical to the validated
deployment.

## Scope — what this template does NOT do

- Does not modify any `CLAUDE.md` (rule text lives in `~/.claude/CLAUDE.md`).
- Does not install other supervisor-mode artifacts (no honesty gate, no scope
  gate, no secrets gate, no `tasks.md`, no `handoff.md`, no `tests/uat/`).
- Does not touch project `.gitignore`. Projects choose `LOCAL_ONLY`
  (gitignore `.claude/`) vs `REPO_SHARED` (commit `.claude/`) themselves.
- Does not dispatch subagents or generate cards. Companion skill
  `supervisor-card` (at `~/.claude/skills/supervisor-card/`) handles
  `docs/SUPERVISOR.md` generation separately.
