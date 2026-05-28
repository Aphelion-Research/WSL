"""Strategy FINAL: H4-scale regime + M5 precision entry + H4 exits.

KEY INSIGHT: M5 ATR ≈ 1-4 pts. Cost ≈ 0.65 pts = 17-65% of ATR.
Any strategy with M5-scale stops is DOA after costs.

FIX: Use H4 ATR (12-25 pts) for stops/targets. Cost becomes 3-5%.
M5 is used ONLY for entry timing (pullback to EMA within H4 trend).

Architecture:
1. H4 regime: EMA crossover on H4-smoothed price (bullish/bearish)
2. H4 ATR for stops/targets: SL=1.5*H4_ATR, TP=2*H4_ATR
3. M5 entry: Wait for pullback to M5 EMA-20 in trend direction
4. Hold for H4+ duration (12-96 bars = 1-8 hours)

This effectively trades daily/multi-day gold swings but uses M5 granularity
to get precise entries and exits.

Usage:
    python -m datasets.strategy_final
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import polars as pl

ROOT = Path.home() / "Dominion"
DATASET_PATH = ROOT / "datasets" / "mtf_xauusd_v1.parquet"
OUTPUT_DIR = ROOT / "datasets" / "strategy_final_results"


def compute_h4_atr(close: np.ndarray, high: np.ndarray, low: np.ndarray, period: int = 14) -> np.ndarray:
    """Compute ATR at H4 scale (using 48-bar rolling on M5)."""
    n = len(close)
    h4_period = period * 48  # 14 H4 bars = 672 M5 bars

    # True range on M5
    tr = np.zeros(n)
    for i in range(1, n):
        tr[i] = max(high[i] - low[i], abs(high[i] - close[i - 1]), abs(low[i] - close[i - 1]))
    tr[0] = high[0] - low[0]

    # H4-scale ATR: rolling sum of TR over 48 bars (one H4 bar worth of TR)
    # Then smooth with EMA
    h4_tr = np.zeros(n)
    for i in range(48, n):
        h4_tr[i] = tr[i - 47:i + 1].sum()  # total range in last H4 bar

    # EMA of H4_TR
    atr = np.zeros(n)
    alpha = 2.0 / (period + 1)
    warmup = period * 48
    if n > warmup:
        atr[warmup] = h4_tr[48:warmup + 1].mean()
        for i in range(warmup + 1, n):
            atr[i] = alpha * h4_tr[i] + (1 - alpha) * atr[i - 1]

    return atr


def run_strategy(
    df: pl.DataFrame,
    # Regime (H4 EMA crossover)
    fast_ema_periods: int = 5,  # in H4 bars
    slow_ema_periods: int = 20,  # in H4 bars
    # Entry (M5 pullback)
    pullback_ema: int = 20,  # M5 EMA for pullback detection
    entry_zscore: float = -0.5,  # mild pullback (not extreme)
    max_wait_bars: int = 48,  # wait up to 4h for pullback
    # Exits (H4-scale)
    sl_mult: float = 0.5,  # SL as fraction of H4 ATR
    tp_mult: float = 1.0,  # TP as fraction of H4 ATR
    trailing_at: float = 0.5,  # activate trailing after 0.5*H4_ATR profit
    trailing_dist: float = 0.3,  # trail at 0.3*H4_ATR from high
    max_hold: int = 288,  # max 24h hold
    # Filters
    min_h4_atr: float = 5.0,  # minimum H4 ATR in points
    max_spread_pct: float = 0.05,  # spread < 5% of H4 ATR
    # Risk
    capital: float = 100_000.0,
    risk_pct: float = 1.0,
    # Costs
    spread_pts: float = 0.50,
    slippage_pts: float = 0.15,
    commission: float = 1.0,
    lot_size: float = 0.1,
) -> dict:
    """Execute H4-scale swing strategy with M5 precision entries."""
    close = df["close"].to_numpy()
    open_p = df["open"].to_numpy()
    high_p = df["high"].to_numpy()
    low_p = df["low"].to_numpy()
    timestamps = df["timestamp"].to_numpy()
    spread = df["spread"].to_numpy()

    n = len(close)
    total_cost = spread_pts + slippage_pts
    money_per_pt = 1.0 * lot_size * 100

    # H4-scale EMAs
    fast_span = fast_ema_periods * 48
    slow_span = slow_ema_periods * 48
    alpha_f = 2.0 / (fast_span + 1)
    alpha_s = 2.0 / (slow_span + 1)

    ema_fast = np.zeros(n)
    ema_slow = np.zeros(n)
    ema_fast[0] = close[0]
    ema_slow[0] = close[0]
    for i in range(1, n):
        ema_fast[i] = alpha_f * close[i] + (1 - alpha_f) * ema_fast[i - 1]
        ema_slow[i] = alpha_s * close[i] + (1 - alpha_s) * ema_slow[i - 1]

    # M5 EMA for pullback
    ema_m5 = np.zeros(n)
    alpha_m5 = 2.0 / (pullback_ema + 1)
    ema_m5[0] = close[0]
    for i in range(1, n):
        ema_m5[i] = alpha_m5 * close[i] + (1 - alpha_m5) * ema_m5[i - 1]

    # H4-scale ATR
    h4_atr = compute_h4_atr(close, high_p, low_p, period=14)

    # Regime
    regime = np.where(ema_fast > ema_slow, 1, np.where(ema_fast < ema_slow, -1, 0))

    # Backtest
    equity = capital
    equity_curve = np.zeros(n)
    trades = []
    position = None
    pending = None
    last_exit_bar = -48
    warmup = slow_span + 100

    for i in range(warmup, n):
        equity_curve[i] = equity

        # ── MANAGE POSITION ──
        if position is not None:
            d = position["direction"]
            bars_held = i - position["entry_bar"]
            curr_h4_atr = h4_atr[i] if h4_atr[i] > 0 else position["h4_atr_at_entry"]

            if d == 1:
                # Update max favorable
                if high_p[i] > position["max_price"]:
                    position["max_price"] = high_p[i]

                # Trailing stop activation
                profit = position["max_price"] - position["entry_price"]
                if profit >= trailing_at * position["h4_atr_at_entry"]:
                    trail_sl = position["max_price"] - trailing_dist * curr_h4_atr
                    position["sl"] = max(position["sl"], trail_sl)

                # Check exits
                exit_price = None
                if low_p[i] <= position["sl"]:
                    exit_price = position["sl"]
                    reason = "sl"
                elif high_p[i] >= position["tp"]:
                    exit_price = position["tp"]
                    reason = "tp"
                elif bars_held >= max_hold:
                    exit_price = close[i]
                    reason = "time"
                # Regime reversal exit
                elif regime[i] == -1:
                    exit_price = close[i]
                    reason = "regime"

                # Ambiguous bar: SL wins
                if low_p[i] <= position["sl"] and high_p[i] >= position["tp"]:
                    exit_price = position["sl"]
                    reason = "sl"

            else:  # Short
                if low_p[i] < position["min_price"]:
                    position["min_price"] = low_p[i]

                profit = position["entry_price"] - position["min_price"]
                if profit >= trailing_at * position["h4_atr_at_entry"]:
                    trail_sl = position["min_price"] + trailing_dist * curr_h4_atr
                    position["sl"] = min(position["sl"], trail_sl)

                exit_price = None
                if high_p[i] >= position["sl"]:
                    exit_price = position["sl"]
                    reason = "sl"
                elif low_p[i] <= position["tp"]:
                    exit_price = position["tp"]
                    reason = "tp"
                elif bars_held >= max_hold:
                    exit_price = close[i]
                    reason = "time"
                elif regime[i] == 1:
                    exit_price = close[i]
                    reason = "regime"

                if high_p[i] >= position["sl"] and low_p[i] <= position["tp"]:
                    exit_price = position["sl"]
                    reason = "sl"

            if exit_price is not None:
                if d == 1:
                    pnl_pts = exit_price - position["entry_price"] - total_cost / 2
                else:
                    pnl_pts = position["entry_price"] - exit_price - total_cost / 2

                pnl_money = pnl_pts * money_per_pt * position["size"] - commission * position["size"]
                equity += pnl_money

                trades.append({
                    "entry_bar": position["entry_bar"],
                    "exit_bar": i,
                    "direction": d,
                    "entry_price": position["entry_price"],
                    "exit_price": exit_price,
                    "pnl_pts": pnl_pts,
                    "pnl_money": pnl_money,
                    "bars_held": bars_held,
                    "reason": reason,
                    "h4_atr": position["h4_atr_at_entry"],
                    "entry_time": str(timestamps[position["entry_bar"]]),
                    "exit_time": str(timestamps[i]),
                })
                position = None
                last_exit_bar = i

        # ── PENDING: WAIT FOR PULLBACK ──
        if pending is not None and position is None:
            wait = i - pending["signal_bar"]
            if wait > max_wait_bars:
                pending = None
            else:
                d = pending["direction"]
                # Pullback: price touches or crosses M5 EMA
                if d == 1 and low_p[i] <= ema_m5[i]:
                    # Enter long
                    if i + 1 < n:
                        entry_price = open_p[i + 1] + total_cost / 2
                        h4_atr_now = h4_atr[i]
                        sl = entry_price - sl_mult * h4_atr_now
                        tp = entry_price + tp_mult * h4_atr_now

                        risk_amt = equity * risk_pct / 100.0
                        sl_dist = entry_price - sl
                        if sl_dist > 0.1 and equity > 0:
                            lots = np.clip(risk_amt / (sl_dist * money_per_pt), 0.01, 10.0)
                            position = {
                                "direction": 1,
                                "entry_price": entry_price,
                                "sl": sl,
                                "tp": tp,
                                "entry_bar": i + 1,
                                "size": lots,
                                "max_price": entry_price,
                                "min_price": entry_price,
                                "h4_atr_at_entry": h4_atr_now,
                            }
                    pending = None

                elif d == -1 and high_p[i] >= ema_m5[i]:
                    if i + 1 < n:
                        entry_price = open_p[i + 1] - total_cost / 2
                        h4_atr_now = h4_atr[i]
                        sl = entry_price + sl_mult * h4_atr_now
                        tp = entry_price - tp_mult * h4_atr_now

                        risk_amt = equity * risk_pct / 100.0
                        sl_dist = sl - entry_price
                        if sl_dist > 0.1 and equity > 0:
                            lots = np.clip(risk_amt / (sl_dist * money_per_pt), 0.01, 10.0)
                            position = {
                                "direction": -1,
                                "entry_price": entry_price,
                                "sl": sl,
                                "tp": tp,
                                "entry_bar": i + 1,
                                "size": lots,
                                "max_price": entry_price,
                                "min_price": entry_price,
                                "h4_atr_at_entry": h4_atr_now,
                            }
                    pending = None

        # ── NEW SIGNAL ──
        if position is None and pending is None and i < n - max_hold:
            if i - last_exit_bar < 48:  # min 4h between trades
                continue

            # Session: 7-18 UTC only
            bar_hour = int((timestamps[i] - timestamps[i].astype("datetime64[D]")).astype("timedelta64[h]").astype(int))
            if bar_hour < 7 or bar_hour >= 18:
                continue

            # H4 ATR filter
            if h4_atr[i] < min_h4_atr:
                continue

            # Spread filter
            if spread[i] / (h4_atr[i] + 1e-10) > max_spread_pct:
                continue

            # Regime change detection (new trend)
            curr = regime[i]
            prev = regime[i - 1]

            # Signal on fresh regime confirmation (not just existing trend)
            # OR: signal when regime is established AND price pulls back
            if curr == 1 and regime[i - 48:i].mean() > 0.8:
                # Bullish regime confirmed — look for pullback
                pending = {"direction": 1, "signal_bar": i}
            elif curr == -1 and regime[i - 48:i].mean() < -0.8:
                pending = {"direction": -1, "signal_bar": i}

    equity_curve[-1] = equity

    if not trades:
        return {"error": "No trades"}

    pnls = np.array([t["pnl_money"] for t in trades])
    directions = np.array([t["direction"] for t in trades])
    bars_arr = np.array([t["bars_held"] for t in trades])
    reasons = [t["reason"] for t in trades]

    n_trades = len(trades)
    winners = pnls > 0
    win_rate = winners.mean()
    total_pnl = pnls.sum()

    avg_win = pnls[winners].mean() if winners.sum() > 0 else 0
    avg_loss = pnls[~winners].mean() if (~winners).sum() > 0 else 0
    rr = abs(avg_win / avg_loss) if avg_loss != 0 else 0
    pf = abs(pnls[winners].sum() / (pnls[~winners].sum() + 1e-10))

    trade_years = n / (288 * 252)
    trades_per_year = n_trades / trade_years
    sharpe = (pnls.mean() / (pnls.std() + 1e-10)) * np.sqrt(trades_per_year)

    cum_pnl = np.cumsum(pnls)
    running_max = np.maximum.accumulate(cum_pnl)
    max_dd = (cum_pnl - running_max).min()
    max_dd_pct = max_dd / capital * 100

    annual_ret = (total_pnl / capital) / trade_years * 100
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
        "rr_ratio": rr,
        "profit_factor": pf,
        "sharpe": sharpe,
        "max_drawdown": max_dd,
        "max_drawdown_pct": max_dd_pct,
        "annual_return_pct": annual_ret,
        "calmar": calmar,
        "avg_bars_held": bars_arr.mean(),
        "trades_per_year": trades_per_year,
        "equity_curve": equity_curve,
        "trades": trades,
        "exit_reasons": {r: reasons.count(r) for r in ["sl", "tp", "time", "regime"]},
    }


def main():
    print("=" * 70)
    print("DOMINION FINAL — H4-Scale Swing + M5 Precision Entry")
    print("=" * 70)
    print()

    df = pl.read_parquet(DATASET_PATH)
    print(f"Dataset: {df.shape[0]:,} M5 bars")
    print()

    configs = [
        {"sl_mult": 0.5, "tp_mult": 1.0, "trailing_at": 0.5, "trailing_dist": 0.3, "label": "SL0.5 TP1.0 trail"},
        {"sl_mult": 0.5, "tp_mult": 1.5, "trailing_at": 0.7, "trailing_dist": 0.3, "label": "SL0.5 TP1.5 trail"},
        {"sl_mult": 0.75, "tp_mult": 1.5, "trailing_at": 0.7, "trailing_dist": 0.4, "label": "SL0.75 TP1.5 trail"},
        {"sl_mult": 1.0, "tp_mult": 2.0, "trailing_at": 1.0, "trailing_dist": 0.5, "label": "SL1.0 TP2.0 trail"},
        {"sl_mult": 0.5, "tp_mult": 0.75, "trailing_at": 0.4, "trailing_dist": 0.25, "label": "Tight SL0.5 TP0.75"},
        {"sl_mult": 0.3, "tp_mult": 0.5, "trailing_at": 0.3, "trailing_dist": 0.2, "label": "Scalp SL0.3 TP0.5"},
    ]

    print(f"{'Config':<25} {'N':<6} {'WR%':<7} {'RR':<5} {'PF':<6} {'Sharpe':<8} {'DD%':<7} {'Ann%':<8} {'$/yr':<10}")
    print("-" * 95)

    best = None
    best_sharpe = -999

    for cfg in configs:
        label = cfg.pop("label")
        bt = run_strategy(df, **cfg)
        cfg["label"] = label

        if "error" in bt:
            print(f"{label:<25} No trades")
            continue

        pnl_yr = bt["total_pnl"] / (len(df) / (288 * 252))
        print(f"{label:<25} {bt['n_trades']:<6} {bt['win_rate']*100:<7.1f} "
              f"{bt['rr_ratio']:<5.2f} {bt['profit_factor']:<6.2f} {bt['sharpe']:<8.2f} "
              f"{bt['max_drawdown_pct']:<7.1f} {bt['annual_return_pct']:<8.1f} ${pnl_yr:<10,.0f}")

        if bt["sharpe"] > best_sharpe and bt["n_trades"] > 30:
            best_sharpe = bt["sharpe"]
            best = (label, bt)

    if best is None:
        print("\nNo viable config.")
        return

    label, bt = best
    print(f"\n{'═' * 70}")
    print(f"BEST: {label}")
    print(f"{'═' * 70}")
    print(f"  Trades:        {bt['n_trades']} ({bt['trades_per_year']:.0f}/year)")
    print(f"  Long/Short:    {bt['n_long']}/{bt['n_short']}")
    print(f"  Win Rate:      {bt['win_rate']*100:.1f}% (L={bt['long_wr']*100:.1f}% S={bt['short_wr']*100:.1f}%)")
    print(f"  R:R:           {bt['rr_ratio']:.2f}")
    print(f"  Profit Factor: {bt['profit_factor']:.2f}")
    print(f"  Sharpe:        {bt['sharpe']:.2f}")
    print(f"  Max DD:        {bt['max_drawdown_pct']:.1f}%")
    print(f"  Annual Return: {bt['annual_return_pct']:.1f}%")
    print(f"  Calmar:        {bt['calmar']:.2f}")
    print(f"  Total PnL:     ${bt['total_pnl']:,.0f}")
    print(f"  Avg Hold:      {bt['avg_bars_held']:.0f} bars ({bt['avg_bars_held']*5/60:.1f}h)")
    print(f"  Exits:         {bt['exit_reasons']}")

    # Yearly
    print(f"\n  Yearly:")
    yearly = {}
    for t in bt["trades"]:
        yk = t["exit_time"][:4]
        yearly[yk] = yearly.get(yk, 0) + t["pnl_money"]
    pos_years = sum(1 for v in yearly.values() if v > 0)
    print(f"  Profitable years: {pos_years}/{len(yearly)}")
    for y in sorted(yearly.keys()):
        sign = "+" if yearly[y] > 0 else ""
        print(f"    {y}: {sign}${yearly[y]:>10,.0f}")

    # Save
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    eq_df = pl.DataFrame({"timestamp": df["timestamp"], "equity": bt["equity_curve"]})
    eq_df.write_parquet(OUTPUT_DIR / "equity_curve.parquet")
    pl.DataFrame(bt["trades"]).write_parquet(OUTPUT_DIR / "trades.parquet")
    print(f"\n  Saved to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
