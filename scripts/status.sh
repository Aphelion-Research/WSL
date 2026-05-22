#!/usr/bin/env bash
# Quick status check for Dominion supervision

set -uo pipefail  # Remove -e to allow stat failures

echo "═══════════════════════════════════════════════════════"
echo "🔍 Dominion Task Supervision Status"
echo "═══════════════════════════════════════════════════════"
echo

# Keepalive
echo "📦 Keepalive:"
if pgrep -f keepalive_supervisor.sh > /dev/null; then
    pid=$(pgrep -f keepalive_supervisor.sh)
    echo "  ✅ Running (PID: $pid)"
else
    echo "  ❌ Not running"
fi
echo

# Supervisor
echo "📋 Supervisor:"
if pgrep -f supervise_tasks.sh > /dev/null; then
    pid=$(pgrep -f supervise_tasks.sh)
    echo "  ✅ Running (PID: $pid)"
    echo "  📄 Latest log: logs/supervisor_nohup.log"
    echo
    echo "  Last 5 lines:"
    tail -5 logs/supervisor_nohup.log 2>/dev/null | sed 's/^/    /' || echo "    (log empty)"
else
    echo "  ❌ Not running"
fi
echo

# Tasks
echo "🔧 Active Tasks:"
TASK_COUNT=0

if pgrep -f "ragd_mcp_stdio.py" > /dev/null; then
    echo "  ✅ RAGD MCP server"
    ((TASK_COUNT++))
fi

if pgrep -f "expand_features_3k_turbo.py" > /dev/null; then
    echo "  ✅ Feature expansion (expand_features_3k_turbo.py)"
    ((TASK_COUNT++))
fi

if pgrep -f "build_master_extended.py" > /dev/null; then
    echo "  ✅ Master dataset build (build_master_extended.py)"
    ((TASK_COUNT++))
fi

if pgrep -f "run_training_final.py" > /dev/null; then
    echo "  ✅ Training run (run_training_final.py)"
    ((TASK_COUNT++))
fi

if pgrep -f "overnight_build.sh" > /dev/null; then
    echo "  ✅ Overnight build"
    ((TASK_COUNT++))
fi

if pgrep -f "LokyProcess" > /dev/null; then
    count=$(pgrep -f "LokyProcess" | wc -l)
    echo "  ⚠️  Orphaned workers (LokyProcess: $count)"
    ((TASK_COUNT++))
fi

if [ $TASK_COUNT -eq 0 ]; then
    echo "  ℹ️  No tasks running"
fi
echo

# Datasets
echo "💾 Recent Outputs:"
if [ -f "data/hydra_xauusd_m5_3k.parquet" ]; then
    size=$(du -h data/hydra_xauusd_m5_3k.parquet | cut -f1)
    modified=$(stat -c %y data/hydra_xauusd_m5_3k.parquet | cut -d' ' -f1,2 | cut -d'.' -f1)
    echo "  ✅ hydra_xauusd_m5_3k.parquet ($size, $modified)"
fi

if [ -f "data/hydra_xauusd_m5_master.parquet" ]; then
    size=$(du -h data/hydra_xauusd_m5_master.parquet | cut -f1)
    modified=$(stat -c %y data/hydra_xauusd_m5_master.parquet | cut -d' ' -f1,2 | cut -d'.' -f1)
    echo "  ✅ hydra_xauusd_m5_master.parquet ($size, $modified)"
fi

echo
echo "═══════════════════════════════════════════════════════"
echo
echo "📚 Commands:"
echo "  View logs:  tail -f logs/supervisor_nohup.log"
echo "  Stop all:   pkill -f keepalive_supervisor.sh"
echo "  Restart:    pkill -f supervise_tasks.sh"
echo "  Full docs:  cat docs/SUPERVISION.md"
