#!/usr/bin/env python3
"""
Reference implementation of the stop-check.py template (SKILL.md Artifact 1.5).

Reads a Stop hook payload from stdin, detects push/release/publish intent in
the assistant's last message, resolves the project root via X1 git-root logic,
checks required deliverables, and emits {"decision":"block",...} on stdout if
any are missing.
"""
import glob as glob_mod
import json
import os
import pathlib
import re
import subprocess
import sys

RULE_NUMBER = 99  # Test sentinel

# ── intent detection ──────────────────────────────────────────────────────────

INTENT_PATTERN = re.compile(
    r"git\s+push|gh\s+release\s+create|npm\s+publish|python3?\s+-m\s+build",
    re.IGNORECASE,
)

# ── X1: git-root resolution ───────────────────────────────────────────────────

_LEADING_CD = re.compile(
    r'^\s*cd\s+(?:--\s+)?(?:"([^"]+)"|\'([^\']+)\'|(\S+))\s*(?:&&|;|$)'
)


def detect_cwd_from_payload(payload: dict) -> str:
    """
    Resolution order (X1):
    1. tool_input.cwd if present (test harness / wrapper injection)
    2. Leading `cd <path> &&` parsed from tool_input.command
    3. os.getcwd() of the hook process
    """
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


def find_project_root(payload: dict) -> str:
    """
    From the detected cwd, run `git rev-parse --show-toplevel` to find the
    actual repo root. Falls back to CLAUDE_PROJECT_DIR then cwd on failure.
    """
    cwd = detect_cwd_from_payload(payload)
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if r.returncode == 0:
            top = r.stdout.strip()
            if top and os.path.isdir(top):
                return top
    except Exception:
        pass
    return os.environ.get("CLAUDE_PROJECT_DIR") or cwd or "."


# ── deliverables check ────────────────────────────────────────────────────────

_DEFAULT_REQUIRED = [
    {"name": "README.md",      "glob": "README.md",                        "optional": False},
    {"name": "CHANGELOG.md",   "glob": "CHANGELOG.md",                     "optional": False},
    {"name": "LICENSE",        "glob": "LICENSE|LICENSE.md|LICENSE.txt",    "optional": False},
    {"name": "docs/index.html","glob": "docs/index.html",                  "optional": False},
]


def check_deliverables(project_root: str) -> list:
    """
    Return a list of missing required deliverable names.

    Reads .claude/deliverables.json if present; falls back to _DEFAULT_REQUIRED.
    Malformed deliverables.json fails closed (returns a non-empty list).
    Optional items (optional=true) are skipped.
    """
    config_path = pathlib.Path(project_root) / ".claude" / "deliverables.json"

    if config_path.exists():
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
            required = config.get("required", [])
        except (json.JSONDecodeError, Exception):
            return ["deliverables.json is malformed — fail-closed"]
    else:
        required = _DEFAULT_REQUIRED

    missing = []
    for item in required:
        if item.get("optional"):
            continue
        globs = item["glob"].split("|")
        found = any(
            glob_mod.glob(g, recursive=True, root_dir=project_root)
            for g in globs
        )
        if not found:
            missing.append(item["name"])
    return missing


# ── main ──────────────────────────────────────────────────────────────────────


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    # Infinite-loop guard: if we are already inside a Stop hook response, exit
    if payload.get("stop_hook_active"):
        sys.exit(0)

    msg = payload.get("last_assistant_message") or ""
    if not INTENT_PATTERN.search(msg):
        sys.exit(0)

    project_root = find_project_root(payload)
    missing = check_deliverables(project_root)

    if missing:
        result = {
            "decision": "block",
            "reason": (
                f"Hard Rule {RULE_NUMBER}: missing deliverables before push: "
                + ", ".join(missing)
                + f" (resolved root: {project_root})"
            ),
        }
        print(json.dumps(result))

    sys.exit(0)


if __name__ == "__main__":
    main()
