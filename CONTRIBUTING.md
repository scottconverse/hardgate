# Contributing to hardgate

Thanks for your interest in hardgate! This project is small — three markdown files plus documentation — but contributions are welcome.

## Project structure

```
hardgate/
├── SKILL.md                  # The installer skill (Claude reads this)
├── hard-gate.md              # /hard-gate slash command
├── disable-gate.md           # /disable-gate slash command
├── INSTALL.md                # Manual install instructions
├── INSTALL-PROMPT.md         # Paste-ready install prompt for a CC session
├── README.md / .txt / .docx / .pdf   # Multi-format README
├── USER-MANUAL.md / .docx / .pdf     # Three-section user manual
├── CHANGELOG.md
├── LICENSE                   # MIT
├── docs/
│   ├── index.html            # Landing page (served via GitHub Pages)
│   └── architecture.mmd      # Mermaid UML diagram
├── installer/                # Source for the offline installer
│   ├── install.sh            # Bash installer (Mac/Linux/git-bash)
│   ├── install.ps1           # PowerShell installer (Windows)
│   └── INSTALLER-README.md
├── dist/
│   └── hardgate-v1.0.1.zip   # Built offline installer (attached to Releases)
└── .github/
    └── DISCUSSIONS_SEEDED    # Marker + drafts for seed discussion posts
```

## Development setup

No build tooling is required for the core skill files — they are markdown and are interpreted directly by Claude Code. To work on the installer or documentation:

```bash
git clone https://github.com/scottconverse/hardgate.git
cd hardgate
```

To regenerate the multi-format README and USER-MANUAL (`.txt`, `.docx`, `.pdf`) from the `.md` sources:

```bash
python3 -m pip install --user python-docx reportlab
python3 scripts/build-docs.py
```

To rebuild the offline installer zip reproducibly from `installer/` (syncs the canonical `SKILL.md`, `hard-gate.md`, `disable-gate.md` from the repo root first):

```bash
python3 scripts/build-installer.py            # builds v1.0.1 to dist/
python3 scripts/build-installer.py 1.1.0      # builds v1.1.0 to dist/
```

The build is deterministic — identical inputs produce a byte-identical zip. CI enforces this via a drift check (`.github/workflows/ci.yml`) that rebuilds from source in a tmpdir and compares sha256 against the committed `dist/hardgate-v1.0.1.zip`.

## Testing your changes

hardgate has two layers of tests:

**1. Installer tests (automated, run in CI).** The `scripts/test-installer.sh` harness exercises `install.sh` end-to-end against an isolated fake HOME: zip integrity, happy-path install, content-hash verification, backup-on-reinstall, and refuse-on-missing-sources. `scripts/test-installer.ps1` mirrors this for `install.ps1` on Windows. CI runs both plus a drift check on every push and PR.

```bash
bash scripts/test-installer.sh
pwsh -File scripts/test-installer.ps1    # or powershell -ExecutionPolicy Bypass -File
```

**2. Gate behavioral tests (manual, run by the user).** The installer skill finishes every install by giving the user a paste-ready test prompt that verifies the gate actually fires in a fresh Claude Code session. If you modify `SKILL.md`, test your change by:

1. Copy your modified `SKILL.md` to `~/.claude/skills/hard-gate-installer/SKILL.md`.
2. Restart Claude Code / Cowork.
3. In a clean project directory, run `/hard-gate` and pick a test target.
4. Confirm the 7 artifacts are written and the behavioral test passes.

For tokenizer changes (the Python gate script inside `SKILL.md` — Artifact 1), you can unit-test directly:

```bash
python3 .claude/hooks/<target>-gate.py <<< '{"tool_name":"Bash","tool_input":{"command":"cat /etc/hosts"}}' ; echo $?
```

Expected: `2` for forbidden commands, `0` silently for allowed ones.

## Pull request guidelines

- **Keep changes focused.** One PR = one logical change.
- **Update the CHANGELOG.** Add an entry under `## [Unreleased]` describing what changed and why.
- **Update docs together with code.** If you change how a gate works, update `README.md`, `USER-MANUAL.md`, and `docs/architecture.mmd` in the same PR.
- **Stay Cowork-compatible.** All hook scripts and wiring must go in project-level `.claude/`, never user-level `~/.claude/`. User-level hooks silently fail in Cowork.
- **No secrets.** Never commit a GitHub PAT, API key, or credential. The pre-push secret scan in `coder-ui-qa-test` is the reference.

## Where to ask questions

- **Bug reports** → GitHub Issues
- **Usage questions** → GitHub Discussions → Q&A
- **Feature ideas** → GitHub Discussions → Ideas

## License

By contributing to hardgate, you agree that your contributions will be licensed under the MIT License (see `LICENSE`).
