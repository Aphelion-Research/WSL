"""M15 Scalp Strategy — LightGBM on 15-minute bars.

Builds M15 bars from Dukascopy ticks, computes M15-native features,
trains LightGBM walk-forward, backtests with prop-firm costs.

Scalp parameters:
- Target: 6-bar horizon (1.5h) with 1:1.5 R:R
- SL: 1.0 × M15_ATR (~1.75 pts)
- TP: 1.5 × M15_ATR (~2.6 pts)
- Hold max: 12 bars (3h)
- Session: London/NY only (7-20 UTC)
- Prop firm costs: 0.10 slip + $0.50 commission

Usage:
    python -m datasets.scalp_m15
"""
from __future__ import annotations

from pathlib import Path
import datetime

import numpy as np
import polars as pl
import lightgbm as lgb
from sklearn.metrics import roc_auc_score

ROOT = Path.home() / "Dominion"
TICK_DIR = ROOT / "dukascopy_ticks"
OUTPUT_DIR = ROOT / "datasets" / "scalp_m15_results"


# ─── DATA LOADING ─────────────────────────────────────────────────────────

def load_ticks_for_month(year: int, month: int) -> pl.DataFrame:
    fname = TICK_DIR / f"XAUUSD_ticks_{year}_{month:02d}.parquet"
    if not fname.exists():
        return pl.DataFrame()

    df = pl.read_parquet(fname)

    if month == 12:
        nxt = datetime.datetime(year + 1, 1, 1, tzinfo=datetime.timezone.utc)
    else:
        nxt = datetime.datetime(year, month + 1, 1, tzinfo=datetime.timezone.utc)
    start = datetime.datetime(year, month, 1, tzinfo=datetime.timezone.utc)
    max_ms = int((nxt - start).total_seconds() * 1000)

    df = df.with_columns(pl.col("time").cast(pl.Int64).alias("_ms"))
    df = df.filter(pl.col("_ms") <= max_ms)
    df = df.with_columns(
        (pl.lit(start).cast(pl.Datetime("ms", "UTC"))
         + pl.col("_ms").cast(pl.Duration("ms"))).alias("timestamp")
    )
    return df.select(["timestamp", "bid", "ask", "mid", "bid_vol", "ask_vol"])


def build_m15_bars(start_ym: tuple, end_ym: tuple) -> pl.DataFrame:
    """Load ticks and resample to M15 bars."""
    frames = []
    y, m = start_ym
    while (y, m) <= end_ym:
        df = load_ticks_for_month(y, m)
        if len(df) > 0:
            frames.append(df)
        m += 1
        if m > 12:
            m = 1
            y += 1

    ticks = pl.concat(frames).sort("timestamp")
    print(f"  Total ticks: {len(ticks):,}")

    bars = (
        ticks
        .group_by_dynamic("timestamp", every="15m", closed="left", label="left")
        .agg([
            pl.col("mid").first().alias("open"),
            pl.col("mid").max().alias("high"),
            pl.col("mid").min().alias("low"),
            pl.col("mid").last().alias("close"),
            pl.col("mid").count().alias("tick_volume"),
            (pl.col("ask") - pl.col("bid")).mean().alias("spread"),
            (pl.col("bid_vol") + pl.col("ask_vol")).sum().alias("volume"),
        ])
        .sort("timestamp")
        .filter(pl.col("tick_volume") > 0)
    )
    return bars


# ─── FEATURES ──────────────────────────────────────────────────────────────

def compute_features(bars: pl.DataFrame) -> pl.DataFrame:
    """M15-native features — all stationary, point-in-time safe."""
    close = "close"
    exprs = []

    # Log returns
    for p in [1, 2, 4, 8, 16, 32]:
        exprs.append(
            (pl.col(close) / pl.col(close).shift(p)).log().alias(f"logret_{p}")
        )

    # Rolling z-scores (shift(1) for point-in-time)
    for w in [8, 16, 32, 64, 96]:
        rolled_mean = pl.col(close).shift(1).rolling_mean(w)
        rolled_std = pl.col(close).shift(1).rolling_std(w)
        exprs.append(
            ((pl.col(close) - rolled_mean) / (rolled_std + 1e-10))
            .clip(-5.0, 5.0)
            .alias(f"zscore_{w}")
        )

    # Realized volatility
    log_ret = (pl.col(close) / pl.col(close).shift(1)).log()
    for w in [8, 16, 32, 64]:
        exprs.append(
            (log_ret.rolling_std(w) * np.sqrt(96 * 252))  # 96 M15 bars/day
            .alias(f"rvol_{w}")
        )

    # RSI
    delta = pl.col(close) - pl.col(close).shift(1)
    gain = pl.when(delta > 0).then(delta).otherwise(0.0)
    loss = pl.when(delta < 0).then(-delta).otherwise(0.0)
    for period in [7, 14]:
        avg_g = gain.rolling_mean(period)
        avg_l = loss.rolling_mean(period)
        rs = avg_g / (avg_l + 1e-10)
        exprs.append(
            (pl.lit(100.0) - pl.lit(100.0) / (pl.lit(1.0) + rs)).alias(f"rsi_{period}")
        )

    # ATR pct
    tr = pl.max_horizontal(
        pl.col("high") - pl.col("low"),
        (pl.col("high") - pl.col(close).shift(1)).abs(),
        (pl.col("low") - pl.col(close).shift(1)).abs(),
    )
    for w in [7, 14]:
        exprs.append(
            (tr.rolling_mean(w) / pl.col(close)).alias(f"atr_pct_{w}")
        )

    # Spread ratio
    exprs.append(
        (pl.col("spread") / pl.col(close)).alias("spread_pct")
    )

    # Volume ratio
    exprs.append(
        (pl.col("tick_volume").cast(pl.Float64) /
         (pl.col("tick_volume").shift(1).cast(pl.Float64).rolling_mean(32) + 1e-10))
        .clip(0.0, 10.0)
        .alias("vol_ratio")
    )

    # MACD pct
    ema12 = pl.col(close).ewm_mean(span=12)
    ema26 = pl.col(close).ewm_mean(span=26)
    exprs.append(((ema12 - ema26) / pl.col(close)).alias("macd_pct"))

    # Bollinger band position
    for w in [16, 32]:
        sma = pl.col(close).shift(1).rolling_mean(w)
        std = pl.col(close).shift(1).rolling_std(w)
        exprs.append(
            ((pl.col(close) - sma) / (2.0 * std + 1e-10))
            .clip(-3.0, 3.0)
            .alias(f"bb_pos_{w}")
        )

    # Body ratio (directional conviction)
    exprs.append(
        ((pl.col(close) - pl.col("open")).abs() /
         (pl.col("high") - pl.col("low") + 1e-10))
        .clip(0.0, 1.0)
        .alias("body_ratio")
    )

    # Range position
    for w in [16, 48, 96]:
        exprs.append(
            ((pl.col(close) - pl.col("low").shift(1).rolling_min(w)) /
             (pl.col("high").shift(1).rolling_max(w) - pl.col("low").shift(1).rolling_min(w) + 1e-10))
            .clip(0.0, 1.0)
            .alias(f"range_pos_{w}")
        )

    # Session features (cyclical)
    ts = pl.col("timestamp")
    exprs.extend([
        (2.0 * np.pi * ts.dt.hour().cast(pl.Float64) / 24.0).sin().alias("hour_sin"),
        (2.0 * np.pi * ts.dt.hour().cast(pl.Float64) / 24.0).cos().alias("hour_cos"),
        (2.0 * np.pi * ts.dt.weekday().cast(pl.Float64) / 5.0).sin().alias("dow_sin"),
        (2.0 * np.pi * ts.dt.weekday().cast(pl.Float64) / 5.0).cos().alias("dow_cos"),
        ((ts.dt.hour() >= 8) & (ts.dt.hour() < 16)).cast(pl.Float32).alias("london"),
        ((ts.dt.hour() >= 13) & (ts.dt.hour() < 16)).cast(pl.Float32).alias("overlap"),
    ])

    # Sharpe rolling
    for w in [16, 32]:
        lr = (pl.col(close) / pl.col(close).shift(1)).log()
        exprs.append(
            (lr.rolling_mean(w) / (lr.rolling_std(w) + 1e-10) * np.sqrt(96 * 252))
            .clip(-10.0, 10.0)
            .alias(f"sharpe_{w}")
        )

    # Spread expansion
    exprs.append(
        (pl.col("spread") / (pl.col("spread").shift(1).rolling_median(32) + 1e-10))
        .clip(0.0, 10.0)
        .alias("spread_expansion")
    )

    bars = bars.with_columns(exprs)
    return bars


# ─── TARGETS ───────────────────────────────────────────────────────────────

def compute_targets(bars: pl.DataFrame, horizon: int = 6, sl_mult: float = 1.0, tp_mult: float = 1.5) -> pl.DataFrame:
    """Triple-barrier target for M15 scalp.

    horizon=6 bars = 1.5 hours
    SL = 1.0 × ATR14
    TP = 1.5 × ATR14
    """
    close = bars["close"].to_numpy()
    high = bars["high"].to_numpy()
    low = bars["low"].to_numpy()
    n = len(close)

    # ATR
    atr = np.zeros(n)
    for i in range(1, n):
        tr = max(high[i] - low[i], abs(high[i] - close[i-1]), abs(low[i] - close[i-1]))
        if i < 14:
            atr[i] = tr
        else:
            atr[i] = (atr[i-1] * 13 + tr) / 14

    # Triple barrier: direction agnostic (1=long wins, 0=short wins)
    target = np.full(n, np.nan, dtype=np.float32)

    for t in range(n - horizon):
        if atr[t] < 0.01 or close[t] == 0:
            continue
        if atr[t] / close[t] < 0.0003:
            continue

        sl_long = close[t] - sl_mult * atr[t]
        tp_long = close[t] + tp_mult * atr[t]
        sl_short = close[t] + sl_mult * atr[t]
        tp_short = close[t] - tp_mult * atr[t]

        long_result = None
        short_result = None

        for k in range(1, horizon + 1):
            if long_result is None:
                if low[t+k] <= sl_long:
                    long_result = 0
                elif high[t+k] >= tp_long:
                    long_result = 1
            if short_result is None:
                if high[t+k] >= sl_short:
                    short_result = 0
                elif low[t+k] <= tp_short:
                    short_result = 1

        if long_result == 1 and short_result != 1:
            target[t] = 1.0
        elif short_result == 1 and long_result != 1:
            target[t] = 0.0
        elif long_result == 1 and short_result == 1:
            target[t] = 1.0  # both hit → long wins (conservative)

    return bars.with_columns(pl.Series("target", target))


# ─── TRAINING ──────────────────────────────────────────────────────────────

def train_walk_forward(
    df: pl.DataFrame,
    feature_cols: list[str],
    n_splits: int = 6,
    train_years: float = 3.0,
    test_months: int = 6,
    purge_bars: int = 12,
) -> tuple[np.ndarray, list]:
    """Walk-forward LightGBM training."""
    timestamps = df["timestamp"].to_numpy()
    target = df["target"].to_numpy()
    X = df.select(feature_cols).to_numpy().astype(np.float32)
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)

    n = len(df)
    valid_mask = np.isfinite(target)
    predictions = np.full(n, np.nan, dtype=np.float64)

    first_test = timestamps[0] + np.timedelta64(int(train_years * 365), "D")
    fold_starts = []
    curr = first_test
    end = timestamps[-1]
    while curr < end - np.timedelta64(test_months * 30, "D"):
        fold_starts.append(curr)
        curr += np.timedelta64(test_months * 30, "D")

    if len(fold_starts) > n_splits:
        fold_starts = fold_starts[-n_splits:]

    folds_info = []
    print(f"  Walk-forward: {len(fold_starts)} folds, {len(feature_cols)} features")

    for fold_idx, test_start in enumerate(fold_starts):
        test_end = test_start + np.timedelta64(test_months * 30, "D")
        val_start = test_start - np.timedelta64(test_months * 30, "D")

        train_mask = (timestamps < val_start - np.timedelta64(purge_bars * 15, "m")) & valid_mask
        val_mask = ((timestamps >= val_start) &
                    (timestamps < test_start - np.timedelta64(purge_bars * 15, "m")) & valid_mask)
        test_mask = (timestamps >= test_start) & (timestamps < test_end)

        n_train = train_mask.sum()
        n_val = val_mask.sum()
        n_test = test_mask.sum()

        if n_train < 1000 or n_val < 200 or n_test < 200:
            continue

        # Balance
        y_tr = target[train_mask]
        spw = (len(y_tr) - y_tr.sum()) / (y_tr.sum() + 1e-10)

        dtrain = lgb.Dataset(X[train_mask], y_tr)
        dval = lgb.Dataset(X[val_mask], target[val_mask], reference=dtrain)

        params = {
            "objective": "binary",
            "metric": "auc",
            "boosting_type": "gbdt",
            "learning_rate": 0.03,
            "num_leaves": 31,
            "max_depth": 5,
            "min_child_samples": 100,
            "subsample": 0.7,
            "subsample_freq": 1,
            "colsample_bytree": 0.6,
            "reg_alpha": 1.0,
            "reg_lambda": 5.0,
            "min_gain_to_split": 0.05,
            "scale_pos_weight": spw,
            "verbosity": -1,
            "seed": 42 + fold_idx,
        }

        model = lgb.train(
            params, dtrain, num_boost_round=1500,
            valid_sets=[dval],
            callbacks=[lgb.early_stopping(80, verbose=False), lgb.log_evaluation(0)],
        )

        preds = model.predict(X[test_mask])
        predictions[test_mask] = preds

        # Eval
        test_valid = test_mask & valid_mask
        if test_valid.sum() > 50:
            auc = roc_auc_score(target[test_valid], predictions[test_valid])
        else:
            auc = 0.5

        folds_info.append({
            "fold": fold_idx,
            "n_train": n_train, "n_test": n_test,
            "auc": auc, "trees": model.best_iteration,
            "period": str(test_start)[:10],
        })
        print(f"    Fold {fold_idx}: train={n_train:,} test={n_test:,} "
              f"AUC={auc:.4f} trees={model.best_iteration}")

    # Feature importance from last model
    if folds_info:
        imp = model.feature_importance(importance_type="gain")
        top_idx = np.argsort(imp)[::-1][:15]
        print(f"\n  Top-15 features:")
        for rank, idx in enumerate(top_idx):
            print(f"    {rank+1:2d}. {feature_cols[idx]:<25s} {imp[idx]:>8.1f}")

    return predictions, folds_info


# ─── BACKTEST ──────────────────────────────────────────────────────────────

def backtest_scalp(
    df: pl.DataFrame,
    predictions: np.ndarray,
    long_thresh: float = 0.6,
    short_thresh: float = 0.4,
    sl_mult: float = 1.0,
    tp_mult: float = 1.5,
    max_hold: int = 12,
    capital: float = 100_000.0,
    risk_pct: float = 1.0,
    slippage: float = 0.10,
    commission: float = 0.50,
    lot_size: float = 0.1,
    min_bars_between: int = 2,
) -> dict:
    """M15 scalp backtest — prop firm costs."""
    close = df["close"].to_numpy()
    open_p = df["open"].to_numpy()
    high_p = df["high"].to_numpy()
    low_p = df["low"].to_numpy()
    timestamps = df["timestamp"].to_numpy()
    spread = df["spread"].to_numpy()

    n = len(close)
    money_per_pt = 1.0 * lot_size * 100

    # ATR
    atr = np.zeros(n)
    for i in range(1, n):
        tr = max(high_p[i] - low_p[i], abs(high_p[i] - close[i-1]), abs(low_p[i] - close[i-1]))
        if i < 14:
            atr[i] = tr
        else:
            atr[i] = (atr[i-1] * 13 + tr) / 14

    equity = capital
    equity_curve = np.zeros(n)
    trades = []
    position = None
    last_exit = -min_bars_between

    for i in range(1, n):
        equity_curve[i] = equity

        # Manage position
        if position is not None:
            d = position["direction"]
            bars_held = i - position["entry_bar"]
            exit_price = None

            if d == 1:
                if low_p[i] <= position["sl"]:
                    exit_price = position["sl"]
                    reason = "sl"
                elif high_p[i] >= position["tp"]:
                    exit_price = position["tp"]
                    reason = "tp"
                elif bars_held >= max_hold:
                    exit_price = close[i]
                    reason = "time"
            else:
                if high_p[i] >= position["sl"]:
                    exit_price = position["sl"]
                    reason = "sl"
                elif low_p[i] <= position["tp"]:
                    exit_price = position["tp"]
                    reason = "tp"
                elif bars_held >= max_hold:
                    exit_price = close[i]
                    reason = "time"

            # SL wins on ambiguous bar
            if d == 1 and low_p[i] <= position["sl"] and high_p[i] >= position["tp"]:
                exit_price = position["sl"]
                reason = "sl"
            elif d == -1 and high_p[i] >= position["sl"] and low_p[i] <= position["tp"]:
                exit_price = position["sl"]
                reason = "sl"

            if exit_price is not None:
                if d == 1:
                    pnl_pts = exit_price - position["entry_price"] - slippage / 2
                else:
                    pnl_pts = position["entry_price"] - exit_price - slippage / 2

                pnl_money = pnl_pts * money_per_pt * position["size"] - commission * position["size"]
                equity += pnl_money

                trades.append({
                    "entry_bar": position["entry_bar"],
                    "exit_bar": i,
                    "direction": d,
                    "pnl_pts": pnl_pts,
                    "pnl_money": pnl_money,
                    "bars_held": bars_held,
                    "reason": reason,
                    "entry_time": str(timestamps[position["entry_bar"]]),
                    "exit_time": str(timestamps[i]),
                })
                position = None
                last_exit = i

        # New signal
        if position is None and i < n - max_hold:
            if i - last_exit < min_bars_between:
                continue

            pred = predictions[i - 1]
            if np.isnan(pred):
                continue

            # Session filter: 7-19 UTC
            bar_hour = int((timestamps[i] - timestamps[i].astype("datetime64[D]")).astype("timedelta64[h]").astype(int))
            if bar_hour < 7 or bar_hour >= 19:
                continue

            # ATR filter
            if atr[i] < 0.5 or atr[i] / close[i] < 0.0003:
                continue

            # Spread filter: spread < 40% of ATR
            if spread[i] / (atr[i] + 1e-10) > 0.4:
                continue

            # Risk sizing
            risk_amount = equity * risk_pct / 100.0
            sl_dist = sl_mult * atr[i]
            lots = np.clip(risk_amount / (sl_dist * money_per_pt), 0.01, 10.0)

            if pred > long_thresh:
                entry_price = open_p[i] + slippage / 2
                position = {
                    "direction": 1,
                    "entry_price": entry_price,
                    "sl": entry_price - sl_mult * atr[i],
                    "tp": entry_price + tp_mult * atr[i],
                    "entry_bar": i,
                    "size": lots,
                }
            elif pred < short_thresh:
                entry_price = open_p[i] - slippage / 2
                position = {
                    "direction": -1,
                    "entry_price": entry_price,
                    "sl": entry_price + sl_mult * atr[i],
                    "tp": entry_price - tp_mult * atr[i],
                    "entry_bar": i,
                    "size": lots,
                }

    equity_curve[-1] = equity

    if not trades:
        return {"error": "No trades"}

    pnls = np.array([t["pnl_money"] for t in trades])
    directions = np.array([t["direction"] for t in trades])
    reasons = [t["reason"] for t in trades]

    winners = pnls > 0
    n_trades = len(trades)
    win_rate = winners.mean()
    total_pnl = pnls.sum()

    avg_win = pnls[winners].mean() if winners.sum() > 0 else 0
    avg_loss = pnls[~winners].mean() if (~winners).sum() > 0 else 0
    pf = abs(pnls[winners].sum() / (pnls[~winners].sum() + 1e-10))

    trade_years = n / (96 * 252)  # 96 M15 bars/day
    tpy = n_trades / trade_years if trade_years > 0 else 1
    sharpe = (pnls.mean() / (pnls.std() + 1e-10)) * np.sqrt(tpy)

    cum_pnl = np.cumsum(pnls)
    running_max = np.maximum.accumulate(cum_pnl)
    max_dd = (cum_pnl - running_max).min()
    max_dd_pct = max_dd / capital * 100

    annual_ret = (total_pnl / capital) / trade_years * 100 if trade_years > 0 else 0
    calmar = annual_ret / abs(max_dd_pct) if max_dd_pct != 0 else 0

    long_mask = directions == 1
    short_mask = directions == -1

    return {
        "n_trades": n_trades,
        "n_long": int(long_mask.sum()),
        "n_short": int(short_mask.sum()),
        "win_rate": win_rate,
        "long_wr": (pnls[long_mask] > 0).mean() if long_mask.sum() > 0 else 0,
        "short_wr": (pnls[short_mask] > 0).mean() if short_mask.sum() > 0 else 0,
        "total_pnl": total_pnl,
        "avg_pnl": pnls.mean(),
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "rr": abs(avg_win / avg_loss) if avg_loss != 0 else 0,
        "profit_factor": pf,
        "sharpe": sharpe,
        "max_dd_pct": max_dd_pct,
        "annual_ret_pct": annual_ret,
        "calmar": calmar,
        "trades_per_year": tpy,
        "equity_curve": equity_curve,
        "trades": trades,
        "exits": {r: reasons.count(r) for r in set(reasons)},
    }


# ─── MAIN ─────────────────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print("DOMINION M15 SCALPER — LightGBM Walk-Forward + Prop Firm Costs")
    print("=" * 70)
    print()

    # Build M15 bars from ticks
    print("Building M15 bars from Dukascopy ticks (2010-2026)...")
    bars = build_m15_bars((2010, 1), (2026, 5))
    print(f"  M15 bars: {len(bars):,}")

    # Compute features
    print("Computing features...")
    bars = compute_features(bars)

    # Compute targets
    print("Computing targets (6-bar horizon, 1:1.5 R:R)...")
    bars = compute_targets(bars, horizon=6, sl_mult=1.0, tp_mult=1.5)

    # Drop warmup
    bars = bars.slice(200)

    # Stats
    target = bars["target"].to_numpy()
    valid = np.isfinite(target)
    print(f"  Valid labels: {valid.sum():,} ({valid.mean()*100:.1f}%)")
    print(f"  Class balance: {target[valid].mean()*100:.1f}% long")
    print()

    # Feature columns
    exclude = {"timestamp", "open", "high", "low", "close", "tick_volume",
               "spread", "volume", "target"}
    feature_cols = [c for c in bars.columns if c not in exclude]
    print(f"  Features: {len(feature_cols)}")

    # Train
    print()
    print("─" * 70)
    print("WALK-FORWARD TRAINING")
    print("─" * 70)
    predictions, folds = train_walk_forward(bars, feature_cols, n_splits=8)

    if folds:
        mean_auc = np.mean([f["auc"] for f in folds])
        print(f"\n  Mean OOS AUC: {mean_auc:.4f}")

    # Backtest sweep
    print()
    print("─" * 70)
    print("BACKTEST (Prop Firm Costs)")
    print("─" * 70)

    # Determine thresholds from prediction distribution
    valid_preds = predictions[~np.isnan(predictions)]
    print(f"  OOS predictions: {len(valid_preds):,}")
    print(f"  Pred distribution: mean={valid_preds.mean():.4f} std={valid_preds.std():.4f}")

    # Sweep thresholds
    print(f"\n  {'Long/Short':<15} {'N':<7} {'WR%':<7} {'RR':<5} {'PF':<6} {'Sharpe':<8} {'DD%':<7} {'Ann%':<8} {'$/yr'}")
    print("  " + "-" * 80)

    best = None
    best_sharpe = -999

    for lt, st in [(0.55, 0.45), (0.6, 0.4), (0.65, 0.35), (0.7, 0.3), (0.75, 0.25)]:
        bt = backtest_scalp(bars, predictions, long_thresh=lt, short_thresh=st)
        if "error" in bt:
            continue
        label = f">{lt:.2f}/<{st:.2f}"
        trade_years = len(bars) / (96 * 252)
        pnl_yr = bt["total_pnl"] / trade_years
        print(f"  {label:<15} {bt['n_trades']:<7} {bt['win_rate']*100:<7.1f} "
              f"{bt['rr']:<5.2f} {bt['profit_factor']:<6.2f} {bt['sharpe']:<8.2f} "
              f"{bt['max_dd_pct']:<7.1f} {bt['annual_ret_pct']:<8.1f} ${pnl_yr:>8,.0f}")

        if bt["sharpe"] > best_sharpe and bt["n_trades"] > 100:
            best_sharpe = bt["sharpe"]
            best = (label, bt)

    if best is None:
        print("\n  No viable threshold.")
        return

    label, bt = best
    print(f"\n  BEST: {label}")
    print(f"  ═══════════════════════════════════════════")
    print(f"  Trades:     {bt['n_trades']} ({bt['trades_per_year']:.0f}/year)")
    print(f"  Long/Short: {bt['n_long']}/{bt['n_short']}")
    print(f"  Win Rate:   {bt['win_rate']*100:.1f}% (L={bt['long_wr']*100:.1f}% S={bt['short_wr']*100:.1f}%)")
    print(f"  R:R:        {bt['rr']:.2f}")
    print(f"  PF:         {bt['profit_factor']:.2f}")
    print(f"  Sharpe:     {bt['sharpe']:.2f}")
    print(f"  Max DD:     {bt['max_dd_pct']:.1f}%")
    print(f"  Annual Ret: {bt['annual_ret_pct']:.1f}%")
    print(f"  Calmar:     {bt['calmar']:.2f}")
    print(f"  Total PnL:  ${bt['total_pnl']:,.0f}")
    print(f"  Exits:      {bt['exits']}")

    # Yearly
    print(f"\n  Yearly PnL:")
    yearly = {}
    for t in bt["trades"]:
        yk = t["exit_time"][:4]
        yearly[yk] = yearly.get(yk, 0) + t["pnl_money"]
    pos_years = sum(1 for v in yearly.values() if v > 0)
    print(f"  Profitable: {pos_years}/{len(yearly)}")
    for y in sorted(yearly.keys()):
        print(f"    {y}: {'+'if yearly[y]>0 else ''}{yearly[y]:>10,.0f}")

    # Save
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    eq_df = pl.DataFrame({"timestamp": bars["timestamp"], "equity": bt["equity_curve"]})
    eq_df.write_parquet(OUTPUT_DIR / "equity_curve.parquet")
    pl.DataFrame(bt["trades"]).write_parquet(OUTPUT_DIR / "trades.parquet")
    print(f"\n  Saved to {OUTPUT_DIR}")
    print("=" * 70)


if __name__ == "__main__":
    main()
