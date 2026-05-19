# Symbol Index

**Status:** LIVE_GREEN  
**Last Updated:** 2026-05-19  
**Purpose:** Quick reference for key classes, functions, endpoints

---

## Classes

### Data Pipeline

**`KalmanFilterBank`** (`data_pipeline/fusion/kalman.py`)  
Multi-timescale Kalman filter bank for fusing prices from multiple sources. Maintains trust scores per source, adjusts weights based on innovation residuals. Returns fused price + confidence + source weights + anomaly flag.

**`Pipeline`** (`data_pipeline/pipeline.py`)  
Main orchestrator: fetch sources → fuse prices → reconstruct ticks → compute features → health checks → report. Handles errors gracefully (continues with remaining sources if one fails).

**`FeatureStore`** (`data_pipeline/features/store.py`)  
Computes 400+ features (price, volatility, microstructure, macro, regime, technical). Validates features (NaN %), computes IC, stores in DuckDB `features` table.

**`PipelineMonitor`** (`data_pipeline/health/monitor.py`)  
Health monitoring: staleness detection, gap detection + filling, source trust tracking. Fills small gaps (<= 3 bars) via interpolation.

**`AnomalyDetector`** (`data_pipeline/health/anomaly.py`)  
Isolation forest-based anomaly detection for price spikes, volume spikes, gaps. Stores findings in `anomaly_events` table.

**`ReportGenerator`** (`data_pipeline/health/report.py`)  
Generates intelligence reports (Markdown) with metrics, health summary, recommendations. Stored in `reports/pipeline_run_<run_id>.md`.

---

### Agent OS

**`AgentStore`** (`dominion_agent/store.py`)  
SQLite WAL-backed store for Agent OS tables (sessions, tasks, claims, locks, reviews, etc.). No global singleton — each process creates own instance. Auto-applies migrations on init.

**`Session`** (`dominion_agent/types.py`)  
Agent session dataclass: `session_id`, `agent_name`, `role`, `status`, `started_at`, `ended_at`, `last_heartbeat`, git tracking, metadata. Method: `is_stale(threshold_seconds)`.

**`Task`** (`dominion_agent/types.py`)  
Work item dataclass: `task_id`, `title`, `description`, `kind`, `priority`, `status`, `scope`, `validation`, `acceptance`, `risk`, `tags`, `evidence`. Transitions enforced by `TASK_TRANSITIONS` dict.

**`Adversary`** (`dominion_agent/adversary.py`)  
Adversarial review: runs 9 checks (claim, scope, evidence, validation commands, forbidden tokens, secret paths, report exists, doctor evidence, pytest evidence). Returns `ReviewReport` with verdict (`approved` | `conditional` | `blocked`).

**`ComplexityReport`** (`dominion_agent/complexity.py`)  
Complexity budget tracker: scans Python packages, computes score via weighted formula (files × 1.5 + symbols × 0.3 + TODOs × 2.5 - tests × 1.0, capped). Flags over-budget packages, suggests remediation.

---

### Dominion Loader

**`LoadedFile`** (`dominion_loader/scan.py`)  
File representation: `document_id` (SHA-256), `file_path`, `content_bytes`, `content_hash`, `file_type`, `classification`, `symbols`, `metadata`. Yielded by `iter_loaded_files()`.

**`Manifest`** (`dominion_loader/manifest.py`)  
SQLite-backed manifest for tracking indexed files: `document_id`, `file_path`, `content_hash`, `indexed_at`, `file_type`, `classification`, `symbols_json`, `metadata_json`. Methods: `get()`, `list_changed_since()`.

**`Cache`** (`dominion_loader/cache.py`)  
Content cache (namespace:key → value): fingerprint-validated, SHA-256 keyed. Raises `CacheCorruption` on fingerprint mismatch. Namespaces: `"retrieval:"`, `"context:"`.

**`HardwareProfile`** (`dominion_loader/hw_probe.py`)  
Hardware probe: `cpu_count`, `cpu_model`, `total_memory_gb`, `disk_type`, `has_cuda`, `platform`. Used by Agent 2 to choose model strategy.

---

### LOB & Execution

**`LOBEngine`** (`lob/engine.py`)  
Limit order book reconstruction from tick data. Maintains bid/ask ladders, handles orders (add, cancel, execute). Computes spread, depth, imbalance.

**`ExecSimulator`** (`exec_sim/simulator.py`)  
Execution simulator: replays strategy on historical data, simulates fills via matching engine. Computes slippage, market impact, execution shortfall.

**`TCAAnalyzer`** (`tca/analyzer.py`)  
Trade cost analysis: arrival price benchmark, VWAP benchmark, implementation shortfall, slippage attribution. Output: TCA report (Markdown + JSON).

**`ToxicityMonitor`** (`toxicity/monitor.py`)  
Order flow toxicity monitoring via VPIN (Volume-Synchronized Probability of Informed Trading). Flags high-toxicity periods (VPIN > 0.7).

**`MatchingEngine`** (`exec_sim/matching.py`)  
Order matching logic: price-time priority, handles market/limit orders, computes fills + residual. Used by ExecSimulator.

---

### RAGD (C++ Core, Python Bindings)

**`RAGEngine`** (C++: `ragd/src/rag_engine.cpp`, Python: `ragd/python/ragd_py.cpp`)  
Core retrieval engine: BM25 + keyword + HNSW hybrid search. Methods: `query()`, `query_json()`, `rebuild_vector()`. Returns ranked chunks with scores.

**`Storage`** (C++: `ragd/src/storage.cpp`)  
SQLite storage for nodes, edges, documents. Methods: `add_chunk()`, `mark_file_deleted()`, `metrics_json()`, `health_check()`. WAL mode for concurrency.

**`Indexer`** (C++: `ragd/src/indexer.cpp`)  
File indexer: scans paths, chunks files (AST/section/fixed-size), extracts metadata, stores in `nodes` table. Method: `index_paths()`.

**`HttpApi`** (C++: `ragd/src/http_api.cpp`)  
REST API server (httplib): exposes endpoints `/health`, `/query`, `/index`, `/session/*`, `/memory/*`, `/todos/*`, `/temporal/*`, `/deadzone/*`. Runs on port 7474.

---

## Functions

### Metrics (`scripts/metrics.py`)

**`compute_ic(predictions, actuals) -> (float, float)`**  
Information Coefficient (Spearman rank correlation) + p-value. Handles NaN, requires >=10 valid samples.

**`compute_sharpe(returns, risk_free_rate=0.0, annualization_factor=252) -> float`**  
Sharpe ratio: (mean - rf) / std × sqrt(annualization_factor). Returns ±inf if std=0.

**`compute_max_drawdown(cumulative_returns) -> (float, str, str)`**  
Max drawdown (peak-to-trough) + peak timestamp + trough timestamp. Returns tuple.

**`compute_turnover(positions) -> float`**  
Turnover: fraction of periods with position change. `positions.diff().abs().sum() / len(positions)`.

**`evaluate_model(metrics) -> Dict[str, str]`**  
Assigns rating (`"excellent"` | `"good"` | `"acceptable"` | `"poor"`) per metric based on thresholds.

---

### Feature Computation (`data_pipeline/features/`)

**`compute_returns(df, periods=[1,5,10]) -> pd.DataFrame`**  
Price returns: `df['close'].pct_change(period)`. Returns DataFrame with `return_1`, `return_5`, `return_10` columns.

**`compute_volatility(df, windows=[10,20,60]) -> pd.DataFrame`**  
Rolling volatility: `df['return_1'].rolling(window).std()`. Returns `volatility_10`, `volatility_20`, `volatility_60`.

**`compute_regime(df) -> pd.DataFrame`**  
HMM regime detection (2-state: trend vs ranging). Returns `regime_tactical`, `regime_prob_trend_up`, etc. **WARNING:** Look-ahead bias (fits on full dataset).

**`compute_microstructure(ticks_df) -> pd.DataFrame`**  
VPIN, order flow imbalance (OFI), bid-ask spread. Requires tick data. Returns `vpin`, `ofi`, `spread`.

---

### Safety Filters (`dominion_agent/safety.py`)

**`is_secret_path(path: str) -> bool`**  
Returns True if path references secrets directory or credential file (`secrets/`, `mt5.env`, `.env`, `.key`, `_secret_`, `id_rsa`).

**`is_forbidden_trading_task(text: str) -> bool`**  
Returns True if text contains forbidden trading operation (`order_send`, `Position_Open`, `execute_trade`, `enable live trading`).

**`validate_task_payload(payload: dict) -> SafetyResult`**  
Validates task creation payload: checks forbidden trading, secret paths, dangerous commands (`rm -rf`, `drop table`), empty title. Returns `SafetyResult(ok, violations, redacted_payload)`.

**`redact_path(path: str) -> str`**  
Returns safe version of path for logging: `secrets/mt5.env` → `[REDACTED/.env]`.

---

### Temporal Split (`scripts/temporal_split.py`)

**`temporal_split(df, train_end, val_end) -> (pd.DataFrame, pd.DataFrame, pd.DataFrame)`**  
Splits DataFrame by date boundaries (no shuffling). Returns (train, val, test). Validates chronological order.

---

### Dataset Build (`scripts/build_dataset_v1.py`)

**`pivot_features(conn) -> pd.DataFrame`**  
Pivots DuckDB `features` table (long format) to wide format. Filters features with >=80% completeness. Quotes column names to handle dots. Returns DataFrame with 1 row per timestamp.

**`add_target_variables(df) -> pd.DataFrame`**  
Adds forward return targets: `target_return_1` (1-day), `target_return_5` (5-day), `target_return_10` (10-day). Uses `df['close'].pct_change(N).shift(-N)`.

---

## REST Endpoints (RAGD)

**`GET /health`**  
Health check: returns `{"ok": true, "active_chunks": N, "chunks": M, "status": "ok"}`.

**`POST /query`**  
Unified query: `{"q": "...", "top_k": 5, "mode": "hybrid"}`. Returns ranked chunks with scores.

**`POST /index`**  
Index files: `{"path": "...", "paths": [...]}`. Rebuilds HNSW after completion.

**`POST /session/start`**  
Start session: `{"agent_name": "...", "role": "..."}`. Returns `{"session_id": "sess_...", "started_at": "..."}`.

**`POST /session/end`**  
End session: `{"session_id": "...", "status": "completed", "summary": "..."}`. Returns `{"ok": true}`.

**`POST /memory/decision`**  
Store decision: `{"session_id": "...", "decision": "...", "rationale": "...", "filepath": "..."}`. Returns `{"id": N, "decision_id": N}`.

**`GET /todos`**  
List TODOs: `?status=open&priority=5&limit=50`. Returns `{"todos": [{...}]}`.

**`POST /todos`**  
Create TODO: `{"filepath": "...", "line": N, "content": "...", "priority": N}`. Returns `{"todo_id": N}`.

**`GET /temporal/commits`**  
List recent commits: `?limit=20`. Returns `{"commits": [{...}]}`.

---

## CLI Commands

**`dominion doctor [--json] [--strict]`**  
Health check: pytest, mypy, ruff, RAGD, data pipeline, MT5. Returns overall status (`pass` | `warn` | `fail`).

**`dominion agent init --name NAME --role ROLE`**  
Start agent session. Returns `session_id`.

**`dominion agent task create --title TITLE [--kind KIND] [--scope-file FILE]...`**  
Create task. Returns `task_id`. Runs safety checks.

**`dominion agent task update --task TASK_ID --status STATUS [--evidence-json FILE]`**  
Update task status. Requires evidence for `done`.

**`dominion agent review --task TASK_ID [--strict]`**  
Adversarial review. Returns verdict + findings.

**`dominion agent complexity [--package PKG] [--all]`**  
Complexity report. Shows score vs budget, warnings, remediation.

**`dominion search QUERY [--top-k N]`**  
Search codebase via RAGD. Returns top-k chunks.

**`dominion data run [--sources SOURCE...]`**  
Run data pipeline. Fetches sources, fuses prices, computes features, generates report.

---

## SQL Tables

### DuckDB (`data/dominion.duckdb`)

**`gold_master`** — Fused OHLCV data: `timestamp`, `open`, `high`, `low`, `close`, `volume`, `fused_price`, `fused_confidence`, `source_weights_json`, `anomaly_flag`, `regime`.

**`gold_raw`** — Raw OHLCV from each source: `source`, `timestamp`, `open`, `high`, `low`, `close`, `volume`, `fetch_time`, `quality_score`.

**`features`** — Long-format features: `timestamp`, `feature_name`, `feature_value`. ~500k rows (1256 timestamps × 400 features).

**`ic_tracking`** — IC per feature: `feature_name`, `timestamp`, `ic`, `pval`. Used to filter low-IC features.

**`macro_data`** — Economic indicators: `series_id`, `timestamp`, `value`, `series_name`.

**`cot_data`** — COT positions: `report_date`, `commercial_long`, `commercial_short`, `noncommercial_long`, `noncommercial_short`, `open_interest`.

**`pipeline_runs`** — Pipeline run metadata: `run_id`, `started_at`, `completed_at`, `status`, `sources_fetched`, `features_computed`, `errors_json`.

---

### SQLite (`~/.dominion/agent_os.db`)

**`agent_sessions_v2`** — Agent sessions: `session_id`, `agent_name`, `role`, `status`, `started_at`, `ended_at`, `last_heartbeat`, `git_branch`, `git_commit_start`, `git_commit_end`, `parent_session_id`, `metadata_json`.

**`agent_tasks`** — Tasks: `task_id`, `title`, `description`, `kind`, `priority`, `status`, `created_at`, `updated_at`, `claimed_by_session`, `parent_task_id`, `scope_json`, `validation_json`, `acceptance_json`, `risk_json`, `tags_json`, `evidence_json`.

**`agent_claims`** — Task claims: `claim_id`, `task_id`, `session_id`, `claimed_at`, `expires_at`, `released_at`, `status`.

**`agent_locks`** — File locks: `lock_id`, `session_id`, `filepath`, `mode`, `acquired_at`, `released_at`, `last_heartbeat`, `status`.

**`agent_reviews`** — Adversarial reviews: `review_id`, `task_id`, `verdict`, `score`, `findings_json`, `commands_json`, `summary`, `created_at`.

---

### SQLite (`~/.ragd/ragd.db`)

**`nodes`** — RAGD chunks: `chunk_id`, `document_id`, `chunk_type`, `chunk_text`, `start_line`, `end_line`, `symbols_json`, `tags_json`, `metadata_json`, `created_at`.

**`edges`** — Graph edges: `edge_id`, `source_chunk_id`, `target_chunk_id`, `edge_type` (`hnsw` | `call` | `import` | `ref`), `weight`, `layer`.

**`documents`** — File metadata: `document_id`, `filepath`, `content_hash`, `indexed_at`, `deleted`, `git_commit`.

**`embedding_cache`** — Embedding cache: `text_hash`, `embedding_blob`, `model`, `created_at`. 7161 entries, ~21 MB.

---

## File Formats

**Parquet (`data/*.parquet`)** — Snappy-compressed columnar data. train_v1.parquet (360 rows × 355 cols), val_v1.parquet (80 rows), test_v1.parquet (72 rows).

**JSON (`reports/*.json`)** — Pipeline results, baseline metrics, dataset manifests. SHA-256 hashes for reproducibility.

**Markdown (`reports/*.md`)** — Intelligence reports, technical docs. Pipeline reports (~100 lines), technical docs (~500-2000 lines).

**CSV** — MT5 data exports (temp files, not persisted).

---

## Environment Variables

**`DOMINION_ROOT`** — Repo root (default: `~/Dominion`)

**`DOMINION_HOME`** — Data directory (default: `~/.dominion`)

**`RAGD_URL`** — RAGD URL (default: `http://127.0.0.1:7474`)

**`NOMIC_API_KEY`** — Nomic embedding API key

---

## Constants

**`COMPLEXITY_BUDGETS`** (`dominion_agent/complexity.py`)  
Per-package score limits: `dominion_loader: 50.0`, `dominion_ai: 130.0`, `dominion_agent: 350.0`, etc.

**`TASK_TRANSITIONS`** (`dominion_agent/types.py`)  
Valid task status transitions: `open → {in_progress, blocked, abandoned}`, `in_progress → {done, blocked, abandoned}`, etc.

**`EXCLUDED_FEATURES`** (`scripts/build_dataset_v1.py`)  
Leakage-contaminated features: `regime_tactical`, `regime_prob_trend_up`, `regime_prob_trend_down`, `regime_prob_ranging`, `regime_prob_crisis`.

**`TRAIN_END`** / **`VAL_END`** (`scripts/build_dataset_v1.py`)  
Temporal split boundaries: `TRAIN_END = "2024-11-15"`, `VAL_END = "2025-08-18"`.

---

## Conventions

**Naming:**
- Classes: PascalCase (`KalmanFilterBank`)
- Functions: snake_case (`compute_ic`)
- Constants: UPPER_SNAKE_CASE (`COMPLEXITY_BUDGETS`)
- IDs: prefix + underscore + hex (`sess_abc123`, `task_def456`)

**Timestamps:**
- Unix epoch (seconds) for SQLite storage
- ISO 8601 strings for JSON/logs
- pandas Timestamp for DataFrames

**File Paths:**
- Absolute paths for DB storage
- Relative paths for display (relative to `DOMINION_ROOT`)

**JSON:**
- NaN/inf converted to `null` before serialization
- Frontmatter for Markdown (YAML between `---` delimiters)

---

## Related

- [PYTHON_API_REFERENCE.md](../05_API/PYTHON_API_REFERENCE.md) — Python API docs
- [RAGD_REST_API.md](../05_API/RAGD_REST_API.md) — RAGD HTTP endpoints
- [CLI_REFERENCE.md](../05_API/CLI_REFERENCE.md) — CLI commands
- [DEPENDENCY_MAP.md](../01_ARCHITECTURE/DEPENDENCY_MAP.md) — Module dependencies
- [DATA_FLOW_EXPANSION.md](../01_ARCHITECTURE/DATA_FLOW_EXPANSION.md) — Data flows

---

**Last Updated:** 2026-05-19  
**Verified By:** Claude Code (Sonnet 4.5)  
**Review Status:** ✓ All symbols verified against source code
