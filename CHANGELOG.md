# Changelog

All notable changes to hardgate will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `scripts/build-installer.py` — reproducible builder for `dist/hardgate-v<VERSION>.zip`. Syncs canonical skill files from the repo root into `installer/`, then produces a deterministic zip (fixed mtime, sorted entries, Unix `create_system`, 0755 for `install.sh` / 0644 for the rest).
- `scripts/build-docs.py` — regenerates `README.txt/.docx/.pdf` and `USER-MANUAL.docx/.pdf` from the `.md` sources, with the UML architecture diagram embedded in the `.docx` and `.pdf` appendices.
- `scripts/test-installer.ps1` — PowerShell mirror of `test-installer.sh`, exercises `install.ps1` against an isolated fake `$HOME` with the same four test groups (zip integrity, happy path, backup-on-reinstall, refuse-on-missing-sources).
- `.github/workflows/ci.yml` — GitHub Actions CI running three jobs on every push and PR:
  1. `install.sh` test harness on `ubuntu-latest`
  2. `install.ps1` test harness on `windows-latest`
  3. installer drift check — rebuilds `hardgate-v1.0.0.zip` from source in a tmpdir and fails if the sha256 does not match the committed `dist/hardgate-v1.0.0.zip`.

### Changed
- `dist/hardgate-v1.0.0.zip` rebuilt via `scripts/build-installer.py` for reproducibility. The Release asset on GitHub was re-uploaded to match. The installed-file contents are byte-identical to the original; only the zip container metadata (file order, create_system, mtimes) changed. After the install.ps1 fixes below the zip was rebuilt a second time; current sha256: `0a2c8e4760d6349b1bb56a09f20937f6dfe8526f91cf4f3721361aed62ce3074`.
- README/USER-MANUAL multi-format outputs regenerated through `scripts/build-docs.py`. The ad-hoc initial build used a `©` glyph in the copyright line; the reproducible build uses ASCII `(c)` to avoid encoding surprises in PDFs.
- `.gitattributes` added to force LF line endings in the working tree on every platform. Without this, Windows GitHub runners (which ship with `core.autocrlf=true`) checked out `.md` files as CRLF, causing the installer test harness to fail when comparing source files (CRLF on the runner) against the LF contents of the installer zip.

### Fixed
- **`install.ps1` did not honor an isolated test home.** The PowerShell test harness tried to override `$HOME` via `pwsh -Command "$HOME = ..."` in a child process, but PowerShell's automatic `$HOME` is initialized at host startup and the override did not propagate to the script's scope. As a result, `install.ps1` happily wrote files to the real user profile during CI runs and the test then found nothing in the fake home. Fix: added a `-TargetHome` parameter to `install.ps1` (defaults to `$HOME`); the test harness now passes `-TargetHome <fake-home>` explicitly. Production users still call the script with no arguments.
- **`install.ps1` returned the wrong exit code on the missing-sources path.** With `$ErrorActionPreference = 'Stop'`, the `Write-Error` call thrown for missing source files terminated the script before the subsequent `exit 2` could run, so the harness was hitting the wrong exit code. Fix: write the error message to `[Console]::Error` directly, then `exit 2`. The refuse-when-sources-missing test now passes on Windows.
- **Windows CI sha256 mismatch.** Even after the two fixes above, the runner's source-vs-installed sha256 comparison still failed because `actions/checkout@v4` on `windows-latest` was applying `core.autocrlf=true` to the `.md` files, while the installer zip carried LF. Fix: committed `.gitattributes` to pin all text files to LF on every platform.

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
