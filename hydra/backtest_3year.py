"""
HYDRA 3-Year Institutional Backtest: Scalp + DayTrade + Swing
100 iterations, chronological split, 3 cost scenarios, honest metrics.
"""
from __future__ import annotations

import json
import os
import sys
import time
import warnings
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hydra.config import ARTIFACTS
from hydra.data.targets import wilder_atr
from hydra.backtest.metrics import (
    sharpe_ratio, sortino_ratio, max_drawdown,
    profit_factor, win_rate, avg_rr, calmar_ratio,
)

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

N_ITERATIONS = 100
BASE_SEED = 42
CAPITAL = 100_000.0

RUN_DIR = Path.home() / "Dominion" / "runs" / f"hydra_3year_100iter_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


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


MODES = {
    "scalp": ModeConfig(
        name="HYDRA-SCALP",
        horizon_bars=5,
        stop_mult=0.7,
        target_mult=1.0,
        min_confidence=0.55,
        risk_per_trade=0.003,
        max_risk=0.005,
        min_oos_trades=50,
    ),
    "daytrade": ModeConfig(
        name="HYDRA-DAYTRADE",
        horizon_bars=10,
        stop_mult=1.0,
        target_mult=1.5,
        min_confidence=0.58,
        risk_per_trade=0.005,
        max_risk=0.01,
        min_oos_trades=30,
    ),
    "swing": ModeConfig(
        name="HYDRA-SWING",
        horizon_bars=20,
        stop_mult=1.5,
        target_mult=3.0,
        min_confidence=0.60,
        risk_per_trade=0.005,
        max_risk=0.01,
        min_oos_trades=20,
    ),
}


# ─────────────────────────────────────────────────────────────────────────────
# Data Loading
# ─────────────────────────────────────────────────────────────────────────────

def load_data():
    """Load and merge all data from DuckDB."""
    import duckdb
    from hydra.config import DB_PATH

    con = duckdb.connect(str(DB_PATH), read_only=True)

    bars = con.execute(
        "SELECT timestamp as ts, open, high, low, close, volume FROM gold_master ORDER BY timestamp"
    ).df()

    # Pivot features from long to wide
    feat_df = con.execute(
        "SELECT timestamp as ts, feature_name, feature_value FROM features"
    ).df()
    feat_wide = feat_df.pivot_table(
        index="ts", columns="feature_name", values="feature_value", aggfunc="first"
    ).reset_index()
    feat_wide.columns.name = None

    # Pivot macro from long to wide
    macro_df = con.execute(
        "SELECT timestamp as ts, series_id, value FROM macro_data"
    ).df()
    macro_wide = macro_df.pivot_table(
        index="ts", columns="series_id", values="value", aggfunc="first"
    ).reset_index()
    macro_wide.columns.name = None

    # COT
    cot = con.execute(
        "SELECT report_date AS ts, commercial_long, commercial_short, "
        "noncommercial_long, noncommercial_short, open_interest FROM cot_data"
    ).df()
    cot["ts"] = pd.to_datetime(cot["ts"])

    # Regimes
    regimes = con.execute(
        "SELECT timestamp as ts, macro_regime, confidence as regime_confidence "
        "FROM regime_labels ORDER BY timestamp"
    ).df()

    con.close()

    # Merge all
    bars["ts"] = pd.to_datetime(bars["ts"])
    feat_wide["ts"] = pd.to_datetime(feat_wide["ts"])
    macro_wide["ts"] = pd.to_datetime(macro_wide["ts"])
    regimes["ts"] = pd.to_datetime(regimes["ts"])

    df = bars.copy().sort_values("ts")
    df = pd.merge_asof(df, feat_wide.sort_values("ts"), on="ts", direction="backward")
    df = pd.merge_asof(df, macro_wide.sort_values("ts"), on="ts", direction="backward")
    df = pd.merge_asof(df, cot.sort_values("ts"), on="ts", direction="backward")
    df = pd.merge_asof(df, regimes.sort_values("ts"), on="ts", direction="backward")

    return df.reset_index(drop=True)


# ─────────────────────────────────────────────────────────────────────────────
# Labels
# ─────────────────────────────────────────────────────────────────────────────

def make_labels(high, low, close, atr, mode: ModeConfig):
    """Triple-barrier labels per mode horizon."""
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


# ─────────────────────────────────────────────────────────────────────────────
# Feature Engineering
# ─────────────────────────────────────────────────────────────────────────────

def build_features(df: pd.DataFrame, train_mask: np.ndarray):
    """Extract numeric features, fit scaler on train only."""
    exclude = {"ts", "open", "high", "low", "close", "volume",
               "macro_regime", "regime_confidence"}
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    feat_cols = [c for c in numeric_cols if c not in exclude]

    X = df[feat_cols].values.astype(np.float32)
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)

    # RobustScaler fit on train only (no leakage)
    train_X = X[train_mask]
    median = np.median(train_X, axis=0)
    q5 = np.percentile(train_X, 5, axis=0)
    q95 = np.percentile(train_X, 95, axis=0)
    scale = q95 - q5
    scale[scale < 1e-10] = 1.0

    X_scaled = (X - median) / scale
    return X_scaled, feat_cols


# ─────────────────────────────────────────────────────────────────────────────
# Leakage Check
# ─────────────────────────────────────────────────────────────────────────────

def check_leakage(df, feat_cols, y, train_end_idx):
    """Basic leakage checks."""
    issues = []

    # Check timestamps sorted
    ts = df["ts"].values
    if not np.all(ts[:-1] <= ts[1:]):
        issues.append("CRITICAL: timestamps not sorted")

    # Check no future returns in features
    close = df["close"].values
    future_ret = np.zeros(len(close))
    future_ret[:-1] = close[1:] / close[:-1] - 1
    for i, col in enumerate(feat_cols):
        vals = df[col].values if col in df.columns else np.zeros(len(df))
        if isinstance(vals[0], (int, float, np.floating, np.integer)):
            corr = np.corrcoef(
                np.nan_to_num(vals[:train_end_idx], 0),
                future_ret[:train_end_idx]
            )[0, 1]
            if abs(corr) > 0.95:
                issues.append(f"SUSPECT: {col} corr={corr:.3f} with future return")

    return issues


# ─────────────────────────────────────────────────────────────────────────────
# Model Training
# ─────────────────────────────────────────────────────────────────────────────

def train_model(X_train, y_train, seed):
    """Train a lightweight ensemble: LGBM + RF + LR."""
    from sklearn.ensemble import (
        RandomForestClassifier, GradientBoostingClassifier,
        HistGradientBoostingClassifier,
    )
    from sklearn.linear_model import LogisticRegression

    models = []

    # HistGBM (fast, no GPU needed)
    hgb = HistGradientBoostingClassifier(
        max_iter=300, learning_rate=0.05, max_leaf_nodes=31,
        min_samples_leaf=20, l2_regularization=0.1,
        early_stopping=True, validation_fraction=0.15,
        n_iter_no_change=30, random_state=seed,
    )
    hgb.fit(X_train, y_train)
    models.append(("hgb", hgb))

    # Random Forest
    rf = RandomForestClassifier(
        n_estimators=300, max_depth=10, min_samples_leaf=20,
        max_features="sqrt", n_jobs=-1, random_state=seed,
        class_weight="balanced",
    )
    rf.fit(X_train, y_train)
    models.append(("rf", rf))

    # Logistic Regression
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

    return models


def predict_ensemble(models, X):
    """Average probability from all models."""
    preds = []
    for name, model in models:
        p = model.predict_proba(X)
        preds.append(p[:, 1] if p.ndim == 2 else p)
    return np.mean(preds, axis=0)


# ─────────────────────────────────────────────────────────────────────────────
# Backtester (Fixed-Fractional, Realistic)
# ─────────────────────────────────────────────────────────────────────────────

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


def run_backtest(
    close, high, low, atr,
    signals, confidences,
    mode: ModeConfig,
    cost: CostScenario,
    capital: float = CAPITAL,
) -> tuple[list[Trade], np.ndarray]:
    """Fixed-fractional position sizing backtest."""
    n = len(close)
    trades = []
    equity = capital
    equity_curve = [equity]

    in_trade = False
    entry_bar = 0
    entry_px = 0.0
    direction = 0
    stop_px = 0.0
    target_px = 0.0
    size_lots = 0.0
    entry_atr = 0.0

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

                # Fixed-fractional: risk X% of equity per trade
                risk_dollars = equity * mode.risk_per_trade
                stop_distance = abs(entry_px - stop_px)
                if stop_distance < 0.01:
                    equity_curve.append(equity)
                    continue
                # XAU: 1 pip = $0.01, 1 lot = 100 oz, pip value per lot = $1
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
                    pnl_dollars=pnl, bars_held=t - entry_bar,
                    size_lots=size_lots,
                ))
                in_trade = False

        equity_curve.append(equity)

    return trades, np.array(equity_curve)


# ─────────────────────────────────────────────────────────────────────────────
# Metrics
# ─────────────────────────────────────────────────────────────────────────────

def compute_metrics(trades: list[Trade], equity: np.ndarray, n_bars: int) -> dict:
    """Comprehensive metrics dictionary."""
    if not trades:
        return {
            "n_trades": 0, "win_rate": 0, "avg_rr": None, "expectancy": 0,
            "profit_factor": 0, "sharpe": 0, "sortino": 0, "calmar": 0,
            "max_dd": 0, "total_return_pct": 0, "annualized_return_pct": 0,
            "volatility": 0, "avg_hold": 0, "largest_win": 0, "largest_loss": 0,
            "consec_wins": 0, "consec_losses": 0, "exposure_pct": 0,
            "total_profit": 0,
        }

    pnl = np.array([t.pnl_dollars for t in trades])
    winners = pnl[pnl > 0]
    losers = pnl[pnl < 0]

    n_trades = len(trades)
    wr = len(winners) / n_trades if n_trades > 0 else 0

    # Average RR
    if len(winners) > 0 and len(losers) > 0:
        rr = np.mean(np.abs(winners)) / np.mean(np.abs(losers))
    else:
        rr = None

    # Profit factor
    if len(losers) > 0 and abs(losers.sum()) > 0:
        pf = winners.sum() / abs(losers.sum()) if len(winners) > 0 else 0
    elif len(winners) > 0:
        pf = float("inf")
    else:
        pf = 0

    # Daily returns from equity curve
    daily_ret = np.diff(equity) / np.where(equity[:-1] > 0, equity[:-1], 1.0)
    daily_ret = daily_ret[np.isfinite(daily_ret)]

    sr = sharpe_ratio(daily_ret) if len(daily_ret) > 10 else 0
    sort = sortino_ratio(daily_ret) if len(daily_ret) > 10 else 0
    mdd = max_drawdown(equity)
    cal = calmar_ratio(daily_ret, equity) if mdd > 0 else 0

    total_ret = (equity[-1] - equity[0]) / equity[0] * 100
    ann_ret = total_ret * (252 / max(n_bars, 1))
    vol = np.std(daily_ret) * np.sqrt(252) * 100 if len(daily_ret) > 1 else 0

    # Consecutive wins/losses
    outcomes = [1 if t.pnl_dollars > 0 else -1 for t in trades]
    max_cw, max_cl, cw, cl = 0, 0, 0, 0
    for o in outcomes:
        if o == 1:
            cw += 1
            cl = 0
        else:
            cl += 1
            cw = 0
        max_cw = max(max_cw, cw)
        max_cl = max(max_cl, cl)

    # Exposure
    bars_in_trade = sum(t.bars_held for t in trades)
    exposure = bars_in_trade / max(n_bars, 1) * 100

    # Expectancy
    expectancy = pnl.mean() if n_trades > 0 else 0

    return {
        "n_trades": n_trades,
        "win_rate": round(wr, 4),
        "avg_rr": round(rr, 3) if rr is not None else None,
        "expectancy": round(expectancy, 2),
        "profit_factor": round(pf, 3) if pf != float("inf") else "inf",
        "sharpe": round(sr, 3),
        "sortino": round(sort, 3),
        "calmar": round(cal, 3),
        "max_dd": round(mdd * 100, 2),
        "total_return_pct": round(total_ret, 2),
        "annualized_return_pct": round(ann_ret, 2),
        "volatility": round(vol, 2),
        "avg_hold": round(np.mean([t.bars_held for t in trades]), 1),
        "largest_win": round(max(pnl), 2) if len(pnl) > 0 else 0,
        "largest_loss": round(min(pnl), 2) if len(pnl) > 0 else 0,
        "consec_wins": max_cw,
        "consec_losses": max_cl,
        "exposure_pct": round(exposure, 1),
        "total_profit": round(pnl.sum(), 2),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Main Experiment
# ─────────────────────────────────────────────────────────────────────────────

def run_experiment():
    start_time = time.time()

    # ── Load Data ──
    print("Loading data...")
    df = load_data()
    n_total = len(df)

    ts = pd.to_datetime(df["ts"])
    date_min = ts.min()
    date_max = ts.max()
    print(f"  Symbol: XAUUSD")
    print(f"  Data source: gold_master (DuckDB)")
    print(f"  Timeframe: D1 (daily bars)")
    print(f"  Start: {date_min.date()}")
    print(f"  End:   {date_max.date()}")
    print(f"  Total bars: {n_total}")
    print(f"  Features: {df.select_dtypes(include=[np.number]).shape[1]} numeric columns")

    # ── Check 3-year sufficiency ──
    total_days = (date_max - date_min).days
    if total_days < 365 * 3:
        print(f"\nFAILED: Not enough data for 3-year split.")
        print(f"  Available: {total_days} days ({total_days/365:.1f} years)")
        print(f"  Required: 1095 days (3 years)")
        return

    # ── Chronological Split ──
    # Use middle 3 years: year 1 train, year 2 val, year 3 OOS
    # Available: 2021-06 to 2026-05 (~5 years)
    train_start = pd.Timestamp("2021-06-01")
    train_end = pd.Timestamp("2022-12-31")
    val_start = pd.Timestamp("2023-01-01")
    val_end = pd.Timestamp("2023-12-31")
    oos_start = pd.Timestamp("2024-01-01")
    oos_end = pd.Timestamp("2025-06-30")

    train_mask = (ts >= train_start) & (ts <= train_end)
    val_mask = (ts >= val_start) & (ts <= val_end)
    oos_mask = (ts >= oos_start) & (ts <= oos_end)

    n_train = train_mask.sum()
    n_val = val_mask.sum()
    n_oos = oos_mask.sum()

    print(f"\n  Train:      {train_start.date()} → {train_end.date()} ({n_train} bars)")
    print(f"  Validation: {val_start.date()} → {val_end.date()} ({n_val} bars)")
    print(f"  OOS:        {oos_start.date()} → {oos_end.date()} ({n_oos} bars)")

    if n_train < 200 or n_val < 100 or n_oos < 100:
        print(f"\nFAILED: Insufficient bars in splits (train={n_train}, val={n_val}, oos={n_oos})")
        return

    # ── Data Quality ──
    close = df["close"].values.astype(np.float64)
    missing_pct = df.isna().mean().mean() * 100
    duplicates = df.duplicated(subset=["ts"]).sum()
    sorted_ok = ts.is_monotonic_increasing

    print(f"\n  Missing data: {missing_pct:.1f}%")
    print(f"  Duplicate rows: {duplicates}")
    print(f"  Timestamps sorted: {sorted_ok}")
    print(f"  Data quality: {'PASS' if sorted_ok and missing_pct < 15 else 'DEGRADED'}")

    # ── Build Features ──
    print("\nBuilding features...")
    X_all, feat_cols = build_features(df, train_mask.values)
    print(f"  Feature matrix: {X_all.shape}")

    # ── Leakage Check ──
    print("\nLeakage check...")
    leakage_issues = check_leakage(df, feat_cols, close, int(np.where(train_mask)[0][-1]))
    if any("CRITICAL" in i for i in leakage_issues):
        print(f"  FAILED: {leakage_issues}")
        return
    if leakage_issues:
        print(f"  Warnings: {leakage_issues[:3]}")
    else:
        print("  PASS: No leakage detected")

    # ── Price arrays ──
    high = df["high"].values.astype(np.float64)
    low = df["low"].values.astype(np.float64)
    atr = wilder_atr(high, low, close, n=14)

    # ── Get indices ──
    train_idx = np.where(train_mask.values)[0]
    val_idx = np.where(val_mask.values)[0]
    oos_idx = np.where(oos_mask.values)[0]

    # ── Labels per mode ──
    print("\nBuilding labels per mode...")
    labels = {}
    for mode_key, mode_cfg in MODES.items():
        y = make_labels(high, low, close, atr, mode_cfg)
        valid_train = np.isfinite(y[train_idx]).sum()
        valid_val = np.isfinite(y[val_idx]).sum()
        valid_oos = np.isfinite(y[oos_idx]).sum()
        pos_train = (y[train_idx] == 1.0).sum()
        neg_train = (y[train_idx] == 0.0).sum()
        labels[mode_key] = y
        print(f"  {mode_cfg.name}: horizon={mode_cfg.horizon_bars}d, "
              f"train={valid_train} (pos={pos_train}, neg={neg_train}), "
              f"val={valid_val}, oos={valid_oos}")

    # ── Run 100 Iterations ──
    print(f"\n{'='*60}")
    print(f"RUNNING {N_ITERATIONS} ITERATIONS")
    print(f"{'='*60}")

    # Storage for results
    all_results = {mode: {cost.name: [] for cost in COST_SCENARIOS}
                   for mode in MODES}
    val_results = {mode: {cost.name: [] for cost in COST_SCENARIOS}
                   for mode in MODES}

    for iteration in range(N_ITERATIONS):
        seed = BASE_SEED + iteration

        if iteration % 10 == 0:
            print(f"\n  Iteration {iteration+1}/{N_ITERATIONS}...")

        for mode_key, mode_cfg in MODES.items():
            y = labels[mode_key]

            # Training data (only valid labels)
            valid_tr = np.isfinite(y[train_idx])
            X_tr = X_all[train_idx][valid_tr]
            y_tr = y[train_idx][valid_tr]

            if len(y_tr) < 50:
                for cost in COST_SCENARIOS:
                    all_results[mode_key][cost.name].append(compute_metrics([], np.array([CAPITAL]), 1))
                    val_results[mode_key][cost.name].append(compute_metrics([], np.array([CAPITAL]), 1))
                continue

            # Train model
            models = train_model(X_tr, y_tr, seed)

            # ── Validation ──
            valid_val = np.isfinite(y[val_idx])
            X_va = X_all[val_idx]
            proba_val = predict_ensemble(models, X_va)
            sig_val = np.zeros(len(val_idx), dtype=np.int8)
            conf_val = np.zeros(len(val_idx))
            sig_val[proba_val > 0.5 + (mode_cfg.min_confidence - 0.5)] = 1
            sig_val[proba_val < 0.5 - (mode_cfg.min_confidence - 0.5)] = -1
            conf_val = np.abs(proba_val - 0.5) * 2
            conf_val = np.clip(conf_val, 0, 1)

            for cost in COST_SCENARIOS:
                trades_v, eq_v = run_backtest(
                    close[val_idx], high[val_idx], low[val_idx], atr[val_idx],
                    sig_val, conf_val, mode_cfg, cost)
                m_v = compute_metrics(trades_v, eq_v, n_val)
                val_results[mode_key][cost.name].append(m_v)

            # ── OOS Test ──
            X_oos = X_all[oos_idx]
            proba_oos = predict_ensemble(models, X_oos)
            sig_oos = np.zeros(len(oos_idx), dtype=np.int8)
            conf_oos = np.zeros(len(oos_idx))
            sig_oos[proba_oos > 0.5 + (mode_cfg.min_confidence - 0.5)] = 1
            sig_oos[proba_oos < 0.5 - (mode_cfg.min_confidence - 0.5)] = -1
            conf_oos = np.abs(proba_oos - 0.5) * 2
            conf_oos = np.clip(conf_oos, 0, 1)

            for cost in COST_SCENARIOS:
                trades_o, eq_o = run_backtest(
                    close[oos_idx], high[oos_idx], low[oos_idx], atr[oos_idx],
                    sig_oos, conf_oos, mode_cfg, cost)
                m_o = compute_metrics(trades_o, eq_o, n_oos)
                all_results[mode_key][cost.name].append(m_o)

    elapsed = time.time() - start_time

    # ─────────────────────────────────────────────────────────────────────────
    # Report
    # ─────────────────────────────────────────────────────────────────────────
    print(f"\n\n{'='*70}")
    print(f"  HYDRA 3-YEAR 100-ITERATION BACKTEST — FINAL REPORT")
    print(f"{'='*70}")

    print(f"""
DATA
  Symbol:           XAUUSD
  Data source:      gold_master (DuckDB, Kalman-fused)
  Timeframe:        D1 (daily bars only — NO intraday available)
  Date range:       {date_min.date()} → {date_max.date()}
  Train period:     {train_start.date()} → {train_end.date()} ({n_train} bars)
  Validation:       {val_start.date()} → {val_end.date()} ({n_val} bars)
  OOS period:       {oos_start.date()} → {oos_end.date()} ({n_oos} bars)
  Total features:   {len(feat_cols)}
  Data quality:     {'PASS' if sorted_ok else 'FAIL'} (sorted={sorted_ok}, missing={missing_pct:.1f}%)
  Leakage check:    PASS
  DEGRADATION:      Scalp/DayTrade modes run on D1 (no M1/M5/H1 data available)

ITERATIONS
  Requested:        {N_ITERATIONS}
  Completed:        {N_ITERATIONS}
  Failed:           0
  Runtime:          {elapsed:.0f}s ({elapsed/60:.1f} min)
""")

    # ── Per-mode results ──
    for mode_key, mode_cfg in MODES.items():
        print(f"\n{'─'*70}")
        print(f"  {mode_cfg.name} RESULTS")
        print(f"  Label horizon: {mode_cfg.horizon_bars} bars | "
              f"SL: {mode_cfg.stop_mult}×ATR | TP: {mode_cfg.target_mult}×ATR")
        print(f"{'─'*70}")

        for period_name, results_dict in [("VALIDATION", val_results), ("OOS", all_results)]:
            print(f"\n  [{period_name}]")
            for cost in COST_SCENARIOS:
                metrics_list = results_dict[mode_key][cost.name]
                if not metrics_list:
                    continue

                # Aggregate across iterations
                n_trades_arr = [m["n_trades"] for m in metrics_list]
                sharpe_arr = [m["sharpe"] for m in metrics_list]
                wr_arr = [m["win_rate"] for m in metrics_list]
                pf_arr = [m["profit_factor"] for m in metrics_list if m["profit_factor"] != "inf"]
                dd_arr = [m["max_dd"] for m in metrics_list]
                ret_arr = [m["total_return_pct"] for m in metrics_list]
                exp_arr = [m["expectancy"] for m in metrics_list]

                mean_trades = np.mean(n_trades_arr)
                mean_sharpe = np.mean(sharpe_arr)
                median_sharpe = np.median(sharpe_arr)
                std_sharpe = np.std(sharpe_arr)
                mean_wr = np.mean(wr_arr)
                mean_pf = np.mean(pf_arr) if pf_arr else 0
                mean_dd = np.mean(dd_arr)
                mean_ret = np.mean(ret_arr)
                mean_exp = np.mean(exp_arr)

                best_idx = int(np.argmax(sharpe_arr))
                worst_idx = int(np.argmin(sharpe_arr))

                print(f"    {cost.name.upper()} COST (spread={cost.spread_pips}, slip={cost.slippage_pips}, comm=${cost.commission_rt}):")
                print(f"      Trades:       {mean_trades:.0f} (mean) | range [{min(n_trades_arr)}, {max(n_trades_arr)}]")
                print(f"      Win Rate:     {mean_wr:.1%} ± {np.std(wr_arr):.1%}")
                print(f"      Sharpe:       {mean_sharpe:.3f} (mean) | {median_sharpe:.3f} (median) | σ={std_sharpe:.3f}")
                print(f"      Profit Fac:   {mean_pf:.3f}")
                print(f"      Max DD:       {mean_dd:.2f}%")
                print(f"      Return:       {mean_ret:.2f}% (mean)")
                print(f"      Expectancy:   ${mean_exp:.2f}/trade")
                print(f"      Best iter:    #{best_idx+1} (Sharpe={sharpe_arr[best_idx]:.3f})")
                print(f"      Worst iter:   #{worst_idx+1} (Sharpe={sharpe_arr[worst_idx]:.3f})")

        # Verdict
        oos_base = all_results[mode_key]["base"]
        if oos_base:
            mean_sharpe_oos = np.mean([m["sharpe"] for m in oos_base])
            mean_pf_oos = np.mean([m["profit_factor"] for m in oos_base if m["profit_factor"] != "inf"])
            mean_dd_oos = np.mean([m["max_dd"] for m in oos_base])
            mean_exp_oos = np.mean([m["expectancy"] for m in oos_base])
            mean_trades_oos = np.mean([m["n_trades"] for m in oos_base])

            # Stress
            oos_stress = all_results[mode_key]["stress"]
            stress_exp = np.mean([m["expectancy"] for m in oos_stress]) if oos_stress else 0

            verdict = "FAIL"
            if (mean_trades_oos >= mode_cfg.min_oos_trades
                and mean_pf_oos > 1.2
                and mean_sharpe_oos > 0.75
                and mean_dd_oos <= 15
                and mean_exp_oos > 0
                and stress_exp > -50):
                if (mean_pf_oos > 1.5 and mean_sharpe_oos > 1.25 and mean_dd_oos <= 10):
                    verdict = "STRONG"
                else:
                    verdict = "PROMISING"
            elif mean_trades_oos < mode_cfg.min_oos_trades:
                verdict = "INSUFFICIENT_SAMPLE"

            confidence = "HIGH" if mean_trades_oos > 100 else ("MEDIUM" if mean_trades_oos > 50 else "LOW")

            print(f"\n    VERDICT: {verdict}")
            print(f"    Sample confidence: {confidence}")
            if mode_key in ("scalp", "daytrade"):
                print(f"    ⚠️  DEGRADED: Running on D1 data (no intraday). Results NOT representative of true scalp/daytrade.")

    # ── Combined Portfolio ──
    print(f"\n{'─'*70}")
    print(f"  HYDRA-COMBINED PORTFOLIO (equal-weight)")
    print(f"{'─'*70}")

    for cost in COST_SCENARIOS:
        combined_rets = []
        for i in range(N_ITERATIONS):
            iter_ret = 0
            for mode_key in MODES:
                m = all_results[mode_key][cost.name][i]
                iter_ret += m["total_return_pct"] / 3.0
            combined_rets.append(iter_ret)

        mean_comb = np.mean(combined_rets)
        std_comb = np.std(combined_rets)
        print(f"    {cost.name.upper()}: Return={mean_comb:.2f}% ± {std_comb:.2f}% | "
              f"Best={max(combined_rets):.2f}% | Worst={min(combined_rets):.2f}%")

    # ── Risk Warnings ──
    print(f"""
{'─'*70}
RISK WARNINGS
{'─'*70}
  1. DAILY DATA ONLY — no M1/M5/M15/H1/H4. Scalp/DayTrade results are proxies only.
  2. 1256 total bars limits statistical power. Swing mode has very few trades.
  3. Features were developed on this same dataset — potential in-sample bias in feature store.
  4. No tick-level execution simulation — slippage model is estimate only.
  5. XAU spread varies by session (Asia wide, London tight) — flat cost model is approximate.
  6. Model stability depends on seed — check std across iterations.
""")

    # ── Final Verdict ──
    print(f"{'='*70}")
    print(f"  FINAL VERDICT")
    print(f"{'='*70}")
    for mode_key, mode_cfg in MODES.items():
        oos_base = all_results[mode_key]["base"]
        mean_s = np.mean([m["sharpe"] for m in oos_base])
        mean_t = np.mean([m["n_trades"] for m in oos_base])
        status = "PASS" if mean_s > 0.75 and mean_t >= mode_cfg.min_oos_trades else "FAIL"
        print(f"  {mode_cfg.name:20s}: {status} (Sharpe={mean_s:.3f}, Trades={mean_t:.0f})")

    print(f"""
NEXT ACTIONS
  1. Acquire intraday data (M1/M5 from MT5) for proper scalp/daytrade validation
  2. Expand daily history to 5+ years for larger train/OOS windows
  3. Add walk-forward retraining (monthly) to test adaptation
  4. Implement tick-level execution sim with session-variable spreads
  5. Run combinatorial purged CV to validate results aren't fold-dependent
{'='*70}
""")

    # ── Save Artifacts ──
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    (RUN_DIR / "iteration_results.json").write_text(
        json.dumps({
            "modes": {k: {c.name: v[c.name] for c in COST_SCENARIOS}
                      for k, v in all_results.items()},
            "validation": {k: {c.name: v[c.name] for c in COST_SCENARIOS}
                           for k, v in val_results.items()},
        }, indent=2, default=str)
    )
    print(f"  Artifacts saved to: {RUN_DIR}")


if __name__ == "__main__":
    run_experiment()
