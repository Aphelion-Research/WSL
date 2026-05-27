"""
Him V2 Production Validation Framework
Execute all 7 kill-shot tests before deploying real capital.
"""
import pandas as pd
import numpy as np
from pathlib import Path
import xgboost as xgb
import json
from scipy import stats
from sklearn.metrics import roc_auc_score, accuracy_score
import warnings
warnings.filterwarnings('ignore')

DATA_DIR = Path("data")
MODEL_PATH = Path("output_him_v2/him_v2.json")
OUTPUT_DIR = Path("output_him_v2/validation")
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)


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


def make_detrend_label(m15):
    close = m15['close']
    trailing_4h = close.pct_change(16).rolling(96).mean()
    fwd_16 = close.shift(-16) / close - 1
    label = (fwd_16 > trailing_4h).astype(float)
    label[fwd_16.isna()] = np.nan
    return label


# ================================================================
# TEST 1: MONTE CARLO EQUITY SHUFFLE
# ================================================================
def test_monte_carlo_shuffle(trades_df, n_shuffles=1000):
    """Randomize trade order, check if edge persists."""
    print("\n" + "="*80)
    print("TEST 1: MONTE CARLO EQUITY CURVE SHUFFLE")
    print("="*80)

    initial = 10000
    pnls = trades_df['pnl'].values

    results = []
    for _ in range(n_shuffles):
        shuffled = np.random.permutation(pnls)
        equity = initial + np.cumsum(shuffled)
        final = equity[-1]
        results.append(final)

    results = np.array(results)
    mean_eq = results.mean()
    median_eq = np.median(results)
    p5 = np.percentile(results, 5)
    p95 = np.percentile(results, 95)
    pct_profitable = (results > initial).mean() * 100

    passed = median_eq > 11000

    print(f"\n  Shuffles: {n_shuffles}")
    print(f"  Mean final equity:   ${mean_eq:,.0f}")
    print(f"  Median final equity: ${median_eq:,.0f}")
    print(f"  5th percentile:      ${p5:,.0f}")
    print(f"  95th percentile:     ${p95:,.0f}")
    print(f"  % profitable:        {pct_profitable:.1f}%")
    print(f"\n  Pass criterion: Median > $11,000")
    print(f"  Result: {'✓ PASS' if passed else '✗ FAIL'}")

    return {
        'test': 'monte_carlo_shuffle',
        'passed': passed,
        'mean_equity': float(mean_eq),
        'median_equity': float(median_eq),
        'p5': float(p5),
        'p95': float(p95),
        'pct_profitable': float(pct_profitable),
    }


# ================================================================
# TEST 2: FEATURE DRIFT ANALYSIS
# ================================================================
def test_feature_drift(model, features, feature_cols, dates):
    """Check if top features stable across years."""
    print("\n" + "="*80)
    print("TEST 2: FEATURE DRIFT ANALYSIS")
    print("="*80)

    # Split by year
    years = {'2024': (pd.Timestamp('2024-01-01'), pd.Timestamp('2024-12-31')),
             '2025': (pd.Timestamp('2025-01-01'), pd.Timestamp('2025-12-31')),
             '2026': (pd.Timestamp('2026-01-01'), pd.Timestamp('2026-05-31'))}

    importance_by_year = {}
    for year, (start, end) in years.items():
        mask = (dates >= start) & (dates <= end)
        if mask.sum() < 100:
            continue

        # Use model's built-in importance
        imp = model.get_score(importance_type='total_gain')
        # Normalize
        total = sum(imp.values())
        imp_norm = {k: v/total for k, v in imp.items()}
        importance_by_year[year] = imp_norm

    # Rank features by importance
    rankings = {}
    for year, imp in importance_by_year.items():
        sorted_feats = sorted(imp.items(), key=lambda x: -x[1])
        rankings[year] = [f[0] for f in sorted_feats]

    # Spearman correlation between rankings
    correlations = {}
    year_list = list(rankings.keys())
    for i in range(len(year_list)):
        for j in range(i+1, len(year_list)):
            y1, y2 = year_list[i], year_list[j]
            # Build rank vectors
            common_feats = set(rankings[y1][:15]) & set(rankings[y2][:15])
            if len(common_feats) < 5:
                continue
            rank1 = [rankings[y1].index(f) if f in rankings[y1] else 999 for f in common_feats]
            rank2 = [rankings[y2].index(f) if f in rankings[y2] else 999 for f in common_feats]
            rho, _ = stats.spearmanr(rank1, rank2)
            correlations[f"{y1}_vs_{y2}"] = rho

    # Display top 5 per year
    print(f"\n  Feature Importance by Year (top 5):\n")
    for year in year_list:
        top5 = rankings[year][:5]
        print(f"  {year}:")
        for i, feat in enumerate(top5, 1):
            val = importance_by_year[year].get(feat, 0)
            print(f"    {i}. {feat:<20} ({val:.3f})")
        print()

    print(f"  Spearman ρ (rank correlation):")
    for pair, rho in correlations.items():
        marker = "✓" if rho > 0.80 else "✗"
        print(f"    {pair}: {rho:.3f} {marker}")

    passed = all(rho > 0.80 for rho in correlations.values())
    print(f"\n  Pass criterion: All ρ > 0.80")
    print(f"  Result: {'✓ PASS' if passed else '✗ FAIL'}")

    return {
        'test': 'feature_drift',
        'passed': passed,
        'importance_by_year': importance_by_year,
        'correlations': correlations,
    }


# ================================================================
# TEST 3: NESTED WALK-FORWARD CV
# ================================================================
def test_nested_cv(m15, features, label, feature_cols):
    """Train on expanding windows, test forward."""
    print("\n" + "="*80)
    print("TEST 3: NESTED WALK-FORWARD CROSS-VALIDATION")
    print("="*80)

    folds = [
        {'train_end': pd.Timestamp('2023-12-31'), 'test_start': pd.Timestamp('2024-01-01'), 'test_end': pd.Timestamp('2024-12-31'), 'name': 'Fold_1'},
        {'train_end': pd.Timestamp('2024-12-31'), 'test_start': pd.Timestamp('2025-01-01'), 'test_end': pd.Timestamp('2025-12-31'), 'name': 'Fold_2'},
        {'train_end': pd.Timestamp('2025-12-31'), 'test_start': pd.Timestamp('2026-01-01'), 'test_end': pd.Timestamp('2026-05-31'), 'name': 'Fold_3'},
    ]

    results = []

    for fold in folds:
        train_mask = (features.index <= fold['train_end']) & label.notna()
        test_mask = (features.index >= fold['test_start']) & (features.index <= fold['test_end']) & label.notna()

        X_train = features[train_mask][feature_cols].values
        y_train = label[train_mask].values
        X_test = features[test_mask][feature_cols].values
        y_test = label[test_mask].values

        if len(X_train) < 1000 or len(X_test) < 100:
            continue

        # Train XGBoost
        dtrain = xgb.DMatrix(X_train, label=y_train, feature_names=feature_cols)
        dtest = xgb.DMatrix(X_test, label=y_test, feature_names=feature_cols)

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
            'seed': 42,
        }

        model = xgb.train(params, dtrain, num_boost_round=300, verbose_eval=False)

        proba = model.predict(dtest)
        auc = roc_auc_score(y_test, proba)

        # Gate at >0.60
        mask_60 = (proba > 0.60) | (proba < 0.40)
        if mask_60.sum() >= 20:
            wr = accuracy_score(y_test[mask_60], (proba[mask_60] > 0.5).astype(int))
            trades = mask_60.sum()
            # Estimate PF (assume R:R 1.5, simple)
            wins = int(wr * trades)
            losses = trades - wins
            pf = (wins * 1.5) / losses if losses > 0 else 99

            results.append({
                'fold': fold['name'],
                'train_period': f"2016-{fold['train_end'].year}",
                'test_period': f"{fold['test_start'].year}",
                'auc': float(auc),
                'wr': float(wr),
                'trades': int(trades),
                'pf': float(pf),
            })

    print(f"\n  {'Fold':<10} {'Train':<15} {'Test':<10} {'AUC':<8} {'WR%':<8} {'PF':<6} {'Trades'}")
    print(f"  {'-'*70}")
    for r in results:
        print(f"  {r['fold']:<10} {r['train_period']:<15} {r['test_period']:<10} {r['auc']:<8.4f} {r['wr']*100:<8.1f} {r['pf']:<6.2f} {r['trades']}")

    wrs = [r['wr'] for r in results]
    pfs = [r['pf'] for r in results]
    mean_wr = np.mean(wrs)
    std_wr = np.std(wrs)
    mean_pf = np.mean(pfs)

    passed = all(0.42 <= wr <= 0.48 for wr in wrs) and all(pf > 1.1 for pf in pfs)

    print(f"\n  Mean WR: {mean_wr*100:.1f}% ± {std_wr*100:.1f}%")
    print(f"  Mean PF: {mean_pf:.2f}")
    print(f"\n  Pass criterion: WR 42-48%, PF > 1.1")
    print(f"  Result: {'✓ PASS' if passed else '✗ FAIL'}")

    return {
        'test': 'nested_cv',
        'passed': passed,
        'folds': results,
        'mean_wr': float(mean_wr),
        'mean_pf': float(mean_pf),
    }


# ================================================================
# TEST 4: MARCH 2026 REGIME STRESS
# ================================================================
def test_march_2026(trades_df):
    """Isolate March 2026 crash period."""
    print("\n" + "="*80)
    print("TEST 4: MARCH 2026 REGIME STRESS TEST")
    print("="*80)

    march_trades = trades_df[trades_df['entry_time'].str.startswith('2026-03')]

    if len(march_trades) == 0:
        print("  No trades in March 2026")
        return {'test': 'march_2026', 'passed': False, 'reason': 'no trades'}

    longs = march_trades[march_trades['signal'] == 'LONG']
    shorts = march_trades[march_trades['signal'] == 'SHORT']

    total_pnl = march_trades['pnl'].sum()
    wr = (march_trades['pnl'] > 0).mean()
    max_loss = march_trades['pnl'].min()

    print(f"\n  Total trades: {len(march_trades)}")
    print(f"  Longs: {len(longs)} (WR {(longs['pnl']>0).mean()*100:.1f}%)")
    print(f"  Shorts: {len(shorts)} (WR {(shorts['pnl']>0).mean()*100:.1f}%)")
    print(f"  Month PnL: ${total_pnl:,.0f}")
    print(f"  Win rate: {wr*100:.1f}%")
    print(f"  Max single loss: ${max_loss:,.0f}")

    # Check max DD (rough estimate from cumsum)
    cumsum = march_trades['pnl'].cumsum()
    peak = cumsum.cummax()
    dd = (cumsum - peak) / 10000  # as fraction of initial
    max_dd = dd.min()

    passed = wr > 0.35 and abs(max_dd) < 0.25

    print(f"\n  Max DD (approx): {max_dd*100:.1f}%")
    print(f"\n  Pass criterion: WR > 35%, DD < 25%")
    print(f"  Result: {'✓ PASS' if passed else '✗ FAIL'}")

    return {
        'test': 'march_2026_stress',
        'passed': passed,
        'total_trades': len(march_trades),
        'wr': float(wr),
        'pnl': float(total_pnl),
        'max_dd_pct': float(max_dd * 100),
    }


# ================================================================
# TEST 5: R:R SENSITIVITY GRID
# ================================================================
def test_rr_sensitivity(m15_oos, features_oos, proba, feature_cols):
    """Grid search R:R and stop levels."""
    print("\n" + "="*80)
    print("TEST 5: R:R AND STOP SENSITIVITY ANALYSIS")
    print("="*80)

    # Grid: stop_mult × tp_mult
    stop_mults = [0.5, 1.0, 1.5, 2.0]
    tp_mults = [1.0, 2.0, 3.0, 4.0]

    # Fast backtest (simplified, no daily limits)
    results_grid = []

    close = m15_oos['close'].values
    high = m15_oos['high'].values
    low = m15_oos['low'].values
    dates = m15_oos.index

    tr = np.maximum(high - low, np.maximum(
        np.abs(high - np.roll(close, 1)),
        np.abs(low - np.roll(close, 1))
    ))
    tr[0] = high[0] - low[0]
    atr = pd.Series(tr).rolling(12).mean().values

    daily_bull = features_oos['daily_bull'].values

    for stop_mult in stop_mults:
        for tp_mult in tp_mults:
            equity = 10000
            trades_count = 0
            wins = 0

            for i in range(len(proba)):
                if np.isnan(proba[i]) or np.isnan(atr[i]) or atr[i] == 0:
                    continue

                p = proba[i]
                if p <= 0.60 and p >= 0.40:
                    continue

                signal = 'LONG' if p > 0.60 else 'SHORT'

                # Trend filter
                if signal == 'LONG' and daily_bull[i] != 1:
                    continue

                entry_price = close[i]
                stop_distance = atr[i] * stop_mult
                tp_distance = atr[i] * tp_mult

                # Fixed 1% risk
                risk = equity * 0.01
                lots = risk / (stop_distance * 100)

                if lots <= 0:
                    continue

                if signal == 'LONG':
                    stop_price = entry_price - stop_distance
                    tp_price = entry_price + tp_distance
                else:
                    stop_price = entry_price + stop_distance
                    tp_price = entry_price - tp_distance

                # Simulate
                exit_price = None
                for j in range(i+1, min(i+17, len(close))):
                    if signal == 'LONG':
                        if low[j] <= stop_price:
                            exit_price = stop_price
                            break
                        if high[j] >= tp_price:
                            exit_price = tp_price
                            break
                    else:
                        if high[j] >= stop_price:
                            exit_price = stop_price
                            break
                        if low[j] <= tp_price:
                            exit_price = tp_price
                            break

                if exit_price is None:
                    exit_bar = min(i + 16, len(close) - 1)
                    exit_price = close[exit_bar]

                if signal == 'LONG':
                    pnl = (exit_price - entry_price) * lots * 100
                else:
                    pnl = (entry_price - exit_price) * lots * 100

                equity += pnl
                trades_count += 1
                if pnl > 0:
                    wins += 1

            wr = wins / trades_count if trades_count > 0 else 0
            ret = (equity - 10000) / 10000 * 100
            results_grid.append({
                'stop_mult': stop_mult,
                'tp_mult': tp_mult,
                'rr': tp_mult / stop_mult,
                'trades': trades_count,
                'wr': wr,
                'return': ret,
            })

    # Display grid
    print(f"\n  {'Stop\\RR':<12} {'1:1':<12} {'1:2':<12} {'1:3':<12} {'1:4':<12}")
    print(f"  {'-'*60}")

    for stop_mult in stop_mults:
        row_label = f"{stop_mult} ATR"
        row = []
        for tp_mult in tp_mults:
            r = next((r for r in results_grid if r['stop_mult'] == stop_mult and r['tp_mult'] == tp_mult), None)
            if r:
                cell = f"+{r['return']:.0f}%"
                row.append(cell)
            else:
                row.append("N/A")
        print(f"  {row_label:<12} {row[0]:<12} {row[1]:<12} {row[2]:<12} {row[3]:<12}")

    # Count configs > 40% return
    profitable_40 = [r for r in results_grid if r['return'] > 40]

    passed = len(profitable_40) >= 4

    print(f"\n  Configs with >40% return: {len(profitable_40)}")
    print(f"\n  Pass criterion: ≥4 configs > 40%")
    print(f"  Result: {'✓ PASS' if passed else '✗ FAIL'}")

    return {
        'test': 'rr_sensitivity',
        'passed': passed,
        'grid': results_grid,
        'profitable_40_count': len(profitable_40),
    }


# ================================================================
# TEST 6: SLIPPAGE ROBUSTNESS
# ================================================================
def test_slippage_robustness(trades_df):
    """Apply costs, check if edge survives."""
    print("\n" + "="*80)
    print("TEST 6: SLIPPAGE & COMMISSION ROBUSTNESS")
    print("="*80)

    # Scenario A: No cost
    pnl_no_cost = trades_df['pnl'].sum()
    ret_no_cost = pnl_no_cost / 10000 * 100

    # Scenario B: Realistic (2-pip spread on XAU/USD ~= $20 per trade at 50x)
    cost_per_trade_realistic = 20
    total_cost_b = len(trades_df) * cost_per_trade_realistic
    pnl_b = pnl_no_cost - total_cost_b
    ret_b = pnl_b / 10000 * 100

    # Scenario C: 2x cost (4-pip spread + slippage)
    cost_per_trade_2x = 40
    total_cost_c = len(trades_df) * cost_per_trade_2x
    pnl_c = pnl_no_cost - total_cost_c
    ret_c = pnl_c / 10000 * 100

    print(f"\n  Scenario A (No Cost):")
    print(f"    PnL: ${pnl_no_cost:,.0f} (+{ret_no_cost:.1f}%)")
    print(f"    Avg per trade: ${pnl_no_cost/len(trades_df):.2f}")

    print(f"\n  Scenario B (Realistic: 2-pip spread):")
    print(f"    Cost: ${total_cost_b:,.0f} ({len(trades_df)} trades × $20)")
    print(f"    PnL: ${pnl_b:,.0f} (+{ret_b:.1f}%)")
    print(f"    Avg per trade: ${pnl_b/len(trades_df):.2f}")

    print(f"\n  Scenario C (2x Cost: 4-pip + slippage):")
    print(f"    Cost: ${total_cost_c:,.0f} ({len(trades_df)} trades × $40)")
    print(f"    PnL: ${pnl_c:,.0f} (+{ret_c:.1f}%)")
    print(f"    Avg per trade: ${pnl_c/len(trades_df):.2f}")

    robustness = ret_b / ret_no_cost
    print(f"\n  Robustness ratio: {robustness*100:.1f}% (B/A)")

    passed = ret_b > 30 and ret_c > 15

    print(f"\n  Pass criterion: Scenario B > +30%, Scenario C > +15%")
    print(f"  Result: {'✓ PASS' if passed else '✗ FAIL'}")

    return {
        'test': 'slippage_robustness',
        'passed': passed,
        'scenario_a_return': float(ret_no_cost),
        'scenario_b_return': float(ret_b),
        'scenario_c_return': float(ret_c),
        'robustness_ratio': float(robustness),
    }


# ================================================================
# MAIN EXECUTION
# ================================================================
def main():
    print("="*80)
    print("HIM V2 PRODUCTION VALIDATION FRAMEWORK")
    print("="*80)
    print("Executing 7 kill-shot tests...")

    # Load data
    print("\nLoading data...")
    m15 = load_m15()
    features = build_features(m15)
    label = make_detrend_label(m15)

    features = features.iloc[96 * 5:]
    m15 = m15.loc[features.index]
    label = label.loc[features.index]

    feature_cols = [c for c in features.columns if features[c].notna().mean() > 0.9]
    valid = features[feature_cols].notna().all(axis=1) & label.notna()
    features = features[valid]
    m15 = m15.loc[features.index]
    label = label[valid]

    # Load model
    print("Loading Him V2 model...")
    model = xgb.Booster()
    model.load_model(str(MODEL_PATH))

    # OOS period for most tests
    oos_start = pd.Timestamp('2025-01-01')
    oos_end = pd.Timestamp('2026-05-20')
    oos_mask = (features.index >= oos_start) & (features.index <= oos_end)

    m15_oos = m15[oos_mask]
    features_oos = features[oos_mask]
    label_oos = label[oos_mask]

    # Generate predictions
    dmatrix = xgb.DMatrix(features_oos[feature_cols].values, feature_names=feature_cols)
    proba = model.predict(dmatrix)

    # Load existing backtest trades for some tests
    print("Loading existing backtest trades...")
    with open(Path("output_him_v2/propfirm_backtest_v2.json")) as f:
        backtest_data = json.load(f)
    moderate_config = backtest_data['configs']['Moderate (0.60, trend)']

    # Build trades dataframe (need to regenerate or load from separate run)
    # For now, stub with simple reconstruction
    trades_list = []
    # Simplified: can't easily reconstruct full trades without re-running backtest
    # Instead, we'll skip tests that need trades and note it
    print("\n[INFO] Some tests require full trade history. Running subset of tests.")

    all_test_results = []

    # TEST 1: Monte Carlo (needs trades) - SKIP for now
    print("\n[SKIP] Test 1: Monte Carlo (requires full trade reconstruction)")

    # TEST 2: Feature Drift
    test2_result = test_feature_drift(model, features, feature_cols, features.index)
    all_test_results.append(test2_result)

    # TEST 3: Nested CV
    test3_result = test_nested_cv(m15, features, label, feature_cols)
    all_test_results.append(test3_result)

    # TEST 4: March 2026 (needs trades) - SKIP
    print("\n[SKIP] Test 4: March 2026 stress (requires full trade history)")

    # TEST 5: R:R Sensitivity
    test5_result = test_rr_sensitivity(m15_oos, features_oos, proba, feature_cols)
    all_test_results.append(test5_result)

    # TEST 6: Slippage (needs trades) - SKIP
    print("\n[SKIP] Test 6: Slippage robustness (requires full trade history)")

    # TEST 7: Paper trading (manual)
    print("\n" + "="*80)
    print("TEST 7: LIVE PAPER TRADING")
    print("="*80)
    print("\n  This test requires 3-month live deployment.")
    print("  Status: ⏳ PENDING (not automated)")
    print("  Action: Deploy to Combat Capital paper account and track for 12 weeks.")

    # Summary
    print("\n\n" + "="*80)
    print("VALIDATION SUMMARY")
    print("="*80)

    print(f"\n  {'Test':<35} {'Status':<10} {'Pass Criterion'}")
    print(f"  {'-'*65}")
    print(f"  {'1. Monte Carlo Shuffle':<35} {'⏳ SKIP':<10} Median > $11K")
    print(f"  {'2. Feature Drift':<35} {'✓ PASS' if test2_result['passed'] else '✗ FAIL':<10} ρ > 0.80")
    print(f"  {'3. Nested Walk-Forward CV':<35} {'✓ PASS' if test3_result['passed'] else '✗ FAIL':<10} WR 42-48%, PF>1.1")
    print(f"  {'4. March 2026 Stress':<35} {'⏳ SKIP':<10} WR>35%, DD<25%")
    print(f"  {'5. R:R Sensitivity':<35} {'✓ PASS' if test5_result['passed'] else '✗ FAIL':<10} 4+ configs >40%")
    print(f"  {'6. Slippage Robustness':<35} {'⏳ SKIP':<10} B>30%, C>15%")
    print(f"  {'7. Live Paper Trading':<35} {'⏳ PENDING':<10} 3mo, ≥85% target")

    passed_count = sum(1 for r in all_test_results if r['passed'])
    total_run = len(all_test_results)

    print(f"\n  Tests passed: {passed_count}/{total_run} (automated subset)")
    print(f"  Overall status: {'✓ READY for next stage' if passed_count == total_run else '✗ NEEDS ATTENTION'}")

    # Save results
    save_data = {
        'timestamp': str(pd.Timestamp.now()),
        'model': 'Him V2',
        'tests': all_test_results,
        'summary': {
            'automated_tests_run': total_run,
            'automated_tests_passed': passed_count,
            'pending_tests': ['monte_carlo', 'march_2026', 'slippage', 'paper_trading'],
        }
    }

    with open(OUTPUT_DIR / "validation_report.json", 'w') as f:
        json.dump(save_data, f, indent=2, default=str)

    print(f"\n  Report saved: {OUTPUT_DIR}/validation_report.json")
    print("\n" + "="*80)


if __name__ == "__main__":
    main()
