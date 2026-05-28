#!/usr/bin/env python3
"""Backtest best model overnight with realistic costs."""
import pandas as pd
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

DATASET = Path("data/hydra_xauusd_m5_selected.parquet")
OUTPUT = Path("runs/backtest_results.csv")

LABEL = 'label_12b'
SPREAD_COST = 0.0003  # 30 pips
SLIPPAGE = 0.0001  # 10 pips
POSITION_SIZE = 1.0


def backtest():
    """Full backtest with costs."""
    import lightgbm as lgb
    from sklearn.preprocessing import RobustScaler

    print("Loading dataset...")
    df = pd.read_parquet(DATASET)

    label_cols = [c for c in df.columns if 'label' in c or 'fwd_ret' in c]
    feature_cols = [c for c in df.columns if c not in label_cols]

    df = df[df[LABEL].notna()].copy()
    y = df[LABEL].astype(int).values
    X = df[feature_cols].values

    print(f"Dataset: {len(X)} rows × {len(feature_cols)} features")

    # Walk-forward backtest
    n = len(X)
    fold_size = n // 5
    embargo = 60

    all_trades = []

    for fold in range(1, 6):
        test_start = (fold - 1) * fold_size
        test_end = test_start + fold_size if fold < 5 else n
        train_end = test_start - embargo

        if train_end < fold_size:
            continue

        train_idx = np.arange(0, train_end)
        test_idx = np.arange(test_start, test_end)

        X_train, X_test = X[train_idx], X[test_idx]
        y_train, y_test = y[train_idx], y[test_idx]

        scaler = RobustScaler()
        X_train_sc = scaler.fit_transform(X_train)
        X_test_sc = scaler.transform(X_test)

        # Train model
        model = lgb.LGBMClassifier(
            n_estimators=500,
            learning_rate=0.03,
            max_depth=12,
            n_jobs=-1,
            verbosity=-1,
            random_state=42
        )
        model.fit(X_train_sc, y_train)
        y_pred_proba = model.predict_proba(X_test_sc)[:, 1]

        # Generate signals
        threshold = 0.55  # More conservative
        signals = (y_pred_proba >= threshold).astype(int) * 2 - 1  # -1 or +1
        signals[y_pred_proba < threshold] = 0  # No trade zone

        # Simulate trades
        for i in range(len(test_idx)):
            if signals[i] == 0:
                continue

            # Entry
            entry_cost = SPREAD_COST + SLIPPAGE

            # Exit after label_12b bars (12 bars = 1 hour)
            if y_test[i] == 1:  # TP hit
                pnl = 0.015 - entry_cost  # 1.5% gain - costs
            else:  # SL hit
                pnl = -0.015 - entry_cost  # 1.5% loss - costs

            all_trades.append({
                'fold': fold,
                'signal': signals[i],
                'outcome': y_test[i],
                'pnl': pnl * POSITION_SIZE,
                'predicted_prob': y_pred_proba[i]
            })

        print(f"Fold {fold}: {len([t for t in all_trades if t['fold'] == fold])} trades")

    # Analysis
    trades_df = pd.DataFrame(all_trades)
    trades_df.to_csv(OUTPUT, index=False)

    total_pnl = trades_df['pnl'].sum()
    win_rate = (trades_df['outcome'] == 1).mean()
    avg_win = trades_df[trades_df['pnl'] > 0]['pnl'].mean()
    avg_loss = trades_df[trades_df['pnl'] < 0]['pnl'].mean()
    sharpe = trades_df['pnl'].mean() / (trades_df['pnl'].std() + 1e-10) * np.sqrt(252 * 288 / 12)

    print(f"\n{'='*60}")
    print("BACKTEST RESULTS")
    print(f"{'='*60}")
    print(f"Total trades:    {len(trades_df)}")
    print(f"Win rate:        {win_rate:.2%}")
    print(f"Total PnL:       {total_pnl:.4f}")
    print(f"Avg win:         {avg_win:.4f}")
    print(f"Avg loss:        {avg_loss:.4f}")
    print(f"Sharpe:          {sharpe:.3f}")
    print(f"Profit factor:   {abs(trades_df[trades_df['pnl'] > 0]['pnl'].sum() / trades_df[trades_df['pnl'] < 0]['pnl'].sum()):.2f}")
    print(f"\nSaved: {OUTPUT}")


if __name__ == "__main__":
    backtest()
