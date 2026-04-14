# Changelog

All notable changes to hardgate will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### v1.1.0 Sprint 1 — quick wins (7 audit items)

- **(B3, #15)** Step 0 plugin discovery now walks `~/.claude/plugins/` directly instead of `~/.claude/plugins/marketplaces/`. The old subpath only caught Cowork-marketplace installs and missed CLI/manual installs and custom registries.
- **(B6, #16)** `disable-gate.md` no longer instructs the model to remove `PostToolUse` hook entries from `settings.json`. Hardgate has never installed `PostToolUse` hooks — the line was leftover drift from an earlier install spec. Also added the missing `<target>-stop-check.py` to the deletion list (the `.sh` wrapper was already there but the `.py` script was not).
- **(B7, #21)** Switched all hook command paths in SKILL.md from `"$CLAUDE_PROJECT_DIR/.claude/hooks/..."` (whole-path quoting) to `"$CLAUDE_PROJECT_DIR"/.claude/hooks/...` (variable-only quoting). Both forms are functionally equivalent in POSIX shells, but variable-only matches Anthropic's documented hook examples and is the convention to follow. Four spots updated: Artifact 1 .sh wrapper, Artifact 2 PreToolUse wiring, Artifact 2 Stop hook for skill targets, Artifact 6 SessionStart wrapper + wiring.
- **(B2, #22)** README troubleshooting section for "SessionStart announcement missing" now documents that BOTH the flat `{"additionalContext": "..."}` and nested `{"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "..."}}` JSON output formats work. Hardgate uses the flat form because it matches Anthropic's documented examples and works in both Claude Code CLI and Cowork. The previous note actively steered users away from the (also valid) nested form.
- **(U3, #13)** `hard-gate.md` "Do not analyze, plan, or describe what you will do" directive now has an explicit exception for the Step 2 parameter confirmation, which is required before any artifacts are written. Removes the tension between the slash command's terse instruction and SKILL.md Step 2's "confirm with the user in 2-3 sentences" requirement.
- **(U5, #19)** Behavioral test commands in SKILL.md Step 6 are now portable and self-cleaning. `cat /etc/hosts` (system file, may be restricted on some Linux containers) is now `cat README.md` (file guaranteed to exist in any project). The false-positive test `mkdir /tmp/cat-pics-test` (left an unowned directory behind on every run) is now `TMP=$(mktemp -d) && mkdir "$TMP/cat-shaped-dir" && rm -rf "$TMP"` (exercises the same `mkdir <path-containing-cat>` over-match path, then self-cleans).
- **(U4, #14)** SKILL.md Step 0 has a new bootstrap-conflict warning: if installing a gate on the context-mode plugin (or any tool that intercepts Bash) AND that tool is already running as a hard gate in this session, the installer's own discovery commands will be blocked. Recommends running the installer in a fresh session where the target gate is not yet active. Keeps the existing `ctx_execute` instruction as the workaround for soft/advisory installs.

### Build artifact

- `dist/hardgate-v1.0.1.zip` rebuilt after Sprint 1 SKILL.md changes. New sha256: `8a4ea156ad6c8c860ba82ae6f7c6d9346608e803cb27288b9811d1c63acc94eb`. The CI drift check is updated automatically since the committed zip is the source of truth.

## [1.0.1] — 2026-04-14

Hotfix release addressing four issues from the v1.0 technical audit and live development findings: a critical scope bug in skill gates, a security gap in the tokenizer, a phantom hook reference, and a UX friction point. Plus the post-v1.0.0 build/CI infrastructure that previously sat in `[Unreleased]`.

### Fixed
- **(X1) Skill gates checked the wrong project root.** The skill-target gate template used `$CLAUDE_PROJECT_DIR` (the Cowork session root) for deliverable resolution. Pushes from any sub-project under that root were blocked by deliverable checks against the parent directory. Confirmed live: a font fix in `civicrecords-ai` was blocked because `Desktop\Claude` did not contain a `USER-MANUAL.pdf`. Fix: the gate now resolves the project root via `git rev-parse --show-toplevel` from the user's cwd, falling back to `$CLAUDE_PROJECT_DIR` only if the user is not in a git repo. Both the `SKILL.md` Artifact 1 skill-target template and the live `coder-ui-qa-test-gate.py` deployments need this patch. Failure messages now also print the resolved project root so wrong-project blocks are easy to diagnose.
- **(D2) Tokenizer was bypassable via `sh -c` and inline-code interpreter flags.** `sh -c "cat /etc/hosts"` passed because the tokenizer saw `sh`, not `cat`. Same for `bash -c`, `zsh -c`, `python3 -c "import os; os.system('cat /etc/hosts')"`, `perl -e`, `ruby -e`, `node -e`, `php -r`, `deno eval`. This was the most realistic bypass path for a model under pressure. Fix: the tokenizer now (a) detects `sh|bash|zsh|dash|ash|ksh + -c <arg>`, recursively re-tokenizes the `-c` argument with `shlex.split()` capped at depth 2, and **fails closed** on unparseable arguments; (b) detects scripting interpreters (`python|python2|python3|perl|ruby|node|deno|php`) with their inline-code flags and **blocks outright** — there is no reliable way to statically analyze arbitrary inline code. Verified against 19 cases including direct calls, env-prefix bypass, compound chains, nested `bash -c "bash -c \"...\""`, and benign `sh -c "git add ."` (which still passes).
- **(B1) `stop-check.sh` was wired in `settings.json` but never created.** SKILL.md Artifact 2 added a `Stop` hook entry pointing at `<target>-stop-check.sh` for skill targets, and `disable-gate.md` listed it for removal — but no artifact ever wrote it. Result: the Stop hook event fired with no script present, Claude Code logged a non-blocking error, and the deliverable check at end-of-turn never ran. Fix: a new Artifact 1.5 in `SKILL.md` creates `<target>-stop-check.sh` and `<target>-stop-check.py` for skill targets, with the same git-root resolution from X1, the same deliverables list, a `chmod +x`, and a unit test. Step 5 verification now hard-fails for skill targets if the stop-check is missing.
- **(U1) Test prompt was lost after the required session restart.** Step 6 of the install protocol generated a paste-ready test prompt and told the user to restart the Code tab — but the prompt only existed in the previous session's transcript, which is hard to recover after restart. Confirmed during development: a user who typed "run behavioral tests" in the new session got blank stares from the model. Fix: Step 6 now writes the test prompt to `.claude/hardgate-test-prompt.txt` before instructing the user to restart, and the user-facing message points at that file.
- **`install.ps1` did not honor an isolated test home.** The PowerShell test harness tried to override `$HOME` via `pwsh -Command "$HOME = ..."` in a child process, but PowerShell's automatic `$HOME` is initialized at host startup and the override did not propagate to the script's scope. Fix: added a `-TargetHome` parameter to `install.ps1` (defaults to `$HOME`); the test harness passes `-TargetHome <fake-home>` explicitly.
- **`install.ps1` returned the wrong exit code on the missing-sources path.** With `$ErrorActionPreference = 'Stop'`, `Write-Error` threw before `exit 2` could run. Fix: write the error message to `[Console]::Error` directly, then `exit 2`.
- **Windows CI sha256 mismatch.** Windows GitHub runners apply `core.autocrlf=true` on checkout, converting `.md` files to CRLF, while the installer zip carries LF — the test harness then compared mismatched bytes. Fix: committed `.gitattributes` to pin all text files to LF on every platform.

### Added
- `scripts/build-installer.py` — reproducible builder for `dist/hardgate-v<VERSION>.zip`. Syncs canonical skill files from the repo root into `installer/`, then produces a deterministic zip (fixed mtime, sorted entries, Unix `create_system`, 0755 for `install.sh` / 0644 for the rest).
- `scripts/build-docs.py` — regenerates `README.txt/.docx/.pdf` and `USER-MANUAL.docx/.pdf` from the `.md` sources, with the UML architecture diagram embedded in the `.docx` and `.pdf` appendices.
- `scripts/test-installer.sh` and `scripts/test-installer.ps1` — installer test harnesses for Linux/git-bash and Windows PowerShell. Each runs four test groups: zip integrity, happy-path install, backup-on-reinstall, refuse-on-missing-sources.
- `.github/workflows/ci.yml` — GitHub Actions CI running three jobs on every push and PR:
  1. `install.sh` test harness on `ubuntu-latest`
  2. `install.ps1` test harness on `windows-latest`
  3. installer drift check — rebuilds `hardgate-v1.0.1.zip` from source in a tmpdir and fails if the sha256 does not match the committed `dist/hardgate-v1.0.1.zip`.
- `.gitattributes` — forces LF line endings on every platform regardless of git's `autocrlf` setting.
- `CHANGELOG.md`, `CONTRIBUTING.md`, `.gitignore` — repo hygiene files.

### Changed
- `dist/hardgate-v1.0.1.zip` is the new release artifact built via `scripts/build-installer.py` for reproducibility. The v1.0.0 zip is no longer in `dist/`; the v1.0.0 GitHub Release asset remains downloadable from its own tag.
- `SKILL.md` Artifact 1 unit test for the gate script now uses an explicit `[ $EXIT -eq 2 ] || exit 1` assertion instead of just `echo "EXIT: $?"`. A confused model can hallucinate "EXIT: 2" success without actually running the test, but cannot fake a non-zero shell exit.
- README/USER-MANUAL multi-format outputs regenerated through `scripts/build-docs.py`. The ad-hoc initial build used a `©` glyph in the copyright line; the reproducible build uses ASCII `(c)` to avoid encoding surprises in PDFs.
- All version references updated: `scripts/build-installer.py` default, `scripts/test-installer.{sh,ps1}` zip path, `.github/workflows/ci.yml` build/check commands, `docs/index.html` Download Installer button href, `CONTRIBUTING.md` examples.

### Deferred to v1.1.0
This release intentionally ships only the four hotfix items (X1, D2, B1, U1) and the post-v1.0.0 build infrastructure. Eighteen additional items from the audit (X2 deliverables config, D1 `if`-field optimization, B2–B7, U2–U7, D3–D5, X4 override marker file) are queued for the v1.1.0 milestone.

## [1.0.0] — 2026-04-14

### Added
- `hard-gate-installer` skill (SKILL.md) — discovers plugins/skills/commands, classifies the target, extracts enforcement parameters, writes 7 artifacts, and runs a behavioral test.
- `/hard-gate` slash command — invokes the installer skill with an optional target argument.
- `/disable-gate` slash command — removes an installed gate with safe JSON editing of `settings.json` and backup.
- Offline installer `hardgate-v1.0.0.zip` with cross-platform install scripts (`install.sh` for Mac/Linux/git-bash, `install.ps1` for Windows).
- `INSTALL.md` — three-step quick start.
- `INSTALL-PROMPT.md` — paste-ready prompt for installing via a Claude Code session.
- `README.md`, `README.txt`, `README.docx`, `README.pdf` — project overview in four formats, with UML embedded in docx/pdf.
- `USER-MANUAL.md`, `USER-MANUAL.docx`, `USER-MANUAL.pdf` — three-section manual (End-User, Technical User, Architectural) with embedded UML.
- `docs/architecture.mmd` — Mermaid UML diagram of the 7-location enforcement model.
- `docs/index.html` — custom landing page served via GitHub Pages at <https://scottconverse.github.io/hardgate/>.
- `.github/DISCUSSIONS_SEEDED` — marker + drafts for 4 seed discussion posts.
- GitHub Discussions seeded with 4 starter posts (Announcements, Q&A, Ideas, Show and tell).

### Enforcement model
- **Level 3 (blocking)** — PreToolUse hook returns `exit 2` via a Python tokenizer that strips env-var and path prefixes before matching the verb.
- **Level 2 (reminder)** — SessionStart hook emits `additionalContext` JSON; per-project memory file provides a persistent reminder.
- **Level 1 (advisory)** — Global and project `CLAUDE.md` rule text provides refusal language and rationale.

### Cowork compatibility
- All hook scripts and wiring go in **project-level** `.claude/` using `$CLAUDE_PROJECT_DIR`. User-level hooks silently fail in Cowork's Code tab ([claude-code#27398](https://github.com/anthropics/claude-code/issues/27398)).

### Known limitations
- Hooks are bound to the session's `$CLAUDE_PROJECT_DIR` at session start, not cwd. Changing directories with `cd` does not change which project's hooks fire. To get different gate behavior in a sub-project, open a new session rooted at the sub-project directory.
- Shortcut gates are advisory-only — there is no tool call to intercept when a user types words instead of a slash command.

[1.0.1]: https://github.com/scottconverse/hardgate/releases/tag/v1.0.1
[1.0.0]: https://github.com/scottconverse/hardgate/releases/tag/v1.0.0
