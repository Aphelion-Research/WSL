"""End-to-end strategy: enhanced features → LightGBM walk-forward → realistic backtest.

Strategy thesis:
- Multi-TF momentum divergence (H4 trend vs M5 mean-reversion)
- Session timing (London/NY overlap, Asian range breakout)
- Volatility regime filtering (trade high-vol regimes only)
- Asymmetric cost model (spread + slippage + commission)

Usage:
    python -m datasets.strategy_v1
"""
from __future__ import annotations

import datetime
from pathlib import Path

import numpy as np
import polars as pl
import lightgbm as lgb
from scipy.stats import spearmanr

ROOT = Path.home() / "Dominion"
DATASET_PATH = ROOT / "datasets" / "mtf_xauusd_v1.parquet"
OUTPUT_DIR = ROOT / "datasets" / "strategy_results"


# ─── FEATURE ENGINEERING ───────────────────────────────────────────────────

def add_session_features(df: pl.DataFrame) -> pl.DataFrame:
    """Calendar/session features — all point-in-time safe (derived from timestamp)."""
    ts = pl.col("timestamp")
    return df.with_columns([
        ts.dt.hour().alias("hour"),
        ts.dt.weekday().alias("dow"),
        # Session flags
        ((ts.dt.hour() >= 8) & (ts.dt.hour() < 16)).cast(pl.Int8).alias("london_session"),
        ((ts.dt.hour() >= 13) & (ts.dt.hour() < 21)).cast(pl.Int8).alias("ny_session"),
        ((ts.dt.hour() >= 13) & (ts.dt.hour() < 16)).cast(pl.Int8).alias("london_ny_overlap"),
        ((ts.dt.hour() >= 0) & (ts.dt.hour() < 8)).cast(pl.Int8).alias("asian_session"),
        # Cyclical encoding
        (2.0 * np.pi * ts.dt.hour().cast(pl.Float64) / 24.0).sin().alias("hour_sin"),
        (2.0 * np.pi * ts.dt.hour().cast(pl.Float64) / 24.0).cos().alias("hour_cos"),
        (2.0 * np.pi * ts.dt.weekday().cast(pl.Float64) / 5.0).sin().alias("dow_sin"),
        (2.0 * np.pi * ts.dt.weekday().cast(pl.Float64) / 5.0).cos().alias("dow_cos"),
    ])


def add_momentum_divergence(df: pl.DataFrame) -> pl.DataFrame:
    """Cross-TF momentum divergence — signals when fast TF disagrees with slow TF."""
    return df.with_columns([
        # M5 vs H1 momentum divergence
        (pl.col("m5_logret_5") - pl.col("h1_logret_1")).alias("div_m5_h1_momentum"),
        # M5 vs H4 momentum divergence
        (pl.col("m5_logret_10") - pl.col("h4_logret_1")).alias("div_m5_h4_momentum"),
        # RSI divergence
        (pl.col("m5_rsi_14") - pl.col("h1_rsi_14")).alias("div_rsi_m5_h1"),
        (pl.col("m5_rsi_14") - pl.col("h4_rsi_14")).alias("div_rsi_m5_h4"),
        # Volatility divergence (M5 vol vs H1 vol)
        (pl.col("m5_rvol_10") / (pl.col("h1_rvol_10") + 1e-10)).alias("vol_ratio_m5_h1"),
        (pl.col("m5_rvol_20") / (pl.col("h4_rvol_10") + 1e-10)).alias("vol_ratio_m5_h4"),
    ])


def add_microstructure_from_bars(df: pl.DataFrame) -> pl.DataFrame:
    """Microstructure proxies from bar data."""
    return df.with_columns([
        # Spread expansion (current spread vs rolling median)
        (pl.col("spread") / (pl.col("spread").shift(1).rolling_median(20) + 1e-10))
        .clip(0.0, 10.0).alias("spread_expansion"),
        # Tick intensity (tick_volume relative to expected)
        (pl.col("tick_volume").cast(pl.Float64) /
         (pl.col("tick_volume").shift(1).cast(pl.Float64).rolling_mean(50) + 1e-10))
        .clip(0.0, 10.0).alias("tick_intensity"),
        # Bar body ratio: abs(close-open) / (high-low) — directional conviction
        ((pl.col("close") - pl.col("open")).abs() /
         (pl.col("high") - pl.col("low") + 1e-10))
        .clip(0.0, 1.0).alias("body_ratio"),
        # Upper/lower wick ratios
        ((pl.col("high") - pl.max_horizontal("open", "close")) /
         (pl.col("high") - pl.col("low") + 1e-10))
        .clip(0.0, 1.0).alias("upper_wick_ratio"),
        ((pl.min_horizontal("open", "close") - pl.col("low")) /
         (pl.col("high") - pl.col("low") + 1e-10))
        .clip(0.0, 1.0).alias("lower_wick_ratio"),
    ])


def add_range_breakout(df: pl.DataFrame) -> pl.DataFrame:
    """Asian session range breakout indicator."""
    return df.with_columns([
        # Rolling 12-bar (1 hour) high/low range
        (pl.col("close") - pl.col("low").shift(1).rolling_min(12)).alias("_dist_from_low12"),
        (pl.col("high").shift(1).rolling_max(12) - pl.col("close")).alias("_dist_from_high12"),
    ]).with_columns([
        # Position within recent range [0, 1]
        (pl.col("_dist_from_low12") /
         (pl.col("_dist_from_low12") + pl.col("_dist_from_high12") + 1e-10))
        .clip(0.0, 1.0).alias("range_position_12"),
    ]).drop(["_dist_from_low12", "_dist_from_high12"]).with_columns([
        # Rolling 48-bar (4 hour) range position
        ((pl.col("close") - pl.col("low").shift(1).rolling_min(48)) /
         (pl.col("high").shift(1).rolling_max(48) - pl.col("low").shift(1).rolling_min(48) + 1e-10))
        .clip(0.0, 1.0).alias("range_position_48"),
    ])


def add_volatility_features(df: pl.DataFrame) -> pl.DataFrame:
    """Volatility regime features."""
    return df.with_columns([
        # Vol of vol (realized vol of realized vol)
        pl.col("m5_rvol_10").rolling_std(20).alias("vol_of_vol_20"),
        # Vol ratio short/long
        (pl.col("m5_rvol_5") / (pl.col("m5_rvol_50") + 1e-10)).alias("vol_term_structure"),
        # Spread vol ratio (spread normalized by ATR)
        (pl.col("spread") / (pl.col("m5_atr_pct_14") * pl.col("close") + 1e-10))
        .clip(0.0, 5.0).alias("spread_atr_ratio"),
    ])


def build_features(df: pl.DataFrame) -> pl.DataFrame:
    """Full feature build pipeline."""
    df = add_session_features(df)
    df = add_momentum_divergence(df)
    df = add_microstructure_from_bars(df)
    df = add_range_breakout(df)
    df = add_volatility_features(df)
    return df


# ─── WALK-FORWARD TRAINING ─────────────────────────────────────────────────

def get_feature_cols(df: pl.DataFrame) -> list[str]:
    exclude = {
        "timestamp", "open", "high", "low", "close",
        "tick_volume", "spread", "spread_std", "volume", "target",
        "hour", "dow",
    }
    return [c for c in df.columns if c not in exclude]


def walk_forward_train(
    df: pl.DataFrame,
    feature_cols: list[str],
    n_splits: int = 5,
    train_years: int = 3,
    val_months: int = 6,
    test_months: int = 6,
    purge_bars: int = 24,  # 2 hours gap
) -> dict:
    """Expanding-window walk-forward with purge/embargo.

    Each fold:
    - Train: expanding window (at least train_years of data)
    - Purge: 2h gap (prevent label leakage at boundary)
    - Validation: 6 months (for early stopping)
    - Purge: 2h gap
    - Test: 6 months (out-of-sample evaluation)
    """
    timestamps = df["timestamp"].to_numpy()
    target = df["target"].to_numpy()
    X = df.select(feature_cols).to_numpy().astype(np.float32)

    # Replace inf/nan for training
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)

    n = len(df)
    valid_mask = np.isfinite(target)

    # Determine split boundaries based on time
    start_dt = timestamps[0]
    end_dt = timestamps[-1]

    # First test starts after train_years
    first_test_start = start_dt + np.timedelta64(train_years * 365, "D")

    results = {
        "folds": [],
        "oos_predictions": np.full(n, np.nan, dtype=np.float64),
        "models": [],
    }

    # Generate folds
    fold_starts = []
    current_test_start = first_test_start
    while current_test_start < end_dt - np.timedelta64(test_months * 30, "D"):
        fold_starts.append(current_test_start)
        current_test_start += np.timedelta64(test_months * 30, "D")

    if len(fold_starts) > n_splits:
        fold_starts = fold_starts[-n_splits:]

    print(f"Walk-forward: {len(fold_starts)} folds, {len(feature_cols)} features")
    print()

    for fold_idx, test_start in enumerate(fold_starts):
        val_start = test_start - np.timedelta64(val_months * 30, "D")
        test_end = test_start + np.timedelta64(test_months * 30, "D")

        # Index ranges
        train_mask = (timestamps < val_start - np.timedelta64(purge_bars * 5, "m")) & valid_mask
        val_mask = (
            (timestamps >= val_start) &
            (timestamps < test_start - np.timedelta64(purge_bars * 5, "m")) &
            valid_mask
        )
        test_mask = (timestamps >= test_start) & (timestamps < test_end) & valid_mask

        n_train = train_mask.sum()
        n_val = val_mask.sum()
        n_test = test_mask.sum()

        if n_train < 1000 or n_val < 100 or n_test < 100:
            print(f"  Fold {fold_idx}: skipped (insufficient data)")
            continue

        print(f"  Fold {fold_idx}: train={n_train:,} val={n_val:,} test={n_test:,}")

        # Train LightGBM
        dtrain = lgb.Dataset(X[train_mask], target[train_mask])
        dval = lgb.Dataset(X[val_mask], target[val_mask], reference=dtrain)

        # Compute scale_pos_weight for proper class balancing
        n_pos = target[train_mask].sum()
        n_neg = train_mask.sum() - n_pos
        spw = n_neg / n_pos if n_pos > 0 else 1.0

        params = {
            "objective": "binary",
            "metric": "auc",
            "boosting_type": "gbdt",
            "learning_rate": 0.05,
            "num_leaves": 31,
            "max_depth": 5,
            "min_child_samples": 200,
            "subsample": 0.7,
            "subsample_freq": 1,
            "colsample_bytree": 0.5,
            "reg_alpha": 2.0,
            "reg_lambda": 10.0,
            "min_gain_to_split": 0.1,
            "scale_pos_weight": spw,
            "verbosity": -1,
            "n_jobs": -1,
            "seed": 42 + fold_idx,
            "max_bin": 127,
        }

        callbacks = [
            lgb.early_stopping(100, verbose=False),
            lgb.log_evaluation(0),
        ]

        model = lgb.train(
            params,
            dtrain,
            num_boost_round=3000,
            valid_sets=[dval],
            callbacks=callbacks,
        )

        # Predict on test
        preds = model.predict(X[test_mask])
        results["oos_predictions"][test_mask] = preds
        results["models"].append(model)

        # Fold metrics
        from sklearn.metrics import roc_auc_score, log_loss
        auc = roc_auc_score(target[test_mask], preds)
        ll = log_loss(target[test_mask], preds)
        ic = spearmanr(preds, target[test_mask])[0]

        results["folds"].append({
            "fold": fold_idx,
            "n_train": n_train,
            "n_test": n_test,
            "auc": auc,
            "logloss": ll,
            "ic": ic,
            "n_trees": model.best_iteration,
            "test_start": str(test_start),
            "test_end": str(test_end),
        })

        print(f"    AUC={auc:.4f} IC={ic:.4f} LogLoss={ll:.4f} Trees={model.best_iteration}")

    return results


# ─── BACKTEST ──────────────────────────────────────────────────────────────

def backtest(
    df: pl.DataFrame,
    predictions: np.ndarray,
    long_threshold: float = 0.55,
    short_threshold: float = 0.35,
    spread_points: float = 0.50,
    slippage_points: float = 0.15,
    commission_per_lot: float = 1.0,
    lot_size: float = 0.1,
    pip_value: float = 1.0,
    atr_sl_mult: float = 1.5,
    atr_tp_mult: float = 2.5,
    max_holding_bars: int = 20,
    capital: float = 100_000.0,
    risk_per_trade_pct: float = 1.0,
) -> dict:
    """Realistic bar-by-bar backtest with next-bar entry.

    Rules:
    - Signal at bar t → enter at OPEN of bar t+1 (no same-bar entry)
    - Entry price adjusted for spread + slippage
    - ATR-based stop/TP (adaptive to volatility)
    - Maximum holding period (force exit at open of bar t+max_holding)
    - Risk sizing: risk_per_trade_pct of capital per trade
    - Commission: per round-trip
    """
    timestamps = df["timestamp"].to_numpy()
    open_prices = df["open"].to_numpy()
    high_prices = df["high"].to_numpy()
    low_prices = df["low"].to_numpy()
    close_prices = df["close"].to_numpy()

    # ATR for position sizing and stops
    atr_pct = df["m5_atr_pct_14"].to_numpy()

    n = len(df)
    trades = []
    equity_curve = np.zeros(n)
    equity = capital
    position = None  # {"direction", "entry_price", "sl", "tp", "entry_bar", "size"}

    total_cost = spread_points + slippage_points

    for i in range(1, n):
        equity_curve[i] = equity

        # Check existing position
        if position is not None:
            direction = position["direction"]
            entry_bar = position["entry_bar"]
            bars_held = i - entry_bar

            # Check stop loss / take profit
            hit_sl = False
            hit_tp = False
            exit_price = None
            exit_reason = None

            if direction == 1:  # Long
                if low_prices[i] <= position["sl"]:
                    hit_sl = True
                    exit_price = position["sl"]
                    exit_reason = "sl"
                elif high_prices[i] >= position["tp"]:
                    hit_tp = True
                    exit_price = position["tp"]
                    exit_reason = "tp"
            else:  # Short
                if high_prices[i] >= position["sl"]:
                    hit_sl = True
                    exit_price = position["sl"]
                    exit_reason = "sl"
                elif low_prices[i] <= position["tp"]:
                    hit_tp = True
                    exit_price = position["tp"]
                    exit_reason = "tp"

            # Max holding period exit
            if not hit_sl and not hit_tp and bars_held >= max_holding_bars:
                exit_price = open_prices[i]
                exit_reason = "timeout"

            # Conservative: if both SL and TP could hit in same bar, SL wins
            if hit_sl and hit_tp:
                exit_price = position["sl"]
                exit_reason = "sl"
                hit_tp = False

            if exit_price is not None:
                # Calculate PnL
                if direction == 1:
                    pnl_points = exit_price - position["entry_price"]
                else:
                    pnl_points = position["entry_price"] - exit_price

                # Subtract exit cost
                pnl_points -= total_cost / 2  # half spread on exit

                pnl_money = pnl_points * pip_value * lot_size * 100 * position["size"]
                pnl_money -= commission_per_lot * position["size"]  # commission

                equity += pnl_money

                trades.append({
                    "entry_bar": entry_bar,
                    "exit_bar": i,
                    "direction": direction,
                    "entry_price": position["entry_price"],
                    "exit_price": exit_price,
                    "exit_reason": exit_reason,
                    "pnl_points": pnl_points,
                    "pnl_money": pnl_money,
                    "bars_held": bars_held,
                    "entry_time": str(timestamps[entry_bar]),
                    "exit_time": str(timestamps[i]),
                })

                position = None

        # Generate new signal (only if flat)
        if position is None and i < n - max_holding_bars:
            pred = predictions[i - 1]  # signal from PREVIOUS bar
            if np.isnan(pred):
                continue

            # ATR check
            if not np.isfinite(atr_pct[i - 1]) or atr_pct[i - 1] < 0.0003:
                continue

            atr_abs = atr_pct[i - 1] * close_prices[i - 1]

            # Risk sizing
            risk_amount = equity * risk_per_trade_pct / 100.0
            sl_distance = atr_sl_mult * atr_abs
            if sl_distance < 0.01:
                continue
            # lots = risk / (SL distance in money per lot)
            money_per_point = pip_value * lot_size * 100
            lots = risk_amount / (sl_distance * money_per_point)
            lots = min(lots, 5.0)  # cap at 5 lots
            lots = max(lots, 0.01)

            # Session filter: only trade during London/NY hours (7-20 UTC)
            bar_hour = (timestamps[i] - timestamps[i].astype("datetime64[D]")).astype("timedelta64[h]").astype(int)
            if bar_hour < 7 or bar_hour >= 20:
                continue

            if pred > long_threshold:
                entry_price = open_prices[i] + total_cost / 2
                sl = entry_price - atr_sl_mult * atr_abs
                tp = entry_price + atr_tp_mult * atr_abs
                position = {
                    "direction": 1,
                    "entry_price": entry_price,
                    "sl": sl,
                    "tp": tp,
                    "entry_bar": i,
                    "size": lots,
                }
            elif pred < short_threshold:
                entry_price = open_prices[i] - total_cost / 2
                sl = entry_price + atr_sl_mult * atr_abs
                tp = entry_price - atr_tp_mult * atr_abs
                position = {
                    "direction": -1,
                    "entry_price": entry_price,
                    "sl": sl,
                    "tp": tp,
                    "entry_bar": i,
                    "size": lots,
                }

    equity_curve[-1] = equity

    # Compute metrics
    if not trades:
        return {"error": "No trades generated"}

    pnls = np.array([t["pnl_money"] for t in trades])
    directions = np.array([t["direction"] for t in trades])
    exit_reasons = [t["exit_reason"] for t in trades]

    n_trades = len(trades)
    n_long = (directions == 1).sum()
    n_short = (directions == -1).sum()
    winners = pnls > 0
    win_rate = winners.mean()

    # Separate long/short stats
    long_mask = directions == 1
    short_mask = directions == -1
    long_wr = pnls[long_mask].mean() if long_mask.sum() > 0 else 0
    short_wr = pnls[short_mask].mean() if short_mask.sum() > 0 else 0

    total_pnl = pnls.sum()
    avg_win = pnls[winners].mean() if winners.sum() > 0 else 0
    avg_loss = pnls[~winners].mean() if (~winners).sum() > 0 else 0
    profit_factor = abs(pnls[winners].sum() / pnls[~winners].sum()) if (~winners).sum() > 0 and pnls[~winners].sum() != 0 else 0

    # Sharpe (annualized from per-trade PnL)
    if pnls.std() > 0:
        avg_bars = np.mean([t["bars_held"] for t in trades])
        trades_per_year = (252 * 288) / avg_bars if avg_bars > 0 else 1
        sharpe = (pnls.mean() / pnls.std()) * np.sqrt(trades_per_year)
    else:
        sharpe = 0

    # Max drawdown
    cum_pnl = np.cumsum(pnls)
    running_max = np.maximum.accumulate(cum_pnl)
    drawdown = cum_pnl - running_max
    max_dd = drawdown.min()
    max_dd_pct = max_dd / capital * 100 if capital > 0 else 0

    # Calmar
    years = (timestamps[-1] - timestamps[0]).astype("timedelta64[D]").astype(int) / 365.25
    annual_return = total_pnl / capital / years * 100 if years > 0 else 0
    calmar = annual_return / abs(max_dd_pct) if max_dd_pct != 0 else 0

    return {
        "n_trades": n_trades,
        "n_long": int(n_long),
        "n_short": int(n_short),
        "win_rate": win_rate,
        "total_pnl": total_pnl,
        "avg_pnl_per_trade": pnls.mean(),
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "profit_factor": profit_factor,
        "sharpe": sharpe,
        "max_drawdown": max_dd,
        "max_drawdown_pct": max_dd_pct,
        "annual_return_pct": annual_return,
        "calmar": calmar,
        "avg_bars_held": np.mean([t["bars_held"] for t in trades]),
        "exit_reasons": {
            "tp": exit_reasons.count("tp"),
            "sl": exit_reasons.count("sl"),
            "timeout": exit_reasons.count("timeout"),
        },
        "equity_curve": equity_curve,
        "trades": trades,
        "long_avg_pnl": float(long_wr),
        "short_avg_pnl": float(short_wr),
    }


# ─── MAIN ─────────────────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print("DOMINION STRATEGY V1 — Multi-TF LightGBM + Realistic Backtest")
    print("=" * 70)
    print()

    # Load dataset
    print("Loading dataset...")
    df = pl.read_parquet(DATASET_PATH)
    print(f"  Raw: {df.shape}")

    # Build enhanced features
    print("Building enhanced features...")
    df = build_features(df)
    print(f"  After features: {df.shape}")

    # Get feature columns
    feature_cols = get_feature_cols(df)
    print(f"  Feature count: {len(feature_cols)}")

    # Drop rows where target is NaN (can't train on them)
    # But keep them in the dataframe for backtest continuity
    print()

    # Walk-forward training
    print("─" * 70)
    print("WALK-FORWARD TRAINING")
    print("─" * 70)

    results = walk_forward_train(
        df, feature_cols,
        n_splits=8,
        train_years=3,
        val_months=6,
        test_months=6,
    )

    # Print fold summary
    print()
    print("Fold Summary:")
    print(f"  {'Fold':<6} {'AUC':<8} {'IC':<8} {'LogLoss':<10} {'Trees':<6} {'Period'}")
    print("  " + "-" * 65)
    for f in results["folds"]:
        print(f"  {f['fold']:<6} {f['auc']:<8.4f} {f['ic']:<8.4f} {f['logloss']:<10.4f} {f['n_trees']:<6} {f['test_start'][:10]}")

    mean_auc = np.mean([f["auc"] for f in results["folds"]])
    mean_ic = np.mean([f["ic"] for f in results["folds"]])
    print(f"\n  Mean AUC: {mean_auc:.4f}")
    print(f"  Mean IC: {mean_ic:.4f}")

    # Feature importance (from last model)
    if results["models"]:
        last_model = results["models"][-1]
        importance = last_model.feature_importance(importance_type="gain")
        imp_idx = np.argsort(importance)[::-1][:20]
        print("\n  Top-20 Features (gain):")
        for rank, idx in enumerate(imp_idx):
            print(f"    {rank+1:2d}. {feature_cols[idx]:<35s} {importance[idx]:>10.1f}")

    # Backtest on OOS predictions
    print()
    print("─" * 70)
    print("BACKTEST (Out-of-Sample Only)")
    print("─" * 70)

    predictions = results["oos_predictions"]
    has_pred = ~np.isnan(predictions)
    print(f"  OOS predictions available: {has_pred.sum():,} bars")

    # Only backtest where we have OOS predictions
    bt_mask = has_pred
    if bt_mask.sum() < 1000:
        print("  ERROR: Not enough OOS predictions for backtest")
        return

    # Adaptive thresholds: only trade when model is confident
    # Use top/bottom 20% of predictions as signals
    valid_preds = predictions[has_pred]
    long_thresh = np.percentile(valid_preds, 80)
    short_thresh = np.percentile(valid_preds, 20)
    print(f"  Adaptive thresholds: long>{long_thresh:.4f}, short<{short_thresh:.4f}")

    bt = backtest(
        df,
        predictions,
        long_threshold=long_thresh,
        short_threshold=short_thresh,
        spread_points=0.50,
        slippage_points=0.15,
        commission_per_lot=1.0,
        lot_size=0.1,
        atr_sl_mult=1.5,
        atr_tp_mult=2.5,
        max_holding_bars=20,
        capital=100_000.0,
        risk_per_trade_pct=1.0,
    )

    if "error" in bt:
        print(f"  ERROR: {bt['error']}")
        return

    print(f"\n  {'Metric':<25s} {'Value':<15s}")
    print("  " + "-" * 40)
    print(f"  {'Trades':<25s} {bt['n_trades']}")
    print(f"  {'Long / Short':<25s} {bt['n_long']} / {bt['n_short']}")
    print(f"  {'Win Rate':<25s} {bt['win_rate']*100:.1f}%")
    print(f"  {'Profit Factor':<25s} {bt['profit_factor']:.2f}")
    print(f"  {'Total PnL':<25s} ${bt['total_pnl']:,.0f}")
    print(f"  {'Avg PnL/Trade':<25s} ${bt['avg_pnl_per_trade']:.2f}")
    print(f"  {'Avg Win':<25s} ${bt['avg_win']:.2f}")
    print(f"  {'Avg Loss':<25s} ${bt['avg_loss']:.2f}")
    print(f"  {'Sharpe':<25s} {bt['sharpe']:.2f}")
    print(f"  {'Max Drawdown':<25s} ${bt['max_drawdown']:,.0f} ({bt['max_drawdown_pct']:.1f}%)")
    print(f"  {'Annual Return':<25s} {bt['annual_return_pct']:.1f}%")
    print(f"  {'Calmar Ratio':<25s} {bt['calmar']:.2f}")
    print(f"  {'Avg Bars Held':<25s} {bt['avg_bars_held']:.1f}")
    print(f"  {'Exit Reasons':<25s} TP={bt['exit_reasons']['tp']} SL={bt['exit_reasons']['sl']} Timeout={bt['exit_reasons']['timeout']}")
    print(f"  {'Long Avg PnL':<25s} ${bt['long_avg_pnl']:.2f}")
    print(f"  {'Short Avg PnL':<25s} ${bt['short_avg_pnl']:.2f}")

    # Monthly breakdown
    print()
    print("  Monthly PnL Breakdown (last 2 years):")
    trades_arr = bt["trades"]
    monthly_pnl = {}
    for t in trades_arr:
        month_key = t["exit_time"][:7]
        monthly_pnl[month_key] = monthly_pnl.get(month_key, 0) + t["pnl_money"]

    months_sorted = sorted(monthly_pnl.keys())[-24:]
    pos_months = sum(1 for m in months_sorted if monthly_pnl[m] > 0)
    neg_months = len(months_sorted) - pos_months
    print(f"  Positive months: {pos_months}/{len(months_sorted)}")

    for m in months_sorted:
        bar = "█" * max(1, int(abs(monthly_pnl[m]) / 500))
        sign = "+" if monthly_pnl[m] > 0 else "-"
        print(f"    {m}: {sign}${abs(monthly_pnl[m]):>8,.0f} {'▓' if monthly_pnl[m] > 0 else '░'}{bar}")

    # Save results
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Save equity curve
    eq_df = pl.DataFrame({
        "timestamp": df["timestamp"],
        "equity": bt["equity_curve"],
        "prediction": predictions,
    })
    eq_df.write_parquet(OUTPUT_DIR / "equity_curve.parquet")

    # Save trades
    trades_df = pl.DataFrame(trades_arr)
    trades_df.write_parquet(OUTPUT_DIR / "trades.parquet")

    # Save last model
    if results["models"]:
        results["models"][-1].save_model(str(OUTPUT_DIR / "model_last_fold.txt"))

    print(f"\n  Results saved to {OUTPUT_DIR}")
    print()
    print("=" * 70)
    print("DONE")
    print("=" * 70)


if __name__ == "__main__":
    main()
