#!/usr/bin/env bash
# Keep supervisor alive across WSL restarts
# Add to ~/.bashrc: ~/Dominion/scripts/keepalive_supervisor.sh &

set -euo pipefail

PROJECT_ROOT="/home/Martin/Dominion"
SUPERVISOR_SCRIPT="$PROJECT_ROOT/scripts/supervise_tasks.sh"
PIDFILE="$PROJECT_ROOT/logs/supervisor.pid"
LOG_FILE="$PROJECT_ROOT/logs/keepalive.log"

mkdir -p "$PROJECT_ROOT/logs"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" >> "$LOG_FILE"
}

is_supervisor_running() {
    if [ -f "$PIDFILE" ]; then
        local pid=$(cat "$PIDFILE")
        if ps -p "$pid" > /dev/null 2>&1; then
            return 0
        fi
    fi
    return 1
}

start_supervisor() {
    log "Starting supervisor..."
    cd "$PROJECT_ROOT"
    nohup "$SUPERVISOR_SCRIPT" > logs/supervisor_nohup.log 2>&1 &
    local pid=$!
    echo "$pid" > "$PIDFILE"
    log "Supervisor started (PID: $pid)"
}

# Main loop
log "Keepalive started (PID: $$)"

while true; do
    if ! is_supervisor_running; then
        log "⚠ Supervisor not running, restarting..."
        start_supervisor
    fi
    sleep 30
done
