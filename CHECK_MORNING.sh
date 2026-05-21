#!/bin/bash
echo "================================================================"
echo "MORNING STATUS CHECK - $(date)"
echo "================================================================"

# Show monitor log
if [ -f /tmp/overnight_monitor.log ]; then
    echo -e "\n=== OVERNIGHT PROGRESS ==="
    tail -20 /tmp/overnight_monitor.log
fi

# Show main log
if [ -f /tmp/overnight_build.log ]; then
    echo -e "\n=== BUILD LOG (last 30 lines) ==="
    tail -30 /tmp/overnight_build.log
fi

# Check processes
echo -e "\n=== RUNNING PROCESSES ==="
ps aux | grep -E 'fetch_dukascopy|overnight_build|monitor_overnight' | grep -v grep || echo "All processes finished"

# Check outputs
echo -e "\n=== OUTPUT FILES ==="
ls -lh data/mt5_history/XAUUSD_M5_MASTER.parquet 2>/dev/null || echo "MASTER price file: NOT YET"
ls -lh data/hydra_xauusd_m5_master.parquet 2>/dev/null || echo "Master dataset: NOT YET"
ls -lh data/hydra_xauusd_m5_3k.parquet 2>/dev/null || echo "3K dataset: NOT YET"
ls -lh runs/overnight_results_*.csv 2>/dev/null | tail -1 || echo "Training results: NOT YET"

# Quick stats if complete
if [ -f data/hydra_xauusd_m5_3k.parquet ]; then
    echo -e "\n=== FINAL DATASET STATS ==="
    python3 << 'PYEOF'
import pandas as pd
df = pd.read_parquet('data/hydra_xauusd_m5_3k.parquet')
label_cols = [c for c in df.columns if 'label' in c or 'fwd_ret' in c]
feature_cols = [c for c in df.columns if c not in label_cols]
real = [c for c in feature_cols if not df[c].eq(0).all()]
print(f"Rows: {len(df):,}")
print(f"Features: {len(real):,}")
print(f"Labels: {len(label_cols)}")
print(f"Date range: {df.index.min()} to {df.index.max()}")
PYEOF
fi

# Training results if exist
if ls runs/overnight_results_*.csv >/dev/null 2>&1; then
    echo -e "\n=== TRAINING RESULTS ==="
    python3 -c "import pandas as pd; df=pd.read_csv(sorted(__import__('pathlib').Path('runs').glob('overnight_results_*.csv'))[-1]); print(df.to_string(index=False)); print(f'\nAvg AUC: {df.auc.mean():.3f}')"
fi

echo -e "\n================================================================"
