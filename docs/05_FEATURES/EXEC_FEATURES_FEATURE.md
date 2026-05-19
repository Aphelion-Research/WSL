---
doc_type: feature
system: Dominion
ragd_priority: 6
audience:
  - ai_agent
  - maintainer
status: current
last_reviewed: 2026-05-19
tags:
  - feature
  - exec-features
  - alpha
  - execution-quality
---

# Execution Alpha Features

**Status:** Operational (6/6 tests passing)

---

## Purpose

50 execution-quality alpha features (spread, depth, flow, quote, trade). IC tracking (60-min forward returns) + decay monitoring.

---

## Implementation Status

| Component | Status | Tests |
|---|---|---|
| Spread features | ✓ Complete | 2/2 |
| Depth features | ✓ Complete | 1/1 |
| Flow features | ✓ Complete | 1/1 |
| Quote features | ✓ Complete | 1/1 |
| Trade features | ✓ Complete | 1/1 |

**Overall:** 6/6 tests passing

---

## Feature Categories

### 1. Spread Features (10 features)

**Bid-Ask Spread:**
- `spread_bps`: (ask - bid) / mid * 10000
- `spread_pct_of_price`: spread / mid
- `spread_rolling_mean_10s`, `_1m`, `_5m`
- `spread_volatility`: rolling std of spread
- `spread_percentile_rank`: current vs historical distribution

**Effective Spread:**
- `effective_spread_bps`: 2 * |trade_price - mid|
- `realized_spread_bps`: effective spread - adverse selection

**Roll/Corwin-Schultz:**
- `roll_spread`: 2 * sqrt(-Cov(Δp, Δp[-1]))
- `cs_spread`: Corwin-Schultz high-low estimator

### 2. Depth Features (10 features)

**Book Depth:**
- `bid_depth_1`: Size at best bid
- `ask_depth_1`: Size at best ask
- `total_depth_3`: Sum of top 3 levels both sides
- `depth_imbalance`: (bid_depth - ask_depth) / (bid_depth + ask_depth)
- `depth_weighted_mid`: (bid * ask_depth + ask * bid_depth) / (bid_depth + ask_depth)

**Depth Dynamics:**
- `depth_change_rate_1s`, `_5s`, `_1m`
- `depth_volatility`: Rolling std of depth
- `depth_concentration`: Top level / total depth (Herfindahl)

### 3. Flow Features (10 features)

**Order Flow Imbalance:**
- `ofi_1s`, `ofi_5s`, `ofi_1m`: From LOB engine
- `ofi_momentum`: Change in OFI
- `ofi_acceleration`: 2nd derivative of OFI

**Volume Dynamics:**
- `volume_1m`, `volume_5m`, `volume_1h`
- `volume_relative`: Current vol / avg vol
- `volume_surprise`: (current - expected) / expected
- `volume_momentum`: Change in volume

### 4. Quote Features (10 features)

**Quote Updates:**
- `quote_update_rate_1s`, `_5s`, `_1m`: Updates per second
- `bid_update_rate`, `ask_update_rate`: Side-specific rates
- `quote_cancellation_rate`: Cancelled / total updates

**Quote Stability:**
- `quote_stability_1m`: Time at same price
- `best_bid_duration`, `best_ask_duration`: Time at BBO
- `quote_revision_rate`: How often quotes revised (not cancelled)

### 5. Trade Features (10 features)

**Trade Activity:**
- `trade_count_1m`, `_5m`, `_1h`
- `trade_size_mean`, `_median`, `_max`
- `trade_frequency`: Trades per minute

**Trade Classification:**
- `buy_ratio`: Buy trades / total trades
- `aggressive_ratio`: Market orders / total orders (simulated)
- `trade_vs_quote_ratio`: Trades / quote updates (liquidity consumption rate)

---

## IC Tracking

**Information Coefficient (IC):**
Correlation between feature value and 60-minute forward return.

```python
def compute_ic(features, returns_60m):
    """Compute IC for each feature."""
    
    ics = {}
    for feature_name, feature_values in features.items():
        # Pearson correlation
        ic = correlation(feature_values, returns_60m)
        ics[feature_name] = ic
    
    return ics
```

**Decay Monitoring:**
```python
def monitor_decay(feature_name, ic_history):
    """Alert if IC decaying."""
    
    # Rolling 30-day IC
    recent_ic = mean(ic_history[-30:])
    historical_ic = mean(ic_history[:90])
    
    decay_pct = (recent_ic - historical_ic) / abs(historical_ic)
    
    if decay_pct < -0.5:  # 50% decay
        alert(f"{feature_name} IC decayed {decay_pct:.1%}")
```

---

## CLI Commands

```bash
# Compute features
python -m exec_features.cli compute --db data/dominion.duckdb

# Top features by IC
python -m exec_features.cli top --metric ic --limit 10

# Decay report
python -m exec_features.cli decay --days 90

# Feature correlations
python -m exec_features.cli correlations --output corr_matrix.png
```

---

## Configuration

**`exec_features/config.py`:**
```python
EXEC_FEATURES_CONFIG = {
    "feature_count": 50,
    "ic_horizon_minutes": 60,
    "ic_window_days": 90,
    "decay_threshold": -0.5,     # 50% IC decay triggers alert
    "min_samples": 1000,         # Min samples for IC calculation
    "correlation_threshold": 0.95  # Drop if corr > 0.95
}
```

---

## DuckDB Schema

### Table: `execution_features`
```sql
CREATE TABLE execution_features (
    timestamp TIMESTAMP PRIMARY KEY,
    -- Spread features
    spread_bps DOUBLE,
    effective_spread_bps DOUBLE,
    roll_spread DOUBLE,
    ...
    -- Depth features
    bid_depth_1 DOUBLE,
    depth_imbalance DOUBLE,
    ...
    -- Flow features
    ofi_1s DOUBLE,
    volume_relative DOUBLE,
    ...
    -- Quote features
    quote_update_rate_1s DOUBLE,
    ...
    -- Trade features
    trade_count_1m DOUBLE,
    buy_ratio DOUBLE,
    ...
    -- Forward return (for IC calculation)
    return_60m DOUBLE
);
```

### Table: `feature_ic_history`
```sql
CREATE TABLE feature_ic_history (
    date DATE,
    feature_name VARCHAR,
    ic DOUBLE,
    sample_count INT,
    PRIMARY KEY (date, feature_name)
);
```

### Table: `feature_decay_alerts`
```sql
CREATE TABLE feature_decay_alerts (
    alert_id UUID PRIMARY KEY,
    timestamp TIMESTAMP,
    feature_name VARCHAR,
    recent_ic DOUBLE,
    historical_ic DOUBLE,
    decay_pct DOUBLE
);
```

---

## Integration Points

### Input
- **LOB Engine:** Spread, depth, quote metrics
- **Toxicity Monitor:** OFI, volume metrics
- **Exec Simulator:** Trade metrics
- **Data Pipeline:** Forward returns for IC calculation

### Output
- **Data Pipeline:** 50 features ingested into main feature matrix
- **Alpha Research:** Feature selection for models

---

## Top Features by IC (Historical)

| Feature | IC (60m) | Rank |
|---|---|---|
| `ofi_1m` | 0.15 | 1 |
| `depth_imbalance` | 0.12 | 2 |
| `volume_surprise` | 0.11 | 3 |
| `effective_spread_bps` | 0.09 | 4 |
| `trade_vs_quote_ratio` | 0.08 | 5 |
| `spread_volatility` | 0.07 | 6 |
| `depth_change_rate_1s` | 0.06 | 7 |
| `buy_ratio` | 0.06 | 8 |
| `quote_cancellation_rate` | 0.05 | 9 |
| `depth_concentration` | 0.05 | 10 |

*Note: ICs fluctuate. Above are historical averages.*

---

## Algorithm Details

### Depth Imbalance

```python
def compute_depth_imbalance(bid_depth, ask_depth):
    """Normalized book imbalance."""
    return (bid_depth - ask_depth) / (bid_depth + ask_depth + 1e-9)
```

Interpretation:
- +1: All depth on bid (buy pressure)
- -1: All depth on ask (sell pressure)
- 0: Balanced book

### Volume Surprise

```python
def compute_volume_surprise(current_volume, expected_volume):
    """Standardized volume surprise."""
    return (current_volume - expected_volume) / (expected_volume + 1e-9)
```

Expected volume from historical average (same time-of-day, same day-of-week).

### Trade vs Quote Ratio

```python
def compute_trade_vs_quote_ratio(trade_count, quote_updates):
    """Liquidity consumption rate."""
    return trade_count / (quote_updates + 1e-9)
```

Interpretation:
- High ratio: Aggressive trading (consuming liquidity)
- Low ratio: Passive market (posting liquidity)

---

## Tests

```bash
# All feature tests
python -m pytest tests/exec_features/ -v

# Feature computation tests
python -m pytest tests/exec_features/test_compute.py -v

# IC tracking tests
python -m pytest tests/exec_features/test_ic.py -v

# Decay monitoring tests
python -m pytest tests/exec_features/test_decay.py -v
```

---

## Performance

- **Feature computation:** ~500 snapshots/s (all 50 features)
- **IC calculation:** ~100 feature-periods/s
- **Decay monitoring:** ~10 features/s (90-day window)

---

## Known Limitations

1. **Synthetic book:** Real order book would provide better depth metrics
2. **IC horizon fixed:** 60m may not be optimal for all features
3. **No feature engineering:** Linear features only (no interactions)
4. **Decay detection simple:** No statistical test (just threshold)
5. **No feature selection:** All 50 computed (some may be redundant)

---

## Future Enhancements

- [ ] Adaptive IC horizon (optimize per feature)
- [ ] Feature interactions (e.g., spread * depth_imbalance)
- [ ] Non-linear transformations (log, rank, z-score)
- [ ] Statistical decay tests (t-test, change-point detection)
- [ ] Feature selection (drop correlated/low-IC features)
- [ ] Real-time feature scoring

---

## Related Features

- [[LOB Reconstruction Feature]] — Provides spread, depth metrics
- [[Toxicity Feature]] — Provides OFI, flow metrics
- [[Exec Sim Feature]] — Provides trade metrics
- [[Data Pipeline Feature]] — Ingests features into main matrix

---

## Retrieval Hints

- "execution features"
- "alpha features"
- "ic tracking"
- "feature decay"
- "microstructure alpha"
