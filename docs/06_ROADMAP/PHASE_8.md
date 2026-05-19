---
doc_type: roadmap
system: Dominion
ragd_priority: 5
audience:
  - maintainer
  - owner
status: planned
last_reviewed: 2026-05-19
tags:
  - roadmap
  - phase-8
  - risk-management
  - safety
---

# Phase 8: Risk Management System (Planned)

**Timeline:** Q4 2026 - Q1 2027 (3 months)  
**Status:** 📋 Planned

---

## Goals

1. Pre-trade risk checks (position limits, concentration)
2. Real-time risk monitoring (VaR, Greeks, exposure)
3. Dynamic position sizing (volatility-scaled Kelly)
4. Drawdown-based de-risking
5. Circuit breakers + kill switches

---

## Deliverables

### Pre-Trade Checks
- [ ] Position limit enforcement (per symbol, total)
- [ ] Concentration checks (sector, regime)
- [ ] Liquidity checks (ADV limits)
- [ ] Margin requirement validation
- [ ] Prohibited instruments blacklist

### Real-Time Monitoring
- [ ] VaR computation (parametric, historical, Monte Carlo)
- [ ] Greeks calculation (delta, gamma, vega, theta)
- [ ] Exposure tracking (gross, net, sector)
- [ ] Correlation monitoring (portfolio-level)
- [ ] Stress testing (regime shift scenarios)

### Dynamic Sizing
- [ ] Volatility-scaled Kelly
- [ ] Regime-conditional sizing
- [ ] Drawdown-based scaling
- [ ] Confidence-weighted sizing
- [ ] Adaptive rebalancing

### Circuit Breakers
- [ ] Daily loss limit (-5%)
- [ ] Drawdown limit (-15%)
- [ ] VaR limit (99% < $50K)
- [ ] Position size limit (20% per symbol)
- [ ] Emergency kill switch

### Reporting
- [ ] Daily risk report
- [ ] Weekly risk review
- [ ] Monthly stress test
- [ ] Incident log
- [ ] Risk dashboard

---

## Timeline

| Milestone | Date | Status |
|---|---|---|
| Pre-trade checks operational | 2026-12-15 | Pending |
| VaR computation live | 2026-12-31 | Pending |
| Dynamic sizing implemented | 2027-01-15 | Pending |
| Circuit breakers tested | 2027-01-31 | Pending |
| Risk dashboard live | 2027-02-15 | Pending |
| Phase 8 complete | 2027-02-28 | Pending |

---

## Dependencies

**Requires Phase 7:**
- Paper trading live (for risk metrics)
- Position tracking
- P&L attribution

**Requires Phase 6:**
- Portfolio construction (for VaR)
- Volatility estimation
- Covariance matrix

**Requires Phase 4:**
- Regime detection (for regime-conditional sizing)
- Intelligence reports (for stress scenarios)

**External:**
- Risk-free rate data (FRED)
- Volatility surface data (if options)
- Sector classification data

---

## Success Criteria

- [ ] Zero limit breaches (position, loss, VaR)
- [ ] VaR accuracy: actual losses < VaR 95% of days
- [ ] Dynamic sizing reduces drawdown by >20% vs fixed
- [ ] Circuit breakers tested (simulated scenarios)
- [ ] Risk dashboard operational 24/7

---

## Pre-Trade Risk Checks

**Position Limits:**
```python
def check_position_limits(symbol, proposed_size):
    # Per-symbol limit
    if abs(proposed_size) > 0.20 * portfolio_value:
        return False, "Exceeds 20% position limit"
    
    # Total gross exposure
    gross_exposure = sum(abs(pos) for pos in positions.values())
    if gross_exposure + abs(proposed_size) > 2.0 * portfolio_value:
        return False, "Exceeds 200% gross exposure"
    
    # Sector concentration
    sector = get_sector(symbol)
    sector_exposure = sum(positions[s] for s in positions if get_sector(s) == sector)
    if abs(sector_exposure + proposed_size) > 0.50 * portfolio_value:
        return False, "Exceeds 50% sector concentration"
    
    return True, "OK"
```

**Liquidity Checks:**
```python
def check_liquidity(symbol, proposed_size):
    adv = get_avg_daily_volume(symbol)  # Average daily volume
    max_participation = 0.05  # 5% of ADV
    
    if abs(proposed_size) > max_participation * adv:
        return False, f"Exceeds {max_participation*100}% ADV"
    
    return True, "OK"
```

**Blacklist:**
- Penny stocks (<$5)
- Low liquidity (ADV <100K shares)
- Prohibited sectors (per user config)
- Halted symbols

---

## Real-Time Risk Monitoring

**VaR (Value at Risk):**

**Parametric VaR (99%, 1-day):**
```
VaR = Z_α × σ_p × √Δt
where:
  Z_α = 2.33 (99th percentile)
  σ_p = portfolio volatility
  Δt = 1 day
```

**Historical VaR:**
- 250-day rolling window
- Compute daily returns
- 99th percentile worst loss

**Monte Carlo VaR:**
- 10,000 simulations
- Multivariate normal (mean, covariance)
- 99th percentile worst outcome

**Greeks (if options used):**
- Delta: price sensitivity
- Gamma: delta sensitivity
- Vega: volatility sensitivity
- Theta: time decay

**Exposure Tracking:**
```python
gross_exposure = sum(abs(position) for position in positions)
net_exposure = sum(position for position in positions)
long_exposure = sum(position for position in positions if position > 0)
short_exposure = sum(position for position in positions if position < 0)
```

**Correlation Monitoring:**
- Track portfolio correlation to SPY, GLD, TLT
- Alert if correlation >0.7 (lack of diversification)
- Regime-conditional correlation

**Stress Testing:**
- Scenario 1: Market crash (-20%)
- Scenario 2: Vol spike (+50%)
- Scenario 3: Regime shift (Bull → Bear)
- Scenario 4: Flash crash (-5% intraday)
- Scenario 5: Data feed loss (flat pricing)

---

## Dynamic Position Sizing

**Volatility-Scaled Kelly:**
```python
def size_position(signal, volatility, confidence, regime):
    # Base Kelly fraction
    kelly_fraction = signal * confidence
    
    # Scale by volatility (inverse)
    vol_scale = TARGET_VOL / volatility
    
    # Regime adjustment
    regime_scale = {
        'Bull': 1.2,
        'Neutral': 1.0,
        'Bear': 0.6
    }[regime]
    
    # Drawdown adjustment
    drawdown_scale = max(0.5, 1 - current_drawdown / MAX_DRAWDOWN)
    
    # Combined
    final_size = kelly_fraction * vol_scale * regime_scale * drawdown_scale
    
    # Clip to limits
    return np.clip(final_size, -0.20, 0.20)
```

**Regime-Conditional Sizing:**
- Bull: +20% size (trends strong)
- Neutral: Baseline (no adjustment)
- Bear: -40% size (high risk)

**Drawdown-Based Scaling:**
```python
if drawdown < 5%:
    scale = 1.0
elif drawdown < 10%:
    scale = 0.75
elif drawdown < 15%:
    scale = 0.50
else:
    scale = 0.0  # Stop trading
```

**Confidence-Weighted Sizing:**
- Confidence from ensemble agreement
- High confidence (>0.8): Full size
- Medium confidence (0.5-0.8): 50% size
- Low confidence (<0.5): 25% size

---

## Circuit Breakers

**Daily Loss Limit:**
```python
if daily_pnl < -0.05 * portfolio_value:
    HALT_TRADING()
    SEND_ALERT("Daily loss limit breached")
    LOG_INCIDENT("circuit_breaker_daily_loss")
```

**Drawdown Limit:**
```python
if current_drawdown > 0.15:
    HALT_TRADING()
    SEND_ALERT("15% drawdown limit breached")
    LOG_INCIDENT("circuit_breaker_drawdown")
```

**VaR Limit:**
```python
if var_99 > 50000:
    REDUCE_POSITIONS(target_var=40000)
    SEND_ALERT(f"VaR limit breached: ${var_99:.0f}")
```

**Position Size Limit:**
```python
for symbol, position in positions.items():
    if abs(position) > 0.20 * portfolio_value:
        REDUCE_POSITION(symbol, target=0.18 * portfolio_value)
        SEND_ALERT(f"Position limit breached: {symbol}")
```

**Emergency Kill Switch:**
- Manual trigger (CLI command, dashboard button)
- Closes all positions immediately
- Market orders (accept slippage)
- Logs incident + sends critical alert
- Requires manual restart (not auto-resume)

---

## Risk Dashboard

**Row 1: Current Risk**
- VaR 99% (1-day)
- Current drawdown
- Gross/net exposure
- Sharpe ratio (rolling 30-day)

**Row 2: Position Risk**
- Top 5 positions (size, P&L, risk contribution)
- Concentration by sector
- Long/short split
- Liquidity coverage (days to unwind)

**Row 3: Historical**
- VaR accuracy (backtest vs actual)
- Drawdown history (1-year)
- Limit breach log (last 30 days)
- Stress test results (weekly)

**Row 4: Alerts**
- Active circuit breakers
- Recent violations
- Near-miss warnings (>80% of limit)
- System health

---

## Key Decisions

- VaR confidence: 99% (conservative, match industry)
- Position limit: 20% per symbol (balance concentration vs diversification)
- Daily loss limit: -5% (prevent catastrophic loss)
- Max drawdown: 15% (circuit breaker threshold)
- Regime-conditional sizing (adapt to market state)

---

## Risks and Mitigations

1. **VaR model risk** (Medium)
   - Risk: VaR underestimates tail risk
   - Mitigation: Use 3 methods (parametric, historical, MC), stress tests

2. **False circuit breakers** (Medium)
   - Risk: Stop trading on transient volatility
   - Mitigation: 5-minute confirmation window, multiple metrics

3. **Covariance estimation error** (Medium)
   - Risk: Correlation matrix noisy → bad VaR
   - Mitigation: Shrinkage estimators, rolling windows

4. **Regime misclassification** (Low)
   - Risk: HMM assigns wrong regime → bad sizing
   - Mitigation: Confidence scoring, smoothing

5. **Operational error** (Low)
   - Risk: Kill switch accidentally triggered
   - Mitigation: Two-factor confirmation, audit log

---

## Metrics (Target)

| Metric | Target |
|---|---|
| VaR 99% (1-day) | <$50K |
| Max drawdown | <15% |
| Position concentration | <20% per symbol |
| Sector concentration | <50% per sector |
| Gross exposure | <200% |
| Limit breaches | 0 |
| VaR accuracy | >95% days |

---

## Expected Challenges

**VaR calibration:**
- Parametric assumes normality (fat tails in reality)
- Historical VaR backward-looking
- Solution: Ensemble of methods + stress tests

**Real-time computation:**
- Covariance matrix inversion expensive
- Solution: Caching, incremental updates

**Backtesting risk system:**
- Hard to test circuit breakers without live trades
- Solution: Simulated scenarios, replay historical crashes

**False positives:**
- Over-aggressive limits stop trading unnecessarily
- Solution: Tune thresholds empirically

---

## Research Questions

1. Which VaR method most accurate (parametric, historical, MC)?
2. Optimal drawdown threshold (15% vs 10% vs 20%)?
3. Does regime-conditional sizing improve risk-adjusted returns?
4. How often do circuit breakers trigger (false positive rate)?
5. VaR vs CVaR (conditional VaR): which better?

---

## Lessons from Prior Work

**From Phase 7 (Paper Trading):**
- Real-time latency critical (<1s)
- Model degradation real concern
- Operational procedures necessary

**From Phase 6 (Alpha Research):**
- Volatility scaling improves Sharpe
- Ensemble models more robust
- Walk-forward validation critical

**Apply here:**
- Volatility-scaled position sizing
- Ensemble for correlation estimates
- Real-time monitoring dashboard

---

## Next Phase

→ [[PHASE_9]] — Multi-Asset Expansion (Planned)
