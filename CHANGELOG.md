# Changelog

All notable changes to hardgate will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

[1.0.0]: https://github.com/scottconverse/hardgate/releases/tag/v1.0.0
