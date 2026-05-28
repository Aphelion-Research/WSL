# Agent 6 Report: Mathematical Physics / Signal Processing

**Phase:** 0 (Adversarial Review)
**Agent:** 6 — Mathematical Physics & Signal Processing
**Scope:** Blocks X (Advanced Statistical, 120 cols), Y (Advanced Network, 60 cols), Z1 (Regime & State, 90 cols)
**Date:** 2026-05-20

---

## 1. WHAT I AGREE WITH

1. **PCA per-fold fitting is correct.** The current `esn_features()` in `hydra/data/features.py` calls `pca.fit(combined[train_idx])` which is the correct approach for cross-validation. No future information leaks into the PCA basis for the fold under evaluation.

2. **Fractional differentiation (FFD) is causal by construction.** The convolution in `data_pipeline/features/price.py` uses historical weights only. The choice of d=0.4 is within the standard range (0.3-0.5) for maintaining memory while achieving stationarity per Marcos Lopez de Prado's research.

3. **Transfer entropy formulation is directionally correct.** The KSG-style estimator in `causal_engine/information.py` uses `TE(X->Y) = H(Y|Y_past) - H(Y|Y_past, X_past)` which is the standard definition. The `max(te, 0.0)` clamp is appropriate since negative TE is estimation noise.

4. **Path signatures are causal by mathematical construction.** The iterated integral of a path over [0,T] uses only data up to T. This is one of the few advanced features that requires zero additional leakage-prevention machinery.

5. **ESN reservoir states are causal.** The sequential update `x[t] = f(x[t-1], u[t])` means each state depends only on current and past inputs. The multi-scale design (spectral radii 0.5, 0.9, 0.99) gives three memory timescales — this is sound physics.

6. **Column budget allocation is reasonable.** X=120, Y=60, Z1=90 totaling 270 advanced columns is manageable for a feature matrix of ~725K rows given 32GB RAM constraints (~1.5GB at float32).

7. **The Hurst exponent implementation is causally correct.** Rolling windows looking backward only, R/S analysis on `data[T-w:T]`.

---

## 2. WHAT I REJECT

1. **HMM full-sample fit is unacceptable — CONFIRMED LEAKAGE.** In `data_pipeline/features/regime.py` line 53: `model.fit(X_valid)` where `X_valid` is the ENTIRE dataset. This is the single most dangerous leak in the codebase. The HMM sees future returns, future volatility regimes, and future volume patterns when assigning labels to historical bars. Every downstream model trained on these regime features receives future information. **This must be blocked from entering any training pipeline until refactored.**

2. **The conditional entropy estimator in `causal_engine/information.py` is mathematically wrong.** Lines 73-89 use `KNeighborsRegressor` prediction residual variance as a proxy for conditional entropy. This assumes Gaussianity of residuals (H = 0.5*log(2*pi*e*var)), which contradicts the entire purpose of using a non-parametric k-NN estimator. The correct KSG estimator uses digamma functions on k-NN distances, not regression residual variance. The current implementation will systematically underestimate TE for non-Gaussian processes (heavy-tailed financial returns).

3. **TDA on 725K rows is computationally infeasible without fundamental redesign.** Vietoris-Rips complex on n points is O(n^3) in memory and O(n^4) in time for the full persistence computation. Even with windowing at 200 bars, computing 725K windows at O(200^3) = O(8M) operations each yields ~5.8 trillion operations. This cannot be parallelized naively because each window must be computed sequentially for causality. The "sparse approximation" hand-wave in the spec is insufficient.

4. **The FFD convolution uses `mode='same'` which introduces non-causal boundary effects.** In `data_pipeline/features/price.py` line 182: `np.convolve(price, weights, mode='same')` — the 'same' mode pads the output to match the input length, which means the convolution at early indices uses zero-padding that implicitly assumes knowledge about the series length. Should use `mode='full'` and truncate, or `mode='valid'` and left-pad with NaN.

5. **The proposed monthly PCA refit schedule (120 refits over 10 years) ignores structural breaks.** PCA loadings fitted before a structural break (e.g., COVID-19 March 2020, 2022 rate hikes) will be catastrophically wrong for post-break data. Monthly refit frequency means up to 20 trading days of stale loadings after a regime change. The spec should mandate event-triggered refits in addition to calendar refits.

---

## 3. WHAT IS UNDERSPECIFIED

1. **Wavelet mother function and decomposition level are unspecified.** CWT with Morlet gives excellent frequency localization but O(n*scales) compute. DWT with Daubechies-4 is O(n) but has poor frequency resolution. The spec says "wavelets (30 cols)" but does not specify:
   - Which wavelet family (Morlet, db4, sym5, coif3)?
   - How many scales/levels (4-8 for DWT, 20-100 for CWT)?
   - Which summary statistics per scale (energy, entropy, coefficients themselves)?
   - Boundary handling (zero-padding, symmetric extension, periodic)?

2. **Path signature truncation level and input dimensionality are unspecified.** For a d-dimensional path truncated at level k, the signature has `sum(d^i, i=1..k)` components. For d=1 (just price): level 4 gives 4 features. For d=5 (OHLCV): level 3 gives 5+25+125 = 155 features — already exceeding the Block X budget. The spec must fix: which channels enter the path, and what truncation level.

3. **Persistent homology parameters lack concrete values.** The Takens embedding requires:
   - Embedding dimension (typically 2-10, affects complexity as O(n^dim))
   - Time delay (1 bar? 5 bars? Must relate to dominant frequency)
   - Filtration range (max edge length — too small misses topology, too large is O(n^3))
   - Which topological summaries: Betti curves? Persistence landscapes? Persistence entropy? Silhouettes?

4. **Transfer entropy window size and recomputation frequency are unspecified.** For M5 bars, 500 bars = 1.7 trading days. Is this rolling (every bar) or fixed windows (every 500 bars)? Rolling gives 725K computations of O(500^2) = 181 billion operations. Fixed windows give 1,450 computations — feasible but loses granularity.

5. **The HMM expanding window refit lacks a warm-start strategy.** When refitting weekly with expanding data, does the new model initialize from the previous model's parameters, or cold-start? Cold-start risks label permutation (state 1 in week 50 maps to state 3 in week 51). Warm-start risks getting stuck in local optima as the data distribution shifts.

6. **Changepoint detection algorithm is unspecified.** PELT? Binary segmentation? BOCPD (Bayesian online)? Each has different computational profiles and causality guarantees. Only BOCPD is truly online/causal. PELT and binary segmentation are retrospective.

7. **Cross-asset universe for Block Y is undefined.** Transfer entropy requires pairs. Which assets? DXY, UST10Y, VIX, SPX, Oil — these 5 plus Gold give 30 directional pairs. But data availability at M5 frequency for all these is not guaranteed (FRED is daily).

---

## 4. WHAT CAN SILENTLY FAIL

1. **PCA on insufficient data produces unstable components.** First year of expanding window: ~60K M5 bars. PCA with 30 components on 3000-dimensional ESN states needs at minimum p << n (components << samples). This holds (30 << 60K), BUT the explained variance ratio will be highly volatile month-to-month in early periods, causing feature magnitudes to jump discontinuously at each refit boundary.

2. **HMM state label permutation across refits.** Even with warm-start, there is no guarantee that "state 2" in refit_k maps to "state 2" in refit_{k+1}. The current mapping by mean return (`state_means.sort()`) will flip labels when a regime's average return crosses another's — creating discontinuous jumps in regime probability features. This is not a bug but a fundamental limitation of mixture models.

3. **Wavelet boundary coefficients are meaningless.** DWT at level L produces boundary-affected coefficients for the first 2^L - 1 samples at each decomposition level. For level 7 (128 samples), the first 127 values of the detail coefficients are unreliable. If these are included without NaN-masking, they inject noise.

4. **Path signatures of constant price segments are zero.** In low-volatility regimes (Asian session dead zones), the signature will be identically zero or numerically epsilon, causing division-by-zero in any downstream normalization. Need explicit handling.

5. **Transfer entropy estimator returns 0.0 for short windows.** Line 35 in `causal_engine/information.py`: `if n < k + 1: return 0.0`. With k=5 (default) and lag=1, any window shorter than 7 bars returns zero. This is correct defensively but means early-window features are constant zeros that models may memorize.

6. **Persistent homology on flat price series produces trivial topology.** When price is locally linear (trending strongly), the Vietoris-Rips complex collapses to contractible simplicial complexes with trivial Betti numbers (B0=1, B1=0, B2=0...). The "features" become constants, wasting columns.

7. **Bipower variation normalization constant is wrong.** In `data_pipeline/features/microstructure.py` line 137: `bpv = (abs_returns * lagged_abs).rolling(window).sum() * (np.pi / 2)`. The correct normalization for bipower variation is `mu_1^{-2}` where `mu_1 = sqrt(2/pi)`, so the multiplier should be `pi/2` per unit, but applied as `(pi/2) * (1/n) * sum(|r_t||r_{t-1}|)`. The missing `1/n` makes BPV scale linearly with window size, making the jump component (`RV - BPV`) non-comparable across different window sizes.

---

## 5. WHAT WOULD POISON THE DATASET

1. **HMM full-sample leakage (CRITICAL).** Every row in the dataset currently receives regime labels computed from ALL rows including future data. If Block Z1 regime features are computed from this HMM, all 90 columns of Z1 are poisoned. Any model trained on Z1 will appear to have supernatural predictive power that vanishes in live trading. **Severity: dataset-destroying.**

2. **PCA refit without embargo period.** If PCA is refitted at time T using data[0:T], and the new components are applied starting at row T, then row T's features were partially determined by row T's data (the last observation in the fitting window). Standard practice: apply new PCA starting at T + embargo (typically T + 1 bar minimum, T + 1 day preferred). Without embargo, leakage is 1 bar — small but systematic.

3. **Wavelet CWT with full-length computation.** If `cwt(price[0:T], scales)` is computed once on the full series and then sliced, the scalogram at time T can be influenced by boundary effects from both ends. CWT must be computed causally: `cwt(price[0:T])` for each T, or using causal wavelets (analytic signal, minimum-phase).

4. **Transfer entropy computed on pre-normalized data.** If features are z-scored over the full sample before computing TE, the z-score normalization leaks future mean/variance into the TE computation. TE must operate on raw or rolling-normalized data.

5. **Regime transition probability matrix estimated on full history.** The transition matrix P[i,j] = P(state_j at t+1 | state_i at t) estimated from all data tells you the long-run transition dynamics including future regime switches. Must be estimated on expanding window [0:T] only.

6. **Changepoint detection via retrospective algorithms.** PELT and binary segmentation identify changepoints by looking at the full segment. A changepoint detected at bar 5000 using data[0:10000] means the model "knows" at bar 5000 that a change occurred there — but in real-time at bar 5000, you cannot know if the current bar is a changepoint without future context. Only BOCPD (Bayesian Online Changepoint Detection) is causal.

---

## 6. WHAT AN IMPLEMENTER MIGHT MISUNDERSTAND

1. **"Expanding window PCA" does not mean recompute on every bar.** At 725K bars with monthly refit, there are ~120 refit points (12/year * 10 years). Between refits, the SAME PCA model transforms new data. An implementer might interpret "expanding" as "refit every bar" — creating 725K PCA fits, which is both computationally absurd and unnecessary.

2. **Path signature level k does NOT produce k features for multivariate paths.** For a d-dimensional path at level k: features = d + d^2 + d^3 + ... + d^k. A 5D path (OHLCV) at level 3 produces 5+25+125 = 155 features. An implementer counting "20 columns for signatures" needs d=1 at level 4 (giving 4 features) or d=2 at level 2 (giving 2+4=6 features). The combinatorial explosion must be explicitly controlled.

3. **HMM `predict_proba()` returns posteriors, not filtered probabilities.** The hmmlearn `predict_proba()` uses the forward-backward algorithm, which runs the BACKWARD pass through future data to compute smoothed posteriors. For causal features, you must use ONLY the FORWARD pass: `model._do_forward_pass(X)` to get filtered (causal) state probabilities. Using `predict_proba()` on the full sequence is equivalent to peeking at future data for each bar's state assignment.

4. **"Causal wavelet transform" is not the same as "CWT computed on past data."** Even if you compute CWT(data[0:T]), the finite-length edge effects at time T mean the last few coefficients are unreliable. A truly causal wavelet uses an asymmetric (minimum-phase) wavelet that concentrates filter energy in the past. Morlet is symmetric — it is NOT causal even when computed on past-only data.

5. **Persistent homology is NOT a time series method by default.** Takens embedding converts a scalar time series into a point cloud in R^d (delay embedding). The TDA then operates on this point cloud. An implementer might try to compute persistence directly on the time series as a 1D filtration, which gives only trivial topology (connected components).

6. **Transfer entropy is not symmetric and not transitive.** TE(X->Y) != TE(Y->X) in general. An implementer might compute only one direction and assume symmetry. For 10 assets, you need the FULL 10x10 directed matrix (100 values minus 10 diagonal = 90 directed TE values).

---

## 7. WHAT MUST BE TESTED

1. **Leakage test for HMM regime features.** Train a model using ONLY regime features (Block Z1) to predict next-bar returns. If accuracy >> 50% on held-out data sliced by TIME (walk-forward), the features leak. If accuracy drops to ~50% when HMM is retrained with expanding window, the leakage is confirmed eliminated.

2. **PCA component stability test.** Compute cosine similarity between PCA loadings at consecutive refit points. If similarity < 0.8, the components are too unstable for the refit frequency. Test: cos_sim(V_month_k, V_month_{k+1}) for all k.

3. **Computational feasibility benchmark.** Time the following on a single year of M5 data (~75K bars):
   - TDA with window=200: expect >1 hour if using Ripser on dense point clouds
   - Path signatures with level=4, d=5: expect <1 minute (iisignature is fast)
   - Transfer entropy for 10 pairs with window=500: expect ~10 minutes with KSG
   - HMM refit with expanding window: expect <30 seconds per refit

4. **Null distribution test for TDA features.** Compute persistent homology features on shuffled (permuted) price series. If TDA features on real data are statistically indistinguishable from shuffled data (KS test p > 0.05), the features carry no information and should be dropped.

5. **Transfer entropy significance test.** Compute TE on 1000 time-shifted surrogates (shift X by random lag, breaking causal coupling). The real TE must exceed the 95th percentile of surrogate TEs to be considered significant. Features below this threshold should be set to zero.

6. **FFD boundary test.** Verify that `compute_frac_diff()` with `mode='same'` does not produce anomalous values in the first `len(weights)` rows. Compare against `mode='valid'` implementation.

7. **Path signature invariance test.** Signatures are reparametrization-invariant. Test: compute sig(path) and sig(path_time_warped). They should be identical (up to numerical precision). If not, the implementation is wrong.

8. **HMM label permutation test.** Across 10 consecutive weekly refits, verify that state labels maintain semantic consistency (state mapped to "trending_up" actually has positive mean return in THAT window's data, not historical data).

---

## 8. WHAT MUST BE DEFERRED

1. **Full persistent homology pipeline (Block X TDA component).** Until:
   - Ripser++ or GUDHI with sparse filtration is benchmarked on 725K rows
   - Window size is determined by empirical autocorrelation length
   - Null distribution testing confirms information content
   - Estimated compute time fits within the 8-hour pipeline budget
   
   **Replace with:** Placeholder zeros (20 cols of NaN) marked as `tda_deferred_*`. Allocate the 20 TDA columns to additional wavelet features or signature features in the interim.

2. **Cross-asset transfer entropy at M5 frequency (Block Y partial).** Until:
   - M5-frequency data for DXY, VIX, UST10Y is confirmed available and aligned
   - KSG estimator is validated against known ground truth (e.g., coupled Lorenz systems)
   - Compute budget for 90 directed TE values per bar is benchmarked
   
   **Replace with:** Daily-frequency TE computed offline, forward-filled to M5 bars. This is causal (yesterday's TE applied to today) and computationally trivial.

3. **Regime transition probability matrix at weekly resolution.** Until:
   - HMM leakage is fixed (expanding window + forward-only filtering)
   - State label permutation is solved (Hungarian algorithm matching across refits)
   - Minimum 6 months of data per refit is verified
   
   **Replace with:** Simple binary "regime_changed" flag and "bars_since_last_change" counter, which are trivially causal.

4. **Wavelet packet decomposition (full tree).** The full wavelet packet tree at level 5 produces 32 nodes, each needing multiple summary statistics. This is 100+ features from wavelets alone, exceeding Block X budget. Defer the full packet tree until feature importance from Phase 5 models identifies which nodes are predictive. Start with standard DWT (single branch) at levels 1-5.

---

## 9. WHAT MUST BE ESCALATED TO AGENT 0

1. **HMM LEAKAGE IS A BLOCKING DEFECT.** `data_pipeline/features/regime.py` line 53 fits on ALL data. If any other agent or pipeline has consumed these features for model training, ALL results from those models are invalid. Agent 0 must:
   - Audit every downstream consumer of `regime_tactical`, `regime_prob_*` columns
   - Invalidate any model performance metrics derived from data including these features
   - Issue a stop-ship on Block Z1 until the expanding-window + forward-filter rewrite is complete

2. **The transfer entropy estimator is mathematically incorrect.** `causal_engine/information.py` conflates conditional entropy with residual variance under Gaussian assumption. Any agent relying on TE values from this module (Agent 5 for causal discovery, Agent 7 for feature selection) is receiving garbage estimates. Agent 0 must:
   - Flag all TE-derived results as unreliable
   - Prioritize reimplementation with proper KSG (Kraskov-Stogbauer-Grassberger) estimator
   - Decide: use `npeet` library, or implement from scratch?

3. **Computational budget allocation decision.** TDA, TE, and wavelets collectively require a compute budget decision:
   - TDA (if kept): ~40 hours for full dataset with window=200 (unacceptable)
   - TE rolling (if M5): ~10 hours for 90 pairs (marginal)
   - Wavelets DWT: ~5 minutes (trivial)
   - Path signatures: ~30 minutes (trivial)
   
   Agent 0 must decide: drop TDA entirely, or allocate GPU/multiprocessing resources?

4. **`hmmlearn.predict_proba()` uses backward pass — affects all HMM-derived features.** Even after fixing the expanding-window fit, using `predict_proba()` on the full sequence means each bar's posterior probability uses future observations. This is a SECOND leakage vector independent of the fitting leakage. Agent 0 must mandate: only forward-filtered probabilities (alpha-pass) may be used as features.

5. **FFD mode='same' boundary contamination.** The current fractional differentiation implementation has subtle non-causality at series boundaries. Agent 0 must decide: fix now (breaking change to feature values) or document and defer?

---

## 10. WHAT I WOULD CHANGE IF I HAD AUTHORITY

1. **Replace hmmlearn with online Bayesian HMM.** Instead of batch EM on expanding windows, use a Bayesian online changepoint detector (BOCD) with explicit posterior over run lengths. This is inherently causal, requires no refit schedule, handles label permutation naturally (states are defined by sufficient statistics, not arbitrary indices), and produces uncertainty estimates.

2. **Replace TDA with topological data analysis LITE.** Instead of full Vietoris-Rips persistence:
   - Compute only H0 (connected components) via single-linkage clustering on Takens embedding
   - Use persistence entropy (scalar) rather than full persistence diagrams
   - Window = 100 bars max (O(100^2) = 10K per window, feasible)
   - This gives 3-5 features instead of 20, but they are computable and meaningful

3. **Implement path signatures as the PRIMARY advanced feature block.** Signatures are:
   - Fast (O(n * d^k) per window, k=3 with d=3 gives 39 features in milliseconds)
   - Provably causal (iterated integrals over past)
   - Universal nonlinear features of paths (Stone-Weierstrass theorem for path space)
   - Well-supported by `signatory` (GPU) or `iisignature` (CPU)
   - Reallocate 20 TDA columns and 10 TE columns to signatures: give signatures 50 columns total

4. **Fix the transfer entropy estimator immediately.** Replace the KNeighborsRegressor hack with proper KSG estimator:
   ```python
   # Correct KSG estimator for conditional MI
   from scipy.special import digamma
   from sklearn.neighbors import KDTree
   # Use Kraskov et al. (2004) Algorithm 1
   ```
   This is a 50-line fix that transforms garbage output into valid information-theoretic measures.

5. **Add wavelet scattering transform instead of raw CWT/DWT.** The scattering transform (Mallat 2012):
   - Is provably invariant to time-warping (useful for financial time series)
   - Is Lipschitz-continuous (stable features)
   - Produces fixed-size output regardless of input length
   - Is causal when computed on [0:T]
   - Library: `kymatio` (PyTorch-backed, GPU-accelerable)
   - 30 columns from a 2-layer scattering transform with J=5 scales

6. **Implement PCA with exponential forgetting instead of hard expanding window.** Instead of monthly hard refit:
   - Use incremental PCA with exponential decay (half-life = 1 month)
   - Update components every bar with weight exp(-dt/tau)
   - No discontinuous jumps at refit boundaries
   - Naturally adapts to structural breaks (recent data weighted more)
   - `sklearn.decomposition.IncrementalPCA` supports partial_fit

7. **Mandate that ALL Block Z1 regime features include uncertainty quantification.** Instead of point estimates (regime_tactical = "trending_up"), require:
   - Posterior probability for each state (already exists but leaks via backward pass)
   - Entropy of the state distribution (H = -sum(p_i * log(p_i)))
   - Predictive uncertainty (how confident is the current state assignment)
   - These uncertainty features are often MORE predictive than the point estimates

---

## RAGD_QUERIES

```yaml
queries:
  - id: RAGD_Q6_001
    query: "What is the minimum sample size for stable 4-state Gaussian HMM estimation with full covariance?"
    purpose: "Determine first-valid-date for HMM expanding window"
    expected_answer: "~200-500 observations per state minimum; with 4 states and 3D observations, need ~800-2000 total samples for stable EM convergence"

  - id: RAGD_Q6_002
    query: "Computational complexity of Vietoris-Rips persistence on n points in R^d"
    purpose: "Validate TDA feasibility assessment"
    expected_answer: "O(n^3) memory for 3-skeleton, O(n^{d+1}) for full complex; Ripser uses implicit matrix representation reducing to O(n^2) memory"

  - id: RAGD_Q6_003
    query: "KSG estimator for transfer entropy: algorithm, bias, and convergence rate"
    purpose: "Validate rejection of current TE implementation"
    expected_answer: "Kraskov et al. 2004; bias = O(1/k); convergence = O(n^{-1/(d+2)}); requires n >> 2^d samples for d-dimensional embedding"

  - id: RAGD_Q6_004
    query: "Path signature truncation: how many features for d-dimensional path at level k?"
    purpose: "Validate column budget for signatures"
    expected_answer: "sum_{i=1}^{k} d^i = d(d^k - 1)/(d-1); for d=3,k=3: 3+9+27=39; for d=5,k=3: 5+25+125=155"

  - id: RAGD_Q6_005
    query: "Wavelet scattering transform: output dimensionality for J scales, L layers"
    purpose: "Validate wavelet column budget"
    expected_answer: "Layer 0: 1 coeff; Layer 1: J coeffs; Layer 2: J*(J-1)/2 coeffs; Total for J=5,L=2: 1+5+10=16 time-averaged coefficients per channel"

  - id: RAGD_Q6_006
    query: "hmmlearn predict_proba forward-backward algorithm: does it use future data?"
    purpose: "Confirm second leakage vector in HMM features"
    expected_answer: "Yes. predict_proba uses the forward-backward (Baum-Welch) algorithm which runs a backward pass from T to 0, incorporating all future observations into each time step's posterior"

  - id: RAGD_Q6_007
    query: "Bayesian Online Changepoint Detection (Adams & MacKay 2007): online complexity and implementation"
    purpose: "Evaluate BOCD as replacement for batch changepoint detection"
    expected_answer: "O(T) memory with run-length pruning; O(1) per new observation amortized; implementations: bayesian_changepoint_detection (Python), changepointR"

  - id: RAGD_Q6_008
    query: "Incremental PCA with exponential forgetting: stability guarantees and convergence"
    purpose: "Evaluate alternative to hard monthly PCA refit"
    expected_answer: "Exponential forgetting with rate lambda gives effective window of 1/lambda samples; components converge if lambda < 1/d where d is ambient dimension; Oja's rule with forgetting"
```

---

## EVIDENCE_LEDGER

| ID | Claim | Evidence Location | Status |
|----|-------|------------------|--------|
| E6_001 | PCA fit on train_idx only (no leakage per fold) | `hydra/data/features.py` line 112: `pca.fit(combined[train_idx])` | CONFIRMED CORRECT |
| E6_002 | HMM fit on ALL data (full leakage) | `data_pipeline/features/regime.py` line 53: `model.fit(X_valid)` where X_valid = entire dataset | CONFIRMED LEAKAGE |
| E6_003 | HMM predict_proba uses backward pass | hmmlearn source: `predict_proba()` calls `_do_forward_pass()` then `_do_backward_pass()` | CONFIRMED (via library API) |
| E6_004 | TE estimator assumes Gaussianity | `causal_engine/information.py` line 87: `h = 0.5 * np.log(2 * np.pi * np.e * var)` — this is the Gaussian entropy formula | CONFIRMED INCORRECT |
| E6_005 | FFD uses mode='same' (boundary issue) | `data_pipeline/features/price.py` line 182: `np.convolve(price, weights, mode='same')` | CONFIRMED |
| E6_006 | ESN reservoir is causal (sequential update) | `hydra/data/features.py` lines 101-107: explicit `for t in range(len(prices))` with state depending on previous state | CONFIRMED CORRECT |
| E6_007 | Reservoir size = 3000 per scale | `reservoir/config.py` line 9: `RESERVOIR_SIZE = 3000` | CONFIRMED |
| E6_008 | Multi-scale ESN uses 3 spectral radii | `reservoir/config.py` lines 10-14: fast=0.5, medium=0.9, slow=0.99 | CONFIRMED |
| E6_009 | BPV normalization may be scale-dependent | `data_pipeline/features/microstructure.py` line 137: `.rolling(window).sum() * (pi/2)` with no 1/n division | NEEDS VERIFICATION |
| E6_010 | No wavelet implementation exists in codebase | `find -name "*.py" | xargs grep wavelet` returns only .venv matches | CONFIRMED ABSENT |
| E6_011 | No path signature implementation exists | `find -name "*.py" | xargs grep signature` returns only unrelated matches (type signatures) | CONFIRMED ABSENT |
| E6_012 | No TDA/persistent homology implementation exists | No matches outside .venv | CONFIRMED ABSENT |
| E6_013 | FEATURE_WINDOWS = [5, 10, 20, 50, 100, 252] | `data_pipeline/config.py` line 62 | CONFIRMED |
| E6_014 | Dataset is M5 bars, ~725K rows over 10 years | Implied by spec (288 bars/day * 252 days/year * 10 years ~ 725K) | ASSUMED |
| E6_015 | 32GB RAM constraint | `reservoir/config.py` line 8 comment: "Reduced for 32GB RAM" | CONFIRMED |

---

## SUMMARY OF BLOCKING ISSUES

| Priority | Issue | Impact | Resolution |
|----------|-------|--------|------------|
| P0 | HMM full-sample fit | ALL Z1 features poisoned | Rewrite with expanding window + forward-only filter |
| P0 | HMM predict_proba backward pass | Even after fit fix, probabilities leak | Use only forward pass (alpha values) |
| P1 | TE estimator mathematically wrong | Block Y information flow features invalid | Rewrite with KSG estimator |
| P1 | TDA computationally infeasible | Block X 20 columns cannot be populated | Defer or replace with TDA-lite |
| P2 | FFD mode='same' boundary | First ~50 rows of frac_diff have edge artifacts | Change to mode='full' + truncate |
| P2 | BPV window-scaling bug | Jump detection features non-comparable across windows | Add 1/n normalization |

---

## RECOMMENDED COLUMN ALLOCATION (REVISED)

Given feasibility constraints, the proposed budget should be:

**Block X (120 cols) — Advanced Statistical:**
- PCA on ESN states (expanding monthly): 30 cols
- Wavelet scattering transform (J=5, L=2): 30 cols
- Path signatures (d=3, level=3): 39 cols → round to 40
- Information theory (rolling MI, entropy rate): 20 cols
- TDA-lite (H0 persistence entropy only): 0 cols (deferred) → reallocate to wavelets/signatures

**Block Y (60 cols) — Advanced Network:**
- Transfer entropy (daily, forward-filled): 20 cols (10 pairs x 2 directions)
- Graph centrality metrics (from asset correlation network): 20 cols
- Cross-correlation network topology (rolling): 20 cols

**Block Z1 (90 cols) — Regime & State:**
- BOCD changepoint posterior: 20 cols
- Forward-filtered HMM state probabilities: 20 cols (4 states x 5 statistics)
- Regime duration/transition features: 20 cols
- Regime-conditioned statistics (vol, skew, mean by regime): 30 cols
