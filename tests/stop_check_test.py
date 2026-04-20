"""Tests for the hardgate stop-check.py template (SKILL.md Artifact 1.5).

Covers:
- Intent regex: matches for git push, gh release create, npm publish, python -m build
- Intent regex: misses for unrelated messages
- stop_hook_active=True → exit 0 immediately (infinite-loop guard)
- Deliverables absent → {"decision":"block",...} on stdout
- Deliverables present → exit 0, no stdout
- Malformed deliverables.json → fail-closed
- Optional deliverables not counted as missing
- X1 git-root resolution with subprocess.run mocked
"""
import json
import os
import pathlib
import subprocess
import sys
from unittest import mock

import pytest

# ── fixture paths ─────────────────────────────────────────────────────────────

FIXTURES = pathlib.Path(__file__).parent / "fixtures"
STOP_CHECK_PY = FIXTURES / "stop_check.py"

# Import fixture module for unit tests
sys.path.insert(0, str(FIXTURES))
import stop_check as sc_mod  # noqa: E402


# ── subprocess helpers ────────────────────────────────────────────────────────


def run_sc(payload: dict, env: dict = None) -> tuple:
    """Run stop_check.py with payload. Returns (exit_code, stdout, stderr)."""
    return _run_raw(json.dumps(payload), env)


def _run_raw(stdin: str, env: dict = None) -> tuple:
    result = subprocess.run(
        [sys.executable, str(STOP_CHECK_PY)],
        input=stdin,
        capture_output=True,
        text=True,
        env=env if env is not None else os.environ.copy(),
    )
    return result.returncode, result.stdout, result.stderr


# ═════════════════════════════════════════════════════════════════════════════
# Intent regex
# ═════════════════════════════════════════════════════════════════════════════

class TestIntentRegex:
    @pytest.mark.parametrize("msg", [
        "I will now git push origin main",
        "Running git push --force-with-lease origin main",
        "Executing: git push",
        "gh release create v1.0.0 --notes 'release'",
        "npm publish --access public",
        "python -m build && twine upload dist/*",
        "python3 -m build .",
        # case-insensitive
        "GIT PUSH origin main",
        "NPM PUBLISH",
    ])
    def test_intent_detected(self, msg):
        assert sc_mod.INTENT_PATTERN.search(msg), f"Expected intent match in: {msg!r}"

    @pytest.mark.parametrize("msg", [
        # True negatives only — none of these contain the pattern strings.
        "git status looks clean",
        "git commit -m fix-something",
        "git add -A",
        "running unit tests now",
        "npm install",
        "npm run build",
        "",
        "git log --oneline -10",
    ])
    def test_no_intent_on_non_push(self, msg):
        assert not sc_mod.INTENT_PATTERN.search(msg), \
            f"Unexpected intent match in: {msg!r}"

    def test_git_commit_not_matched(self):
        assert not sc_mod.INTENT_PATTERN.search("git commit -m 'release v1'")

    def test_git_push_matched(self):
        assert sc_mod.INTENT_PATTERN.search("git push origin main")

    def test_gh_release_create_matched(self):
        assert sc_mod.INTENT_PATTERN.search("gh release create v2.0.0")

    def test_npm_install_not_matched(self):
        assert not sc_mod.INTENT_PATTERN.search("npm install && npm run test")

    def test_python_m_build_matched(self):
        assert sc_mod.INTENT_PATTERN.search("python3 -m build .")

    def test_python_without_m_build_not_matched(self):
        assert not sc_mod.INTENT_PATTERN.search("python3 script.py")


# ═════════════════════════════════════════════════════════════════════════════
# Infinite-loop guard (stop_hook_active)
# ═════════════════════════════════════════════════════════════════════════════

class TestInfiniteLoopGuard:
    def test_stop_hook_active_true_exits_zero(self):
        payload = {
            "stop_hook_active": True,
            "last_assistant_message": "I will git push origin main now",
        }
        code, stdout, _ = run_sc(payload)
        assert code == 0
        assert stdout.strip() == "", "stop_hook_active=true must produce no block output"

    def test_stop_hook_active_false_proceeds(self, tmp_path):
        payload = {
            "stop_hook_active": False,
            "last_assistant_message": "I will git push origin main",
            "tool_input": {"cwd": str(tmp_path)},
        }
        code, stdout, _ = run_sc(payload)
        assert code == 0
        # tmp_path has no deliverables → block decision expected
        if stdout.strip():
            data = json.loads(stdout.strip())
            assert data["decision"] == "block"


# ═════════════════════════════════════════════════════════════════════════════
# Deliverables check
# ═════════════════════════════════════════════════════════════════════════════

class TestDeliverablesCheck:
    def test_empty_dir_all_missing(self, tmp_path):
        missing = sc_mod.check_deliverables(str(tmp_path))
        assert len(missing) > 0, "Empty directory must report missing deliverables"

    def test_all_present_none_missing(self, tmp_path):
        (tmp_path / "README.md").write_text("# Test")
        (tmp_path / "CHANGELOG.md").write_text("## Log")
        (tmp_path / "LICENSE").write_text("MIT")
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "index.html").write_text("<html></html>")

        missing = sc_mod.check_deliverables(str(tmp_path))
        assert missing == [], f"All deliverables present; expected []. Got: {missing}"

    def test_partial_lists_only_missing_ones(self, tmp_path):
        (tmp_path / "README.md").write_text("# Test")
        missing = sc_mod.check_deliverables(str(tmp_path))
        assert "README.md" not in missing
        assert "CHANGELOG.md" in missing

    def test_license_txt_accepted_as_license(self, tmp_path):
        (tmp_path / "README.md").write_text("r")
        (tmp_path / "CHANGELOG.md").write_text("c")
        (tmp_path / "LICENSE.txt").write_text("l")   # alternate name
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "index.html").write_text("<html/>")
        missing = sc_mod.check_deliverables(str(tmp_path))
        assert "LICENSE" not in missing

    def test_custom_deliverables_json_used(self, tmp_path):
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        config = {
            "version": 1,
            "required": [
                {"name": "CUSTOM.md", "glob": "CUSTOM.md", "optional": False},
            ],
        }
        (claude_dir / "deliverables.json").write_text(json.dumps(config))
        missing = sc_mod.check_deliverables(str(tmp_path))
        assert "CUSTOM.md" in missing

    def test_optional_deliverable_not_blocking(self, tmp_path):
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        config = {
            "version": 1,
            "required": [
                {"name": "OPTIONAL.md", "glob": "OPTIONAL.md", "optional": True},
            ],
        }
        (claude_dir / "deliverables.json").write_text(json.dumps(config))
        missing = sc_mod.check_deliverables(str(tmp_path))
        assert "OPTIONAL.md" not in missing, "Optional item must not be counted as missing"

    def test_malformed_deliverables_json_fails_closed(self, tmp_path):
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        (claude_dir / "deliverables.json").write_text("{ not valid json }")
        missing = sc_mod.check_deliverables(str(tmp_path))
        assert len(missing) > 0, "Malformed deliverables.json must fail-closed (non-empty missing)"


# ═════════════════════════════════════════════════════════════════════════════
# X1 git-root resolution (subprocess.run mocked)
# ═════════════════════════════════════════════════════════════════════════════

class TestX1GitRootResolution:
    def test_cwd_field_used_as_git_cwd(self, tmp_path):
        payload = {
            "stop_hook_active": False,
            "tool_input": {
                "cwd": str(tmp_path),
                "command": "git push origin main",
            },
        }
        with mock.patch("subprocess.run") as mock_run:
            mock_run.return_value = mock.Mock(
                returncode=0,
                stdout=str(tmp_path) + "\n",
            )
            sc_mod.find_project_root(payload)
            _, kwargs = mock_run.call_args
            assert kwargs["cwd"] == str(tmp_path), \
                "tool_input.cwd must be passed as cwd to git rev-parse"

    def test_leading_cd_parsed_from_command(self, tmp_path):
        payload = {
            "stop_hook_active": False,
            "tool_input": {"command": f"cd {tmp_path} && git push origin main"},
        }
        with mock.patch("subprocess.run") as mock_run:
            mock_run.return_value = mock.Mock(
                returncode=0,
                stdout=str(tmp_path) + "\n",
            )
            root = sc_mod.find_project_root(payload)
        assert root == str(tmp_path)

    def test_git_rev_parse_failure_falls_back(self, tmp_path):
        payload = {"stop_hook_active": False, "tool_input": {"cwd": str(tmp_path)}}
        with mock.patch("subprocess.run") as mock_run:
            mock_run.return_value = mock.Mock(returncode=1, stdout="")
            root = sc_mod.find_project_root(payload)
        assert root is not None and root != ""

    def test_subprocess_exception_falls_back(self, tmp_path):
        payload = {"stop_hook_active": False, "tool_input": {"cwd": str(tmp_path)}}
        with mock.patch("subprocess.run", side_effect=OSError("git not found")):
            root = sc_mod.find_project_root(payload)
        assert root is not None


# ═════════════════════════════════════════════════════════════════════════════
# Full integration: block decision JSON on stdout
# ═════════════════════════════════════════════════════════════════════════════

class TestBlockDecisionJson:
    def test_missing_deliverables_produce_block_json(self, tmp_path):
        payload = {
            "stop_hook_active": False,
            "last_assistant_message": "I will git push origin main",
            "tool_input": {"cwd": str(tmp_path)},
        }
        code, stdout, _ = run_sc(payload)
        assert code == 0  # Stop hooks signal via JSON, not exit code
        assert stdout.strip(), "Expected block JSON on stdout"
        data = json.loads(stdout.strip())
        assert data["decision"] == "block"
        assert "reason" in data
        assert str(sc_mod.RULE_NUMBER) in data["reason"]

    def test_no_output_when_no_intent(self, tmp_path):
        payload = {
            "stop_hook_active": False,
            "last_assistant_message": "Running the test suite now.",
            "tool_input": {"cwd": str(tmp_path)},
        }
        code, stdout, _ = run_sc(payload)
        assert code == 0
        assert stdout.strip() == "", "No intent → no block output"

    def test_no_output_when_deliverables_present(self, tmp_path):
        (tmp_path / "README.md").write_text("r")
        (tmp_path / "CHANGELOG.md").write_text("c")
        (tmp_path / "LICENSE").write_text("l")
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "index.html").write_text("<html/>")

        payload = {
            "stop_hook_active": False,
            "last_assistant_message": "I will git push origin main",
            "tool_input": {"cwd": str(tmp_path)},
        }
        code, stdout, _ = run_sc(payload)
        assert code == 0
        assert stdout.strip() == "", "All deliverables present → no block output"

    def test_fixture_stop_payload_file(self, tmp_path):
        fixture = FIXTURES / "stop_payload.json"
        payload = json.loads(fixture.read_text(encoding="utf-8"))
        payload["tool_input"] = {"cwd": str(tmp_path)}
        code, stdout, _ = run_sc(payload)
        assert code == 0
        if stdout.strip():
            data = json.loads(stdout.strip())
            assert data["decision"] == "block"
