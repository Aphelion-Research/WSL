#!/usr/bin/env bash
# verify_source.sh — Dominion source-only gate (no live services required)
#
# Checks:
#   1. Python syntax/compile — repo-owned source directories only
#   2. Default pytest suite (unit tests, no integration marker)
#   3. domdata forbidden-token safety scanner
#   4. Lightweight smoke tests from verify_live.sh that do not need live services
#
# Explicitly excludes: .venv, __pycache__, .pytest_cache, .git, build, dist,
#   data/, tmp/, vault/files/, vault/symbols/, apps/mt5*, wine prefixes,
#   generated databases, generated market data, and binary archives.
#
# Exit codes: 0 = SOURCE_GREEN, 1 = SOURCE_WARN, 2 = SOURCE_FAIL

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PASS=0; WARN=0; FAIL=0
declare -A RESULTS

check() {
    local name="$1"; shift
    local out exit_code
    if out=$("$@" 2>&1); then
        exit_code=0
    else
        exit_code=$?
    fi
    RESULTS["$name"]="$exit_code"
    if [[ $exit_code -eq 0 ]]; then
        printf "  PASS  %-50s\n" "$name"
        ((PASS++)) || true
    else
        printf "  FAIL  %-50s  (exit $exit_code)\n" "$name"
        printf "        %s\n" "$(echo "$out" | tail -5)"
        ((FAIL++)) || true
    fi
}

warn_check() {
    local name="$1"; shift
    local out exit_code
    if out=$("$@" 2>&1); then
        exit_code=0
        printf "  PASS  %-50s\n" "$name"
        ((PASS++)) || true
    else
        exit_code=$?
        printf "  WARN  %-50s  (exit $exit_code)\n" "$name"
        printf "        %s\n" "$(echo "$out" | tail -3)"
        ((WARN++)) || true
    fi
    RESULTS["$name"]="$exit_code"
}

echo "=== Dominion Source-Only Verification  $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
echo "(No live services required)"
echo ""

# ---------------------------------------------------------------------------
echo "--- Python Syntax (source roots only) ---"
check "compile-source" python "$ROOT/scripts/compile_source.py"

# ---------------------------------------------------------------------------
echo ""
echo "--- Safety Scanner ---"
check "no-trading-tokens" python "$ROOT/domdata/check_no_trading.py"

# ---------------------------------------------------------------------------
echo ""
echo "--- Unit Tests (pytest, no integration) ---"
# pytest.ini already sets: -m "not integration" and testpaths to source packages
check "pytest-unit" python -m pytest -q --tb=short

# ---------------------------------------------------------------------------
echo ""
echo "--- Lightweight Smoke (no live services) ---"

# domdata CLI — offline checks that do not require MT5/RAGD
check  "domdata-notice"         domdata notice
check  "domdata-order-blocked"  bash -c "domdata order-send 2>&1 | grep -qi 'blocked\|forbidden\|not allowed\|disabled'"

# Agent OS imports (pure Python, no network)
warn_check "agent-imports" python -c \
    "from dominion_agent import tasks, sessions, safety; print('ok')"

# ragd binary presence (build artifact gate)
warn_check "ragd-binary-exists"  test -f "$ROOT/ragd/build/ragd"
warn_check "native-scan-exists"  test -f "$ROOT/ragd/build/dominion-native-scan"

# ---------------------------------------------------------------------------
echo ""
echo "=== Summary ==="
printf "  PASS: %d  WARN: %d  FAIL: %d\n" "$PASS" "$WARN" "$FAIL"
if [[ $FAIL -gt 0 ]]; then
    echo "  Status: SOURCE_FAIL"
    exit 2
elif [[ $WARN -gt 0 ]]; then
    echo "  Status: SOURCE_WARN"
    exit 1
else
    echo "  Status: SOURCE_GREEN"
    exit 0
fi
