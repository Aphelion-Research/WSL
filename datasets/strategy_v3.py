"""Strategy V3: Multi-timeframe trend following with adaptive exits.

Core thesis: Gold exhibits persistent multi-day trends. Instead of trying to
predict M5 bar direction (nearly random), ride H4/H1 trends and use M5 only
for entry timing and exit management.

Architecture:
1. TREND DETECTION: H4 Donchian channel breakout (purely mechanical)
2. ENTRY TIMING: Wait for M5 pullback into EMA (better entry price)
3. EXIT: Trailing stop at 2x ATR, tightens in profit
4. FILTER: Only trade when vol regime is favorable (not too low, not spike)

No ML — pure systematic rules. ML adds complexity without proven edge here.

Usage:
    python -m datasets.strategy_v3
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import polars as pl

ROOT = Path.home() / "Dominion"
DATASET_PATH = ROOT / "datasets" / "mtf_xauusd_v1.parquet"
OUTPUT_DIR = ROOT / "datasets" / "strategy_v3_results"


def backtest_trend_following(
    df: pl.DataFrame,
    # Donchian breakout params
    donchian_period: int = 20,  # H4 bars (= 80 hours = ~3.5 days)
    # Entry params
    pullback_ema: int = 12,  # M5 EMA for pullback entry
    max_entry_wait: int = 24,  # max M5 bars to wait for pullback (2h)
    # Exit params
    initial_sl_atr: float = 2.0,
    trailing_atr: float = 1.5,
    breakeven_at_atr: float = 1.0,  # move SL to BE after 1 ATR profit
    # Filter params
    min_atr_pct: float = 0.001,  # minimum volatility to trade
    max_spread_atr_ratio: float = 0.3,  # spread must be < 30% of ATR
    # Risk params
    capital: float = 100_000.0,
    risk_pct: float = 0.5,  # risk per trade
    max_positions: int = 1,
    # Cost model
    spread_points: float = 0.50,
    slippage_points: float = 0.15,
    commission_per_lot: float = 1.0,
    lot_size: float = 0.1,
) -> dict:
    """Pure trend-following backtest.

    Entry logic:
    1. H4 Donchian breakout: close breaks above/below N-period high/low
    2. After breakout signal, wait for M5 price to pull back to 12-EMA
    3. Enter on the next M5 bar after pullback touch

    Exit logic:
    1. Initial stop = entry - 2*ATR (for longs)
    2. After 1*ATR profit: move stop to breakeven
    3. Trailing stop at 1.5*ATR from highest price since entry
    4. No take profit — let winners run (trailing stop exits)
    """
    # Extract arrays
    timestamps = df["timestamp"].to_numpy()
    open_p = df["open"].to_numpy()
    high_p = df["high"].to_numpy()
    low_p = df["low"].to_numpy()
    close_p = df["close"].to_numpy()
    spread = df["spread"].to_numpy()

    # Compute H4 Donchian from H4 features
    # We'll use the close + rolling high/low directly on M5 but at H4 scale
    # H4 = 48 M5 bars. Donchian 20 on H4 = 960 M5 bars of lookback
    h4_bars = donchian_period * 48  # Convert H4 periods to M5 bars

    # M5 EMA for pullback
    ema = np.zeros(len(close_p))
    alpha = 2.0 / (pullback_ema + 1)
    ema[0] = close_p[0]
    for i in range(1, len(close_p)):
        ema[i] = alpha * close_p[i] + (1 - alpha) * ema[i - 1]

    # ATR (14-period on M5)
    atr = np.zeros(len(close_p))
    atr_period = 14
    for i in range(1, len(close_p)):
        tr = max(high_p[i] - low_p[i],
                 abs(high_p[i] - close_p[i - 1]),
                 abs(low_p[i] - close_p[i - 1]))
        if i < atr_period:
            atr[i] = tr
        else:
            atr[i] = (atr[i - 1] * (atr_period - 1) + tr) / atr_period

    # Rolling high/low for Donchian
    rolling_high = np.zeros(len(close_p))
    rolling_low = np.zeros(len(close_p))
    for i in range(h4_bars, len(close_p)):
        rolling_high[i] = high_p[i - h4_bars:i].max()
        rolling_low[i] = low_p[i - h4_bars:i].min()

    n = len(close_p)
    total_cost = spread_points + slippage_points
    money_per_point = 1.0 * lot_size * 100  # pip_value * lot_size * 100

    # State
    equity = capital
    equity_curve = np.zeros(n)
    trades = []
    position = None
    pending_signal = None  # {"direction", "signal_bar", "signal_price"}

    for i in range(h4_bars + 1, n):
        equity_curve[i] = equity

        # ── MANAGE POSITION ──
        if position is not None:
            direction = position["direction"]
            entry_price = position["entry_price"]
            current_atr = atr[i]

            # Update trailing stop
            if direction == 1:
                # Track highest price since entry
                if high_p[i] > position["max_price"]:
                    position["max_price"] = high_p[i]

                # Breakeven logic
                if position["max_price"] - entry_price >= breakeven_at_atr * current_atr:
                    position["sl"] = max(position["sl"], entry_price + total_cost)

                # Trailing stop
                trail_sl = position["max_price"] - trailing_atr * current_atr
                position["sl"] = max(position["sl"], trail_sl)

                # Check stop hit
                if low_p[i] <= position["sl"]:
                    exit_price = position["sl"]
                    pnl_points = exit_price - entry_price - total_cost
                    pnl_money = pnl_points * money_per_point * position["size"]
                    pnl_money -= commission_per_lot * position["size"]
                    equity += pnl_money

                    trades.append({
                        "entry_bar": position["entry_bar"],
                        "exit_bar": i,
                        "direction": 1,
                        "entry_price": entry_price,
                        "exit_price": exit_price,
                        "pnl_points": pnl_points,
                        "pnl_money": pnl_money,
                        "bars_held": i - position["entry_bar"],
                        "max_excursion": position["max_price"] - entry_price,
                        "entry_time": str(timestamps[position["entry_bar"]]),
                        "exit_time": str(timestamps[i]),
                    })
                    position = None

            else:  # Short
                if low_p[i] < position["min_price"]:
                    position["min_price"] = low_p[i]

                if entry_price - position["min_price"] >= breakeven_at_atr * current_atr:
                    position["sl"] = min(position["sl"], entry_price - total_cost)

                trail_sl = position["min_price"] + trailing_atr * current_atr
                position["sl"] = min(position["sl"], trail_sl)

                if high_p[i] >= position["sl"]:
                    exit_price = position["sl"]
                    pnl_points = entry_price - exit_price - total_cost
                    pnl_money = pnl_points * money_per_point * position["size"]
                    pnl_money -= commission_per_lot * position["size"]
                    equity += pnl_money

                    trades.append({
                        "entry_bar": position["entry_bar"],
                        "exit_bar": i,
                        "direction": -1,
                        "entry_price": entry_price,
                        "exit_price": exit_price,
                        "pnl_points": pnl_points,
                        "pnl_money": pnl_money,
                        "bars_held": i - position["entry_bar"],
                        "max_excursion": entry_price - position["min_price"],
                        "entry_time": str(timestamps[position["entry_bar"]]),
                        "exit_time": str(timestamps[i]),
                    })
                    position = None

        # ── PENDING SIGNAL: WAIT FOR PULLBACK ──
        if pending_signal is not None and position is None:
            bars_waiting = i - pending_signal["signal_bar"]
            if bars_waiting > max_entry_wait:
                pending_signal = None  # expired
            else:
                direction = pending_signal["direction"]
                # Pullback condition: price touches EMA
                if direction == 1 and low_p[i] <= ema[i]:
                    # Enter long on next bar open
                    if i + 1 < n:
                        entry_price = open_p[i + 1] + total_cost / 2
                        current_atr = atr[i]
                        sl = entry_price - initial_sl_atr * current_atr

                        # Risk sizing
                        risk_amount = equity * risk_pct / 100.0
                        sl_dist = entry_price - sl
                        if sl_dist > 0 and equity > 0:
                            lots = risk_amount / (sl_dist * money_per_point)
                            lots = np.clip(lots, 0.01, 5.0)

                            position = {
                                "direction": 1,
                                "entry_price": entry_price,
                                "sl": sl,
                                "entry_bar": i + 1,
                                "size": lots,
                                "max_price": entry_price,
                                "min_price": entry_price,
                            }
                        pending_signal = None

                elif direction == -1 and high_p[i] >= ema[i]:
                    if i + 1 < n:
                        entry_price = open_p[i + 1] - total_cost / 2
                        current_atr = atr[i]
                        sl = entry_price + initial_sl_atr * current_atr

                        risk_amount = equity * risk_pct / 100.0
                        sl_dist = sl - entry_price
                        if sl_dist > 0 and equity > 0:
                            lots = risk_amount / (sl_dist * money_per_point)
                            lots = np.clip(lots, 0.01, 5.0)

                            position = {
                                "direction": -1,
                                "entry_price": entry_price,
                                "sl": sl,
                                "entry_bar": i + 1,
                                "size": lots,
                                "max_price": entry_price,
                                "min_price": entry_price,
                            }
                        pending_signal = None

        # ── GENERATE NEW SIGNAL (Donchian breakout) ──
        if position is None and pending_signal is None and i < n - 50:
            # Filters
            atr_pct_val = atr[i] / close_p[i] if close_p[i] > 0 else 0
            if atr_pct_val < min_atr_pct:
                continue
            spread_ratio = spread[i] / (atr[i] + 1e-10)
            if spread_ratio > max_spread_atr_ratio:
                continue

            # Session filter: only generate signals during London/NY
            bar_hour = int((timestamps[i] - timestamps[i].astype("datetime64[D]")).astype("timedelta64[h]").astype(int))
            if bar_hour < 7 or bar_hour >= 20:
                continue

            # Donchian breakout
            if close_p[i] > rolling_high[i] and close_p[i - 1] <= rolling_high[i - 1]:
                pending_signal = {"direction": 1, "signal_bar": i, "signal_price": close_p[i]}
            elif close_p[i] < rolling_low[i] and close_p[i - 1] >= rolling_low[i - 1]:
                pending_signal = {"direction": -1, "signal_bar": i, "signal_price": close_p[i]}

    equity_curve[-1] = equity

    if not trades:
        return {"error": "No trades"}

    # ── METRICS ──
    pnls = np.array([t["pnl_money"] for t in trades])
    directions = np.array([t["direction"] for t in trades])
    bars_held = np.array([t["bars_held"] for t in trades])

    n_trades = len(trades)
    winners = pnls > 0
    win_rate = winners.mean()
    total_pnl = pnls.sum()

    avg_win = pnls[winners].mean() if winners.sum() > 0 else 0
    avg_loss = pnls[~winners].mean() if (~winners).sum() > 0 else 0
    pf = abs(pnls[winners].sum() / (pnls[~winners].sum() + 1e-10))

    # Sharpe
    avg_bars = bars_held.mean()
    trades_per_year = (252 * 288) / avg_bars if avg_bars > 0 else 1
    sharpe = (pnls.mean() / (pnls.std() + 1e-10)) * np.sqrt(min(trades_per_year, n_trades))

    # Drawdown
    cum_pnl = np.cumsum(pnls)
    running_max = np.maximum.accumulate(cum_pnl)
    max_dd = (cum_pnl - running_max).min()
    max_dd_pct = max_dd / capital * 100

    # Annualized
    total_bars = n
    years = total_bars / (288 * 252)
    annual_return = (total_pnl / capital) / years * 100 if years > 0 else 0
    calmar = annual_return / abs(max_dd_pct) if max_dd_pct != 0 else 0

    # Per-direction
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
        "rr_ratio": abs(avg_win / avg_loss) if avg_loss != 0 else 0,
        "profit_factor": pf,
        "sharpe": sharpe,
        "max_drawdown": max_dd,
        "max_drawdown_pct": max_dd_pct,
        "annual_return_pct": annual_return,
        "calmar": calmar,
        "avg_bars_held": avg_bars,
        "max_bars_held": int(bars_held.max()),
        "equity_curve": equity_curve,
        "trades": trades,
        "long_pnl": pnls[long_mask].sum() if long_mask.sum() > 0 else 0,
        "short_pnl": pnls[short_mask].sum() if short_mask.sum() > 0 else 0,
    }


def main():
    print("=" * 70)
    print("DOMINION STRATEGY V3 — Trend Following (Donchian + Pullback Entry)")
    print("=" * 70)
    print()

    df = pl.read_parquet(DATASET_PATH)
    print(f"Dataset: {df.shape[0]:,} bars, {df['timestamp'].min()} → {df['timestamp'].max()}")
    print()

    # Parameter sweep
    configs = [
        {"donchian_period": 10, "initial_sl_atr": 2.0, "trailing_atr": 1.5, "risk_pct": 0.5, "label": "Fast (10H4)"},
        {"donchian_period": 15, "initial_sl_atr": 2.0, "trailing_atr": 1.5, "risk_pct": 0.5, "label": "Medium (15H4)"},
        {"donchian_period": 20, "initial_sl_atr": 2.0, "trailing_atr": 1.5, "risk_pct": 0.5, "label": "Slow (20H4)"},
        {"donchian_period": 20, "initial_sl_atr": 2.5, "trailing_atr": 2.0, "risk_pct": 0.5, "label": "Wide (20H4 wide)"},
        {"donchian_period": 15, "initial_sl_atr": 1.5, "trailing_atr": 1.0, "risk_pct": 0.75, "label": "Tight (15H4 tight)"},
        {"donchian_period": 15, "initial_sl_atr": 2.0, "trailing_atr": 1.5, "risk_pct": 1.0, "label": "Aggressive (15H4 1%)"},
    ]

    print(f"{'Config':<22} {'Trades':<8} {'WR%':<7} {'RR':<5} {'PF':<7} {'Sharpe':<8} {'DD%':<7} {'Annual%':<9} {'Calmar':<7} {'PnL$'}")
    print("-" * 105)

    best = None
    best_sharpe = -999

    for cfg in configs:
        label = cfg.pop("label")
        bt = backtest_trend_following(df, **cfg)
        cfg["label"] = label

        if "error" in bt:
            print(f"{label:<22} No trades")
            continue

        print(f"{label:<22} {bt['n_trades']:<8} {bt['win_rate']*100:<7.1f} "
              f"{bt['rr_ratio']:<5.1f} {bt['profit_factor']:<7.2f} {bt['sharpe']:<8.2f} "
              f"{bt['max_drawdown_pct']:<7.1f} {bt['annual_return_pct']:<9.1f} "
              f"{bt['calmar']:<7.2f} ${bt['total_pnl']:>10,.0f}")

        if bt["sharpe"] > best_sharpe:
            best_sharpe = bt["sharpe"]
            best = (label, bt)

    if best is None:
        print("\nNo viable configuration found.")
        return

    label, bt = best
    print(f"\n{'═' * 70}")
    print(f"BEST: {label} (Sharpe={bt['sharpe']:.2f})")
    print(f"{'═' * 70}")
    print()
    print(f"  Trades:          {bt['n_trades']} (Long={bt['n_long']}, Short={bt['n_short']})")
    print(f"  Win Rate:        {bt['win_rate']*100:.1f}% (L={bt['long_wr']*100:.1f}%, S={bt['short_wr']*100:.1f}%)")
    print(f"  R:R Ratio:       {bt['rr_ratio']:.2f}")
    print(f"  Profit Factor:   {bt['profit_factor']:.2f}")
    print(f"  Total PnL:       ${bt['total_pnl']:,.0f}")
    print(f"  Annual Return:   {bt['annual_return_pct']:.1f}%")
    print(f"  Max Drawdown:    {bt['max_drawdown_pct']:.1f}%")
    print(f"  Sharpe:          {bt['sharpe']:.2f}")
    print(f"  Calmar:          {bt['calmar']:.2f}")
    print(f"  Avg Hold:        {bt['avg_bars_held']:.0f} bars ({bt['avg_bars_held']*5/60:.1f}h)")
    print(f"  Max Hold:        {bt['max_bars_held']} bars ({bt['max_bars_held']*5/60:.1f}h)")
    print(f"  Long PnL:        ${bt['long_pnl']:,.0f}")
    print(f"  Short PnL:       ${bt['short_pnl']:,.0f}")

    # Monthly PnL
    print(f"\n  Monthly PnL (full history):")
    monthly = {}
    for t in bt["trades"]:
        mk = t["exit_time"][:7]
        monthly[mk] = monthly.get(mk, 0) + t["pnl_money"]

    months_sorted = sorted(monthly.keys())
    pos_months = sum(1 for m in months_sorted if monthly[m] > 0)
    print(f"  Positive months: {pos_months}/{len(months_sorted)} ({pos_months/len(months_sorted)*100:.0f}%)")

    # Show last 36 months
    for m in months_sorted[-36:]:
        v = monthly[m]
        bar_len = max(1, int(abs(v) / 300))
        bar_char = "▓" if v > 0 else "░"
        sign = "+" if v > 0 else "-"
        print(f"    {m}: {sign}${abs(v):>8,.0f} {bar_char * min(bar_len, 40)}")

    # Yearly summary
    print(f"\n  Yearly Summary:")
    yearly = {}
    for t in bt["trades"]:
        yk = t["exit_time"][:4]
        yearly[yk] = yearly.get(yk, 0) + t["pnl_money"]
    for y in sorted(yearly.keys()):
        print(f"    {y}: ${yearly[y]:>10,.0f}")

    # Save
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    eq_df = pl.DataFrame({"timestamp": df["timestamp"], "equity": bt["equity_curve"]})
    eq_df.write_parquet(OUTPUT_DIR / "equity_curve.parquet")
    pl.DataFrame(bt["trades"]).write_parquet(OUTPUT_DIR / "trades.parquet")
    print(f"\n  Saved to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
