# Dominion C++ Data Pipeline

High-performance XAU/USD quant research data pipeline written in C++20.

## Architecture

**Complete C++ rewrite** of Python data_pipeline (~4100 LOC → native C++):
- Multi-source Kalman fusion (Yahoo, FRED, AlphaVantage, COT, MT5)
- 400+ feature engineering (price, microstructure, cross-asset, macro, COT, regime, calendar)
- Health monitoring + anomaly detection
- WebSocket event bus integration
- DuckDB persistence
- RAGD intelligence reports

## Dependencies

### Build Requirements
- CMake 3.20+
- C++20 compiler (GCC 11+, Clang 14+)
- OpenSSL
- SQLite3
- libuuid

### Fetched by CMake
- nlohmann/json 3.11.3
- cpp-httplib 0.18.6
- websocketpp 0.8.2

### Optional
- OpenMP (auto-detected, enables parallel feature computation)
- ONNX Runtime (optional, enable with `-DDOMINION_ENABLE_ONNX=ON`)

## Build

```bash
cd dominion_cpp
mkdir build && cd build
cmake ..
make -j$(nproc)
```

Install:
```bash
sudo make install  # installs to /usr/local/bin
```

## Usage

### Run Pipeline
```bash
# Full pipeline (all sources)
dominion_daemon

# CLI interface
dominion_cli run

# Filter sources
dominion_cli run --sources yahoo,fred
```

### Health Monitoring
```bash
# Quick status
dominion_cli status

# Deep health check
dominion_cli doctor

# Top features by IC
dominion_cli features --top 50
```

### Environment Setup

Required environment variables:
```bash
export ALPHAVANTAGE_API_KEY="your_key"
export FRED_API_KEY="your_key"
export HOME="/home/user"  # for repo root detection
```

Optional:
```bash
export DOMDATA_MT5_LOGIN="12345"
export DOMDATA_MT5_SERVER="broker-server"
export DOMDATA_MT5_PASSWORD="secret"
export DOMDATA_MT5_PATH="/path/to/MT5"
```

## Implementation Status

### ✅ Complete
- Core pipeline orchestration
- Config from environment
- DuckDB schema
- Kalman filter bank (multi-timescale fusion + trust scoring)
- Brownian bridge tick reconstruction
- Event bus (WebSocket pub/sub)
- Rolling statistics primitives (mean, std, ema, diff, returns, drawdown)
- Feature validation + IC computation
- Health monitoring skeleton
- Anomaly detection
- Report generation
- CLI tool

### 🚧 TODO (Stub implementations)
- **Data sources** (yahoo, fred, alphavantage, cot, mt5) — all return "Not implemented"
- **Storage layer** (SQLite prepared statements for all CRUD operations)
- **Feature modules**:
  - Price: Hurst, autocorr, fractional diff, ADF
  - Microstructure: Roll spread, Corwin-Schultz, Kyle's lambda, VPIN
  - Cross-asset: Granger causality, lead-lag correlation, beta
  - Macro: Real yield, yield curve, Fed proximity
  - Regime: HMM (requires external lib or Python bridge), time-based micro regime
  - Calendar: Day of week, month, quarter, FOMC proximity
  - COT: Percentile rankings, momentum
- **MT5 Collector** (native API bindings or Wine subprocess bridge)
- **ONNX inference** (optional feature)

### Bridge Strategy for Complex Components

**HMM Regime Detection:**
- Option 1: Python bridge (subprocess call to existing Python HMM code)
- Option 2: Native implementation using Eigen + Baum-Welch algorithm
- Option 3: Use pre-trained HMM from Python ONNX export

**MT5 Data Collection:**
- Current Python domdata CLI works via subprocess
- Native option: Link against MetaTrader5 C++ SDK (Windows) or Wine bridge (Linux)
- Recommended: Keep Python domdata for now, call via subprocess

## Performance Targets

- Full pipeline run: <5 minutes (vs 8-12 minutes Python)
- Kalman fusion: <100ms for 1000 bars
- Feature computation: <1 second for 400 features × 1000 bars (with OpenMP)
- Memory: <2GB peak (vs 4-6GB Python)

## Integration Points

### RAGD C++ Server
- Already exists at `/home/Martin/Dominion/ragd/src/`
- HTTP POST to `http://127.0.0.1:7474/memory/remember`
- Daily intelligence reports

### Event Bus
- WebSocket at `ws://127.0.0.1:7474/bus`
- Topics: `pipeline.run.complete`, `pipeline.anomaly`, `pipeline.regime_change`
- Consumed by TUI, agent OS, downstream systems

### Python Training
- Reads features from DuckDB
- Trains models in Python (hydra/)
- Exports to ONNX for C++ inference

## Safety Guarantees

1. **Read-only MT5** — Trading functions blocked (order_send, order_check)
2. **Point-in-time safety** — All rolling operations lag by 1 bar (no lookahead)
3. **Graceful degradation** — Pipeline continues if ≥1 source succeeds
4. **Audit trail** — All runs logged with UUID, errors, metadata

## Development

### Adding a Data Source

1. Implement `DataSource` interface in `src/sources/your_source.cpp`
2. Return `SourceResult` with bars/macro/cot data
3. Add to `Pipeline::fetch_sources()` source list
4. Update CMakeLists.txt

### Adding Features

1. Implement in `src/features/your_module.cpp`
2. Return `FeatureMap` (name → values vector)
3. Call from `Pipeline::compute_features()`
4. Features auto-validated + IC computed

## Testing

```bash
# Build tests
cmake -DDOMINION_BUILD_TESTS=ON ..
make -j$(nproc)

# Run tests
ctest -V
```

## License

Proprietary — Matin & Dan @ Dominion V2
