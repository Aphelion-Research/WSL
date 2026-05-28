# Dataset Architecture: Immutable Splits First

**Status:** Approved  
**Date:** 2026-05-27  
**Authors:** Martin, Claude  
**Problem:** Data leakage (feature, label, and temporal split contamination) due to lack of structural isolation between data stages.

---

## 1. Overview

A five-layer dataset pipeline where temporal splits happen BEFORE feature computation, making data leakage structurally impossible rather than merely validated after the fact.

**Core invariant:** Feature functions receive one fold's data only. Cross-fold access is physically impossible.

---

## 2. Data Layers

| Layer | Name | Contents | Format | Mutability |
|-------|------|----------|--------|------------|
| L0 | Raw | MT5 OHLCV per timeframe | Parquet | Append-only |
| L1 | Temporal Folds | Raw data split into isolated time windows | Parquet per fold | Immutable once created |
| L2 | Features | Computed per-fold independently | Parquet per fold | Immutable (recompute = new version) |
| L3 | Labels | Forward-looking targets per-fold | Parquet per fold | Immutable |
| L4 | Dataset Artifact | Train/val/test matrices + metadata + hash | Directory bundle | Content-addressed, immutable |

**Flow:** L0 → L1 → L2 → L3 → L4

Each layer is produced from the previous layer ONLY. No skipping layers, no cross-layer shortcuts.

---

## 3. Temporal Fold Design

### 3.1 Fold Structure

```
|← warmup buffer (computation only, excluded from training) →|← usable data →|← embargo →|

Fold 1:  [=====warmup=====][==========TRAIN==========][==embargo==]
Fold 2:                     [=====warmup=====][==========VAL==========][==embargo==]
Fold 3:                                       [=====warmup=====][==========TEST==========]
```

### 3.2 Warmup Buffer

Each fold receives N extra bars prepended from the immediately preceding time period. For Fold 1, warmup comes from the earliest available raw data (before the first usable train window). These bars:
- ARE available for feature computation (rolling windows, lookback)
- ARE NOT included in training rows, labels, or evaluation
- Size determined by: `warmup_bars = max(feature.lookback_bars for all features)`

### 3.3 Embargo Gap

Gap between folds where no data is used (neither train nor test):
- `embargo_bars >= max(label_horizon_bars, max_hold_period_bars)`
- Currently `embargo_bars: 10` in config is TOO SMALL for `horizon_bars: 20`
- New default: `embargo_bars = 2 * label_horizon_bars` (40 bars for 20-bar horizon)

### 3.4 Walk-Forward Expansion

For k-fold walk-forward:
- Fold k's training set = union of all prior folds' usable data (not warmup)
- Validation = newest usable slice before test
- Test = most recent time slice

This gives expanding training windows while maintaining strict temporal ordering.

### 3.5 Fold Configuration

```python
@dataclass(frozen=True)
class FoldConfig:
    n_folds: int = 6
    warmup_bars: int = 500
    embargo_bars: int = 40
    label_horizon_bars: int = 20
    base_timeframe: str = "M5"
    higher_timeframes: list[str] = ("H1", "H4", "D1")
```

---

## 4. Feature Computation (Leakage-Proof)

### 4.1 Isolation Contract

Feature functions receive a `FoldSlice` containing ONLY that fold's data (warmup + usable range). They cannot:
- Access global dataset statistics (mean, std, min, max of full series)
- Reference data from other folds
- Import or read data files directly

```python
class FeatureBuilder:
    def compute(self, fold_data: FoldSlice) -> pl.DataFrame:
        """
        fold_data.raw: OHLCV bars (warmup + usable)
        fold_data.warmup_end_idx: index where warmup ends
        fold_data.higher_tf: dict of asof-joined higher TF data (within fold time range)
        
        Returns: feature columns for usable rows only (warmup excluded from output)
        """
```

### 4.2 Multi-Timeframe Handling

Higher timeframe data (H1, H4, D1) is included in each fold via point-in-time safe asof join:
- Strategy: `backward` only (each M5 bar sees most recent H1/H4/D1 bar with time <= current)
- Time range: clipped to fold's time window (warmup start → usable end)
- No future H1 bar can appear at an earlier M5 timestamp

### 4.3 Normalization (Most Common Leak Source)

**Forbidden:**
- Z-score using full dataset mean/std
- Min-max using global min/max
- Any normalization referencing data outside the fold

**Allowed:**
- Rolling z-score using expanding/rolling window within the fold
- Quantile normalization using only past data (within fold)
- Rank transform within fold

### 4.4 Feature Registry

Each feature declares metadata:

```python
@dataclass
class FeatureSpec:
    name: str
    lookback_bars: int          # determines warmup contribution
    timeframes_needed: list[str]  # which higher TFs it asof-joins
    is_stateful: bool           # carries state across bars (rolling = True)
    compute_fn: Callable        # the actual computation
    version: str                # semantic version for tracking changes
```

The maximum `lookback_bars` across all features determines fold warmup size.

---

## 5. Label Construction

### 5.1 Forward-Looking Constraint

Labels are prediction targets — they ARE allowed to look forward. But:
- Computed LAST (after features, on fold's usable data only)
- Label at bar `t` can look forward to `t + horizon`
- If `t + horizon` exceeds fold boundary → label is NaN → row excluded from training

### 5.2 Boundary Trimming

Last `label_horizon_bars` rows of each fold have incomplete labels and are dropped:
- Combined with embargo gap → no signal leakage between folds
- This is an acceptable data loss (small fraction of total)

### 5.3 Label Types

Current: ATR-based risk-reward (stop/target multiples of ATR)

```python
@dataclass
class LabelConfig:
    type: str = "atr_rr"
    atr_window: int = 14
    stop_mult: float = 1.0
    target_mult: float = 2.0
    horizon_bars: int = 20
```

---

## 6. Versioning & Lineage

### 6.1 Content-Addressed Artifacts

Each L4 dataset artifact lives in a content-addressed directory:

```
datasets/
  v_a3f2c1/
    manifest.json
    train.parquet
    val.parquet
    test.parquet
    feature_stats.json
```

Directory name = first 6 chars of SHA-256(manifest.json content).

### 6.2 Manifest Schema

```json
{
  "version_hash": "a3f2c1d4e5f6...",
  "created_at": "2026-05-27T14:30:00Z",
  "raw_data": {
    "hash": "sha256 of L0 parquets used",
    "date_range": {"start": "2023-01-01", "end": "2026-05-20"},
    "base_timeframe": "M5",
    "bar_count": 500000
  },
  "fold_config": {
    "n_folds": 6,
    "warmup_bars": 500,
    "embargo_bars": 40,
    "label_horizon_bars": 20
  },
  "feature_config": {
    "hash": "sha256 of feature registry + params",
    "count": 3000,
    "registry_git_commit": "abc123"
  },
  "label_config": {
    "type": "atr_rr",
    "horizon": 20,
    "target_mult": 2.0,
    "stop_mult": 1.0
  },
  "output_stats": {
    "train_rows": 150000,
    "val_rows": 30000,
    "test_rows": 30000,
    "feature_count": 3000,
    "nan_rate": 0.02
  },
  "leakage_audit": {
    "passed": true,
    "checks_run": 12,
    "timestamp": "2026-05-27T14:29:55Z"
  },
  "higher_timeframes": {
    "H1": {"hash": "sha256 of H1 parquet", "bars": 25000},
    "H4": {"hash": "sha256 of H4 parquet", "bars": 6250},
    "D1": {"hash": "sha256 of D1 parquet", "bars": 1000}
  }
}
```

### 6.3 Reproducibility Contract

Given:
- Same raw data (verified by hash)
- Same feature registry (verified by git commit + hash)
- Same fold/label config

The pipeline MUST produce byte-identical output. Non-deterministic operations (random seeds, threading order) are pinned.

### 6.4 Registry

`datasets/registry.json` maps models to dataset versions:

```json
{
  "hydra_moe_v1": "v_a3f2c1",
  "him_v2_multiscale": "v_b7e4d2",
  "current_dev": "v_c9f8a3"
}
```

---

## 7. Leakage Validation (Defense in Depth)

Even though architecture makes leakage structurally impossible, these checks run automatically when producing L4. Any failure blocks artifact creation.

### 7.1 Checks

| # | Check | What It Catches |
|---|-------|-----------------|
| 1 | Temporal monotonicity | No test timestamp < max train timestamp |
| 2 | Feature independence | Recompute features with last 100 warmup bars removed; usable-region features must not change |
| 3 | Embargo sufficiency | `embargo_bars >= max(label_horizon, max_hold_bars)` |
| 4 | Column name audit | No forbidden patterns in feature columns |
| 5 | Distribution similarity | Features suspiciously identical between train/test → likely global computation |
| 6 | Hash chain integrity | Manifest hashes match actual file content |
| 7 | Warmup exclusion | No training row index falls within warmup range |
| 8 | Label boundary | No label at time t references data beyond fold boundary |
| 9 | NaN pattern | Interior NaNs in features suggest lookahead gap |
| 10 | Fold isolation | Features recomputed on isolated fold match features in combined output |
| 11 | Normalization audit | No feature has mean≈0, std≈1 across entire dataset (global z-score) |
| 12 | Cross-fold correlation | Warmup-region features correlated with prior fold's test → warmup bleeding |

### 7.2 Audit Report

Validation produces a JSON report stored alongside the artifact. Models cannot be trained on datasets that fail audit.

---

## 8. Directory Structure

```
Dominion/
  datasets/                        # L4: versioned artifacts
    registry.json
    v_a3f2c1/
      manifest.json
      train.parquet
      val.parquet
      test.parquet
      feature_stats.json
  data/
    mt5_history/                    # L0: raw data (unchanged)
      XAUUSD_M5_MASTER.parquet
      XAUUSD_H1.parquet
      XAUUSD_H4.parquet
      XAUUSD_D1.parquet
  dominion/
    dataset/
      pipeline.py                  # Orchestrator: L0 → L4
      splitter.py                  # L0 → L1: temporal fold creation
      feature_builder.py           # L1 → L2: per-fold feature computation
      label_builder.py             # L2 → L3: per-fold label computation  
      versioner.py                 # L3 → L4: hashing, manifest, artifact bundling
      validator.py                 # Leakage audit suite (12 checks)
      contracts.py                 # Data contracts (existing, expanded)
      registry.py                  # Feature registry with metadata
      config.py                    # FoldConfig, LabelConfig, etc.
```

---

## 9. Pipeline Orchestration

### 9.1 CLI Interface

```bash
# Build new dataset version
dominion dataset build --config config/dataset/default.yaml

# Validate existing dataset
dominion dataset validate datasets/v_a3f2c1/

# Compare two versions
dominion dataset diff v_a3f2c1 v_b7e4d2

# List all versions
dominion dataset list

# Pin model to dataset version
dominion dataset pin hydra_moe_v1 v_a3f2c1
```

### 9.2 Config File

```yaml
# config/dataset/default.yaml
raw_data:
  base_timeframe: M5
  source: data/mt5_history/XAUUSD_M5_MASTER.parquet
  higher_timeframes:
    H1: data/mt5_history/XAUUSD_H1.parquet
    H4: data/mt5_history/XAUUSD_H4.parquet
    D1: data/mt5_history/XAUUSD_D1.parquet
  date_range:
    start: "2023-01-01"
    end: "2026-05-20"

folds:
  n_folds: 6
  warmup_bars: 500
  embargo_bars: 40

features:
  registry: dominion.dataset.registry.HYDRA_REGISTRY
  normalization: rolling_zscore
  
labels:
  type: atr_rr
  horizon_bars: 20
  atr_window: 14
  stop_mult: 1.0
  target_mult: 2.0

validation:
  enabled: true
  fail_on_warning: false
  checks: all
```

---

## 10. Migration Path

### From Current State

1. Keep existing `data/mt5_history/` as L0 (no change)
2. New `dominion/dataset/` modules implement L1→L4
3. Existing `hydra/data/cv.py` split logic → replaced by `splitter.py`
4. Existing `dominion/matrix/builder.py` → refactored into `feature_builder.py` (per-fold interface)
5. Existing `utils/leakage_validation.py` → consolidated into `validator.py`
6. Existing `dominion/dataset/contracts.py` → expanded with new contracts
7. Old scripts (`retrain_him_v2_multiscale.py`, etc.) → updated to load from `datasets/v_xxx/`

### Backwards Compatibility

During migration, both old and new paths coexist. New models use `datasets/` artifacts. Old models continue working until migrated.

---

## 11. What This Architecture Prevents

| Leakage Type | How It's Prevented |
|-------------|-------------------|
| Feature sees future data | Features computed per-fold; future data not in fold's input |
| Global normalization | Normalizer receives fold data only; global stats unavailable |
| Train/test overlap | Embargo gap + temporal fold isolation |
| Label bleeding into features | Labels computed AFTER features, on separate pass |
| Shuffled data | Temporal splitter enforces monotonic timestamps |
| Inadequate embargo | Config enforces `embargo >= 2 * label_horizon` |
| Irreproducible results | Content-addressed artifacts with full lineage |
| Silent drift | Feature stats stored; drift detected on re-runs |

---

## 12. Non-Goals (Explicit Exclusions)

- Live/streaming data pipeline (this is batch-only for research)
- Auto-retraining triggers (manual `dataset build` for now)
- Multi-asset support (XAU/USD only; generalizable later)
- Feature store with sharing across projects (single project)
- Cloud storage (local-first; Modal GPU compute pulls from local artifacts)
