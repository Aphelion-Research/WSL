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
  - phase-7
  - paper-trading
  - live-testing
---

# Phase 7: Live Paper Trading (Planned)

**Timeline:** Q3 2026 - Q4 2026 (3 months)  
**Status:** 📋 Planned

---

## Goals

1. Real-time alpha signal generation
2. Paper trading infrastructure
3. Live performance monitoring
4. Regime adaptation validation
5. Operational readiness assessment

---

## Deliverables

### Paper Trading Engine
- [ ] Real-time tick processing
- [ ] Live alpha signal generation
- [ ] Simulated order routing
- [ ] Position tracking
- [ ] P&L attribution

### Monitoring Infrastructure
- [ ] Real-time dashboard (Streamlit/Dash)
- [ ] Performance metrics (Sharpe, drawdown, turnover)
- [ ] Regime state display
- [ ] Feature IC monitoring
- [ ] Alert system (email/Slack)

### Data Pipeline Integration
- [ ] Live MT5 feed → feature generation
- [ ] Kalman fusion real-time
- [ ] Toxicity monitor live
- [ ] Intelligence report generation (daily)
- [ ] RAGD ingestion (real-time)

### Operational Procedures
- [ ] Daily health checks
- [ ] System restart procedures
- [ ] Error handling protocols
- [ ] Performance review process
- [ ] Incident response playbook

### Validation
- [ ] Compare paper vs backtest metrics
- [ ] Regime detection accuracy
- [ ] Feature decay monitoring
- [ ] Slippage model validation
- [ ] 30-day live performance report

---

## Timeline

| Milestone | Date | Status |
|---|---|---|
| Paper engine operational | 2026-09-15 | Pending |
| Dashboard live | 2026-09-30 | Pending |
| 30 days paper trading | 2026-10-31 | Pending |
| Performance validated | 2026-11-15 | Pending |
| Operational procedures documented | 2026-11-30 | Pending |
| Phase 7 complete | 2026-11-30 | Pending |

---

## Dependencies

**Requires Phase 6:**
- Trained alpha models
- Backtesting framework (for comparison)
- Portfolio construction rules

**Requires Phase 2:**
- Real-time data pipeline
- Kalman fusion
- MT5/domdata integration

**Requires Phase 4:**
- Regime detection (live)
- Intelligence reports (daily)

**External:**
- MT5 account (demo or paper)
- Monitoring infrastructure (server/cloud)
- Alert system (email/Slack integration)

---

## Success Criteria

- [ ] Paper trading runs 30+ days without manual intervention
- [ ] Sharpe ratio within 20% of backtest
- [ ] Zero crashes/data loss
- [ ] <1 second latency (tick → signal)
- [ ] Regime detection matches offline
- [ ] All alerts functional

---

## Paper Trading Architecture

**Real-time flow:**
```
MT5 Tick → domdata → Pipeline → Features → Alpha Model → Signal
                                                           ↓
                                                     Position Sizer
                                                           ↓
                                                     Paper Executor
                                                           ↓
                                                     P&L Tracker
                                                           ↓
                                                     Dashboard/DB
```

**Components:**

**1. Tick Processor**
- Subscribe to MT5 tick feed (domdata)
- Parse bid/ask/volume
- Forward to feature pipeline

**2. Feature Pipeline**
- Compute 50 selected features
- Kalman fusion (6 timescales)
- Toxicity monitor
- Feature caching (60-second TTL)

**3. Alpha Engine**
- Load trained models
- Generate signal (-1 to +1)
- Confidence score
- Log predictions

**4. Position Sizer**
- Kelly/half-Kelly calculation
- Volatility scaling
- Position limits enforcement
- Regime-conditional sizing

**5. Paper Executor**
- Simulated order matching
- Almgren-Chriss slippage
- Fill reporting
- Order book simulation

**6. P&L Tracker**
- Mark-to-market
- Attribution (decision/timing/impact/opportunity)
- Cumulative P&L
- Trade-level logging

**7. Dashboard**
- Equity curve (real-time)
- Sharpe/drawdown/turnover
- Regime state
- Top features IC
- Recent trades

---

## Monitoring Dashboard

**Layout (Streamlit):**

**Row 1: Summary**
- Total P&L (today, week, month)
- Sharpe ratio (rolling 30-day)
- Current position (size, entry, P&L)
- Regime state (Bull/Neutral/Bear)

**Row 2: Performance**
- Equity curve (1-month)
- Drawdown chart
- Win rate (rolling 100 trades)
- Turnover (daily avg)

**Row 3: Features**
- Top 10 feature IC (rolling 24h)
- Feature decay alerts
- Correlation heatmap
- Signal strength histogram

**Row 4: System Health**
- Data pipeline status
- Latency (tick → signal)
- Error rate (last 1h)
- Uptime

**Row 5: Recent Activity**
- Last 10 trades
- Open positions
- Pending orders
- Recent alerts

---

## Alert System

**Critical alerts (immediate):**
- System crash/restart
- Data feed loss >5 min
- Feature computation error
- Model prediction NaN/Inf
- Position limit breach

**Warning alerts (daily digest):**
- Sharpe ratio <0.5 (rolling 7-day)
- Drawdown >10%
- Feature IC decay >50%
- Regime transition
- Turnover >150%/day

**Info alerts (weekly):**
- Performance summary
- Top trades (P&L)
- Feature IC rankings
- Model accuracy

**Delivery:**
- Critical: Email + Slack (real-time)
- Warning: Email (daily 9am)
- Info: Email (Monday 9am)

---

## Key Decisions

- Paper trading duration: 30 days minimum (validate seasonality)
- Dashboard refresh: 1 second (balance latency vs load)
- Alert thresholds: Conservative (avoid false positives)
- Model retraining: Weekly (adapt to live data)
- Latency target: <1 second (tick → signal)

---

## Risks and Mitigations

1. **Lookahead bias** (High risk)
   - Risk: Live features use future data accidentally
   - Mitigation: Audit feature generation, timestamp checks

2. **Data feed loss** (Medium risk)
   - Risk: MT5 connection drops
   - Mitigation: Reconnect logic, backup feed (Yahoo)

3. **Model staleness** (Medium risk)
   - Risk: Models trained on old data underperform
   - Mitigation: Weekly retraining, IC monitoring

4. **Regime shift** (Medium risk)
   - Risk: Market regime changes, models fail
   - Mitigation: Regime-conditional models, drawdown limits

5. **Infrastructure failure** (Low risk)
   - Risk: Server crash, database corruption
   - Mitigation: Daily backups, health checks, auto-restart

---

## Validation Protocol

**Week 1: Smoke test**
- Verify all components operational
- Check latency <1 second
- Validate feature computation
- Test alert system

**Week 2-3: Performance monitoring**
- Track Sharpe ratio daily
- Compare to backtest
- Monitor regime transitions
- Check feature IC stability

**Week 4: Deep analysis**
- Backtest vs live comparison
- Slippage model accuracy
- Regime detection accuracy
- Feature decay analysis

**Final report:**
- 30-day performance summary
- Backtest vs live delta
- Operational incidents
- Recommendations for Phase 8

---

## Metrics (Target)

| Metric | Backtest | Live Target | Tolerance |
|---|---|---|---|
| Sharpe ratio | 1.2 | 1.0 | ±20% |
| Max drawdown | 15% | 18% | +3% |
| Win rate | 52% | 50% | ±2% |
| Turnover | 80%/day | 90%/day | +10% |
| Latency | N/A | <1s | Hard limit |
| Uptime | N/A | >99% | Hard limit |

---

## Operational Procedures

**Daily (automated):**
- 8:00am: Generate intelligence report
- 8:30am: Rebuild RAGD index
- 9:00am: Send daily performance email
- 5:00pm: Snapshot positions/P&L
- 6:00pm: Database backup

**Daily (manual):**
- 9:15am: Review overnight performance
- 9:30am: Check dashboard for anomalies
- 5:15pm: Review day's trades

**Weekly (manual):**
- Monday 9am: Review weekly performance
- Retrain models on latest data
- Check feature IC rankings
- Update PHASE_7_LIVE_LOG.md

**Incident response:**
1. Alert received → check dashboard
2. Identify root cause (data/model/infra)
3. Stop trading if critical
4. Fix + validate
5. Resume + document in INCIDENT_LOG.md

---

## Expected Challenges

**Lookahead bias:**
- Most common cause of backtest vs live divergence
- Solution: Timestamp audit, feature generation review

**Model degradation:**
- Models trained on past data may not generalize
- Solution: Weekly retraining, IC monitoring, regime adaptation

**Operational overhead:**
- Daily monitoring time-consuming
- Solution: Automate health checks, weekly reviews only

**Infrastructure stability:**
- Server crashes, network issues
- Solution: Auto-restart, monitoring, backups

---

## Research Questions

1. Does backtest Sharpe translate to live?
2. How stable is regime detection in real-time?
3. Do features decay faster than expected?
4. Is 1-second latency sufficient?
5. What's the failure rate (crashes, data loss)?

---

## Lessons from Prior Work

**From Phase 6 (Alpha Research):**
- Walk-forward validation critical
- Feature decay real concern
- Ensemble models more robust

**From Phase 3 (Microstructure):**
- Real-time LOB reconstruction works
- Toxicity monitor useful for risk
- Synthetic quotes limitation

**Apply here:**
- Monitor feature IC daily
- Use ensemble for robustness
- Toxicity-based position sizing

---

## Next Phase

→ [[PHASE_8]] — Risk Management System (Planned)
