# HYDRA-MoE: Jointly-Trained Mixture-of-Experts

**Status:** Research addition to Dominion V2  
**Target:** XAU/USD M5 directional prediction  
**Hypothesis:** Regime-conditional signal exists but is averaged out by global models

---

## Problem Statement

Existing HYDRA stacked models (Alpha, Mega, V2) achieve OOS AUC ~0.523 with sequential gate + brains architecture. Root cause:

1. Gate predicts tradeability (93% AUC) but brains train on ALL bars regardless of regime
2. Direction experts learn averaged cross-regime patterns → weaker than regime-specific patterns
3. Sequential training prevents experts from specializing to regimes the router discovers

**Result:** Recall collapse (>0.99 → always LONG), weak edge after spread costs.

---

## Solution: Joint MoE Training

Train gate (router) and direction experts **end-to-end** with single loss:

```
Loss = BCE(Σ w_k * P_k(long), y_true) + λ * Entropy(w)
      ↑                                    ↑
  weighted expert sum              prevent routing collapse
```

Router learns "which expert handles this bar best" by observing which expert **predicts correctly** for bars assigned to it. Experts learn "given I was selected for this regime, what is direction."

This is proper MoE (Jacobs et al. 1991, Shazeer et al. 2017), not stacking.

---

## Architecture

```
Input: M5 bar features x ∈ R^1115
    ↓
[ROUTER — 2-layer MLP]
    Features: ~60 regime indicators (vol, trend, session, VIX, spread)
    Hidden: [128, 64] + BatchNorm + Dropout(0.2)
    Output: w = softmax(logits / temp) ∈ Δ^K  (K=4)
    ↓
[EXPERTS — 4 LightGBM classifiers]
    Expert 0 (Trend-Up):      momentum, EMA, COT longs, GLD inflows
    Expert 1 (Trend-Down):    DXY strength, real yields, breakdown signals
    Expert 2 (Mean-Revert):   RSI, BB, zscore, autocorr, drawdown
    Expert 3 (Crisis/Vol):    VIX, VPIN, Amihud, spread, vol-of-vol
    Each: LightGBM 2000 rounds, early stop, L1/L2 reg
    ↓
[AGGREGATION]
    P(long) = Σ_k w_k * P_k(long | x)
    ↓
[CALIBRATION — Isotonic Regression]
    Fit on val set → reliable probabilities for thresholding
    ↓
[CONFIDENCE GATE]
    Trade if P(long) > 0.60 or P(long) < 0.40
    No trade otherwise
```

---

## Training Protocol

### Phase 0: Initialization (1-2 min)
1. K-Means clustering on regime features → 4 hard regime labels
2. Train each expert on its assigned regime bars (independent)
3. Initialize router to match cluster soft weights (RBF kernel)

### Phase 1: Alternating Optimization (10-15 min, 5 rounds)
For each round:
- **Step A:** Fix experts → optimize router via gradient descent (500 steps)
- **Step B:** Fix router → retrain experts with routing weights as sample_weight

Temperature annealing: 1.0 → 0.5 (softer early, sharper late)

Collapse detection: if any expert gets >90% mean routing weight → reset + double entropy lambda

### Phase 2: Convergence Fine-Tuning (optional)
If AUC still improving (delta > 0.0005), run 3 more alternating rounds with tighter criteria.

### Final Calibration
- Fit IsotonicRegression on val set predictions
- Evaluate ECE (Expected Calibration Error) — target < 0.03

---

## Usage

### Training

```bash
# Full dataset (782k bars)
python scripts/train_hydra_moe.py

# Debug mode (50k bars, fast iteration)
python scripts/train_hydra_moe.py --debug

# Custom dataset
python scripts/train_hydra_moe.py --data data/custom_dataset.parquet
```

**Output:**
- Models: `output_hydra_moe/models/` (router.pt, expert_*.pkl, calibrator.pkl)
- Predictions: `output_hydra_moe/predictions/` (oos_proba_moe.npy, routing weights)
- Metrics: `output_hydra_moe/metrics/results_moe.json`
- Plots: `output_hydra_moe/plots/` (ROC, calibration, routing distribution, etc.)
- Logs: `output_hydra_moe/logs/training.log`

### Evaluation (Standalone)

```bash
python scripts/evaluate_hydra_moe.py \
  --model-dir output_hydra_moe \
  --data data/hydra_xauusd_m5_master_clean.parquet
```

### Shadow Comparison vs Single-Brain Day

```bash
python scripts/shadow_compare.py \
  --moe-proba output_hydra_moe/predictions/oos_proba_moe.npy \
  --baseline-proba output_hydra_day/oos_proba_day.npy \
  --labels <path-to-oos-labels> \
  --gate 0.60
```

**Analysis:**
- Agreement rate (same direction)
- Disagreement winner (when they differ, who is right)
- Combined signals (AND/OR strategies)
- Per-session performance

---

## Success Criteria

| Metric | Target | Critical? |
|--------|--------|-----------|
| OOS AUC | > 0.5278 (beats Single-Brain) | YES |
| OOS AUC stretch | > 0.5310 | No |
| DeLong p-value | < 0.10 (statistically significant) | No |
| ECE (calibration) | < 0.03 | YES |
| Recall | < 0.90 (not always LONG) | YES |
| Expert routing balance | All experts >5% | YES |

**Production Recommendation Logic:**

- **DEPLOY:** OOS AUC > 0.5310 AND significant AND ECE < 0.03
- **RESEARCH:** Beats baseline but not deploy criteria
- **REJECT:** Does not beat Single-Brain Day

---

## Key Implementation Details

### Router

- **PyTorch MLP** (2 hidden layers, BatchNorm, Dropout)
- **Entropy regularization:** `-mean(sum(w * log(w)))` weighted by λ=0.01
- **Temperature annealing:** Linear 1.0 → 0.5 over training rounds
- **Optimizer:** Adam lr=1e-3, weight_decay=1e-4, cosine annealing
- **Gradient clipping:** max_norm=1.0

### Experts

- **LightGBM binary classifiers** with per-expert hyperparameters
- **Sample weighting:** Each bar gets weight = routing_weight[expert_k]
- **Class imbalance handling:** `scale_pos_weight` if ratio > 1.5
- **Early stopping:** 100-150 rounds patience on val AUC

### Calibration

- **Method:** Isotonic regression (non-parametric, monotonic)
- **Fit set:** Validation set (never OOS)
- **Metrics:** ECE (15 bins), MCE, Brier score
- **Reliability diagram:** Fraction positive vs mean predicted probability

### Feature Groups

- **Router features (~60):** Volatility regime, trend efficiency, session, cross-asset regime, spread/flow indicators
- **Expert preferences:** Substring matching to boost MI scoring (not hard exclusion)
  - Trend-Up: momentum, EMA, COT, GLD
  - Trend-Down: DXY, yields, breakdowns
  - Mean-Revert: RSI, BB, zscore, autocorr
  - Crisis/Vol: VIX, VPIN, Amihud, spread dynamics

---

## Known Failure Modes & Mitigations

| Failure | Detection | Mitigation |
|---------|-----------|------------|
| Expert collapse (>90% to one expert) | Check mean routing weights | Reset router to K-Means init, double λ_entropy |
| Data leakage via scaler | Audit: scaler fit only on train | Hard check in code |
| Recall collapse (always LONG) | Check OOS recall > 0.99 | Add scale_pos_weight to experts |
| Router gradient vanishing | Monitor entropy loss | Temperature annealing schedule |
| NaN propagation | Check for inf/nan in predictions | np.nan_to_num before all model calls |
| Degenerate clusters (<5% bars) | Check Phase 0 regime distribution | Use full dataset if cluster too small |

---

## Test Suite

```bash
pytest tests/test_moe.py -v
```

**Tests:**
- Router output shape and simplex constraint
- Entropy regularization correctness
- Expert weighted training
- MoE predict shapes and bounds
- Calibrator reduces ECE
- Feature group coverage
- Regime assignment balance
- Save/load roundtrip
- Temporal split no leakage
- DeLong test validity

All tests must pass before full training.

---

## Files

```
hydra/moe/
├── __init__.py                # Package exports
├── README.md                  # This file
├── router.py                  # PyTorch MLP router
├── experts.py                 # LightGBM expert wrappers
├── moe_model.py               # Full system class
├── training.py                # 3-phase joint training
├── calibration.py             # Isotonic + conformal
├── evaluation.py              # Comprehensive metrics
├── feature_groups.py          # Feature routing definitions
└── regime_labels.py           # K-Means initialization

scripts/
├── train_hydra_moe.py         # Main training entrypoint
├── evaluate_hydra_moe.py      # Standalone evaluation
└── shadow_compare.py          # Side-by-side vs baseline

tests/
└── test_moe.py                # pytest test suite

output_hydra_moe/
├── models/                    # Saved artifacts
├── predictions/               # OOS proba + routing weights
├── metrics/                   # results_moe.json
├── plots/                     # All evaluation plots
└── logs/                      # training.log
```

---

## Next Steps

1. **After debug run passes:** Run full training on 782k bars
2. **If OOS AUC > 0.5310:** Deploy in shadow mode alongside Single-Brain Day
3. **If OOS AUC 0.5280-0.5310:** Hyperparameter search (router depth, entropy lambda, temperature schedule)
4. **If OOS AUC < 0.5280:** Ablation study:
   - Try GMM instead of K-Means for softer initialization
   - Add more regime features (order flow toxicity, VWAP distance, session overlap indicators)
   - Increase n_experts to 6 (add breakout, fade, weekend regimes)

---

## References

- Jacobs et al. (1991): *Adaptive Mixtures of Local Experts* — original MoE paper
- Shazeer et al. (2017): *Outrageously Large Neural Networks: The Sparsely-Gated Mixture-of-Experts Layer* — modern scaling
- DeLong et al. (1988): *Comparing the Areas under Two or More Correlated ROC Curves* — statistical significance test
- Guo et al. (2017): *On Calibration of Modern Neural Networks* — reliability diagrams, ECE

---

**Contact:** Matin, Dan  
**Collaboration:** tmux + SSH + Tailscale  
**Status:** Shadow mode, read-only MT5 data bridge  
**Last Updated:** 2026-05-27
