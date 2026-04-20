"""Tests for the hardgate gate.py template (SKILL.md Artifact 1).

Covers:
- Tokenizer: verb extraction, env-var stripping, wrapper stripping, path prefixes
- Shell -c bypass recursion at depth 1 and 2, depth cap (MAX_SHELL_C_DEPTH)
- Inline-code interpreter matrix: all 9 flag/interpreter combinations
- Fail-open on outer JSON parse errors
- ENG-001: fail-closed on inner -c shlex.split() failures
- X4 override marker: fresh bypass, expired block+delete, corrupt silent-delete
"""
import json
import os
import pathlib
import subprocess
import sys
import time

import pytest

# ── fixture paths ─────────────────────────────────────────────────────────────

FIXTURES = pathlib.Path(__file__).parent / "fixtures"
GATE_PY = FIXTURES / "gate.py"

# Import fixture module for unit tests (functions directly, not subprocess)
sys.path.insert(0, str(FIXTURES))
import gate as gate_mod  # noqa: E402  (after sys.path manipulation)

# ── subprocess helpers ────────────────────────────────────────────────────────


def run_gate(cmd: str, env: dict = None) -> tuple:
    """Run gate.py with a Bash payload containing cmd. Returns (exit_code, stdout, stderr)."""
    payload = {"tool_name": "Bash", "tool_input": {"command": cmd}}
    return _run_raw(json.dumps(payload), env)


def _run_raw(stdin: str, env: dict = None) -> tuple:
    result = subprocess.run(
        [sys.executable, str(GATE_PY)],
        input=stdin,
        capture_output=True,
        text=True,
        env=env if env is not None else os.environ.copy(),
    )
    return result.returncode, result.stdout, result.stderr


# ═════════════════════════════════════════════════════════════════════════════
# Tokenizer — verb extraction
# ═════════════════════════════════════════════════════════════════════════════

class TestVerbExtraction:
    def test_simple_forbidden(self):
        assert gate_mod.is_forbidden("cat README.md")

    def test_simple_allowed(self):
        assert not gate_mod.is_forbidden("git add .")

    def test_empty_command(self):
        assert not gate_mod.is_forbidden("")

    def test_whitespace_only(self):
        assert not gate_mod.is_forbidden("   ")

    def test_forbidden_after_ampersand_ampersand(self):
        assert gate_mod.is_forbidden("git status && cat README.md")

    def test_forbidden_after_semicolon(self):
        assert gate_mod.is_forbidden("echo hello; grep foo bar.txt")

    def test_forbidden_after_pipe(self):
        assert gate_mod.is_forbidden("echo foo | grep pattern")

    def test_forbidden_after_or_or(self):
        assert gate_mod.is_forbidden("git diff || grep something file")

    def test_allowed_pipeline(self):
        assert not gate_mod.is_forbidden("git add . && git commit -m 'msg'")

    def test_all_forbidden_verbs_detected(self):
        for verb in gate_mod.FORBIDDEN:
            assert gate_mod.is_forbidden(f"{verb} somefile"), \
                f"Verb '{verb}' should be in FORBIDDEN set"


# ═════════════════════════════════════════════════════════════════════════════
# Tokenizer — env-var stripping
# ═════════════════════════════════════════════════════════════════════════════

class TestEnvVarStripping:
    def test_single_env_var_before_forbidden(self):
        tokens = gate_mod.strip_wrappers(["FOO=bar", "cat", "file.txt"])
        assert tokens[0] == "cat"

    def test_multiple_env_vars(self):
        tokens = gate_mod.strip_wrappers(["A=1", "B=2", "grep", "pattern"])
        assert tokens[0] == "grep"

    def test_env_var_empty_value(self):
        tokens = gate_mod.strip_wrappers(["DEBUG=", "cat", "file"])
        assert tokens[0] == "cat"

    def test_no_env_var_untouched(self):
        tokens = gate_mod.strip_wrappers(["git", "status"])
        assert tokens[0] == "git"

    def test_env_var_before_allowed_verb(self):
        tokens = gate_mod.strip_wrappers(["VERBOSE=1", "git", "push"])
        assert tokens[0] == "git"

    def test_env_var_integration(self):
        assert gate_mod.is_forbidden("DEBUG=1 cat README.md")


# ═════════════════════════════════════════════════════════════════════════════
# Tokenizer — wrapper stripping
# ═════════════════════════════════════════════════════════════════════════════

class TestWrapperStripping:
    @pytest.mark.parametrize("wrapper", sorted(gate_mod.WRAPPERS))
    def test_each_wrapper_before_forbidden(self, wrapper):
        assert gate_mod.is_forbidden(f"{wrapper} cat README.md"), \
            f"'{wrapper} cat ...' should be blocked"

    def test_nested_wrappers(self):
        assert gate_mod.is_forbidden("sudo env cat README.md")

    def test_wrapper_before_allowed_passes(self):
        assert not gate_mod.is_forbidden("sudo git status")

    def test_env_var_then_wrapper_then_forbidden(self):
        assert gate_mod.is_forbidden("A=1 sudo cat file.txt")


# ═════════════════════════════════════════════════════════════════════════════
# Tokenizer — path prefix stripping
# ═════════════════════════════════════════════════════════════════════════════

class TestPathPrefixStripping:
    def test_absolute_path_forbidden(self):
        assert gate_mod.is_forbidden("/usr/bin/cat README.md")

    def test_usr_local_bin(self):
        assert gate_mod.is_forbidden("/usr/local/bin/grep pattern file.txt")

    def test_relative_path_prefix(self):
        assert gate_mod.is_forbidden("./cat README.md")

    def test_absolute_path_allowed(self):
        assert not gate_mod.is_forbidden("/usr/bin/git status")

    def test_path_prefixed_wrapper_then_forbidden(self):
        # /usr/bin/sudo → sudo → stripped; then cat → blocked
        assert gate_mod.is_forbidden("/usr/bin/sudo cat README.md")


# ═════════════════════════════════════════════════════════════════════════════
# Shell -c bypass detection
# ═════════════════════════════════════════════════════════════════════════════

class TestShellCBypass:
    @pytest.mark.parametrize("interp", sorted(gate_mod.SHELL_INTERPRETERS))
    def test_each_interpreter_depth1_forbidden(self, interp):
        assert gate_mod.is_forbidden(f"{interp} -c 'cat README.md'"), \
            f"'{interp} -c cat ...' should be blocked"

    @pytest.mark.parametrize("interp", sorted(gate_mod.SHELL_INTERPRETERS))
    def test_each_interpreter_depth1_allowed(self, interp):
        assert not gate_mod.is_forbidden(f"{interp} -c 'git status'"), \
            f"'{interp} -c git status' should pass"

    def test_depth2_forbidden(self):
        assert gate_mod.is_forbidden("sh -c 'bash -c \"cat README.md\"'")

    def test_depth2_allowed(self):
        assert not gate_mod.is_forbidden("sh -c 'bash -c \"git status\"'")

    def test_depth_cap_fails_closed(self):
        # Calling check_tokens at exactly MAX_SHELL_C_DEPTH must return True
        # regardless of what follows — depth cap is fail-closed.
        result = gate_mod.check_tokens(
            ["sh", "-c", "bash -c 'git status'"],
            depth=gate_mod.MAX_SHELL_C_DEPTH,
        )
        assert result is True, (
            f"At depth={gate_mod.MAX_SHELL_C_DEPTH} the gate must fail-closed "
            f"(return True). Got False."
        )

    def test_depth_cap_constant_is_2(self):
        assert gate_mod.MAX_SHELL_C_DEPTH == 2

    # ENG-001 — Blocker: fail-closed on unparseable inner -c argument
    def test_eng001_unparseable_inner_c_blocked(self):
        """
        ENG-001 (Blocker): when shlex.split() raises ValueError on the inner
        -c argument (e.g. unclosed quote), the gate must fail-closed and return
        True (blocked). A fail-open implementation returns False.

        This test documents the required behaviour. The corresponding fix to the
        SKILL.md template code ships in the next PR with this test already
        waiting.
        """
        result = gate_mod.check_tokens(["bash", "-c", "cat 'unclosed"])
        assert result is True, (
            "ENG-001: unparseable inner -c must fail-closed (True). "
            "Got False — gate is fail-open on malformed shell -c arguments."
        )

    def test_missing_inner_arg_passes(self):
        # bash -c with no argument is not forbidden (nothing to analyse)
        assert not gate_mod.is_forbidden("bash -c")


# ═════════════════════════════════════════════════════════════════════════════
# Inline-code interpreter blocking
# ═════════════════════════════════════════════════════════════════════════════

class TestInlineCodeBlocking:
    @pytest.mark.parametrize("interp,flag,code", [
        # Code strings must contain no embedded single-quotes or semicolons —
        # split_pipeline is regex-based and does not respect quoting, so
        # embedded chars would corrupt the shlex.split step.
        ("python",  "-c",     "import sys"),
        ("python2", "-c",     "import sys"),
        ("python3", "-c",     "import sys"),
        ("perl",    "-e",     "print 42"),
        ("ruby",    "-e",     "puts 42"),
        ("node",    "-e",     "process.exit()"),
        ("node",    "--eval", "process.exit()"),
        ("deno",    "eval",   "console.log(1)"),
        ("php",     "-r",     "phpinfo()"),
    ])
    def test_inline_code_blocked(self, interp, flag, code):
        cmd = f"{interp} {flag} '{code}'"
        assert gate_mod.is_forbidden(cmd), f"Expected {cmd!r} to be blocked"

    def test_script_file_invocation_allowed(self):
        # Running a named script file is not an inline-code invocation
        assert not gate_mod.is_forbidden("python3 script.py")
        assert not gate_mod.is_forbidden("node app.js")
        assert not gate_mod.is_forbidden("perl myscript.pl")

    def test_script_interpreter_set_complete(self):
        expected = {"python", "python2", "python3", "perl", "ruby", "node", "deno", "php"}
        assert set(gate_mod.SCRIPT_INTERPRETERS.keys()) == expected


# ═════════════════════════════════════════════════════════════════════════════
# JSON parse error handling (stdin → subprocess)
# ═════════════════════════════════════════════════════════════════════════════

class TestJsonParsing:
    def test_fail_open_on_malformed_json(self):
        code, _, _ = _run_raw("not valid json at all {{{")
        assert code == 0, f"Malformed outer JSON must exit 0 (fail-open), got {code}"

    def test_fail_open_on_empty_stdin(self):
        code, _, _ = _run_raw("")
        assert code == 0

    def test_non_bash_tool_passes_through(self):
        payload = {"tool_name": "Read", "tool_input": {"file_path": "/etc/passwd"}}
        code, _, _ = _run_raw(json.dumps(payload))
        assert code == 0

    def test_bash_tool_forbidden_exits_2(self):
        code, _, stderr = run_gate("cat README.md")
        assert code == 2
        assert "HARD-RULE" in stderr

    def test_bash_tool_allowed_exits_0(self):
        code, _, _ = run_gate("git status")
        assert code == 0

    def test_fixture_payload_file_blocked(self):
        fixture = FIXTURES / "pretooluse_payload.json"
        payload_text = fixture.read_text(encoding="utf-8")
        code, _, stderr = _run_raw(payload_text)
        assert code == 2
        assert "HARD-RULE" in stderr


# ═════════════════════════════════════════════════════════════════════════════
# X4 override marker
# ═════════════════════════════════════════════════════════════════════════════

class TestOverrideMarker:
    def _marker(self, tmp_path: pathlib.Path) -> pathlib.Path:
        d = tmp_path / ".claude"
        d.mkdir(exist_ok=True)
        return d / f"hardgate-override-rule-{gate_mod.RULE_NUMBER}"

    def _env(self, tmp_path: pathlib.Path) -> dict:
        e = os.environ.copy()
        e["CLAUDE_PROJECT_DIR"] = str(tmp_path)
        return e

    def test_fresh_marker_bypasses_gate(self, tmp_path):
        self._marker(tmp_path).write_text(str(time.time()))
        code, _, stderr = run_gate("cat README.md", env=self._env(tmp_path))
        assert code == 0, "Fresh marker (<60s) must bypass the gate"
        assert "bypass granted" in stderr.lower() or "one-time" in stderr.lower()

    def test_fresh_marker_consumed_after_use(self, tmp_path):
        marker = self._marker(tmp_path)
        marker.write_text(str(time.time()))
        run_gate("cat README.md", env=self._env(tmp_path))
        assert not marker.exists(), "Marker must be deleted after a successful bypass"

    def test_expired_marker_does_not_bypass(self, tmp_path):
        # Write a timestamp 120 s in the past
        self._marker(tmp_path).write_text(str(time.time() - 120))
        code, _, _ = run_gate("cat README.md", env=self._env(tmp_path))
        assert code == 2, "Expired marker must not bypass; gate should block"

    def test_expired_marker_deleted(self, tmp_path):
        marker = self._marker(tmp_path)
        marker.write_text(str(time.time() - 120))
        run_gate("cat README.md", env=self._env(tmp_path))
        assert not marker.exists(), "Expired marker must be deleted"

    def test_corrupt_marker_does_not_bypass(self, tmp_path):
        self._marker(tmp_path).write_text("not-a-float")
        code, _, stderr = run_gate("cat README.md", env=self._env(tmp_path))
        assert code == 2, "Corrupt marker must not bypass"

    def test_corrupt_marker_deleted_silently(self, tmp_path):
        marker = self._marker(tmp_path)
        marker.write_text("not-a-float")
        _, _, stderr = run_gate("cat README.md", env=self._env(tmp_path))
        assert not marker.exists(), "Corrupt marker must be deleted"
        assert "traceback" not in stderr.lower(), "Corrupt marker must not produce a traceback"
