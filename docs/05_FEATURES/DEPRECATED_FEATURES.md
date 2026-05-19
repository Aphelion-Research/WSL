---
doc_type: catalog
system: Dominion
ragd_priority: 4
audience:
  - maintainer
status: active
last_reviewed: 2026-05-19
tags:
  - features
  - deprecated
  - legacy
---

# Deprecated Features

**Purpose:** Historical record of features that have been deprecated or removed.

**Status:** 8 deprecated features across Dominion development history.

**Deprecation Reasons:**
- Performance issues
- Data unavailability
- Better alternatives emerged
- Complexity > benefit
- Failed validation

---

## 1. Simple Average Fusion (Deprecated Phase 2)

**Original Purpose:**
Fuse multiple data sources using simple arithmetic mean.

**Implemented:** Phase 1 (Q1 2025)
**Deprecated:** Phase 2 (Q2 2025)

**Why Deprecated:**
Kalman filter bank provided 62% error reduction vs simple average (0.12% vs 0.32% RMSE).

**Replacement:**
[[PHASE_2]] — 6-timescale Kalman filter bank with dynamic trust scoring.

**Decision:**
[[ADR_0003_kalman_fusion_over_simple_average]]

**Code Removed:**
```python
# Old: data_pipeline/fusion/simple_average.py (deleted)
def fuse_simple(sources):
    return np.mean(sources, axis=0)
```

**Migration:**
All users automatically migrated to Kalman fusion (Q2 2025).

---

## 2. Twitter Sentiment Analysis (Deprecated Phase 6)

**Original Purpose:**
Extract sentiment from Twitter/X for alpha generation.

**Implemented:** Phase 4 (Q1 2026, experimental)
**Deprecated:** Phase 6 (Q2 2026)

**Why Deprecated:**
- Twitter API cost prohibitive ($5K/month for real-time)
- IC consistently weak (<0.02)
- Noise >> signal (bots, spam)
- 3 months research, no improvement

**Replacement:**
None. Sentiment analysis shelved pending better data source.

**Lessons Learned:**
Social media sentiment requires:
- Large-scale data (100K+ posts/day)
- Bot filtering
- Source credibility scoring
- Not viable for solo researcher budget

**Code Removed:**
```python
# Removed: research/sentiment/twitter_scraper.py
# Removed: research/sentiment/finbert_inference.py
```

---

## 3. Tick-Level Prediction (Deprecated Phase 6)

**Original Purpose:**
Predict next tick direction (up/down/flat) for ultra-short-term alpha.

**Implemented:** Phase 3 (Q4 2025, experimental)
**Deprecated:** Phase 6 (Q2 2026)

**Why Deprecated:**
- Accuracy only 52% (barely > random)
- Slippage dominates at tick level (2 bps spread)
- Requires real LOB data (synthetic quotes insufficient)
- Signal-to-noise ratio too low

**Replacement:**
Focus on 1-min+ horizons where signal stronger.

**Lessons Learned:**
Ultra-high-frequency trading requires:
- Real limit order book data (not synthetic)
- Sub-millisecond latency (co-location)
- Market maker infrastructure
- Not viable for retail futures trader

**Code Removed:**
```python
# Removed: microstructure/prediction/tick_lstm.py
# Removed: tests/test_tick_prediction.py
```

---

## 4. PostgreSQL Storage (Rejected Phase 1)

**Original Purpose:**
Use PostgreSQL for data storage.

**Considered:** Phase 1 (Q1 2025)
**Rejected:** Phase 1 (Q1 2025, never implemented)

**Why Rejected:**
- Operational overhead (server management, backups)
- Overkill for OLAP workloads
- DuckDB superior for analytics (columnar, in-process)

**Chosen Alternative:**
[[ADR_0005_duckdb_for_analytics_storage]] (to be created) — DuckDB for data storage.

**Never Implemented:**
No migration needed (rejected before implementation).

---

## 5. Manual Feature Engineering (Deprecated Phase 2)

**Original Purpose:**
Hand-craft features via manual pandas operations.

**Implemented:** Phase 1 (Q1 2025)
**Deprecated:** Phase 2 (Q2 2025)

**Why Deprecated:**
- Slow (30+ minutes for 400 features)
- Error-prone (manual formula translation)
- Not scalable

**Replacement:**
Vectorized feature generation pipeline with caching.

**Performance:**
- Before: 30 min per day
- After: <30 sec per day (60× speedup)

**Migration:**
Rewrote all features using numpy/pandas vectorized operations (Q2 2025).

---

## 6. Fixed Position Sizing (Deprecated Phase 8)

**Original Purpose:**
Fixed 10% allocation per position.

**Implemented:** Phase 1-6 (Q1 2025 - Q2 2026)
**Deprecated:** Phase 8 (Q4 2026)

**Why Deprecated:**
Dynamic position sizing (volatility-scaled Kelly) reduced drawdown by >20%.

**Replacement:**
[[PHASE_8]] — Volatility-scaled Kelly with regime + drawdown adjustments.

**Lessons Learned:**
Fixed sizing ignores:
- Volatility (high vol = too much risk)
- Regime (bear = reduce exposure)
- Drawdown (underwater = de-risk)

**Migration:**
All position sizing switched to dynamic (Q4 2026).

---

## 7. Single-Asset Focus (Deprecated Phase 9)

**Original Purpose:**
Trade only GC=F (gold futures).

**Implemented:** Phase 1-8 (Q1 2025 - Q1 2027)
**Deprecated:** Phase 9 (Q2 2027)

**Why Deprecated:**
Multi-asset portfolio provides:
- Diversification (lower drawdown)
- Higher Sharpe (1.5 vs 1.0)
- Reduced regime-specific risk

**Replacement:**
[[PHASE_9]] — 12-asset portfolio (metals, energy, currencies, indices, bonds).

**Migration:**
GC=F retained as asset #1, added 11 more (Q2-Q3 2027).

---

## 8. Regex-Based Markdown Parsing (Deprecated Phase 0)

**Original Purpose:**
Parse markdown docs using regex for RAGD ingestion.

**Implemented:** Phase 0 (Q4 2024)
**Deprecated:** Phase 0 (Q4 2024)

**Why Deprecated:**
Regex fragile (breaks on nested structures, code blocks, tables).

**Replacement:**
[[ADR_0002_native_cpp_scan_over_python]] — Native C++ markdown parser via tree-sitter.

**Performance:**
- Before: 201ms (Python regex, fragile)
- After: 18ms (C++ tree-sitter, robust)
- Speedup: 11×

**Migration:**
Automatic (RAGD rebuild with new parser, Q4 2024).

---

## Deprecation Statistics

| Reason | Count | Examples |
|---|---|---|
| Performance | 3 | Simple average, manual features, regex parsing |
| Failed validation | 2 | Twitter sentiment, tick prediction |
| Better alternative | 2 | PostgreSQL (→ DuckDB), fixed sizing (→ dynamic) |
| Scope expansion | 1 | Single-asset (→ multi-asset) |

---

## Deprecation Process

**Criteria for Deprecation:**

1. **Performance:** New approach >2× better
2. **Validation:** IC <0.03 after 3+ months research
3. **Complexity:** Maintenance cost > benefit
4. **External:** Data source unavailable/too expensive
5. **Obsolescence:** Better alternative exists

**Deprecation Workflow:**

1. Identify feature for deprecation
2. Document reason (this file)
3. Create ADR if major decision (e.g., [[ADR_0003_kalman_fusion_over_simple_average]])
4. Announce deprecation (CHANGELOG.md)
5. Provide migration path (if applicable)
6. Remove code (after migration complete)
7. Archive tests (move to `tests/deprecated/`)
8. Update documentation

**Grace Period:**
- Minor features: 1 sprint (2 weeks)
- Major features: 1 phase (1-3 months)
- Breaking changes: 2 phases (advance notice)

---

## Code Archaeology

**Removed Code Preserved In:**
- Git history (tags: `deprecated/twitter-sentiment`, `deprecated/tick-prediction`, etc.)
- Archive branch: `archive/deprecated-features`
- Documentation: This file

**How to Retrieve:**
```bash
# View deprecated feature code
git show deprecated/twitter-sentiment:research/sentiment/twitter_scraper.py

# Checkout archive branch
git checkout archive/deprecated-features
```

---

## Lessons Learned

**What Worked:**
- Performance-driven deprecation (Kalman vs simple average)
- Rapid prototyping + validation (kill bad ideas early)
- Clear migration paths (DuckDB, dynamic sizing)

**What Struggled:**
- Sunk cost fallacy (Twitter sentiment, 3 months wasted)
- Inadequate upfront research (tick prediction feasibility)
- Scope creep (should have killed tick prediction at prototype)

**Best Practices:**
1. Kill bad ideas fast (don't invest 3+ months)
2. Validate feasibility before implementation
3. Performance benchmark early (don't optimize prematurely, but test viability)
4. Document deprecation rationale (avoid rediscovering same mistakes)

---

## Anti-Patterns to Avoid

**"We might need it later"**
- No. If it's not useful now, delete it.
- YAGNI (You Aren't Gonna Need It).

**"It works, why deprecate?"**
- Maintenance cost compounds.
- 10 mediocre features < 5 great features.

**"Too much work to migrate"**
- Technical debt grows if not paid.
- Migration cost < long-term maintenance cost.

**"But I spent weeks on this!"**
- Sunk cost fallacy.
- Kill it and move on.

---

## Future Deprecation Candidates

**Under Review:**

1. **Economic Indicator Features** (Current: Alpha)
   - IC weak (<0.02)
   - Low frequency (monthly)
   - May deprecate if Phase 6 validation fails

2. **Regime-Switching Kalman Filter** (Current: Prototype)
   - Marginal improvement (~5%)
   - 3× computational cost
   - Likely to deprecate unless significant gain found

3. **Alternative Data (Satellite)** (Current: Prototype)
   - Cost prohibitive ($5K+/month)
   - No implementation yet
   - Likely to shelve indefinitely

**Review Frequency:**
- Experimental features: Monthly
- Beta features: Quarterly
- Production features: Annually

---

## Related Documentation

- [[CURRENT_FEATURES]] — Operational features
- [[PLANNED_FEATURES]] — Production roadmap
- [[EXPERIMENTAL_FEATURES]] — Research features
- [[ADR_INDEX]] — Architectural decision records
- [[CHANGELOG]] — User-facing changelog (to be created)

---

## Maintenance Notes

**Last Updated:** 2026-05-19 (Phase 5)

**Update Frequency:** As features deprecated

**How to Add:**
1. Announce deprecation (team/users if applicable)
2. Add entry here (include reason, replacement, migration)
3. Create ADR if major decision
4. Archive code (git tag + branch)
5. Remove from codebase (after grace period)
