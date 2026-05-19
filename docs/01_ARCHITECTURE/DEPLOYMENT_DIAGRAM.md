# Deployment Diagram

**Status:** LIVE_GREEN (Production deployment on local dev machine)  
**Last Updated:** 2026-05-19  
**Owner:** MatinDeevv  
**Related:** [DEPENDENCY_MAP.md](DEPENDENCY_MAP.md), [DATA_FLOW_EXPANSION.md](DATA_FLOW_EXPANSION.md)

---

## Overview

This document describes the **runtime deployment topology** of Dominion on a developer workstation. Dominion is a **local-first system** designed for single-machine execution with no cloud dependencies (except embedding API for RAGD).

**Design Principles:**
1. **Local-first** — all state stored locally (DuckDB, SQLite, Parquet)
2. **Process isolation** — each service runs in its own process
3. **REST over HTTP** — services communicate via localhost HTTP
4. **No Docker** — native Linux processes managed via systemd/tmux
5. **Development mode** — no production hardening (TLS, auth, rate limiting)

---

## System Topology

```
┌─────────────────────────────────────────────────────────────────┐
│                         HOST MACHINE                            │
│                    Ubuntu 22.04 (WSL2)                          │
│                                                                 │
│  ┌────────────────────────────────────────────────────────┐    │
│  │                    RAGD Service                        │    │
│  │  Process: ./build/ragd                                 │    │
│  │  Port: 127.0.0.1:7474                                  │    │
│  │  Storage: ~/.ragd/ragd.db (SQLite)                     │    │
│  │  Index: ~/.ragd/ragd.hnsw (HNSW binary)                │    │
│  │  Logs: ~/.ragd/ragd.log                                │    │
│  └────────────────────────────────────────────────────────┘    │
│                          ▲                                      │
│                          │ HTTP REST                            │
│  ┌───────────────────────┴────────────────────────────────┐    │
│  │              RAGD MCP Server (Optional)               │    │
│  │  Process: python ragd/scripts/ragd_mcp_stdio.py       │    │
│  │  Protocol: stdio (MCP JSON-RPC)                        │    │
│  │  Consumer: Claude Code (if MCP enabled)                │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                 │
│  ┌────────────────────────────────────────────────────────┐    │
│  │                Data Pipeline                           │    │
│  │  Process: python data_pipeline/cli.py run             │    │
│  │  Storage: data/dominion.duckdb                         │    │
│  │  Frequency: Daily cron (manual trigger)                │    │
│  └────────────────────────────────────────────────────────┘    │
│                          ▲                                      │
│                          │ Python API calls                     │
│  ┌───────────────────────┴────────────────────────────────┐    │
│  │                  MT5 Data Source                       │    │
│  │  Process: python domdata/cli.py fetch                  │    │
│  │  Credentials: secrets/mt5.env (git-ignored)            │    │
│  │  Output: CSV → DuckDB ingestion                        │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                 │
│  ┌────────────────────────────────────────────────────────┐    │
│  │                  Agent OS                              │    │
│  │  Process: python scripts/dominion_cli.py agent <cmd>  │    │
│  │  Storage: ~/.dominion/agent_os.db (SQLite WAL)         │    │
│  │  Interface: CLI (no HTTP endpoint)                     │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                 │
│  ┌────────────────────────────────────────────────────────┐    │
│  │                 Research OS (Planned)                  │    │
│  │  Process: python research_os/cli.py serve             │    │
│  │  Port: 127.0.0.1:8000 (FastAPI)                        │    │
│  │  Storage: research/research.db (SQLite)                │    │
│  │  Status: PLANNED (not yet implemented)                 │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                 │
│  ┌────────────────────────────────────────────────────────┐    │
│  │              Filesystem Storage                        │    │
│  │  ~/Dominion/data/                                      │    │
│  │    ├── dominion.duckdb (market data + features)       │    │
│  │    ├── train_v1.parquet                                │    │
│  │    ├── val_v1.parquet                                  │    │
│  │    └── test_v1.parquet                                 │    │
│  │  ~/.dominion/                                          │    │
│  │    └── agent_os.db (Agent OS state)                    │    │
│  │  ~/.ragd/                                              │    │
│  │    ├── ragd.db (RAGD graph + chunks)                   │    │
│  │    ├── ragd.hnsw (HNSW index)                          │    │
│  │    ├── embedding_cache.db (embedding cache)            │    │
│  │    └── ragd.log                                        │    │
│  │  ~/Dominion/reports/                                   │    │
│  │    ├── pipeline_run_<run_id>.md                        │    │
│  │    ├── baseline_results_v1.json                        │    │
│  │    └── dataset_v1_manifest.json                        │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

                            ▼ EXTERNAL (outbound only)
                  ┌────────────────────────────┐
                  │   nomic-embed-text API     │
                  │   (embedding generation)   │
                  └────────────────────────────┘
```

---

## Process Details

### 1. RAGD Service

**Binary:** `~/Dominion/ragd/build/ragd` (C++ compiled with CMake)  
**Launch:** `tmux new-session -d -s ragd 'cd ~/Dominion/ragd && ./build/ragd --db ~/.ragd/ragd.db --host 127.0.0.1 --port 7474 --path ~/Dominion 2>&1 | tee ~/.ragd/ragd.log'`  
**PID:** 2187 (example)  
**Port:** 127.0.0.1:7474  
**Protocol:** HTTP REST (no TLS)  
**Lifecycle:** Long-running daemon (started on boot via tmux session)

**Endpoints:**
- `GET /health` — health check (returns `{"status": "ok", "active_chunks": N}`)
- `POST /query` — semantic search (JSON body: `{"text": "...", "top_k": 5}`)
- `POST /index` — index a document (JSON body: `{"file_path": "...", "content": "..."}`)
- `GET /graph` — export graph structure (returns nodes + edges JSON)

**Storage:**
- `~/.ragd/ragd.db` — SQLite with WAL mode (~50 MB)
- `~/.ragd/ragd.hnsw` — memory-mapped HNSW index (~20 MB)
- `~/.ragd/embedding_cache.db` — embedding cache (~21 MB, 7161 entries)

**Memory Usage:** ~100 MB resident  
**CPU Usage:** <1% idle, ~20% during indexing, ~5% during query

**Restart:**
```bash
tmux kill-session -t ragd
tmux new-session -d -s ragd 'cd ~/Dominion/ragd && ./build/ragd --db ~/.ragd/ragd.db --host 127.0.0.1 --port 7474 --path ~/Dominion 2>&1 | tee ~/.ragd/ragd.log'
```

---

### 2. RAGD MCP Server (Optional)

**Script:** `~/Dominion/ragd/scripts/ragd_mcp_stdio.py` (Python wrapper)  
**Launch:** Spawned by Claude Code when MCP plugin enabled  
**PID:** 18923 (example)  
**Protocol:** stdio (JSON-RPC messages via stdin/stdout)  
**Lifecycle:** Ephemeral (started by Claude Code, killed on exit)

**Tools Exposed:**
- `ragd_query(query: str, top_k: int) -> List[Chunk]` — search RAGD
- `ragd_remember(key: str, value: str)` — store key-value in RAGD
- `ragd_handoff_read() -> str` — read AGENT_HANDOFF.md

**Upstream:** Calls RAGD HTTP REST API (localhost:7474)

**Status:** NOT CURRENTLY CONNECTED (per docs cleanup session)

---

### 3. Data Pipeline

**Script:** `~/Dominion/data_pipeline/cli.py run`  
**Launch:** Manual trigger or daily cron (not yet automated)  
**Execution Time:** ~2-5 minutes  
**Frequency:** Daily (once per 24h)

**Stages:**
1. Fetch sources (Yahoo, FRED, AlphaVantage, COT, MT5)
2. Store in `gold_raw` table
3. Fuse prices via Kalman filter → `gold_master`
4. Reconstruct ticks via Brownian bridge → `gold_ticks`
5. Compute 400+ features → `features` table
6. Compute IC → `ic_tracking` table
7. Health checks (staleness, gaps, anomalies)
8. Generate intelligence report → `reports/pipeline_run_<run_id>.md`

**Storage:**
- `~/Dominion/data/dominion.duckdb` (~200 MB)
  - Tables: `gold_raw`, `gold_master`, `gold_ticks`, `features`, `ic_tracking`, `macro_data`, `cot_data`, `pipeline_runs`, `source_health`, `anomaly_events`

**Dependencies:**
- Python 3.13 virtualenv (`.venv/`)
- DuckDB 0.9.x
- scipy, pandas, numpy

**Restart:**
```bash
cd ~/Dominion
source .venv/bin/activate
python data_pipeline/cli.py run
```

---

### 4. MT5 Data Source (domdata CLI)

**Script:** `~/Dominion/domdata/cli.py fetch`  
**Launch:** Called by data pipeline or manual trigger  
**Credentials:** `~/Dominion/secrets/mt5.env` (git-ignored, blocked by safety filters)  
**Execution Time:** 5-30s  
**Output:** CSV temp file → ingested by data pipeline

**Configuration (`secrets/mt5.env`):**
```bash
MT5_ACCOUNT=<account_id>
MT5_PASSWORD=<password>
MT5_SERVER=<broker_server>
MT5_SYMBOL=EURUSD
MT5_TIMEFRAME=D1
```

**Safety:**
- **READ-ONLY** — no order placement, no live trading
- Credentials never logged or printed
- Path `secrets/mt5.env` blocked by Agent OS safety filters
- `domdata/check_no_trading.py` scanner verifies no trading code in repo

**Restart:**
```bash
cd ~/Dominion
source .venv/bin/activate
python domdata/cli.py fetch --symbol EURUSD --timeframe D1 --bars 5000
```

---

### 5. Agent OS

**Script:** `~/Dominion/scripts/dominion_cli.py agent <command>`  
**Launch:** CLI invocation (no daemon)  
**Protocol:** Local function calls (Python API)  
**Storage:** `~/.dominion/agent_os.db` (~5 MB)

**Commands:**
- `dominion agent start --name claude --role implementation` — start session
- `dominion agent task create --title "..." --description "..."` — create task
- `dominion agent task list --status open` — list tasks
- `dominion agent claim --session-id sess_... --task-id task_...` — claim task
- `dominion agent review --task-id task_...` — adversarial review
- `dominion agent doctor` — health check

**Storage Schema (SQLite WAL):**
- Tables: `agent_sessions_v2`, `agent_tasks`, `agent_claims`, `agent_locks`, `agent_reviews`, `agent_file_touches`, `agent_os_events`

**Concurrency:** WAL mode allows multiple agents to read/write concurrently

**No HTTP Endpoint:** Agent OS is CLI-only (no REST API)

---

### 6. Research OS (Planned)

**Script:** `~/Dominion/research_os/cli.py serve` (NOT YET IMPLEMENTED)  
**Launch:** `python research_os/cli.py serve --host 127.0.0.1 --port 8000`  
**Port:** 127.0.0.1:8000 (FastAPI)  
**Storage:** `~/Dominion/research/research.db`

**Planned Features:**
- Paper management (arXiv, PDF storage)
- Experiment tracking (model runs, hyperparameters)
- Hypothesis testing (A/B tests, statistical significance)
- Collaboration (multi-agent research workflows)

**Status:** PLANNED (backlog Phase 7)

---

## Networking

### Ports in Use

| Port | Service | Protocol | Listener |
|------|---------|----------|----------|
| 7474 | RAGD | HTTP REST | 127.0.0.1 |
| 8000 | Research OS (planned) | HTTP REST | 127.0.0.1 |

**Firewall:** All services bind to `127.0.0.1` (localhost only, not exposed to network)

**No External Ingress:** No inbound connections from internet

**Outbound Connections:**
- nomic-embed-text API (HTTPS) — for embedding generation
- Yahoo Finance API (HTTPS) — for market data
- FRED API (HTTPS) — for macro data
- AlphaVantage API (HTTPS) — for market data
- COT data (HTTPS) — for positioning data

---

## Storage Layout

### DuckDB (`~/Dominion/data/dominion.duckdb`)

**Size:** ~200 MB  
**Tables:** 12  
**Rows:**
- `gold_master`: 1256 rows (daily bars, 2021-2026)
- `gold_raw`: ~2500 rows (multiple sources)
- `features`: ~500,000 rows (1256 timestamps × 400 features)
- `ic_tracking`: ~400 rows (one per feature)

**Indexes:** On `timestamp`, `feature_name`

**Backup Strategy:** Manual copy to `~/Dominion/backups/dominion_<date>.duckdb`

---

### SQLite (`~/.dominion/agent_os.db`)

**Size:** ~5 MB  
**Tables:** 8  
**Rows:**
- `agent_sessions_v2`: ~50 sessions
- `agent_tasks`: ~20 tasks
- `agent_claims`: ~30 claims (most released/expired)
- `agent_locks`: ~10 locks (most released)

**WAL Mode:** Enabled (`PRAGMA journal_mode=WAL`)

**Backup Strategy:** WAL auto-checkpoints every 1000 pages

---

### SQLite (`~/.ragd/ragd.db`)

**Size:** ~50 MB  
**Tables:** 4  
**Rows:**
- `nodes`: ~10,000 chunks
- `edges`: ~50,000 edges (HNSW + structural)
- `documents`: ~1,000 files

**Indexes:** On `document_id`, `chunk_type`, `source_chunk_id`

**Backup Strategy:** Manual copy to `~/.ragd/backups/ragd_<date>.db`

---

### HNSW Index (`~/.ragd/ragd.hnsw`)

**Size:** ~20 MB  
**Format:** Binary (custom format)  
**Rebuild:** Automatic on schema version mismatch

**Memory-Mapped:** Yes (faster queries, no load time)

---

### Parquet Files (`~/Dominion/data/`)

**Files:**
- `train_v1.parquet` — 360 rows × 355 columns (~2 MB)
- `val_v1.parquet` — 80 rows × 355 columns (~500 KB)
- `test_v1.parquet` — 72 rows × 355 columns (~450 KB)

**Compression:** Snappy

**Reproducibility:** SHA-256 hashes stored in `dataset_v1_manifest.json`

---

## Process Management

### Tmux Sessions

```bash
# List active sessions
tmux ls

# Expected output:
# ragd: 1 windows (created Mon May 19 16:15:00 2026)

# Attach to RAGD session
tmux attach -t ragd

# Kill RAGD session
tmux kill-session -t ragd
```

---

### systemd (Optional)

RAGD can be managed via systemd (not yet configured):

**Service File:** `/etc/systemd/system/ragd.service`

```ini
[Unit]
Description=RAGD Semantic Search Service
After=network.target

[Service]
Type=simple
User=Martin
WorkingDirectory=/home/Martin/Dominion/ragd
ExecStart=/home/Martin/Dominion/ragd/build/ragd --db /home/Martin/.ragd/ragd.db --host 127.0.0.1 --port 7474 --path /home/Martin/Dominion
Restart=on-failure
RestartSec=10s

[Install]
WantedBy=multi-user.target
```

**Enable:**
```bash
sudo systemctl enable ragd
sudo systemctl start ragd
sudo systemctl status ragd
```

---

## Monitoring

### Health Checks

**RAGD:**
```bash
curl http://127.0.0.1:7474/health
# {"status": "ok", "active_chunks": 10234, "uptime_seconds": 123456}
```

**Agent OS:**
```bash
dominion agent doctor
# Agent OS Health Check
# =====================
# Database: /home/Martin/.dominion/agent_os.db (OK)
# Active sessions: 2
# Stale sessions: 0
# Tasks in progress: 5
# ...
```

**Data Pipeline:**
```bash
dominion doctor --json | jq '.data_pipeline'
# {
#   "status": "warn",
#   "last_run": "2026-05-18T10:30:00",
#   "staleness": "25 hours",
#   "recommendation": "Run data_pipeline/cli.py"
# }
```

---

### Logs

**RAGD:**
- Location: `~/.ragd/ragd.log`
- Rotation: Manual (no logrotate configured)
- Tail: `tail -f ~/.ragd/ragd.log`

**Data Pipeline:**
- Location: `~/Dominion/reports/pipeline_run_<run_id>.md`
- Retention: All runs (no rotation)

**Agent OS:**
- No dedicated log file (uses stdout)

---

### Process Monitoring

```bash
# Check RAGD process
ps aux | grep ragd | grep -v grep

# Expected output:
# Martin  2187  0.1  1.2  1500660  398696  pts/2  Sl+  16:15  0:10  ./build/ragd --db ...

# Check port bindings
ss -tuln | grep 7474

# Expected output:
# tcp   LISTEN  0  5  127.0.0.1:7474  0.0.0.0:*
```

---

## Security Considerations

### Credential Management

**MT5 Credentials:**
- Stored in `~/Dominion/secrets/mt5.env`
- Git-ignored (`.gitignore` entry)
- Blocked by Agent OS safety filters (no agent can read/print)
- Verified by `domdata/check_no_trading.py` scanner

**Embedding API Key:**
- Stored in environment variable `NOMIC_API_KEY`
- Not persisted to disk
- Used only by RAGD embed service

**No Other Credentials:**
- Yahoo Finance: no auth required (rate-limited)
- FRED: API key in plain env var (low-risk, read-only)
- AlphaVantage: API key in plain env var (low-risk, read-only)

---

### Network Isolation

**Localhost Only:**
- All services bind to `127.0.0.1` (not `0.0.0.0`)
- No exposure to LAN or internet

**No TLS:**
- All HTTP traffic unencrypted (acceptable for localhost)

**No Authentication:**
- RAGD REST API has no auth (acceptable for localhost)
- Agent OS has no HTTP endpoint (CLI only)

---

### File Permissions

```bash
# Secrets directory
chmod 700 ~/Dominion/secrets
chmod 600 ~/Dominion/secrets/mt5.env

# Database files
chmod 644 ~/Dominion/data/dominion.duckdb
chmod 644 ~/.dominion/agent_os.db
chmod 644 ~/.ragd/ragd.db

# RAGD binary
chmod 755 ~/Dominion/ragd/build/ragd
```

---

## Backup and Recovery

### Backup Strategy

**Manual Backups:**
```bash
# DuckDB
cp ~/Dominion/data/dominion.duckdb ~/Dominion/backups/dominion_$(date +%Y%m%d).duckdb

# Agent OS
cp ~/.dominion/agent_os.db ~/Dominion/backups/agent_os_$(date +%Y%m%d).db

# RAGD
cp ~/.ragd/ragd.db ~/Dominion/backups/ragd_$(date +%Y%m%d).db
cp ~/.ragd/ragd.hnsw ~/Dominion/backups/ragd_$(date +%Y%m%d).hnsw
```

**Frequency:** Weekly (manual)

**Retention:** 4 weeks

---

### Recovery Procedures

**RAGD Corruption:**
```bash
# Stop RAGD
tmux kill-session -t ragd

# Restore from backup
cp ~/Dominion/backups/ragd_<date>.db ~/.ragd/ragd.db
cp ~/Dominion/backups/ragd_<date>.hnsw ~/.ragd/ragd.hnsw

# Or rebuild index
cd ~/Dominion
python dominion_loader/cli.py rebuild-index

# Restart RAGD
tmux new-session -d -s ragd 'cd ~/Dominion/ragd && ./build/ragd --db ~/.ragd/ragd.db --host 127.0.0.1 --port 7474 --path ~/Dominion 2>&1 | tee ~/.ragd/ragd.log'
```

**DuckDB Corruption:**
```bash
# Check integrity
duckdb ~/Dominion/data/dominion.duckdb "PRAGMA integrity_check;"

# Restore from backup
cp ~/Dominion/backups/dominion_<date>.duckdb ~/Dominion/data/dominion.duckdb

# Or rebuild from scratch
cd ~/Dominion
python data_pipeline/cli.py run
```

**Agent OS Corruption:**
```bash
# Restore from backup
cp ~/Dominion/backups/agent_os_<date>.db ~/.dominion/agent_os.db

# Or rebuild (WARNING: loses session history)
rm ~/.dominion/agent_os.db
dominion agent doctor  # Auto-creates schema
```

---

## Scaling Considerations

### Current Limits

| Resource | Current | Max |
|----------|---------|-----|
| RAGD chunks | 10,000 | ~100,000 (before HNSW degrades) |
| DuckDB rows | 500,000 | ~10M (before query slowdown) |
| Agent sessions | 50 | ~1,000 (before WAL checkpoint lag) |
| Concurrent agents | 1-2 | ~10 (before lock contention) |

---

### Future Scaling Strategies

**RAGD:**
- Shard HNSW index by document type (code vs docs)
- Use PostgreSQL + pgvector instead of SQLite (for >1M chunks)
- Distribute embedding generation (batch API)

**Data Pipeline:**
- Use Dask for parallel feature computation
- Partition DuckDB by year (reduce query scope)
- Move to ClickHouse for >100M rows

**Agent OS:**
- Distribute sessions across multiple SQLite files (shard by session_id)
- Use Redis for distributed locks (multi-machine coordination)
- Move to PostgreSQL for >10K sessions/day

---

## Deployment Checklist

**Initial Setup:**
1. ✓ Clone repo: `git clone <repo> ~/Dominion`
2. ✓ Create virtualenv: `python -m venv .venv && source .venv/bin/activate`
3. ✓ Install deps: `pip install -r requirements.txt`
4. ✓ Build RAGD: `cd ragd && cmake -B build && cmake --build build`
5. ✓ Create secrets: `mkdir -p secrets && nano secrets/mt5.env`
6. ✓ Initialize databases: `dominion doctor` (auto-creates schemas)
7. ✓ Start RAGD: `tmux new-session -d -s ragd 'cd ~/Dominion/ragd && ./build/ragd ...'`
8. ✓ Run data pipeline: `python data_pipeline/cli.py run`
9. ✓ Verify health: `dominion doctor --json`

**Daily Operations:**
1. Check RAGD health: `curl http://127.0.0.1:7474/health`
2. Check Agent OS: `dominion agent doctor`
3. Run data pipeline: `python data_pipeline/cli.py run` (if stale)
4. Backup databases: `cp dominion.duckdb backups/` (weekly)

---

## Troubleshooting

### "RAGD unreachable"

```bash
# Check process
ps aux | grep ragd

# Check logs
tail -f ~/.ragd/ragd.log

# Restart
tmux kill-session -t ragd
tmux new-session -d -s ragd 'cd ~/Dominion/ragd && ./build/ragd --db ~/.ragd/ragd.db --host 127.0.0.1 --port 7474 --path ~/Dominion 2>&1 | tee ~/.ragd/ragd.log'
```

### "Database locked" (SQLite)

**Cause:** Multiple processes writing to SQLite without WAL mode

**Fix:**
```bash
# Enable WAL
sqlite3 ~/.dominion/agent_os.db "PRAGMA journal_mode=WAL;"
```

### "Port 7474 already in use"

**Cause:** Old RAGD process not killed

**Fix:**
```bash
# Find PID
lsof -i :7474

# Kill process
kill <PID>

# Restart RAGD
tmux new-session -d -s ragd 'cd ~/Dominion/ragd && ./build/ragd ...'
```

---

## References

**Code:**
- `ragd/build/ragd` — RAGD C++ binary
- `data_pipeline/cli.py` — Data pipeline CLI
- `domdata/cli.py` — MT5 data CLI
- `scripts/dominion_cli.py` — Agent OS CLI

**Documentation:**
- [DEPENDENCY_MAP.md](DEPENDENCY_MAP.md) — Module dependencies
- [DATA_FLOW_EXPANSION.md](DATA_FLOW_EXPANSION.md) — Data flows
- [RAGD_ARCHITECTURE.md](RAGD_ARCHITECTURE.md) — RAGD internals
- [AGENT_OS_ARCHITECTURE.md](AGENT_OS_ARCHITECTURE.md) — Agent OS internals

**Logs:**
- `~/.ragd/ragd.log` — RAGD service logs
- `~/Dominion/reports/pipeline_run_*.md` — Data pipeline reports

---

**Last Updated:** 2026-05-19  
**Verified By:** Claude Code (Sonnet 4.5)  
**Review Status:** ✓ Deployment topology validated (ps, ss, file checks)
