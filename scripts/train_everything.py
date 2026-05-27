"""
FULL ASSAULT: Every legitimate approach to find 60%+ win rate on XAU/USD.

Approaches:
1. Daily bars + daily features (frequency-matched)
2. Big moves only (predict >1ATR moves, ignore noise)
3. Regime detection + conditional direction
4. Weekly horizon (less efficient, risk premia exist)
5. Ensemble with confidence gating

All with purged walk-forward validation.
"""
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.metrics import roc_auc_score, accuracy_score
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
import xgboost as xgb
import json
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

DATA_DIR = Path("data")
OUTPUT_DIR = Path("output_fullassault")
OUTPUT_DIR.mkdir(exist_ok=True)


# ============================================================
# DATA LOADING
# ============================================================

def load_xau_daily():
    """Build proper daily OHLCV from M5 data."""
    m5 = pd.read_parquet(DATA_DIR / "mt5_history/XAUUSD_M5_dukascopy.parquet")
    m5['time'] = pd.to_datetime(m5['time'])
    m5 = m5.set_index('time').sort_index()

    daily = m5.resample('1D').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'tick_volume': 'sum',
        'spread': 'mean',
    }).dropna(subset=['close'])

    # Remove weekends with no data
    daily = daily[daily['tick_volume'] > 0]
    return daily


def load_xau_h4():
    """Build H4 bars from M5."""
    m5 = pd.read_parquet(DATA_DIR / "mt5_history/XAUUSD_M5_dukascopy.parquet")
    m5['time'] = pd.to_datetime(m5['time'])
    m5 = m5.set_index('time').sort_index()

    h4 = m5.resample('4h').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'tick_volume': 'sum',
        'spread': 'mean',
    }).dropna(subset=['close'])
    h4 = h4[h4['tick_volume'] > 0]
    return h4


def load_cross_asset():
    df = pd.read_parquet(DATA_DIR / "cross_asset/cross_asset_daily.parquet")
    df.index = pd.to_datetime(df.index)
    return df


def load_macro():
    macro_dir = DATA_DIR / "macro"
    series = {}
    for name in ['DGS2', 'DGS10', 'DGS5', 'DFII10', 'DFII5', 'T5YIE', 'T10YIE', 'DFF',
                 'T10Y2Y', 'T10Y3M']:
        f = macro_dir / f"{name}.parquet"
        if f.exists():
            s = pd.read_parquet(f)
            if 'value' in s.columns and 'date' in s.columns:
                s = s.set_index('date')['value']
            elif 'value' in s.columns:
                s = s['value']
            elif len(s.columns) == 1:
                s = s.iloc[:, 0]
            else:
                s = s.iloc[:, -1]
            s.index = pd.to_datetime(s.index)
            s = pd.to_numeric(s, errors='coerce')
            series[name] = s
    combined = pd.DataFrame(series)
    combined = combined.ffill()
    return combined


def load_cot():
    df = pd.read_parquet(DATA_DIR / "cot/cot_gold_weekly.parquet")
    df.index = pd.to_datetime(df.index)
    return df


# ============================================================
# FEATURE ENGINEERING - DAILY
# ============================================================

def build_daily_features(daily, cross, macro, cot):
    """Build features at daily frequency - where signals actually live."""
    f = pd.DataFrame(index=daily.index)

    close = daily['close']
    high = daily['high']
    low = daily['low']
    volume = daily['tick_volume']

    # --- PRICE MOMENTUM ---
    f['ret_1d'] = close.pct_change(1)
    f['ret_3d'] = close.pct_change(3)
    f['ret_5d'] = close.pct_change(5)
    f['ret_10d'] = close.pct_change(10)
    f['ret_20d'] = close.pct_change(20)

    # --- TREND POSITION ---
    for period in [20, 50, 100, 200]:
        sma = close.rolling(period).mean()
        f[f'sma{period}_pos'] = (close - sma) / sma

    # --- VOLATILITY (ATR-based) ---
    tr = pd.concat([high - low, (high - close.shift(1)).abs(), (low - close.shift(1)).abs()], axis=1).max(axis=1)
    f['atr_14'] = tr.rolling(14).mean() / close
    f['atr_5'] = tr.rolling(5).mean() / close
    f['vol_ratio'] = f['atr_5'] / f['atr_14'].replace(0, np.nan)

    # Realized vol
    f['rvol_10d'] = f['ret_1d'].rolling(10).std() * np.sqrt(252)
    f['rvol_20d'] = f['ret_1d'].rolling(20).std() * np.sqrt(252)
    f['vol_regime'] = f['rvol_10d'] / f['rvol_20d'].replace(0, np.nan)

    # --- MEAN REVERSION ---
    f['bb_pos'] = (close - close.rolling(20).mean()) / (2 * close.rolling(20).std().replace(0, np.nan))
    f['rsi_14'] = compute_rsi(close, 14)
    f['rsi_5'] = compute_rsi(close, 5)

    # --- VOLUME ---
    f['vol_sma_ratio'] = volume / volume.rolling(20).mean().replace(0, np.nan)

    # --- CANDLE STRUCTURE ---
    body = (close - daily['open']).abs()
    range_ = (high - low).replace(0, np.nan)
    f['body_ratio'] = body / range_
    f['upper_wick'] = (high - pd.concat([close, daily['open']], axis=1).max(axis=1)) / range_
    f['lower_wick'] = (pd.concat([close, daily['open']], axis=1).min(axis=1) - low) / range_

    # --- DAY OF WEEK ---
    f['dow'] = daily.index.dayofweek
    f['cos_dow'] = np.cos(2 * np.pi * f['dow'] / 5)
    f['sin_dow'] = np.sin(2 * np.pi * f['dow'] / 5)
    f.drop('dow', axis=1, inplace=True)

    # --- CROSS-ASSET (lagged 1 day for point-in-time) ---
    cross_aligned = cross.reindex(daily.index, method='ffill').shift(1)

    if 'dxy' in cross_aligned.columns:
        dxy = cross_aligned['dxy']
        f['dxy_ret_1d'] = dxy.pct_change(1)
        f['dxy_ret_5d'] = dxy.pct_change(5)
        f['dxy_sma50'] = (dxy - dxy.rolling(50).mean()) / dxy.rolling(50).mean()
        # Gold-DXY divergence
        f['gold_dxy_div_5d'] = f['ret_5d'] + dxy.pct_change(5)  # should be negative normally

    if 'vix' in cross_aligned.columns:
        f['vix'] = cross_aligned['vix']
        f['vix_change_5d'] = cross_aligned['vix'].diff(5)
        f['vix_ma_ratio'] = cross_aligned['vix'] / cross_aligned['vix'].rolling(20).mean()

    if 'silver' in cross_aligned.columns:
        silver_ret = cross_aligned['silver'].pct_change(5)
        f['gold_silver_spread_5d'] = f['ret_5d'] - silver_ret  # relative strength

    if 'spx' in cross_aligned.columns:
        f['spx_ret_5d'] = cross_aligned['spx'].pct_change(5)
        f['gold_spx_corr_20d'] = close.pct_change().rolling(20).corr(cross_aligned['spx'].pct_change())

    if 'tlt' in cross_aligned.columns:
        f['tlt_ret_5d'] = cross_aligned['tlt'].pct_change(5)
        f['gold_tlt_corr_20d'] = close.pct_change().rolling(20).corr(cross_aligned['tlt'].pct_change())

    if 'btc' in cross_aligned.columns:
        f['btc_ret_5d'] = cross_aligned['btc'].pct_change(5)

    if 'wti' in cross_aligned.columns:
        f['wti_ret_5d'] = cross_aligned['wti'].pct_change(5)

    if 'copper' in cross_aligned.columns:
        f['copper_ret_5d'] = cross_aligned['copper'].pct_change(5)

    # --- YIELDS (lagged 1 day) ---
    macro_aligned = macro.reindex(daily.index, method='ffill').shift(1)

    if 'DGS10' in macro_aligned.columns and 'DGS2' in macro_aligned.columns:
        f['yield_10y2y'] = macro_aligned['DGS10'] - macro_aligned['DGS2']
        f['yield_10y2y_change_5d'] = f['yield_10y2y'].diff(5)

    if 'DFII10' in macro_aligned.columns:
        f['real_yield_10y'] = macro_aligned['DFII10']
        f['real_yield_10y_change_5d'] = macro_aligned['DFII10'].diff(5)
        f['real_yield_10y_change_20d'] = macro_aligned['DFII10'].diff(20)

    if 'T10YIE' in macro_aligned.columns:
        f['breakeven_10y'] = macro_aligned['T10YIE']
        f['breakeven_change_5d'] = macro_aligned['T10YIE'].diff(5)

    # --- COT (weekly, lagged 3 days for release delay) ---
    cot_aligned = cot.copy()
    cot_aligned.index = cot_aligned.index + pd.Timedelta(days=3)
    cot_aligned = cot_aligned.reindex(daily.index, method='ffill')

    net = cot_aligned['mm_long'] - cot_aligned['mm_short']
    f['cot_net'] = net
    f['cot_net_pctile'] = net.rolling(52*5, min_periods=52).rank(pct=True)  # 5yr percentile
    f['cot_net_change'] = net.diff(1)
    f['cot_oi_change'] = cot_aligned['open_interest'].pct_change(1)

    return f


def compute_rsi(series, period):
    delta = series.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


# ============================================================
# LABELS
# ============================================================

def make_labels(daily):
    """Multiple label types for different approaches."""
    labels = pd.DataFrame(index=daily.index)
    close = daily['close']

    # Standard direction
    for h in [1, 3, 5, 10, 20]:
        fwd = close.shift(-h) / close - 1
        labels[f'dir_{h}d'] = (fwd > 0).astype(float)
        labels[f'ret_{h}d'] = fwd

    # Big move labels (only predict moves > 1 ATR)
    tr = pd.concat([
        daily['high'] - daily['low'],
        (daily['high'] - close.shift(1)).abs(),
        (daily['low'] - close.shift(1)).abs()
    ], axis=1).max(axis=1)
    atr_14 = tr.rolling(14).mean()

    for h in [3, 5, 10]:
        fwd = close.shift(-h) / close - 1
        threshold = (atr_14 * h * 0.5) / close  # half ATR per day
        labels[f'big_up_{h}d'] = (fwd > threshold).astype(float)
        labels[f'big_down_{h}d'] = (fwd < -threshold).astype(float)
        labels[f'big_move_{h}d'] = ((fwd > threshold) | (fwd < -threshold)).astype(float)

    return labels


# ============================================================
# REGIME DETECTION
# ============================================================

def detect_regimes(daily, features):
    """
    Classify market regime: trending / mean-reverting / random.
    Use simple rule-based approach (not ML to avoid lookahead).
    """
    close = daily['close']
    regimes = pd.Series(index=daily.index, dtype='object')

    # Hurst exponent proxy (variance ratio test)
    ret = close.pct_change()

    # Variance ratio: var(n*ret) / (n * var(ret))
    # > 1 = trending, < 1 = mean-reverting, ~1 = random
    n = 10
    var_1 = ret.rolling(60).var()
    var_n = ret.rolling(60).apply(lambda x: pd.Series(x).rolling(n).sum().var() if len(x) >= n else np.nan)
    vr = var_n / (n * var_1).replace(0, np.nan)

    # ADX proxy (trend strength)
    high = daily['high']
    low = daily['low']

    plus_dm = (high - high.shift(1)).clip(lower=0)
    minus_dm = (low.shift(1) - low).clip(lower=0)

    tr = pd.concat([high - low, (high - close.shift(1)).abs(), (low - close.shift(1)).abs()], axis=1).max(axis=1)
    atr_14 = tr.rolling(14).mean()

    plus_di = 100 * plus_dm.rolling(14).mean() / atr_14.replace(0, np.nan)
    minus_di = 100 * minus_dm.rolling(14).mean() / atr_14.replace(0, np.nan)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    adx = dx.rolling(14).mean()

    features_out = features.copy()
    features_out['adx'] = adx
    features_out['variance_ratio'] = vr

    # Regime classification
    features_out['regime_trending'] = (adx > 25).astype(float)
    features_out['regime_volatile'] = (features['rvol_10d'] > features['rvol_20d'] * 1.5).astype(float)

    return features_out


# ============================================================
# WALK-FORWARD WITH PURGING
# ============================================================

def purged_walk_forward(df, feature_cols, label_col, n_splits=5, purge_days=5):
    """
    Walk-forward cross-validation with purge gap.
    More robust than single split.
    """
    valid = df.dropna(subset=[label_col] + feature_cols)
    n = len(valid)

    # Each fold uses expanding window
    fold_size = n // (n_splits + 1)
    results = []

    for i in range(n_splits):
        train_end = fold_size * (i + 2)
        test_start = train_end + purge_days
        test_end = min(test_start + fold_size, n)

        if test_end <= test_start:
            continue

        train = valid.iloc[:train_end]
        test = valid.iloc[test_start:test_end]

        if len(test) < 50:
            continue

        X_train = train[feature_cols].values
        y_train = train[label_col].values
        X_test = test[feature_cols].values
        y_test = test[label_col].values

        # XGBoost
        dtrain = xgb.DMatrix(X_train, label=y_train)
        dtest = xgb.DMatrix(X_test, label=y_test)

        params = {
            'objective': 'binary:logistic',
            'eval_metric': 'auc',
            'tree_method': 'hist',
            'max_depth': 3,
            'learning_rate': 0.01,
            'subsample': 0.8,
            'colsample_bytree': 0.6,
            'min_child_weight': 50,
            'reg_alpha': 2.0,
            'reg_lambda': 10.0,
            'seed': 42 + i,
        }

        model = xgb.train(
            params, dtrain, num_boost_round=300,
            evals=[(dtest, 'test')],
            early_stopping_rounds=20,
            verbose_eval=False,
        )

        proba = model.predict(dtest)
        auc = roc_auc_score(y_test, proba)
        acc = accuracy_score(y_test, (proba > 0.5).astype(int))

        results.append({
            'fold': i,
            'train_size': len(train),
            'test_size': len(test),
            'auc': auc,
            'accuracy': acc,
            'test_start': str(test.index[0]),
            'test_end': str(test.index[-1]),
        })

    return results


def train_final_model(df, feature_cols, label_col, train_pct=0.7):
    """Train final model with early stopping on last 30% as val/OOS."""
    valid = df.dropna(subset=[label_col] + feature_cols)
    n = len(valid)

    train_end = int(n * train_pct)
    val_end = int(n * 0.85)

    train = valid.iloc[:train_end]
    val = valid.iloc[train_end+5:val_end]  # 5-day purge
    oos = valid.iloc[val_end+5:]  # 5-day purge

    X_train, y_train = train[feature_cols].values, train[label_col].values
    X_val, y_val = val[feature_cols].values, val[label_col].values
    X_oos, y_oos = oos[feature_cols].values, oos[label_col].values

    dtrain = xgb.DMatrix(X_train, label=y_train, feature_names=feature_cols)
    dval = xgb.DMatrix(X_val, label=y_val, feature_names=feature_cols)
    doos = xgb.DMatrix(X_oos, label=y_oos, feature_names=feature_cols)

    params = {
        'objective': 'binary:logistic',
        'eval_metric': 'auc',
        'tree_method': 'hist',
        'max_depth': 3,
        'learning_rate': 0.005,
        'subsample': 0.8,
        'colsample_bytree': 0.6,
        'min_child_weight': 50,
        'reg_alpha': 2.0,
        'reg_lambda': 10.0,
        'seed': 42,
    }

    model = xgb.train(
        params, dtrain, num_boost_round=1000,
        evals=[(dtrain, 'train'), (dval, 'val')],
        early_stopping_rounds=50,
        verbose_eval=100,
    )

    val_proba = model.predict(dval)
    oos_proba = model.predict(doos)

    val_auc = roc_auc_score(y_val, val_proba)
    oos_auc = roc_auc_score(y_oos, oos_proba)
    oos_acc = accuracy_score(y_oos, (oos_proba > 0.5).astype(int))

    # Confidence gating
    gating = {}
    for t in [0.50, 0.52, 0.55, 0.58, 0.60, 0.65, 0.70]:
        mask = (oos_proba > t) | (oos_proba < (1 - t))
        if mask.sum() >= 20:
            g_acc = accuracy_score(y_oos[mask], (oos_proba[mask] > 0.5).astype(int))
            gating[str(t)] = {
                'n_trades': int(mask.sum()),
                'trade_rate': float(mask.mean()),
                'accuracy': float(g_acc),
            }

    # Top features
    importance = model.get_score(importance_type='total_gain')
    top_feats = sorted(importance.items(), key=lambda x: -x[1])[:10]

    return {
        'val_auc': float(val_auc),
        'oos_auc': float(oos_auc),
        'oos_accuracy': float(oos_acc),
        'oos_samples': len(oos),
        'best_iter': model.best_iteration,
        'top_features': top_feats,
        'confidence_gating': gating,
        'train_period': f"{train.index[0]} to {train.index[-1]}",
        'oos_period': f"{oos.index[0]} to {oos.index[-1]}",
    }, model, oos_proba, y_oos


# ============================================================
# APPROACH 1: DAILY DIRECTION (frequency-matched)
# ============================================================

def approach_daily_direction(daily, features, labels):
    """Simple: predict next N day direction at daily frequency."""
    print("\n" + "="*70)
    print("APPROACH 1: DAILY DIRECTION (frequency-matched features)")
    print("="*70)

    results = {}
    for label in ['dir_1d', 'dir_3d', 'dir_5d', 'dir_10d', 'dir_20d']:
        df = pd.concat([features, labels[[label]]], axis=1)
        feature_cols = [c for c in features.columns if not c.startswith('ret_')]

        # Quick walk-forward check
        wf = purged_walk_forward(df, feature_cols, label, n_splits=4)
        if not wf:
            continue

        mean_auc = np.mean([r['auc'] for r in wf])
        mean_acc = np.mean([r['accuracy'] for r in wf])

        print(f"\n  {label}: WF mean AUC={mean_auc:.4f}, Acc={mean_acc:.4f}")
        for r in wf:
            print(f"    Fold {r['fold']}: AUC={r['auc']:.4f}, Acc={r['accuracy']:.4f} ({r['test_start'][:10]} to {r['test_end'][:10]})")

        # Train final if promising
        if mean_auc > 0.52:
            print(f"  → Training final model for {label}...")
            final, model, proba, y_true = train_final_model(df, feature_cols, label)
            results[label] = final
            print(f"    Val AUC: {final['val_auc']:.4f}")
            print(f"    OOS AUC: {final['oos_auc']:.4f}")
            print(f"    OOS Acc: {final['oos_accuracy']:.4f}")
            print(f"    Gating:")
            for t, g in final['confidence_gating'].items():
                print(f"      >{t}: {g['n_trades']} trades, acc={g['accuracy']:.4f}")
        else:
            results[label] = {'wf_mean_auc': mean_auc, 'wf_mean_acc': mean_acc, 'skipped': True}

    return results


# ============================================================
# APPROACH 2: BIG MOVES ONLY
# ============================================================

def approach_big_moves(daily, features, labels):
    """Only predict significant moves (>1 ATR). Higher signal, fewer trades."""
    print("\n" + "="*70)
    print("APPROACH 2: BIG MOVES ONLY (predict large directional moves)")
    print("="*70)

    results = {}
    for label in ['big_up_5d', 'big_up_10d', 'big_down_5d', 'big_down_10d']:
        df = pd.concat([features, labels[[label]]], axis=1)
        feature_cols = list(features.columns)

        # Check class balance
        valid = df.dropna(subset=[label])
        pos_rate = valid[label].mean()
        print(f"\n  {label}: positive rate = {pos_rate:.3f} ({int(pos_rate*len(valid))}/{len(valid)})")

        if pos_rate < 0.05 or pos_rate > 0.95:
            print(f"    Too imbalanced, skipping")
            continue

        wf = purged_walk_forward(df, feature_cols, label, n_splits=4)
        if not wf:
            continue

        mean_auc = np.mean([r['auc'] for r in wf])
        mean_acc = np.mean([r['accuracy'] for r in wf])
        print(f"  WF mean AUC={mean_auc:.4f}, Acc={mean_acc:.4f}")

        if mean_auc > 0.53:
            print(f"  → Training final model for {label}...")
            final, model, proba, y_true = train_final_model(df, feature_cols, label)
            results[label] = final
            print(f"    OOS AUC: {final['oos_auc']:.4f}, Acc: {final['oos_accuracy']:.4f}")
            print(f"    Gating:")
            for t, g in final['confidence_gating'].items():
                print(f"      >{t}: {g['n_trades']} trades, acc={g['accuracy']:.4f}")

    return results


# ============================================================
# APPROACH 3: REGIME-FILTERED DIRECTION
# ============================================================

def approach_regime_filtered(daily, features, labels):
    """Only predict direction when market is in a trending regime."""
    print("\n" + "="*70)
    print("APPROACH 3: REGIME-FILTERED (only trade in trending markets)")
    print("="*70)

    results = {}

    # Filter to trending regime
    trending_mask = features['regime_trending'] == 1
    trending_pct = trending_mask.mean()
    print(f"  Trending regime: {trending_pct:.1%} of days ({int(trending_mask.sum())} days)")

    # Also try volatile regime
    volatile_mask = features['regime_volatile'] == 1
    print(f"  Volatile regime: {volatile_mask.mean():.1%} of days")

    for regime_name, mask in [('trending', trending_mask), ('volatile', volatile_mask)]:
        print(f"\n  --- Regime: {regime_name} ---")

        for label in ['dir_3d', 'dir_5d', 'dir_10d']:
            df_full = pd.concat([features, labels[[label]]], axis=1)
            df = df_full[mask].copy()

            if len(df) < 200:
                print(f"    {label}: too few samples ({len(df)})")
                continue

            feature_cols = [c for c in features.columns if c not in ['regime_trending', 'regime_volatile']]

            wf = purged_walk_forward(df, feature_cols, label, n_splits=3)
            if not wf:
                continue

            mean_auc = np.mean([r['auc'] for r in wf])
            mean_acc = np.mean([r['accuracy'] for r in wf])
            key = f"{regime_name}_{label}"
            print(f"    {label}: WF AUC={mean_auc:.4f}, Acc={mean_acc:.4f}")

            if mean_auc > 0.53:
                print(f"    → Training final model...")
                final, model, proba, y_true = train_final_model(df, feature_cols, label)
                results[key] = final
                print(f"      OOS AUC: {final['oos_auc']:.4f}, Acc: {final['oos_accuracy']:.4f}")
                for t, g in final['confidence_gating'].items():
                    if g['accuracy'] > 0.58:
                        print(f"      >{t}: {g['n_trades']} trades, ACC={g['accuracy']:.4f} ***")

    return results


# ============================================================
# APPROACH 4: WEEKLY HORIZON (less efficient market)
# ============================================================

def approach_weekly(daily, features, labels):
    """Weekly bars — markets less efficient at longer horizons."""
    print("\n" + "="*70)
    print("APPROACH 4: WEEKLY HORIZON (less efficient timeframe)")
    print("="*70)

    # Resample features to weekly (take Friday values)
    weekly_feat = features.resample('W-FRI').last().dropna(how='all')
    weekly_labels = labels.resample('W-FRI').last()

    # Add weekly-specific features
    weekly_close = daily['close'].resample('W-FRI').last()
    weekly_feat['ret_1w'] = weekly_close.pct_change(1)
    weekly_feat['ret_2w'] = weekly_close.pct_change(2)
    weekly_feat['ret_4w'] = weekly_close.pct_change(4)

    # Weekly label: next week direction
    weekly_fwd = weekly_close.shift(-1) / weekly_close - 1
    weekly_labels['dir_1w'] = (weekly_fwd > 0).astype(float)
    weekly_fwd_2w = weekly_close.shift(-2) / weekly_close - 1
    weekly_labels['dir_2w'] = (weekly_fwd_2w > 0).astype(float)

    results = {}
    for label in ['dir_1w', 'dir_2w']:
        if label not in weekly_labels.columns:
            continue

        df = pd.concat([weekly_feat, weekly_labels[[label]]], axis=1)
        feature_cols = list(weekly_feat.columns)

        valid = df.dropna(subset=[label] + feature_cols)
        print(f"\n  {label}: {len(valid)} weekly samples, pos_rate={valid[label].mean():.3f}")

        if len(valid) < 150:
            print(f"    Too few samples")
            continue

        wf = purged_walk_forward(df, feature_cols, label, n_splits=3, purge_days=2)
        if not wf:
            continue

        mean_auc = np.mean([r['auc'] for r in wf])
        mean_acc = np.mean([r['accuracy'] for r in wf])
        print(f"  WF mean AUC={mean_auc:.4f}, Acc={mean_acc:.4f}")

        if mean_auc > 0.52:
            final, model, proba, y_true = train_final_model(df, feature_cols, label, train_pct=0.65)
            results[label] = final
            print(f"    OOS AUC: {final['oos_auc']:.4f}, Acc: {final['oos_accuracy']:.4f}")
            for t, g in final['confidence_gating'].items():
                if g['accuracy'] > 0.55:
                    print(f"      >{t}: {g['n_trades']} trades, ACC={g['accuracy']:.4f}")

    return results


# ============================================================
# APPROACH 5: H4 TIMEFRAME (compromise between M5 noise and daily slowness)
# ============================================================

def approach_h4(h4, cross, macro, cot):
    """H4 bars — more data than daily, less noise than M5."""
    print("\n" + "="*70)
    print("APPROACH 5: H4 TIMEFRAME (6 bars/day, ~15K samples)")
    print("="*70)

    close = h4['close']
    high = h4['high']
    low = h4['low']
    volume = h4['tick_volume']

    f = pd.DataFrame(index=h4.index)

    # Momentum
    f['ret_1bar'] = close.pct_change(1)
    f['ret_6bar'] = close.pct_change(6)  # 1 day
    f['ret_30bar'] = close.pct_change(30)  # 5 days

    # Trend
    for p in [20, 50, 120]:
        sma = close.rolling(p).mean()
        f[f'sma{p}_pos'] = (close - sma) / sma

    # Vol
    tr = pd.concat([high - low, (high - close.shift(1)).abs(), (low - close.shift(1)).abs()], axis=1).max(axis=1)
    f['atr_14'] = tr.rolling(14).mean() / close
    f['atr_6'] = tr.rolling(6).mean() / close
    f['vol_ratio'] = f['atr_6'] / f['atr_14'].replace(0, np.nan)

    # RSI
    f['rsi_14'] = compute_rsi(close, 14)

    # Volume
    f['vol_ratio_bar'] = volume / volume.rolling(30).mean().replace(0, np.nan)

    # Time
    f['cos_hour'] = np.cos(2 * np.pi * h4.index.hour / 24)
    f['cos_dow'] = np.cos(2 * np.pi * h4.index.dayofweek / 5)

    # Cross-asset (daily, lagged)
    cross_daily = cross.reindex(h4.index.normalize(), method='ffill')
    cross_daily.index = h4.index  # align
    cross_daily = cross_daily.shift(6)  # lag 1 day (6 H4 bars)

    if 'dxy' in cross_daily.columns:
        f['dxy_ret_1d'] = cross_daily['dxy'].pct_change(6)
    if 'vix' in cross_daily.columns:
        f['vix'] = cross_daily['vix']

    # Labels
    for bars, name in [(6, '1d'), (18, '3d'), (30, '5d')]:
        fwd = close.shift(-bars) / close - 1
        f[f'label_{name}'] = (fwd > 0).astype(float)

    # Drop warmup
    f = f.iloc[200:]

    feature_cols = [c for c in f.columns if not c.startswith('label_')]
    results = {}

    for label in ['label_1d', 'label_3d', 'label_5d']:
        valid = f.dropna(subset=[label] + feature_cols)
        print(f"\n  {label}: {len(valid)} samples, pos={valid[label].mean():.3f}")

        wf = purged_walk_forward(valid, feature_cols, label, n_splits=4, purge_days=12)
        if not wf:
            continue

        mean_auc = np.mean([r['auc'] for r in wf])
        mean_acc = np.mean([r['accuracy'] for r in wf])
        print(f"  WF AUC={mean_auc:.4f}, Acc={mean_acc:.4f}")

        if mean_auc > 0.52:
            final, model, proba, y_true = train_final_model(valid, feature_cols, label)
            results[label] = final
            print(f"    OOS AUC: {final['oos_auc']:.4f}, Acc: {final['oos_accuracy']:.4f}")
            for t, g in final['confidence_gating'].items():
                if g['accuracy'] > 0.55:
                    print(f"      >{t}: {g['n_trades']} trades, ACC={g['accuracy']:.4f}")

    return results


# ============================================================
# APPROACH 6: RANDOM FOREST (different algo, less prone to overfit)
# ============================================================

def approach_random_forest(features, labels):
    """RF with heavy regularization — sometimes finds different patterns than XGB."""
    print("\n" + "="*70)
    print("APPROACH 6: RANDOM FOREST (different inductive bias)")
    print("="*70)

    results = {}
    for label in ['dir_5d', 'dir_10d', 'dir_20d']:
        df = pd.concat([features, labels[[label]]], axis=1)
        feature_cols = list(features.columns)
        valid = df.dropna(subset=[label] + feature_cols)

        n = len(valid)
        train_end = int(n * 0.7)
        val_end = int(n * 0.85)

        train = valid.iloc[:train_end]
        oos = valid.iloc[val_end+5:]

        X_train, y_train = train[feature_cols].values, train[label].values
        X_oos, y_oos = oos[feature_cols].values, oos[label].values

        rf = RandomForestClassifier(
            n_estimators=500,
            max_depth=5,
            min_samples_leaf=50,
            max_features=0.3,
            random_state=42,
            n_jobs=-1,
        )
        rf.fit(X_train, y_train)

        proba = rf.predict_proba(X_oos)[:, 1]
        auc = roc_auc_score(y_oos, proba)
        acc = accuracy_score(y_oos, (proba > 0.5).astype(int))

        print(f"  {label}: OOS AUC={auc:.4f}, Acc={acc:.4f}")

        # Gating
        for t in [0.55, 0.60, 0.65]:
            mask = (proba > t) | (proba < (1-t))
            if mask.sum() >= 20:
                g_acc = accuracy_score(y_oos[mask], (proba[mask] > 0.5).astype(int))
                print(f"    >{t}: {mask.sum()} trades, acc={g_acc:.4f}")

        results[label] = {'oos_auc': float(auc), 'oos_accuracy': float(acc)}

    return results


# ============================================================
# MAIN
# ============================================================

def main():
    print("="*70)
    print("FULL ASSAULT: Finding 60%+ win rate on XAU/USD")
    print("="*70)

    # Load data
    print("\nLoading data...")
    daily = load_xau_daily()
    h4 = load_xau_h4()
    cross = load_cross_asset()
    macro = load_macro()
    cot = load_cot()

    print(f"  Daily: {len(daily)} bars ({daily.index.min().date()} to {daily.index.max().date()})")
    print(f"  H4: {len(h4)} bars")
    print(f"  Cross-asset: {len(cross)} days")
    print(f"  Macro: {len(macro)} days")
    print(f"  COT: {len(cot)} weeks")

    # Build daily features
    print("\nBuilding daily features...")
    features = build_daily_features(daily, cross, macro, cot)
    features = detect_regimes(daily, features)

    # Drop warmup
    features = features.iloc[250:]
    daily = daily.loc[features.index]

    # Make labels
    labels = make_labels(daily)

    # Drop any remaining NaN in features
    valid_mask = features.notna().all(axis=1)
    features = features[valid_mask]
    labels = labels.loc[features.index]
    daily = daily.loc[features.index]

    print(f"\nFinal daily dataset: {len(features)} samples × {len(features.columns)} features")
    print(f"Date range: {features.index.min().date()} to {features.index.max().date()}")

    all_results = {
        'timestamp': datetime.now().isoformat(),
        'n_daily_samples': len(features),
        'n_features': len(features.columns),
    }

    # Run all approaches
    all_results['approach_1_daily_direction'] = approach_daily_direction(daily, features, labels)
    all_results['approach_2_big_moves'] = approach_big_moves(daily, features, labels)
    all_results['approach_3_regime_filtered'] = approach_regime_filtered(daily, features, labels)
    all_results['approach_4_weekly'] = approach_weekly(daily, features, labels)
    all_results['approach_5_h4'] = approach_h4(h4, cross, macro, cot)
    all_results['approach_6_random_forest'] = approach_random_forest(features, labels)

    # Save
    with open(OUTPUT_DIR / "fullassault_results.json", 'w') as f:
        json.dump(all_results, f, indent=2, default=str)

    # FINAL SUMMARY
    print("\n\n" + "="*70)
    print("FINAL SUMMARY — ALL APPROACHES")
    print("="*70)

    best_result = None
    best_acc = 0.5

    for approach_name, approach_results in all_results.items():
        if not isinstance(approach_results, dict) or approach_name in ['timestamp', 'n_daily_samples', 'n_features']:
            continue

        print(f"\n{approach_name}:")
        for label, res in approach_results.items():
            if isinstance(res, dict) and 'oos_accuracy' in res:
                acc = res['oos_accuracy']
                auc = res.get('oos_auc', 0)
                marker = " ★★★" if acc >= 0.60 else " ★★" if acc >= 0.55 else ""
                print(f"  {label}: AUC={auc:.4f}, Acc={acc:.4f}{marker}")

                if acc > best_acc:
                    best_acc = acc
                    best_result = (approach_name, label, res)

                # Check gating
                if 'confidence_gating' in res:
                    for t, g in res['confidence_gating'].items():
                        if g['accuracy'] >= 0.60 and g['n_trades'] >= 20:
                            print(f"    GATED >{t}: {g['n_trades']} trades, ACC={g['accuracy']:.4f} ★★★")
                            if g['accuracy'] > best_acc:
                                best_acc = g['accuracy']
                                best_result = (approach_name, f"{label}_gated_{t}", g)

    print(f"\n{'='*70}")
    if best_result:
        print(f"BEST OVERALL: {best_result[0]} / {best_result[1]}")
        print(f"  Accuracy: {best_acc:.4f} ({best_acc*100:.1f}%)")
    else:
        print("NO APPROACH ACHIEVED >50% ACCURACY")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
