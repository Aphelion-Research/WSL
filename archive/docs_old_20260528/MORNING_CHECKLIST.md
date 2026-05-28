# Morning Checklist — May 21, 2026

## Overnight Build Status

**Check if complete:**
```bash
tail -50 /tmp/overnight_build.log
```

**Look for:** "OVERNIGHT BUILD COMPLETE"

---

## Expected Outputs

1. **Price data:** `data/mt5_history/XAUUSD_M5_MASTER.parquet`
   - Target: 850K+ M5 bars (2015 → 2026)
   - Check: `python3 -c "import pandas as pd; df=pd.read_parquet('data/mt5_history/XAUUSD_M5_MASTER.parquet'); print(f'{len(df)} bars, {df.timestamp.min()} to {df.timestamp.max()}')"`

2. **Base features:** `data/hydra_xauusd_m5_master.parquet`
   - Target: 850K rows × ~600 features
   - Check: `python3 -c "import pandas as pd; df=pd.read_parquet('data/hydra_xauusd_m5_master.parquet'); print(f'{len(df)} rows × {len([c for c in df.columns if not any(x in c for x in [\"label\",\"fwd_ret\"])])} features')"`

3. **Expanded features:** `data/hydra_xauusd_m5_3k.parquet`
   - Target: 850K rows × 4,500+ features
   - Check: `python3 -c "import pandas as pd; df=pd.read_parquet('data/hydra_xauusd_m5_3k.parquet'); print(f'{len(df)} rows × {len([c for c in df.columns if not any(x in c for x in [\"label\",\"fwd_ret\"])])} features')"`

4. **Training results:** `runs/overnight_results_20260521.csv`
   - Check: `cat runs/overnight_results_20260521.csv`

---

## Quick Verification

```bash
cd /home/Martin/Dominion

# Check all outputs exist
ls -lh data/mt5_history/XAUUSD_M5_MASTER.parquet
ls -lh data/hydra_xauusd_m5_master.parquet
ls -lh data/hydra_xauusd_m5_3k.parquet
ls -lh runs/overnight_results_*.csv

# Dataset stats
python3 << 'EOF'
import pandas as pd
from pathlib import Path

print("="*60)
print("OVERNIGHT BUILD RESULTS")
print("="*60)

# Price data
if Path('data/mt5_history/XAUUSD_M5_MASTER.parquet').exists():
    df = pd.read_parquet('data/mt5_history/XAUUSD_M5_MASTER.parquet')
    print(f"\nPrice data: {len(df):,} M5 bars")
    print(f"  Range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    print(f"  Years: {(df['timestamp'].max() - df['timestamp'].min()).days / 365.25:.1f}")

# Base features
if Path('data/hydra_xauusd_m5_master.parquet').exists():
    df = pd.read_parquet('data/hydra_xauusd_m5_master.parquet')
    label_cols = [c for c in df.columns if 'label' in c or 'fwd_ret' in c]
    feature_cols = [c for c in df.columns if c not in label_cols]
    real_features = [c for c in feature_cols if not df[c].eq(0).all()]
    print(f"\nBase dataset: {len(df):,} rows × {len(real_features)} features")

# Expanded features
if Path('data/hydra_xauusd_m5_3k.parquet').exists():
    df = pd.read_parquet('data/hydra_xauusd_m5_3k.parquet')
    label_cols = [c for c in df.columns if 'label' in c or 'fwd_ret' in c]
    feature_cols = [c for c in df.columns if c not in label_cols]
    real_features = [c for c in feature_cols if not df[c].eq(0).all()]
    print(f"\nExpanded dataset: {len(df):,} rows × {len(real_features)} features")

# Training results
results_files = sorted(Path('runs').glob('overnight_results_*.csv'))
if results_files:
    results = pd.read_csv(results_files[-1])
    print(f"\nTraining results (3 folds):")
    print(results.to_string(index=False))
    print(f"\nAverage AUC: {results['auc'].mean():.3f}")
    print(f"Average Acc: {results['acc'].mean():.3f}")

print("="*60)
EOF
```

---

## If Build Failed

**Check error:**
```bash
grep -i error /tmp/overnight_build.log | tail -20
```

**Resume from last step:**
- If Dukascopy incomplete: Re-run `python3 scripts/fetch_dukascopy_robust.py`
- If master dataset incomplete: Re-run `python3 scripts/build_master_extended.py`
- If 3K expansion incomplete: Re-run `python3 scripts/expand_features_3k.py`

---

## Next Steps (Morning)

1. **Verify datasets** (use commands above)
2. **Analyze results:** Check AUC scores in training results
3. **Feature importance:** Run feature selection if AUC > 0.55
4. **Hyperparameter tuning:** If edge exists, tune LightGBM/XGB
5. **Extended training:** 5-fold full walk-forward on 3K dataset

---

## Current Status (Pre-Sleep)

- Dukascopy fetch: 40% complete (1188/2970 files)
- Extended data sources: ✓ Complete (87 cross-asset + 30 crypto + 88 FRED)
- Feature expansion test: ✓ Complete (4,489 features from 100K dataset)
- Overnight pipeline: ✓ Running (PID: 375040)

**ETA for Dukascopy:** ~00:30 UTC (1.5 hrs)
**ETA for full build:** ~03:00 UTC (4 hrs total)

Sleep well. Dataset ready by morning.
