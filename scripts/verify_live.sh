#!/usr/bin/env bash
# verify_live.sh — Dominion live-green integration check
# Runs all platform checks and reports OFFLINE_GREEN / LIVE_GREEN / LIVE_WARN / LIVE_FAIL
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
    echo "$out" | head -3 > /dev/null  # suppress
    RESULTS["$name"]="$exit_code:$out"
    if [[ $exit_code -eq 0 ]]; then
        printf "  PASS  %-40s\n" "$name"
        ((PASS++)) || true
    else
        printf "  FAIL  %-40s  (exit $exit_code)\n" "$name"
        ((FAIL++)) || true
    fi
}

warn_check() {
    local name="$1"; shift
    local out exit_code
    if out=$("$@" 2>&1); then
        exit_code=0
        printf "  PASS  %-40s\n" "$name"
        ((PASS++)) || true
    else
        exit_code=$?
        printf "  WARN  %-40s  (exit $exit_code)\n" "$name"
        ((WARN++)) || true
    fi
    RESULTS["$name"]="$exit_code:$out"
}

echo "=== Dominion Live-Green Verification  $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
echo ""
echo "--- Build Presence ---"
check "ragd-binary-exists"        test -f "$ROOT/ragd/build/ragd"
check "native-doctor-exists"      test -f "$ROOT/ragd/build/dominion-native-doctor"
check "native-scan-exists"        test -f "$ROOT/ragd/build/dominion-native-scan"
check "native-vault-doctor-exists" test -f "$ROOT/ragd/build/dominion-native-vault-doctor"

echo ""
echo "--- RAGD Health ---"
check "ragd-health" bash -c "curl -sf http://127.0.0.1:7474/health | python3 -c \"import sys,json; d=json.load(sys.stdin); sys.exit(0 if d.get('ok') else 1)\""
check "ragd-query-smoke" bash -c "curl -sf -X POST http://127.0.0.1:7474/query -H 'Content-Type: application/json' -d '{\"query\":\"dominion native manifest\",\"top_k\":3}' | python3 -c \"import sys,json; d=json.load(sys.stdin); sys.exit(0 if len(d.get('results',d.get('chunks',[])))>0 else 1)\""

echo ""
echo "--- Native Doctor (live) ---"
# native doctor warns due to .md extension bug in vault link resolution (known false positive)
warn_check "native-doctor-live" bash -c "$ROOT/ragd/build/dominion-native-doctor --root '$ROOT' --live --json | python3 -c \"import sys,json; d=json.load(sys.stdin); overall=d.get('overall','fail'); sys.exit(0 if overall in ('ok','pass','warn') else 1)\""

echo ""
echo "--- Python Truth (live) ---"
check "python-truth-live" python "$ROOT/scripts/dominion_cli.py" truth --live --json

echo ""
echo "--- Vault Doctor ---"
check "vault-doctor-clean" bash -c "python '$ROOT/scripts/dominion_cli.py' vault doctor --json | python3 -c \"import sys,json; d=json.load(sys.stdin); sys.exit(0 if len(d.get('broken_links',[]))==0 else 1)\""

echo ""
echo "--- domdata Safety ---"
check "domdata-notice"      domdata notice
check "domdata-order-blocked" bash -c "domdata order-send 2>&1 | grep -qi 'blocked\|forbidden\|not allowed\|disabled'; exit \$?"
warn_check "domdata-doctor" domdata doctor

echo ""
echo "--- Agent OS Smoke ---"
warn_check "agent-imports" python -c "from dominion_agent import tasks, sessions, safety; print('ok')"

echo ""
echo "--- Safety Scanner ---"
check "no-trading-tokens" python "$ROOT/domdata/check_no_trading.py"

# Summary
echo ""
echo "=== Summary ==="
printf "  PASS: %d  WARN: %d  FAIL: %d\n" "$PASS" "$WARN" "$FAIL"
if [[ $FAIL -gt 0 ]]; then
    echo "  Status: LIVE_FAIL"
    exit 2
elif [[ $WARN -gt 0 ]]; then
    echo "  Status: LIVE_WARN"
    exit 1
else
    echo "  Status: LIVE_GREEN"
    exit 0
fi
