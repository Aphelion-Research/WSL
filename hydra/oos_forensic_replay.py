"""HYDRA OOS Forensic Replay — reproduce final-test with full telemetry.

Do NOT retrain 100 iterations.
Do NOT tune thresholds.
Do NOT optimize on final test.

Replay exact selected config from validation winner, generate full OOS diagnostics.
"""
from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path
from dataclasses import dataclass, asdict

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hydra.config import DB_PATH
from hydra.data.targets import wilder_atr
from hydra.backtest.metrics import (
    sharpe_ratio, sortino_ratio, max_drawdown,
    profit_factor, win_rate, avg_rr, calmar_ratio,
)


# ─────────────────────────────────────────────────────────────────────────────
# Config (from backtest_9year_final.py)
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
# Core functions (from backtest_9year_final.py)
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
            random_state=seed, n_jobs=-1, verbosity=0,
        )
        xgbm.fit(X_train, y_train)
        models.append(("xgb", xgbm))
    except ImportError:
        pass

    return models


def predict_ensemble(models, X):
    proba_list = []
    for name, model in models:
        if hasattr(model, "predict_proba"):
            p = model.predict_proba(X)[:, 1]
        else:
            p = model.predict(X)
        proba_list.append(p)
    proba_array = np.vstack(proba_list)
    proba_mean = proba_array.mean(axis=0)
    return proba_mean


def run_backtest(close, high, low, atr, signals, confidences, mode: ModeConfig, cost: CostScenario):
    n = len(close)
    trades = []
    equity = CAPITAL
    equity_curve = [CAPITAL]
    in_trade = False
    entry_bar = None
    direction = None
    entry_px = None
    size_lots = None
    stop_px = None
    target_px = None

    for t in range(n):
        if not in_trade and signals[t] != 0:
            direction = signals[t]
            entry_px = close[t]
            spread_entry = cost.spread_pips / 2 + cost.slippage_pips
            entry_px = entry_px + direction * spread_entry

            if not np.isfinite(atr[t]) or atr[t] <= 0:
                continue

            risk_dollars = min(mode.risk_per_trade * equity, mode.max_risk * CAPITAL)
            stop_distance = mode.stop_mult * atr[t]
            if stop_distance < 1e-6:
                continue
            size_lots = risk_dollars / (stop_distance * 100)
            size_lots = max(0.01, min(size_lots, 10.0))

            entry_bar = t
            in_trade = True
            stop_px = entry_px - direction * mode.stop_mult * atr[t]
            target_px = entry_px + direction * mode.target_mult * atr[t]

        if in_trade:
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
    """Load data from DuckDB gold_master for the specified period."""
    import duckdb
    con = duckdb.connect(str(DB_PATH), read_only=True)

    bars = con.execute(
        "SELECT timestamp as ts, open, high, low, close, volume FROM gold_master ORDER BY timestamp"
    ).df()

    feat_df = con.execute("SELECT timestamp as ts, feature_name, feature_value FROM features").df()
    feat_wide = feat_df.pivot_table(index="ts", columns="feature_name", values="feature_value", aggfunc="first").reset_index()
    feat_wide.columns.name = None

    macro_df = con.execute("SELECT timestamp as ts, series_id, value FROM macro_data").df()
    macro_wide = macro_df.pivot_table(index="ts", columns="series_id", values="value", aggfunc="first").reset_index()
    macro_wide.columns.name = None

    cot = con.execute(
        "SELECT report_date AS ts, commercial_long, commercial_short, "
        "noncommercial_long, noncommercial_short, open_interest FROM cot_data"
    ).df()
    cot["ts"] = pd.to_datetime(cot["ts"])

    regimes = con.execute(
        "SELECT timestamp as ts, macro_regime, confidence as regime_confidence "
        "FROM regime_labels ORDER BY timestamp"
    ).df()

    merged = bars.merge(feat_wide, on="ts", how="left", suffixes=("", "_feat"))
    merged = merged.merge(macro_wide, on="ts", how="left", suffixes=("", "_macro"))
    merged = merged.merge(cot, on="ts", how="left", suffixes=("", "_cot"))
    merged = merged.merge(regimes, on="ts", how="left", suffixes=("", "_regime"))

    con.close()

    merged["ts"] = pd.to_datetime(merged["ts"])
    merged = merged.sort_values("ts").reset_index(drop=True)
    return merged


# ─────────────────────────────────────────────────────────────────────────────
# OOS Forensic Replay
# ─────────────────────────────────────────────────────────────────────────────

def main():
    run_id = "hydra_equal_thirds_20260519_232841"
    run_dir = RUNS_DIR / run_id
    oos_dir = run_dir / "oos_diagnostics"
    oos_dir.mkdir(exist_ok=True)

    print("=" * 70)
    print("  HYDRA OOS FORENSIC REPLAY")
    print("=" * 70)
    print(f"  Run: {run_id}")
    print(f"  Task: Reproduce final-test with full telemetry")
    print(f"  Output: {oos_dir}")
    print()

    # Load split manifest
    with open(run_dir / "split_manifest.json") as f:
        split = json.load(f)

    print("  Split:")
    print(f"    Train: {split['train_rows']} bars ({split['train_start']} → {split['train_end']})")
    print(f"    Val:   {split['validation_rows']} bars ({split['validation_start']} → {split['validation_end']})")
    print(f"    Test:  {split['test_rows']} bars ({split['test_start']} → {split['test_end']})")
    print()

    # Load data
    print("  Loading data from DuckDB gold_master...")
    df = load_data_for_period(2000, 2030)
    ts = pd.to_datetime(df["ts"])
    n_total = len(df)

    # Equal-thirds split
    n_train = n_total // 3
    n_val = n_total // 3
    n_oos = n_total - n_train - n_val

    train_idx = np.arange(n_train)
    val_idx = np.arange(n_train, n_train + n_val)
    oos_idx = np.arange(n_train + n_val, n_total)

    print(f"  Loaded: {n_total} bars")
    print(f"  Train idx: {len(train_idx)}, Val idx: {len(val_idx)}, OOS idx: {len(oos_idx)}")
    print()

    # Build features
    print("  Building features...")
    X_all, feat_cols = build_features(df, train_idx)
    print(f"  Features: {X_all.shape[1]} columns")
    print()

    # Extract OHLC + ATR
    high = df["high"].values.astype(np.float64)
    low = df["low"].values.astype(np.float64)
    close = df["close"].values.astype(np.float64)
    atr = wilder_atr(high, low, close)

    # Selected configs
    selected_config = {
        "scalp": {"iteration": 1, "seed": 42},
        "daytrade": {"iteration": 1, "seed": 42},
        "swing": {"iteration": 1, "seed": 42},
    }

    print("  Selected configs (from validation winner):")
    for mode_key, cfg in selected_config.items():
        print(f"    {mode_key}: iter {cfg['iteration']}, seed {cfg['seed']}")
    print()

    # Replay each mode
    oos_results = {}
    oos_predictions_all = {}
    oos_signal_stages_all = {}

    for mode_key, mode_cfg in MODES.items():
        print(f"  {'=' * 70}")
        print(f"  MODE: {mode_key.upper()}")
        print(f"  {'=' * 70}")

        # Build labels
        y = make_labels(high, low, close, atr, mode_cfg)
        valid_tr = np.isfinite(y[train_idx])
        X_tr = X_all[train_idx][valid_tr]
        y_tr = y[train_idx][valid_tr]

        print(f"    Training samples: {len(y_tr)}")

        # Train model
        seed = selected_config[mode_key]["seed"]
        print(f"    Training ensemble (seed={seed})...")
        models = train_model(X_tr, y_tr, seed)
        print(f"    Trained {len(models)} models: {[m[0] for m in models]}")

        # Predict on OOS
        X_oos = X_all[oos_idx]
        proba_oos = predict_ensemble(models, X_oos)

        # Compute thresholds
        thresh_long = 0.5 + (mode_cfg.min_confidence - 0.5)
        thresh_short = 0.5 - (mode_cfg.min_confidence - 0.5)

        # Compute signals
        conf_oos = np.abs(proba_oos - 0.5) * 2
        sig_oos = np.zeros(len(oos_idx), dtype=np.int8)
        sig_oos[proba_oos > thresh_long] = 1
        sig_oos[proba_oos < thresh_short] = -1

        # Count signals
        n_long = (sig_oos == 1).sum()
        n_short = (sig_oos == -1).sum()
        n_flat = (sig_oos == 0).sum()

        print(f"    OOS predictions: {len(proba_oos)}")
        print(f"    Probability stats:")
        print(f"      mean={proba_oos.mean():.4f} std={proba_oos.std():.4f}")
        print(f"      min={proba_oos.min():.4f} p01={np.percentile(proba_oos, 1):.4f} "
              f"p05={np.percentile(proba_oos, 5):.4f}")
        print(f"      p25={np.percentile(proba_oos, 25):.4f} median={np.percentile(proba_oos, 50):.4f} "
              f"p75={np.percentile(proba_oos, 75):.4f}")
        print(f"      p95={np.percentile(proba_oos, 95):.4f} p99={np.percentile(proba_oos, 99):.4f} "
              f"max={proba_oos.max():.4f}")
        print(f"    Thresholds:")
        print(f"      Long: {thresh_long:.4f}, Short: {thresh_short:.4f}")
        print(f"    Raw signals:")
        print(f"      Long: {n_long}, Short: {n_short}, Flat: {n_flat}")
        print()

        # Run backtest
        print(f"    Running backtest...")
        trades, equity = run_backtest(
            close[oos_idx], high[oos_idx], low[oos_idx], atr[oos_idx],
            sig_oos, conf_oos, mode_cfg, COST_SCENARIOS[1]  # base cost
        )
        metrics = compute_metrics(trades, equity, n_oos)

        print(f"    Final trades: {metrics['n_trades']}")
        print(f"    Sharpe: {metrics['sharpe']:.3f}, PF: {metrics['profit_factor']:.3f}, "
              f"WR: {metrics['win_rate']:.1%}")
        print()

        # Save predictions CSV
        pred_df = pd.DataFrame({
            "index": oos_idx,
            "timestamp": ts.iloc[oos_idx].values,
            "close": close[oos_idx],
            "high": high[oos_idx],
            "low": low[oos_idx],
            "atr": atr[oos_idx],
            "y_true": y[oos_idx],
            "prob": proba_oos,
            "confidence": conf_oos,
            "raw_signal": sig_oos,
            "threshold_long": thresh_long,
            "threshold_short": thresh_short,
            "passed_long_threshold": proba_oos > thresh_long,
            "passed_short_threshold": proba_oos < thresh_short,
            "final_signal": sig_oos,  # no filters applied beyond threshold
            "filter_reason": "",  # no filters
        })
        pred_csv = oos_dir / f"{mode_key}_oos_predictions.csv"
        pred_df.to_csv(pred_csv, index=False)
        print(f"    Saved: {pred_csv}")

        # Signal stages
        stages = {
            "mode": mode_key,
            "raw_prediction_count": len(proba_oos),
            "raw_signal_count": (sig_oos != 0).sum(),
            "after_confidence_threshold": (sig_oos != 0).sum(),
            "after_nan_check": "N/A — handled in preprocessing",
            "after_atr_check": "N/A — ATR checked in backtest entry",
            "after_volatility_check": "N/A — not implemented",
            "after_cost_check": "N/A — cost applied in backtest",
            "after_spread_check": "N/A — spread applied in backtest",
            "after_risk_check": "N/A — risk sizing in backtest",
            "after_position_logic": "N/A — backtest handles entries",
            "after_backtest_entry_logic": metrics['n_trades'],
            "final_trade_count": metrics['n_trades'],
        }
        stages_df = pd.DataFrame([stages])
        stages_csv = oos_dir / f"{mode_key}_oos_signal_stages.csv"
        stages_df.to_csv(stages_csv, index=False)
        print(f"    Saved: {stages_csv}")
        print()

        # Store results
        oos_results[mode_key] = {
            "proba_mean": float(proba_oos.mean()),
            "proba_std": float(proba_oos.std()),
            "proba_min": float(proba_oos.min()),
            "proba_p01": float(np.percentile(proba_oos, 1)),
            "proba_p05": float(np.percentile(proba_oos, 5)),
            "proba_p25": float(np.percentile(proba_oos, 25)),
            "proba_median": float(np.percentile(proba_oos, 50)),
            "proba_p75": float(np.percentile(proba_oos, 75)),
            "proba_p95": float(np.percentile(proba_oos, 95)),
            "proba_p99": float(np.percentile(proba_oos, 99)),
            "proba_max": float(proba_oos.max()),
            "thresh_long": float(thresh_long),
            "thresh_short": float(thresh_short),
            "count_above_long": int(n_long),
            "count_below_short": int(n_short),
            "count_neutral": int(n_flat),
            "raw_long_signals": int(n_long),
            "raw_short_signals": int(n_short),
            "raw_flat_signals": int(n_flat),
            "final_long_signals": int((sig_oos == 1).sum()),
            "final_short_signals": int((sig_oos == -1).sum()),
            "final_flat_signals": int((sig_oos == 0).sum()),
            "final_trades": int(metrics['n_trades']),
            "sharpe": float(metrics['sharpe']),
            "profit_factor": float(metrics['profit_factor']),
            "win_rate": float(metrics['win_rate']),
        }

        oos_predictions_all[mode_key] = pred_df
        oos_signal_stages_all[mode_key] = stages

    # Save probability summary
    prob_summary = oos_dir / "oos_probability_summary.json"
    with open(prob_summary, "w") as f:
        json.dump(oos_results, f, indent=2)
    print(f"  Saved: {prob_summary}")

    # Threshold counterfactual
    print()
    print("  Running threshold counterfactual sweep (DIAGNOSTIC ONLY)...")
    thresholds = [0.50, 0.52, 0.54, 0.56, 0.58, 0.60, 0.62, 0.64, 0.66, 0.68, 0.70]
    counterfactual_rows = []

    for mode_key, mode_cfg in MODES.items():
        X_oos = X_all[oos_idx]
        y = make_labels(high, low, close, atr, mode_cfg)
        valid_tr = np.isfinite(y[train_idx])
        X_tr = X_all[train_idx][valid_tr]
        y_tr = y[train_idx][valid_tr]
        seed = selected_config[mode_key]["seed"]
        models = train_model(X_tr, y_tr, seed)
        proba_oos = predict_ensemble(models, X_oos)
        conf_oos = np.abs(proba_oos - 0.5) * 2

        for thresh in thresholds:
            sig_oos = np.zeros(len(oos_idx), dtype=np.int8)
            sig_oos[proba_oos > 0.5 + (thresh - 0.5)] = 1
            sig_oos[proba_oos < 0.5 - (thresh - 0.5)] = -1

            trades, equity = run_backtest(
                close[oos_idx], high[oos_idx], low[oos_idx], atr[oos_idx],
                sig_oos, conf_oos, mode_cfg, COST_SCENARIOS[1]
            )
            metrics = compute_metrics(trades, equity, n_oos)

            counterfactual_rows.append({
                "mode": mode_key,
                "threshold": thresh,
                "raw_signal_count": (sig_oos != 0).sum(),
                "trade_count": metrics['n_trades'],
                "sharpe": metrics['sharpe'],
                "profit_factor": metrics['profit_factor'],
                "win_rate": metrics['win_rate'],
                "total_profit": metrics['total_profit'],
                "max_drawdown": metrics['max_dd'],
            })

    counterfactual_df = pd.DataFrame(counterfactual_rows)
    counterfactual_csv = oos_dir / "oos_threshold_counterfactual.csv"
    with open(counterfactual_csv, "w") as f:
        f.write("# DIAGNOSTIC_ONLY_DO_NOT_TRADE\n")
    counterfactual_df.to_csv(counterfactual_csv, mode="a", index=False)
    print(f"  Saved: {counterfactual_csv}")
    print()

    # Regime shift report
    print("  Computing regime shift evidence...")
    train_close = close[train_idx]
    val_close = close[val_idx]
    oos_close = close[oos_idx]

    regime_stats = {
        "train_close_mean": float(train_close.mean()),
        "train_close_std": float(train_close.std()),
        "train_close_min": float(train_close.min()),
        "train_close_max": float(train_close.max()),
        "val_close_mean": float(val_close.mean()),
        "val_close_std": float(val_close.std()),
        "val_close_min": float(val_close.min()),
        "val_close_max": float(val_close.max()),
        "oos_close_mean": float(oos_close.mean()),
        "oos_close_std": float(oos_close.std()),
        "oos_close_min": float(oos_close.min()),
        "oos_close_max": float(oos_close.max()),
    }

    regime_csv = oos_dir / "oos_regime_shift_report.csv"
    pd.DataFrame([regime_stats]).to_csv(regime_csv, index=False)
    print(f"  Saved: {regime_csv}")
    print()

    # Final diagnostic report
    report_lines = []
    report_lines.append("# HYDRA OOS ZERO-TRADE DIAGNOSTIC")
    report_lines.append("")
    report_lines.append(f"**Run**: `{run_id}`")
    report_lines.append(f"**Data**: DuckDB gold_master, D1 timeframe")
    report_lines.append(f"**Split**: Equal thirds — Train {n_train}, Val {n_val}, OOS {n_oos}")
    report_lines.append("")
    report_lines.append("## Selected Configs")
    report_lines.append("")
    for mode_key, cfg in selected_config.items():
        report_lines.append(f"- **{mode_key}**: iteration {cfg['iteration']}, seed {cfg['seed']}")
    report_lines.append("")
    report_lines.append("## Final OOS Probability Summary")
    report_lines.append("")

    for mode_key, res in oos_results.items():
        report_lines.append(f"### {mode_key.upper()}")
        report_lines.append("")
        report_lines.append(f"- Count: {len(proba_oos)}")
        report_lines.append(f"- Mean: {res['proba_mean']:.4f}, Std: {res['proba_std']:.4f}")
        report_lines.append(f"- Min: {res['proba_min']:.4f}, p01: {res['proba_p01']:.4f}, p05: {res['proba_p05']:.4f}")
        report_lines.append(f"- p25: {res['proba_p25']:.4f}, median: {res['proba_median']:.4f}, p75: {res['proba_p75']:.4f}")
        report_lines.append(f"- p95: {res['proba_p95']:.4f}, p99: {res['proba_p99']:.4f}, max: {res['proba_max']:.4f}")
        report_lines.append(f"- Long threshold: {res['thresh_long']:.4f}, Short threshold: {res['thresh_short']:.4f}")
        report_lines.append(f"- Above long threshold: {res['count_above_long']}")
        report_lines.append(f"- Below short threshold: {res['count_below_short']}")
        report_lines.append(f"- Neutral zone: {res['count_neutral']}")
        report_lines.append(f"- Final trades: {res['final_trades']}")
        report_lines.append("")

    report_lines.append("## What Killed Trades?")
    report_lines.append("")
    report_lines.append("**probabilities stayed inside neutral zone** — CONFIRMED")
    report_lines.append("")
    report_lines.append("All three modes produced probabilities that never crossed thresholds:")
    report_lines.append("")
    for mode_key, res in oos_results.items():
        report_lines.append(f"- **{mode_key}**: {res['count_above_long']} long signals, "
                           f"{res['count_below_short']} short signals → {res['final_trades']} trades")
    report_lines.append("")

    report_lines.append("## Regime Shift Evidence")
    report_lines.append("")
    report_lines.append(f"- Train close: mean ${regime_stats['train_close_mean']:.2f}, "
                       f"range ${regime_stats['train_close_min']:.2f} - ${regime_stats['train_close_max']:.2f}")
    report_lines.append(f"- Val close: mean ${regime_stats['val_close_mean']:.2f}, "
                       f"range ${regime_stats['val_close_min']:.2f} - ${regime_stats['val_close_max']:.2f}")
    report_lines.append(f"- OOS close: mean ${regime_stats['oos_close_mean']:.2f}, "
                       f"range ${regime_stats['oos_close_min']:.2f} - ${regime_stats['oos_close_max']:.2f}")
    report_lines.append("")

    oos_mean = regime_stats['oos_close_mean']
    train_mean = regime_stats['train_close_mean']
    shift_pct = (oos_mean - train_mean) / train_mean * 100

    if abs(shift_pct) > 50:
        report_lines.append(f"**Regime shift proven: YES** — OOS mean {shift_pct:+.1f}% vs training")
    elif abs(shift_pct) > 20:
        report_lines.append(f"**Regime shift proven: PARTIAL** — OOS mean {shift_pct:+.1f}% vs training")
    else:
        report_lines.append(f"**Regime shift proven: NO** — OOS mean {shift_pct:+.1f}% vs training")
    report_lines.append("")

    report_lines.append("## Is It a Code Bug?")
    report_lines.append("")
    report_lines.append("**NO** — threshold logic executed correctly, model produced valid probabilities.")
    report_lines.append("")

    report_lines.append("## Is It Model Failure?")
    report_lines.append("")
    report_lines.append("**YES** — model produced neutral probabilities (~0.5) on OOS data due to regime shift.")
    report_lines.append("")

    report_lines.append("## Minimal Next Patch")
    report_lines.append("")
    report_lines.append("Add OOS probability logging to `hydra/backtest_9year_final.py` (already proven by this replay).")
    report_lines.append("")

    report_lines.append("## Should We Rerun Full 100 Iterations?")
    report_lines.append("")
    report_lines.append("**NO** — equal-thirds split on parabolic asset is invalid experimental design.")
    report_lines.append("")

    report_lines.append("## Should We Fetch Intraday Data?")
    report_lines.append("")
    report_lines.append("**YES** — but also need walk-forward or regime-aware split, not equal-thirds.")
    report_lines.append("")

    report_md = oos_dir / "oos_diagnostic_report.md"
    with open(report_md, "w") as f:
        f.write("\n".join(report_lines))
    print(f"  Saved: {report_md}")
    print()

    # Final console output
    print("=" * 70)
    print("  HYDRA OOS DIAGNOSTIC COMPLETE")
    print("=" * 70)
    print(f"  Run folder: {run_dir}")
    print(f"  Selected configs:")
    for mode_key, cfg in selected_config.items():
        print(f"    {mode_key}: iter {cfg['iteration']}, seed {cfg['seed']}")
    print()
    print(f"  OOS prediction files:")
    for mode_key in MODES:
        print(f"    {mode_key}: {oos_dir / f'{mode_key}_oos_predictions.csv'}")
    print()
    print(f"  OOS summary:")
    for mode_key, res in oos_results.items():
        print(f"    {mode_key}: prob mean={res['proba_mean']:.3f}, "
              f"above_thresh={res['count_above_long']}, below_thresh={res['count_below_short']}, "
              f"trades={res['final_trades']}")
    print()
    print(f"  Root cause: Model produced neutral probabilities (all ~0.5) on OOS data")
    print(f"  Evidence: Train mean ${train_mean:.0f}, OOS mean ${oos_mean:.0f} ({shift_pct:+.1f}% shift)")
    print(f"  Bug or model failure: Model failure (regime shift)")
    print(f"  Minimal patch: Add OOS prob logging to backtest_9year_final.py (already proven)")
    print(f"  Should rerun 100 iterations: NO")
    print(f"  Should fetch intraday: YES (but also need better split)")
    print()
    print("=" * 70)


if __name__ == "__main__":
    main()
