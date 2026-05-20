"""HYDRA Walk-Forward Backtest — Fixes zero OOS trades failure.

ROOT CAUSES FIXED:
1. Parallelism: All models now use n_jobs=-1 or equivalent (20 cores)
2. Walk-forward: Expanding 12-month train windows, 3-month val/test
3. Overfit detection: Auto-reject if PF>50, WR>85%, or trades<30
4. Percentage barriers: ATR normalized by close (regime-invariant)
5. Lower thresholds: 0.52/0.54/0.56 (down from 0.55/0.58/0.60)

Usage:
    python -m hydra.backtest_walkforward --mode scalp --iterations 100
"""
from __future__ import annotations

import argparse
import sys
import time
import warnings
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hydra.config import DB_PATH
from hydra.data.features_stationary import build_stationary_features
from hydra.backtest.metrics import (
    sharpe_ratio, sortino_ratio, max_drawdown,
    profit_factor, win_rate,
)

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

CAPITAL = 100_000.0
BASE_SEED = 42
RUNS_DIR = Path.home() / "Dominion" / "runs"
N_CORES = 20


@dataclass
class CostScenario:
    name: str
    spread_pips: float
    slippage_pips: float
    commission_rt: float


COST_SCENARIOS = [
    CostScenario("base", 0.35, 0.15, 2.50),
]


@dataclass
class ModeConfig:
    name: str
    horizon_bars: int
    stop_mult: float
    target_mult: float
    min_confidence: float
    risk_per_trade: float
    max_risk: float


MODES = {
    "scalp": ModeConfig("HYDRA-SCALP", 5, 1.5, 1.5, 0.52, 0.003, 0.005),
    "daytrade": ModeConfig("HYDRA-DAYTRADE", 10, 1.5, 1.5, 0.54, 0.005, 0.01),
    "swing": ModeConfig("HYDRA-SWING", 20, 1.5, 3.0, 0.56, 0.005, 0.01),
}


@dataclass
class Trade:
    entry_bar: int
    exit_bar: int
    direction: int
    entry_px: float
    exit_px: float
    pnl_dollars: float
    bars_held: int
    size_lots: float


# ─────────────────────────────────────────────────────────────────────────────
# Triple-Barrier with Percentage ATR (FIXED)
# ─────────────────────────────────────────────────────────────────────────────

def compute_atr(high, low, close, period=14):
    """Compute ATR (Wilder's method)."""
    hl = high - low
    hc = np.abs(high - np.roll(close, 1))
    lc = np.abs(low - np.roll(close, 1))
    tr = np.maximum(np.maximum(hl, hc), lc)
    tr[0] = high[0] - low[0]

    atr = np.full(len(close), np.nan, dtype=np.float32)
    atr[period-1] = tr[:period].mean()
    for i in range(period, len(close)):
        atr[i] = (atr[i-1] * (period - 1) + tr[i]) / period

    return atr


def make_labels_pct(high, low, close, mode: ModeConfig):
    """Triple-barrier labels with PERCENTAGE ATR barriers (regime-invariant).

    OLD (absolute):
        sl = close[t] - sl_mult * atr[t]
        tp = close[t] + tp_mult * atr[t]

    NEW (percentage):
        atr_pct = atr[t] / close[t]
        sl = close[t] * (1 - sl_mult * atr_pct)
        tp = close[t] * (1 + tp_mult * atr_pct)

    This makes barriers regime-invariant: 1.5% move = 1.5% whether gold=$1400 or $4400.
    """
    n = len(close)
    y = np.full(n, np.nan, dtype=np.float32)
    H = mode.horizon_bars
    sl_mult = mode.stop_mult
    tp_mult = mode.target_mult

    atr = compute_atr(high, low, close, 14)

    for t in range(n - H):
        if not np.isfinite(atr[t]) or atr[t] <= 0 or close[t] <= 0:
            continue

        # Percentage ATR
        atr_pct = atr[t] / close[t]

        # Percentage barriers
        sl_long = close[t] * (1 - sl_mult * atr_pct)
        tp_long = close[t] * (1 + tp_mult * atr_pct)

        for k in range(1, H + 1):
            if low[t + k] <= sl_long:
                y[t] = 0.0
                break
            if high[t + k] >= tp_long:
                y[t] = 1.0
                break

    return y


# ─────────────────────────────────────────────────────────────────────────────
# Model Training (PARALLELIZED)
# ─────────────────────────────────────────────────────────────────────────────

def train_model(X_train, y_train, seed):
    """Train ensemble with FULL PARALLELISM (all cores)."""
    from sklearn.ensemble import (
        RandomForestClassifier, HistGradientBoostingClassifier,
    )
    from sklearn.linear_model import LogisticRegression

    models = []

    # HistGradientBoosting (uses all cores by default)
    hgb = HistGradientBoostingClassifier(
        max_iter=300, learning_rate=0.05, max_leaf_nodes=31,
        min_samples_leaf=20, l2_regularization=0.1,
        early_stopping=True, validation_fraction=0.15,
        n_iter_no_change=30, random_state=seed,
    )
    hgb.fit(X_train, y_train)
    models.append(("hgb", hgb))

    # Random Forest (n_jobs=-1)
    rf = RandomForestClassifier(
        n_estimators=300, max_depth=10, min_samples_leaf=20,
        max_features="sqrt", n_jobs=-1, random_state=seed,
        class_weight="balanced",
    )
    rf.fit(X_train, y_train)
    models.append(("rf", rf))

    # Logistic Regression (n_jobs=-1)
    lr = LogisticRegression(
        C=0.5, max_iter=3000, random_state=seed,
        class_weight="balanced", solver="saga", penalty="l1",
        n_jobs=-1,
    )
    lr.fit(X_train, y_train)
    models.append(("lr", lr))

    try:
        import lightgbm as lgb
        lgbm = lgb.LGBMClassifier(
            n_estimators=300, learning_rate=0.03, num_leaves=31,
            min_data_in_leaf=20, feature_fraction=0.8,
            bagging_fraction=0.8, bagging_freq=5,
            lambda_l1=0.1, lambda_l2=0.1,
            verbose=-1, random_state=seed,
            n_jobs=-1, num_threads=N_CORES,
        )
        lgbm.fit(X_train, y_train)
        models.append(("lgbm", lgbm))
    except ImportError:
        pass

    try:
        import xgboost as xgb
        xgbm = xgb.XGBClassifier(
            n_estimators=300, learning_rate=0.03, max_depth=6,
            min_child_weight=20, subsample=0.8, colsample_bytree=0.8,
            reg_alpha=0.1, reg_lambda=0.1,
            verbosity=0, random_state=seed, use_label_encoder=False,
            eval_metric="logloss",
            n_jobs=N_CORES, tree_method='hist',
        )
        xgbm.fit(X_train, y_train)
        models.append(("xgb", xgbm))
    except ImportError:
        pass

    return models


def predict_ensemble(models, X):
    preds = []
    for name, model in models:
        p = model.predict_proba(X)
        preds.append(p[:, 1] if p.ndim == 2 else p)
    return np.mean(preds, axis=0)


# ─────────────────────────────────────────────────────────────────────────────
# Backtest
# ─────────────────────────────────────────────────────────────────────────────

def run_backtest(close, high, low, signals, confidences,
                 mode: ModeConfig, cost: CostScenario, capital: float = CAPITAL):
    n = len(close)
    atr = compute_atr(high, low, close, 14)

    trades = []
    equity = capital
    equity_curve = [equity]
    in_trade = False
    entry_bar = entry_px = direction = stop_px = target_px = size_lots = 0

    for t in range(n):
        if not in_trade:
            sig = signals[t]
            conf = confidences[t]
            if sig != 0 and conf >= mode.min_confidence and np.isfinite(atr[t]) and atr[t] > 0 and close[t] > 0:
                direction = int(sig)
                spread_cost = cost.spread_pips + cost.slippage_pips
                entry_px = close[t] + direction * spread_cost / 2
                entry_atr = atr[t]

                # Percentage barriers
                atr_pct = entry_atr / close[t]
                stop_px = entry_px * (1 - direction * mode.stop_mult * atr_pct)
                target_px = entry_px * (1 + direction * mode.target_mult * atr_pct)

                risk_dollars = equity * mode.risk_per_trade
                stop_distance = abs(entry_px - stop_px)
                if stop_distance < 0.01:
                    equity_curve.append(equity)
                    continue
                size_lots = risk_dollars / (stop_distance * 100)
                size_lots = min(size_lots, equity * mode.max_risk / (entry_atr * 100))
                if size_lots < 0.01:
                    equity_curve.append(equity)
                    continue
                entry_bar = t
                in_trade = True
        else:
            exit_px = None
            if direction == 1:
                if low[t] <= stop_px:
                    exit_px = stop_px
                elif high[t] >= target_px:
                    exit_px = target_px
            else:
                if high[t] >= stop_px:
                    exit_px = stop_px
                elif low[t] <= target_px:
                    exit_px = target_px
            if exit_px is None and (t - entry_bar) >= mode.horizon_bars:
                exit_px = close[t]
            if exit_px is not None:
                spread_exit = cost.spread_pips / 2 + cost.slippage_pips
                exit_px_adj = exit_px - direction * spread_exit
                raw_pnl = direction * (exit_px_adj - entry_px) * size_lots * 100
                pnl = raw_pnl - cost.commission_rt * size_lots
                equity += pnl
                trades.append(Trade(
                    entry_bar=entry_bar, exit_bar=t, direction=direction,
                    entry_px=entry_px, exit_px=exit_px_adj,
                    pnl_dollars=pnl, bars_held=t - entry_bar, size_lots=size_lots,
                ))
                in_trade = False
        equity_curve.append(equity)

    return trades, np.array(equity_curve)


def compute_metrics(trades: list[Trade], equity: np.ndarray) -> dict:
    if not trades:
        return {"n_trades": 0, "win_rate": 0, "expectancy": 0,
                "profit_factor": 0, "sharpe": 0, "sortino": 0,
                "max_dd": 0, "total_return_pct": 0}

    pnl = np.array([t.pnl_dollars for t in trades])
    winners = pnl[pnl > 0]
    losers = pnl[pnl < 0]
    n_trades = len(trades)
    wr = len(winners) / n_trades

    if len(losers) > 0 and abs(losers.sum()) > 0:
        pf = winners.sum() / abs(losers.sum()) if len(winners) > 0 else 0
    elif len(winners) > 0:
        pf = 9999.0
    else:
        pf = 0

    daily_ret = np.diff(equity) / np.where(equity[:-1] > 0, equity[:-1], 1.0)
    daily_ret = daily_ret[np.isfinite(daily_ret)]
    sr = sharpe_ratio(daily_ret) if len(daily_ret) > 10 else 0
    sort = sortino_ratio(daily_ret) if len(daily_ret) > 10 else 0
    mdd = max_drawdown(equity)

    total_ret = (equity[-1] - equity[0]) / equity[0] * 100

    return {
        "n_trades": n_trades,
        "win_rate": round(wr, 4),
        "expectancy": round(pnl.mean(), 2),
        "profit_factor": round(pf, 3),
        "sharpe": round(sr, 3),
        "sortino": round(sort, 3),
        "max_dd": round(mdd * 100, 2),
        "total_return_pct": round(total_ret, 2),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Walk-Forward Folds
# ─────────────────────────────────────────────────────────────────────────────

def create_walk_forward_folds(df: pd.DataFrame):
    """Create walk-forward folds with expanding train window.

    Structure:
    - Train: 12 months minimum, expanding
    - Val: 3 months fixed
    - Test: 3 months fixed (never seen during train/val)
    - Step: roll forward 3 months per fold

    Target: 6-8 folds across 5-year dataset.
    """
    df = df.sort_values("ts").reset_index(drop=True)
    df["year_month"] = pd.to_datetime(df["ts"]).dt.to_period("M")

    months = sorted(df["year_month"].unique())
    n_months = len(months)

    folds = []

    train_months = 12
    val_months = 3
    test_months = 3
    step_months = 3

    start_idx = train_months

    while start_idx + val_months + test_months <= n_months:
        train_end_month = months[start_idx - 1]
        val_start_month = months[start_idx]
        val_end_month = months[start_idx + val_months - 1]
        test_start_month = months[start_idx + val_months]
        test_end_month = months[start_idx + val_months + test_months - 1]

        train_mask = df["year_month"] <= train_end_month
        val_mask = (df["year_month"] >= val_start_month) & (df["year_month"] <= val_end_month)
        test_mask = (df["year_month"] >= test_start_month) & (df["year_month"] <= test_end_month)

        folds.append({
            "train_mask": train_mask.values,
            "val_mask": val_mask.values,
            "test_mask": test_mask.values,
            "train_end": str(train_end_month),
            "val_range": f"{val_start_month} to {val_end_month}",
            "test_range": f"{test_start_month} to {test_end_month}",
        })

        start_idx += step_months

    return folds


# ─────────────────────────────────────────────────────────────────────────────
# Single Iteration
# ─────────────────────────────────────────────────────────────────────────────

def run_single_iteration(seed: int, df: pd.DataFrame, mode: ModeConfig, cost: CostScenario, folds: list):
    """Run one iteration across all walk-forward folds."""

    fold_results = []

    for fold_idx, fold in enumerate(folds):
        train_mask = fold["train_mask"]
        val_mask = fold["val_mask"]
        test_mask = fold["test_mask"]

        # Extract OHLC
        high = df["high"].values
        low = df["low"].values
        close = df["close"].values

        # Make labels
        y = make_labels_pct(high, low, close, mode)

        # Build features
        X, feat_cols = build_features_stationary(df.copy())

        # Train
        train_valid = train_mask & np.isfinite(y)
        X_train = X[train_valid]
        y_train = y[train_valid]

        if len(y_train) < 100:
            fold_results.append({
                "fold": fold_idx,
                "train_end": fold["train_end"],
                "val_range": fold["val_range"],
                "test_range": fold["test_range"],
                "status": "SKIP_INSUFFICIENT_TRAIN",
                "val_trades": 0,
                "oos_trades": 0,
            })
            continue

        models = train_model(X_train, y_train, seed)

        # Validation
        val_indices = np.where(val_mask)[0]
        X_val = X[val_mask]
        y_val = y[val_mask]

        # Predict on all val bars (handle NaN inside backtest)
        proba_val_full = predict_ensemble(models, X_val)
        signals_val_full = np.where(proba_val_full >= mode.min_confidence, 1, 0)

        close_val = close[val_mask]
        high_val = high[val_mask]
        low_val = low[val_mask]

        trades_val, equity_val = run_backtest(
            close_val, high_val, low_val, signals_val_full, proba_val_full, mode, cost
        )
        metrics_val = compute_metrics(trades_val, equity_val)

        # OVERFIT DETECTION
        val_pf = metrics_val["profit_factor"]
        val_wr = metrics_val["win_rate"]
        val_trades = metrics_val["n_trades"]

        if val_pf > 50 or val_wr > 0.85 or val_trades < 30:
            fold_results.append({
                "fold": fold_idx,
                "train_end": fold["train_end"],
                "val_range": fold["val_range"],
                "test_range": fold["test_range"],
                "status": "OVERFIT",
                "val_pf": val_pf,
                "val_wr": val_wr,
                "val_trades": val_trades,
                "oos_trades": 0,
            })
            continue

        # Test (OOS)
        test_indices = np.where(test_mask)[0]
        X_test = X[test_mask]
        y_test = y[test_mask]

        # Predict on all test bars
        proba_test_full = predict_ensemble(models, X_test)
        signals_test_full = np.where(proba_test_full >= mode.min_confidence, 1, 0)

        close_test = close[test_mask]
        high_test = high[test_mask]
        low_test = low[test_mask]

        trades_test, equity_test = run_backtest(
            close_test, high_test, low_test, signals_test_full, proba_test_full, mode, cost
        )
        metrics_test = compute_metrics(trades_test, equity_test)

        # Sharpe decay
        val_sharpe = metrics_val["sharpe"]
        test_sharpe = metrics_test["sharpe"]
        sharpe_decay = ((val_sharpe - test_sharpe) / val_sharpe * 100) if val_sharpe > 0 else 0

        fold_results.append({
            "fold": fold_idx,
            "train_end": fold["train_end"],
            "val_range": fold["val_range"],
            "test_range": fold["test_range"],
            "status": "OK",
            "val_trades": val_trades,
            "val_sharpe": val_sharpe,
            "val_pf": val_pf,
            "val_wr": val_wr,
            "oos_trades": metrics_test["n_trades"],
            "oos_sharpe": test_sharpe,
            "oos_pf": metrics_test["profit_factor"],
            "oos_wr": metrics_test["win_rate"],
            "sharpe_decay_pct": sharpe_decay,
        })

    return fold_results


def build_features_stationary(df: pd.DataFrame):
    """Build regime-invariant features (no training-anchored scaling)."""
    df = build_stationary_features(df)

    exclude = {"ts", "open", "high", "low", "close", "volume",
               "macro_regime", "regime_confidence", "structural_regime",
               "tactical_regime", "micro_regime", "confidence", "regime_id",
               "p_trend_up", "p_trend_dn", "p_range", "p_crisis", "year_month"}
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    feat_cols = [c for c in numeric_cols if c not in exclude]

    X = df[feat_cols].values.astype(np.float32)
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)

    return X, feat_cols


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def load_data():
    """Load OHLCV data from DuckDB."""
    import duckdb
    con = duckdb.connect(str(DB_PATH), read_only=True)

    df = con.execute(
        "SELECT timestamp as ts, open, high, low, close, volume FROM gold_master ORDER BY timestamp"
    ).df()
    df["ts"] = pd.to_datetime(df["ts"])
    con.close()

    return df.sort_values("ts").reset_index(drop=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", type=str, default="scalp", choices=MODES.keys())
    parser.add_argument("--iterations", type=int, default=100)
    args = parser.parse_args()

    mode = MODES[args.mode]
    cost = COST_SCENARIOS[0]

    print("=" * 80)
    print("HYDRA WALK-FORWARD BACKTEST")
    print("=" * 80)
    print(f"Mode: {mode.name}")
    print(f"Iterations: {args.iterations}")
    print(f"Cores: {N_CORES}")
    print(f"Confidence threshold: {mode.min_confidence}")
    print("=" * 80)

    # Load data
    print("\nLoading data...")
    df = load_data()
    print(f"Loaded {len(df)} bars from {df['ts'].min()} to {df['ts'].max()}")

    # Create folds
    print("\nCreating walk-forward folds...")
    folds = create_walk_forward_folds(df)
    print(f"Created {len(folds)} folds:")
    for i, fold in enumerate(folds):
        print(f"  Fold {i}: Train up to {fold['train_end']} | Val {fold['val_range']} | Test {fold['test_range']}")

    # Time single iteration
    print("\nTiming single iteration...")
    start_time = time.time()
    single_result = run_single_iteration(BASE_SEED, df, mode, cost, folds)
    elapsed = time.time() - start_time
    print(f"Single iteration: {elapsed:.1f}s")
    print(f"Estimated total time for {args.iterations} iterations: {elapsed * args.iterations / 60:.1f} min")

    # Run all iterations in parallel
    print(f"\nRunning {args.iterations} iterations in parallel...")
    start_time = time.time()
    all_results = Parallel(n_jobs=N_CORES)(
        delayed(run_single_iteration)(BASE_SEED + i, df, mode, cost, folds)
        for i in range(args.iterations)
    )
    elapsed = time.time() - start_time
    print(f"Completed in {elapsed:.1f}s ({elapsed/60:.1f} min)")

    # Aggregate results
    print("\n" + "=" * 80)
    print("FOLD-BY-FOLD RESULTS")
    print("=" * 80)

    for fold_idx in range(len(folds)):
        fold_data = [r[fold_idx] for r in all_results]

        ok_folds = [f for f in fold_data if f["status"] == "OK"]
        overfit_folds = [f for f in fold_data if f["status"] == "OVERFIT"]

        print(f"\nFold {fold_idx}: Val {folds[fold_idx]['val_range']} | Test {folds[fold_idx]['test_range']}")
        print(f"  Status: {len(ok_folds)} OK, {len(overfit_folds)} OVERFIT")

        if ok_folds:
            oos_sharpes = [f["oos_sharpe"] for f in ok_folds]
            oos_pfs = [f["oos_pf"] for f in ok_folds]
            oos_trades = [f["oos_trades"] for f in ok_folds]

            print(f"  OOS Sharpe: median={np.median(oos_sharpes):.3f}, mean={np.mean(oos_sharpes):.3f}")
            print(f"  OOS PF: median={np.median(oos_pfs):.3f}, mean={np.mean(oos_pfs):.3f}")
            print(f"  OOS Trades: median={np.median(oos_trades):.0f}, mean={np.mean(oos_trades):.0f}")

            zero_trade_pct = sum(1 for t in oos_trades if t == 0) / len(oos_trades) * 100
            if zero_trade_pct > 0:
                print(f"  WARNING: {zero_trade_pct:.1f}% iterations had zero OOS trades")

    # Final verdict
    print("\n" + "=" * 80)
    print("FINAL VERDICT")
    print("=" * 80)

    all_ok_folds = []
    for results in all_results:
        all_ok_folds.extend([f for f in results if f["status"] == "OK"])

    if not all_ok_folds:
        print("NO EDGE. ALL FOLDS OVERFIT OR INSUFFICIENT DATA.")
        return

    oos_sharpes = [f["oos_sharpe"] for f in all_ok_folds]
    oos_pfs = [f["oos_pf"] for f in all_ok_folds]

    median_sharpe = np.median(oos_sharpes)
    pct_sharpe_positive = sum(1 for s in oos_sharpes if s > 0.5) / len(oos_sharpes) * 100
    pct_pf_positive = sum(1 for p in oos_pfs if p > 1.2) / len(oos_pfs) * 100

    print(f"Median OOS Sharpe: {median_sharpe:.3f}")
    print(f"% folds with OOS Sharpe > 0.5: {pct_sharpe_positive:.1f}%")
    print(f"% folds with OOS PF > 1.2: {pct_pf_positive:.1f}%")

    if median_sharpe < 0.3:
        print("\nVERDICT: NO EDGE. STOP RESEARCH.")
    elif pct_sharpe_positive < 30:
        print("\nVERDICT: INCONCLUSIVE. EDGE TOO WEAK.")
    else:
        print("\nVERDICT: EDGE EXISTS. PROCEED TO LIVE TESTING.")

    # Save report
    run_id = f"walkforward_{mode.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    run_dir = RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    report_path = run_dir / "REPORT.md"
    with open(report_path, "w") as f:
        f.write(f"# Walk-Forward Backtest Report\n\n")
        f.write(f"**Mode:** {mode.name}\n")
        f.write(f"**Iterations:** {args.iterations}\n")
        f.write(f"**Folds:** {len(folds)}\n\n")
        f.write(f"## Final Verdict\n\n")
        f.write(f"- Median OOS Sharpe: {median_sharpe:.3f}\n")
        f.write(f"- % folds with OOS Sharpe > 0.5: {pct_sharpe_positive:.1f}%\n")
        f.write(f"- % folds with OOS PF > 1.2: {pct_pf_positive:.1f}%\n\n")

        if median_sharpe < 0.3:
            f.write("**VERDICT:** NO EDGE. STOP RESEARCH.\n")
        elif pct_sharpe_positive < 30:
            f.write("**VERDICT:** INCONCLUSIVE. EDGE TOO WEAK.\n")
        else:
            f.write("**VERDICT:** EDGE EXISTS. PROCEED TO LIVE TESTING.\n")

    print(f"\nReport saved to: {report_path}")


if __name__ == "__main__":
    main()
