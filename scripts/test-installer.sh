#!/usr/bin/env bash
# Exercise hardgate's install.sh end-to-end against an isolated fake HOME.
set -euo pipefail

REPO_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
ZIP="$REPO_ROOT/dist/hardgate-v1.0.1.zip"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

PASS=0; FAIL=0
pass() { echo "  [PASS] $*"; PASS=$((PASS+1)); }
fail() { echo "  [FAIL] $*"; FAIL=$((FAIL+1)); }

echo "=== TEST 1: zip integrity ==="
unzip -qq -t "$ZIP" && pass "zip CRC ok" || fail "zip corrupt"

echo
echo "=== TEST 2: install.sh happy path ==="
unzip -qq "$ZIP" -d "$WORK"
EXTRACTED="$WORK/hardgate-v1.0.1"
[ -d "$EXTRACTED" ] && pass "extracted directory exists" || fail "missing extracted dir"
chmod +x "$EXTRACTED/install.sh"

FAKE_HOME="$WORK/home"
mkdir -p "$FAKE_HOME"
set +e
(
  cd "$EXTRACTED"
  HOME="$FAKE_HOME" bash ./install.sh
) > "$WORK/install1.log" 2>&1
RC=$?
set -e
[ "$RC" = "0" ] && pass "install.sh exit 0 (happy path)" || fail "install.sh exit $RC"

for rel in \
  ".claude/skills/hard-gate-installer/SKILL.md" \
  ".claude/commands/hard-gate.md" \
  ".claude/commands/disable-gate.md"
do
  if [ -f "$FAKE_HOME/$rel" ]; then pass "installed $rel"
  else fail "missing $rel"
  fi
done

# sha256 comparison
for pair in \
  "SKILL.md:.claude/skills/hard-gate-installer/SKILL.md" \
  "hard-gate.md:.claude/commands/hard-gate.md" \
  "disable-gate.md:.claude/commands/disable-gate.md"
do
  SRC="${pair%%:*}"
  DST="${pair##*:}"
  SH_A="$(sha256sum "$REPO_ROOT/$SRC" | awk '{print $1}')"
  SH_B="$(sha256sum "$FAKE_HOME/$DST" | awk '{print $1}')"
  if [ "$SH_A" = "$SH_B" ]; then pass "sha256 match for $SRC"
  else fail "sha256 mismatch for $SRC ($SH_A vs $SH_B)"
  fi
done

echo
echo "=== TEST 3: re-run creates .bak-* ==="
echo "SENTINEL_MODIFIED" > "$FAKE_HOME/.claude/commands/hard-gate.md"
sleep 1
set +e
(
  cd "$EXTRACTED"
  HOME="$FAKE_HOME" bash ./install.sh
) > "$WORK/install2.log" 2>&1
set -e
BAKS="$(ls "$FAKE_HOME/.claude/commands/"hard-gate.md.bak-* 2>/dev/null | wc -l)"
[ "$BAKS" -ge "1" ] && pass "backup file created ($BAKS)" || fail "no backup created"
BAK_FILE="$(ls "$FAKE_HOME/.claude/commands/"hard-gate.md.bak-* 2>/dev/null | head -1)"
if [ -n "$BAK_FILE" ] && grep -q SENTINEL_MODIFIED "$BAK_FILE"; then
  pass "backup preserved modified content"
else
  fail "backup did not contain SENTINEL_MODIFIED"
fi
if grep -q "Load and follow" "$FAKE_HOME/.claude/commands/hard-gate.md"; then
  pass "reinstalled file has real content"
else
  fail "reinstalled file content wrong"
fi

echo
echo "=== TEST 4: refuses when sources missing (exit 2) ==="
BARE="$WORK/bare"
mkdir -p "$BARE"
cp "$EXTRACTED/install.sh" "$BARE/install.sh"
chmod +x "$BARE/install.sh"
set +e
(
  cd "$BARE"
  HOME="$FAKE_HOME" bash ./install.sh
) > "$WORK/install3.log" 2>&1
RC=$?
set -e
[ "$RC" = "2" ] && pass "refused with exit 2" || fail "expected exit 2, got $RC"
grep -qi missing "$WORK/install3.log" && pass "error message mentions 'missing'" || fail "no 'missing' in stderr"

echo
echo "=============================================="
echo "  Results: PASS=$PASS  FAIL=$FAIL"
echo "=============================================="
exit "$FAIL"
