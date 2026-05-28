"""Strategy V4: Daily momentum regime + Intraday mean-reversion entry.

THESIS: Gold trends at the daily level (H4+) and mean-reverts intraday (M5).
The edge: IDENTIFY the daily regime, then FADE intraday moves in the opposite
direction of the trend. This captures the "buy the dip in an uptrend" dynamic.

Architecture:
1. REGIME: H4 exponential moving average crossover (trend detection)
   - Fast EMA (5) > Slow EMA (20) → bullish regime
   - Fast EMA (5) < Slow EMA (20) → bearish regime
2. ENTRY: In bullish regime, buy when M5 zscore < -1.5 (oversold in uptrend)
   In bearish regime, sell when M5 zscore > 1.5 (overbought in downtrend)
3. EXIT: Fixed R:R (1.5:1) with ATR-based stops
4. FILTER: Spread < 30% of ATR, London/NY session, no Friday 18:00+

Key difference from V3: We're FADING the M5 move, not following it.
This works because the H4 trend provides the directional bias.

Usage:
    python -m datasets.strategy_v4
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import polars as pl

ROOT = Path.home() / "Dominion"
DATASET_PATH = ROOT / "datasets" / "mtf_xauusd_v1.parquet"
OUTPUT_DIR = ROOT / "datasets" / "strategy_v4_results"


def run_strategy(
    df: pl.DataFrame,
    # Regime params
    fast_ema_h4: int = 5,
    slow_ema_h4: int = 20,
    # Entry params
    zscore_entry: float = 1.5,
    zscore_window: int = 20,
    # Exit params
    sl_atr_mult: float = 1.0,
    tp_atr_mult: float = 1.5,
    max_hold: int = 36,  # 3 hours
    # Filter params
    min_atr_pct: float = 0.0005,
    max_spread_ratio: float = 0.3,
    min_bars_between: int = 12,  # 1 hour minimum between trades
    # Risk
    capital: float = 100_000.0,
    risk_pct: float = 0.75,
    # Costs
    spread_pts: float = 0.50,
    slippage_pts: float = 0.15,
    commission: float = 1.0,
    lot_size: float = 0.1,
) -> dict:
    """Execute the regime-aligned mean-reversion strategy."""
    close = df["close"].to_numpy()
    open_p = df["open"].to_numpy()
    high_p = df["high"].to_numpy()
    low_p = df["low"].to_numpy()
    timestamps = df["timestamp"].to_numpy()
    spread = df["spread"].to_numpy()

    n = len(close)
    total_cost = spread_pts + slippage_pts
    money_per_pt = 1.0 * lot_size * 100

    # Compute H4 EMAs (on M5 data, using H4-equivalent spans)
    # H4 = 48 M5 bars. EMA(5 H4) on M5 ≈ EMA(240). EMA(20 H4) ≈ EMA(960)
    # But that's too slow. Instead use direct H4 EMA values from features.
    # Actually, compute H4-like EMAs by smoothing close with H4-equivalent alpha.
    h4_fast_span = fast_ema_h4 * 48
    h4_slow_span = slow_ema_h4 * 48

    alpha_fast = 2.0 / (h4_fast_span + 1)
    alpha_slow = 2.0 / (h4_slow_span + 1)

    ema_fast = np.zeros(n)
    ema_slow = np.zeros(n)
    ema_fast[0] = close[0]
    ema_slow[0] = close[0]
    for i in range(1, n):
        ema_fast[i] = alpha_fast * close[i] + (1 - alpha_fast) * ema_fast[i - 1]
        ema_slow[i] = alpha_slow * close[i] + (1 - alpha_slow) * ema_slow[i - 1]

    # Regime: +1 bullish, -1 bearish, 0 flat
    regime = np.where(ema_fast > ema_slow, 1, np.where(ema_fast < ema_slow, -1, 0))

    # M5 z-score (rolling)
    zscore = np.full(n, 0.0, dtype=np.float64)
    for i in range(zscore_window, n):
        window = close[i - zscore_window:i]
        mu = window.mean()
        sigma = window.std()
        if sigma > 1e-10:
            zscore[i] = (close[i] - mu) / sigma

    # ATR
    atr = np.zeros(n)
    atr_period = 14
    for i in range(1, n):
        tr = max(high_p[i] - low_p[i],
                 abs(high_p[i] - close[i - 1]),
                 abs(low_p[i] - close[i - 1]))
        if i < atr_period:
            atr[i] = tr
        else:
            atr[i] = (atr[i - 1] * (atr_period - 1) + tr) / atr_period

    # Backtest
    equity = capital
    equity_curve = np.zeros(n)
    trades = []
    position = None
    last_trade_bar = -min_bars_between

    warmup = max(h4_slow_span, zscore_window) + 100

    for i in range(warmup, n):
        equity_curve[i] = equity

        # Manage position
        if position is not None:
            direction = position["direction"]
            bars_held = i - position["entry_bar"]

            exit_price = None

            if direction == 1:
                if low_p[i] <= position["sl"]:
                    exit_price = position["sl"]
                elif high_p[i] >= position["tp"]:
                    exit_price = position["tp"]
                elif bars_held >= max_hold:
                    exit_price = close[i]
            else:
                if high_p[i] >= position["sl"]:
                    exit_price = position["sl"]
                elif low_p[i] <= position["tp"]:
                    exit_price = position["tp"]
                elif bars_held >= max_hold:
                    exit_price = close[i]

            # Conservative: check if both SL and TP could hit
            if direction == 1 and low_p[i] <= position["sl"] and high_p[i] >= position["tp"]:
                exit_price = position["sl"]  # SL wins
            elif direction == -1 and high_p[i] >= position["sl"] and low_p[i] <= position["tp"]:
                exit_price = position["sl"]

            if exit_price is not None:
                if direction == 1:
                    pnl_pts = exit_price - position["entry_price"] - total_cost / 2
                else:
                    pnl_pts = position["entry_price"] - exit_price - total_cost / 2

                pnl_money = pnl_pts * money_per_pt * position["size"] - commission * position["size"]
                equity += pnl_money

                is_win = pnl_money > 0
                trades.append({
                    "entry_bar": position["entry_bar"],
                    "exit_bar": i,
                    "direction": direction,
                    "entry_price": position["entry_price"],
                    "exit_price": exit_price,
                    "pnl_pts": pnl_pts,
                    "pnl_money": pnl_money,
                    "bars_held": bars_held,
                    "regime": position["regime_at_entry"],
                    "zscore_at_entry": position["zscore_at_entry"],
                    "entry_time": str(timestamps[position["entry_bar"]]),
                    "exit_time": str(timestamps[i]),
                    "win": is_win,
                })
                position = None
                last_trade_bar = i

        # New entry
        if position is None and i < n - max_hold:
            if i - last_trade_bar < min_bars_between:
                continue

            # Session filter (7-19 UTC)
            bar_hour = int((timestamps[i] - timestamps[i].astype("datetime64[D]")).astype("timedelta64[h]").astype(int))
            if bar_hour < 7 or bar_hour >= 19:
                continue

            # Friday filter (no new trades after 16:00 on Friday)
            bar_dow = int((timestamps[i].astype("datetime64[D]") - np.datetime64("1970-01-01", "D")).astype(int) % 7)
            if bar_dow == 4 and bar_hour >= 16:  # Friday
                continue

            # ATR filter
            if atr[i] / close[i] < min_atr_pct:
                continue

            # Spread filter
            if spread[i] / (atr[i] + 1e-10) > max_spread_ratio:
                continue

            current_regime = regime[i]
            current_zscore = zscore[i]

            # LONG: Bullish regime + oversold M5
            if current_regime == 1 and current_zscore < -zscore_entry:
                entry_price = open_p[min(i + 1, n - 1)] + total_cost / 2
                sl = entry_price - sl_atr_mult * atr[i]
                tp = entry_price + tp_atr_mult * atr[i]

                risk_amount = equity * risk_pct / 100.0
                sl_dist = entry_price - sl
                if sl_dist > 0 and equity > 0:
                    lots = np.clip(risk_amount / (sl_dist * money_per_pt), 0.01, 5.0)
                    position = {
                        "direction": 1,
                        "entry_price": entry_price,
                        "sl": sl,
                        "tp": tp,
                        "entry_bar": min(i + 1, n - 1),
                        "size": lots,
                        "regime_at_entry": current_regime,
                        "zscore_at_entry": current_zscore,
                    }

            # SHORT: Bearish regime + overbought M5
            elif current_regime == -1 and current_zscore > zscore_entry:
                entry_price = open_p[min(i + 1, n - 1)] - total_cost / 2
                sl = entry_price + sl_atr_mult * atr[i]
                tp = entry_price - tp_atr_mult * atr[i]

                risk_amount = equity * risk_pct / 100.0
                sl_dist = sl - entry_price
                if sl_dist > 0 and equity > 0:
                    lots = np.clip(risk_amount / (sl_dist * money_per_pt), 0.01, 5.0)
                    position = {
                        "direction": -1,
                        "entry_price": entry_price,
                        "sl": sl,
                        "tp": tp,
                        "entry_bar": min(i + 1, n - 1),
                        "size": lots,
                        "regime_at_entry": current_regime,
                        "zscore_at_entry": current_zscore,
                    }

    equity_curve[-1] = equity

    if not trades:
        return {"error": "No trades"}

    pnls = np.array([t["pnl_money"] for t in trades])
    directions = np.array([t["direction"] for t in trades])
    bars_arr = np.array([t["bars_held"] for t in trades])

    winners = pnls > 0
    n_trades = len(trades)
    win_rate = winners.mean()
    total_pnl = pnls.sum()

    avg_win = pnls[winners].mean() if winners.sum() > 0 else 0
    avg_loss = pnls[~winners].mean() if (~winners).sum() > 0 else 0
    pf = abs(pnls[winners].sum() / (pnls[~winners].sum() + 1e-10))

    avg_bars = bars_arr.mean()
    # Use actual number of trades for Sharpe normalization
    trade_years = n / (288 * 252)
    trades_per_year = n_trades / trade_years if trade_years > 0 else 1
    sharpe = (pnls.mean() / (pnls.std() + 1e-10)) * np.sqrt(trades_per_year)

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
        "rr_ratio": abs(avg_win / avg_loss) if avg_loss != 0 else 0,
        "profit_factor": pf,
        "sharpe": sharpe,
        "max_drawdown": max_dd,
        "max_drawdown_pct": max_dd_pct,
        "annual_return_pct": annual_ret,
        "calmar": calmar,
        "avg_bars_held": avg_bars,
        "equity_curve": equity_curve,
        "trades": trades,
        "trades_per_year": trades_per_year,
    }


def main():
    print("=" * 70)
    print("DOMINION V4 — Regime Mean-Reversion (H4 trend + M5 fade)")
    print("=" * 70)
    print()

    df = pl.read_parquet(DATASET_PATH)
    print(f"Dataset: {df.shape[0]:,} bars ({df['timestamp'].min()} → {df['timestamp'].max()})")
    print()

    # Parameter grid
    configs = [
        {"zscore_entry": 1.0, "sl_atr_mult": 1.0, "tp_atr_mult": 1.5, "label": "Z1.0 RR1.5"},
        {"zscore_entry": 1.5, "sl_atr_mult": 1.0, "tp_atr_mult": 1.5, "label": "Z1.5 RR1.5"},
        {"zscore_entry": 2.0, "sl_atr_mult": 1.0, "tp_atr_mult": 1.5, "label": "Z2.0 RR1.5"},
        {"zscore_entry": 1.5, "sl_atr_mult": 1.0, "tp_atr_mult": 2.0, "label": "Z1.5 RR2.0"},
        {"zscore_entry": 1.5, "sl_atr_mult": 1.5, "tp_atr_mult": 2.0, "label": "Z1.5 SL1.5 RR2.0"},
        {"zscore_entry": 2.0, "sl_atr_mult": 1.5, "tp_atr_mult": 2.5, "label": "Z2.0 SL1.5 RR2.5"},
        {"zscore_entry": 1.5, "sl_atr_mult": 1.0, "tp_atr_mult": 1.0, "label": "Z1.5 RR1.0"},
        {"zscore_entry": 1.0, "sl_atr_mult": 0.75, "tp_atr_mult": 1.0, "label": "Z1.0 tight"},
    ]

    print(f"{'Config':<22} {'N':<6} {'WR%':<7} {'RR':<5} {'PF':<6} {'Sharpe':<8} {'DD%':<7} {'Ann%':<8} {'$/yr':<10} {'Calmar'}")
    print("-" * 100)

    best = None
    best_metric = -999

    for cfg in configs:
        label = cfg.pop("label")
        bt = run_strategy(df, **cfg)
        cfg["label"] = label

        if "error" in bt:
            print(f"{label:<22} No trades")
            continue

        pnl_per_year = bt["total_pnl"] / (len(df) / (288 * 252))
        print(f"{label:<22} {bt['n_trades']:<6} {bt['win_rate']*100:<7.1f} "
              f"{bt['rr_ratio']:<5.2f} {bt['profit_factor']:<6.2f} {bt['sharpe']:<8.2f} "
              f"{bt['max_drawdown_pct']:<7.1f} {bt['annual_return_pct']:<8.1f} "
              f"${pnl_per_year:<10,.0f} {bt['calmar']:<.2f}")

        # Optimize for Sharpe but require minimum trades
        metric = bt["sharpe"] if bt["n_trades"] > 100 else -999
        if metric > best_metric:
            best_metric = metric
            best = (label, bt, cfg)

    if best is None:
        print("\nNo viable strategy.")
        return

    label, bt, cfg = best

    print(f"\n{'═' * 70}")
    print(f"BEST: {label}")
    print(f"{'═' * 70}")
    print(f"  Config: zscore={cfg.get('zscore_entry', 1.5)}, "
          f"SL={cfg.get('sl_atr_mult', 1.0)}xATR, TP={cfg.get('tp_atr_mult', 1.5)}xATR")
    print(f"  Trades:       {bt['n_trades']} ({bt['trades_per_year']:.0f}/year)")
    print(f"  Long/Short:   {bt['n_long']}/{bt['n_short']}")
    print(f"  Win Rate:     {bt['win_rate']*100:.1f}% (L={bt['long_wr']*100:.1f}% S={bt['short_wr']*100:.1f}%)")
    print(f"  R:R:          {bt['rr_ratio']:.2f}")
    print(f"  PF:           {bt['profit_factor']:.2f}")
    print(f"  Sharpe:       {bt['sharpe']:.2f}")
    print(f"  Max DD:       {bt['max_drawdown_pct']:.1f}%")
    print(f"  Annual Ret:   {bt['annual_return_pct']:.1f}%")
    print(f"  Calmar:       {bt['calmar']:.2f}")
    print(f"  Total PnL:    ${bt['total_pnl']:,.0f}")
    print(f"  Avg Hold:     {bt['avg_bars_held']:.0f} bars ({bt['avg_bars_held']*5:.0f} min)")

    # Yearly breakdown
    print(f"\n  Yearly PnL:")
    yearly = {}
    yearly_trades = {}
    for t in bt["trades"]:
        yk = t["exit_time"][:4]
        yearly[yk] = yearly.get(yk, 0) + t["pnl_money"]
        yearly_trades[yk] = yearly_trades.get(yk, 0) + 1

    for y in sorted(yearly.keys()):
        wr_year = sum(1 for t in bt["trades"] if t["exit_time"][:4] == y and t["win"]) / yearly_trades[y] * 100
        print(f"    {y}: ${yearly[y]:>10,.0f}  ({yearly_trades[y]:>3} trades, WR={wr_year:.0f}%)")

    # Monthly last 24
    print(f"\n  Monthly PnL (last 24):")
    monthly = {}
    for t in bt["trades"]:
        mk = t["exit_time"][:7]
        monthly[mk] = monthly.get(mk, 0) + t["pnl_money"]

    months_sorted = sorted(monthly.keys())[-24:]
    pos_m = sum(1 for m in months_sorted if monthly[m] > 0)
    print(f"  Positive: {pos_m}/{len(months_sorted)}")
    for m in months_sorted:
        v = monthly[m]
        bar = "▓" * min(max(1, int(abs(v) / 200)), 30) if v > 0 else "░" * min(max(1, int(abs(v) / 200)), 30)
        print(f"    {m}: {'+'if v>0 else '-'}${abs(v):>7,.0f} {bar}")

    # Save
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    eq_df = pl.DataFrame({"timestamp": df["timestamp"], "equity": bt["equity_curve"]})
    eq_df.write_parquet(OUTPUT_DIR / "equity_curve.parquet")
    pl.DataFrame(bt["trades"]).write_parquet(OUTPUT_DIR / "trades.parquet")
    print(f"\n  Saved to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
