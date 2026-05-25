# Python → C++ Migration Status

**Date:** 2026-05-25  
**Goal:** Migrate entire Dominion system to C++ (except Python-only training + ONNX export)

## Migration Targets

| Component | Python LOC | Status | Priority |
|-----------|------------|--------|----------|
| **data_pipeline/** | 4,100 | 🔄 In Progress | P0 |
| **domdata/** | 1,300 | 📋 Planned | P1 |
| **ragd_bus/** | 635 | 📋 Planned | P2 |
| **dominion_agent/** | ~2,000 | 📋 Planned | P3 |
| **ragd/** | N/A | ✅ Already C++ | - |
| **cpp/kernels/** | N/A | ✅ Already C++ | - |

## Data Pipeline (dominion_cpp/) — Current Status

### ✅ Completed Modules (Scaffolding + Core Logic)

**Infrastructure (1,200 LOC):**
- `types.hpp` — Core data structures (Tick, Bar, FusedBar, Feature, etc.)
- `config.hpp/cpp` — Config from environment, Kalman params, windows, thresholds
- `storage.hpp/cpp` — SQLite wrapper + DuckDB schema (11 tables DDL)
- `pipeline.hpp/cpp` — Main orchestrator (9 phases: init → fetch → fuse → features → report)
- `bus.hpp/cpp` — WebSocket client + publisher (event-driven architecture)

**Fusion (600 LOC):**
- `fusion/kalman.cpp` — 6-timescale Kalman filter bank + trust scoring + fusion
- `fusion/bridge.cpp` — Brownian bridge synthetic tick reconstruction
- `fusion/conflict.cpp` — Byzantine fault tolerance + outlier quarantine

**Features (800 LOC):**
- `features/store.cpp` — Feature validation (clip ±100σ), IC computation (rolling correlation)
- `features/primitives.cpp` — Rolling statistics (mean, std, ema, diff, returns, drawdown)
- `features/price.cpp` — Price features (returns, Sharpe, z-score, drawdown)
- `features/microstructure.cpp` — Amihud illiquidity, realized variance
- Stubs: crossasset, macro, regime, calendar, cot

**Health (400 LOC):**
- `health/monitor.cpp` — Staleness checks, gap detection, drift detection
- `health/anomaly.cpp` — Price/volume anomaly detection (z-score), source divergence
- `health/report.cpp` — Markdown report generation + RAGD HTTP POST

**Entry Points (300 LOC):**
- `main.cpp` — Daemon with signal handling
- `cli.cpp` — CLI tool (run, status, doctor, features, backfill commands)

**MT5 (300 LOC):**
- `mt5/collector.cpp` — JSONL tick/bar collector (dedup, heartbeat)
- `mt5/safety.cpp` — Read-only guard (blocks order_send/order_check)

### 🚧 TODO (Stub Implementations)

**Data Sources (5 modules):**
- `sources/yahoo.cpp` — Fetch GC=F, GLD via Yahoo Finance API (retry + validation)
- `sources/fred.cpp` — Fetch 10 FRED series (DGS10, DXY, VIX, CPI, etc.)
- `sources/alphavantage.cpp` — GLD ETF with 23h cache + rate limiting (13s delay)
- `sources/cot.cpp` — Download ZIP, parse Excel, extract gold 088691
- `sources/mt5.cpp` — Subprocess call to domdata CLI or native MT5 API

**Storage Layer:**
- Implement all SQLite prepared statement CRUD operations (15 methods)
- Transaction management
- Efficient bulk inserts (features table = 400k+ rows/run)

**Feature Modules (6 modules, ~150 features missing):**
- **Price:** Hurst exponent, autocorrelation (lags 1,5,10), fractional differentiation, ADF test
- **Microstructure:** Roll spread, Corwin-Schultz, Kyle's lambda, VPIN, bipower variation
- **Cross-asset:** Rolling correlation/beta (10 series × 6 windows), lead-lag, Granger causality
- **Macro:** Real yield (TIPS), yield curve slope, DXY z-score, CPI surprise, Fed proximity
- **Regime:** HMM (4-state tactical regime) + time-based micro regime (london/ny/asian)
- **Calendar:** Day of week, month, quarter, month-end, options expiry, seasonal (Q4, Ramadan)
- **COT:** Net commercial/spec percentile (52/104/252 week windows), momentum (4/8/12 week)

**Testing:**
- Unit tests for Kalman filter (predict/update correctness)
- Integration test (full pipeline with mock sources)
- Point-in-time safety tests (verify no lookahead in features)

## Build System

**CMakeLists.txt:**
- ✅ C++20, CMake 3.20+
- ✅ FetchContent for nlohmann/json, cpp-httplib, websocketpp
- ✅ System deps: OpenSSL, SQLite3, libuuid
- ✅ OpenMP auto-detection
- ✅ Optional ONNX Runtime support (`-DDOMINION_ENABLE_ONNX=ON`)
- ✅ 2 targets: `dominion_daemon`, `dominion_cli`

## Implementation Estimates

| Task | Effort | Complexity |
|------|--------|------------|
| Data sources (5) | 2 days | Medium (HTTP APIs, retry, validation) |
| Storage layer | 1 day | Low (SQLite boilerplate) |
| Price features | 1 day | Medium (Hurst, autocorr, ADF requires statsmodels port) |
| Microstructure | 1 day | Medium (Roll spread, Kyle's lambda formulas) |
| Cross-asset | 2 days | High (Granger causality = VAR model + F-test) |
| Macro features | 0.5 days | Low (mostly arithmetic) |
| Regime features | 2 days | High (HMM = Baum-Welch algorithm or Python bridge) |
| Calendar features | 0.5 days | Low (date arithmetic) |
| COT features | 0.5 days | Low (percentile + momentum) |
| Testing | 1 day | Medium (setup fixtures, mocks) |
| **TOTAL** | **12 days** | **One developer, full-time** |

## Dependencies on External Systems

**RAGD (already C++):**
- `ragd/src/` — HTTP server at 127.0.0.1:7474
- Pipeline sends daily reports via POST `/memory/remember`

**MT5 (Python domdata for now):**
- `domdata/domdata.py` CLI works via subprocess
- C++ MT5 native API requires MetaTrader5 SDK (Windows) or Wine bridge (Linux)
- **Decision:** Keep Python domdata, call via subprocess in `sources/mt5.cpp`

**Training (stays Python):**
- `hydra/` — Python training scripts
- Reads features from DuckDB
- Exports to ONNX for C++ inference (optional)

## Performance Expectations

**Baseline (Python):**
- Full pipeline: 8-12 minutes
- Memory: 4-6GB peak
- CPU: 1 core (no parallelism)

**Target (C++):**
- Full pipeline: <5 minutes (2-3× speedup)
- Memory: <2GB peak (half Python)
- CPU: Multi-core (OpenMP feature computation)

**Bottlenecks:**
- Yahoo/FRED/AV network latency: 2-3 minutes (unavoidable)
- Feature computation: 30 seconds → 5 seconds (OpenMP)
- Kalman fusion: 5 seconds → <1 second (native loops)

## Next Steps

1. **Implement data sources** (yahoo, fred) — highest priority, blocks testing
2. **Storage layer** — enables feature persistence
3. **Complete price + microstructure features** — most features depend on these
4. **HMM regime decision:**
   - Option A: Python bridge (subprocess to existing regime_safe.py)
   - Option B: Native C++ Baum-Welch (2 days implementation)
   - Option C: Pre-trained HMM ONNX export (requires ONNX Runtime)
5. **Integration tests** — verify end-to-end with real data

## Migration Roadmap

**Phase 1: Data Pipeline (CURRENT)** — 12 days
- Complete dominion_cpp/ implementation
- Parity with Python data_pipeline/

**Phase 2: MT5 Collector (P1)** — 5 days
- Native C++ MT5 API bindings or Wine bridge
- Replace Python domdata/ with dominion_cpp/mt5/

**Phase 3: Event Bus (P2)** — 3 days
- Replace Python ragd_bus/ with C++ WebSocket server
- Integrate with existing RAGD C++ backend

**Phase 4: Agent OS (P3)** — 10 days
- Replace Python dominion_agent/ with C++ orchestrator
- Session management, task queue, locks, claims

**Phase 5: ONNX Inference (Optional)** — 3 days
- ONNX Runtime integration
- Load trained models from Python
- Real-time inference in C++ pipeline

**TOTAL:** 33 days (1.5 months, single developer)

## Success Criteria

1. ✅ **Full pipeline runs** without Python dependencies (except training)
2. ✅ **<5 minute runtime** for daily pipeline
3. ✅ **<2GB memory** peak usage
4. ✅ **All 400+ features** computed with point-in-time safety
5. ✅ **Event bus integration** publishes to RAGD
6. ✅ **CLI tool** provides status/doctor/features commands
7. ✅ **Read-only safety** blocks trading functions

## Notes

- **C++ standard:** C++20 (consistent with ragd/ C++17, but uses newer features)
- **Coding style:** Follows ragd/ conventions (RAII, move semantics, exceptions for errors)
- **WebSocket:** websocketpp (same as potential ragd_bus/ C++ rewrite)
- **JSON:** nlohmann/json (same as ragd/)
- **Database:** SQLite3 (DuckDB via command-line tool, native C++ API possible)

## Questions for Review

1. **HMM regime:** Python bridge or native C++?
2. **MT5 API:** Subprocess to Python domdata or native API?
3. **DuckDB:** SQLite sufficient or need native DuckDB C++ API?
4. **ONNX:** Enable by default or optional feature?
5. **Testing:** Unit tests only or integration tests with real Yahoo/FRED APIs?
