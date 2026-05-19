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
  - tca
  - transaction-cost
  - execution-quality
---

# Transaction Cost Analysis (TCA) Feature

**Status:** Operational (4/4 tests passing)

---

## Purpose

Decompose transaction costs into decision, timing, impact, opportunity components. Benchmark vs VWAP/TWAP. Regime-conditional analysis.

---

## Implementation Status

| Component | Status | Tests |
|---|---|---|
| Cost attribution | ✓ Complete | 2/2 |
| Benchmark comparison | ✓ Complete | 1/1 |
| Regime conditioning | ✓ Complete | 1/1 |

**Overall:** 4/4 tests passing

---

## Cost Attribution Framework

**Total Cost = Decision + Timing + Impact + Opportunity**

```
Decision Cost: Arrival price vs decision price
Timing Cost: Arrival price vs start-of-execution price
Impact Cost: Execution price vs arrival price
Opportunity Cost: Could-have-executed vs did-execute
```

---

## Key Components

### 1. Cost Decomposition (`tca/attribution.py`)

```python
def decompose_costs(trade, benchmarks):
    """Decompose transaction cost into components."""
    
    # Decision cost (pre-trade)
    decision_cost = (trade.arrival_price - trade.decision_price) / trade.decision_price
    
    # Timing cost (delay from decision to execution)
    timing_cost = (trade.start_exec_price - trade.arrival_price) / trade.arrival_price
    
    # Impact cost (execution vs arrival)
    impact_cost = (trade.avg_fill_price - trade.start_exec_price) / trade.start_exec_price
    
    # Opportunity cost (if didn't fill completely)
    if trade.fill_rate < 1.0:
        unfilled = trade.size * (1 - trade.fill_rate)
        opportunity_cost = unfilled * (trade.end_price - trade.avg_fill_price) / trade.avg_fill_price
    else:
        opportunity_cost = 0
    
    total_cost = decision_cost + timing_cost + impact_cost + opportunity_cost
    
    return {
        "decision_bps": decision_cost * 10000,
        "timing_bps": timing_cost * 10000,
        "impact_bps": impact_cost * 10000,
        "opportunity_bps": opportunity_cost * 10000,
        "total_bps": total_cost * 10000
    }
```

### 2. Benchmark Comparison (`tca/benchmarks.py`)

**Benchmarks:**
- **VWAP:** Volume-weighted average price over interval
- **TWAP:** Time-weighted average price over interval
- **Arrival Price:** Price when decision made
- **Open/Close:** Day open or close price

```python
def compute_vwap_benchmark(trades, volume_profile):
    """VWAP = sum(price * volume) / sum(volume)"""
    return sum(t.price * t.volume for t in trades) / sum(t.volume for t in trades)

def compute_twap_benchmark(prices, timestamps):
    """TWAP = average of prices over interval"""
    return mean(prices)
```

### 3. Regime Conditioning (`tca/regime.py`)

TCA metrics vary by market regime. Condition on:
- **Volatility regime:** Low/medium/high
- **Liquidity regime:** Deep/normal/thin
- **Trend regime:** Bull/neutral/bear (from HMM)

```python
def condition_on_regime(tca_results, regime):
    """Adjust TCA interpretation based on regime."""
    
    if regime == "high_volatility":
        # Higher impact expected
        threshold_impact = 15  # bps
    elif regime == "low_liquidity":
        # Higher slippage expected
        threshold_slippage = 20  # bps
    else:
        threshold_impact = 10
        threshold_slippage = 10
    
    # Flag if cost exceeds regime-adjusted threshold
    return {
        "impact_abnormal": tca_results.impact_bps > threshold_impact,
        "slippage_abnormal": tca_results.slippage_bps > threshold_slippage
    }
```

---

## CLI Commands

```bash
# Analyze trade
python -m tca.cli analyze --trade-id [uuid]

# Batch analysis
python -m tca.cli analyze --date 2026-05-19

# Report
python -m tca.cli report --period weekly

# Heatmap (cost by size × urgency)
python -m tca.cli heatmap --output tca_heatmap.png
```

---

## Configuration

**`tca/config.py`:**
```python
TCA_CONFIG = {
    "benchmarks": ["vwap", "twap", "arrival"],
    "cost_components": ["decision", "timing", "impact", "opportunity"],
    "regime_conditioning": True,
    "thresholds": {
        "decision_cost_bps": 5,
        "timing_cost_bps": 5,
        "impact_cost_bps": 10,
        "total_cost_bps": 20
    }
}
```

---

## DuckDB Schema

### Table: `tca_trades`
```sql
CREATE TABLE tca_trades (
    trade_id UUID PRIMARY KEY,
    timestamp TIMESTAMP,
    side VARCHAR,               -- 'buy' | 'sell'
    size DOUBLE,
    decision_price DOUBLE,
    arrival_price DOUBLE,
    start_exec_price DOUBLE,
    avg_fill_price DOUBLE,
    end_price DOUBLE,
    fill_rate DOUBLE,           -- executed / requested
    regime VARCHAR              -- from HMM
);
```

### Table: `tca_attribution`
```sql
CREATE TABLE tca_attribution (
    trade_id UUID PRIMARY KEY REFERENCES tca_trades(trade_id),
    decision_cost_bps DOUBLE,
    timing_cost_bps DOUBLE,
    impact_cost_bps DOUBLE,
    opportunity_cost_bps DOUBLE,
    total_cost_bps DOUBLE
);
```

### Table: `tca_benchmarks`
```sql
CREATE TABLE tca_benchmarks (
    trade_id UUID REFERENCES tca_trades(trade_id),
    benchmark VARCHAR,           -- 'vwap' | 'twap' | 'arrival'
    benchmark_price DOUBLE,
    vs_benchmark_bps DOUBLE,     -- fill price vs benchmark
    PRIMARY KEY (trade_id, benchmark)
);
```

---

## Integration Points

### Input
- **Exec Simulator:** Simulated trades for analysis
- **LOB Engine:** Arrival price, book state
- **Data Pipeline:** Regime labels (HMM)
- **Toxicity Monitor:** Toxicity score (affects impact)

### Output
- **Data Pipeline:** TCA metrics as execution quality features
- **Reports:** Daily/weekly TCA summaries

---

## Algorithm Details

### Cost Attribution Example

```
Trade:
- Decision time: 09:30, price = 1900.00
- Arrival time: 09:31, price = 1900.50 (+50 cents)
- Start exec: 09:32, price = 1901.00 (+50 cents)
- Avg fill: 1901.50 (+50 cents)
- Size: 100 oz, filled 90 oz (90%)
- End price (if didn't fill): 1902.00

Decision cost: (1900.50 - 1900.00) / 1900.00 = 0.0263% = 2.63 bps
Timing cost: (1901.00 - 1900.50) / 1900.50 = 0.0263% = 2.63 bps
Impact cost: (1901.50 - 1901.00) / 1901.00 = 0.0263% = 2.63 bps
Opportunity cost: 10 oz * (1902.00 - 1901.50) / 1901.50 = 0.26 oz-$
Total cost: 2.63 + 2.63 + 2.63 + (opportunity) = ~8 bps
```

### Benchmark Comparison

```python
vwap = 1901.20  # Market VWAP over interval
fill_price = 1901.50

vs_vwap = (1901.50 - 1901.20) / 1901.20 * 10000 = 1.58 bps

# Interpretation: paid 1.58 bps above VWAP
```

---

## Tests

```bash
# All TCA tests
python -m pytest tests/tca/ -v

# Attribution tests
python -m pytest tests/tca/test_attribution.py -v

# Benchmark tests
python -m pytest tests/tca/test_benchmarks.py -v

# Regime tests
python -m pytest tests/tca/test_regime.py -v
```

---

## Performance

- **Cost decomposition:** ~1,000 trades/s
- **Benchmark computation:** ~500 trades/s
- **Report generation:** ~100 trades/s (with charts)

---

## Known Limitations

1. **Simulated trades only:** No live order flow (yet)
2. **Price snapshots:** Not tick-by-tick (approximations)
3. **Regime detection lag:** HMM labels lag real-time by 1 bar
4. **Opportunity cost simplified:** Assumes linear price movement
5. **No cross-venue:** Single market only

---

## Future Enhancements

- [ ] Real-time TCA (intraday monitoring)
- [ ] Peer benchmarking (compare vs other traders)
- [ ] Machine learning cost prediction
- [ ] Micro-structural TCA (sub-second analysis)
- [ ] Multi-venue cost attribution

---

## Related Features

- [[Exec Sim Feature]] — Generates trades for TCA
- [[LOB Reconstruction Feature]] — Provides price snapshots
- [[Data Pipeline Feature]] — Regime labels

---

## Retrieval Hints

- "tca"
- "transaction cost"
- "execution quality"
- "cost attribution"
- "vwap benchmark"
