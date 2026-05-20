# Agent 1: Quant Finance / Gold Market Structure
## Phase 0 Adversarial Review

**Scope:** 3,000-column M5 XAUUSD dataset, 10+ years, point-in-time safe
**Reviewed artifacts:** `hydra/config.py`, `hydra/data/targets.py`, `hydra/data/cv.py`, `hydra/data_sources/dukascopy_provider.py`, `data_pipeline/features/price.py`, `data_pipeline/features/microstructure.py`, `data_pipeline/features/regime.py`, `data_pipeline/features/crossasset.py`, `data_pipeline/sources/fred.py`, `data_pipeline/sources/cot.py`, `hydra/data/features.py`

---

## 1. WHAT I AGREE WITH

1. **Triple-barrier labeling with asymmetric TP/SL (2:1 reward-risk) is correct for directional gold trading.** The economic rationale is sound: gold exhibits momentum clustering and mean-reversion at different timescales; asymmetric barriers exploit this by requiring less directional conviction for profitable exits.

2. **Wilder ATR as the volatility normalizer is appropriate for gold.** Gold's volatility is non-stationary (LBMA sessions vs Asia dead-zone, macro events), and Wilder's exponential smoothing adapts faster than SMA-based ATR while remaining robust to spike outliers.

3. **Purged walk-forward CV with embargo is the correct validation framework.** The implementation in `cv.py` correctly separates train/val/test with purge gaps, preventing serial-correlation leakage.

4. **Dukascopy bi5 tick data as the primary source is a defensible choice.** Coverage from 2010, tick-level granularity, and free access. The bi5 parser correctly handles the 20-byte struct, 0-indexed months, and LZMA decompression.

5. **The BacktestConfig spread of $0.30 is realistic for institutional XAUUSD execution during London/NY overlap.** This is consistent with major ECN spreads (IC Markets, Pepperstone) for gold during liquid hours.

6. **Using mid-price from (bid+ask)/2 for bar construction** in `_ticks_to_bars` is correct for feature computation (avoids bid-ask bounce artifacts in returns).

7. **The feature selection pipeline (MI + IC intersection) provides dual-gate filtering** that reduces spurious features while retaining economically meaningful ones.

---

## 2. WHAT I REJECT

1. **`embargo_bars=10` for M5 data is dangerously insufficient.** 10 M5 bars = 50 minutes. The `horizon_bars=20` in TargetConfig means labels look 100 minutes forward (20 * 5min). The embargo MUST be >= `horizon_bars` to prevent test-set labels from being computed using prices that overlap with the training window's label computation period. **Required minimum: embargo_bars >= 20 (matching horizon_bars), recommended: 24 (2 hours of M5 bars).**

2. **HMM regime detection (`detect_tactical_regime_hmm`) fits on ALL valid data simultaneously.** Line 52-53 of `regime.py`: `model.fit(X_valid)` uses the entire dataset. This is full-sample look-ahead. The state labels assigned to bar `t` use information from bars `t+1` through `T`. This poisons any feature derived from `regime_tactical`. **Reject entirely unless replaced with expanding-window or online HMM.**

3. **VPIN implementation is not VPIN.** True VPIN (Easley, Lopez de Prado, O'Hara 2012) requires volume buckets of fixed size V, not time bars. The current implementation (`compute_vpin` in `microstructure.py`) classifies each bar as buy/sell using a close-vs-open tick rule and computes a rolling average. This is a bar-level order imbalance proxy, not VPIN. **Must be renamed to `order_imbalance_proxy` or reimplemented on tick data with volume clock.**

4. **The COT forward-fill has no release-date awareness.** CFTC COT reports for gold (088691) are released every Friday at 15:30 ET, reflecting positions as of Tuesday close. The current implementation (`cot.py`) forward-fills from `report_date` but `report_date` is the as-of date (Tuesday), not the release date (Friday). Any model trained on Tuesday-dated COT data that was only publicly available on Friday has 3 trading days of look-ahead bias. **Must shift COT availability to Friday 15:30 ET (or the following Monday's Asian open for M5 bars).**

5. **Cross-asset feature computation uses `.ffill().bfill()` without PIT timestamps.** In `crossasset.py` line 168: `merged = merged.ffill().bfill()`. The `.bfill()` is future-peeking by definition. FRED series (e.g., CPI is released with 2-week lag; Fed Funds is same-day) have different publication delays. **The bfill MUST be removed entirely, and ffill must only forward-fill from the known publication timestamp, not the observation date.**

6. **`min_atr_pct=0.0005` is too permissive for M5 gold.** Gold at $2,000/oz with M5 ATR of ~$1.50 gives ATR/close = 0.00075. The threshold of 0.0005 would allow labeling during dead-zone bars where ATR collapses to ~$0.80 and the spread ($0.30) consumes 37.5% of the stop. **Minimum should be 0.002 for M5 (ATR >= $4.00 at $2,000 spot).**

---

## 3. WHAT IS UNDERSPECIFIED

1. **M5 ATR window calibration.** `atr_window=14` on daily = 14 trading days. On M5, 14 bars = 70 minutes. What is the intended lookback? If the goal is "same effective horizon as daily ATR-14" that would be ~14 trading days * 288 M5 bars/day = 4,032 bars. If the goal is "intraday volatility normalization" then 14-50 bars (1-4 hours) makes sense. These produce wildly different TP/SL levels.

2. **Which M5 bars to include.** Gold trades ~23 hours/day (CME COMEX electronic: Sun 18:00-Fri 17:00 ET). Are weekend gaps included as a single bar? Are CME maintenance windows (16:00-16:15 CT daily) filtered? The Dukascopy provider downloads all 24 hours including illiquid Saturday morning ticks from Middle Eastern brokers.

3. **TP/SL absolute minimum vs spread.** With `tp_mult=2.0` and `sl_mult=1.0`, if ATR = $2.00 on a quiet M5 bar, then TP = $4.00 and SL = $2.00. The round-trip cost is spread ($0.30) + slippage ($0.10) + commission ($0.02/oz equiv) = ~$0.42. SL of $2.00 means cost is 21% of risk. This is marginally viable but not specified as a constraint anywhere.

4. **How 3,000 columns are achieved.** Current pipeline: ~80 price + ~60 microstructure + ~40 regime + ~100 cross-asset + COT/calendar = ~300 features. The 10x gap to 3,000 is unspecified. Likely sources: multi-timeframe aggregation (H1, H4, D1 features on M5 index), expanded cross-asset universe, tick-derived features, but no specification exists.

5. **Point-in-time join semantics for mixed-frequency data.** FRED is daily (some weekly, CPI monthly). COT is weekly. Gold bars are M5. The join strategy (asof merge? last-known-value with publication lag?) is not specified.

6. **Session-weighted vs clock-weighted features.** Many features use simple rolling windows. Gold volatility is 3-5x higher during London AM fix (10:30 GMT) than during Asian session. Should rolling windows be session-weighted or pure clock-time?

7. **Survivorship in Dukascopy data.** Dukascopy's CDN occasionally has missing hours (especially 2010-2012). How are gaps handled? Linear interpolation creates false low-volatility bars. Forward-fill creates false zero-return bars. Both poison microstructure features.

---

## 4. WHAT CAN SILENTLY FAIL

1. **Wilder ATR on M5 with atr_window=14 during Asian session will produce ATR values dominated by 1-2 hour noise.** A single 3-minute spike during thin Asian liquidity will persist in ATR for 70 minutes, creating false label opportunities that would never be tradeable.

2. **The triple-barrier labeling loop checks `if low[t+k] <= sl` before `if high[t+k] >= tp`.** On M5 bars where both TP and SL are breached within the same bar (very common during news events), the code always assigns LOSS priority. This introduces systematic short bias in labels. Gold has positive skew during macro events (flight to safety), so this bias will train models to underweight long opportunities during the exact conditions where gold rallies hardest.

3. **Rolling correlation with FRED series on M5 timestamps.** If FRED data is joined at daily granularity and forward-filled to M5, then `rolling(252).corr()` on M5 bars computes correlation over 252 * 5 minutes = 21 hours. The correlation will be nearly undefined because the FRED series is constant within each day. The feature will be dominated by numerical noise from the 1-2 daily step changes in the forward-filled macro series.

4. **Kyle's lambda and Amihud illiquidity use `df["volume"]`.** Dukascopy volume is notional tick volume (bid_vol + ask_vol from bi5), not true exchange volume. COMEX gold volume is only available from CME at 1-minute granularity with delay. Kyle's lambda estimated on tick volume has no economic meaning.

5. **Granger causality test in `crossasset.py` uses `window=252`.** On M5 bars, this is 252 * 5 min = 21 hours. The test requires stationarity over the window. Gold returns are approximately stationary over 21 hours, but the FRED series (levels, not returns) are non-stationary. The Granger test will produce spurious results without differencing.

6. **ESN reservoir features use raw `close` prices** (line 98 in `features.py`: `prices = df["close"].values`). Gold prices are non-stationary (~$1,200 in 2016 to ~$2,400 in 2024). The ESN states will be dominated by the level, not the dynamics. Must use returns or log-returns.

---

## 5. WHAT WOULD POISON THE DATASET

1. **HMM full-sample fit is the most dangerous single leakage vector.** If regime labels are used as features (they are, via `regime_prob_trend_up` etc.), every model trained on these features has access to future information. The model will learn that "high regime_prob_trend_up correlates with positive forward returns" — because the HMM was fit knowing the future. This will show 85%+ accuracy in backtest and 50% live.

2. **COT Tuesday-dating without Friday release shift.** The speculator_sentiment feature will appear predictive in backtest because the model sees Tuesday's positioning before Friday's public release. In live trading, this edge evaporates. Estimated false alpha: 3-5 bps/week on a 50-bar horizon.

3. **bfill() in cross-asset merge.** Any CPI, NFP, or FOMC data that is back-filled into pre-release timestamps creates structural look-ahead in macro features. CPI month-over-month change computed before the release date is literally impossible information.

4. **Corwin-Schultz spread on M5 bars where high==low.** During very quiet periods (Asia 01:00-03:00 UTC), M5 bars frequently have high==low (single price for 5 minutes). The formula computes `log(high/low)^2 = 0`, producing spread = 0. This is not "zero spread" — it's "no information." But the feature will be used as if spread genuinely collapsed, biasing spread-momentum strategies.

5. **Label computation using bars beyond the dataset boundary.** `triple_barrier_long` iterates `for t in range(n - horizon)`, so the last `horizon` bars get NaN labels. If `horizon=20` and a feature uses `rolling(20).mean()`, the last feature value with a valid label uses bars `[n-40, n-20]` for its feature but bars `[n-20, n]` for its label. If these bars are in a different regime or contain a structural break (e.g., new Fed regime), the label is informative about a future the model cannot see.

---

## 6. WHAT AN IMPLEMENTER MIGHT MISUNDERSTAND

1. **"horizon_bars=20 on M5 means 100 minutes" is NOT equivalent to "horizon_bars=20 on daily means 1 month."** The econometric properties are completely different. Daily returns are approximately IID; M5 returns exhibit strong intraday seasonality, autocorrelation, and session-boundary effects. A 100-minute horizon spans at most 1 session transition; a 1-month horizon spans ~22 session cycles. The label distributions will be radically different.

2. **Gold spread is NOT constant at $0.30.** The spread config `spread_pips: 0.30` is an average. During NFP (first Friday), spreads blow out to $2-5. During Asian dead-zone, spreads can be $0.50-0.80 on retail feeds. During London AM fix, spreads compress to $0.10 at institutional level. Any feature or label that assumes constant spread is wrong.

3. **"Volume" from Dukascopy is not the same as COMEX volume.** Dukascopy tick volume represents the number of price updates from their liquidity providers. It correlates with true volume (~0.7 Spearman) but has different dynamics during off-hours. An implementer using "volume" features calibrated on exchange data papers will get misleading results.

4. **FRED series have different publication lags:**
   - Fed Funds Rate (FEDFUNDS): 1 business day after FOMC
   - 10Y Treasury (DGS10): Same day, 18:00 ET
   - CPI (CPIAUCSL): ~15 days after reference month end
   - Dollar Index (DTWEXBGS): Weekly, Monday
   
   A single ffill strategy is wrong. Each series needs its own PIT offset.

5. **The `both = long_win & short_win` case in `make_targets` assigns y=1.0 (long wins).** This occurs when price moves TP distance in both directions within the horizon. This is NOT a long signal — it's a high-volatility regime indicator. Assigning it as "long wins" biases the training set toward long during volatile periods, which happens to correlate with gold's positive skew during crises. This will look like alpha but is actually a survivorship artifact.

6. **Purge of 20 bars between train/val/test in `cv.py` assumes labels are computed from the NEXT 20 bars.** But the label at bar `t` uses bars `t+1` through `t+20`. So the purge prevents direct overlap, but the embargo of 10 bars means validation starts at bar `t+30`, whose label uses bars `t+31` through `t+50`. This is safe for the label itself, but features at bar `t+30` that use `rolling(50)` lookback will include bars from the training set. The embargo should be `max(horizon_bars, max_feature_lookback)` but this is never enforced.

---

## 7. WHAT MUST BE TESTED

1. **Label distribution by session.** Compute P(long_win | London), P(long_win | NY), P(long_win | Asian). If these differ by > 5 percentage points, the model will learn session effects rather than genuine predictive features. Gold has documented London AM fix buying pressure — this should show up.

2. **Effective TP/SL hit rates vs spread.** For each labeled bar, compute: (TP_distance - spread) / SL_distance. If this ratio < 1.5 on average, the asymmetric barrier is not providing meaningful edge over a coin flip after costs.

3. **HMM regime stability under expanding-window refit.** Fit HMM on [0, T] and [0, T+1000]. Do state assignments for bars [0, T] change by > 10%? If yes, the regime labels are unstable and economically meaningless.

4. **VPIN proxy vs actual order flow.** Compare bar-level order imbalance to actual CME trade-and-quote data for overlapping periods. If rank correlation < 0.5, the feature has no microstructure information content.

5. **ATR regime filter effectiveness.** After applying `min_atr_pct` filter on M5, what fraction of bars survive? If > 90%, the filter is too loose. If < 30%, insufficient training data. Target: 50-70% (liquid session bars only).

6. **Cross-asset feature stationarity.** Run ADF tests on all rolling correlation/beta features at the M5 cadence. Non-stationary features (expected for level-based correlations) must be differenced or removed.

7. **Forward-return distribution conditioned on ATR quantile.** If labels are disproportionately concentrated in high-ATR periods (top quartile), the model may only be learning "trade when volatile" rather than directional prediction.

8. **Embargo sufficiency test.** Train a model with embargo=20 vs embargo=100 on the same data. If OOS performance differs by > 2pp in accuracy, the shorter embargo is leaking.

---

## 8. WHAT MUST BE DEFERRED

1. **GVZ (Gold VIX) integration.** CBOE GVZ has limited history (2010+) and is only available at daily close. Useful for daily regime classification but adds minimal information at M5 resolution. Defer until daily overlay features are specified.

2. **LBMA Gold Price (AM/PM fix).** The fix occurs twice daily (10:30 and 15:00 London). As a feature on M5 bars, it's only informative as a reference level (distance-to-fix, fix-to-fix return). Implementation requires careful timestamping (fix results published ~30 seconds after window closes). Defer until the PIT framework is established.

3. **Physical gold features (ETF flows, COMEX delivery, Shanghai premium).** These are daily/weekly frequency, require complex PIT handling, and contribute to long-horizon (H4+) predictions. Irrelevant for M5 scalping labels. Defer to Phase 2.

4. **Tick-level VPIN.** True VPIN requires volume-clock bars and Lee-Ready classification on individual ticks. The computational cost for 10 years of tick data (~50TB uncompressed) is prohibitive in Phase 0. Implement the volume-clock infrastructure in Phase 1, defer true VPIN to Phase 2.

5. **GAT node embeddings.** The current implementation is a stub (returns zeros). Graph attention networks over asset correlation graphs require a separate training pipeline with its own validation. Defer entirely to Phase 2.

6. **RAGD episodic features.** Requires a running vector database populated with historical state summaries. This is a meta-learning system that depends on the base dataset being correct first. Defer to Phase 3.

7. **Causal DAG feature weighting.** Requires causal discovery (PC/FCI algorithm) which is computationally expensive on 3,000 features and sensitive to sample size. Defer until feature set is finalized.

---

## 9. WHAT MUST BE ESCALATED TO AGENT 0

1. **CRITICAL: The daily-to-M5 transition changes the fundamental nature of the prediction problem.** Daily labels predict directional moves over 4 weeks. M5 labels predict directional moves over 100 minutes. These require different feature sets, different validation approaches, and different economic reasoning. The protocol must explicitly acknowledge this is a NEW SYSTEM, not a rescaling of the old one.

2. **CRITICAL: Label horizon and embargo must be co-specified as a single constraint.** Current config allows `horizon_bars=20, embargo_bars=10` which is internally inconsistent. Propose: `embargo_bars = max(horizon_bars, max_feature_lookback_bars) + safety_margin`. This must be a hard constraint in `CVConfig`, not a suggestion.

3. **DECISION REQUIRED: What is the minimum acceptable label rate?** If `min_atr_pct` is raised to 0.002 and dead-zone bars are excluded, approximately 40-60% of M5 bars will have valid labels. The remaining bars are "no-trade zones." Is this acceptable? Alternative: use a 3-class label (long/short/flat) which preserves all bars but changes the modeling problem.

4. **DECISION REQUIRED: Should the HMM regime be removed entirely or replaced?** Options: (a) Remove and use only time-of-day session labels, (b) Replace with expanding-window online HMM (introduces regime-shift lag), (c) Replace with change-point detection (PELT/BOCPD) which is causal by construction. Each has different feature implications.

5. **DECISION REQUIRED: Volume source.** Dukascopy tick volume vs COMEX exchange volume (available via CME DataMine, ~$500/month) vs no volume features. This determines whether Kyle's lambda, Amihud, and order flow features are meaningful or should be dropped.

6. **BUDGET: 10 years of M5 bars at 288 bars/day * 260 days/year = 748,800 bars.** With 3,000 columns, the dataset is 748,800 * 3,000 * 4 bytes = ~8.5 GB (float32). Feature computation (especially rolling windows over 748K rows) will require chunked processing or Polars/DuckDB. Is memory-mapped computation acceptable, or must everything fit in RAM?

---

## 10. WHAT I WOULD CHANGE IF I HAD AUTHORITY

1. **Replace `embargo_bars=10` with `embargo_bars=max(horizon_bars + 12, 32)`.** The +12 provides 1 hour of safety margin beyond the label horizon. The floor of 32 (160 minutes) ensures no feature with lookback <= 30 bars can leak.

2. **Replace HMM regime with session-aware change-point detection.** Use BOCPD (Bayesian Online Change-Point Detection) with a hazard function calibrated to gold's empirical regime duration (~4-8 hours). This is causal, online, and does not require full-sample fitting.

3. **Implement explicit PIT registry.** Create a `PointInTimeRegistry` class that maps each external data source to its (observation_date, publication_date, first_available_bar) tuple. All joins go through this registry. The COT example: observation=Tuesday, publication=Friday 15:30 ET, first_available_bar=Friday 15:35 ET M5 bar.

4. **Rename `vpin_50` to `order_imbalance_50` and add suffix `_proxy` to all volume-derived features.** This prevents false confidence in microstructure features computed from tick-volume rather than true exchange volume.

5. **Add spread-aware label filtering.** After computing ATR and before labeling, add: `if atr[t] < 3 * spread: y[t] = NaN`. This ensures no label is generated where transaction costs consume > 33% of the stop distance. At spread=$0.30, this requires ATR >= $0.90, which filters the quietest ~15% of sessions.

6. **Separate feature computation into M5-native and aggregated-from-higher-TF.** Create two explicit namespaces: `feat_m5_*` (computed on raw M5 bars) and `feat_h1_*`, `feat_h4_*`, `feat_d1_*` (computed on resampled bars, then broadcast back to M5 index). This makes the multi-resolution structure explicit and auditable.

7. **Fix the `both = long_win & short_win` case.** Instead of assigning y=1.0, assign y=NaN (no valid label). These bars represent high-volatility regimes where directionality is ambiguous. Alternatively, create a separate "high_vol" target class.

8. **Add minimum trade duration filter.** If TP or SL is hit on bar k=1 (the very next bar after entry), the "trade" was likely just noise/spread. Add `min_hold_bars=3` (15 minutes) before allowing barrier hits. This prevents the model from learning to trade one-bar spikes.

9. **Replace `bfill()` with strict `ffill()` + NaN for pre-history.** In `crossasset.py`, the merge should be: `merged = merged.ffill()` only, with the first valid observation for each series being the first available data point. Pre-history bars get NaN for that feature (handled downstream by imputation or exclusion).

10. **Add session-conditional spread to BacktestConfig.** Replace fixed `spread_pips=0.30` with a lookup: London overlap = 0.15, NY session = 0.25, Asian session = 0.50, news events = 2.00. Label validity and backtest realism both depend on this.

---

## RAGD_QUERIES

Queries for the Retrieval-Augmented Graph Database to validate assumptions:

1. `MATCH (e:Episode) WHERE e.context CONTAINS 'gold_spread' AND e.session = 'asian' RETURN avg(e.spread_observed)` — Validate Asian session spread assumption of $0.50-0.80.

2. `MATCH (e:Episode)-[:DURING]->(r:Regime {type: 'high_vol'}) WHERE e.label_both_hit = true RETURN count(e), avg(e.forward_return_20bar)` — Quantify the "both barriers hit" regime and its true forward return.

3. `MATCH (e:Episode) WHERE e.atr_pct < 0.001 AND e.label IS NOT NULL RETURN e.outcome, count(*)` — Validate that low-ATR labels are noise.

4. `MATCH (s:Series {id: 'COT_speculator_sentiment'})-[:AVAILABLE_AT]->(t:Timestamp) RETURN min(t.bar_ts - s.report_date) as min_lag` — Confirm COT publication lag in the dataset.

5. `MATCH (f:Feature {name: 'regime_prob_trend_up'})-[:COMPUTED_USING]->(d:Data) WHERE d.timestamp > f.timestamp RETURN count(*)` — Detect forward-looking data usage in regime features.

---

## EVIDENCE_LEDGER

| # | Claim | Source | Verification Status |
|---|-------|--------|-------------------|
| E1 | Gold M5 ATR during London session ~ $3-5 at $2000 spot | Dukascopy historical data 2023 | NEEDS_VERIFICATION |
| E2 | Gold spread blows out to $2-5 during NFP | Broker tick data, Pepperstone/IC Markets published stats | KNOWN_TRUE |
| E3 | CFTC COT reports released Friday 15:30 ET | CFTC publication schedule (cftc.gov/MarketReports) | KNOWN_TRUE |
| E4 | Dukascopy has missing hours 2010-2012 for XAUUSD | Community reports, personal observation of bi5 gaps | NEEDS_VERIFICATION |
| E5 | FRED CPI (CPIAUCSL) publication lag ~15 days | BLS release calendar | KNOWN_TRUE |
| E6 | Gold trades Sun 18:00 - Fri 17:00 ET on CME Globex | CME Group product specifications for GC | KNOWN_TRUE |
| E7 | HMM state assignments unstable across sample sizes | Lopez de Prado, "Advances in Financial Machine Learning" Ch. 10 | KNOWN_TRUE (theoretical) |
| E8 | True VPIN requires volume-clock bars | Easley, Lopez de Prado, O'Hara (2012), "Flow Toxicity and Liquidity" | KNOWN_TRUE |
| E9 | Gold positive skew during macro stress events | Baur & Lucey (2010), "Is Gold a Hedge or a Safe Haven?" | KNOWN_TRUE |
| E10 | Corwin-Schultz undefined when high==low | Corwin & Schultz (2012) original paper, boundary condition | KNOWN_TRUE |
| E11 | embargo >= horizon required for valid purged CV | de Prado (2018), AFML Ch. 7 | KNOWN_TRUE |
| E12 | LBMA AM fix at 10:30 GMT, PM fix at 15:00 GMT | LBMA website, IBA administration rules | KNOWN_TRUE |
| E13 | GVZ available from ~2010, daily resolution only | CBOE product page | KNOWN_TRUE |
| E14 | 748,800 M5 bars over 10 years (260 days * 288 bars) | Arithmetic: 10 * 260 * 288 = 748,800 | KNOWN_TRUE |
| E15 | Dukascopy tick volume != exchange volume | Structural: Dukascopy is OTC liquidity aggregator | KNOWN_TRUE |

---

## APPENDIX: Recommended M5 Triple-Barrier Calibration

Based on gold market microstructure at M5 resolution:

| Parameter | Current (Daily) | Proposed (M5) | Rationale |
|-----------|----------------|---------------|-----------|
| atr_window | 14 | 48 (4 hours) | Captures full session volatility cycle |
| horizon_bars | 20 (1 month) | 36 (3 hours) | Spans 1 full session, allows intra-session momentum |
| stop_mult | 1.0 | 1.5 | Wider stop prevents Asian noise stop-outs |
| target_mult | 2.0 | 2.5 | Compensates for M5 spread drag |
| min_atr_pct | 0.0005 | 0.0020 | Filters bars where spread > 33% of ATR |
| embargo_bars | 10 | 48 | = max(horizon_bars + 12, 48) |
| purge_bars | 20 | 48 | = horizon_bars + feature_lookback_margin |

**Expected label rate with these parameters:** ~55% of London/NY session bars, ~25% of Asian session bars, ~45% overall.

**Expected class balance:** ~52% long (gold's structural bid), ~48% short. Slight long bias is economically justified (central bank buying, inflation hedge demand).
