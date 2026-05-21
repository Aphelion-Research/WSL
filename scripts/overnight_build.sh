#!/bin/bash
set -e

LOG="/tmp/overnight_build.log"
echo "========================================" | tee -a $LOG
echo "OVERNIGHT BUILD STARTED: $(date)" | tee -a $LOG
echo "========================================" | tee -a $LOG

# Wait for Dukascopy fetch to complete
echo "[$(date +%H:%M:%S)] Waiting for Dukascopy fetch..." | tee -a $LOG
while [ ! -f data/mt5_history/XAUUSD_M5_dukascopy.parquet ]; do
    FILES=$(ls data/dukascopy_daily/*.parquet 2>/dev/null | wc -l)
    echo "[$(date +%H:%M:%S)] Dukascopy progress: $FILES/2970 files" | tee -a $LOG
    sleep 300  # Check every 5 min
done
echo "[$(date +%H:%M:%S)] Dukascopy fetch complete!" | tee -a $LOG

# Merge price sources
echo "[$(date +%H:%M:%S)] Merging price sources..." | tee -a $LOG
python3 << 'PYEOF' | tee -a $LOG
import pandas as pd
from pathlib import Path

mt5 = pd.read_parquet('data/mt5_history/XAUUSD_M5_expanded.parquet')
duka = pd.read_parquet('data/mt5_history/XAUUSD_M5_dukascopy.parquet')

mt5['timestamp'] = pd.to_datetime(mt5['timestamp']).dt.tz_localize(None)
duka['timestamp'] = pd.to_datetime(duka['timestamp']).dt.tz_localize(None)

# Combine
all_data = pd.concat([mt5, duka], ignore_index=True)
all_data = all_data.sort_values('timestamp')
all_data = all_data.drop_duplicates(subset=['timestamp'], keep='first')

print(f"MT5: {len(mt5)} bars")
print(f"Dukascopy: {len(duka)} bars")
print(f"Merged: {len(all_data)} bars")
print(f"Range: {all_data['timestamp'].min()} to {all_data['timestamp'].max()}")

all_data.to_parquet('data/mt5_history/XAUUSD_M5_MASTER.parquet', index=False)
print("Saved: data/mt5_history/XAUUSD_M5_MASTER.parquet")
PYEOF

# Rebuild master dataset with all data sources
echo "[$(date +%H:%M:%S)] Building master dataset with extended data..." | tee -a $LOG
python3 << 'PYEOF' | tee -a $LOG
import pandas as pd
import sys
sys.path.insert(0, '/home/Martin/Dominion')

# Modify build script to use MASTER file + extended data sources
code = open('scripts/build_master_dataset.py').read()

# Inject extended data source paths
code = code.replace(
    "Path('data/cross_asset/cross_asset_daily.parquet')",
    "Path('data/cross_asset_extended/cross_asset_extended_daily.parquet')"
)
code = code.replace(
    "Path('data/macro/macro_daily.parquet')",
    "Path('data/macro_extended/fred_extended_daily.parquet')"
)
code = code.replace(
    "pd.read_parquet('data/mt5_history/XAUUSD_M5.parquet')",
    "pd.read_parquet('data/mt5_history/XAUUSD_M5_MASTER.parquet')"
)

# Write modified version
with open('scripts/build_master_extended.py', 'w') as f:
    f.write(code)

exec(open('scripts/build_master_extended.py').read())
PYEOF

# Expand to 3K+ features
echo "[$(date +%H:%M:%S)] Expanding to 3K+ features..." | tee -a $LOG
timeout 3600 python3 scripts/expand_features_3k.py 2>&1 | tee -a $LOG

# Run walk-forward training
echo "[$(date +%H:%M:%S)] Running walk-forward training..." | tee -a $LOG
timeout 7200 python3 << 'PYEOF' | tee -a $LOG
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import RobustScaler
from sklearn.metrics import accuracy_score, roc_auc_score
import lightgbm as lgb
import xgboost as xgb
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

DATASET = Path("data/hydra_xauusd_m5_3k.parquet")
OUTPUT_DIR = Path("runs")
OUTPUT_DIR.mkdir(exist_ok=True)

print(f"Loading {DATASET}...")
df = pd.read_parquet(DATASET)
print(f"  {len(df)} rows × {len(df.columns)} cols")

label_cols = [c for c in df.columns if 'label' in c or 'fwd_ret' in c]
feature_cols = [c for c in df.columns if c not in label_cols]

LABEL = 'label_12b'
df = df[df[LABEL].notna()].copy()
print(f"  After dropping NaN: {len(df)} rows")

y = df[LABEL].astype(int).values
X = df[feature_cols].values

# 5-fold walk-forward
n = len(X)
fold_size = n // 5
embargo = 60

results = []
for fold in range(1, 4):  # 3 folds (faster overnight)
    test_start = (fold - 1) * fold_size
    test_end = test_start + fold_size if fold < 5 else n
    train_end = test_start - embargo

    if train_end < fold_size:
        continue

    train_idx = np.arange(0, train_end)
    test_idx = np.arange(test_start, test_end)

    X_train, X_test = X[train_idx], X[test_idx]
    y_train, y_test = y[train_idx], y[test_idx]

    print(f"\nFold {fold}: train={len(train_idx)} test={len(test_idx)}")

    scaler = RobustScaler()
    X_train_sc = scaler.fit_transform(X_train)
    X_test_sc = scaler.transform(X_test)

    # LightGBM
    model = lgb.LGBMClassifier(n_estimators=300, max_depth=10, n_jobs=-1, verbosity=-1)
    model.fit(X_train_sc, y_train)
    y_pred_proba = model.predict_proba(X_test_sc)[:, 1]

    auc = roc_auc_score(y_test, y_pred_proba)
    acc = accuracy_score(y_test, (y_pred_proba >= 0.5).astype(int))

    results.append({'fold': fold, 'model': 'LightGBM', 'auc': auc, 'acc': acc})
    print(f"  LightGBM: AUC={auc:.3f} Acc={acc:.3f}")

# Save results
results_df = pd.DataFrame(results)
results_df.to_csv(OUTPUT_DIR / f"overnight_results_{pd.Timestamp.now().strftime('%Y%m%d')}.csv", index=False)

print("\n" + "="*60)
print("OVERNIGHT TRAINING COMPLETE")
print("="*60)
for _, row in results_df.iterrows():
    print(f"Fold {row['fold']}: AUC={row['auc']:.3f} Acc={row['acc']:.3f}")
print(f"Avg AUC: {results_df['auc'].mean():.3f}")
print("="*60)
PYEOF

# Final summary
echo "" | tee -a $LOG
echo "========================================" | tee -a $LOG
echo "OVERNIGHT BUILD COMPLETE: $(date)" | tee -a $LOG
echo "========================================" | tee -a $LOG

echo "" | tee -a $LOG
echo "Files created:" | tee -a $LOG
ls -lh data/mt5_history/XAUUSD_M5_MASTER.parquet 2>/dev/null | tee -a $LOG
ls -lh data/hydra_xauusd_m5_master.parquet 2>/dev/null | tee -a $LOG
ls -lh data/hydra_xauusd_m5_3k.parquet 2>/dev/null | tee -a $LOG
ls -lh runs/overnight_results_*.csv 2>/dev/null | tail -1 | tee -a $LOG

echo "" | tee -a $LOG
python3 << 'PYEOF' | tee -a $LOG
import pandas as pd
from pathlib import Path

print("Dataset stats:")
for f in ['data/hydra_xauusd_m5_master.parquet', 'data/hydra_xauusd_m5_3k.parquet']:
    if Path(f).exists():
        df = pd.read_parquet(f)
        label_cols = [c for c in df.columns if 'label' in c or 'fwd_ret' in c]
        feature_cols = [c for c in df.columns if c not in label_cols]
        print(f"  {f.split('/')[-1]}: {len(df)} rows × {len(feature_cols)} features")

print("\nTraining results:")
results_file = sorted(Path('runs').glob('overnight_results_*.csv'))
if results_file:
    results = pd.read_csv(results_file[-1])
    print(results.to_string(index=False))
    print(f"\nAvg AUC: {results['auc'].mean():.3f}")
PYEOF

echo "" | tee -a $LOG
echo "Log saved to: $LOG" | tee -a $LOG
