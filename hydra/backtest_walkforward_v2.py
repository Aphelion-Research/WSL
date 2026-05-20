"""HYDRA Walk-Forward V2 — Nuclear parallelism, precomputed everything.

Performance target: 100 iterations in under 3 minutes on 20 cores.
Strategy: precompute features/labels/folds ONCE, parallelize iterations via joblib.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
import warnings
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

os.environ['OMP_NUM_THREADS'] = '4'
os.environ['OPENBLAS_NUM_THREADS'] = '4'
os.environ['MKL_NUM_THREADS'] = '4'

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from joblib import Parallel, delayed

from hydra.config import DB_PATH
from hydra.data.features_stationary import build_stationary_features
from hydra.backtest.metrics import sharpe_ratio, sortino_ratio, max_drawdown

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

CAPITAL = 100_000.0
BASE_SEED = 42
RUNS_DIR = Path.home() / "Dominion" / "runs"
N_CORES = 20
N_WORKERS = 10  # parallel iteration workers (1-2 threads each)

@dataclass
class CostScenario:
    name: str
    spread_pips: float
    slippage_pips: float
    commission_rt: float

COST_SCENARIOS = [CostScenario("base", 0.35, 0.15, 2.50)]

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
# Triple-Barrier (percentage ATR)
# ─────────────────────────────────────────────────────────────────────────────

def compute_atr(high, low, close, period=14):
    hl = high - low
    hc = np.abs(high - np.roll(close, 1))
    lc = np.abs(low - np.roll(close, 1))
    tr = np.maximum(np.maximum(hl, hc), lc)
    tr[0] = high[0] - low[0]

    atr = np.full(len(close), np.nan, dtype=np.float64)
    atr[period-1] = tr[:period].mean()
    for i in range(period, len(close)):
        atr[i] = (atr[i-1] * (period - 1) + tr[i]) / period
    return atr


def make_labels_pct(high, low, close, mode: ModeConfig):
    n = len(close)
    y = np.full(n, np.nan, dtype=np.float32)
    H = mode.horizon_bars
    sl_mult = mode.stop_mult
    tp_mult = mode.target_mult
    atr = compute_atr(high, low, close, 14)

    for t in range(n - H):
        if not np.isfinite(atr[t]) or atr[t] <= 0 or close[t] <= 0:
            continue
        atr_pct = atr[t] / close[t]
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
# Model Training
# ─────────────────────────────────────────────────────────────────────────────

def train_model(X_train, y_train, seed):
    from sklearn.ensemble import (
        RandomForestClassifier, HistGradientBoostingClassifier,
    )
    from sklearn.linear_model import LogisticRegression
    import lightgbm as lgb
    import xgboost as xgb

    models = []

    hgb = HistGradientBoostingClassifier(
        max_iter=100, learning_rate=0.05, max_leaf_nodes=31,
        min_samples_leaf=20, l2_regularization=0.1,
        early_stopping=False, random_state=seed,
    )
    hgb.fit(X_train, y_train)
    models.append(("hgb", hgb))

    rf = RandomForestClassifier(
        n_estimators=100, max_depth=8, min_samples_leaf=20,
        max_features="sqrt", n_jobs=1, random_state=seed,
        class_weight="balanced",
    )
    rf.fit(X_train, y_train)
    models.append(("rf", rf))

    lr = LogisticRegression(
        C=0.5, max_iter=1000, random_state=seed,
        class_weight="balanced", solver="lbfgs", penalty="l2",
        n_jobs=1,
    )
    lr.fit(X_train, y_train)
    models.append(("lr", lr))

    lgbm = lgb.LGBMClassifier(
        n_estimators=100, learning_rate=0.05, num_leaves=31,
        min_data_in_leaf=20, feature_fraction=0.8,
        bagging_fraction=0.8, bagging_freq=5,
        lambda_l1=0.1, lambda_l2=0.1,
        verbose=-1, random_state=seed,
        n_jobs=1, num_threads=1,
        force_col_wise=True,
    )
    lgbm.fit(X_train, y_train)
    models.append(("lgbm", lgbm))

    xgbm = xgb.XGBClassifier(
        n_estimators=100, learning_rate=0.05, max_depth=5,
        min_child_weight=20, subsample=0.8, colsample_bytree=0.8,
        reg_alpha=0.1, reg_lambda=1.0,
        verbosity=0, random_state=seed,
        eval_metric='logloss', n_jobs=1, tree_method='hist',
    )
    xgbm.fit(X_train, y_train)
    models.append(("xgb", xgbm))

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
# Walk-Forward Folds (precomputed indices)
# ─────────────────────────────────────────────────────────────────────────────

def create_walk_forward_folds(df: pd.DataFrame):
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
            "train_idx": np.where(train_mask.values)[0],
            "val_idx": np.where(val_mask.values)[0],
            "test_idx": np.where(test_mask.values)[0],
            "train_end": str(train_end_month),
            "val_range": f"{val_start_month} to {val_end_month}",
            "test_range": f"{test_start_month} to {test_end_month}",
        })
        start_idx += step_months

    return folds


# ─────────────────────────────────────────────────────────────────────────────
# Precomputed Data Container
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class PrecomputedData:
    X: np.ndarray           # (n_bars, n_features) float32
    y: np.ndarray           # (n_bars,) float32
    close: np.ndarray       # (n_bars,) float64
    high: np.ndarray        # (n_bars,) float64
    low: np.ndarray         # (n_bars,) float64
    folds: list             # list of fold dicts with indices
    mode: ModeConfig
    cost: CostScenario


def precompute_all(df: pd.DataFrame, mode: ModeConfig, cost: CostScenario) -> PrecomputedData:
    """Compute features, labels, and folds ONCE. Everything reusable across seeds."""
    print("  Building features...")
    t0 = time.time()
    df2 = build_stationary_features(df.copy())
    print(f"  Features: {time.time()-t0:.2f}s")

    exclude = {"ts", "open", "high", "low", "close", "volume", "year_month",
               "macro_regime", "regime_confidence", "structural_regime",
               "tactical_regime", "micro_regime", "confidence", "regime_id",
               "p_trend_up", "p_trend_dn", "p_range", "p_crisis"}
    numeric_cols = df2.select_dtypes(include=[np.number]).columns.tolist()
    feat_cols = [c for c in numeric_cols if c not in exclude]
    X = df2[feat_cols].values.astype(np.float32)
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
    print(f"  Feature matrix: {X.shape} ({len(feat_cols)} features)")

    print("  Computing labels...")
    t0 = time.time()
    high = df["high"].values.astype(np.float64)
    low = df["low"].values.astype(np.float64)
    close = df["close"].values.astype(np.float64)
    y = make_labels_pct(high, low, close, mode)
    valid = np.isfinite(y).sum()
    print(f"  Labels: {time.time()-t0:.2f}s ({valid} valid, {np.sum(y==1)} long, {np.sum(y==0)} short)")

    print("  Creating folds...")
    folds = create_walk_forward_folds(df)
    print(f"  {len(folds)} folds created")

    return PrecomputedData(X=X, y=y, close=close, high=high, low=low,
                           folds=folds, mode=mode, cost=cost)


# ─────────────────────────────────────────────────────────────────────────────
# Single Iteration (operates on precomputed data only — no I/O, no feature eng)
# ─────────────────────────────────────────────────────────────────────────────

def run_single_iteration(seed: int, data: PrecomputedData):
    """Run one full walk-forward pass. ~5-8s with precomputed data."""
    X = data.X
    y = data.y
    close = data.close
    high = data.high
    low = data.low
    mode = data.mode
    cost = data.cost

    fold_results = []

    for fold_idx, fold in enumerate(data.folds):
        train_idx = fold["train_idx"]
        val_idx = fold["val_idx"]
        test_idx = fold["test_idx"]

        # Training data
        train_valid_mask = np.isfinite(y[train_idx])
        X_train = X[train_idx][train_valid_mask]
        y_train = y[train_idx][train_valid_mask]

        if len(y_train) < 100:
            fold_results.append({
                "fold": fold_idx,
                "status": "SKIP_INSUFFICIENT",
                "val_trades": 0, "oos_trades": 0,
            })
            continue

        # Train models
        models = train_model(X_train, y_train, seed)

        # ─── Validation ───
        X_val = X[val_idx]
        proba_val = predict_ensemble(models, X_val)
        signals_val = np.where(proba_val >= mode.min_confidence, 1, 0)

        close_val = close[val_idx]
        high_val = high[val_idx]
        low_val = low[val_idx]

        trades_val, equity_val = run_backtest(
            close_val, high_val, low_val, signals_val, proba_val, mode, cost
        )
        metrics_val = compute_metrics(trades_val, equity_val)

        val_pf = metrics_val["profit_factor"]
        val_wr = metrics_val["win_rate"]
        val_trades = metrics_val["n_trades"]

        # Overfit detection — auto-lower threshold if too few trades
        effective_threshold = mode.min_confidence
        n_val_bars = len(val_idx)
        # Min trades: 1 for sparse data, up to 30 for dense data (>500 val bars)
        min_trades = max(1, min(30, n_val_bars // 20))

        if val_trades < min_trades and effective_threshold > 0.505:
            for adj in [0.005, 0.01, 0.015, 0.02, 0.03, 0.04, 0.05]:
                new_thresh = mode.min_confidence - adj
                if new_thresh < 0.505:
                    break
                signals_adj = np.where(proba_val >= new_thresh, 1, 0)
                trades_adj, eq_adj = run_backtest(
                    close_val, high_val, low_val, signals_adj, proba_val, mode, cost
                )
                m_adj = compute_metrics(trades_adj, eq_adj)
                if m_adj["n_trades"] >= min_trades:
                    effective_threshold = new_thresh
                    trades_val, equity_val = trades_adj, eq_adj
                    metrics_val = m_adj
                    val_pf = m_adj["profit_factor"]
                    val_wr = m_adj["win_rate"]
                    val_trades = m_adj["n_trades"]
                    break

        # Layer 1: per-iteration overfit rejection
        # Only apply PF/WR filters when enough trades to be meaningful
        overfit_by_stats = val_trades >= 10 and (val_pf > 50 or val_wr > 0.85)
        if overfit_by_stats or val_trades < min_trades:
            fold_results.append({
                "fold": fold_idx,
                "status": "OVERFIT",
                "val_pf": val_pf, "val_wr": val_wr, "val_trades": val_trades,
                "oos_trades": 0,
            })
            continue

        # ─── Test (OOS) ───
        X_test = X[test_idx]
        proba_test = predict_ensemble(models, X_test)
        signals_test = np.where(proba_test >= effective_threshold, 1, 0)

        close_test = close[test_idx]
        high_test = high[test_idx]
        low_test = low[test_idx]

        trades_test, equity_test = run_backtest(
            close_test, high_test, low_test, signals_test, proba_test, mode, cost
        )
        metrics_test = compute_metrics(trades_test, equity_test)

        val_sharpe = metrics_val["sharpe"]
        test_sharpe = metrics_test["sharpe"]
        sharpe_decay = ((val_sharpe - test_sharpe) / val_sharpe * 100) if val_sharpe > 0 else 0

        fold_results.append({
            "fold": fold_idx,
            "status": "OK",
            "val_trades": val_trades,
            "val_sharpe": val_sharpe,
            "val_pf": val_pf,
            "val_wr": val_wr,
            "oos_trades": metrics_test["n_trades"],
            "oos_sharpe": test_sharpe,
            "oos_pf": metrics_test["profit_factor"],
            "oos_wr": metrics_test["win_rate"],
            "sharpe_decay_pct": round(sharpe_decay, 1),
            "threshold_used": effective_threshold,
        })

    return fold_results


# ─────────────────────────────────────────────────────────────────────────────
# Progress Table
# ─────────────────────────────────────────────────────────────────────────────

def print_fold_table(folds, all_results, n_iterations):
    """Print live results table."""
    print("\n╔═══════╦══════════════════╦═══════╦════════╦═══════╦══════════════════╦═══════╦════════╦════════╗")
    print("║ Fold  ║ Val Period       ║ V.Trd ║ V.Shp  ║ V.PF  ║ OOS Period       ║ O.Trd ║ O.Shp  ║ Decay% ║")
    print("╠═══════╬══════════════════╬═══════╬════════╬═══════╬══════════════════╬═══════╬════════╬════════╣")

    for fold_idx in range(len(folds)):
        fold_data = [r[fold_idx] for r in all_results if fold_idx < len(r)]
        ok_folds = [f for f in fold_data if f.get("status") == "OK"]

        val_range = folds[fold_idx]["val_range"]
        test_range = folds[fold_idx]["test_range"]

        if ok_folds:
            med_vt = int(np.median([f["val_trades"] for f in ok_folds]))
            med_vs = np.median([f["val_sharpe"] for f in ok_folds])
            med_vp = np.median([f["val_pf"] for f in ok_folds])
            med_ot = int(np.median([f["oos_trades"] for f in ok_folds]))
            med_os = np.median([f["oos_sharpe"] for f in ok_folds])
            med_decay = np.median([f["sharpe_decay_pct"] for f in ok_folds])

            print(f"║ {fold_idx+1:2d}/{len(folds):2d} ║ {val_range:<16s} ║ {med_vt:5d} ║ {med_vs:6.2f} ║ {med_vp:5.2f} ║ {test_range:<16s} ║ {med_ot:5d} ║ {med_os:6.2f} ║ {med_decay:5.1f}% ║")
        else:
            overfit_n = sum(1 for f in fold_data if f.get("status") == "OVERFIT")
            skip_n = sum(1 for f in fold_data if f.get("status") == "SKIP_INSUFFICIENT")
            print(f"║ {fold_idx+1:2d}/{len(folds):2d} ║ {val_range:<16s} ║   --  ║   --   ║  --   ║ {test_range:<16s} ║   --  ║   --   ║  SKIP  ║")

    print("╚═══════╩══════════════════╩═══════╩════════╩═══════╩══════════════════╩═══════╩════════╩════════╝")


# ─────────────────────────────────────────────────────────────────────────────
# Data Loading
# ─────────────────────────────────────────────────────────────────────────────

def load_data():
    import duckdb
    con = duckdb.connect(str(DB_PATH), read_only=True)
    df = con.execute(
        "SELECT timestamp as ts, open, high, low, close, volume FROM gold_master "
        "WHERE close > 1000 ORDER BY timestamp"
    ).df()
    df["ts"] = pd.to_datetime(df["ts"])
    con.close()
    return df.sort_values("ts").reset_index(drop=True)


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", type=str, default="scalp", choices=MODES.keys())
    parser.add_argument("--iterations", type=int, default=100)
    parser.add_argument("--workers", type=int, default=N_WORKERS)
    args = parser.parse_args()

    mode = MODES[args.mode]
    cost = COST_SCENARIOS[0]

    print("=" * 80)
    print("HYDRA WALK-FORWARD V2 — NUCLEAR PARALLELISM")
    print("=" * 80)
    print(f"Mode: {mode.name}")
    print(f"Iterations: {args.iterations}")
    print(f"Workers: {args.workers} (threads/worker: 4, total cores: {args.workers*4})")
    print(f"Confidence threshold: {mode.min_confidence}")
    print("=" * 80)

    # Load data
    print("\n[1/5] Loading data...")
    df = load_data()
    print(f"  {len(df)} bars: {df['ts'].min().date()} to {df['ts'].max().date()}")

    # Precompute everything
    print("\n[2/5] Precomputing features + labels + folds...")
    t0 = time.time()
    data = precompute_all(df, mode, cost)
    print(f"  Done in {time.time()-t0:.2f}s")

    # Time single iteration
    print("\n[3/5] Benchmarking single iteration...")
    t0 = time.time()
    single_result = run_single_iteration(BASE_SEED, data)
    single_time = time.time() - t0
    print(f"  Single iteration: {single_time:.2f}s")
    ok_count = sum(1 for f in single_result if f["status"] == "OK")
    overfit_count = sum(1 for f in single_result if f["status"] == "OVERFIT")
    print(f"  Folds: {ok_count} OK, {overfit_count} OVERFIT, {len(single_result)-ok_count-overfit_count} SKIP")

    if single_time > 10:
        print(f"  WARNING: Single iteration {single_time:.1f}s > 10s target")
        est_total = single_time * args.iterations / args.workers
        print(f"  Estimated total: {est_total/60:.1f} min with {args.workers} workers")
    else:
        est_total = single_time * args.iterations / args.workers
        print(f"  Estimated total: {est_total/60:.1f} min with {args.workers} workers")

    # Run all iterations in parallel
    print(f"\n[4/5] Running {args.iterations} iterations ({args.workers} parallel workers)...")
    t0 = time.time()

    all_results = Parallel(n_jobs=args.workers, verbose=10)(
        delayed(run_single_iteration)(BASE_SEED + i, data)
        for i in range(args.iterations)
    )

    elapsed = time.time() - t0
    print(f"\n  Completed {args.iterations} iterations in {elapsed:.1f}s ({elapsed/60:.1f} min)")
    print(f"  Throughput: {args.iterations/elapsed:.1f} iterations/sec")

    # ─── Layer 2: Per-fold memorization detection ───
    print("\n[5/5] Overfit detection + results...")

    for fold_idx in range(len(data.folds)):
        fold_data = [r[fold_idx] for r in all_results if fold_idx < len(r)]
        ok_folds = [f for f in fold_data if f.get("status") == "OK"]
        if ok_folds:
            iteration_sharpes = [f["oos_sharpe"] for f in ok_folds]
            if np.std(iteration_sharpes) < 0.001 and len(ok_folds) > 10:
                print(f"  MEMORIZATION DETECTED in fold {fold_idx} — std(sharpes)={np.std(iteration_sharpes):.6f}")

    # Print results table
    print_fold_table(data.folds, all_results, args.iterations)

    # ─── Layer 3: Final verdict ───
    print("\n" + "=" * 80)
    print("FINAL VERDICT")
    print("=" * 80)

    all_ok = []
    for results in all_results:
        all_ok.extend([f for f in results if f.get("status") == "OK"])

    if not all_ok:
        print("NO EDGE. ALL FOLDS OVERFIT OR INSUFFICIENT DATA.")
        return

    oos_sharpes = [f["oos_sharpe"] for f in all_ok]
    oos_pfs = [f["oos_pf"] for f in all_ok]
    oos_trades = [f["oos_trades"] for f in all_ok]

    median_sharpe = np.median(oos_sharpes)
    mean_sharpe = np.mean(oos_sharpes)
    pct_sharpe_pos = sum(1 for s in oos_sharpes if s > 0) / len(oos_sharpes) * 100
    pct_sharpe_good = sum(1 for s in oos_sharpes if s > 0.5) / len(oos_sharpes) * 100
    pct_pf_good = sum(1 for p in oos_pfs if p > 1.2) / len(oos_pfs) * 100
    median_trades = np.median(oos_trades)
    pct_zero_trades = sum(1 for t in oos_trades if t == 0) / len(oos_trades) * 100

    # Overfit fold percentage
    all_fold_statuses = [f.get("status") for results in all_results for f in results]
    pct_overfit = all_fold_statuses.count("OVERFIT") / len(all_fold_statuses) * 100

    print(f"  Total OK fold-iterations: {len(all_ok)}")
    print(f"  Median OOS Sharpe:  {median_sharpe:.3f}")
    print(f"  Mean OOS Sharpe:    {mean_sharpe:.3f}")
    print(f"  % Sharpe > 0:       {pct_sharpe_pos:.1f}%")
    print(f"  % Sharpe > 0.5:     {pct_sharpe_good:.1f}%")
    print(f"  % PF > 1.2:         {pct_pf_good:.1f}%")
    print(f"  Median OOS trades:  {median_trades:.0f}")
    print(f"  % zero-trade folds: {pct_zero_trades:.1f}%")
    print(f"  % overfit folds:    {pct_overfit:.1f}%")

    # Layer 3 rejection
    if median_sharpe < 0.3:
        verdict = "NO EDGE. STOP RESEARCH."
    elif pct_overfit > 50:
        verdict = "METHODOLOGY BROKEN. >50% OVERFIT."
    elif pct_sharpe_good < 30:
        verdict = "INCONCLUSIVE. EDGE TOO WEAK."
    elif pct_zero_trades > 30:
        verdict = "SIGNAL TOO RARE. LOWER THRESHOLDS."
    else:
        verdict = "EDGE EXISTS. PROCEED TO LIVE TESTING."

    print(f"\n  >>> VERDICT: {verdict}")

    # Save report
    run_id = f"walkforward_{mode.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    run_dir = RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    # Save proba distributions
    np.save(run_dir / "oos_sharpes.npy", np.array(oos_sharpes))
    np.save(run_dir / "oos_pfs.npy", np.array(oos_pfs))
    np.save(run_dir / "oos_trades.npy", np.array(oos_trades))

    # Save report
    report_path = run_dir / "REPORT.md"
    with open(report_path, "w") as f:
        f.write(f"# Walk-Forward Backtest Report — {mode.name}\n\n")
        f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Iterations:** {args.iterations}\n")
        f.write(f"**Folds:** {len(data.folds)}\n")
        f.write(f"**Workers:** {args.workers}\n")
        f.write(f"**Runtime:** {elapsed:.1f}s\n\n")

        f.write("## Configuration\n\n")
        f.write(f"- Mode: {mode.name}\n")
        f.write(f"- Horizon: {mode.horizon_bars} bars\n")
        f.write(f"- Stop mult: {mode.stop_mult}\n")
        f.write(f"- Target mult: {mode.target_mult}\n")
        f.write(f"- Min confidence: {mode.min_confidence}\n")
        f.write(f"- Spread: {cost.spread_pips} pips\n")
        f.write(f"- Slippage: {cost.slippage_pips} pips\n")
        f.write(f"- Commission RT: ${cost.commission_rt}\n\n")

        f.write("## Results\n\n")
        f.write(f"| Metric | Value |\n|--------|-------|\n")
        f.write(f"| Median OOS Sharpe | {median_sharpe:.3f} |\n")
        f.write(f"| Mean OOS Sharpe | {mean_sharpe:.3f} |\n")
        f.write(f"| % Sharpe > 0 | {pct_sharpe_pos:.1f}% |\n")
        f.write(f"| % Sharpe > 0.5 | {pct_sharpe_good:.1f}% |\n")
        f.write(f"| % PF > 1.2 | {pct_pf_good:.1f}% |\n")
        f.write(f"| Median OOS trades | {median_trades:.0f} |\n")
        f.write(f"| % zero-trade folds | {pct_zero_trades:.1f}% |\n")
        f.write(f"| % overfit folds | {pct_overfit:.1f}% |\n\n")

        f.write("## Fold Details\n\n")
        f.write("| Fold | Val Period | V.Trades | V.Sharpe | V.PF | OOS Period | O.Trades | O.Sharpe | Decay% |\n")
        f.write("|------|-----------|----------|----------|------|-----------|----------|----------|--------|\n")

        for fold_idx in range(len(data.folds)):
            fold_data = [r[fold_idx] for r in all_results if fold_idx < len(r)]
            ok_folds = [fd for fd in fold_data if fd.get("status") == "OK"]
            val_range = data.folds[fold_idx]["val_range"]
            test_range = data.folds[fold_idx]["test_range"]

            if ok_folds:
                med_vt = int(np.median([fd["val_trades"] for fd in ok_folds]))
                med_vs = np.median([fd["val_sharpe"] for fd in ok_folds])
                med_vp = np.median([fd["val_pf"] for fd in ok_folds])
                med_ot = int(np.median([fd["oos_trades"] for fd in ok_folds]))
                med_os = np.median([fd["oos_sharpe"] for fd in ok_folds])
                med_decay = np.median([fd["sharpe_decay_pct"] for fd in ok_folds])
                f.write(f"| {fold_idx+1} | {val_range} | {med_vt} | {med_vs:.3f} | {med_vp:.2f} | {test_range} | {med_ot} | {med_os:.3f} | {med_decay:.1f}% |\n")
            else:
                f.write(f"| {fold_idx+1} | {val_range} | -- | -- | -- | {test_range} | -- | -- | SKIP |\n")

        f.write(f"\n## Verdict\n\n**{verdict}**\n")

    print(f"\n  Report: {report_path}")
    print(f"  Data:   {run_dir}")


if __name__ == "__main__":
    main()
