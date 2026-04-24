"""Smoke tests for templates/commit-size-gate/commit-size-gate.py — Rule 11.

Covers the four behavioral cases validated before promotion in civiccore,
scottconverse/patentforgelocal (commit 007e924), and scottconverse/productteam
(commit 76333aa):

- 900-line staged diff, no tag                → BLOCK (exit 2)
- 900-line staged diff, "[MVP]" tag           → ALLOW (exit 0)
- 25-line staged diff, no tag                  → ALLOW (exit 0)
- 900-line staged diff, substring "MVP flow"   → BLOCK (exit 2)

Tests execute the real template file via subprocess with a temporary git repo
providing real `git diff --cached --numstat` output. No fixture copy.
"""
import json
import os
import pathlib
import subprocess
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).parent.parent
TEMPLATE_GATE = REPO_ROOT / "templates" / "commit-size-gate" / "commit-size-gate.py"


def _init_repo_with_staged(tmp_path: pathlib.Path, lines: int) -> pathlib.Path:
    """Initialize a git repo and stage `lines` new lines in big.txt.

    A seed commit is made first so HEAD exists and `git diff --cached` has a
    well-defined parent to diff against.
    """
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "t@t.local"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "tester"], cwd=tmp_path, check=True)
    (tmp_path / "seed.txt").write_text("seed\n", encoding="utf-8")
    subprocess.run(["git", "add", "seed.txt"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "seed"], cwd=tmp_path, check=True)

    content = "".join(f"line {i}\n" for i in range(lines))
    (tmp_path / "big.txt").write_text(content, encoding="utf-8")
    subprocess.run(["git", "add", "big.txt"], cwd=tmp_path, check=True)
    return tmp_path


def _run(cmd: str, project_dir: pathlib.Path) -> int:
    """Invoke the template gate with `CLAUDE_PROJECT_DIR=project_dir` and a
    Bash PreToolUse payload containing `cmd`. Return the exit code.
    """
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(project_dir)
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}})
    result = subprocess.run(
        [sys.executable, str(TEMPLATE_GATE)],
        input=payload,
        capture_output=True,
        text=True,
        env=env,
    )
    return result.returncode


def test_template_file_exists():
    assert TEMPLATE_GATE.is_file(), (
        f"Template gate not found at {TEMPLATE_GATE}. Promotion commit may be missing."
    )


class TestCommitSizeGateTemplate:
    def test_900_no_tag_blocks(self, tmp_path):
        _init_repo_with_staged(tmp_path, 900)
        code = _run('git commit -m "big change"', tmp_path)
        assert code == 2, (
            "900-line staged diff with no tag must BLOCK (exit 2). "
            f"Got exit {code}."
        )

    def test_900_with_mvp_tag_allows(self, tmp_path):
        _init_repo_with_staged(tmp_path, 900)
        code = _run('git commit -m "[MVP] big change"', tmp_path)
        assert code == 0, (
            "900-line staged diff with [MVP] tag must ALLOW (exit 0). "
            f"Got exit {code}."
        )

    def test_25_no_tag_allows(self, tmp_path):
        _init_repo_with_staged(tmp_path, 25)
        code = _run('git commit -m "tiny fix"', tmp_path)
        assert code == 0, (
            "25-line staged diff with no tag must ALLOW (exit 0) — "
            f"under the 800-line threshold. Got exit {code}."
        )

    def test_900_mvp_substring_no_brackets_blocks(self, tmp_path):
        """Adversarial: 'fixed a bug with the MVP flow' contains 'MVP' as a
        substring but not as the literal bracketed token '[MVP]'. The gate's
        TAG_RE regex requires the literal bracketed form, so this must BLOCK.
        A fail-open / substring-matching implementation would ALLOW.
        """
        _init_repo_with_staged(tmp_path, 900)
        code = _run('git commit -m "fixed a bug with the MVP flow"', tmp_path)
        assert code == 2, (
            "Adversarial substring 'MVP flow' (no brackets) must BLOCK (exit 2). "
            f"Got exit {code} — substring matching is leaking, gate is broken."
        )
