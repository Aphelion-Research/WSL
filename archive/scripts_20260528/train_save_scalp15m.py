"""
Production 15-min scalp model: train, save, and multi-period OOS validation.
Detrended 4h label, confidence gating, no lookahead.
"""
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.metrics import roc_auc_score, accuracy_score
from sklearn.ensemble import RandomForestClassifier
import xgboost as xgb
from scipy import stats
import json
import pickle
import warnings
warnings.filterwarnings('ignore')

DATA_DIR = Path("data")
OUTPUT_DIR = Path("output_scalp15m")
OUTPUT_DIR.mkdir(exist_ok=True)

FEATURE_COLS = None  # set during build


def load_m15():
    m5 = pd.read_parquet(DATA_DIR / "mt5_history/XAUUSD_M5_dukascopy.parquet")
    m5['time'] = pd.to_datetime(m5['time'])
    m5 = m5.set_index('time').sort_index()
    m15 = m5.resample('15min').agg({
        'open': 'first', 'high': 'max', 'low': 'min',
        'close': 'last', 'tick_volume': 'sum', 'spread': 'mean',
    }).dropna(subset=['close'])
    m15 = m15[m15['tick_volume'] > 0]
    return m15


def build_features(m15):
    """Build features with NO lookahead."""
    close = m15['close']
    high = m15['high']
    low = m15['low']
    volume = m15['tick_volume']

    f = pd.DataFrame(index=m15.index)

    # Returns
    f['ret_1bar'] = close.pct_change(1)
    f['ret_4bar'] = close.pct_change(4)
    f['ret_16bar'] = close.pct_change(16)
    f['ret_96bar'] = close.pct_change(96)

    # Range position (24h)
    rolling_high_96 = close.rolling(96).max()
    rolling_low_96 = close.rolling(96).min()
    range_96 = (rolling_high_96 - rolling_low_96).replace(0, np.nan)
    f['range_pos_24h'] = (close - rolling_low_96) / range_96

    # VWAP deviation
    tp = (high + low + close) / 3
    vol = volume.replace(0, 1)
    f['vwap_dev_4h'] = (close - (tp * vol).rolling(16).sum() / vol.rolling(16).sum()) / close
    f['vwap_dev_24h'] = (close - (tp * vol).rolling(96).sum() / vol.rolling(96).sum()) / close

    # ATR
    tr_15 = pd.concat([high - low, (high - close.shift(1)).abs(), (low - close.shift(1)).abs()], axis=1).max(axis=1)
    atr_12 = tr_15.rolling(12).mean()
    atr_48 = tr_15.rolling(48).mean()
    atr_96 = tr_15.rolling(96).mean()
    f['atr_3h_pct'] = atr_12 / close
    f['atr_24h_pct'] = atr_96 / close
    f['vol_ratio'] = atr_12 / atr_48.replace(0, np.nan)

    # RSI
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss_val = (-delta.where(delta < 0, 0)).rolling(14).mean()
    f['rsi_14'] = 100 - 100 / (1 + gain / loss_val.replace(0, np.nan))

    # Bollinger
    bb_mid = close.rolling(20).mean()
    bb_std = close.rolling(20).std().replace(0, np.nan)
    f['bb_pos'] = (close - bb_mid) / (2 * bb_std)

    # Volume
    f['vol_zscore'] = (volume - volume.rolling(96).mean()) / volume.rolling(96).std().replace(0, np.nan)

    # Session
    hour = m15.index.hour + m15.index.minute / 60
    f['cos_hour'] = np.cos(2 * np.pi * hour / 24)
    f['sin_hour'] = np.sin(2 * np.pi * hour / 24)
    f['cos_dow'] = np.cos(2 * np.pi * m15.index.dayofweek / 5)

    # Pullback
    f['pullback_from_high'] = (rolling_high_96 - close) / atr_96.replace(0, np.nan)
    f['pullback_from_low'] = (close - rolling_low_96) / atr_96.replace(0, np.nan)

    # Spread
    f['spread_zscore'] = (m15['spread'] - m15['spread'].rolling(96).mean()) / m15['spread'].rolling(96).std().replace(0, np.nan)

    # Consecutive bars
    f['consec_up'] = close.diff().gt(0).rolling(8).sum()
    f['consec_down'] = close.diff().lt(0).rolling(8).sum()

    # Daily overlay (SHIFTED 2 DAYS — no lookahead)
    m5_daily = close.resample('1D').last().dropna()
    d_sma50 = ((m5_daily - m5_daily.rolling(50).mean()) / m5_daily.rolling(50).mean()).shift(2)
    d_sma100 = ((m5_daily - m5_daily.rolling(100).mean()) / m5_daily.rolling(100).mean()).shift(2)
    d_ret_5d = m5_daily.pct_change(5).shift(2)

    f['daily_sma50'] = d_sma50.reindex(m15.index, method='ffill')
    f['daily_sma100'] = d_sma100.reindex(m15.index, method='ffill')
    f['daily_ret_5d'] = d_ret_5d.reindex(m15.index, method='ffill')
    f['daily_bull'] = ((f['daily_sma50'] > 0) & (f['daily_sma100'] > 0)).astype(float)
    f['daily_bear'] = ((f['daily_sma50'] < 0) & (f['daily_sma100'] < 0)).astype(float)

    return f


def build_label(m15):
    """Detrended 4h label."""
    close = m15['close']
    trailing_4h = close.pct_change(16).rolling(96).mean()
    fwd = close.shift(-16) / close - 1
    label = (fwd > trailing_4h).astype(float)
    label[fwd.isna()] = np.nan
    return label


def train_model(X_train, y_train, X_val, y_val, feature_names, seed=42):
    """Train XGBoost with early stopping."""
    dtrain = xgb.DMatrix(X_train, label=y_train, feature_names=feature_names)
    dval = xgb.DMatrix(X_val, label=y_val, feature_names=feature_names)

    params = {
        'objective': 'binary:logistic',
        'eval_metric': 'auc',
        'tree_method': 'hist',
        'max_depth': 4,
        'learning_rate': 0.01,
        'subsample': 0.7,
        'colsample_bytree': 0.5,
        'min_child_weight': 100,
        'reg_alpha': 3.0,
        'reg_lambda': 10.0,
        'seed': seed,
    }

    model = xgb.train(
        params, dtrain, num_boost_round=500,
        evals=[(dval, 'val')],
        early_stopping_rounds=30,
        verbose_eval=False,
    )
    return model


def evaluate_oos(model, X_oos, y_oos, feature_names, daily_bull=None):
    """Evaluate with confidence gating."""
    doos = xgb.DMatrix(X_oos, feature_names=feature_names)
    proba = model.predict(doos)

    auc = roc_auc_score(y_oos, proba)
    acc = accuracy_score(y_oos, (proba > 0.5).astype(int))
    base = max(y_oos.mean(), 1 - y_oos.mean())

    results = {
        'auc': float(auc),
        'accuracy': float(acc),
        'base_rate': float(base),
        'edge': float(acc - base),
        'n_samples': len(y_oos),
        'gating': {},
    }

    for t in [0.52, 0.55, 0.58, 0.60, 0.65, 0.70, 0.75]:
        mask = (proba > t) | (proba < (1 - t))
        if mask.sum() >= 20:
            g_acc = accuracy_score(y_oos[mask], (proba[mask] > 0.5).astype(int))
            results['gating'][str(t)] = {
                'trades': int(mask.sum()),
                'trade_rate': float(mask.mean()),
                'win_rate': float(g_acc),
            }

    # Bull + Long gating
    if daily_bull is not None:
        results['bull_long'] = {}
        for t in [0.52, 0.55, 0.58, 0.60, 0.65, 0.70]:
            mask = (daily_bull == 1) & (proba > t)
            if mask.sum() >= 20:
                wr = y_oos[mask].mean()
                results['bull_long'][str(t)] = {
                    'trades': int(mask.sum()),
                    'win_rate': float(wr),
                }

    return results, proba


def main():
    print("=" * 70)
    print("PRODUCTION MODEL: 15-MIN SCALP (detrend_4h)")
    print("=" * 70)

    # Load and build
    print("\nLoading M15 data...")
    m15 = load_m15()
    print(f"  {len(m15)} bars ({m15.index[0]} to {m15.index[-1]})")

    print("Building features...")
    features = build_features(m15)

    print("Building label...")
    label = build_label(m15)

    # Trim warmup
    features = features.iloc[96 * 3:]
    label = label.loc[features.index]

    # Feature columns
    feature_cols = [c for c in features.columns if features[c].notna().mean() > 0.9]

    # Clean
    valid = features[feature_cols].notna().all(axis=1) & label.notna()
    features = features[valid]
    label = label[valid]

    print(f"  Final: {len(features)} bars × {len(feature_cols)} features")

    # ================================================================
    # MULTI-PERIOD OOS TESTING
    # Train on expanding window, test on multiple non-overlapping periods
    # ================================================================
    print("\n" + "=" * 70)
    print("MULTI-PERIOD OOS VALIDATION")
    print("=" * 70)

    # Define test windows (each ~6 months / ~12K M15 bars)
    # Total data: 2016 to 2026 (~10 years)
    # Train on first N years, test on next 6 months, repeat
    all_dates = features.index
    total_bars = len(all_dates)

    # ~6 month windows for OOS
    window_bars = 96 * 130  # ~130 trading days = 6 months
    purge_bars = 96  # 1 day purge

    test_windows = []
    # Start testing from 2019 (need 3+ years training)
    test_start_date = pd.Timestamp('2019-01-01')
    idx_start = features.index.get_indexer([test_start_date], method='nearest')[0]

    current = idx_start
    while current + window_bars < total_bars:
        test_windows.append((current, current + window_bars))
        current += window_bars

    print(f"\n  Test windows: {len(test_windows)} × ~6 months each")

    all_window_results = []
    all_predictions = []

    for i, (test_start, test_end) in enumerate(test_windows):
        train_end = test_start - purge_bars
        if train_end < 1000:
            continue

        train_df = features.iloc[:train_end]
        test_df = features.iloc[test_start:test_end]
        train_y = label.iloc[:train_end].values
        test_y = label.iloc[test_start:test_end].values

        # Split train into train/val (last 20% of train as val)
        val_split = int(len(train_df) * 0.85)
        X_train = train_df.iloc[:val_split][feature_cols].values
        y_train = train_y[:val_split]
        X_val = train_df.iloc[val_split:][feature_cols].values
        y_val = train_y[val_split:]
        X_test = test_df[feature_cols].values

        model = train_model(X_train, y_train, X_val, y_val, feature_cols, seed=42 + i)
        daily_bull = test_df['daily_bull'].values

        results, proba = evaluate_oos(model, X_test, test_y, feature_cols, daily_bull)
        results['window'] = i
        results['period'] = f"{test_df.index[0].date()} to {test_df.index[-1].date()}"
        results['train_size'] = len(train_df)
        all_window_results.append(results)

        for j in range(len(proba)):
            all_predictions.append({
                'date': test_df.index[j],
                'window': i,
                'proba': float(proba[j]),
                'y_true': float(test_y[j]),
                'daily_bull': float(daily_bull[j]),
            })

        wr_all = results['accuracy']
        wr_60 = results['gating'].get('0.6', {}).get('win_rate', 0)
        wr_65 = results['gating'].get('0.65', {}).get('win_rate', 0)
        trades_60 = results['gating'].get('0.6', {}).get('trades', 0)
        trades_65 = results['gating'].get('0.65', {}).get('trades', 0)

        print(f"\n  Window {i}: {results['period']}")
        print(f"    Train: {results['train_size']} | Test: {results['n_samples']}")
        print(f"    AUC={results['auc']:.4f} | All: {wr_all:.4f}")
        print(f"    >0.60: {trades_60} trades, WR={wr_60:.4f}")
        print(f"    >0.65: {trades_65} trades, WR={wr_65:.4f}")
        if '0.65' in results.get('bull_long', {}):
            bl = results['bull_long']['0.65']
            print(f"    BULL+>0.65: {bl['trades']} trades, WR={bl['win_rate']:.4f}")

    # ================================================================
    # AGGREGATE RESULTS
    # ================================================================
    print("\n\n" + "=" * 70)
    print("AGGREGATE MULTI-PERIOD RESULTS")
    print("=" * 70)

    pred_df = pd.DataFrame(all_predictions)
    pred_df['date'] = pd.to_datetime(pred_df['date'])

    # Overall stats
    overall_auc = roc_auc_score(pred_df['y_true'], pred_df['proba'])
    overall_acc = accuracy_score(pred_df['y_true'], (pred_df['proba'] > 0.5).astype(int))
    print(f"\n  Total predictions: {len(pred_df)}")
    print(f"  Overall AUC: {overall_auc:.4f}")
    print(f"  Overall Accuracy: {overall_acc:.4f}")
    print(f"  Base rate: {pred_df['y_true'].mean():.4f}")

    print(f"\n  Confidence Gating (all windows combined):")
    print(f"  {'Threshold':<12} {'Trades':<10} {'WinRate':<10} {'p-value':<10}")
    print(f"  {'-'*42}")

    for t in [0.50, 0.52, 0.55, 0.58, 0.60, 0.65, 0.70, 0.75]:
        mask = (pred_df['proba'] > t) | (pred_df['proba'] < (1 - t))
        n = mask.sum()
        if n < 20:
            continue
        y = pred_df.loc[mask, 'y_true'].values
        p = pred_df.loc[mask, 'proba'].values
        wr = accuracy_score(y, (p > 0.5).astype(int))
        p_val = 1 - stats.binom.cdf(int(wr * n) - 1, n, 0.5)
        marker = " ★★★" if wr >= 0.70 else " ★★" if wr >= 0.60 else " ★" if wr >= 0.55 else ""
        print(f"  >{t:<10} {n:<10} {wr:<10.4f} {p_val:<10.6f}{marker}")

    # Bull + Long
    print(f"\n  Bull + Long Gating:")
    print(f"  {'Threshold':<12} {'Trades':<10} {'WinRate':<10} {'p-value':<10}")
    print(f"  {'-'*42}")

    for t in [0.52, 0.55, 0.58, 0.60, 0.65, 0.70, 0.75]:
        mask = (pred_df['daily_bull'] == 1) & (pred_df['proba'] > t)
        n = mask.sum()
        if n < 20:
            continue
        wr = pred_df.loc[mask, 'y_true'].mean()
        p_val = 1 - stats.binom.cdf(int(wr * n) - 1, n, 0.5)
        marker = " ★★★" if wr >= 0.70 else " ★★" if wr >= 0.60 else " ★" if wr >= 0.55 else ""
        print(f"  >{t:<10} {n:<10} {wr:<10.4f} {p_val:<10.6f}{marker}")

    # Per-window consistency
    print(f"\n  Per-Window Consistency (>0.60 gating):")
    print(f"  {'Window':<8} {'Period':<28} {'Trades':<10} {'WinRate':<10}")
    print(f"  {'-'*56}")

    consistent_count = 0
    for r in all_window_results:
        g = r['gating'].get('0.6', {})
        wr = g.get('win_rate', 0)
        trades = g.get('trades', 0)
        marker = " ★" if wr >= 0.65 else ""
        if wr > 0.55:
            consistent_count += 1
        print(f"  {r['window']:<8} {r['period']:<28} {trades:<10} {wr:<10.4f}{marker}")

    print(f"\n  Windows with >55% WR at >0.60 gate: {consistent_count}/{len(all_window_results)}")

    # ================================================================
    # TRAIN FINAL PRODUCTION MODEL
    # ================================================================
    print("\n\n" + "=" * 70)
    print("TRAINING FINAL PRODUCTION MODEL (all data up to 2025)")
    print("=" * 70)

    # Use all data up to end of 2025 for training
    cutoff = pd.Timestamp('2025-12-31')
    train_mask = features.index <= cutoff
    final_train = features[train_mask]
    final_label = label[train_mask]

    val_split = int(len(final_train) * 0.9)
    X_train = final_train.iloc[:val_split][feature_cols].values
    y_train = final_label.iloc[:val_split].values
    X_val = final_train.iloc[val_split:][feature_cols].values
    y_val = final_label.iloc[val_split:].values

    final_model = train_model(X_train, y_train, X_val, y_val, feature_cols, seed=42)

    # Save model
    model_path = OUTPUT_DIR / "scalp15m_detrend4h.json"
    final_model.save_model(str(model_path))
    print(f"  Model saved: {model_path}")

    # Save feature names and config
    config = {
        'model_file': str(model_path),
        'feature_cols': feature_cols,
        'label': 'detrend_4h',
        'description': 'Predict if gold 4h return exceeds trailing avg 4h return',
        'timeframe': 'M15',
        'horizon': '16 bars (4 hours)',
        'daily_overlay_shift': 2,
        'warmup_bars': 288,
        'params': {
            'max_depth': 4,
            'learning_rate': 0.01,
            'subsample': 0.7,
            'colsample_bytree': 0.5,
            'min_child_weight': 100,
            'reg_alpha': 3.0,
            'reg_lambda': 10.0,
        },
        'recommended_gating': {
            'conservative': {'threshold': 0.65, 'expected_wr': '70-85%', 'trades_per_day': '~1-3'},
            'moderate': {'threshold': 0.60, 'expected_wr': '65-75%', 'trades_per_day': '~5-10'},
            'aggressive': {'threshold': 0.55, 'expected_wr': '60-68%', 'trades_per_day': '~15-25'},
        },
    }

    with open(OUTPUT_DIR / "model_config.json", 'w') as fout:
        json.dump(config, fout, indent=2)

    # Save validation results
    validation = {
        'timestamp': str(pd.Timestamp.now()),
        'multi_period_oos': all_window_results,
        'overall_auc': float(overall_auc),
        'overall_accuracy': float(overall_acc),
        'total_oos_predictions': len(pred_df),
        'windows_tested': len(all_window_results),
    }
    with open(OUTPUT_DIR / "validation_results.json", 'w') as fout:
        json.dump(validation, fout, indent=2, default=str)

    # Feature importance
    importance = final_model.get_score(importance_type='total_gain')
    top_feats = sorted(importance.items(), key=lambda x: -x[1])[:15]
    print(f"\n  Top features:")
    for name, val in top_feats:
        print(f"    {name}: {val:.0f}")

    print(f"\n\n{'='*70}")
    print("DONE — Files saved:")
    print(f"  Model:      {model_path}")
    print(f"  Config:     {OUTPUT_DIR}/model_config.json")
    print(f"  Validation: {OUTPUT_DIR}/validation_results.json")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
