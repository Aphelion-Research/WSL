# Task Supervision System

Auto-supervises Dominion tasks across WSL disconnects.

---

## Architecture

```
keepalive_supervisor.sh (PID in logs/supervisor.pid)
  └─ supervise_tasks.sh (monitors actual tasks)
       ├─ RAGD MCP server (ragd_mcp_stdio.py)
       ├─ Feature expansion (expand_features_3k_turbo.py)
       ├─ Master dataset builds (build_master_*.py)
       ├─ Training runs (run_training_*.py)
       └─ Overnight jobs (overnight_*.sh)
```

**Keepalive:** Restarts supervisor if it dies (checks every 30s)  
**Supervisor:** Monitors tasks, logs progress (checks every 10s)

---

## Status

### Check running processes
```bash
ps aux | grep -E 'keepalive|supervise_tasks|ragd_mcp' | grep -v grep
```

### Check logs
```bash
tail -f logs/keepalive.log         # Keepalive restarts
tail -f logs/supervisor_nohup.log  # Current supervisor output
ls -lt logs/supervisor_*.log       # Individual supervisor runs
```

### Check supervised tasks
```bash
ps aux | grep -E 'expand_features|build_master|training|overnight|ragd' | grep -v grep
```

---

## Manual Control

### Start supervision (auto-starts on WSL login via ~/.bashrc)
```bash
~/Dominion/scripts/keepalive_supervisor.sh &
```

### Stop supervision
```bash
# Stop keepalive (supervisor continues)
pkill -f keepalive_supervisor.sh

# Stop supervisor (tasks continue)
pkill -f supervise_tasks.sh

# Stop both (tasks continue)
pkill -f keepalive_supervisor.sh && pkill -f supervise_tasks.sh
```

### Restart supervisor
```bash
pkill -f supervise_tasks.sh  # Keepalive auto-restarts within 30s
```

---

## Logs

- `logs/keepalive.log` → Keepalive events (supervisor restarts)
- `logs/keepalive_nohup.log` → Keepalive stdout/stderr
- `logs/supervisor_nohup.log` → Latest supervisor stdout/stderr
- `logs/supervisor_YYYYMMDD_HHMMSS.log` → Individual supervisor runs

---

## Task Detection

Supervisor auto-detects running tasks by scanning for:

| Task | Detection Pattern | Output Check |
|------|------------------|--------------|
| Feature expansion | `expand_features_3k_turbo.py` | `data/hydra_xauusd_m5_3k.parquet` |
| Master dataset | `build_master_extended.py` | `data/hydra_xauusd_m5_master.parquet` |
| Training | `run_training_final.py` | `models/` directory |
| Overnight jobs | `overnight_build.sh` | Various outputs |
| RAGD MCP | `ragd_mcp_stdio.py` | Always running |

---

## Auto-Start

Keepalive auto-starts on WSL login via `~/.bashrc`:

```bash
# Auto-start Dominion supervisor keepalive
pgrep -f keepalive_supervisor.sh > /dev/null 2>&1 || ~/Dominion/scripts/keepalive_supervisor.sh &
```

Disabled by commenting out this line.

---

## Edge Cases

### Orphaned workers
If parent script dies but workers (LokyProcess, multiprocessing) survive:

```bash
# Supervisor auto-kills orphaned workers
# Manual cleanup:
pkill -f LokyProcess
pkill -f multiprocessing
```

### Dual supervisors
If keepalive spawns duplicate supervisors:

```bash
# Kill old supervisors (keep highest PID)
ps aux | grep supervise_tasks.sh | grep -v grep
kill <old_pid>
```

### WSL freeze/disconnect
Supervisor + tasks continue running. Reconnect:

```bash
# Check if alive
ps aux | grep -E 'keepalive|supervise' | grep -v grep

# View logs
tail -f logs/supervisor_nohup.log
```

---

## Future Improvements

- [ ] Slack/email alerts on task completion
- [ ] Web dashboard (Flask/FastAPI)
- [ ] Task prioritization (nice/ionice)
- [ ] Auto-retry failed tasks
- [ ] Resource limits (cgroups)
- [ ] tmux integration (one task per pane)

---

## Contact

**Owners:** Matin, Dan  
**Sessions:** `tmux ls` (ragd, dominion, ssh)  
**Logs:** `logs/` directory
