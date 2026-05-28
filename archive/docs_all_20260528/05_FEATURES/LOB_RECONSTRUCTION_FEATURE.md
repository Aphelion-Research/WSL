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
  - lob
  - microstructure
  - order-book
---

# LOB Reconstruction Feature

**Status:** Operational (8/8 tests passing)

---

## Purpose

Reconstruct 10-level order book from XAU/USD tick data. Compute microstructure metrics: OFI (Order Flow Imbalance), VPIN (Volume-synchronized PIN), Roll/Corwin-Schultz spreads, depth-weighted mid.

---

## Implementation Status

| Component | Status | Tests | Coverage |
|---|---|---|---|
| Tick ingestion | ✓ Complete | 2/2 | High |
| Order book state machine | ✓ Complete | 3/3 | High |
| OFI computation | ✓ Complete | 1/1 | High |
| VPIN computation | ✓ Complete | 1/1 | High |
| Spread estimation | ✓ Complete | 1/1 | High |

**Overall:** 8/8 tests passing

---

## Key Components

### 1. Tick Ingestion (`lob/ingestion.py`)

**Functions:**
- `load_gold_ticks(db_path, limit)` — Load from DuckDB gold_master table
- `generate_synthetic_quotes(df, spread_bps)` — Generate bid/ask from mid prices
- `compute_roll_spread(prices, window)` — Roll spread estimation
- `prepare_lob_data(db_path, limit)` — Complete ingestion pipeline

**Data flow:**
```
DuckDB (gold_master) → Ticks DataFrame → Synthetic Quotes → LOB Data
```

### 2. Order Book State Machine (`lob/book.py`)

**10-level book structure:**
```python
{
  "bids": [(price, size), ...],  # 10 levels
  "asks": [(price, size), ...]   # 10 levels
}
```

**State updates:**
- Insert: Add new level
- Modify: Update size at level
- Delete: Remove level
- Sort: Maintain price-time priority

### 3. Metrics Engine (`lob/metrics.py`)

**OFI (Order Flow Imbalance):**
```
OFI = Δbid_size - Δask_size
```

Timeframes: 1s, 5s, 1m

**VPIN (Volume-synchronized PIN):**
```
VPIN = |buy_volume - sell_volume| / total_volume
```

Bucketing: 50-bucket rolling window

**Roll Spread:**
```
Roll = 2 * sqrt(-Cov(Δp[t], Δp[t-1]))
```

**Corwin-Schultz Spread:**
```
CS = (2 * (e^α - 1)) / (1 + e^α)
where α = function of high-low ratio
```

**Depth-Weighted Mid:**
```
DWM = (bid_price * ask_size + ask_price * bid_size) / (bid_size + ask_size)
```

---

## CLI Commands

```bash
# Compute LOB from ticks
python -m lob.cli compute --db data/dominion.duckdb --limit 10000

# Compute metrics
python -m lob.cli metrics --db data/dominion.duckdb

# Compute VPIN
python -m lob.cli vpin --db data/dominion.duckdb --buckets 50

# Status
python -m lob.cli status
```

---

## Configuration

**`lob/config.py`:**
```python
LOB_CONFIG = {
    "book_depth": 10,           # Levels per side
    "tick_size": 0.01,          # Minimum price increment
    "spread_bps_default": 2.0,  # Synthetic quote spread
    "ofi_windows": [1, 5, 60],  # Seconds
    "vpin_buckets": 50,         # Rolling buckets
    "roll_window": 20           # Ticks for Roll spread
}
```

---

## DuckDB Schema

### Table: `lob_snapshots`
```sql
CREATE TABLE lob_snapshots (
    timestamp TIMESTAMP,
    bid_price_1 DOUBLE, bid_size_1 DOUBLE,
    bid_price_2 DOUBLE, bid_size_2 DOUBLE,
    ... (10 levels)
    ask_price_1 DOUBLE, ask_size_1 DOUBLE,
    ask_price_2 DOUBLE, ask_size_2 DOUBLE,
    ... (10 levels)
    PRIMARY KEY (timestamp)
);
```

### Table: `lob_events`
```sql
CREATE TABLE lob_events (
    timestamp TIMESTAMP,
    event_type VARCHAR,  -- 'insert' | 'modify' | 'delete'
    side VARCHAR,        -- 'bid' | 'ask'
    price DOUBLE,
    size DOUBLE,
    PRIMARY KEY (timestamp, event_type, side, price)
);
```

### Table: `lob_metrics`
```sql
CREATE TABLE lob_metrics (
    timestamp TIMESTAMP,
    ofi_1s DOUBLE,
    ofi_5s DOUBLE,
    ofi_1m DOUBLE,
    vpin DOUBLE,
    roll_spread DOUBLE,
    cs_spread DOUBLE,
    depth_weighted_mid DOUBLE,
    PRIMARY KEY (timestamp)
);
```

---

## Integration Points

### Input
- **Data Pipeline:** Gold master prices from Kalman fusion
- **domdata:** MT5 tick data (if real-time)

### Output
- **Toxicity Monitor:** OFI + VPIN metrics
- **Exec Simulator:** Order book state for matching
- **TCA Dashboard:** Spread metrics for cost attribution
- **Data Pipeline:** LOB features ingested for alpha generation

---

## Algorithm Details

### Synthetic Quote Generation

Since XAU/USD spot doesn't have full order book (MT5 provides ticks only), generate synthetic bid/ask:

```python
mid_price = fused_price  # From data pipeline
spread_bps = 2.0         # 2 basis points default

half_spread = mid_price * (spread_bps / 10000) / 2
bid = mid_price - half_spread
ask = mid_price + half_spread

# Size proportional to tick volume (or constant)
bid_size = 10.0
ask_size = 10.0
```

Limitations:
- No true depth (synthetic)
- Spread constant (real spreads vary)
- No order flow dynamics

Future: Integrate real order book if available.

### OFI Computation

```python
def compute_ofi(current_book, previous_book):
    """Order Flow Imbalance = Δbid_size - Δask_size"""
    
    # Top-of-book changes
    curr_bid_size = sum(size for price, size in current_book['bids'][:3])
    prev_bid_size = sum(size for price, size in previous_book['bids'][:3])
    
    curr_ask_size = sum(size for price, size in current_book['asks'][:3])
    prev_ask_size = sum(size for price, size in previous_book['asks'][:3])
    
    ofi = (curr_bid_size - prev_bid_size) - (curr_ask_size - prev_ask_size)
    return ofi
```

Aggregate over windows (1s, 5s, 1m) for different time horizons.

### VPIN Computation

```python
def compute_vpin(trades, buckets=50):
    """Volume-synchronized Probability of Informed Trading"""
    
    # Classify trades as buy/sell (using Lee-Ready algorithm)
    for trade in trades:
        if trade.price > mid:
            trade.side = 'buy'
        elif trade.price < mid:
            trade.side = 'sell'
        else:
            # Use previous price (tick test)
            trade.side = 'buy' if trade.price > prev_price else 'sell'
    
    # Bucket by volume
    bucket_volume = total_volume / buckets
    
    # Compute |buy_vol - sell_vol| per bucket
    vpin_values = []
    for bucket in volume_buckets:
        buy_vol = sum(trade.volume for trade in bucket if trade.side == 'buy')
        sell_vol = sum(trade.volume for trade in bucket if trade.side == 'sell')
        vpin_values.append(abs(buy_vol - sell_vol) / bucket_volume)
    
    # VPIN = average over buckets
    return mean(vpin_values)
```

---

## Tests

```bash
# Run all LOB tests
python -m pytest tests/lob/ -v

# Specific tests
python -m pytest tests/lob/test_ingestion.py -v
python -m pytest tests/lob/test_book.py -v
python -m pytest tests/lob/test_metrics.py -v
```

**Test coverage:**
- Tick ingestion (load, generate quotes, spreads)
- Order book updates (insert, modify, delete)
- OFI computation (1s, 5s, 1m)
- VPIN computation (50 buckets)
- Roll/CS spreads

---

## Performance

- **Tick ingestion:** ~1000 ticks/s
- **Book updates:** ~5000 updates/s
- **Metrics computation:** ~500 snapshots/s
- **Memory:** ~50MB for 10K snapshots

---

## Known Limitations

1. **Synthetic quotes:** No real order book depth (MT5 ticks only)
2. **Spread constant:** Real spreads vary with volatility/liquidity
3. **No tick-by-tick order flow:** Can't classify aggressive vs passive
4. **VPIN requires trade classification:** Lee-Ready heuristic imperfect
5. **No level updates between ticks:** Assumes book static between observations

---

## Future Enhancements

- [ ] Real order book integration (if data source available)
- [ ] Dynamic spread estimation (Bayesian updating)
- [ ] Trade classification improvements (bulk volume classification)
- [ ] High-frequency order flow metrics (sub-second)
- [ ] Book imbalance ratios (bid depth / ask depth)

---

## Related Features

- [[Data Pipeline Feature]] — Provides fused prices
- [[Toxicity Feature]] — Consumes OFI + VPIN
- [[Exec Sim Feature]] — Uses book state for matching
- [[TCA Feature]] — Uses spread metrics

---

## Retrieval Hints

- "lob reconstruction"
- "order book"
- "ofi vpin"
- "microstructure metrics"
- "bid ask spread"
