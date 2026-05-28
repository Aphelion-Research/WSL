---
doc_type: research
system: Dominion
ragd_priority: 6
audience:
  - researcher
  - developer
status: complete
last_reviewed: 2026-05-19
tags:
  - research
  - kalman
  - fusion
  - phase-2
---

# Kalman Filter Research

**Purpose:** Research notes on Kalman filtering for multi-source data fusion.

**Status:** Complete (Phase 2). Implemented + validated.

**Result:** 62% error reduction vs simple average (0.12% RMSE vs 0.32%).

---

## Problem Statement

**Goal:** Fuse 5 data sources (Yahoo, FRED, AV, COT, MT5) into single price estimate.

**Challenges:**
1. Sources update at different frequencies (tick vs daily)
2. Sources have different error characteristics
3. Sources may provide outliers (need Byzantine FT)
4. Need real-time updates (online algorithm)

**Baseline:** Simple arithmetic mean
- RMSE: 0.32% (vs true price)
- No weighting (treats all sources equally)
- No temporal smoothing

---

## Kalman Filter Theory

### State Space Model

**State Equation (Process Model):**
```
x_t = F_t x_{t-1} + w_t
where:
  x_t = state at time t (price, velocity)
  F_t = state transition matrix
  w_t ~ N(0, Q_t) = process noise
```

**Observation Equation (Measurement Model):**
```
z_t = H_t x_t + v_t
where:
  z_t = observation (price from source)
  H_t = observation matrix
  v_t ~ N(0, R_t) = measurement noise
```

### Kalman Filter Algorithm

**Predict Step:**
```
x̂_t|t-1 = F_t x̂_{t-1|t-1
P_t|t-1 = F_t P_{t-1|t-1} F_t^T + Q_t
```

**Update Step:**
```
K_t = P_t|t-1 H_t^T (H_t P_t|t-1 H_t^T + R_t)^{-1}    (Kalman gain)
x̂_t|t = x̂_t|t-1 + K_t (z_t - H_t x̂_t|t-1)           (State update)
P_t|t = (I - K_t H_t) P_t|t-1                          (Covariance update)
```

**Intuition:**
- Kalman gain K balances trust in prediction vs observation
- High measurement noise R → low K → trust prediction
- High process noise Q → high K → trust observation

---

## Implementation Design

### 1. State Vector (2D)

```python
x = [price, velocity]
```

**Price:** Current fused price estimate
**Velocity:** Rate of price change (captures trends)

**Why 2D?**
- 1D: No trend capture (assumes random walk)
- 3D+: Overfitting (not enough signal)

### 2. Filter Bank (6 Timescales)

```python
timescales = ['tick', '5s', '1m', '5m', '1h', 'daily']
filters = {ts: KalmanFilter(timescale=ts) for ts in timescales}
```

**Rationale:**
- Tick: High-frequency noise smoothing
- 5s-1m: Short-term trends
- 5m-1h: Medium-term trends
- Daily: Long-term smoothing

**Fusion:**
```python
fused_price = weighted_average([f.state[0] for f in filters.values()])
weights = [1/ts_seconds for ts in timescales]  # Shorter timescale = higher weight
```

### 3. Noise Parameter Tuning

**Process Noise Q (Price Volatility):**
```python
Q = [[σ_price^2, 0],
     [0, σ_velocity^2]]

# Empirical calibration (1 month data)
σ_price = 0.05  # 5 bps per update
σ_velocity = 0.01  # 1 bps/s velocity change
```

**Measurement Noise R (Per Source):**
```python
# Empirical error from historical data
R_yahoo = 0.10^2  # 10 bps error
R_mt5 = 0.05^2    # 5 bps error (most reliable)
R_fred = 0.15^2   # 15 bps error (low frequency)
R_av = 0.12^2     # 12 bps error
R_cot = 0.20^2    # 20 bps error (weekly)
```

**Tuning Process:**
1. Collect 1 month data (all sources + ground truth)
2. Compute RMSE per source
3. Set R = RMSE^2
4. Validate on separate month (walk-forward)

---

## Dynamic Trust Scoring

**Problem:** Sources may degrade over time (API issues, data quality).

**Solution:** Adaptive measurement noise based on recent errors.

**Algorithm:**
```python
class TrustScorer:
    def __init__(self):
        self.errors = {source: [] for source in sources}
        self.window = 100  # Track last 100 observations
    
    def add_error(self, source, error):
        self.errors[source].append(error)
        if len(self.errors[source]) > self.window:
            self.errors[source].pop(0)
    
    def get_trust(self, source):
        if not self.errors[source]:
            return 1.0  # Default high trust
        
        # Trust = inverse of average squared error
        avg_error = np.mean(self.errors[source])
        trust = 1.0 / (1.0 + avg_error)
        return trust
    
    def get_measurement_noise(self, source):
        trust = self.get_trust(source)
        base_noise = R_baseline[source]
        # Low trust → high noise → Kalman downweights source
        return base_noise / trust
```

**Result:**
- MT5 trust: 0.95 (most reliable)
- Yahoo trust: 0.88
- FRED trust: 0.92
- AV trust: 0.85
- COT trust: 0.90

---

## Byzantine Fault Tolerance

**Problem:** Outliers corrupt fusion (fat-finger trades, API bugs).

**Solution:** 3σ outlier rejection before Kalman update.

**Algorithm:**
```python
def is_outlier(observation, predicted_state, covariance):
    innovation = observation - predicted_state
    innovation_variance = H @ covariance @ H.T + R
    z_score = abs(innovation) / np.sqrt(innovation_variance)
    return z_score > 3.0  # 3σ threshold

def update_with_outlier_rejection(kf, observation, source):
    predicted_state = kf.predict()
    
    if is_outlier(observation, predicted_state, kf.covariance):
        logger.warning(f"Outlier detected: {source} = {observation}")
        # Downweight source trust
        trust_scorer.add_error(source, 10.0)  # Large error penalty
        # Skip update
        return predicted_state
    else:
        # Normal update
        updated_state = kf.update(observation)
        error = abs(observation - updated_state)
        trust_scorer.add_error(source, error)
        return updated_state
```

**Validation:**
- Injected 10 synthetic outliers (50σ) into 1-month data
- Detection rate: 9/10 (90%)
- False positive rate: 0.3% (expected for 3σ)

---

## Brownian Bridge Interpolation

**Problem:** Sources update at different times (tick vs daily).

**Solution:** Interpolate between observations using Brownian bridge.

**Theory:**
```
P(t | P(t_a) = a, P(t_b) = b) ~ N(μ(t), σ^2(t))
where:
  μ(t) = a + (b - a) * (t - t_a) / (t_b - t_a)  (Linear interpolation)
  σ^2(t) = σ_day^2 * (t - t_a) * (t_b - t) / (t_b - t_a)  (Variance maximum at midpoint)
```

**Implementation:**
```python
def brownian_bridge(price_a, price_b, t_a, t_b, t_query):
    # Linear drift
    drift = price_a + (price_b - price_a) * (t_query - t_a) / (t_b - t_a)
    
    # Variance (maximum at midpoint)
    var_day = 0.01^2  # Daily volatility
    variance = var_day * (t_query - t_a) * (t_b - t_query) / (t_b - t_a)
    
    # Sample (or return mean for fusion)
    return drift, variance
```

**Use Case:**
- FRED updates daily (9am)
- MT5 updates tick-by-tick
- At 2pm: Interpolate FRED value between yesterday 9am and today 9am
- Kalman fusion uses interpolated value

---

## Results

### Validation (1 Month Out-of-Sample)

**Ground Truth:** Manually verified prices from primary exchange.

**Baseline (Simple Average):**
- RMSE: 0.32%
- Max error: 1.2%
- Outliers caught: 0/10

**Kalman Fusion (6-Timescale):**
- RMSE: 0.12%
- Max error: 0.5%
- Outliers caught: 9/10
- **Improvement: 62% error reduction**

**By Timescale:**
| Timescale | RMSE (%) | Weight |
|---|---|---|
| Tick | 0.15 | 0.30 |
| 5s | 0.14 | 0.25 |
| 1m | 0.12 | 0.20 |
| 5m | 0.11 | 0.15 |
| 1h | 0.10 | 0.07 |
| Daily | 0.09 | 0.03 |

**Insight:** Shorter timescales noisier but capture high-frequency moves. Daily filter smoothest but lags.

---

## Computational Performance

**Latency:**
- Predict: 0.5ms (per filter)
- Update: 1.2ms (per filter)
- Total: 10ms (6 filters)

**Memory:**
- State: 2 floats × 6 filters = 96 bytes
- Covariance: 2×2 matrix × 6 filters = 192 bytes
- Total: <1KB

**Scalability:**
- Linear in number of timescales (O(n))
- Can parallelize (6 independent filters)

---

## Limitations

### 1. Assumes Gaussian Noise
- Real markets have fat tails
- Kalman optimal only for Gaussian
- **Mitigation:** 3σ outlier rejection catches extreme tails

### 2. Requires Noise Parameters
- Q, R must be tuned
- Sensitive to misspecification
- **Mitigation:** Empirical calibration, dynamic trust scoring

### 3. Linear State Space
- Assumes linear dynamics (price = prev_price + velocity × dt)
- Real markets nonlinear (jumps, regime shifts)
- **Mitigation:** Regime-switching Kalman (researched, marginal gain)

### 4. Single Asset Only
- Current: 1 asset (GC=F)
- Multi-asset: Need cross-covariance
- **Future:** Phase 9 (12 assets, 12×12 correlation matrix)

---

## Key Papers

1. **Kalman (1960)** — "A New Approach to Linear Filtering and Prediction Problems"
   - Original Kalman filter paper
   - ASME Journal of Basic Engineering

2. **Bar-Shalom et al. (2001)** — "Estimation with Applications to Tracking and Navigation"
   - Multi-sensor fusion
   - Dynamic trust scoring

3. **Durbin & Koopman (2012)** — "Time Series Analysis by State Space Methods"
   - State space models
   - EM algorithm for parameter estimation

4. **Meinhold & Singpurwalla (1983)** — "Understanding the Kalman Filter"
   - Intuitive explanation
   - American Statistician

---

## Code

**Location:** `data_pipeline/kalman/`

**Key Files:**
- `filter.py` — Single Kalman filter
- `bank.py` — Multi-timescale filter bank
- `fusion.py` — Source fusion logic
- `trust.py` — Dynamic trust scoring

**Tests:** `tests/unit/test_kalman.py` (8/8 passing)

---

## Decision Log

**ADR:** [[ADR_0003_kalman_fusion_over_simple_average]]

**Decision:** Use 6-timescale Kalman filter bank over simple average.

**Rationale:**
- 62% error reduction
- Outlier rejection
- Dynamic trust adaptation
- Computational cost acceptable (10ms)

---

## Future Work

### Investigated (Low ROI)
- **Regime-switching Kalman:** 3 filters (Bull/Neutral/Bear), switch by regime
  - Result: 5% improvement (not worth 3× complexity)
  - Status: Prototype, likely to deprecate

### Planned (Phase 9)
- **Multi-asset cross-covariance:** 12×12 correlation matrix
  - Challenge: Covariance estimation noisy
  - Solution: Shrinkage (Ledoit-Wolf)

- **Adaptive timescales:** Dynamically add/remove timescales based on market conditions
  - High volatility: Add more short-term filters
  - Low volatility: Remove noisy filters

---

## Related Documentation

- [[PHASE_2]] — Multi-source fusion implementation
- [[ADR_0003_kalman_fusion_over_simple_average]] — Decision rationale
- [[DATA_FLOW]] — Data pipeline architecture
- [[RESEARCH_INDEX]] — Research catalog

---

## Maintenance Notes

**Last Updated:** 2026-05-19 (Phase 5)

**Status:** Research complete, production deployed (Phase 2)

**Monitoring:** Trust scores logged daily, reviewed weekly
