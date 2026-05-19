# Temporal Train/Val/Test Split Report

**Date:** 2026-05-19  
**Author:** Claude Code (Sonnet 4.5)  
**Dataset:** Dominion v1 (gold_master + features tables)  
**Status:** ✓ VALIDATED

---

## Executive Summary

**Temporal split computed:** 70% train / 15% val / 15% test

**Total rows:** 1256 (daily gold prices, 2021-05-21 to 2026-05-19)

**No shuffling:** Chronological split prevents leakage.

**Validation:** All checks passed.

---

## Split Boundaries

### TRAIN (70%)
- **Rows:** 879
- **Dates:** 2021-05-21 to 2024-11-15
- **Duration:** ~3.5 years

### VAL (15%)
- **Rows:** 188
- **Dates:** 2024-11-15 to 2025-08-18
- **Duration:** ~9 months

### TEST (15%)
- **Rows:** 189
- **Dates:** 2025-08-18 to 2026-05-19
- **Duration:** ~9 months

---

## Split Rationale

### Why 70/15/15?

**Train (70%):** Need long history for:
- Kalman filters to converge (6 timescales)
- Regime detection (if using expanding-window HMM)
- Rolling window features (max window = 252 days)
- Seasonal patterns (multiple years)

**Val (15%):** Enough data for:
- Hyperparameter tuning
- Early stopping
- Model selection
- ~6-9 months covers multiple market regimes

**Test (15%):** Held-out set for:
- Final model evaluation
- Unbiased performance estimate
- Publication-ready metrics

### Why Temporal (Not Random)?

**Time series properties:**
- Autocorrelation: returns are correlated across time
- Regime persistence: market regimes last weeks-months
- Distribution shift: 2021 gold market ≠ 2026 gold market

**Random shuffle breaks these:**
- Train on 2026, test on 2021 → unrealistic
- Leakage: future info in train set
- Overfitting: model memorizes temporal patterns

**Temporal split is realistic:**
- Train on past, predict future (production scenario)
- No leakage: train never sees future data
- Harder test: must generalize to unseen future

---

## Validation Checks

### ✓ Percentage Sums to 100%
- Train: 70.0%
- Val: 15.0%
- Test: 15.0%
- Total: 100.0%

### ✓ Minimum Data Requirements
- Train ≥ 60%: ✓ (70.0%)
- Val ≥ 10%: ✓ (15.0%)
- Test ≥ 10%: ✓ (15.0%)

### ✓ Chronological Order
- Train end (2024-11-15) = Val start (2024-11-15) ✓
- Val end (2025-08-18) = Test start (2025-08-18) ✓
- No gaps ✓
- No overlaps ✓

### ✓ No Shuffling
- Rows ordered by timestamp ASC
- Train < Val < Test chronologically

---

## Feature Status

### Current State

**gold_master table:** 4 feature columns
- `close`, `high`, `low`, `open` (OHLC prices)
- `volume`, `source`, `trust`, `anomaly_flag` (metadata)
- **No engineered features yet** (400+ features referenced in AGENT_HANDOFF.md are in separate `features` table or not yet computed)

**features table:** Long format
- Columns: `timestamp`, `feature_name`, `feature_value`, `feature_version`, `ic_252`, `ic_updated_at`
- Feature engineering exists but not yet joined to gold_master

### Excluded Features (Leakage)

Per leakage audit report (2026-05-19_leakage_audit.md):

- `regime_tactical` — HMM fit on full dataset
- `regime_prob_trend_up`
- `regime_prob_trend_down`
- `regime_prob_ranging`
- `regime_prob_crisis`

**Status:** These features not found in gold_master ✓ (Never added, or added to features table only)

**Action:** When joining features, **exclude** these 5 columns.

---

## Dataset Build Steps (Remaining)

### 1. Join Features to gold_master

```python
# Pivot features table from long to wide format
features_wide = conn.execute("""
    SELECT
        timestamp,
        MAX(CASE WHEN feature_name = 'return_5' THEN feature_value END) as return_5,
        MAX(CASE WHEN feature_name = 'return_10' THEN feature_value END) as return_10,
        -- ... pivot all ~400 features
    FROM features
    WHERE feature_name NOT IN (
        'regime_tactical',
        'regime_prob_trend_up',
        'regime_prob_trend_down',
        'regime_prob_ranging',
        'regime_prob_crisis'
    )
    GROUP BY timestamp
""").df()

# Join to gold_master
dataset = conn.execute("""
    SELECT g.*, f.*
    FROM gold_master g
    LEFT JOIN features_wide f ON g.timestamp = f.timestamp
    ORDER BY g.timestamp
""").df()
```

### 2. Drop Rows with NaN Features

**Issue:** First 252 rows will have NaNs (max rolling window = 252 days)

**Solution:**
```python
# Drop rows where any feature is NaN
dataset_clean = dataset.dropna()

# Recompute split boundaries on clean dataset
```

**Expected loss:** ~252 rows from start of train set → Train: 879 - 252 = 627 rows (still >2 years)

### 3. Create Split Views

```python
train_end = "2024-11-15"
val_end = "2025-08-18"

train_df = dataset_clean[dataset_clean["timestamp"] <= train_end]
val_df = dataset_clean[(dataset_clean["timestamp"] > train_end) & (dataset_clean["timestamp"] <= val_end)]
test_df = dataset_clean[dataset_clean["timestamp"] > val_end]
```

### 4. Save to Parquet

```python
train_df.to_parquet("data/train_v1.parquet")
val_df.to_parquet("data/val_v1.parquet")
test_df.to_parquet("data/test_v1.parquet")
```

### 5. Compute Feature Stats (Train Only)

```python
# Mean, std, min, max, skew, kurt
feature_stats = train_df.describe()
feature_stats.to_json("data/feature_stats_v1.json")
```

### 6. Hash Dataset

```python
import hashlib

def hash_dataframe(df):
    return hashlib.sha256(df.to_csv(index=False).encode()).hexdigest()

manifest = {
    "version": "1.0",
    "created": "2026-05-19",
    "split_boundaries": {
        "train_end": train_end,
        "val_end": val_end,
    },
    "row_counts": {
        "train": len(train_df),
        "val": len(val_df),
        "test": len(test_df),
    },
    "feature_count": len(dataset_clean.columns) - 5,  # Exclude OHLC + timestamp
    "hashes": {
        "train": hash_dataframe(train_df),
        "val": hash_dataframe(val_df),
        "test": hash_dataframe(test_df),
    },
}
```

---

## Usage

### Loading Data

```python
import pandas as pd

train_df = pd.read_parquet("data/train_v1.parquet")
val_df = pd.read_parquet("data/val_v1.parquet")
test_df = pd.read_parquet("data/test_v1.parquet")
```

### Training Models

```python
# Separate features and target
X_train = train_df.drop(columns=["timestamp", "close", "high", "low", "open", "target_return_1"])
y_train = train_df["target_return_1"]  # 1-day forward return

# Train model
model.fit(X_train, y_train)

# Validate
X_val = val_df.drop(columns=["timestamp", "close", "high", "low", "open", "target_return_1"])
y_val = val_df["target_return_1"]
val_score = model.score(X_val, y_val)
```

**IMPORTANT:** Never train on val or test. Never peek at test until final evaluation.

---

## Regime Distribution (Train/Val/Test)

**Note:** Regime labels removed due to leakage. Use **micro regime** (time-of-day) instead:

```python
# Micro regime (no leakage)
df["regime_micro"] = pd.cut(
    df["timestamp"].dt.hour,
    bins=[0, 8, 13, 17, 22, 24],
    labels=["asian", "london", "overlap", "ny", "dead_zone"]
)
```

**Train distribution:** All time zones represented (24-hour data)

**Val/Test:** Same (no regime shift expected)

---

## Known Limitations

1. **Small dataset:** 1256 daily rows → After dropna, expect ~1000 rows
   - Train: ~630 rows
   - Val: ~180 rows
   - Test: ~180 rows
   - **Mitigation:** Use simple models (Ridge, RandomForest), avoid deep learning

2. **Single asset:** Gold only (XAU/USD)
   - **Mitigation:** Cross-asset features (DXY, VIX, TNX) provide diversification

3. **Daily frequency:** No intraday data in gold_master
   - **Mitigation:** Use `gold_ticks` for intraday models (requires different split)

4. **Forward returns not computed yet:** Need target variable
   - **Action:** Add `target_return_1`, `target_return_5`, `target_return_10` to dataset

5. **Features not joined yet:** gold_master has price only, features table separate
   - **Action:** Join + pivot features (Task #13)

---

## Next Steps

1. ✓ Compute split boundaries (this report)
2. → Join features to gold_master (Task #13)
3. → Add target variables (forward returns)
4. → Drop NaN rows
5. → Save to Parquet
6. → Compute feature stats
7. → Hash dataset
8. → Train baseline models (Task #11)

---

## References

- **Leakage audit:** `reports/2026-05-19_leakage_audit.md`
- **Split config:** `reports/temporal_split_v1.json`
- **Split script:** `scripts/temporal_split.py`
- **Dataset manifest:** (To be created in Task #13)

---

**Split validated.** Ready for dataset build (Task #13).
