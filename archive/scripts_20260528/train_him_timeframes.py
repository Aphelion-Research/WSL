"""
Him V2 Specialized Timeframe Models: M5, M15, H1
Each model has 10 EMA ensemble + VWAP (universal) plus timeframe-specific features.
Train: 2015-2024 | Test: 2025-2026
"""
import pandas as pd
import numpy as np
import xgboost as xgb
import json
import warnings
from pathlib import Path
from datetime import datetime
from sklearn.metrics import roc_auc_score

warnings.filterwarnings('ignore')

DATA_PATH = Path("data/mt5_history/XAUUSD_M5_dukascopy.parquet")
MODEL_DIR = Path("models/Him")
OUTPUT_DIR = Path("output_him_v2")
MODEL_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)


# ============================================================
# UNIVERSAL FEATURES: 10 EMA Ensemble + VWAP
# ============================================================

EMA_PERIODS = [9, 21, 50, 100, 150, 200, 300, 500, 800, 1000]

def compute_10ema_ensemble(close):
    """Compute 10 EMA ensemble features from close prices."""
    f = pd.DataFrame(index=close.index)

    emas = {}
    for p in EMA_PERIODS:
        ema = close.ewm(span=p, adjust=False).mean()
        emas[p] = ema
        f[f'ema_{p}'] = ema

    # Price above each key EMA (binary)
    for p in [9, 21, 50, 200]:
        f[f'price_above_ema{p}'] = (close > emas[p]).astype(float)

    # Bullish order count: how many consecutive EMAs are in order
    bullish_count = np.zeros(len(close))
    ordered_periods = [9, 21, 50, 100, 150, 200, 300, 500, 800, 1000]
    for i in range(len(ordered_periods) - 1):
        shorter = emas[ordered_periods[i]].values
        longer = emas[ordered_periods[i + 1]].values
        bullish_count += (shorter > longer).astype(float)
    f['ema_bullish_count'] = bullish_count / (len(ordered_periods) - 1)

    # EMA spread: (ema9 - ema1000) / close
    f['ema_spread'] = (emas[9] - emas[1000]) / close

    # Distance to nearest EMA
    ema_arr = np.column_stack([emas[p].values for p in EMA_PERIODS])
    close_arr = close.values.reshape(-1, 1)
    distances = np.abs(ema_arr - close_arr) / close_arr
    f['dist_to_nearest_ema'] = np.nanmin(distances, axis=1)

    # Drop raw EMA values (keep derived features only)
    feature_cols = [c for c in f.columns if not c.startswith('ema_') or c in ['ema_bullish_count', 'ema_spread']]
    # Actually keep all - model can use raw EMAs as price levels normalized
    # Convert raw EMAs to relative position (normalized)
    for p in EMA_PERIODS:
        f[f'ema_{p}_pos'] = (close - emas[p]) / close
        del f[f'ema_{p}']

    return f


def compute_vwap_bands(close, high, low, volume, period=72):
    """Compute VWAP + bands features."""
    f = pd.DataFrame(index=close.index)

    tp = (high + low + close) / 3
    vol = volume.replace(0, 1)

    vwap = (tp * vol).rolling(period).sum() / vol.rolling(period).sum()
    f['vwap_dev'] = close - vwap
    f['vwap_dev_pct'] = f['vwap_dev'] / vwap

    # VWAP bands (rolling std of deviation)
    dev_std = f['vwap_dev'].rolling(period).std()
    upper = vwap + dev_std
    lower = vwap - dev_std
    band_width = (upper - lower).replace(0, np.nan)
    f['price_vs_vwap_band'] = ((close - lower) / band_width).clip(0, 1)

    # VWAP slope
    f['vwap_slope'] = vwap.diff(5) / vwap

    return f


# ============================================================
# M5 MODEL (Scalping Specialist)
# ============================================================

def train_m5(m5):
    print("\n" + "=" * 80)
    print("M5 MODEL (Scalping Specialist)")
    print("=" * 80)

    close = m5['close']
    high = m5['high']
    low = m5['low']
    volume = m5['tick_volume']

    # --- Label: next 12-bar (1h) excess return over trailing mean ---
    fwd_ret_12 = close.pct_change(12).shift(-12)
    trailing_avg = close.pct_change(12).rolling(48).mean()
    label = (fwd_ret_12 > trailing_avg).astype(float)

    # --- Universal features ---
    f_ema = compute_10ema_ensemble(close)
    f_vwap = compute_vwap_bands(close, high, low, volume, period=72)

    # --- M5-specific features ---
    f_spec = pd.DataFrame(index=m5.index)

    # Momentum (multi-scale for 1h horizon)
    for bars in [4, 12, 24, 48, 96]:
        f_spec[f'ret_{bars}bar'] = close.pct_change(bars)

    # Pullback/Reversal
    for n in [12, 24, 48]:
        rolling_high = high.rolling(n).max()
        rolling_low = low.rolling(n).min()
        f_spec[f'pullback_high_{n}'] = (rolling_high - close) / close
        f_spec[f'pullback_low_{n}'] = (close - rolling_low) / close

    # Range position (48-bar = 4h window)
    rh_48 = close.rolling(48).max()
    rl_48 = close.rolling(48).min()
    rng_48 = (rh_48 - rl_48).replace(0, np.nan)
    f_spec['range_pos_4h'] = (close - rl_48) / rng_48

    # Volume ratio
    f_spec['vol_ratio'] = volume / volume.rolling(48).mean().replace(0, np.nan)

    # Volatility
    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs()
    ], axis=1).max(axis=1)
    atr_24 = tr.rolling(24).mean()
    f_spec['atr_2h_pct'] = atr_24 / close
    f_spec['vol_ratio_short_long'] = tr.rolling(12).mean() / atr_24.replace(0, np.nan)

    # Session timing
    hour = m5.index.hour + m5.index.minute / 60
    f_spec['cos_hour'] = np.cos(2 * np.pi * hour / 24)
    f_spec['sin_hour'] = np.sin(2 * np.pi * hour / 24)
    f_spec['cos_dow'] = np.cos(2 * np.pi * m5.index.dayofweek / 5)

    # Combine all features
    features = pd.concat([f_ema, f_vwap, f_spec], axis=1)
    features['label'] = label
    features = features.dropna()

    feature_cols = [c for c in features.columns if c != 'label']
    print(f"  Features: {len(feature_cols)}")
    print(f"  Label balance: {features['label'].mean()*100:.1f}% up")

    # Split
    train = features[features.index < '2025-01-01']
    test = features[features.index >= '2025-01-01']
    print(f"  Train: {len(train):,} bars | Test: {len(test):,} bars")

    # Train XGBoost
    dtrain = xgb.DMatrix(train[feature_cols].values, label=train['label'].values, feature_names=feature_cols)
    dtest = xgb.DMatrix(test[feature_cols].values, label=test['label'].values, feature_names=feature_cols)

    params = {
        'max_depth': 4,
        'learning_rate': 0.05,
        'subsample': 0.7,
        'colsample_bytree': 0.5,
        'min_child_weight': 100,
        'reg_alpha': 3.0,
        'reg_lambda': 5.0,
        'objective': 'binary:logistic',
        'eval_metric': 'auc',
        'tree_method': 'hist',
        'seed': 42,
    }

    model = xgb.train(
        params, dtrain,
        num_boost_round=300,
        evals=[(dtrain, 'train'), (dtest, 'test')],
        early_stopping_rounds=50,
        verbose_eval=50,
    )

    # Evaluate
    test_pred = model.predict(dtest)
    test_auc = roc_auc_score(test['label'].values, test_pred)
    print(f"  Test AUC: {test_auc:.4f}")
    print(f"  Best iteration: {model.best_iteration}")
    print(f"  Pred dist: mean={test_pred.mean():.4f}, std={test_pred.std():.4f}")
    print(f"    >0.55: {(test_pred>0.55).sum()} | >0.60: {(test_pred>0.60).sum()} | >0.65: {(test_pred>0.65).sum()}")

    # Save model
    model_path = MODEL_DIR / "Him_M5.json"
    model.save_model(str(model_path))
    print(f"  Model saved: {model_path}")

    # Top features
    importance = model.get_score(importance_type='gain')
    imp_sorted = sorted(importance.items(), key=lambda x: -x[1])[:10]
    print(f"  Top 10 features:")
    for feat, gain in imp_sorted:
        print(f"    {feat:<25s} {gain:.1f}")

    return {
        'features': feature_cols,
        'timeframe': 'M5',
        'label': 'excess_return_12bar',
        'test_auc': float(test_auc),
        'best_iteration': model.best_iteration,
        'holding_bars': 12,
        'pred_std': float(test_pred.std()),
        'train_size': len(train),
        'test_size': len(test),
    }


# ============================================================
# M15 MODEL (Mean-Reversion Specialist)
# ============================================================

def train_m15(m5):
    print("\n" + "=" * 80)
    print("M15 MODEL (Mean-Reversion Specialist)")
    print("=" * 80)

    # Resample to M15
    m15 = m5.resample('15min').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'tick_volume': 'sum',
        'spread': 'mean',
    }).dropna(subset=['close'])
    m15 = m15[m15['tick_volume'] > 0]
    print(f"  M15 bars: {len(m15):,}")

    close = m15['close']
    high = m15['high']
    low = m15['low']
    volume = m15['tick_volume']

    # --- Label: excess return over trailing 96-bar average ---
    ret_16 = close.pct_change(16)
    trailing_avg = ret_16.rolling(96).mean()
    fwd_ret_16 = close.pct_change(16).shift(-16)
    label = (fwd_ret_16 > trailing_avg).astype(float)

    # --- Universal features ---
    f_ema = compute_10ema_ensemble(close)
    f_vwap = compute_vwap_bands(close, high, low, volume, period=72)

    # --- M15-specific features ---
    f_spec = pd.DataFrame(index=m15.index)

    # Momentum (medium-term)
    for bars in [16, 32, 64, 96]:
        f_spec[f'ret_{bars}bar'] = close.pct_change(bars)

    # Pullback depth (ATR-normalized)
    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs()
    ], axis=1).max(axis=1)
    atr_96 = tr.rolling(96).mean().replace(0, np.nan)

    for period in [16, 32, 64]:
        rh = close.rolling(period).max()
        f_spec[f'pullback_high_{period}'] = (rh - close) / atr_96

    # Range position (96-bar)
    rolling_high_96 = close.rolling(96).max()
    rolling_low_96 = close.rolling(96).min()
    rng_96 = (rolling_high_96 - rolling_low_96).replace(0, np.nan)
    f_spec['range_pos_96bar'] = (close - rolling_low_96) / rng_96

    # RSI
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss_val = (-delta.where(delta < 0, 0)).rolling(14).mean().replace(0, np.nan)
    f_spec['rsi_14'] = 100 - 100 / (1 + gain / loss_val)

    # Bollinger position
    bb_mid = close.rolling(20).mean()
    bb_std = close.rolling(20).std().replace(0, np.nan)
    f_spec['bb_pos'] = (close - bb_mid) / (2 * bb_std)

    # Session timing
    hour = m15.index.hour + m15.index.minute / 60
    f_spec['cos_hour'] = np.cos(2 * np.pi * hour / 24)
    f_spec['sin_hour'] = np.sin(2 * np.pi * hour / 24)
    f_spec['cos_dow'] = np.cos(2 * np.pi * m15.index.dayofweek / 5)

    # Combine
    features = pd.concat([f_ema, f_vwap, f_spec], axis=1)
    features['label'] = label
    features = features.dropna()

    feature_cols = [c for c in features.columns if c != 'label']
    print(f"  Features: {len(feature_cols)}")
    print(f"  Label balance: {features['label'].mean()*100:.1f}% up")

    # Split
    train = features[features.index < '2025-01-01']
    test = features[features.index >= '2025-01-01']
    print(f"  Train: {len(train):,} bars | Test: {len(test):,} bars")

    # Train
    dtrain = xgb.DMatrix(train[feature_cols].values, label=train['label'].values, feature_names=feature_cols)
    dtest = xgb.DMatrix(test[feature_cols].values, label=test['label'].values, feature_names=feature_cols)

    params = {
        'max_depth': 4,
        'learning_rate': 0.05,
        'subsample': 0.7,
        'colsample_bytree': 0.5,
        'min_child_weight': 100,
        'reg_alpha': 3.0,
        'reg_lambda': 5.0,
        'objective': 'binary:logistic',
        'eval_metric': 'auc',
        'tree_method': 'hist',
        'seed': 42,
    }

    model = xgb.train(
        params, dtrain,
        num_boost_round=300,
        evals=[(dtrain, 'train'), (dtest, 'test')],
        early_stopping_rounds=50,
        verbose_eval=50,
    )

    test_pred = model.predict(dtest)
    test_auc = roc_auc_score(test['label'].values, test_pred)
    print(f"  Test AUC: {test_auc:.4f}")
    print(f"  Best iteration: {model.best_iteration}")
    print(f"  Pred dist: mean={test_pred.mean():.4f}, std={test_pred.std():.4f}")
    print(f"    >0.55: {(test_pred>0.55).sum()} | >0.60: {(test_pred>0.60).sum()} | >0.65: {(test_pred>0.65).sum()}")

    model_path = MODEL_DIR / "Him_M15.json"
    model.save_model(str(model_path))
    print(f"  Model saved: {model_path}")

    importance = model.get_score(importance_type='gain')
    imp_sorted = sorted(importance.items(), key=lambda x: -x[1])[:10]
    print(f"  Top 10 features:")
    for feat, gain in imp_sorted:
        print(f"    {feat:<25s} {gain:.1f}")

    return {
        'features': feature_cols,
        'timeframe': 'M15',
        'label': 'mean_reversion_16bar',
        'test_auc': float(test_auc),
        'best_iteration': model.best_iteration,
        'holding_bars': 16,
        'pred_std': float(test_pred.std()),
        'train_size': len(train),
        'test_size': len(test),
    }


# ============================================================
# H1 MODEL (Swing Trading Specialist)
# ============================================================

def train_h1(m5):
    print("\n" + "=" * 80)
    print("H1 MODEL (Swing Trading Specialist)")
    print("=" * 80)

    # Resample to H1
    h1 = m5.resample('1h').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'tick_volume': 'sum',
        'spread': 'mean',
    }).dropna(subset=['close'])
    h1 = h1[h1['tick_volume'] > 0]
    print(f"  H1 bars: {len(h1):,}")

    close = h1['close']
    high = h1['high']
    low = h1['low']
    volume = h1['tick_volume']

    # --- Label: next 4-hour excess return (detrended) ---
    fwd_ret_4h = close.pct_change(4).shift(-4)
    trailing_avg_4h = close.pct_change(4).rolling(24).mean()
    label = (fwd_ret_4h > trailing_avg_4h).astype(float)

    # --- Universal features ---
    f_ema = compute_10ema_ensemble(close)
    f_vwap = compute_vwap_bands(close, high, low, volume, period=72)

    # --- H1-specific features ---
    f_spec = pd.DataFrame(index=h1.index)

    # Momentum (multi-scale)
    for bars in [1, 2, 4, 8, 12, 24, 48, 96]:
        f_spec[f'ret_{bars}bar'] = close.pct_change(bars)

    # ATR multi-scale
    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs()
    ], axis=1).max(axis=1)
    atr_6 = tr.rolling(6).mean().replace(0, np.nan)
    atr_24 = tr.rolling(24).mean().replace(0, np.nan)
    atr_96 = tr.rolling(96).mean().replace(0, np.nan)
    f_spec['atr_6h_pct'] = atr_6 / close
    f_spec['atr_24h_pct'] = atr_24 / close
    f_spec['atr_96h_pct'] = atr_96 / close
    f_spec['vol_ratio_short_long'] = atr_6 / atr_24

    # Range position (multi-scale)
    for period, suffix in [(12, '12h'), (24, '24h'), (48, '48h'), (96, '96h')]:
        rh = close.rolling(period).max()
        rl = close.rolling(period).min()
        rng = (rh - rl).replace(0, np.nan)
        f_spec[f'range_pos_{suffix}'] = (close - rl) / rng

    # Pullback from high (ATR-normalized)
    for period, suffix in [(12, '12h'), (24, '24h'), (48, '48h')]:
        rh = close.rolling(period).max()
        rl = close.rolling(period).min()
        f_spec[f'pullback_high_{suffix}'] = (rh - close) / atr_24
        f_spec[f'pullback_low_{suffix}'] = (close - rl) / atr_24

    # Volume
    f_spec['vol_ratio'] = volume / volume.rolling(24).mean().replace(0, np.nan)
    f_spec['vol_zscore'] = (volume - volume.rolling(96).mean()) / volume.rolling(96).std().replace(0, np.nan)

    # Session timing
    f_spec['cos_hour'] = np.cos(2 * np.pi * h1.index.hour / 24)
    f_spec['sin_hour'] = np.sin(2 * np.pi * h1.index.hour / 24)
    f_spec['cos_dow'] = np.cos(2 * np.pi * h1.index.dayofweek / 5)

    # RSI
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss_val = (-delta.where(delta < 0, 0)).rolling(14).mean().replace(0, np.nan)
    f_spec['rsi_14'] = 100 - 100 / (1 + gain / loss_val)

    # Bollinger band position
    bb_mid = close.rolling(20).mean()
    bb_std = close.rolling(20).std().replace(0, np.nan)
    f_spec['bb_pos'] = (close - bb_mid) / (2 * bb_std)

    # Consecutive direction
    f_spec['consec_up'] = close.diff().gt(0).rolling(8).sum()
    f_spec['consec_down'] = close.diff().lt(0).rolling(8).sum()

    # Combine
    features = pd.concat([f_ema, f_vwap, f_spec], axis=1)
    features['label'] = label
    features = features.dropna()

    feature_cols = [c for c in features.columns if c != 'label']
    print(f"  Features: {len(feature_cols)}")
    print(f"  Label balance: {features['label'].mean()*100:.1f}% up")

    # Split
    train = features[features.index < '2025-01-01']
    test = features[features.index >= '2025-01-01']
    print(f"  Train: {len(train):,} bars | Test: {len(test):,} bars")

    # Train
    dtrain = xgb.DMatrix(train[feature_cols].values, label=train['label'].values, feature_names=feature_cols)
    dtest = xgb.DMatrix(test[feature_cols].values, label=test['label'].values, feature_names=feature_cols)

    params = {
        'max_depth': 4,
        'learning_rate': 0.05,
        'subsample': 0.7,
        'colsample_bytree': 0.5,
        'min_child_weight': 100,
        'reg_alpha': 3.0,
        'reg_lambda': 5.0,
        'objective': 'binary:logistic',
        'eval_metric': 'auc',
        'tree_method': 'hist',
        'seed': 42,
    }

    model = xgb.train(
        params, dtrain,
        num_boost_round=300,
        evals=[(dtrain, 'train'), (dtest, 'test')],
        early_stopping_rounds=50,
        verbose_eval=50,
    )

    test_pred = model.predict(dtest)
    test_auc = roc_auc_score(test['label'].values, test_pred)
    print(f"  Test AUC: {test_auc:.4f}")
    print(f"  Best iteration: {model.best_iteration}")
    print(f"  Pred dist: mean={test_pred.mean():.4f}, std={test_pred.std():.4f}")
    print(f"    >0.55: {(test_pred>0.55).sum()} | >0.60: {(test_pred>0.60).sum()} | >0.65: {(test_pred>0.65).sum()}")

    model_path = MODEL_DIR / "Him_H1.json"
    model.save_model(str(model_path))
    print(f"  Model saved: {model_path}")

    importance = model.get_score(importance_type='gain')
    imp_sorted = sorted(importance.items(), key=lambda x: -x[1])[:10]
    print(f"  Top 10 features:")
    for feat, gain in imp_sorted:
        print(f"    {feat:<25s} {gain:.1f}")

    return {
        'features': feature_cols,
        'timeframe': 'H1',
        'label': 'excess_return_4h',
        'test_auc': float(test_auc),
        'best_iteration': model.best_iteration,
        'holding_bars': 4,
        'pred_std': float(test_pred.std()),
        'train_size': len(train),
        'test_size': len(test),
    }


# ============================================================
# MAIN
# ============================================================

def main():
    start = datetime.now()
    print(f"HIM V2 TIMEFRAME MODELS — {start.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print("Universal features: 10 EMA ensemble + VWAP bands")
    print("Timeframes: M5 (scalp) | M15 (mean-reversion) | H1 (swing)")
    print("=" * 80)

    # Load M5 data
    print("\nLoading M5 data...")
    m5 = pd.read_parquet(DATA_PATH)
    m5['time'] = pd.to_datetime(m5['time'])
    m5 = m5.set_index('time').sort_index()
    m5 = m5[m5.index >= '2015-01-01']
    print(f"  M5 bars: {len(m5):,} ({m5.index[0].date()} to {m5.index[-1].date()})")

    # Train all 3 models
    results = {}
    results['M5'] = train_m5(m5)
    results['M15'] = train_m15(m5)
    results['H1'] = train_h1(m5)

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"\n  {'Model':<8} {'Features':<10} {'Test AUC':<10} {'Pred Std':<10} {'Iters':<8} {'Label'}")
    print(f"  {'-'*60}")
    for tf, r in results.items():
        print(f"  {tf:<8} {len(r['features']):<10} {r['test_auc']:<10.4f} {r['pred_std']:<10.4f} {r['best_iteration']:<8} {r['label']}")

    # Save config
    config_path = OUTPUT_DIR / "him_timeframe_configs.json"
    with open(config_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n  Configs saved: {config_path}")

    elapsed = (datetime.now() - start).total_seconds()
    print(f"  Total time: {elapsed:.0f}s")

    # Verdict
    viable = sum(1 for r in results.values() if r['test_auc'] > 0.54)
    print(f"\n  Viable models (AUC > 0.54): {viable}/3")
    if viable == 3:
        print("  ✓ All models trained with 10 EMA ensemble + VWAP")
        print("  ✓ Ready for multi-model deployment")
    elif viable >= 2:
        print("  ⚠ Partial success — review weak model")
    else:
        print("  ✗ Models need more work")


if __name__ == "__main__":
    main()
