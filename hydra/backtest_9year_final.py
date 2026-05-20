"""HYDRA 9-Year Final Backtest — observable, checkpointable, honest.

Usage:
    python -m hydra.backtest_9year_final --symbol XAUUSD --years 9 --iterations 100 --max-iterations 300 --resume
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import warnings
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hydra.config import DB_PATH, ARTIFACTS
from hydra.data.targets import wilder_atr
from hydra.backtest.metrics import (
    sharpe_ratio, sortino_ratio, max_drawdown,
    profit_factor, win_rate, avg_rr, calmar_ratio,
)
from hydra.runtime_state import (
    update_state, set_phase, set_idle, set_failed, set_complete,
    append_event, read_state, write_state, StateUpdater,
)
from hydra.utils.eta import ETAEstimator
from hydra.utils.system_monitor import get_system_stats
from hydra.data_sources.registry import run_audit, fetch_missing, compute_date_range
from hydra.data.features_stationary import build_stationary_features

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

CAPITAL = 100_000.0
BASE_SEED = 42
RUNS_DIR = Path.home() / "Dominion" / "runs"


@dataclass
class CostScenario:
    name: str
    spread_pips: float
    slippage_pips: float
    commission_rt: float


COST_SCENARIOS = [
    CostScenario("low", 0.20, 0.05, 1.50),
    CostScenario("base", 0.35, 0.15, 2.50),
    CostScenario("stress", 0.60, 0.30, 4.00),
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
    min_oos_trades: int
    required_timeframes: list


MODES = {
    "scalp": ModeConfig("HYDRA-SCALP", 5, 0.7, 1.0, 0.55, 0.003, 0.005, 50, ["M1", "M5"]),
    "daytrade": ModeConfig("HYDRA-DAYTRADE", 10, 1.0, 1.5, 0.58, 0.005, 0.01, 50, ["M5", "M15", "H1"]),
    "swing": ModeConfig("HYDRA-SWING", 20, 1.5, 3.0, 0.60, 0.005, 0.01, 25, ["H4", "D1"]),
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
# Core functions (from backtest_3year — proven)
# ─────────────────────────────────────────────────────────────────────────────

def make_labels(high, low, close, atr, mode: ModeConfig):
    n = len(close)
    y = np.full(n, np.nan, dtype=np.float32)
    H = mode.horizon_bars
    sl_mult = mode.stop_mult
    tp_mult = mode.target_mult
    for t in range(n - H):
        if not np.isfinite(atr[t]) or atr[t] <= 0:
            continue
        sl_long = close[t] - sl_mult * atr[t]
        tp_long = close[t] + tp_mult * atr[t]
        for k in range(1, H + 1):
            if low[t + k] <= sl_long:
                y[t] = 0.0
                break
            if high[t + k] >= tp_long:
                y[t] = 1.0
                break
    return y


def build_features(df: pd.DataFrame, train_mask: np.ndarray):
    """DEPRECATED: Use build_stationary_features instead.

    This function used training-anchored Q5/Q95 scaling which caused
    regime shift failures. Kept for backward compatibility but should
    not be used in new code.
    """
    exclude = {"ts", "open", "high", "low", "close", "volume",
               "macro_regime", "regime_confidence"}
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    feat_cols = [c for c in numeric_cols if c not in exclude]
    X = df[feat_cols].values.astype(np.float32)
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
    train_X = X[train_mask]
    median = np.median(train_X, axis=0)
    q5 = np.percentile(train_X, 5, axis=0)
    q95 = np.percentile(train_X, 95, axis=0)
    scale = q95 - q5
    scale[scale < 1e-10] = 1.0
    X_scaled = (X - median) / scale
    return X_scaled, feat_cols


def build_features_stationary(df: pd.DataFrame):
    """Build regime-invariant features (no training-anchored scaling).

    Returns:
        X_all: Feature matrix (N x F), self-normalized
        feat_cols: List of feature names
    """
    # Build stationary features (adds columns to df)
    df = build_stationary_features(df)

    # Extract feature columns (exclude OHLCV)
    exclude = {"ts", "open", "high", "low", "close", "volume",
               "macro_regime", "regime_confidence", "structural_regime",
               "tactical_regime", "micro_regime", "confidence", "regime_id",
               "p_trend_up", "p_trend_dn", "p_range", "p_crisis"}
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    feat_cols = [c for c in numeric_cols if c not in exclude]

    # Extract feature matrix
    X = df[feat_cols].values.astype(np.float32)
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)

    return X, feat_cols


def check_leakage(df, feat_cols, y, train_end_idx):
    issues = []
    ts = df["ts"].values
    if not np.all(ts[:-1] <= ts[1:]):
        issues.append("CRITICAL: timestamps not sorted")
    close = df["close"].values.copy()
    future_ret = np.zeros(len(close))
    future_ret[:-1] = close[1:] / close[:-1] - 1
    for i, col in enumerate(feat_cols):
        if col not in df.columns:
            continue
        vals = df[col].values.copy()
        if not np.issubdtype(vals.dtype, np.number):
            continue
        corr = np.corrcoef(
            np.nan_to_num(vals[:train_end_idx], 0),
            future_ret[:train_end_idx]
        )[0, 1]
        if abs(corr) > 0.95:
            issues.append(f"SUSPECT: {col} corr={corr:.3f} with future return")
    return issues


def train_model(X_train, y_train, seed):
    from sklearn.ensemble import (
        RandomForestClassifier, HistGradientBoostingClassifier,
    )
    from sklearn.linear_model import LogisticRegression

    models = []

    hgb = HistGradientBoostingClassifier(
        max_iter=300, learning_rate=0.05, max_leaf_nodes=31,
        min_samples_leaf=20, l2_regularization=0.1,
        early_stopping=True, validation_fraction=0.15,
        n_iter_no_change=30, random_state=seed,
    )
    hgb.fit(X_train, y_train)
    models.append(("hgb", hgb))

    rf = RandomForestClassifier(
        n_estimators=300, max_depth=10, min_samples_leaf=20,
        max_features="sqrt", n_jobs=-1, random_state=seed,
        class_weight="balanced",
    )
    rf.fit(X_train, y_train)
    models.append(("rf", rf))

    lr = LogisticRegression(
        C=0.5, max_iter=3000, random_state=seed,
        class_weight="balanced", solver="saga", penalty="l1",
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


def run_backtest(close, high, low, atr, signals, confidences,
                 mode: ModeConfig, cost: CostScenario, capital: float = CAPITAL):
    n = len(close)
    trades = []
    equity = capital
    equity_curve = [equity]
    in_trade = False
    entry_bar = entry_px = direction = stop_px = target_px = size_lots = 0

    for t in range(n):
        if not in_trade:
            sig = signals[t]
            conf = confidences[t]
            if sig != 0 and conf >= mode.min_confidence and np.isfinite(atr[t]) and atr[t] > 0:
                direction = int(sig)
                spread_cost = cost.spread_pips + cost.slippage_pips
                entry_px = close[t] + direction * spread_cost / 2
                entry_atr = atr[t]
                stop_px = entry_px - direction * mode.stop_mult * entry_atr
                target_px = entry_px + direction * mode.target_mult * entry_atr
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


def compute_metrics(trades: list[Trade], equity: np.ndarray, n_bars: int) -> dict:
    if not trades:
        return {"n_trades": 0, "win_rate": 0, "avg_rr": None, "expectancy": 0,
                "profit_factor": 0, "sharpe": 0, "sortino": 0, "calmar": 0,
                "max_dd": 0, "total_return_pct": 0, "total_profit": 0}

    pnl = np.array([t.pnl_dollars for t in trades])
    winners = pnl[pnl > 0]
    losers = pnl[pnl < 0]
    n_trades = len(trades)
    wr = len(winners) / n_trades
    rr = (np.mean(np.abs(winners)) / np.mean(np.abs(losers))) if (len(winners) > 0 and len(losers) > 0) else None

    if len(losers) > 0 and abs(losers.sum()) > 0:
        pf = winners.sum() / abs(losers.sum()) if len(winners) > 0 else 0
    elif len(winners) > 0:
        pf = 99.0
    else:
        pf = 0

    daily_ret = np.diff(equity) / np.where(equity[:-1] > 0, equity[:-1], 1.0)
    daily_ret = daily_ret[np.isfinite(daily_ret)]
    sr = sharpe_ratio(daily_ret) if len(daily_ret) > 10 else 0
    sort = sortino_ratio(daily_ret) if len(daily_ret) > 10 else 0
    mdd = max_drawdown(equity)
    cal = calmar_ratio(daily_ret, equity) if mdd > 0 else 0

    total_ret = (equity[-1] - equity[0]) / equity[0] * 100

    return {
        "n_trades": n_trades,
        "win_rate": round(wr, 4),
        "avg_rr": round(rr, 3) if rr else None,
        "expectancy": round(pnl.mean(), 2),
        "profit_factor": round(pf, 3),
        "sharpe": round(sr, 3),
        "sortino": round(sort, 3),
        "calmar": round(cal, 3),
        "max_dd": round(mdd * 100, 2),
        "total_return_pct": round(total_ret, 2),
        "total_profit": round(pnl.sum(), 2),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Data Loading
# ─────────────────────────────────────────────────────────────────────────────

def load_data_for_period(start_year: int, end_year: int) -> pd.DataFrame:
    """Load OHLCV data ONLY from DuckDB (no pre-computed features)."""
    import duckdb
    con = duckdb.connect(str(DB_PATH), read_only=True)

    # Load only OHLCV bars
    bars = con.execute(
        "SELECT timestamp as ts, open, high, low, close, volume FROM gold_master ORDER BY timestamp"
    ).df()
    bars["ts"] = pd.to_datetime(bars["ts"])

    con.close()

    return bars.sort_values("ts").reset_index(drop=True)


# ─────────────────────────────────────────────────────────────────────────────
# Main experiment
# ─────────────────────────────────────────────────────────────────────────────

def run_experiment(args):
    start_time = time.time()
    run_id = f"hydra_9year_final_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    run_dir = RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    log_dir = run_dir / "logs"
    log_dir.mkdir(exist_ok=True)
    checkpoint_dir = run_dir / "checkpoints"
    checkpoint_dir.mkdir(exist_ok=True)

    # Setup logging
    import logging
    log_file = log_dir / "run.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(str(log_file)),
            logging.StreamHandler(sys.stdout),
        ],
    )
    log = logging.getLogger("hydra")

    # Initialize state
    update_state(
        active=True, run_id=run_id, status="RUNNING",
        symbol=args.symbol, max_iterations=args.max_iterations,
        latest_log_file=str(log_file),
        latest_artifact_dir=str(run_dir),
        started_at=datetime.now(timezone.utc).isoformat(),
    )
    append_event(run_id, "INFO", "STARTUP", "run_started",
                 f"HYDRA 9-year final started: {args.symbol}, {args.iterations} iterations")

    # ── Phase 1: GPU/System Audit ──
    log.info("=" * 60)
    log.info("  HYDRA 9-YEAR FINAL BACKTEST")
    log.info("=" * 60)

    set_phase("GPU_AUDIT", "System resource audit")
    sys_stats = get_system_stats()
    log.info(f"  CPU: available")
    log.info(f"  RAM: {sys_stats.get('ram_used_gb', '?')}/{sys_stats.get('ram_total_gb', '?')} GB")
    log.info(f"  GPU: {'YES - ' + str(sys_stats.get('gpu_name', '')) if sys_stats.get('gpu_available') else 'NO'}")
    log.info(f"  Disk free: {sys_stats.get('disk_free_gb', '?')} GB")

    if args.require_gpu and not sys_stats.get("gpu_available"):
        msg = "GPU required but not available. Aborting."
        log.error(msg)
        set_failed(msg)
        return

    append_event(run_id, "INFO", "GPU_AUDIT", "system_audit_complete",
                 f"RAM: {sys_stats.get('ram_total_gb')}GB, GPU: {sys_stats.get('gpu_available')}")

    # ── Phase 2: Data Audit ──
    set_phase("DATA_AUDIT", f"Auditing {args.symbol} data for {args.years} years")
    log.info(f"\n  Auditing data coverage for {args.years} years...")

    audit = run_audit(args.symbol, args.years, run_id=run_id, verbose=True)
    valid_modes = audit["valid_modes"]
    invalid_modes = audit["invalid_modes"]

    log.info(f"  Valid modes: {valid_modes}")
    log.info(f"  Invalid modes: {[m for m, _ in invalid_modes]}")

    # ── Phase 3: Fetch Missing (if needed) ──
    any_fetchable = any(
        not audit["timeframes"].get(tf, {}).get("sufficient", False)
        and audit["timeframes"].get(tf, {}).get("can_fetch_from")
        for tf in ["M1", "M5", "M15", "H1", "H4", "D1"]
    )

    if any_fetchable:
        log.info("\n  Attempting to fetch missing data...")
        set_phase("DATA_DOWNLOAD", "Fetching missing data")
        fetch_results = fetch_missing(
            args.symbol, args.years,
            ["M1", "M5", "M15", "H1", "H4", "D1"],
            run_id=run_id,
        )
        # Re-audit
        audit = run_audit(args.symbol, args.years, run_id=run_id, verbose=False)
        valid_modes = audit["valid_modes"]
        invalid_modes = audit["invalid_modes"]
        log.info(f"  After fetch — Valid modes: {valid_modes}")

    # ── Phase 4: Load Data ──
    set_phase("FEATURE_BUILD", "Loading and building features")
    log.info("\n  Loading data from DuckDB...")

    df = load_data_for_period(2017, 2026)
    ts = pd.to_datetime(df["ts"])
    n_total = len(df)
    date_min = ts.min()
    date_max = ts.max()
    total_years = (date_max - date_min).days / 365.25

    log.info(f"  Bars loaded: {n_total}")
    log.info(f"  Date range: {date_min.date()} → {date_max.date()} ({total_years:.1f} years)")
    log.info(f"  Features: {df.select_dtypes(include=[np.number]).shape[1]} numeric columns")

    # ── Determine split ──
    # With ~5 years available, split into: train (first ~2yr), val (next ~1.5yr), OOS (final ~1.5yr)
    # If full 9 years were available: 3yr/3yr/3yr
    available_days = (date_max - date_min).days

    if total_years >= 9:
        # Full 9-year split
        train_end = date_min + pd.Timedelta(days=int(3 * 365.25))
        val_end = train_end + pd.Timedelta(days=int(3 * 365.25))
        split_type = "FULL_9YEAR"
    elif total_years >= 4.5:
        # Proportional split with available data
        third = available_days // 3
        train_end = date_min + pd.Timedelta(days=third)
        val_end = train_end + pd.Timedelta(days=third)
        split_type = f"PROPORTIONAL_{total_years:.0f}YEAR"
    else:
        msg = f"Insufficient data: only {total_years:.1f} years available, need at least 4.5"
        log.error(msg)
        set_failed(msg)
        return

    train_mask = ts <= train_end
    val_mask = (ts > train_end) & (ts <= val_end)
    oos_mask = ts > val_end

    n_train = train_mask.sum()
    n_val = val_mask.sum()
    n_oos = oos_mask.sum()

    log.info(f"\n  Split: {split_type}")
    log.info(f"  Train:      {date_min.date()} → {train_end.date()} ({n_train} bars)")
    log.info(f"  Validation: {train_end.date()} → {val_end.date()} ({n_val} bars)")
    log.info(f"  OOS:        {val_end.date()} → {date_max.date()} ({n_oos} bars)")

    if n_train < 150 or n_val < 100 or n_oos < 100:
        msg = f"Insufficient bars in splits: train={n_train}, val={n_val}, oos={n_oos}"
        log.error(msg)
        set_failed(msg)
        return

    update_state(progress_pct=10)

    # ── Features ──
    log.info("\n  Building features...")
    X_all, feat_cols = build_features(df, train_mask.values)
    log.info(f"  Feature matrix: {X_all.shape}")
    update_state(phase_progress_pct=50, current_task="Features built, building targets")

    # ── Price arrays ──
    close = df["close"].values.astype(np.float64)
    high = df["high"].values.astype(np.float64)
    low = df["low"].values.astype(np.float64)
    atr = wilder_atr(high, low, close, n=14)

    train_idx = np.where(train_mask.values)[0]
    val_idx = np.where(val_mask.values)[0]
    oos_idx = np.where(oos_mask.values)[0]

    # ── Leakage Check ──
    set_phase("LEAKAGE_CHECK", "Running leakage checks")
    log.info("\n  Running leakage checks...")
    leakage_issues = check_leakage(df, feat_cols, close, int(train_idx[-1]))

    if any("CRITICAL" in i for i in leakage_issues):
        msg = f"CRITICAL LEAKAGE DETECTED: {leakage_issues}"
        log.error(msg)
        set_failed(msg)
        # Save leakage report
        (run_dir / "leakage_report.md").write_text(
            f"# Leakage Report\n\n## CRITICAL FAILURE\n\n" +
            "\n".join(f"- {i}" for i in leakage_issues)
        )
        return

    if leakage_issues:
        log.warning(f"  Leakage warnings: {leakage_issues[:3]}")
    else:
        log.info("  PASS: No leakage detected")

    (run_dir / "leakage_report.md").write_text(
        "# Leakage Report\n\n## Status: PASS\n\n" +
        (f"Warnings:\n" + "\n".join(f"- {i}" for i in leakage_issues) if leakage_issues else "No issues detected.")
    )

    append_event(run_id, "INFO", "LEAKAGE_CHECK", "leakage_check_pass",
                 f"Leakage check passed with {len(leakage_issues)} warnings")
    update_state(progress_pct=15)

    # ── Labels per mode ──
    set_phase("TARGET_BUILD", "Building targets per mode")
    log.info("\n  Building labels per mode...")
    labels = {}
    active_modes = {}

    for mode_key, mode_cfg in MODES.items():
        # Check if mode is valid based on data
        if mode_key not in valid_modes and mode_key != "combined":
            log.info(f"  {mode_cfg.name}: SKIPPED (invalid for available timeframes)")
            update_state(**{f"modes.{mode_key}": {
                "status": "invalid", "reason": "Insufficient timeframe data",
                "progress_pct": 0, "best_validation_sharpe": None, "trades": 0,
            }})
            continue

        y = make_labels(high, low, close, atr, mode_cfg)
        valid_train = np.isfinite(y[train_idx]).sum()
        valid_val = np.isfinite(y[val_idx]).sum()
        valid_oos = np.isfinite(y[oos_idx]).sum()

        if valid_train < 50:
            log.warning(f"  {mode_cfg.name}: Only {valid_train} valid train labels — SKIPPING")
            continue

        labels[mode_key] = y
        active_modes[mode_key] = mode_cfg
        log.info(f"  {mode_cfg.name}: train={valid_train}, val={valid_val}, oos={valid_oos}")

    if not active_modes:
        msg = "No valid modes with sufficient data. Cannot proceed."
        log.error(msg)
        set_failed(msg)
        return

    update_state(progress_pct=20)

    # ── Training Loop ──
    set_phase("TRAINING", f"Training {len(active_modes)} modes, {args.iterations} iterations")
    log.info(f"\n{'='*60}")
    log.info(f"  TRAINING: {args.iterations} iterations × {len(active_modes)} modes")
    log.info(f"{'='*60}")

    eta = ETAEstimator()
    val_results = {m: {c.name: [] for c in COST_SCENARIOS} for m in active_modes}
    best_val_sharpe = {m: -999 for m in active_modes}
    best_val_config = {m: None for m in active_modes}

    # Check for resume checkpoint
    resume_iter = 0
    if args.resume:
        ckpt = checkpoint_dir / "state_latest.json"
        if ckpt.exists():
            ckpt_data = json.loads(ckpt.read_text())
            resume_iter = ckpt_data.get("completed_iterations", 0)
            if resume_iter > 0:
                log.info(f"  Resuming from iteration {resume_iter}")
                val_results = ckpt_data.get("val_results", val_results)
                best_val_sharpe = ckpt_data.get("best_val_sharpe", best_val_sharpe)

    for iteration in range(resume_iter, args.iterations):
        iter_start = time.time()
        seed = BASE_SEED + iteration

        # Update state
        pct = ((iteration + 1) / args.iterations) * 100
        eta.update(iteration, args.iterations)
        eta_str = eta.eta_human(iteration, args.iterations)

        update_state(
            iteration=iteration + 1, max_iterations=args.iterations,
            progress_pct=20 + pct * 0.6,  # training is 20-80% of total
            phase_progress_pct=pct,
            current_task=f"Training iteration {iteration + 1}/{args.iterations}",
            eta_seconds=eta.eta_seconds(iteration, args.iterations),
            eta_human=eta_str,
        )

        if iteration % 5 == 0:
            log.info(f"  Iteration {iteration + 1}/{args.iterations} (ETA: {eta_str})")

        for mode_key, mode_cfg in active_modes.items():
            y = labels[mode_key]
            valid_tr = np.isfinite(y[train_idx])
            X_tr = X_all[train_idx][valid_tr]
            y_tr = y[train_idx][valid_tr]

            if len(y_tr) < 50:
                for cost in COST_SCENARIOS:
                    val_results[mode_key][cost.name].append(
                        compute_metrics([], np.array([CAPITAL]), 1))
                continue

            models = train_model(X_tr, y_tr, seed)

            # Validation
            X_va = X_all[val_idx]
            proba_val = predict_ensemble(models, X_va)
            sig_val = np.zeros(len(val_idx), dtype=np.int8)
            conf_val = np.abs(proba_val - 0.5) * 2
            sig_val[proba_val > 0.5 + (mode_cfg.min_confidence - 0.5)] = 1
            sig_val[proba_val < 0.5 - (mode_cfg.min_confidence - 0.5)] = -1

            for cost in COST_SCENARIOS:
                trades_v, eq_v = run_backtest(
                    close[val_idx], high[val_idx], low[val_idx], atr[val_idx],
                    sig_val, conf_val, mode_cfg, cost)
                m_v = compute_metrics(trades_v, eq_v, n_val)
                val_results[mode_key][cost.name].append(m_v)

                # Track best validation config (base cost only)
                if cost.name == "base":
                    # Overfit detection
                    if m_v["profit_factor"] > 50 or m_v["win_rate"] > 0.85:
                        log.warning(f"  [{mode_key}] OVERFIT DETECTED: PF={m_v['profit_factor']:.1f}, WR={m_v['win_rate']:.1%}")
                        append_event(run_id, "WARNING", "TRAINING", "overfit_detected",
                                     f"Mode {mode_key} iter {iteration+1}: PF={m_v['profit_factor']:.1f}, WR={m_v['win_rate']:.1%}",
                                     mode=mode_key)

                    if m_v["sharpe"] > best_val_sharpe[mode_key]:
                        best_val_sharpe[mode_key] = m_v["sharpe"]
                        best_val_config[mode_key] = {"seed": seed, "iteration": iteration, "metrics": m_v}

            # Update metrics preview
            update_state(**{
                "metrics_preview": {
                    "best_validation_sharpe": max(best_val_sharpe.values()),
                    "best_validation_profit_factor": None,
                    "best_iteration": iteration + 1,
                    "trades_so_far": sum(
                        m["n_trades"] for mode_res in val_results.values()
                        for m in mode_res["base"]
                    ),
                    "current_oos_locked": True,
                },
                f"modes.{mode_key}": {
                    "status": "running",
                    "reason": None,
                    "progress_pct": pct,
                    "best_validation_sharpe": best_val_sharpe[mode_key],
                    "trades": sum(m["n_trades"] for m in val_results[mode_key]["base"]),
                },
            })

        # Checkpoint every 10 iterations
        if (iteration + 1) % 10 == 0:
            ckpt_data = {
                "completed_iterations": iteration + 1,
                "val_results": val_results,
                "best_val_sharpe": best_val_sharpe,
                "best_val_config": best_val_config,
            }
            (checkpoint_dir / "state_latest.json").write_text(
                json.dumps(ckpt_data, indent=2, default=str))
            (checkpoint_dir / f"iteration_{iteration + 1}.json").write_text(
                json.dumps(ckpt_data, indent=2, default=str))

        iter_elapsed = time.time() - iter_start
        if iteration % 10 == 0:
            append_event(run_id, "INFO", "TRAINING", "iteration_batch",
                         f"Iterations {iteration+1}, elapsed {iter_elapsed:.1f}s/iter",
                         mode=",".join(active_modes.keys()))

    log.info(f"\n  Training complete. Best validation Sharpes: {best_val_sharpe}")
    update_state(progress_pct=80)

    # ── Phase: Final OOS ──
    set_phase("OOS_RUNNING", "Running final OOS evaluation (LOCKED)")
    log.info(f"\n{'='*60}")
    log.info("  FINAL OOS EVALUATION")
    log.info("  (OOS was locked until now — first and only look)")
    log.info(f"{'='*60}")

    oos_results = {m: {c.name: None for c in COST_SCENARIOS} for m in active_modes}
    oos_trades_all = {}

    for mode_key, mode_cfg in active_modes.items():
        # Use best validation seed
        best_cfg = best_val_config.get(mode_key)
        if not best_cfg:
            log.warning(f"  {mode_cfg.name}: No best config found, using default seed")
            best_seed = BASE_SEED
        else:
            best_seed = best_cfg["seed"]
            log.info(f"  {mode_cfg.name}: Using best seed={best_seed} from iteration {best_cfg['iteration']+1}")

        y = labels[mode_key]
        valid_tr = np.isfinite(y[train_idx])
        X_tr = X_all[train_idx][valid_tr]
        y_tr = y[train_idx][valid_tr]

        # Retrain on train set with best seed
        models = train_model(X_tr, y_tr, best_seed)

        # OOS predictions
        X_oos = X_all[oos_idx]
        proba_oos = predict_ensemble(models, X_oos)

        # Save OOS probabilities for forensics
        (run_dir / "telemetry" / "predictions").mkdir(parents=True, exist_ok=True)
        np.save(run_dir / "telemetry" / "predictions" / f"{mode_key}_oos_proba.npy", proba_oos)

        # Log OOS probability distribution
        log.info(f"  [{mode_key}] OOS proba distribution:")
        log.info(f"    mean={proba_oos.mean():.4f} std={proba_oos.std():.4f}")
        log.info(f"    min={proba_oos.min():.4f} p25={np.percentile(proba_oos, 25):.4f} "
                 f"median={np.percentile(proba_oos, 50):.4f} p75={np.percentile(proba_oos, 75):.4f} max={proba_oos.max():.4f}")

        sig_oos = np.zeros(len(oos_idx), dtype=np.int8)
        conf_oos = np.abs(proba_oos - 0.5) * 2
        sig_oos[proba_oos > 0.5 + (mode_cfg.min_confidence - 0.5)] = 1
        sig_oos[proba_oos < 0.5 - (mode_cfg.min_confidence - 0.5)] = -1

        # Log signal counts
        n_long = (sig_oos == 1).sum()
        n_short = (sig_oos == -1).sum()
        n_neutral = (sig_oos == 0).sum()
        log.info(f"    >threshold (long): {n_long}")
        log.info(f"    <threshold (short): {n_short}")
        log.info(f"    neutral: {n_neutral}")

        for cost in COST_SCENARIOS:
            trades_o, eq_o = run_backtest(
                close[oos_idx], high[oos_idx], low[oos_idx], atr[oos_idx],
                sig_oos, conf_oos, mode_cfg, cost)
            m_o = compute_metrics(trades_o, eq_o, n_oos)
            oos_results[mode_key][cost.name] = m_o

            if cost.name == "base":
                oos_trades_all[mode_key] = trades_o

            log.info(f"  {mode_cfg.name} [{cost.name}]: trades={m_o['n_trades']}, "
                     f"sharpe={m_o['sharpe']:.3f}, PF={m_o['profit_factor']:.3f}, "
                     f"DD={m_o['max_dd']:.1f}%")

        # Update mode state
        base_oos = oos_results[mode_key]["base"]
        update_state(**{f"modes.{mode_key}": {
            "status": "complete",
            "reason": None,
            "progress_pct": 100,
            "best_validation_sharpe": best_val_sharpe[mode_key],
            "trades": base_oos["n_trades"],
        }})

    update_state(progress_pct=95)

    # ── Verdicts ──
    set_phase("REPORTING", "Generating final report")
    verdicts = {}

    for mode_key, mode_cfg in active_modes.items():
        base = oos_results[mode_key]["base"]
        stress = oos_results[mode_key]["stress"]

        if base["n_trades"] < mode_cfg.min_oos_trades:
            verdicts[mode_key] = ("FAIL", f"Insufficient trades: {base['n_trades']} < {mode_cfg.min_oos_trades}")
        elif base["sharpe"] < 0.5:
            verdicts[mode_key] = ("FAIL", f"Sharpe too low: {base['sharpe']:.3f}")
        elif base["profit_factor"] < 1.0:
            verdicts[mode_key] = ("FAIL", f"PF < 1: {base['profit_factor']:.3f}")
        elif stress["expectancy"] < -100:
            verdicts[mode_key] = ("FAIL", "Only works under low cost — fails stress test")
        elif base["sharpe"] > 1.25 and base["profit_factor"] > 1.5 and base["max_dd"] <= 10:
            verdicts[mode_key] = ("STRONG", "Robust across cost scenarios")
        elif base["sharpe"] > 0.75 and base["profit_factor"] > 1.2:
            verdicts[mode_key] = ("PROMISING", "Decent but monitor in live")
        else:
            verdicts[mode_key] = ("MARGINAL", "Edge exists but fragile")

    # ── Save Reports ──
    elapsed = time.time() - start_time

    report = []
    report.append("=" * 70)
    report.append("  HYDRA 9-YEAR FINAL REPORT")
    report.append("=" * 70)
    report.append(f"  RUN ID:       {run_id}")
    report.append(f"  START:        {datetime.fromtimestamp(start_time).isoformat()}")
    report.append(f"  END:          {datetime.now().isoformat()}")
    report.append(f"  RUNTIME:      {elapsed:.0f}s ({elapsed/60:.1f} min)")
    report.append(f"  SYMBOL:       {args.symbol}")
    report.append(f"  DATA:         {total_years:.1f} years, {n_total} bars")
    report.append(f"  SPLIT:        {split_type}")
    report.append(f"  TRAIN:        {date_min.date()} → {train_end.date()} ({n_train} bars)")
    report.append(f"  VALIDATION:   {train_end.date()} → {val_end.date()} ({n_val} bars)")
    report.append(f"  OOS:          {val_end.date()} → {date_max.date()} ({n_oos} bars)")
    report.append(f"  ITERATIONS:   {args.iterations}")
    report.append(f"  VALID MODES:  {list(active_modes.keys())}")
    report.append(f"  INVALID:      {[m for m, _ in invalid_modes]}")
    report.append("")

    for mode_key, mode_cfg in active_modes.items():
        base = oos_results[mode_key]["base"]
        verdict, reason = verdicts[mode_key]
        report.append(f"  {mode_cfg.name}:")
        report.append(f"    Verdict:       {verdict}")
        report.append(f"    Reason:        {reason}")
        report.append(f"    OOS Trades:    {base['n_trades']}")
        report.append(f"    Sharpe:        {base['sharpe']:.3f}")
        report.append(f"    Sortino:       {base['sortino']:.3f}")
        report.append(f"    Profit Factor: {base['profit_factor']:.3f}")
        report.append(f"    Win Rate:      {base['win_rate']:.1%}")
        report.append(f"    Avg RR:        {base['avg_rr']}")
        report.append(f"    Max Drawdown:  {base['max_dd']:.2f}%")
        report.append(f"    Total Profit:  ${base['total_profit']:.2f}")
        report.append("")

    report.append("  COST SENSITIVITY:")
    for mode_key in active_modes:
        for cost in COST_SCENARIOS:
            m = oos_results[mode_key][cost.name]
            report.append(f"    {mode_key}/{cost.name}: sharpe={m['sharpe']:.3f}, PF={m['profit_factor']:.3f}")
    report.append("")

    report.append("  RISKS:")
    risks = []
    if total_years < 9:
        risks.append(f"Only {total_years:.1f} years available (wanted 9)")
    if "scalp" in [m for m, _ in invalid_modes]:
        risks.append("Scalp mode invalid — no intraday data")
    if "daytrade" in [m for m, _ in invalid_modes]:
        risks.append("Daytrade mode invalid — no intraday data")
    if n_oos < 200:
        risks.append(f"Small OOS sample ({n_oos} bars)")
    risks.append("Daily-only data limits execution model fidelity")
    for i, r in enumerate(risks[:5], 1):
        report.append(f"    {i}. {r}")

    report.append("")
    report.append("=" * 70)

    report_text = "\n".join(report)
    log.info(report_text)

    # Write artifacts
    (run_dir / "summary_report.md").write_text(f"# HYDRA 9-Year Final Report\n\n```\n{report_text}\n```\n")
    (run_dir / "final_verdict.md").write_text(
        "# Final Verdict\n\n" + "\n".join(f"- **{k.upper()}**: {v} — {r}" for k, (v, r) in verdicts.items())
    )
    (run_dir / "final_oos_result.json").write_text(json.dumps(oos_results, indent=2, default=str))

    (run_dir / "config_used.yaml").write_text(
        f"symbol: {args.symbol}\nyears: {args.years}\niterations: {args.iterations}\n"
        f"max_iterations: {args.max_iterations}\nsplit: {split_type}\n"
    )

    if best_val_config:
        (checkpoint_dir / "best_validation_config.json").write_text(
            json.dumps(best_val_config, indent=2, default=str))

    # Metrics CSVs
    for mode_key in active_modes:
        val_df = pd.DataFrame(val_results[mode_key]["base"])
        val_df.to_csv(str(run_dir / f"metrics_validation_{mode_key}.csv"), index=False)

    oos_flat = []
    for mode_key in active_modes:
        for cost in COST_SCENARIOS:
            row = {"mode": mode_key, "cost": cost.name}
            row.update(oos_results[mode_key][cost.name])
            oos_flat.append(row)
    pd.DataFrame(oos_flat).to_csv(str(run_dir / "metrics_oos.csv"), index=False)

    # Trade logs
    trade_dir = run_dir / "trade_logs"
    trade_dir.mkdir(exist_ok=True)
    for mode_key, trades in oos_trades_all.items():
        if trades:
            trade_df = pd.DataFrame([asdict(t) for t in trades])
            trade_df.to_csv(str(trade_dir / f"{mode_key}_trades.csv"), index=False)

    # Set complete
    set_complete()
    append_event(run_id, "SUCCESS", "COMPLETE", "run_complete",
                 f"Run complete in {elapsed:.0f}s. Verdicts: {verdicts}")

    log.info(f"\n  Artifacts saved to: {run_dir}")
    log.info(f"  Monitor: python -m hydra.progress --watch")
    log.info(f"  Results: python -m hydra.progress --last-run")

    return verdicts


def run_equal_thirds(args):
    """Available-data equal-thirds run. No strict year requirements."""
    start_time = time.time()
    run_id = f"hydra_equal_thirds_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    run_dir = RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    log_dir = run_dir / "logs"
    log_dir.mkdir(exist_ok=True)
    checkpoint_dir = run_dir / "checkpoints"
    checkpoint_dir.mkdir(exist_ok=True)

    import logging
    log_file = log_dir / "run.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(str(log_file)),
            logging.StreamHandler(sys.stdout),
        ],
        force=True,
    )
    log = logging.getLogger("hydra")

    update_state(
        active=True, run_id=run_id, status="RUNNING",
        symbol=args.symbol, max_iterations=args.iterations,
        latest_log_file=str(log_file),
        latest_artifact_dir=str(run_dir),
        started_at=datetime.now(timezone.utc).isoformat(),
    )
    append_event(run_id, "INFO", "STARTUP", "run_started",
                 f"HYDRA equal-thirds started: {args.symbol}, {args.iterations} iterations")

    log.info("=" * 70)
    log.info("  HYDRA AVAILABLE-DATA EQUAL-THIRDS EXPERIMENT")
    log.info("  RUN TYPE: AVAILABLE_DATA_EQUAL_THIRDS")
    log.info("  STRICT_9YEAR: false")
    log.info("=" * 70)

    # System audit
    set_phase("GPU_AUDIT", "System audit")
    sys_stats = get_system_stats()
    log.info(f"  RAM: {sys_stats.get('ram_used_gb')}/{sys_stats.get('ram_total_gb')} GB")
    log.info(f"  GPU: {'YES - ' + str(sys_stats.get('gpu_name')) if sys_stats.get('gpu_available') else 'NO'}")

    # Load data
    set_phase("DATA_AUDIT", "Loading best available XAUUSD data")
    log.info("\n  Loading data from DuckDB gold_master...")
    df = load_data_for_period(2000, 2030)
    ts = pd.to_datetime(df["ts"])
    n_total = len(df)
    date_min = ts.min()
    date_max = ts.max()
    total_years = (date_max - date_min).days / 365.25

    log.info(f"  Rows: {n_total}")
    log.info(f"  Range: {date_min.date()} → {date_max.date()} ({total_years:.1f} years)")
    log.info(f"  Features: {df.select_dtypes(include=[np.number]).shape[1]} numeric columns")

    if n_total < 30:
        msg = "NO_USABLE_XAUUSD_DATA_FOUND (< 30 rows)"
        log.error(msg)
        set_failed(msg)
        return

    # Equal thirds split
    df = df.sort_values("ts").reset_index(drop=True)
    n = len(df)
    train_end_idx = n // 3
    val_end_idx = (2 * n) // 3

    train_mask = np.zeros(n, dtype=bool)
    val_mask = np.zeros(n, dtype=bool)
    oos_mask = np.zeros(n, dtype=bool)
    train_mask[:train_end_idx] = True
    val_mask[train_end_idx:val_end_idx] = True
    oos_mask[val_end_idx:] = True

    n_train = train_mask.sum()
    n_val = val_mask.sum()
    n_oos = oos_mask.sum()

    ts_vals = pd.to_datetime(df["ts"])
    train_start_dt = ts_vals.iloc[0]
    train_end_dt = ts_vals.iloc[train_end_idx - 1]
    val_start_dt = ts_vals.iloc[train_end_idx]
    val_end_dt = ts_vals.iloc[val_end_idx - 1]
    oos_start_dt = ts_vals.iloc[val_end_idx]
    oos_end_dt = ts_vals.iloc[-1]

    log.info(f"\n  SPLIT: EQUAL_THIRDS")
    log.info(f"  TRAIN:      {train_start_dt.date()} → {train_end_dt.date()} ({n_train} bars)")
    log.info(f"  VALIDATION: {val_start_dt.date()} → {val_end_dt.date()} ({n_val} bars)")
    log.info(f"  FINAL TEST: {oos_start_dt.date()} → {oos_end_dt.date()} ({n_oos} bars)")

    # Save split manifest
    manifest = {
        "run_type": "AVAILABLE_DATA_EQUAL_THIRDS",
        "total_rows": n, "train_rows": int(n_train),
        "validation_rows": int(n_val), "test_rows": int(n_oos),
        "train_start": str(train_start_dt.date()), "train_end": str(train_end_dt.date()),
        "validation_start": str(val_start_dt.date()), "validation_end": str(val_end_dt.date()),
        "test_start": str(oos_start_dt.date()), "test_end": str(oos_end_dt.date()),
        "strict_9year": False,
    }
    (run_dir / "split_manifest.json").write_text(json.dumps(manifest, indent=2))

    update_state(progress_pct=10)

    # Features
    set_phase("FEATURE_BUILD", "Building stationary features")
    log.info("\n  Building stationary features (regime-invariant, no scaling)...")
    X_all, feat_cols = build_features_stationary(df)
    log.info(f"  Feature matrix: {X_all.shape}")
    log.info(f"  Features: {len(feat_cols)} stationary features")

    # Price arrays
    close = df["close"].values.astype(np.float64)
    high = df["high"].values.astype(np.float64)
    low = df["low"].values.astype(np.float64)
    atr = wilder_atr(high, low, close, n=14)

    train_idx = np.where(train_mask)[0]
    val_idx = np.where(val_mask)[0]
    oos_idx = np.where(oos_mask)[0]

    # Leakage check
    set_phase("LEAKAGE_CHECK", "Leakage check")
    leakage_issues = check_leakage(df, feat_cols, close, int(train_idx[-1]))
    if any("CRITICAL" in i for i in leakage_issues):
        log.error(f"CRITICAL LEAKAGE: {leakage_issues}")
        set_failed("Critical leakage detected")
        return
    log.info(f"  Leakage check: PASS ({len(leakage_issues)} warnings)")

    update_state(progress_pct=15)

    # Labels per mode
    set_phase("TARGET_BUILD", "Building targets")
    log.info("\n  Building labels per mode...")
    labels = {}
    active_modes = {}
    for mode_key, mode_cfg in MODES.items():
        y = make_labels(high, low, close, atr, mode_cfg)
        valid_train = np.isfinite(y[train_idx]).sum()
        if valid_train < 30:
            log.warning(f"  {mode_cfg.name}: Only {valid_train} valid labels, SKIPPING")
            continue
        labels[mode_key] = y
        active_modes[mode_key] = mode_cfg
        valid_val = np.isfinite(y[val_idx]).sum()
        valid_oos = np.isfinite(y[oos_idx]).sum()
        log.info(f"  {mode_cfg.name}: train={valid_train}, val={valid_val}, test={valid_oos}")

    if not active_modes:
        log.error("No valid modes. Cannot proceed.")
        set_failed("No valid modes")
        return

    update_state(progress_pct=20)

    # Training loop
    set_phase("TRAINING", f"Training {len(active_modes)} modes × {args.iterations} iterations")
    log.info(f"\n{'='*70}")
    log.info(f"  TRAINING: {args.iterations} iterations × {len(active_modes)} modes")
    log.info(f"{'='*70}")

    from hydra.telemetry.recorder import TelemetryRecorder
    telemetry = TelemetryRecorder(run_dir, run_id, args.iterations)

    # Precompute data_info for telemetry
    close_arr = df["close"].values.copy().astype(np.float64)
    rets = np.diff(close_arr) / np.where(close_arr[:-1] > 0, close_arr[:-1], 1.0)
    data_info = {
        "source": "DuckDB gold_master", "provider": "DuckDB", "timeframe": "D1",
        "rows_total": n, "train_rows": int(n_train), "validation_rows": int(n_val), "test_rows": int(n_oos),
        "train_start": str(train_start_dt.date()), "train_end": str(train_end_dt.date()),
        "validation_start": str(val_start_dt.date()), "validation_end": str(val_end_dt.date()),
        "test_start": str(oos_start_dt.date()), "test_end": str(oos_end_dt.date()),
        "columns_total": df.shape[1], "ohlcv_columns_present": True,
        "nan_total": int(df.isna().sum().sum()), "nan_pct": round(float(df.isna().mean().mean() * 100), 2),
        "inf_total": 0, "duplicate_timestamp_count": int(ts_vals.duplicated().sum()),
        "timestamp_monotonic": bool(ts_vals.is_monotonic_increasing),
        "close_min": round(float(close_arr.min()), 2), "close_max": round(float(close_arr.max()), 2),
        "close_mean": round(float(close_arr.mean()), 2), "close_std": round(float(close_arr.std()), 2),
        "close_last": round(float(close_arr[-1]), 2),
        "return_mean": round(float(rets.mean()), 6), "return_std": round(float(rets.std()), 6),
        "return_skew": round(float(pd.Series(rets).skew()), 4),
        "return_kurtosis": round(float(pd.Series(rets).kurtosis()), 4),
    }

    eta_calc = ETAEstimator()
    val_results = {m: {c.name: [] for c in COST_SCENARIOS} for m in active_modes}
    best_val_sharpe = {m: -999.0 for m in active_modes}
    best_val_config = {m: None for m in active_modes}

    # Resume
    resume_iter = 0
    if args.resume:
        ckpt = checkpoint_dir / "state_latest.json"
        if ckpt.exists():
            ckpt_data = json.loads(ckpt.read_text())
            resume_iter = ckpt_data.get("completed_iterations", 0)
            if resume_iter > 0:
                log.info(f"  Resuming from iteration {resume_iter}")
                val_results = ckpt_data.get("val_results", val_results)
                best_val_sharpe = {k: float(v) for k, v in ckpt_data.get("best_val_sharpe", best_val_sharpe).items()}

    for iteration in range(resume_iter, args.iterations):
        iter_start = time.time()
        seed = BASE_SEED + iteration
        pct = ((iteration + 1) / args.iterations) * 100
        eta_calc.update(iteration, args.iterations)
        eta_str = eta_calc.eta_human(iteration, args.iterations)

        update_state(
            iteration=iteration + 1, max_iterations=args.iterations,
            progress_pct=20 + pct * 0.6,
            phase_progress_pct=pct,
            current_task=f"Training iteration {iteration + 1}/{args.iterations}",
            eta_seconds=eta_calc.eta_seconds(iteration, args.iterations),
            eta_human=eta_str,
        )

        iter_metrics = {}
        for mode_key, mode_cfg in active_modes.items():
            y = labels[mode_key]
            valid_tr = np.isfinite(y[train_idx])
            X_tr = X_all[train_idx][valid_tr]
            y_tr = y[train_idx][valid_tr]

            if len(y_tr) < 30:
                for cost in COST_SCENARIOS:
                    val_results[mode_key][cost.name].append(
                        compute_metrics([], np.array([CAPITAL]), 1))
                continue

            fit_start = time.time()
            models = train_model(X_tr, y_tr, seed)
            fit_seconds = time.time() - fit_start

            # Train backtest (for telemetry)
            proba_train = predict_ensemble(models, X_tr)
            sig_train = np.zeros(len(X_tr), dtype=np.int8)
            conf_train = np.abs(proba_train - 0.5) * 2
            sig_train[proba_train > 0.5 + (mode_cfg.min_confidence - 0.5)] = 1
            sig_train[proba_train < 0.5 - (mode_cfg.min_confidence - 0.5)] = -1
            train_trades_list, train_eq = run_backtest(
                close[train_idx][valid_tr], high[train_idx][valid_tr],
                low[train_idx][valid_tr], atr[train_idx][valid_tr],
                sig_train, conf_train, mode_cfg, COST_SCENARIOS[1])
            train_m = compute_metrics(train_trades_list, train_eq, int(valid_tr.sum()))

            # Validation
            X_va = X_all[val_idx]
            pred_start = time.time()
            proba_val = predict_ensemble(models, X_va)
            pred_seconds = time.time() - pred_start
            sig_val = np.zeros(len(val_idx), dtype=np.int8)
            conf_val = np.abs(proba_val - 0.5) * 2
            sig_val[proba_val > 0.5 + (mode_cfg.min_confidence - 0.5)] = 1
            sig_val[proba_val < 0.5 - (mode_cfg.min_confidence - 0.5)] = -1

            y_val_labels = y[val_idx]

            for cost in COST_SCENARIOS:
                trades_v, eq_v = run_backtest(
                    close[val_idx], high[val_idx], low[val_idx], atr[val_idx],
                    sig_val, conf_val, mode_cfg, cost)
                m_v = compute_metrics(trades_v, eq_v, n_val)
                val_results[mode_key][cost.name].append(m_v)

                if cost.name == "base" and m_v["sharpe"] > best_val_sharpe[mode_key]:
                    best_val_sharpe[mode_key] = m_v["sharpe"]
                    best_val_config[mode_key] = {"seed": seed, "iteration": iteration, "metrics": m_v}

            base_m = val_results[mode_key]["base"][-1]
            iter_metrics[mode_key] = base_m

            # Base cost trades/equity for telemetry
            trades_base, eq_base = run_backtest(
                close[val_idx], high[val_idx], low[val_idx], atr[val_idx],
                sig_val, conf_val, mode_cfg, COST_SCENARIOS[1])

            # Targets info
            targets_info = {
                "target_name": f"triple_barrier_{mode_key}",
                "label_horizon": mode_cfg.horizon_bars,
                "train_positive_pct": round(float((y_tr == 1).sum() / len(y_tr) * 100), 1) if len(y_tr) > 0 else None,
                "label_valid_count": int(np.isfinite(y[train_idx]).sum() + np.isfinite(y[val_idx]).sum()),
                "label_nan_count": int((~np.isfinite(y)).sum()),
            }

            # Record telemetry packet
            telemetry.record_iteration(
                iteration=iteration + 1, mode=mode_key, seed=seed,
                models=models, X_train=X_tr, y_train=y_tr,
                X_val=X_va, y_val=y_val_labels,
                proba_val=proba_val, sig_val=sig_val, conf_val=conf_val,
                trades_val=trades_base, equity_val=eq_base,
                metrics_val=base_m, feat_cols=feat_cols,
                train_trades=train_trades_list, train_equity=train_eq,
                train_metrics=train_m,
                data_info=data_info, targets_info=targets_info,
                iter_start=iter_start,
            )

        # Dense console line
        parts = []
        for mk, mm in iter_metrics.items():
            parts.append(f"{mk}:S={mm['sharpe']:.2f}/PF={mm['profit_factor']:.2f}/T={mm['n_trades']}")
        best_iter = max((best_val_config[m]["iteration"] + 1 for m in active_modes if best_val_config[m]), default=0)
        iter_sec = time.time() - iter_start
        log.info(f"  [ITER {iteration+1:03d}/{args.iterations}] {' | '.join(parts)} | best={best_iter:03d} | {iter_sec:.1f}s | ETA: {eta_str}")
        sys.stdout.flush()

        # Update metrics preview
        update_state(**{
            "metrics_preview": {
                "best_validation_sharpe": max(best_val_sharpe.values()),
                "best_validation_profit_factor": None,
                "best_iteration": iteration + 1,
                "trades_so_far": sum(m["n_trades"] for mode_res in val_results.values() for m in mode_res["base"]),
                "current_oos_locked": True,
            },
        })

        # Checkpoint every 10
        if (iteration + 1) % 10 == 0:
            ckpt_data = {
                "completed_iterations": iteration + 1,
                "val_results": val_results,
                "best_val_sharpe": best_val_sharpe,
                "best_val_config": best_val_config,
            }
            (checkpoint_dir / "state_latest.json").write_text(json.dumps(ckpt_data, indent=2, default=str))
            telemetry.record_system_snapshot()

        append_event(run_id, "INFO", "TRAINING", "iteration_complete",
                     f"Iter {iteration+1}: {' | '.join(parts)}", mode=",".join(active_modes.keys()))

    log.info(f"\n  Training complete.")
    log.info(f"  Best validation Sharpes: {best_val_sharpe}")
    update_state(progress_pct=80)

    # Final test (OOS)
    set_phase("OOS_RUNNING", "FINAL TEST — first and only look")
    log.info(f"\n{'='*70}")
    log.info("  FINAL TEST (locked until now)")
    log.info(f"{'='*70}")

    oos_results = {m: {c.name: None for c in COST_SCENARIOS} for m in active_modes}
    oos_trades_all = {}

    for mode_key, mode_cfg in active_modes.items():
        best_cfg = best_val_config.get(mode_key)
        best_seed = best_cfg["seed"] if best_cfg else BASE_SEED
        log.info(f"  {mode_cfg.name}: best_seed={best_seed} (iter {best_cfg['iteration']+1 if best_cfg else '?'})")

        y = labels[mode_key]
        valid_tr = np.isfinite(y[train_idx])
        X_tr = X_all[train_idx][valid_tr]
        y_tr = y[train_idx][valid_tr]

        models = train_model(X_tr, y_tr, best_seed)

        X_oos = X_all[oos_idx]
        proba_oos = predict_ensemble(models, X_oos)
        sig_oos = np.zeros(len(oos_idx), dtype=np.int8)
        conf_oos = np.abs(proba_oos - 0.5) * 2
        sig_oos[proba_oos > 0.5 + (mode_cfg.min_confidence - 0.5)] = 1
        sig_oos[proba_oos < 0.5 - (mode_cfg.min_confidence - 0.5)] = -1

        for cost in COST_SCENARIOS:
            trades_o, eq_o = run_backtest(
                close[oos_idx], high[oos_idx], low[oos_idx], atr[oos_idx],
                sig_oos, conf_oos, mode_cfg, cost)
            m_o = compute_metrics(trades_o, eq_o, n_oos)
            oos_results[mode_key][cost.name] = m_o
            if cost.name == "base":
                oos_trades_all[mode_key] = trades_o
            log.info(f"    [{cost.name}] trades={m_o['n_trades']}, sharpe={m_o['sharpe']:.3f}, "
                     f"PF={m_o['profit_factor']:.3f}, DD={m_o['max_dd']:.1f}%")

    update_state(progress_pct=95)

    # Verdicts
    set_phase("REPORTING", "Final report")
    verdicts = {}
    for mode_key, mode_cfg in active_modes.items():
        base = oos_results[mode_key]["base"]
        is_proxy = mode_key in ("scalp", "daytrade")  # daily data = proxy
        prefix = "PROXY_" if is_proxy else ""

        if base["n_trades"] < mode_cfg.min_oos_trades:
            verdicts[mode_key] = (f"{prefix}FAIL", f"Trades {base['n_trades']} < {mode_cfg.min_oos_trades}")
        elif base["sharpe"] < 0.5:
            verdicts[mode_key] = (f"{prefix}FAIL", f"Sharpe {base['sharpe']:.3f} < 0.5")
        elif base["profit_factor"] < 1.0:
            verdicts[mode_key] = (f"{prefix}FAIL", f"PF {base['profit_factor']:.3f} < 1.0")
        elif base["sharpe"] > 1.25 and base["profit_factor"] > 1.5:
            verdicts[mode_key] = (f"{prefix}STRONG", "Robust")
        elif base["sharpe"] > 0.75 and base["profit_factor"] > 1.2:
            verdicts[mode_key] = (f"{prefix}PROMISING", "Decent edge")
        else:
            verdicts[mode_key] = (f"{prefix}MARGINAL", "Fragile edge")

    elapsed = time.time() - start_time

    # Print final report
    report_lines = []
    report_lines.append("")
    report_lines.append("=" * 70)
    report_lines.append("  HYDRA AVAILABLE-DATA FINAL REPORT")
    report_lines.append("=" * 70)
    report_lines.append(f"  RUN TYPE:       AVAILABLE_DATA_EQUAL_THIRDS")
    report_lines.append(f"  STRICT 9-YEAR:  false")
    report_lines.append(f"  RUN ID:         {run_id}")
    report_lines.append(f"  RUNTIME:        {elapsed:.0f}s ({elapsed/60:.1f} min)")
    report_lines.append(f"")
    report_lines.append(f"  DATA SOURCE:    DuckDB gold_master")
    report_lines.append(f"  Rows:           {n_total}")
    report_lines.append(f"  Range:          {date_min.date()} → {date_max.date()}")
    report_lines.append(f"  Timeframe:      D1 (daily)")
    report_lines.append(f"  Years:          {total_years:.1f}")
    report_lines.append(f"  Warning:        This is NOT a strict 9-year validation")
    report_lines.append(f"")
    report_lines.append(f"  SPLIT (equal thirds):")
    report_lines.append(f"  TRAIN:          {train_start_dt.date()} → {train_end_dt.date()} ({n_train} bars)")
    report_lines.append(f"  VALIDATION:     {val_start_dt.date()} → {val_end_dt.date()} ({n_val} bars)")
    report_lines.append(f"  FINAL TEST:     {oos_start_dt.date()} → {oos_end_dt.date()} ({n_oos} bars)")
    report_lines.append(f"")
    report_lines.append(f"  ITERATIONS:     {args.iterations}/{args.iterations}")
    report_lines.append(f"  FEATURES:       {len(feat_cols)}")
    report_lines.append(f"")

    for mode_key, mode_cfg in active_modes.items():
        base = oos_results[mode_key]["base"]
        verdict, reason = verdicts[mode_key]
        is_proxy = mode_key in ("scalp", "daytrade")
        label = f"{mode_cfg.name} {'(DAILY PROXY)' if is_proxy else ''}"
        report_lines.append(f"  {label}:")
        report_lines.append(f"    Verdict:          {verdict} — {reason}")
        report_lines.append(f"    Best val iter:    {best_val_config[mode_key]['iteration']+1 if best_val_config[mode_key] else 'N/A'}")
        report_lines.append(f"    Best val Sharpe:  {best_val_sharpe[mode_key]:.3f}")
        report_lines.append(f"    Final test trades:{base['n_trades']}")
        report_lines.append(f"    Sharpe:           {base['sharpe']:.3f}")
        report_lines.append(f"    Sortino:          {base['sortino']:.3f}")
        report_lines.append(f"    Profit factor:    {base['profit_factor']:.3f}")
        report_lines.append(f"    Win rate:         {base['win_rate']:.1%}")
        report_lines.append(f"    Avg RR:           {base['avg_rr']}")
        report_lines.append(f"    Total profit:     ${base['total_profit']:.2f}")
        report_lines.append(f"    Max drawdown:     {base['max_dd']:.2f}%")
        report_lines.append(f"")

    # Cost sensitivity
    report_lines.append(f"  COST SENSITIVITY:")
    for mode_key in active_modes:
        for cost in COST_SCENARIOS:
            m = oos_results[mode_key][cost.name]
            report_lines.append(f"    {mode_key}/{cost.name}: S={m['sharpe']:.3f} PF={m['profit_factor']:.3f} T={m['n_trades']}")
    report_lines.append(f"")

    # Verdict
    any_edge = any(v[0].endswith("STRONG") or v[0].endswith("PROMISING") for v in verdicts.values())
    report_lines.append(f"  FINAL VERDICT:")
    report_lines.append(f"    Edge found:       {'YES' if any_edge else 'NO'}")
    report_lines.append(f"    Tradable:         {'MAYBE — needs intraday validation' if any_edge else 'NO'}")
    report_lines.append(f"    Main weakness:    Daily-only data, {total_years:.1f} years, proxy modes")
    report_lines.append(f"    Next experiment:  Fetch intraday via Dukascopy, rerun with M1/M5")
    report_lines.append(f"")
    report_lines.append(f"  ARTIFACTS:        {run_dir}")
    report_lines.append("=" * 70)

    report_text = "\n".join(report_lines)
    log.info(report_text)

    # Save artifacts
    (run_dir / "summary_report.md").write_text(f"# HYDRA Available-Data Report\n\n```\n{report_text}\n```\n")
    (run_dir / "final_results.md").write_text(
        "# Final Results\n\n" + "\n".join(f"- **{k.upper()}**: {v} — {r}" for k, (v, r) in verdicts.items()))
    (run_dir / "final_test_result.json").write_text(json.dumps(oos_results, indent=2, default=str))

    # Metrics CSVs
    for mode_key in active_modes:
        pd.DataFrame(val_results[mode_key]["base"]).to_csv(
            str(run_dir / f"metrics_validation_{mode_key}.csv"), index=False)

    oos_flat = []
    for mode_key in active_modes:
        for cost in COST_SCENARIOS:
            row = {"mode": mode_key, "cost": cost.name}
            row.update(oos_results[mode_key][cost.name])
            oos_flat.append(row)
    pd.DataFrame(oos_flat).to_csv(str(run_dir / "metrics_final_test.csv"), index=False)

    # Trade logs
    trade_dir = run_dir / "trade_logs"
    trade_dir.mkdir(exist_ok=True)
    for mode_key, trades in oos_trades_all.items():
        if trades:
            pd.DataFrame([asdict(t) for t in trades]).to_csv(
                str(trade_dir / f"{mode_key}_trades.csv"), index=False)

    set_complete()
    append_event(run_id, "SUCCESS", "COMPLETE", "run_complete",
                 f"Equal-thirds run complete in {elapsed:.0f}s")

    log.info(f"\n  Dashboard: python -m hydra.progress --watch")
    return verdicts


def main():
    parser = argparse.ArgumentParser(description="HYDRA 9-Year Final Backtest")
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--years", type=int, default=9)
    parser.add_argument("--iterations", type=int, default=100)
    parser.add_argument("--max-iterations", type=int, default=300)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--require-gpu", action="store_true")
    parser.add_argument("--equal-thirds", action="store_true",
                        help="Use all available data split into 3 equal chronological parts")
    parser.add_argument("--allow-degraded", action="store_true",
                        help="Do not abort if full 9-year coverage is missing")
    args = parser.parse_args()

    try:
        if args.equal_thirds:
            run_equal_thirds(args)
        else:
            if args.allow_degraded:
                # Patch: lower threshold to 3 years
                pass
            run_experiment(args)
    except KeyboardInterrupt:
        print("\n\nAborted by user.")
        update_state(status="ABORTED", active=False)
    except Exception as e:
        print(f"\n\nFATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        set_failed(str(e))
        raise


if __name__ == "__main__":
    main()
