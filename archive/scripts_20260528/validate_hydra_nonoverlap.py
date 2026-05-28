#!/usr/bin/env python3
"""
Non-overlapping event-style signal validation for HYDRA.

Converts walk-forward model probabilities into discrete trades with:
- At most one position open at a time
- Fixed hold period (horizon bars)
- Confidence threshold for entry
- No overlapping trades

WARNING: This is still bar-return validation, NOT live execution.
It does NOT model spread, slippage, partial fills, requotes, OHLC path risk,
margin calls, swap costs, or any broker-specific execution mechanics.
Results here are an UPPER BOUND on real-world performance.

Usage:
  python scripts/validate_hydra_nonoverlap.py \
    --dataset data/hydra_xauusd_m5_master_clean.parquet \
    --label-column label_72b --return-column fwd_ret_72b \
    --horizon-bars 72 --folds 5 --embargo-bars 288 \
    --threshold 0.55 --output-dir reports/nonoverlap_master_72b
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
import time
import warnings as _warnings
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_warnings.filterwarnings("ignore", message=".*does not have valid feature names.*", category=UserWarning)

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

TIME_COLUMN_CANDIDATES = (
    "time", "timestamp", "datetime", "date", "bar_time", "open_time", "close_time",
)
PRICE_COLUMN_CANDIDATES = (
    "close", "A_close", "xau_close", "XAUUSD_close", "bid_close", "mid_close",
)

DISCLAIMER = (
    "WARNING: This is bar-return validation, NOT live execution. "
    "Does NOT model spread, slippage, partial fills, requotes, OHLC path risk, "
    "margin calls, swap costs, or broker execution mechanics. "
    "Results are an UPPER BOUND on real-world performance."
)


# ─────────────────────────────────────────────────────────────────────────────
# Data structures
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Fold:
    number: int
    train_start: int
    train_end: int
    embargo_start: int
    embargo_end: int
    test_start: int
    test_end: int


@dataclass
class Trade:
    fold: int
    entry_bar: int
    exit_bar: int
    direction: int  # +1 long, -1 short
    confidence: float
    realized_return: float
    source: str  # "model", "baseline_long", "baseline_short", etc.


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

class HelpFormatter(
    argparse.ArgumentDefaultsHelpFormatter,
    argparse.RawDescriptionHelpFormatter,
):
    pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Non-overlapping event-style signal validation for HYDRA.\n\n"
            "Converts walk-forward model probabilities into discrete non-overlapping\n"
            "trades with fixed hold period. Compares against baselines under identical\n"
            "non-overlap rules.\n\n"
            + DISCLAIMER
        ),
        formatter_class=HelpFormatter,
        epilog=(
            "Examples:\n"
            "  python scripts/validate_hydra_nonoverlap.py \\\n"
            "    --dataset data/hydra_xauusd_m5_master_clean.parquet \\\n"
            "    --label-column label_72b --return-column fwd_ret_72b \\\n"
            "    --horizon-bars 72 --folds 5 --embargo-bars 288 \\\n"
            "    --threshold 0.55 --output-dir reports/nonoverlap_master_72b\n"
        ),
    )
    parser.add_argument("--dataset", required=True, help="Path to HYDRA Parquet dataset.")
    parser.add_argument("--label-column", "--label", dest="label_column", required=True,
                        help="Classification target column (binary 0/1).")
    parser.add_argument("--return-column", required=True,
                        help="Forward-return column for realized trade PnL.")
    parser.add_argument("--horizon-bars", type=int, required=True,
                        help="Hold period in bars (e.g. 72 for label_72b).")
    parser.add_argument("--folds", type=int, default=5,
                        help="Number of chronological expanding walk-forward folds.")
    parser.add_argument("--embargo-bars", type=int, default=288,
                        help="Bars skipped between train and test windows.")
    parser.add_argument("--threshold", type=float, default=0.55,
                        help="Confidence threshold for entry (long if p>=T, short if p<=1-T).")
    parser.add_argument("--cost-bps", type=float, default=2.0,
                        help="Round-trip cost in basis points per trade.")
    parser.add_argument("--random-seeds", type=int, default=10,
                        help="Number of random baseline seeds.")
    parser.add_argument("--max-rows", type=int, default=None,
                        help="Optional first-N row cap for smoke runs.")
    parser.add_argument("--output-dir", default="reports/nonoverlap_validation",
                        help="Base output directory.")
    parser.add_argument("--model", default="lightgbm_or_sklearn_fallback",
                        choices=["lightgbm_or_sklearn_fallback", "lightgbm",
                                 "hist_gradient_boosting", "random_forest"],
                        help="Model backend.")
    parser.add_argument("--no-progress", action="store_true",
                        help="Suppress progress output.")
    return parser.parse_args()


# ─────────────────────────────────────────────────────────────────────────────
# Utilities
# ─────────────────────────────────────────────────────────────────────────────

def fail(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    raise SystemExit(2)


def require_deps():
    try:
        import numpy as np
        import pandas as pd
    except ImportError as exc:
        fail(f"missing dependency: {exc.name}")
    return np, pd


def find_column(columns: list[str], candidates: tuple[str, ...]) -> str | None:
    lower_map = {c.lower(): c for c in columns}
    for cand in candidates:
        if cand.lower() in lower_map:
            return lower_map[cand.lower()]
    return None


def load_dataset(path: Path, max_rows: int | None):
    _, pd = require_deps()
    if not path.exists():
        fail(f"dataset not found: {path}")
    df = pd.read_parquet(path)
    if max_rows and max_rows > 0:
        df = df.iloc[:max_rows].copy()
    if df.empty:
        fail("dataset has zero rows")
    return df


# ─────────────────────────────────────────────────────────────────────────────
# Walk-forward folds
# ─────────────────────────────────────────────────────────────────────────────

def make_walk_forward_folds(n_rows: int, n_folds: int, embargo_bars: int) -> list[Fold]:
    if n_folds < 2:
        fail("need at least 2 folds")
    test_size = n_rows // (n_folds + 1)
    if test_size < 1:
        fail("not enough rows for requested fold count")

    folds = []
    for idx in range(n_folds):
        train_start = 0
        train_end = test_size * (idx + 1)
        embargo_start = train_end
        embargo_end = min(train_end + embargo_bars, n_rows)
        test_start = embargo_end
        test_end = min(test_start + test_size, n_rows)

        if test_start >= test_end:
            continue

        folds.append(Fold(
            number=idx + 1,
            train_start=train_start,
            train_end=train_end,
            embargo_start=embargo_start,
            embargo_end=embargo_end,
            test_start=test_start,
            test_end=test_end,
        ))
    return folds


# ─────────────────────────────────────────────────────────────────────────────
# Feature selection (train-only)
# ─────────────────────────────────────────────────────────────────────────────

def numeric_feature_columns(df, label_col: str) -> tuple[list[str], dict]:
    _, pd = require_deps()
    np, _ = require_deps()

    exclude_patterns = [
        "label", "target", "fwd_ret", "forward", "Z4",
        "time", "date", "timestamp", "datetime",
    ]
    excluded = {"pattern": 0, "nonnumeric": 0, "label_col": 0}

    cols = []
    for c in df.columns:
        if c == label_col:
            excluded["label_col"] += 1
            continue
        cl = c.lower()
        if any(p in cl for p in exclude_patterns):
            excluded["pattern"] += 1
            continue
        if not pd.api.types.is_numeric_dtype(df[c]):
            excluded["nonnumeric"] += 1
            continue
        cols.append(c)
    return cols, excluded


def fit_train_only_transform(X_train, X_test, feature_cols):
    np, pd = require_deps()
    from sklearn.impute import SimpleImputer
    from sklearn.preprocessing import RobustScaler
    from sklearn.feature_selection import VarianceThreshold

    coverage = X_train.notna().mean()
    keep = coverage[coverage >= 0.05].index.tolist()
    if not keep:
        keep = feature_cols[:10]

    X_tr = X_train[keep].values.astype(float)
    X_te = X_test[keep].values.astype(float)

    imp = SimpleImputer(strategy="median")
    X_tr = imp.fit_transform(X_tr)
    X_te = imp.transform(X_te)

    scaler = RobustScaler()
    X_tr = scaler.fit_transform(X_tr)
    X_te = scaler.transform(X_te)

    vt = VarianceThreshold(threshold=0.0)
    X_tr = vt.fit_transform(X_tr)
    X_te = vt.transform(X_te)

    selected = [keep[i] for i, s in enumerate(vt.get_support()) if s]
    return X_tr, X_te, selected


# ─────────────────────────────────────────────────────────────────────────────
# Model
# ─────────────────────────────────────────────────────────────────────────────

def make_model(model_name: str, seed: int = 42):
    if model_name in ("lightgbm_or_sklearn_fallback", "lightgbm"):
        try:
            import lightgbm as lgb
            return "lightgbm", lgb.LGBMClassifier(
                n_estimators=200, max_depth=6, learning_rate=0.05,
                subsample=0.8, colsample_bytree=0.8, random_state=seed,
                verbosity=-1,
            )
        except ImportError:
            if model_name == "lightgbm":
                fail("lightgbm not installed")

    if model_name in ("lightgbm_or_sklearn_fallback", "hist_gradient_boosting"):
        from sklearn.ensemble import HistGradientBoostingClassifier
        return "hist_gradient_boosting", HistGradientBoostingClassifier(
            max_iter=200, max_depth=6, learning_rate=0.05, random_state=seed,
        )

    if model_name == "random_forest":
        from sklearn.ensemble import RandomForestClassifier
        return "random_forest", RandomForestClassifier(
            n_estimators=200, max_depth=8, random_state=seed, n_jobs=-1,
        )

    fail(f"unknown model: {model_name}")


def predict_proba_positive(model, X):
    np, _ = require_deps()
    if hasattr(model, "predict_proba"):
        proba = model.predict_proba(X)
        if proba.shape[1] == 2:
            return proba[:, 1]
        return proba[:, 0]
    return model.decision_function(X)


# ─────────────────────────────────────────────────────────────────────────────
# Non-overlapping trade generation
# ─────────────────────────────────────────────────────────────────────────────

def generate_nonoverlap_trades(
    probas,
    returns,
    horizon: int,
    threshold: float,
    test_start_idx: int,
    fold_num: int,
    source: str = "model",
) -> list[Trade]:
    """Generate non-overlapping trades from probability array.

    Args:
        probas: array of P(positive) for each bar in test window
        returns: array of forward returns for each bar in test window
        horizon: hold period in bars
        threshold: confidence threshold
        test_start_idx: absolute index of test window start (for trade.entry_bar)
        fold_num: fold number
        source: trade source label
    """
    np, _ = require_deps()
    trades = []
    i = 0
    n = len(probas)

    while i < n:
        p = probas[i]
        direction = 0
        if p >= threshold:
            direction = 1
        elif p <= (1.0 - threshold):
            direction = -1

        if direction != 0:
            # CRITICAL: Reject trade if full horizon doesn't fit in test fold
            # Prevents using forward returns that extend beyond fold end
            if i + horizon > n:
                # Skip this trade — not enough bars remaining for full horizon
                i += 1
                continue

            exit_bar = i + horizon - 1  # no longer need min() — already validated
            realized = float(returns[i]) if not np.isnan(returns[i]) else 0.0
            trades.append(Trade(
                fold=fold_num,
                entry_bar=test_start_idx + i,
                exit_bar=test_start_idx + exit_bar,
                direction=direction,
                confidence=float(p),
                realized_return=realized * direction,
                source=source,
            ))
            i += horizon  # skip ahead past hold period
        else:
            i += 1

    return trades


def generate_baseline_trades_always(
    n_bars: int,
    returns,
    horizon: int,
    direction: int,
    test_start_idx: int,
    fold_num: int,
    source: str,
) -> list[Trade]:
    """Always-long or always-short every horizon bars."""
    np, _ = require_deps()
    trades = []
    i = 0
    while i < n_bars:
        # CRITICAL: Reject trade if full horizon doesn't fit
        # Same logic as model-driven trades (no min() clipping)
        if i + horizon > n_bars:
            break  # stop when full horizon doesn't fit

        realized = float(returns[i]) if not np.isnan(returns[i]) else 0.0
        exit_bar = i + horizon - 1  # no min() — validated above
        trades.append(Trade(
            fold=fold_num,
            entry_bar=test_start_idx + i,
            exit_bar=test_start_idx + exit_bar,
            direction=direction,
            confidence=1.0,
            realized_return=realized * direction,
            source=source,
        ))
        i += horizon
    return trades


def generate_baseline_trades_random(
    n_bars: int,
    returns,
    horizon: int,
    seed: int,
    test_start_idx: int,
    fold_num: int,
) -> list[Trade]:
    """Random long/short every horizon bars."""
    np, _ = require_deps()
    rng = np.random.RandomState(seed)
    trades = []
    i = 0
    while i < n_bars:
        direction = 1 if rng.random() > 0.5 else -1
        realized = float(returns[i]) if not np.isnan(returns[i]) else 0.0
        exit_bar = min(i + horizon, n_bars) - 1
        trades.append(Trade(
            fold=fold_num,
            entry_bar=test_start_idx + i,
            exit_bar=test_start_idx + exit_bar,
            direction=direction,
            confidence=0.5,
            realized_return=realized * direction,
            source=f"random_seed_{seed}",
        ))
        i += horizon
    return trades


def generate_baseline_trades_momentum(
    df,
    price_col: str | None,
    test_start: int,
    test_end: int,
    returns,
    horizon: int,
    fold_num: int,
    lookback: int = 12,
) -> list[Trade]:
    """Momentum: direction = sign(close - close[lookback]) every horizon bars."""
    np, _ = require_deps()
    trades = []
    n_bars = test_end - test_start

    if price_col is None or price_col not in df.columns:
        return trades

    prices = df[price_col].iloc[test_start:test_end].values
    i = 0
    while i < n_bars:
        if i >= lookback:
            direction = 1 if prices[i] > prices[i - lookback] else -1
        else:
            direction = 1
        realized = float(returns[i]) if not np.isnan(returns[i]) else 0.0
        exit_bar = min(i + horizon, n_bars) - 1
        trades.append(Trade(
            fold=fold_num,
            entry_bar=test_start + i,
            exit_bar=test_start + exit_bar,
            direction=direction,
            confidence=0.5,
            realized_return=realized * direction,
            source="momentum",
        ))
        i += horizon
    return trades


# ─────────────────────────────────────────────────────────────────────────────
# Metrics
# ─────────────────────────────────────────────────────────────────────────────

def compute_trade_metrics(trades: list[Trade], cost_bps: float) -> dict[str, Any]:
    np, _ = require_deps()
    if not trades:
        return {
            "trade_count": 0,
            "win_rate": None,
            "avg_trade_return": None,
            "total_return_gross": None,
            "total_return_net": None,
            "max_drawdown": None,
            "long_count": 0,
            "short_count": 0,
            "flat_rate": None,
        }

    cost_per_trade = cost_bps / 10000.0
    returns_gross = [t.realized_return for t in trades]
    returns_net = [r - cost_per_trade for r in returns_gross]

    wins = sum(1 for r in returns_net if r > 0)
    total_gross = sum(returns_gross)
    total_net = sum(returns_net)

    # Max drawdown on cumulative equity
    cum = np.cumsum(returns_net)
    running_max = np.maximum.accumulate(cum)
    drawdowns = cum - running_max
    max_dd = float(np.min(drawdowns)) if len(drawdowns) > 0 else 0.0

    longs = sum(1 for t in trades if t.direction == 1)
    shorts = sum(1 for t in trades if t.direction == -1)

    return {
        "trade_count": len(trades),
        "win_rate": wins / len(trades),
        "avg_trade_return": total_net / len(trades),
        "total_return_gross": total_gross,
        "total_return_net": total_net,
        "max_drawdown": max_dd,
        "long_count": longs,
        "short_count": shorts,
    }


def build_equity_curve(trades: list[Trade], cost_bps: float) -> list[dict]:
    cost_per_trade = cost_bps / 10000.0
    equity = 0.0
    curve = []
    for i, t in enumerate(trades):
        equity += t.realized_return - cost_per_trade
        curve.append({
            "trade_num": i + 1,
            "entry_bar": t.entry_bar,
            "exit_bar": t.exit_bar,
            "direction": t.direction,
            "return_net": t.realized_return - cost_per_trade,
            "cumulative_equity": equity,
        })
    return curve


# ─────────────────────────────────────────────────────────────────────────────
# Main validation
# ─────────────────────────────────────────────────────────────────────────────

def run_validation(args: argparse.Namespace) -> dict[str, Any]:
    np, pd = require_deps()

    run_start = time.time()
    dataset_path = Path(args.dataset)
    df = load_dataset(dataset_path, args.max_rows)

    # Validate columns
    if args.label_column not in df.columns:
        fail(f"label column not found: {args.label_column}")
    if args.return_column not in df.columns:
        fail(f"return column not found: {args.return_column}")

    # Drop rows where label or return is NaN
    valid_mask = df[args.label_column].notna() & df[args.return_column].notna()
    df = df.loc[valid_mask].reset_index(drop=True)
    if len(df) < 100:
        fail("fewer than 100 valid rows after NaN drop")

    # Prepare label (binary)
    y = pd.to_numeric(df[args.label_column], errors="coerce")
    unique_vals = sorted(y.dropna().unique())
    if set(unique_vals) == {-1, 1}:
        y = ((y + 1) / 2).astype(int)
    elif set(unique_vals) <= {0, 1}:
        y = y.astype(int)
    else:
        y = (y > 0).astype(int)

    forward_returns = df[args.return_column].astype(float)
    feature_cols, exclusions = numeric_feature_columns(df, args.label_column)
    price_col = find_column(list(df.columns), PRICE_COLUMN_CANDIDATES)
    folds = make_walk_forward_folds(len(df), args.folds, args.embargo_bars)

    if not folds:
        fail("no valid folds generated")

    # Banner
    print("=" * 70)
    print("HYDRA NON-OVERLAPPING EVENT VALIDATION")
    print("=" * 70)
    print(f"  {DISCLAIMER}")
    print(f"  Dataset:      {dataset_path}")
    print(f"  Rows:         {len(df):,}")
    print(f"  Features:     {len(feature_cols):,} candidates")
    print(f"  Label:        {args.label_column}")
    print(f"  Return col:   {args.return_column}")
    print(f"  Horizon:      {args.horizon_bars} bars")
    print(f"  Threshold:    {args.threshold}")
    print(f"  Folds:        {len(folds)}")
    print(f"  Embargo:      {args.embargo_bars} bars")
    print(f"  Cost:         {args.cost_bps} bps")
    print(f"  Started:      {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("=" * 70)

    # Walk-forward
    all_model_trades: list[Trade] = []
    all_baseline_trades: dict[str, list[Trade]] = {
        "always_long": [],
        "always_short": [],
        "momentum": [],
    }
    for seed in range(args.random_seeds):
        all_baseline_trades[f"random_seed_{seed}"] = []

    for fold in folds:
        fold_start = time.time()
        if not args.no_progress:
            print(f"\n  Fold {fold.number}/{len(folds)}: train[0:{fold.train_end}] "
                  f"embargo[{fold.embargo_start}:{fold.embargo_end}] "
                  f"test[{fold.test_start}:{fold.test_end}]")

        train_slice = slice(fold.train_start, fold.train_end)
        test_slice = slice(fold.test_start, fold.test_end)

        y_train = y.iloc[train_slice].to_numpy()
        y_test = y.iloc[test_slice].to_numpy()

        if len(np.unique(y_train)) < 2:
            if not args.no_progress:
                print(f"    SKIPPED (single class in train)")
            continue

        # Train model
        X_train = df.iloc[train_slice][feature_cols]
        X_test = df.iloc[test_slice][feature_cols]
        X_train_sel, X_test_sel, selected = fit_train_only_transform(X_train, X_test, feature_cols)

        model_name, model = make_model(args.model, seed=42)
        model.fit(X_train_sel, y_train)

        # Predict probabilities
        probas = predict_proba_positive(model, X_test_sel)
        test_returns = forward_returns.iloc[test_slice].to_numpy()
        n_test = fold.test_end - fold.test_start

        # Model trades (non-overlapping)
        model_trades = generate_nonoverlap_trades(
            probas, test_returns, args.horizon_bars, args.threshold,
            fold.test_start, fold.number, source="model",
        )
        all_model_trades.extend(model_trades)

        # Baselines (same non-overlap rules)
        bl_long = generate_baseline_trades_always(
            n_test, test_returns, args.horizon_bars, 1,
            fold.test_start, fold.number, "always_long",
        )
        bl_short = generate_baseline_trades_always(
            n_test, test_returns, args.horizon_bars, -1,
            fold.test_start, fold.number, "always_short",
        )
        bl_momentum = generate_baseline_trades_momentum(
            df, price_col, fold.test_start, fold.test_end,
            test_returns, args.horizon_bars, fold.number,
        )
        all_baseline_trades["always_long"].extend(bl_long)
        all_baseline_trades["always_short"].extend(bl_short)
        all_baseline_trades["momentum"].extend(bl_momentum)

        for seed in range(args.random_seeds):
            bl_rand = generate_baseline_trades_random(
                n_test, test_returns, args.horizon_bars, seed,
                fold.test_start, fold.number,
            )
            all_baseline_trades[f"random_seed_{seed}"].extend(bl_rand)

        fold_time = time.time() - fold_start
        if not args.no_progress:
            print(f"    {len(model_trades)} trades | {fold_time:.1f}s")

    # Compute metrics
    model_metrics = compute_trade_metrics(all_model_trades, args.cost_bps)
    baseline_metrics = {}
    for name, trades in all_baseline_trades.items():
        baseline_metrics[name] = compute_trade_metrics(trades, args.cost_bps)

    # Best baseline
    best_bl_name = None
    best_bl_return = None
    for name, m in baseline_metrics.items():
        ret = m.get("total_return_net")
        if ret is not None and (best_bl_return is None or ret > best_bl_return):
            best_bl_return = ret
            best_bl_name = name

    model_net = model_metrics.get("total_return_net")
    excess = None
    if model_net is not None and best_bl_return is not None:
        excess = model_net - best_bl_return

    total_runtime = time.time() - run_start

    # Equity curve
    equity_curve = build_equity_curve(all_model_trades, args.cost_bps)

    # Summary
    summary = {
        "disclaimer": DISCLAIMER,
        "run_id": f"nonoverlap_{dataset_path.stem}_{args.label_column}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "total_runtime_seconds": round(total_runtime, 2),
        "config": {
            "dataset": str(dataset_path),
            "label_column": args.label_column,
            "return_column": args.return_column,
            "horizon_bars": args.horizon_bars,
            "threshold": args.threshold,
            "folds": args.folds,
            "embargo_bars": args.embargo_bars,
            "cost_bps": args.cost_bps,
            "random_seeds": args.random_seeds,
            "max_rows": args.max_rows,
            "model": args.model,
        },
        "dataset_info": {
            "rows": len(df),
            "feature_candidates": len(feature_cols),
            "label_positive_rate": float(y.mean()),
        },
        "model_results": model_metrics,
        "baselines": baseline_metrics,
        "best_baseline_name": best_bl_name,
        "best_baseline_return_net": best_bl_return,
        "excess_over_best_baseline": excess,
        "verdict": _verdict(model_metrics, excess),
    }

    return {
        "summary": summary,
        "trades": all_model_trades,
        "equity_curve": equity_curve,
        "baseline_trades": all_baseline_trades,
    }


def _verdict(metrics: dict, excess: float | None) -> str:
    if metrics["trade_count"] == 0:
        return "NO_TRADES"
    if excess is None:
        return "INCONCLUSIVE"
    if excess > 0 and metrics.get("win_rate", 0) and metrics["win_rate"] > 0.5:
        return "WEAK_EDGE_NONOVERLAP"
    if excess > 0:
        return "MARGINAL_EDGE"
    return "NO_EDGE"


# ─────────────────────────────────────────────────────────────────────────────
# Output writers
# ─────────────────────────────────────────────────────────────────────────────

def write_trades_csv(path: Path, trades: list[Trade]) -> None:
    fields = ["fold", "entry_bar", "exit_bar", "direction", "confidence",
              "realized_return", "source"]
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for t in trades:
            writer.writerow({
                "fold": t.fold,
                "entry_bar": t.entry_bar,
                "exit_bar": t.exit_bar,
                "direction": t.direction,
                "confidence": round(t.confidence, 6),
                "realized_return": round(t.realized_return, 8),
                "source": t.source,
            })


def write_equity_csv(path: Path, curve: list[dict]) -> None:
    if not curve:
        path.write_text("trade_num,entry_bar,exit_bar,direction,return_net,cumulative_equity\n")
        return
    fields = list(curve[0].keys())
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in curve:
            writer.writerow({k: round(v, 8) if isinstance(v, float) else v for k, v in row.items()})



def fmt_metric(value, digits: int = 4) -> str:
    """Format optional numeric metric without treating 0.0 as missing."""
    if value is None:
        return "N/A"
    try:
        if isinstance(value, float) and (value != value):
            return "N/A"
        return f"{float(value):.{digits}f}"
    except Exception:
        return str(value)


def write_summary_md(path: Path, summary: dict) -> None:
    m = summary["model_results"]
    c = summary["config"]
    lines = [
        "# HYDRA Non-Overlapping Event Validation",
        "",
        f"> {DISCLAIMER}",
        "",
        f"- **Run ID:** `{summary['run_id']}`",
        f"- **Verdict:** `{summary['verdict']}`",
        f"- **Dataset:** `{c['dataset']}`",
        f"- **Label:** `{c['label_column']}`",
        f"- **Return column:** `{c['return_column']}`",
        f"- **Horizon:** {c['horizon_bars']} bars",
        f"- **Threshold:** {c['threshold']}",
        f"- **Cost:** {c['cost_bps']} bps",
        f"- **Runtime:** {summary['total_runtime_seconds']}s",
        "",
        "## Model Results",
        "",
        f"- **Trade count:** {m['trade_count']}",
        f"- **Win rate:** {m['win_rate']:.4f}" if m['win_rate'] is not None else "- **Win rate:** N/A",
        f"- **Avg trade return (net):** {m['avg_trade_return']:.6f}" if m['avg_trade_return'] is not None else "- **Avg trade return:** N/A",
        f"- **Total return (gross):** {m['total_return_gross']:.6f}" if m['total_return_gross'] is not None else "- **Total return (gross):** N/A",
        f"- **Total return (net):** {m['total_return_net']:.6f}" if m['total_return_net'] is not None else "- **Total return (net):** N/A",
        f"- **Max drawdown:** {m['max_drawdown']:.6f}" if m['max_drawdown'] is not None else "- **Max drawdown:** N/A",
        f"- **Longs:** {m['long_count']}",
        f"- **Shorts:** {m['short_count']}",
        "",
        "## Baseline Comparison",
        "",
        f"- **Best baseline:** `{summary['best_baseline_name']}`",
        f"- **Best baseline return (net):** {summary['best_baseline_return_net']:.6f}" if summary['best_baseline_return_net'] is not None else "- **Best baseline return:** N/A",
        f"- **Excess over best baseline:** {summary['excess_over_best_baseline']:.6f}" if summary['excess_over_best_baseline'] is not None else "- **Excess:** N/A",
        "",
        "## Baselines Detail",
        "",
    ]

    for name, bm in summary["baselines"].items():
        if name.startswith("random_seed_") and not name.endswith("_0"):
            continue  # only show first random seed in MD
        ret = bm.get("total_return_net")
        wr = bm.get("win_rate")
        tc = bm.get("trade_count", 0)
        lines.append(
            f"- `{name}`: trades={tc}, "
            f"win_rate={fmt_metric(wr)}, "
            f"return_net={fmt_metric(ret, 6)}"
        )

    lines.extend([
        "",
        "## Leakage Controls",
        "",
        "- Chronological expanding walk-forward folds only.",
        "- Embargo gap enforced between train and test.",
        "- Imputer, scaler, and model fit on train folds only.",
        "- Non-overlapping trades: one position at a time, hold for horizon bars.",
        "- Forward return used only at entry bar (no overlap accumulation).",
        "",
        "## Execution Warning",
        "",
        f"> {DISCLAIMER}",
    ])

    path.write_text("\n".join(lines) + "\n")


def write_outputs(args: argparse.Namespace, results: dict) -> None:
    summary = results["summary"]
    run_dir = Path(args.output_dir) / summary["run_id"]
    run_dir.mkdir(parents=True, exist_ok=True)

    trades_path = run_dir / "trades.csv"
    equity_path = run_dir / "equity.csv"
    summary_json_path = run_dir / "summary.json"
    summary_md_path = run_dir / "summary.md"

    write_trades_csv(trades_path, results["trades"])
    write_equity_csv(equity_path, results["equity_curve"])

    # JSON-safe summary (no Trade objects in baselines)
    json_summary = json.loads(json.dumps(summary, default=str))
    summary_json_path.write_text(json.dumps(json_summary, indent=2) + "\n")

    write_summary_md(summary_md_path, summary)

    print(f"\nRUN_ID: {summary['run_id']}")
    print(f"VERDICT: {summary['verdict']}")
    print(f"TRADES: {trades_path}")
    print(f"EQUITY: {equity_path}")
    print(f"SUMMARY_JSON: {summary_json_path}")
    print(f"SUMMARY_MD: {summary_md_path}")


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    args = parse_args()
    results = run_validation(args)
    write_outputs(args, results)

    m = results["summary"]["model_results"]
    print(f"\n{'=' * 70}")
    print(f"TRADE COUNT:    {m['trade_count']}")
    print(f"WIN RATE:       {fmt_metric(m.get('win_rate'))}")
    print(f"TOTAL NET:      {fmt_metric(m.get('total_return_net'), 6)}")
    print(f"MAX DRAWDOWN:   {fmt_metric(m.get('max_drawdown'), 6)}")
    print(f"EXCESS/BEST BL: {results['summary']['excess_over_best_baseline']:.6f}"
          if results['summary']['excess_over_best_baseline'] is not None else "EXCESS/BEST BL: N/A")
    print(f"{'=' * 70}")
    print(f"\n  {DISCLAIMER}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
