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
  - exec-sim
  - execution
  - simulation
---

# Execution Simulator Feature

**Status:** Operational (8/8 tests passing)

---

## Purpose

Simulate execution strategies (VWAP, TWAP, POV) with Almgren-Chriss market impact model. Order matching + partial fills + slippage tracking.

---

## Implementation Status

| Component | Status | Tests |
|---|---|---|
| Order matching engine | ✓ Complete | 3/3 |
| VWAP strategy | ✓ Complete | 2/2 |
| TWAP strategy | ✓ Complete | 1/1 |
| POV strategy | ✓ Complete | 1/1 |
| Market impact (Almgren-Chriss) | ✓ Complete | 1/1 |

**Overall:** 8/8 tests passing

---

## Key Components

### 1. Order Matching (`exec_sim/matching.py`)

**`walk_book(price, size, book, side)`:**
- Walk order book levels
- Fill against liquidity
- Compute VWAP fill price
- Return executed size + remaining

**`compute_slippage_bps(fill_price, mid_price, side)`:**
- Calculate slippage in basis points
- Positive = adverse, negative = favorable

### 2. Execution Strategies (`exec_sim/strategies.py`)

**VWAP (Volume-Weighted Average Price):**
```python
# Split order proportional to historical volume profile
for interval in trading_window:
    size_i = total_size * (interval_volume / total_volume)
    execute(size_i, interval)
```

**TWAP (Time-Weighted Average Price):**
```python
# Split order equally over time
size_per_interval = total_size / num_intervals
for interval in trading_window:
    execute(size_per_interval, interval)
```

**POV (Percentage of Volume):**
```python
# Execute fixed % of market volume
for interval in trading_window:
    target_size = market_volume * pov_rate  # e.g., 10%
    execute(target_size, interval)
```

### 3. Market Impact Model (`exec_sim/impact.py`)

**Almgren-Chriss temporary + permanent impact:**

```python
def almgren_chriss_impact(size, volume, volatility, urgency):
    """
    Temporary impact: price moves during execution, reverts after
    Permanent impact: price moves permanently
    """
    
    # Model parameters
    gamma = 2.5e-7      # Temporary impact coefficient
    eta = 2.5e-6        # Permanent impact coefficient
    
    # Temporary impact (per-interval)
    temp_impact = gamma * (size ** 0.6) / (volume ** 0.6)
    
    # Permanent impact (cumulative)
    perm_impact = eta * size / volume
    
    # Total impact
    impact_bps = (temp_impact + perm_impact) * volatility * urgency
    
    return impact_bps
```

---

## CLI Commands

```bash
# Run VWAP simulation
python -m exec_sim.cli run --strategy vwap --size 100 --duration 60

# Run TWAP simulation
python -m exec_sim.cli run --strategy twap --size 100 --intervals 10

# Run POV simulation
python -m exec_sim.cli run --strategy pov --size 100 --pov-rate 0.1

# Performance report
python -m exec_sim.cli report --sim-id [uuid]

# Compare strategies
python -m exec_sim.cli compare --sims [uuid1,uuid2,uuid3]
```

---

## Configuration

**`exec_sim/config.py`:**
```python
EXEC_SIM_CONFIG = {
    "strategies": ["vwap", "twap", "pov"],
    "default_duration": 60,        # seconds
    "default_intervals": 10,
    "default_pov_rate": 0.10,      # 10% of volume
    "almgren_chriss": {
        "gamma": 2.5e-7,           # Temporary impact
        "eta": 2.5e-6,             # Permanent impact
        "risk_aversion": 5e-6
    },
    "slippage_model": "almgren_chriss"
}
```

---

## DuckDB Schema

### Table: `sim_strategies`
```sql
CREATE TABLE sim_strategies (
    sim_id UUID PRIMARY KEY,
    strategy VARCHAR,        -- 'vwap' | 'twap' | 'pov'
    total_size DOUBLE,
    duration_seconds INT,
    intervals INT,
    pov_rate DOUBLE,
    start_time TIMESTAMP,
    end_time TIMESTAMP
);
```

### Table: `sim_orders`
```sql
CREATE TABLE sim_orders (
    order_id UUID PRIMARY KEY,
    sim_id UUID REFERENCES sim_strategies(sim_id),
    interval INT,
    timestamp TIMESTAMP,
    side VARCHAR,            -- 'buy' | 'sell'
    size DOUBLE,
    limit_price DOUBLE,
    fill_price DOUBLE,
    executed_size DOUBLE,
    slippage_bps DOUBLE,
    temp_impact_bps DOUBLE,
    perm_impact_bps DOUBLE
);
```

### Table: `sim_performance`
```sql
CREATE TABLE sim_performance (
    sim_id UUID PRIMARY KEY,
    strategy VARCHAR,
    total_executed DOUBLE,
    avg_fill_price DOUBLE,
    vwap_benchmark DOUBLE,
    twap_benchmark DOUBLE,
    slippage_bps DOUBLE,
    impact_cost_bps DOUBLE,
    total_cost_bps DOUBLE,
    completion_rate DOUBLE   -- executed / requested
);
```

---

## Integration Points

### Input
- **LOB Engine:** Order book state for matching
- **Toxicity Monitor:** Toxicity score adjusts urgency parameter
- **Data Pipeline:** Volume profile for VWAP

### Output
- **TCA Dashboard:** Simulated fills for cost attribution
- **Data Pipeline:** Execution quality features

---

## Algorithm Details

### VWAP Strategy

```python
def vwap_strategy(total_size, duration, volume_profile):
    """Execute proportional to volume profile."""
    
    # Historical volume profile (e.g., U-shaped intraday)
    intervals = partition_time(duration, volume_profile)
    
    orders = []
    for i, interval in enumerate(intervals):
        # Size proportional to expected volume
        target_size = total_size * (interval.volume / sum(v.volume for v in intervals))
        
        # Submit order
        order = execute_order(
            size=target_size,
            time=interval.start,
            book=get_book(interval.start)
        )
        orders.append(order)
    
    return orders
```

### POV Strategy

```python
def pov_strategy(total_size, duration, pov_rate):
    """Execute as percentage of market volume."""
    
    executed = 0
    orders = []
    
    while executed < total_size:
        # Observe market volume this interval
        market_vol = get_interval_volume()
        
        # Target = pov_rate * market_vol, capped by remaining
        target_size = min(pov_rate * market_vol, total_size - executed)
        
        order = execute_order(size=target_size)
        orders.append(order)
        executed += order.executed_size
    
    return orders
```

### Market Impact Calculation

```python
def compute_impact(order, market_state):
    """Almgren-Chriss impact."""
    
    # Parameters
    size = order.size
    daily_volume = market_state.daily_volume
    volatility = market_state.volatility
    urgency = order.urgency  # 0 (patient) to 1 (urgent)
    
    # Temporary impact (reverts after execution)
    temp_impact = GAMMA * (size / daily_volume) ** 0.6 * volatility
    
    # Permanent impact (persistent price shift)
    perm_impact = ETA * (size / daily_volume) * volatility
    
    # Scale by urgency (urgent orders pay more impact)
    temp_impact *= urgency
    perm_impact *= urgency
    
    return temp_impact, perm_impact
```

---

## Tests

```bash
# All exec_sim tests
python -m pytest tests/exec_sim/ -v

# Matching engine tests
python -m pytest tests/exec_sim/test_matching.py -v

# Strategy tests
python -m pytest tests/exec_sim/test_strategies.py -v

# Impact model tests
python -m pytest tests/exec_sim/test_impact.py -v
```

---

## Performance

- **Order matching:** ~10,000 orders/s
- **Strategy simulation:** ~1,000 intervals/s
- **Impact computation:** ~5,000 calcs/s
- **Memory:** ~20MB per 10K orders

---

## Known Limitations

1. **Simplified book:** 10-level snapshot, no sub-tick dynamics
2. **No order cancellations:** All orders fill or remain (no cancel/replace)
3. **Deterministic matching:** No randomness in fill priority
4. **Static impact model:** Almgren-Chriss parameters fixed (should calibrate)
5. **No information leakage:** Real orders reveal intent, simulated don't

---

## Future Enhancements

- [ ] Adaptive POV (adjust rate based on market conditions)
- [ ] Implementation shortfall tracking
- [ ] Multi-venue simulation (route across exchanges)
- [ ] Liquidity seeking algorithms
- [ ] Cancel/replace logic
- [ ] Calibrate Almgren-Chriss to XAU/USD empirical data

---

## Related Features

- [[LOB Reconstruction Feature]] — Provides order book
- [[TCA Feature]] — Analyzes execution quality
- [[Toxicity Feature]] — Toxicity score adjusts urgency

---

## Retrieval Hints

- "execution simulator"
- "vwap twap pov"
- "market impact"
- "almgren chriss"
- "order matching"
