# CLI Reference

**Status:** LIVE_GREEN (Production CLI)  
**Last Updated:** 2026-05-19  
**Owner:** MatinDeevv  
**Command:** `dominion` (alias for `python scripts/dominion_cli.py`)

---

## Overview

Dominion CLI provides unified interface to all subsystems:
- **doctor** — health checks
- **agent** — Agent OS operations
- **truth** — full system report
- **scan** — file ingestion
- **ragd** — RAGD management
- **data** — data pipeline
- **lob** — LOB reconstruction
- **sim** — execution simulator
- **tca** — trade cost analysis
- **toxicity** — order flow toxicity

---

## Installation

Add alias to `~/.bashrc` or `~/.zshrc`:

```bash
alias dominion='python ~/Dominion/scripts/dominion_cli.py'
```

Or create symlink:

```bash
ln -s ~/Dominion/scripts/dominion_cli.py ~/bin/dominion
chmod +x ~/bin/dominion
```

---

## Global Options

```
dominion [COMMAND] [OPTIONS]
```

**Help:**
```bash
dominion --help
dominion COMMAND --help
```

---

## Core Commands

### `dominion doctor`

System health check.

**Usage:**
```bash
dominion doctor [--json] [--verbose] [--deep] [--offline] [--strict]
```

**Options:**
- `--json` — Output JSON (machine-readable)
- `--verbose` — Detailed output
- `--deep` — Deep scan (slower)
- `--offline` — Skip network checks
- `--strict` — Exit 1 on warn (not just fail)

**Output:**
```
Dominion Health Check
=====================

Source Code Health:
  Python syntax: PASS (435 tests collected)
  Type checking: PASS (mypy)
  Linting: PASS (ruff)

Live Systems:
  MT5 data: WARN (stale 25h)
  RAGD: GREEN (10716 chunks, <50ms queries)
  WebSocket: OFFLINE (not implemented)
  domdata scanner: GREEN (no trading code)

Data Pipeline:
  DuckDB: GREEN (1256 bars, 400 features)
  Last run: 2026-05-18 10:30 (25h ago) — STALE

Metadata:
  Agent sessions: 2 active
  TODOs: 18 open
  Decisions: 18 recorded

Overall: WARN (MT5 data stale, pipeline stale)
```

**JSON Output:**
```bash
dominion doctor --json | jq .
```

```json
{
  "overall": "warn",
  "checks": {
    "source_code": {
      "status": "pass",
      "pytest": "435 tests collected",
      "mypy": "pass",
      "ruff": "pass"
    },
    "live_systems": {
      "mt5": {"status": "warn", "staleness": "25h"},
      "ragd": {"status": "green", "chunks": 10716},
      "websocket": {"status": "offline"}
    },
    "data_pipeline": {
      "status": "warn",
      "duckdb": "green",
      "last_run": "2026-05-18T10:30:00",
      "staleness": "25h"
    }
  }
}
```

---

### `dominion truth`

Full system truth report (doctor + complexity + ignore + ragd + retrieval).

**Usage:**
```bash
dominion truth [--json]
```

**Output:** Extended health check with complexity scores, ignore stats, RAGD metrics.

---

### `dominion agent`

Agent OS operations.

**Subcommands:**
- `init` — Start session
- `end` — End session
- `heartbeat` — Keep session alive
- `sessions` — List sessions
- `task` — Task management
- `lock` — File lock operations
- `review` — Adversarial review
- `complexity` — Complexity budget
- `dashboard` — System snapshot

---

#### `dominion agent init`

Start agent session.

**Usage:**
```bash
dominion agent init --name AGENT_NAME --role ROLE [--parent SESSION_ID]
```

**Options:**
- `--name` — Agent name (e.g., `"claude-sonnet-4"`)
- `--role` — `research` | `implementation` | `review` | `maintenance`
- `--parent` — Parent session ID (for nested agents)

**Output:**
```
Started session: sess_abc123
Agent: claude-sonnet-4
Role: implementation
Git branch: main
Git commit: 2d0b445
```

---

#### `dominion agent end`

End session.

**Usage:**
```bash
dominion agent end --session SESSION_ID --status STATUS [--summary TEXT]
```

**Options:**
- `--session` — Session ID
- `--status` — `completed` | `failed` | `abandoned`
- `--summary` — Summary text

**Example:**
```bash
dominion agent end --session sess_abc123 --status completed --summary "Fixed bug X"
```

---

#### `dominion agent sessions`

List sessions.

**Usage:**
```bash
dominion agent sessions [--active] [--stale] [--limit N]
```

**Options:**
- `--active` — Active sessions only
- `--stale` — Stale sessions only (no heartbeat >30min)
- `--limit` — Max results (default: 50)

**Output:**
```
Active Sessions:
  sess_abc123: claude-sonnet-4 (implementation), started 2026-05-19 17:00
  sess_def456: claude-opus-4 (research), started 2026-05-19 16:30
```

---

#### `dominion agent task create`

Create task.

**Usage:**
```bash
dominion agent task create --title TITLE [--description TEXT] [--kind KIND] [--priority N] [--scope-file FILE]...
```

**Options:**
- `--title` — Task title (required)
- `--description` — Task description
- `--kind` — `feature` | `bugfix` | `refactor` | `research` | `maintenance` (default: `feature`)
- `--priority` — 1 (highest) to 10 (lowest) (default: 5)
- `--scope-file` — Scope file (repeat for multiple)

**Example:**
```bash
dominion agent task create \
  --title "Add retry logic" \
  --kind feature \
  --priority 3 \
  --scope-file data_pipeline/pipeline.py
```

---

#### `dominion agent task list`

List tasks.

**Usage:**
```bash
dominion agent task list [--status STATUS] [--limit N]
```

**Options:**
- `--status` — `open` | `in_progress` | `blocked` | `done` | `abandoned`
- `--limit` — Max results (default: 50)

**Output:**
```
Open Tasks:
  task_abc123: Add retry logic (feature, priority=3)
  task_def456: Fix memory leak (bugfix, priority=1)
```

---

#### `dominion agent task update`

Update task status.

**Usage:**
```bash
dominion agent task update --task TASK_ID --status STATUS [--evidence-json FILE]
```

**Options:**
- `--task` — Task ID
- `--status` — New status
- `--evidence-json` — Evidence JSON file (required for `done`)

**Example:**
```bash
dominion agent task update --task task_abc123 --status in_progress
# ... work ...
echo '{"commands": [{"command": "pytest", "output": "42 passed"}], "report": "reports/retry_logic.md"}' > evidence.json
dominion agent task update --task task_abc123 --status done --evidence-json evidence.json
```

---

#### `dominion agent review`

Run adversarial review on task.

**Usage:**
```bash
dominion agent review --task TASK_ID [--strict] [--json]
```

**Options:**
- `--task` — Task ID
- `--strict` — Strict mode (fails on large refactors)
- `--json` — JSON output

**Output:**
```
Adversarial Review: task_abc123
===============================

Verdict: approved
Score: 5.0 (lower = better)

Findings:
  [info] claim_check: Task had active claim
  [info] scope_check: Task had scope files
  [info] evidence_check: Evidence provided
  [info] doctor_evidence: Doctor check present
  [info] pytest_evidence: Pytest output present

Summary: Task approved with 0 critical issues
```

---

#### `dominion agent complexity`

Complexity budget tracking.

**Usage:**
```bash
dominion agent complexity [--package PACKAGE] [--all] [--json]
```

**Options:**
- `--package` — Package name (e.g., `dominion_ai`)
- `--all` — All packages
- `--json` — JSON output

**Output:**
```
Complexity Report: dominion_ai
==============================

Score: 105.2
Budget: 130.0
Status: OK (within budget)

Metrics:
  Files: 15
  Public symbols: 42
  Tests: 84 (test/source ratio: 2.0)
  TODOs: 5
  TEMP_ADAPTERs: 2
  Broad excepts: 3
  Untested modules: 1
  Largest file: 256 lines

Warnings:
  5 TODO/FIXME markers — technical debt accumulating
  2 TEMP_ADAPTER(s) found — schedule removal

Remediation:
  Address or assign TODO items before adding new features
  Search for TEMP_ADAPTER comments and resolve them
```

---

#### `dominion agent dashboard`

System dashboard (cockpit view).

**Usage:**
```bash
dominion agent dashboard [--json]
```

**Output:**
```
Dominion Dashboard
==================

Sessions:
  Active: 2
  Stale: 0

Tasks:
  Open: 5
  In progress: 3
  Blocked: 1
  Done (last 7d): 12

Locks:
  Active: 7
  Stale: 0

RAGD:
  Chunks: 10716
  Active: 9024
  Query latency (p95): 42ms

Data Pipeline:
  Last run: 25h ago (STALE)
  Features: 400
  Bars: 1256

Complexity:
  Over budget: 0 packages
  Highest score: dominion_agent (245.3 / 350.0)
```

---

### `dominion scan`

Scan repo and update manifest.

**Usage:**
```bash
dominion scan [--force] [--path PATH]
```

**Options:**
- `--force` — Force full scan (ignore manifest cache)
- `--path` — Scan specific path (default: repo root)

**Output:**
```
Scanning /home/Martin/Dominion...
  Found 1024 files
  Skipped 512 (cached)
  Indexed 512 files
  
Manifest updated: 512 new entries
```

---

### `dominion search`

Search codebase via RAGD.

**Usage:**
```bash
dominion search QUERY [--top-k N] [--json]
```

**Options:**
- `--top-k` — Max results (default: 10)
- `--json` — JSON output

**Example:**
```bash
dominion search "Kalman filter" --top-k 5
```

**Output:**
```
Results for: Kalman filter
===========================

1. data_pipeline/fusion/kalman.py:42-58 (score: 0.92)
   class KalmanFilterBank:
       def fuse(self, observations, timestamp):
           ...

2. data_pipeline/fusion/bridge.py:12-28 (score: 0.85)
   # Kalman filter for price fusion
   def reconstruct_ticks_from_bars(ohlc_df, n_ticks=10):
       ...
```

---

### `dominion data`

Data pipeline operations.

**Subcommands:**
- `run` — Run full pipeline
- `fetch` — Fetch sources only
- `features` — Compute features only
- `report` — Generate report

---

#### `dominion data run`

Run full data pipeline.

**Usage:**
```bash
dominion data run [--sources SOURCE...] [--skip-health]
```

**Options:**
- `--sources` — Source names (`yahoo`, `fred`, `alphavantage`, `cot`, `mt5`)
- `--skip-health` — Skip health checks

**Output:**
```
Starting pipeline run abc12345...
  Fetching yahoo... OK (1256 bars)
  Fetching fred... OK (42 series)
  Fetching mt5... OK (5000 ticks)
  Fusing prices... OK (1256 bars)
  Reconstructing ticks... OK (1000 ticks)
  Computing features... OK (400 features)
  Health checks... OK (0 gaps, 0 anomalies)
  
Report: reports/pipeline_run_abc12345.md
```

---

### `dominion lob`

LOB reconstruction engine.

**Usage:**
```bash
dominion lob reconstruct --input FILE --output FILE [--depth N]
```

**Options:**
- `--input` — Input CSV (ticks)
- `--output` — Output CSV (LOB snapshots)
- `--depth` — LOB depth (default: 10)

---

### `dominion sim`

Execution simulator.

**Usage:**
```bash
dominion sim run --strategy FILE --data FILE [--output FILE]
```

**Options:**
- `--strategy` — Strategy config (JSON)
- `--data` — Market data (CSV)
- `--output` — Output report (Markdown)

---

### `dominion tca`

Trade cost analysis.

**Usage:**
```bash
dominion tca analyze --trades FILE [--output FILE]
```

**Options:**
- `--trades` — Trade log (CSV)
- `--output` — TCA report (Markdown)

---

### `dominion toxicity`

Order flow toxicity monitor.

**Usage:**
```bash
dominion toxicity scan [--threshold N] [--output FILE]
```

**Options:**
- `--threshold` — VPIN threshold (default: 0.7)
- `--output` — Toxicity report (Markdown)

---

## Environment Variables

**`DOMINION_ROOT`** — Repo root (default: `~/Dominion`)

**`DOMINION_HOME`** — Data directory (default: `~/.dominion`)

**`RAGD_URL`** — RAGD URL (default: `http://127.0.0.1:7474`)

**`RAGD_SEMANTIC_HOST`** — RAGD semantic service host (default: `127.0.0.1`)

**`RAGD_SEMANTIC_PORT`** — RAGD semantic service port (default: `7476`)

**`NOMIC_API_KEY`** — Nomic embedding API key

**Example:**
```bash
export DOMINION_ROOT=/home/Martin/Dominion
export RAGD_URL=http://127.0.0.1:7474
```

---

## Exit Codes

**0** — Success

**1** — Failure (error, validation failed)

**2** — Safety violation (forbidden trading, secret access)

**Example:**
```bash
dominion doctor --strict
if [ $? -ne 0 ]; then
  echo "Health check failed"
  exit 1
fi
```

---

## Examples

### Daily Workflow

```bash
# Check health
dominion doctor

# Run data pipeline if stale
dominion data run

# Start agent session
SESSION=$(dominion agent init --name claude --role implementation --json | jq -r .session_id)

# Create task
TASK=$(dominion agent task create --title "Fix bug X" --kind bugfix --json | jq -r .task_id)

# Update status
dominion agent task update --task $TASK --status in_progress

# ... work ...

# Adversarial review
dominion agent review --task $TASK

# End session
dominion agent end --session $SESSION --status completed
```

---

### Pipeline + ML Training

```bash
# Run pipeline
dominion data run

# Build dataset
python scripts/build_dataset_v1.py

# Train baselines
python scripts/train_baselines.py

# Check results
cat reports/baseline_results_v1.json | jq .
```

---

### RAGD Query

```bash
# Search codebase
dominion search "error handling" --top-k 10

# Index new files
dominion scan --path data_pipeline/

# Check RAGD health
curl http://127.0.0.1:7474/health | jq .
```

---

## Troubleshooting

### "Command not found: dominion"

**Cause:** Alias not set or symlink missing.

**Fix:**
```bash
alias dominion='python ~/Dominion/scripts/dominion_cli.py'
```

---

### "SQLite error: database is locked"

**Cause:** Multiple processes writing to SQLite without WAL.

**Fix:**
```bash
sqlite3 ~/.dominion/agent_os.db "PRAGMA journal_mode=WAL;"
```

---

### "RAGD unhealthy"

**Cause:** RAGD service down or corrupted.

**Fix:**
```bash
# Check process
ps aux | grep ragd

# Restart
tmux kill-session -t ragd
tmux new-session -d -s ragd 'cd ~/Dominion/ragd && ./build/ragd --db ~/.ragd/ragd.db --host 127.0.0.1 --port 7474 --path ~/Dominion'
```

---

## Performance

| Command | Typical Latency | Notes |
|---------|----------------|-------|
| `dominion doctor` | 2-5s | Runs pytest, mypy, ruff |
| `dominion agent sessions` | <100ms | Simple DB query |
| `dominion agent complexity` | 1-3s | AST parsing per package |
| `dominion search` | 50-200ms | RAGD query |
| `dominion scan` | 5-60s | Depends on file count |
| `dominion data run` | 2-5min | Full pipeline |

---

## Security

**Credential Files:**
- `secrets/mt5.env` — Blocked by CLI (safety filters)
- Never printed or logged

**Dangerous Commands:**
- `rm -rf`, `git reset --hard`, `drop table` — Require `--dangerous` flag

**Trading Commands:**
- No order placement commands (read-only data pipeline)
- `domdata/check_no_trading.py` scanner verifies no trading code

---

## Related

- [PYTHON_API_REFERENCE.md](PYTHON_API_REFERENCE.md) — Python APIs
- [RAGD_REST_API.md](RAGD_REST_API.md) — RAGD HTTP endpoints
- [AGENT_OS_ARCHITECTURE.md](../01_ARCHITECTURE/AGENT_OS_ARCHITECTURE.md) — Agent OS internals

---

**Last Updated:** 2026-05-19  
**Verified By:** Claude Code (Sonnet 4.5)  
**Review Status:** ✓ All commands tested + help text validated
