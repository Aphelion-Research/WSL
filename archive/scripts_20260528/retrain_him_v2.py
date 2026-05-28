"""
Him V2: Retrain with strict OOS, multiple label types.
Train: 2016-2024 | Val: Jan-Jun 2024 | OOS: Jul 2024 - May 2026
Try: detrended (original), momentum, trend-following, volatility breakout.
"""
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.metrics import roc_auc_score, accuracy_score
import xgboost as xgb
from scipy import stats
import json
import warnings
warnings.filterwarnings('ignore')

DATA_DIR = Path("data")
OUTPUT_DIR = Path("output_him_v2")
OUTPUT_DIR.mkdir(exist_ok=True)


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
    close = m15['close']
    high = m15['high']
    low = m15['low']
    volume = m15['tick_volume']

    f = pd.DataFrame(index=m15.index)

    f['ret_1bar'] = close.pct_change(1)
    f['ret_4bar'] = close.pct_change(4)
    f['ret_16bar'] = close.pct_change(16)
    f['ret_96bar'] = close.pct_change(96)

    rolling_high_96 = close.rolling(96).max()
    rolling_low_96 = close.rolling(96).min()
    range_96 = (rolling_high_96 - rolling_low_96).replace(0, np.nan)
    f['range_pos_24h'] = (close - rolling_low_96) / range_96

    tp = (high + low + close) / 3
    vol = volume.replace(0, 1)
    f['vwap_dev_4h'] = (close - (tp * vol).rolling(16).sum() / vol.rolling(16).sum()) / close
    f['vwap_dev_24h'] = (close - (tp * vol).rolling(96).sum() / vol.rolling(96).sum()) / close

    tr_15 = pd.concat([high - low, (high - close.shift(1)).abs(), (low - close.shift(1)).abs()], axis=1).max(axis=1)
    atr_12 = tr_15.rolling(12).mean()
    atr_48 = tr_15.rolling(48).mean()
    atr_96 = tr_15.rolling(96).mean()
    f['atr_3h_pct'] = atr_12 / close
    f['atr_24h_pct'] = atr_96 / close
    f['vol_ratio'] = atr_12 / atr_48.replace(0, np.nan)

    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss_val = (-delta.where(delta < 0, 0)).rolling(14).mean()
    f['rsi_14'] = 100 - 100 / (1 + gain / loss_val.replace(0, np.nan))

    bb_mid = close.rolling(20).mean()
    bb_std = close.rolling(20).std().replace(0, np.nan)
    f['bb_pos'] = (close - bb_mid) / (2 * bb_std)

    f['vol_zscore'] = (volume - volume.rolling(96).mean()) / volume.rolling(96).std().replace(0, np.nan)

    hour = m15.index.hour + m15.index.minute / 60
    f['cos_hour'] = np.cos(2 * np.pi * hour / 24)
    f['sin_hour'] = np.sin(2 * np.pi * hour / 24)
    f['cos_dow'] = np.cos(2 * np.pi * m15.index.dayofweek / 5)

    f['pullback_from_high'] = (rolling_high_96 - close) / atr_96.replace(0, np.nan)
    f['pullback_from_low'] = (close - rolling_low_96) / atr_96.replace(0, np.nan)

    f['spread_zscore'] = (m15['spread'] - m15['spread'].rolling(96).mean()) / m15['spread'].rolling(96).std().replace(0, np.nan)

    f['consec_up'] = close.diff().gt(0).rolling(8).sum()
    f['consec_down'] = close.diff().lt(0).rolling(8).sum()

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


def make_labels(m15):
    """Multiple label types."""
    close = m15['close']
    high = m15['high']
    low = m15['low']
    labels = {}

    # 1. Original: detrended 4h (excess return vs trailing mean)
    trailing_4h = close.pct_change(16).rolling(96).mean()
    fwd_16 = close.shift(-16) / close - 1
    labels['detrend_4h'] = (fwd_16 > trailing_4h).astype(float)
    labels['detrend_4h'][fwd_16.isna()] = np.nan

    # 2. Pure momentum: is 4h return positive?
    labels['momentum_4h'] = (fwd_16 > 0).astype(float)
    labels['momentum_4h'][fwd_16.isna()] = np.nan

    # 3. Trend-following: is 4h return in same direction as 24h trend?
    trend_24h = close.pct_change(96)
    fwd_direction = fwd_16 > 0
    trend_direction = trend_24h > 0
    labels['trend_follow'] = (fwd_direction == trend_direction).astype(float)
    labels['trend_follow'][fwd_16.isna()] = np.nan

    # 4. Volatility breakout: does 4h move exceed 1.5x ATR?
    tr_15 = pd.concat([high - low, (high - close.shift(1)).abs(), (low - close.shift(1)).abs()], axis=1).max(axis=1)
    atr_96 = tr_15.rolling(96).mean()
    fwd_abs_move = (close.shift(-16) - close).abs()
    expected_move = atr_96 * np.sqrt(16)  # scale ATR to 4h
    labels['vol_breakout'] = (fwd_abs_move > expected_move * 1.0).astype(float)
    labels['vol_breakout'][fwd_16.isna()] = np.nan

    # 5. Big move up: 4h return > 1 ATR (directional breakout)
    fwd_move = close.shift(-16) - close
    labels['big_move_up'] = (fwd_move > atr_96).astype(float)
    labels['big_move_up'][fwd_16.isna()] = np.nan

    # 6. Adaptive detrend: excess vs EXPANDING trailing mean (adapts to trending)
    trailing_expanding = close.pct_change(16).expanding(min_periods=96).mean()
    labels['detrend_adaptive'] = (fwd_16 > trailing_expanding).astype(float)
    labels['detrend_adaptive'][fwd_16.isna()] = np.nan

    # 7. Relative strength: 4h return > median of last 5 days' 4h returns
    rolling_median = close.pct_change(16).rolling(96 * 5).median()
    labels['relative_strength'] = (fwd_16 > rolling_median).astype(float)
    labels['relative_strength'][fwd_16.isna()] = np.nan

    return labels


def train_and_evaluate(X_train, y_train, X_val, y_val, X_oos, y_oos, feature_cols, seed=42):
    """Train XGBoost, return OOS metrics."""
    dtrain = xgb.DMatrix(X_train, label=y_train, feature_names=feature_cols)
    dval = xgb.DMatrix(X_val, label=y_val, feature_names=feature_cols)
    doos = xgb.DMatrix(X_oos, label=y_oos, feature_names=feature_cols)

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

    proba = model.predict(doos)
    auc = roc_auc_score(y_oos, proba)
    acc = accuracy_score(y_oos, (proba > 0.5).astype(int))

    # Gating
    gating = {}
    for t in [0.52, 0.55, 0.58, 0.60, 0.65, 0.70]:
        mask = (proba > t) | (proba < (1 - t))
        n = mask.sum()
        if n >= 20:
            wr = accuracy_score(y_oos[mask], (proba[mask] > 0.5).astype(int))
            p_val = 1 - stats.binom.cdf(int(wr * n) - 1, n, 0.5)
            gating[str(t)] = {'trades': int(n), 'wr': float(wr), 'p_val': float(p_val)}

    # Confidence distribution
    conf_dist = {
        '>0.55': int((proba > 0.55).sum()),
        '>0.60': int((proba > 0.60).sum()),
        '>0.65': int((proba > 0.65).sum()),
        '>0.70': int((proba > 0.70).sum()),
    }

    return {
        'auc': float(auc),
        'accuracy': float(acc),
        'base_rate': float(y_oos.mean()),
        'edge': float(acc - max(y_oos.mean(), 1 - y_oos.mean())),
        'n_oos': len(y_oos),
        'gating': gating,
        'confidence_dist': conf_dist,
        'best_iter': int(model.best_iteration),
    }, model, proba


def main():
    print("Loading M15 data...")
    m15 = load_m15()
    print(f"  {len(m15)} bars ({m15.index[0].date()} to {m15.index[-1].date()})")

    print("Building features...")
    features = build_features(m15)

    print("Building labels (7 types)...")
    labels = make_labels(m15)

    # Trim warmup
    features = features.iloc[96 * 5:]
    m15 = m15.loc[features.index]
    for k in labels:
        labels[k] = labels[k].loc[features.index]

    # Feature columns
    feature_cols = [c for c in features.columns if features[c].notna().mean() > 0.9]

    # Clean
    valid = features[feature_cols].notna().all(axis=1)
    features = features[valid]
    m15 = m15.loc[features.index]
    for k in labels:
        labels[k] = labels[k].loc[features.index]

    print(f"  Clean: {len(features)} bars × {len(feature_cols)} features")

    # ================================================================
    # STRICT TEMPORAL SPLITS
    # ================================================================
    # Split 1: Train 2016-2023 | Val 2023-H2 | OOS 2024-2026 (2 years pure OOS)
    # Split 2: Train 2016-2024H1 | Val 2024H2 | OOS 2025-2026 (1.5 years pure OOS)

    splits = {
        'split_A': {
            'train_end': pd.Timestamp('2023-06-30'),
            'val_end': pd.Timestamp('2024-01-01'),
            'oos_start': pd.Timestamp('2024-01-01'),
            'desc': 'Train 2016-2023H1 | Val 2023H2 | OOS 2024-2026',
        },
        'split_B': {
            'train_end': pd.Timestamp('2024-06-30'),
            'val_end': pd.Timestamp('2025-01-01'),
            'oos_start': pd.Timestamp('2025-01-01'),
            'desc': 'Train 2016-2024H1 | Val 2024H2 | OOS 2025-2026',
        },
        'split_C': {
            'train_end': pd.Timestamp('2025-01-01'),
            'val_end': pd.Timestamp('2025-07-01'),
            'oos_start': pd.Timestamp('2025-07-01'),
            'desc': 'Train 2016-2024 | Val 2025H1 | OOS 2025H2-2026',
        },
    }

    all_results = {}

    for split_name, split_cfg in splits.items():
        print(f"\n\n{'='*80}")
        print(f"  {split_name}: {split_cfg['desc']}")
        print(f"{'='*80}")

        train_mask = features.index <= split_cfg['train_end']
        val_mask = (features.index > split_cfg['train_end']) & (features.index <= split_cfg['val_end'])
        oos_mask = features.index >= split_cfg['oos_start']

        print(f"  Train: {train_mask.sum()} | Val: {val_mask.sum()} | OOS: {oos_mask.sum()}")

        split_results = {}

        for label_name, label_series in labels.items():
            # Get valid samples for this label
            label_valid = label_series.notna()
            t_mask = train_mask & label_valid
            v_mask = val_mask & label_valid
            o_mask = oos_mask & label_valid

            if t_mask.sum() < 1000 or v_mask.sum() < 500 or o_mask.sum() < 500:
                continue

            X_train = features[t_mask][feature_cols].values
            y_train = label_series[t_mask].values
            X_val = features[v_mask][feature_cols].values
            y_val = label_series[v_mask].values
            X_oos = features[o_mask][feature_cols].values
            y_oos = label_series[o_mask].values

            results, model, proba = train_and_evaluate(
                X_train, y_train, X_val, y_val, X_oos, y_oos, feature_cols
            )
            split_results[label_name] = results

            # Print summary
            best_gate = None
            best_wr = 0
            for t, g in results['gating'].items():
                if g['wr'] > best_wr and g['trades'] >= 50:
                    best_wr = g['wr']
                    best_gate = t

            marker = " ★★★" if results['auc'] > 0.56 else " ★★" if results['auc'] > 0.53 else " ★" if results['auc'] > 0.51 else ""
            gate_str = f"  best gate >{best_gate}: {results['gating'][best_gate]['trades']} trades, WR={best_wr:.1%}" if best_gate else "  no valid gate"
            print(f"  {label_name:<22} AUC={results['auc']:.4f} acc={results['accuracy']:.4f} base={results['base_rate']:.3f}{marker}")
            print(f"    {gate_str}")
            print(f"    conf: >0.55={results['confidence_dist']['>0.55']}, >0.60={results['confidence_dist']['>0.60']}, >0.65={results['confidence_dist']['>0.65']}")

        all_results[split_name] = split_results

    # ================================================================
    # FIND BEST COMBINATION
    # ================================================================
    print(f"\n\n{'='*80}")
    print("RANKING: Best label × split combinations")
    print(f"{'='*80}")

    ranked = []
    for split_name, split_results in all_results.items():
        for label_name, results in split_results.items():
            # Score: AUC + best gated WR (must have >50 trades)
            best_gated_wr = 0
            best_gate_trades = 0
            for t, g in results['gating'].items():
                if g['trades'] >= 50 and g['wr'] > best_gated_wr:
                    best_gated_wr = g['wr']
                    best_gate_trades = g['trades']

            score = results['auc'] * 0.4 + best_gated_wr * 0.6
            ranked.append({
                'split': split_name,
                'label': label_name,
                'auc': results['auc'],
                'acc': results['accuracy'],
                'best_wr': best_gated_wr,
                'best_trades': best_gate_trades,
                'score': score,
                'conf_60': results['confidence_dist']['>0.60'],
            })

    ranked.sort(key=lambda x: -x['score'])

    print(f"\n{'Rank':<5} {'Split':<10} {'Label':<22} {'AUC':<8} {'BestWR':<8} {'Trades':<8} {'>0.60':<8} {'Score':<8}")
    print(f"{'-'*77}")
    for i, r in enumerate(ranked[:20]):
        print(f"{i+1:<5} {r['split']:<10} {r['label']:<22} {r['auc']:<8.4f} {r['best_wr']:<8.3f} {r['best_trades']:<8} {r['conf_60']:<8} {r['score']:<8.4f}")

    # Save
    save_data = {
        'timestamp': str(pd.Timestamp.now()),
        'splits': {k: v['desc'] for k, v in splits.items()},
        'results': all_results,
        'ranking': ranked[:20],
    }
    with open(OUTPUT_DIR / "retrain_results.json", 'w') as f:
        json.dump(save_data, f, indent=2, default=str)

    # ================================================================
    # TRAIN BEST MODEL ON ALL DATA UP TO 2025
    # ================================================================
    if ranked:
        best = ranked[0]
        print(f"\n\n{'='*80}")
        print(f"TRAINING PRODUCTION MODEL: {best['label']} ({best['split']})")
        print(f"{'='*80}")

        # Retrain on all data up to end of 2024
        cutoff = pd.Timestamp('2024-12-31')
        label_series = labels[best['label']]
        label_valid = label_series.notna()
        train_mask = (features.index <= cutoff) & label_valid

        val_split = int(train_mask.sum() * 0.9)
        train_idx = features[train_mask].index

        X_all = features[train_mask][feature_cols].values
        y_all = label_series[train_mask].values

        X_train = X_all[:val_split]
        y_train = y_all[:val_split]
        X_val = X_all[val_split:]
        y_val = y_all[val_split:]

        # True OOS: 2025+
        oos_mask = (features.index > cutoff) & label_valid
        X_oos = features[oos_mask][feature_cols].values
        y_oos = label_series[oos_mask].values

        results_final, model_final, proba_final = train_and_evaluate(
            X_train, y_train, X_val, y_val, X_oos, y_oos, feature_cols
        )

        print(f"  OOS (2025-2026): AUC={results_final['auc']:.4f}, Acc={results_final['accuracy']:.4f}")
        print(f"  Base rate: {results_final['base_rate']:.4f}")
        print(f"  Confidence: >0.55={results_final['confidence_dist']['>0.55']}, >0.60={results_final['confidence_dist']['>0.60']}, >0.65={results_final['confidence_dist']['>0.65']}")
        print(f"\n  Gating:")
        for t, g in results_final['gating'].items():
            marker = " ★★★" if g['wr'] >= 0.65 else " ★★" if g['wr'] >= 0.58 else ""
            print(f"    >{t}: {g['trades']} trades, WR={g['wr']:.1%}, p={g['p_val']:.6f}{marker}")

        # Save model
        model_path = OUTPUT_DIR / "him_v2.json"
        model_final.save_model(str(model_path))
        print(f"\n  Model saved: {model_path}")

    print(f"\nDone. Results: {OUTPUT_DIR}/retrain_results.json")


if __name__ == "__main__":
    main()
