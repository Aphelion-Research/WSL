---
doc_type: roadmap
system: Dominion
ragd_priority: 5
audience:
  - maintainer
  - owner
status: complete
last_reviewed: 2026-05-19
tags:
  - roadmap
  - phase-3
  - microstructure
---

# Phase 3: Microstructure Subsystems (Complete)

**Timeline:** Q3 2025 - Q4 2025 (5 weeks × 5 subsystems)  
**Status:** ✓ Complete

---

## Goals

Build 5 advanced microstructure subsystems:
1. LOB Reconstruction Engine
2. Execution Simulator
3. TCA Dashboard
4. Toxicity Monitor
5. Execution Alpha Features

---

## Deliverables

### Week 1-5: LOB Reconstruction
- [x] 10-level order book state machine
- [x] OFI (1s, 5s, 1m)
- [x] VPIN (50 buckets)
- [x] Roll/Corwin-Schultz spreads
- [x] Depth-weighted mid
- [x] 8/8 tests passing

### Week 6-10: Execution Simulator
- [x] Order matching engine
- [x] VWAP/TWAP/POV strategies
- [x] Almgren-Chriss market impact
- [x] Partial fills + slippage
- [x] 8/8 tests passing

### Week 11-15: TCA Dashboard
- [x] Cost attribution (decision/timing/impact/opportunity)
- [x] Benchmark vs VWAP/TWAP
- [x] Regime conditioning
- [x] 4/4 tests passing

### Week 16-20: Toxicity Monitor
- [x] VPIN + OFI integration
- [x] Adverse selection metrics
- [x] Composite toxicity score
- [x] Alerting system
- [x] 4/4 tests passing

### Week 21-25: Execution Alpha Features
- [x] 50 features (spread/depth/flow/quote/trade)
- [x] IC tracking (60min forward returns)
- [x] Decay monitoring
- [x] 6/6 tests passing

---

## Timeline

| Subsystem | Start | End | Status |
|---|---|---|---|
| LOB | 2025-07-01 | 2025-07-31 | ✓ |
| Exec Sim | 2025-08-01 | 2025-08-31 | ✓ |
| TCA | 2025-09-01 | 2025-09-30 | ✓ |
| Toxicity | 2025-10-01 | 2025-10-31 | ✓ |
| Exec Features | 2025-11-01 | 2025-11-30 | ✓ |
| **Phase 3 Total** | **2025-07-01** | **2025-11-30** | ✓ |

---

## Dependencies

**Requires Phase 2:**
- Multi-source data pipeline
- Kalman fusion (for fused prices)
- 400+ base features

**External:**
- None (all synthetic/simulated)

---

## Success Criteria

- [x] All 5 subsystems operational
- [x] 30/30 tests passing
- [x] Integration: LOB → Toxicity → ExecSim → TCA
- [x] Exec features IC >0.05 (top 10)
- [x] TCA cost attribution <20 bps total cost

---

## Integration Flow

```
LOB Engine → OFI + VPIN → Toxicity Monitor
            ↓
            Order Book State → Exec Simulator
                              ↓
                              Simulated Fills → TCA Dashboard
            
All subsystems → Exec Features → Data Pipeline
```

---

## Key Decisions

- Synthetic quotes (no real order book available from MT5)
- VPIN 50 buckets (balance sensitivity vs stability)
- Almgren-Chriss for impact (industry standard)
- 60min IC horizon (balance signal vs noise)
- Composite toxicity weights: VPIN=0.4, OFI=0.3, Adverse=0.3

---

## Blockers Encountered

1. **No real order book** (Workaround)
   - MT5 provides ticks only, no depth
   - Solution: Synthetic bid/ask generation (2 bps spread)

2. **Trade classification accuracy** (Accepted)
   - Lee-Ready ~70-80% accurate
   - Solution: Document limitation, note for future (bulk volume classification)

3. **IC instability early** (Resolved)
   - First 2 weeks IC noisy
   - Solution: Require 1000+ samples before trusting IC

---

## Metrics

| Subsystem | Tests | LOC | Key Metric |
|---|---|---|---|
| LOB | 8/8 | 800 | 1000 ticks/s ingestion |
| Exec Sim | 8/8 | 900 | 10K orders/s matching |
| TCA | 4/4 | 600 | <20 bps total cost |
| Toxicity | 4/4 | 500 | 0.7 alert threshold |
| Exec Features | 6/6 | 700 | 0.15 max IC (ofi_1m) |

**Totals:**
- Tests: 30/30 passing
- LOC: ~3500 Python
- Duration: 25 weeks (5 months)

---

## Lessons Learned

**What worked:**
- Week-long sprints kept focus
- Test-first approach prevented regressions
- Integration testing caught interface issues early

**What struggled:**
- Synthetic quotes limitation real
- Documentation lagged (caught up in Phase 5)
- Feature correlation not analyzed until later

---

## Next Phase

→ [[PHASE_4]] — HMM Regime Detection + Calendar Features
