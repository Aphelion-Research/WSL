"""Strategy V2: Rule-based edges + ML confidence scoring.

Thesis: Gold has persistent regimes. Instead of predicting bar-by-bar direction,
identify regime-aligned setups and use ML only for confidence/timing.

Edges exploited:
1. H4 trend-following (gold trends for days/weeks)
2. M5 pullback entry (enter WITH the trend on mean-reversion)
3. London session momentum (7-10 UTC breakout)
4. Volatility expansion (breakout trades during vol expansion)

Architecture:
- Rule engine generates candidate signals
- LightGBM scores signal quality (not direction)
- Backtest with realistic costs

Usage:
    python -m datasets.strategy_v2
"""
from __future__ import annotations

import datetime
from pathlib import Path

import numpy as np
import polars as pl
import lightgbm as lgb
from sklearn.metrics import roc_auc_score

ROOT = Path.home() / "Dominion"
DATASET_PATH = ROOT / "datasets" / "mtf_xauusd_v1.parquet"
OUTPUT_DIR = ROOT / "datasets" / "strategy_v2_results"


# ─── SIGNAL GENERATION (RULE-BASED) ───────────────────────────────────────

def generate_signals(df: pl.DataFrame) -> pl.DataFrame:
    """Generate candidate signals using multi-TF regime rules.

    Signal = +1 (long candidate), -1 (short candidate), 0 (no signal)

    Rules:
    - H4 trend: defined by H4 MACD pct sign + H4 logret_10 direction
    - M5 pullback: RSI < 35 in uptrend, RSI > 65 in downtrend
    - Session: must be in London/NY session (7-20 UTC)
    - Spread: must be below 2x median
    """
    return df.with_columns([
        # H4 trend direction
        pl.when(
            (pl.col("h4_macd_pct") > 0) & (pl.col("h4_logret_10") > 0)
        ).then(pl.lit(1))
        .when(
            (pl.col("h4_macd_pct") < 0) & (pl.col("h4_logret_10") < 0)
        ).then(pl.lit(-1))
        .otherwise(pl.lit(0))
        .alias("h4_trend"),

        # M5 pullback condition
        pl.when(pl.col("m5_rsi_14") < 35).then(pl.lit(1))   # oversold → long candidate
        .when(pl.col("m5_rsi_14") > 65).then(pl.lit(-1))    # overbought → short candidate
        .otherwise(pl.lit(0))
        .alias("m5_pullback"),

        # Session filter
        pl.col("timestamp").dt.hour().alias("_hour"),

        # Spread filter (below 2x rolling median)
        (pl.col("spread") < pl.col("spread").shift(1).rolling_median(100) * 2.0)
        .cast(pl.Int8).alias("spread_ok"),
    ]).with_columns([
        # Session active
        ((pl.col("_hour") >= 7) & (pl.col("_hour") < 20)).cast(pl.Int8).alias("session_ok"),
    ]).with_columns([
        # Final signal: trend-aligned pullback during good session + spread
        pl.when(
            (pl.col("h4_trend") == 1) &
            (pl.col("m5_pullback") == 1) &
            (pl.col("session_ok") == 1) &
            (pl.col("spread_ok") == 1)
        ).then(pl.lit(1))
        .when(
            (pl.col("h4_trend") == -1) &
            (pl.col("m5_pullback") == -1) &
            (pl.col("session_ok") == 1) &
            (pl.col("spread_ok") == 1)
        ).then(pl.lit(-1))
        .otherwise(pl.lit(0))
        .alias("signal"),
    ]).drop(["_hour"])


def label_signal_outcomes(df: pl.DataFrame, horizon: int = 20, rr_target: float = 2.0) -> pl.DataFrame:
    """Label each signal: did the trade win (TP hit before SL)?

    Uses ATR-based TP/SL with the SAME logic as backtest.
    This is the ML target: predict which signals will succeed.
    """
    close = df["close"].to_numpy()
    high = df["high"].to_numpy()
    low = df["low"].to_numpy()
    signal = df["signal"].to_numpy()
    atr_pct = df["m5_atr_pct_14"].to_numpy()

    n = len(close)
    outcome = np.full(n, np.nan, dtype=np.float32)

    sl_mult = 1.5
    tp_mult = sl_mult * rr_target  # 3.0

    for t in range(n - horizon):
        if signal[t] == 0:
            continue
        if not np.isfinite(atr_pct[t]) or atr_pct[t] < 0.0003:
            continue

        atr_abs = atr_pct[t] * close[t]
        entry = close[t]  # approximate; actual entry is open[t+1]

        if signal[t] == 1:  # Long
            sl = entry - sl_mult * atr_abs
            tp = entry + tp_mult * atr_abs
            for k in range(1, horizon + 1):
                if low[t + k] <= sl:
                    outcome[t] = 0.0
                    break
                if high[t + k] >= tp:
                    outcome[t] = 1.0
                    break
        elif signal[t] == -1:  # Short
            sl = entry + sl_mult * atr_abs
            tp = entry - tp_mult * atr_abs
            for k in range(1, horizon + 1):
                if high[t + k] >= sl:
                    outcome[t] = 0.0
                    break
                if low[t + k] <= tp:
                    outcome[t] = 1.0
                    break

    return df.with_columns(pl.Series("signal_outcome", outcome))


# ─── ENHANCED FEATURES FOR SIGNAL QUALITY ──────────────────────────────────

def build_signal_features(df: pl.DataFrame) -> pl.DataFrame:
    """Features for predicting signal QUALITY (not direction — direction is from rules)."""
    return df.with_columns([
        # Trend strength (H4)
        pl.col("h4_logret_10").abs().alias("sf_trend_strength"),
        # Pullback depth (how oversold/overbought on M5)
        (pl.col("m5_rsi_14") - 50.0).abs().alias("sf_pullback_depth"),
        # Multi-TF alignment score
        (pl.col("h1_logret_5").sign() == pl.col("h4_logret_5").sign())
        .cast(pl.Float32).alias("sf_h1h4_aligned"),
        # Volatility regime
        pl.col("m5_rvol_20").alias("sf_vol_20"),
        pl.col("m5_rvol_50").alias("sf_vol_50"),
        # Vol compression (low vol → breakout potential)
        (pl.col("m5_rvol_5") / (pl.col("m5_rvol_50") + 1e-10)).alias("sf_vol_compression"),
        # Spread quality
        (pl.col("spread") / (pl.col("m5_atr_pct_14") * pl.col("close") + 1e-10))
        .clip(0.0, 5.0).alias("sf_spread_cost_ratio"),
        # Time features
        (2.0 * np.pi * pl.col("timestamp").dt.hour().cast(pl.Float64) / 24.0).sin().alias("sf_hour_sin"),
        (2.0 * np.pi * pl.col("timestamp").dt.hour().cast(pl.Float64) / 24.0).cos().alias("sf_hour_cos"),
        (2.0 * np.pi * pl.col("timestamp").dt.weekday().cast(pl.Float64) / 5.0).sin().alias("sf_dow_sin"),
        # Volume confirmation
        (pl.col("tick_volume").cast(pl.Float64) /
         (pl.col("tick_volume").shift(1).cast(pl.Float64).rolling_mean(20) + 1e-10))
        .clip(0.0, 10.0).alias("sf_vol_confirm"),
        # Range position (where in recent range)
        ((pl.col("close") - pl.col("low").shift(1).rolling_min(48)) /
         (pl.col("high").shift(1).rolling_max(48) - pl.col("low").shift(1).rolling_min(48) + 1e-10))
        .clip(0.0, 1.0).alias("sf_range_pos"),
        # Momentum acceleration
        (pl.col("m5_logret_1") - pl.col("m5_logret_5") / 5.0).alias("sf_momentum_accel"),
        # Higher TF support (H1 BB position)
        pl.col("h1_bb_pos_20").alias("sf_h1_bb"),
        # Consecutive same-direction bars
        pl.col("m5_logret_1").sign().alias("_bar_dir"),
    ]).with_columns([
        # Count consecutive bars in signal direction
        pl.col("_bar_dir")
        .rolling_sum(5)
        .abs()
        .alias("sf_consecutive_dir"),
    ]).drop(["_bar_dir"])


# ─── WALK-FORWARD SIGNAL SCORING ──────────────────────────────────────────

def train_signal_scorer(
    df: pl.DataFrame,
    n_splits: int = 6,
    train_years: int = 3,
    test_months: int = 6,
) -> np.ndarray:
    """Train ML model to predict which signals will succeed."""
    sf_cols = [c for c in df.columns if c.startswith("sf_")]
    timestamps = df["timestamp"].to_numpy()
    signal = df["signal"].to_numpy()
    outcome = df["signal_outcome"].to_numpy()

    # Only train on rows with valid signals
    has_signal = signal != 0
    has_outcome = np.isfinite(outcome)
    trainable = has_signal & has_outcome

    X_all = df.select(sf_cols).to_numpy().astype(np.float32)
    X_all = np.nan_to_num(X_all, nan=0.0, posinf=0.0, neginf=0.0)

    n = len(df)
    scores = np.full(n, np.nan, dtype=np.float64)

    # Walk-forward
    first_test_start = timestamps[0] + np.timedelta64(train_years * 365, "D")
    fold_starts = []
    current = first_test_start
    end_dt = timestamps[-1]
    while current < end_dt - np.timedelta64(test_months * 30, "D"):
        fold_starts.append(current)
        current += np.timedelta64(test_months * 30, "D")

    if len(fold_starts) > n_splits:
        fold_starts = fold_starts[-n_splits:]

    print(f"  Signal scorer: {len(fold_starts)} folds, {len(sf_cols)} features")
    print(f"  Total trainable signals: {trainable.sum():,}")

    purge = 24

    for fold_idx, test_start in enumerate(fold_starts):
        test_end = test_start + np.timedelta64(test_months * 30, "D")

        train_mask = (timestamps < test_start - np.timedelta64(purge * 5, "m")) & trainable
        test_mask = (timestamps >= test_start) & (timestamps < test_end) & has_signal

        n_train = train_mask.sum()
        n_test = test_mask.sum()

        if n_train < 500 or n_test < 50:
            continue

        # Class balance
        y_train = outcome[train_mask]
        n_pos = y_train.sum()
        n_neg = len(y_train) - n_pos
        spw = n_neg / n_pos if n_pos > 0 else 1.0

        dtrain = lgb.Dataset(X_all[train_mask], y_train)

        params = {
            "objective": "binary",
            "metric": "auc",
            "boosting_type": "gbdt",
            "learning_rate": 0.05,
            "num_leaves": 15,
            "max_depth": 4,
            "min_child_samples": 50,
            "subsample": 0.8,
            "colsample_bytree": 0.7,
            "reg_alpha": 1.0,
            "reg_lambda": 5.0,
            "scale_pos_weight": spw,
            "verbosity": -1,
            "seed": 42 + fold_idx,
        }

        model = lgb.train(params, dtrain, num_boost_round=200)

        # Score test signals
        preds = model.predict(X_all[test_mask])
        scores[test_mask] = preds

        # Evaluate
        test_outcome = outcome[test_mask]
        valid_eval = np.isfinite(test_outcome)
        if valid_eval.sum() > 50:
            auc = roc_auc_score(test_outcome[valid_eval], preds[valid_eval])
            print(f"    Fold {fold_idx}: n_train={n_train:,} n_test={n_test:,} AUC={auc:.4f}")
        else:
            print(f"    Fold {fold_idx}: n_train={n_train:,} n_test={n_test:,} (insufficient labels for eval)")

    return scores


# ─── BACKTEST ──────────────────────────────────────────────────────────────

def backtest_signals(
    df: pl.DataFrame,
    scores: np.ndarray,
    min_score: float = 0.5,
    spread_points: float = 0.50,
    slippage_points: float = 0.15,
    commission_per_lot: float = 1.0,
    lot_size: float = 0.1,
    atr_sl_mult: float = 1.5,
    atr_tp_mult: float = 3.0,
    max_holding_bars: int = 30,
    capital: float = 100_000.0,
    risk_per_trade_pct: float = 1.0,
    min_bars_between: int = 6,  # minimum 30 min between trades
) -> dict:
    """Backtest rule-based signals filtered by ML confidence score."""
    timestamps = df["timestamp"].to_numpy()
    open_prices = df["open"].to_numpy()
    high_prices = df["high"].to_numpy()
    low_prices = df["low"].to_numpy()
    close_prices = df["close"].to_numpy()
    signal = df["signal"].to_numpy()
    atr_pct = df["m5_atr_pct_14"].to_numpy()

    n = len(df)
    total_cost = spread_points + slippage_points
    pip_value = 1.0

    trades = []
    equity_curve = np.zeros(n)
    equity = capital
    position = None
    last_trade_bar = -min_bars_between

    for i in range(1, n):
        equity_curve[i] = equity

        # Manage existing position
        if position is not None:
            direction = position["direction"]
            bars_held = i - position["entry_bar"]

            exit_price = None
            exit_reason = None

            if direction == 1:
                if low_prices[i] <= position["sl"]:
                    exit_price = position["sl"]
                    exit_reason = "sl"
                elif high_prices[i] >= position["tp"]:
                    exit_price = position["tp"]
                    exit_reason = "tp"
            else:
                if high_prices[i] >= position["sl"]:
                    exit_price = position["sl"]
                    exit_reason = "sl"
                elif low_prices[i] <= position["tp"]:
                    exit_price = position["tp"]
                    exit_reason = "tp"

            if not exit_price and bars_held >= max_holding_bars:
                exit_price = open_prices[i]
                exit_reason = "timeout"

            # Conservative: SL wins on same-bar
            if exit_reason == "tp":
                if direction == 1 and low_prices[i] <= position["sl"]:
                    exit_price = position["sl"]
                    exit_reason = "sl"
                elif direction == -1 and high_prices[i] >= position["sl"]:
                    exit_price = position["sl"]
                    exit_reason = "sl"

            if exit_price is not None:
                if direction == 1:
                    pnl_points = exit_price - position["entry_price"] - total_cost / 2
                else:
                    pnl_points = position["entry_price"] - exit_price - total_cost / 2

                money_per_point = pip_value * lot_size * 100
                pnl_money = pnl_points * money_per_point * position["size"]
                pnl_money -= commission_per_lot * position["size"]

                equity += pnl_money
                trades.append({
                    "entry_bar": position["entry_bar"],
                    "exit_bar": i,
                    "direction": direction,
                    "entry_price": position["entry_price"],
                    "exit_price": exit_price,
                    "exit_reason": exit_reason,
                    "pnl_points": pnl_points,
                    "pnl_money": pnl_money,
                    "bars_held": bars_held,
                    "score": position["score"],
                    "entry_time": str(timestamps[position["entry_bar"]]),
                    "exit_time": str(timestamps[i]),
                })
                position = None
                last_trade_bar = i

        # New signal check
        if position is None and i < n - max_holding_bars:
            if i - last_trade_bar < min_bars_between:
                continue

            sig = signal[i - 1]
            if sig == 0:
                continue

            score = scores[i - 1]
            if np.isnan(score) or score < min_score:
                continue

            if not np.isfinite(atr_pct[i - 1]) or atr_pct[i - 1] < 0.0003:
                continue

            atr_abs = atr_pct[i - 1] * close_prices[i - 1]

            # Risk sizing
            risk_amount = equity * risk_per_trade_pct / 100.0
            sl_distance = atr_sl_mult * atr_abs
            if sl_distance < 0.01 or equity <= 0:
                continue
            money_per_point = pip_value * lot_size * 100
            lots = risk_amount / (sl_distance * money_per_point)
            lots = np.clip(lots, 0.01, 5.0)

            if sig == 1:
                entry_price = open_prices[i] + total_cost / 2
                position = {
                    "direction": 1,
                    "entry_price": entry_price,
                    "sl": entry_price - atr_sl_mult * atr_abs,
                    "tp": entry_price + atr_tp_mult * atr_abs,
                    "entry_bar": i,
                    "size": lots,
                    "score": score,
                }
            elif sig == -1:
                entry_price = open_prices[i] - total_cost / 2
                position = {
                    "direction": -1,
                    "entry_price": entry_price,
                    "sl": entry_price + atr_sl_mult * atr_abs,
                    "tp": entry_price - atr_tp_mult * atr_abs,
                    "entry_bar": i,
                    "size": lots,
                    "score": score,
                }

    equity_curve[-1] = equity

    if not trades:
        return {"error": "No trades"}

    # Metrics
    pnls = np.array([t["pnl_money"] for t in trades])
    directions = np.array([t["direction"] for t in trades])
    exit_reasons = [t["exit_reason"] for t in trades]

    n_trades = len(trades)
    winners = pnls > 0
    win_rate = winners.mean()

    total_pnl = pnls.sum()
    avg_win = pnls[winners].mean() if winners.sum() > 0 else 0
    avg_loss = pnls[~winners].mean() if (~winners).sum() > 0 else 0
    pf = abs(pnls[winners].sum() / (pnls[~winners].sum() + 1e-10)) if (~winners).sum() > 0 else 0

    avg_bars = np.mean([t["bars_held"] for t in trades])
    trades_per_year = (252 * 288) / avg_bars if avg_bars > 0 else 1
    sharpe = (pnls.mean() / (pnls.std() + 1e-10)) * np.sqrt(trades_per_year)

    cum_pnl = np.cumsum(pnls)
    running_max = np.maximum.accumulate(cum_pnl)
    max_dd = (cum_pnl - running_max).min()
    max_dd_pct = max_dd / capital * 100

    years = (timestamps[-1] - timestamps[0]).astype("timedelta64[D]").astype(int) / 365.25
    oos_years = sum(~np.isnan(scores)) / (288 * 252)  # approximate OOS years
    annual_return = total_pnl / capital / oos_years * 100 if oos_years > 0 else 0
    calmar = annual_return / abs(max_dd_pct) if max_dd_pct != 0 else 0

    # Long/short breakdown
    long_mask = directions == 1
    short_mask = directions == -1
    long_wr = (pnls[long_mask] > 0).mean() if long_mask.sum() > 0 else 0
    short_wr = (pnls[short_mask] > 0).mean() if short_mask.sum() > 0 else 0

    return {
        "n_trades": n_trades,
        "n_long": int(long_mask.sum()),
        "n_short": int(short_mask.sum()),
        "win_rate": win_rate,
        "long_win_rate": long_wr,
        "short_win_rate": short_wr,
        "total_pnl": total_pnl,
        "avg_pnl": pnls.mean(),
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "profit_factor": pf,
        "sharpe": sharpe,
        "max_drawdown": max_dd,
        "max_drawdown_pct": max_dd_pct,
        "annual_return_pct": annual_return,
        "calmar": calmar,
        "avg_bars_held": avg_bars,
        "exit_reasons": {
            "tp": exit_reasons.count("tp"),
            "sl": exit_reasons.count("sl"),
            "timeout": exit_reasons.count("timeout"),
        },
        "equity_curve": equity_curve,
        "trades": trades,
    }


# ─── MAIN ─────────────────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print("DOMINION STRATEGY V2 — Rule-Based Signals + ML Confidence Scoring")
    print("=" * 70)
    print()

    # Load
    print("Loading dataset...")
    df = pl.read_parquet(DATASET_PATH)
    print(f"  Shape: {df.shape}")

    # Generate signals
    print("Generating rule-based signals...")
    df = generate_signals(df)
    signal = df["signal"].to_numpy()
    n_long_sig = (signal == 1).sum()
    n_short_sig = (signal == -1).sum()
    print(f"  Long signals: {n_long_sig:,}")
    print(f"  Short signals: {n_short_sig:,}")
    print(f"  Signal rate: {(n_long_sig + n_short_sig) / len(df) * 100:.1f}%")

    # Label outcomes
    print("Labeling signal outcomes...")
    df = label_signal_outcomes(df, horizon=30, rr_target=2.0)
    outcomes = df["signal_outcome"].to_numpy()
    valid_outcomes = outcomes[np.isfinite(outcomes)]
    print(f"  Labeled signals: {len(valid_outcomes):,}")
    print(f"  Win rate (unfiltered): {valid_outcomes.mean()*100:.1f}%")

    # Build signal quality features
    print("Building signal quality features...")
    df = build_signal_features(df)

    # Train signal scorer
    print()
    print("─" * 70)
    print("TRAINING SIGNAL QUALITY SCORER")
    print("─" * 70)
    scores = train_signal_scorer(df, n_splits=8, train_years=3, test_months=6)

    valid_scores = scores[~np.isnan(scores)]
    print(f"\n  OOS scores available: {len(valid_scores):,}")
    print(f"  Score distribution: mean={valid_scores.mean():.4f} std={valid_scores.std():.4f}")
    print(f"  Percentiles: 25%={np.percentile(valid_scores, 25):.4f} "
          f"50%={np.percentile(valid_scores, 50):.4f} "
          f"75%={np.percentile(valid_scores, 75):.4f}")

    # Backtest at multiple confidence thresholds
    print()
    print("─" * 70)
    print("BACKTEST (Out-of-Sample)")
    print("─" * 70)

    # Try multiple thresholds
    thresholds = [0.3, 0.4, 0.5, 0.55, 0.6, 0.65]
    print(f"\n  {'Thresh':<8} {'Trades':<8} {'WR%':<7} {'PF':<7} {'Sharpe':<8} {'MaxDD%':<8} {'PnL$':<10}")
    print("  " + "-" * 60)

    best_sharpe = -999
    best_thresh = 0.5
    best_bt = None

    for thresh in thresholds:
        bt = backtest_signals(df, scores, min_score=thresh)
        if "error" in bt:
            print(f"  {thresh:<8.2f} {'No trades'}")
            continue

        print(f"  {thresh:<8.2f} {bt['n_trades']:<8} {bt['win_rate']*100:<7.1f} "
              f"{bt['profit_factor']:<7.2f} {bt['sharpe']:<8.2f} "
              f"{bt['max_drawdown_pct']:<8.1f} ${bt['total_pnl']:<10,.0f}")

        if bt["sharpe"] > best_sharpe and bt["n_trades"] > 50:
            best_sharpe = bt["sharpe"]
            best_thresh = thresh
            best_bt = bt

    if best_bt is None:
        print("\n  No viable threshold found.")
        return

    # Detailed results for best threshold
    bt = best_bt
    print(f"\n  Best threshold: {best_thresh} (Sharpe={best_sharpe:.2f})")
    print()
    print(f"  {'─'*50}")
    print(f"  {'DETAILED RESULTS':^50}")
    print(f"  {'─'*50}")
    print(f"  {'Trades':<25} {bt['n_trades']}")
    print(f"  {'Long / Short':<25} {bt['n_long']} / {bt['n_short']}")
    print(f"  {'Win Rate (all)':<25} {bt['win_rate']*100:.1f}%")
    print(f"  {'Win Rate (long)':<25} {bt['long_win_rate']*100:.1f}%")
    print(f"  {'Win Rate (short)':<25} {bt['short_win_rate']*100:.1f}%")
    print(f"  {'Profit Factor':<25} {bt['profit_factor']:.2f}")
    print(f"  {'Total PnL':<25} ${bt['total_pnl']:,.0f}")
    print(f"  {'Avg PnL/Trade':<25} ${bt['avg_pnl']:.2f}")
    print(f"  {'Avg Win':<25} ${bt['avg_win']:.2f}")
    print(f"  {'Avg Loss':<25} ${bt['avg_loss']:.2f}")
    print(f"  {'Sharpe':<25} {bt['sharpe']:.2f}")
    print(f"  {'Max Drawdown':<25} ${bt['max_drawdown']:,.0f} ({bt['max_drawdown_pct']:.1f}%)")
    print(f"  {'Annual Return':<25} {bt['annual_return_pct']:.1f}%")
    print(f"  {'Calmar':<25} {bt['calmar']:.2f}")
    print(f"  {'Avg Bars Held':<25} {bt['avg_bars_held']:.1f}")
    print(f"  {'Exit: TP/SL/Timeout':<25} {bt['exit_reasons']['tp']}/{bt['exit_reasons']['sl']}/{bt['exit_reasons']['timeout']}")

    # Monthly PnL
    print(f"\n  Monthly PnL (last 24 months):")
    monthly_pnl = {}
    for t in bt["trades"]:
        mk = t["exit_time"][:7]
        monthly_pnl[mk] = monthly_pnl.get(mk, 0) + t["pnl_money"]

    months_sorted = sorted(monthly_pnl.keys())[-24:]
    pos_months = sum(1 for m in months_sorted if monthly_pnl[m] > 0)
    print(f"  Positive months: {pos_months}/{len(months_sorted)}")
    for m in months_sorted:
        v = monthly_pnl[m]
        bar_len = max(1, int(abs(v) / 200))
        bar_char = "▓" if v > 0 else "░"
        sign = "+" if v > 0 else "-"
        print(f"    {m}: {sign}${abs(v):>8,.0f} {bar_char * min(bar_len, 30)}")

    # Save
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    eq_df = pl.DataFrame({
        "timestamp": df["timestamp"],
        "equity": bt["equity_curve"],
    })
    eq_df.write_parquet(OUTPUT_DIR / "equity_curve.parquet")
    pl.DataFrame(bt["trades"]).write_parquet(OUTPUT_DIR / "trades.parquet")

    print(f"\n  Results saved to {OUTPUT_DIR}")
    print("=" * 70)


if __name__ == "__main__":
    main()
