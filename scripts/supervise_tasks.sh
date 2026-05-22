#!/usr/bin/env bash
# Supervisor: Keep Dominion tasks running across WSL disconnects
# Usage: ./supervise_tasks.sh [task_name]
# Logs: logs/supervisor_YYYYMMDD_HHMMSS.log

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_DIR="$PROJECT_ROOT/logs"
mkdir -p "$LOG_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOG_DIR/supervisor_$TIMESTAMP.log"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

check_running() {
    local pattern="$1"
    pgrep -f "$pattern" > /dev/null 2>&1
}

# Detect running tasks
detect_tasks() {
    log "Detecting running tasks..."

    TASKS=()

    # Check for feature expansion (expand_features_3k_turbo.py or orphaned workers)
    if check_running "expand_features_3k_turbo.py"; then
        TASKS+=("feature_expansion")
        log "✓ Feature expansion detected (expand_features_3k_turbo.py)"
    elif pgrep -f "LokyProcess.*joblib" > /dev/null 2>&1; then
        TASKS+=("feature_expansion_orphan")
        log "⚠ Orphaned feature workers detected (parent died)"
    fi

    # Check for master dataset build (build_master_extended.py)
    if check_running "build_master_extended.py"; then
        TASKS+=("master_dataset")
        log "✓ Master dataset build detected (build_master_extended.py)"
    fi

    # Check for training runs
    if check_running "run_training_final.py"; then
        TASKS+=("training")
        log "✓ Training detected (run_training_final.py)"
    fi

    # Check for overnight jobs
    if check_running "overnight_build.sh"; then
        TASKS+=("overnight_build")
        log "✓ Overnight build detected"
    fi

    # Check for RAGD MCP server
    if check_running "ragd_mcp_stdio.py"; then
        TASKS+=("ragd_mcp")
        log "✓ RAGD MCP server detected"
    fi

    if [ ${#TASKS[@]} -eq 0 ]; then
        log "⚠ No active tasks detected"
        return 1
    fi

    log "Total tasks: ${#TASKS[@]}"
    return 0
}

# Monitor loop
monitor_tasks() {
    log "Starting supervisor (PID: $$)"
    log "Log: $LOG_FILE"
    log "Press Ctrl+C to stop supervisor (tasks continue)"

    INTERVAL=10  # Check every 10 seconds

    while true; do
        ALL_DONE=true

        for task in "${TASKS[@]}"; do
            case "$task" in
                feature_expansion)
                    if check_running "expand_features_3k_turbo.py"; then
                        log "⏳ Feature expansion running..."
                        ALL_DONE=false
                    else
                        log "✅ Feature expansion complete"
                    fi
                    ;;
                feature_expansion_orphan)
                    if pgrep -f "LokyProcess.*joblib" > /dev/null 2>&1; then
                        log "⚠ Orphaned workers still alive (killing)"
                        pkill -f "LokyProcess"
                        sleep 2
                        ALL_DONE=false
                    else
                        log "✅ Orphaned workers cleaned up"
                    fi
                    ;;
                master_dataset)
                    if check_running "build_master_extended.py"; then
                        log "⏳ Master dataset build running..."
                        ALL_DONE=false
                    else
                        log "✅ Master dataset build complete"
                    fi
                    ;;
                training)
                    if check_running "run_training_final.py"; then
                        log "⏳ Training running..."
                        ALL_DONE=false
                    else
                        log "✅ Training complete"
                    fi
                    ;;
                overnight_build)
                    if check_running "overnight_build.sh"; then
                        log "⏳ Overnight build running..."
                        ALL_DONE=false
                    else
                        log "✅ Overnight build complete"
                    fi
                    ;;
                ragd_mcp)
                    if check_running "ragd_mcp_stdio.py"; then
                        log "⏳ RAGD MCP server running..."
                        ALL_DONE=false
                    else
                        log "⚠ RAGD MCP server stopped (may need restart)"
                    fi
                    ;;
            esac
        done

        if $ALL_DONE; then
            log "🎉 All tasks complete"
            break
        fi

        sleep "$INTERVAL"
    done

    log "Supervisor exiting"
}

# Main
trap 'log "Supervisor interrupted (tasks continue)"; exit 0' INT TERM

if ! detect_tasks; then
    log "No tasks to supervise. Exiting."
    exit 1
fi

monitor_tasks
