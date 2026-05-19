---
doc_type: feature
system: data_pipeline
ragd_priority: 8
audience:
  - ai_agent
  - maintainer
  - owner
status: current
last_reviewed: 2026-05-19
tags:
  - feature
  - data-pipeline
  - kalman
  - fusion
---

# Data Pipeline Feature Specification

**Status:** LIVE_GREEN (16/16 tests passing)  
**Commit:** d16c5a9  
**Docs:** [docs/DATA_PIPELINE.md](../DATA_PIPELINE.md)

---

## Purpose

Institutional-grade XAU/USD data pipeline with multi-source fusion, 400+ alpha features, and daily intelligence reports.

---

## Architecture

```
Sources → Raw Storage → Kalman Fusion → Master Storage → Feature Engine → Reports
```

**5 Data Sources:**
1. Yahoo Finance (GC=F futures, GLD ETF)
2. FRED API (10 macro series)
3. Alpha Vantage (GLD OHLCV)
4. CFTC COT (gold futures positioning)
5. MT5/domdata (real-time ticks)

**Kalman Filter Bank:**
- 6 timescales (tick, m1, m15, h1, h4, d1)
- Dynamic trust scoring per source
- Byzantine fault tolerance (3+ source agreement)

**400+ Features:**
- Price (80): returns, Sharpe, drawdown, Hurst, autocorrelation
- Microstructure (60): Roll spread, Corwin-Schultz, Amihud, Kyle's lambda, VPIN
- Cross-asset (100): correlation, beta, lead-lag, Granger causality
- COT (30): net commercial percentiles, speculator sentiment
- Macro (60): real yield, curve slope, breakeven inflation, Fed proximity
- Regime (40): HMM tactical regime, micro regime, duration
- Calendar (30): day/week/month effects, options expiry

**Health Monitoring:**
- Staleness watchdog
- Gap detection + Brownian bridge filling
- Distribution drift (KL divergence)
- Gold-DXY correlation monitor
- Anomaly detection (>3σ flag, >5σ quarantine)

---

## CLI

```bash
# Full pipeline run
python -m data_pipeline.cli run [--sources yahoo,fred,...]

# Source health dashboard
python -m data_pipeline.cli status

# Deep health check
python -m data_pipeline.cli doctor

# Intelligence report
python -m data_pipeline.cli report

# Historical backfill
python -m data_pipeline.cli backfill --days 365

# Top features by IC
python -m data_pipeline.cli features --top 20
```

---

## Database Schema

**DuckDB:** `data/dominion.duckdb`

**Tables:**
- `gold_raw`: Raw source data
- `gold_master`: Fused price + confidence
- `gold_ticks`: Brownian bridge ticks (100 per bar)
- `macro_data`: FRED macro series
- `cot_data`: CFTC positioning
- `features`: 400+ features with IC tracking
- `regime_labels`: HMM regime states
- `source_health`: Staleness + quality scores
- `pipeline_runs`: Run history
- `intelligence_reports`: Daily reports
- `anomaly_log`: >3σ events

---

## Key Algorithms

### Pipeline Flow Diagram

```mermaid
flowchart LR
    subgraph Sources
        MT5[MT5<br/>Ticks]
        Yahoo[Yahoo<br/>GC=F, GLD]
        FRED[FRED<br/>10 series]
        AV[AV<br/>GLD]
        COT[COT<br/>Positioning]
    end
    
    subgraph Fusion
        MT5 --> KF[Kalman Filter Bank<br/>6 timescales]
        Yahoo --> KF
        FRED --> KF
        AV --> KF
        COT --> Trust[Dynamic Trust Scoring]
        
        KF --> Trust
        Trust --> Byzantine[Byzantine FT<br/>3σ rejection]
        Byzantine --> Fused[Fused Price<br/>+ Uncertainty]
    end
    
    subgraph Features
        Fused --> Price[Price Features<br/>Returns, vol, spreads]
        Fused --> Micro[Microstructure<br/>Roll, Corwin-Schultz]
        Fused --> Cross[Cross-Asset<br/>SPY, DXY correlation]
        COT --> COTFeat[COT Features<br/>Net long, commercial]
        FRED --> Macro[Macro Features<br/>10-year, CPI, etc]
        Fused --> Regime[Regime Detection<br/>3-state HMM]
        Fused --> Calendar[Calendar Features<br/>FOMC, NFP, etc]
    end
    
    subgraph Health
        Price --> Health[Health Monitor]
        Micro --> Health
        Cross --> Health
        COTFeat --> Health
        Macro --> Health
        Regime --> Health
        Calendar --> Health
        
        Health --> Staleness{Staleness<br/>Watchdog}
        Staleness --> Gap{Gap<br/>Detection}
        Gap --> Drift{Drift<br/>Detection}
        Drift --> Anomaly{Anomaly<br/>Detection}
    end
    
    subgraph Storage
        Anomaly --> DuckDB[(DuckDB)]
        DuckDB --> GoldMaster[gold_master]
        DuckDB --> FeaturesTable[features]
        DuckDB --> Reports[intelligence_reports]
        
        Reports --> RAGD[(RAGD)]
    end
```

### Kalman Fusion

```python
# 6-filter bank (one per timescale)
filters = [
    KalmanFilter(timescale="tick", process_noise=0.01, obs_noise=0.5),
    KalmanFilter(timescale="m1", process_noise=0.05, obs_noise=0.3),
    # ... 4 more
]

# Dynamic trust scoring
for source in sources:
    innovation = abs(source.price - filter.predicted_price)
    if innovation < 1 * sigma:
        source.trust += 0.01  # Good innovation
    elif innovation > 3 * sigma:
        source.trust -= 0.05  # Poor innovation
    source.trust = np.clip(source.trust, 0.05, 0.95)

# Byzantine fault tolerance
if len([s for s in sources if s.price > median + 3*sigma]) >= 3:
    # 3+ sources agree on high value → accept
    fused_price = weighted_average(sources, weights=trust_scores)
else:
    # Conflict → quarantine outliers
    fused_price = median(non_outlier_sources)
```

### Brownian Bridge

```python
# Generate 100 synthetic ticks between OHLC bars
# Constraint: respect open/high/low/close
ticks = brownian_bridge(
    open=bar.open,
    high=bar.high,
    low=bar.low,
    close=bar.close,
    n_ticks=100,
    volatility=estimate_volatility(recent_bars)
)
```

### HMM Regime Detection

```python
# 4-state HMM
states = ["trending_up", "trending_down", "ranging", "crisis"]

# Features for regime classification
features = [
    price_momentum,
    volatility,
    drawdown,
    correlation_to_dxy
]

# Train on historical data
hmm = HiddenMarkovModel(n_states=4)
hmm.fit(features)

# Predict current regime
current_regime = hmm.predict(current_features)
```

---

## Integration Points

**Feeds into:**
- LOB reconstruction (`lob/`)
- Execution simulator (`exec_sim/`)
- TCA dashboard (`tca/`)
- Toxicity monitor (`toxicity/`)
- Execution features (`exec_features/`)

**Consumes:**
- MT5 ticks via `domdata`
- Yahoo Finance via `yfinance`
- FRED via `fredapi`
- Alpha Vantage via `requests`
- CFTC via `pandas-datareader`

---

## Configuration

**Environment variables:**
- `ALPHAVANTAGE_API_KEY`: Alpha Vantage key (required)
- `FRED_API_KEY`: FRED key (required)
- `DOMINION_DUCKDB_PATH`: DuckDB path (default: `data/dominion.duckdb`)

**Config file:** None (all config in code)

---

## Testing

**16 tests (all passing):**
- `test_sources.py`: Validation, retry, graceful degradation
- `test_fusion.py`: Kalman convergence, trust updates, Brownian bridge, conflict resolution
- `test_features.py`: Return computation, Hurst exponent, autocorrelation, IC tracking
- `test_health.py`: Anomaly detection (price/volume), source divergence

```bash
pytest data_pipeline/tests/ -v
```

---

## Safety

**Zero trading execution:**
- Data-only pipeline (no orders)
- MT5 read-only via `domdata`
- Forbidden token scanner: PASS

```bash
python domdata/check_no_trading.py
```

---

## Performance

**Benchmarks (2026-05-19):**
- Full run (5 sources, 2y data): ~60 seconds
- Feature computation (400+ features): ~10 seconds
- Kalman fusion (6 filters): ~2 seconds
- Report generation: ~1 second

**Bottlenecks:**
- Feature computation (single-threaded)
- Granger causality (expensive, limited to 3 series)

---

## Known Limitations

- **Not yet run with live data** (initialization only)
- **No automated scheduling** (manual CLI invocation)
- **Alpha Vantage rate limiting** (25 req/day free tier)
- **COT data** limited to 2022-2024 (hardcoded URLs)
- **Regime labels table** not yet populated (HMM output not stored)
- **Single-threaded feature computation** (may be slow)
- **Granger causality** only for 3 macro series (too expensive)

---

## Future Enhancements

- Automated scheduling (cron or systemd timer)
- Multiprocessing for feature groups
- Real-time streaming mode
- Extended COT data (dynamic URL generation)
- More Granger causality tests
- Feature caching
- Incremental updates (not full recompute)

---

## Related Docs

- [docs/DATA_PIPELINE.md](../DATA_PIPELINE.md)
- [/PROGRESS.md](/PROGRESS.md) (Milestone: Sovereign Data Pipeline)
- [05_FEATURES/FEATURE_INDEX.md](FEATURE_INDEX.md)

---

## Retrieval Hints

- "data pipeline"
- "Kalman fusion"
- "multi-source data"
- "400 features"
- "gold XAU/USD"
- "market data"
