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
│   └── hardgate-v1.0.0.zip   # Built offline installer (attached to Releases)
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
python3 scripts/build-docs.py          # (not yet committed — contributions welcome)
```

To rebuild the offline installer zip from `installer/`:

```bash
python3 scripts/build-installer.py     # (not yet committed — contributions welcome)
```

## Testing your changes

hardgate has no unit tests — the installer runs a **behavioral test** at the end of every install to verify the gate actually fires. If you modify `SKILL.md`, test your change by:

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
