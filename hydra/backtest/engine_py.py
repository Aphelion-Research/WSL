"""Python reference backtester — oracle implementation."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np

from hydra.config import BACKTEST, TARGET
from hydra.backtest.metrics import compute_all


@dataclass
class Trade:
    entry_ts: int
    exit_ts: int
    direction: int
    entry_px: float
    exit_px: float
    pnl: float
    bars_held: int
    size: float


def kelly_size(
    confidence: float,
    capital: float,
    payoff_ratio: float = TARGET.target_mult / TARGET.stop_mult,
    kelly_frac: float = BACKTEST.kelly_frac,
    pos_cap: float = BACKTEST.pos_cap,
) -> float:
    p = confidence
    b = payoff_ratio
    edge = p * b - (1 - p)
    if edge <= 0:
        return 0.0
    f_star = edge / b
    size = kelly_frac * f_star * capital
    return min(size, pos_cap * capital)


def run_backtest(
    close: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    atr: np.ndarray,
    signals: np.ndarray,
    confidences: np.ndarray,
    agreement_mult: np.ndarray | None = None,
    capital: float = BACKTEST.capital,
    spread: float = BACKTEST.spread_pips,
    slippage: float = BACKTEST.slippage_pips,
    commission: float = BACKTEST.commission_rt,
    horizon: int = TARGET.horizon_bars,
    trailing_be: float = BACKTEST.trailing_to_be_at,
) -> tuple[list[Trade], np.ndarray]:
    """Run backtest on precomputed signals.

    Args:
        close: close prices
        high: high prices
        low: low prices
        atr: ATR values (same length as close)
        signals: -1, 0, +1 per bar
        confidences: [0, 1] per bar
        agreement_mult: sizing multiplier per bar (default 1.0)
        capital: starting capital

    Returns:
        (trades, equity_curve)
    """
    n = len(close)
    if agreement_mult is None:
        agreement_mult = np.ones(n)

    trades: list[Trade] = []
    equity = capital
    equity_curve = [equity]

    in_trade = False
    entry_bar = 0
    entry_px = 0.0
    direction = 0
    stop_px = 0.0
    target_px = 0.0
    trade_size = 0.0
    entry_atr = 0.0
    stop_moved_to_be = False

    for t in range(n):
        if not in_trade:
            sig = int(signals[t]) if np.isfinite(signals[t]) else 0
            conf = confidences[t] if np.isfinite(confidences[t]) else 0.0

            if sig != 0 and conf > 0 and np.isfinite(atr[t]) and atr[t] > 0:
                direction = sig
                cost = (spread / 2 + slippage)
                entry_px = close[t] + direction * cost
                entry_atr = atr[t]
                stop_px = entry_px - direction * TARGET.stop_mult * entry_atr
                target_px = entry_px + direction * TARGET.target_mult * entry_atr
                trade_size = kelly_size(conf, equity) * agreement_mult[t]
                if trade_size <= 0:
                    continue
                entry_bar = t
                in_trade = True
                stop_moved_to_be = False
        else:
            profit_ticks = direction * (close[t] - entry_px)
            if not stop_moved_to_be and profit_ticks >= trailing_be * entry_atr:
                stop_px = entry_px + direction * spread
                stop_moved_to_be = True

            exit_px: Optional[float] = None
            exit_reason = ""

            if direction == 1:
                if low[t] <= stop_px:
                    exit_px = stop_px
                    exit_reason = "stop"
                elif high[t] >= target_px:
                    exit_px = target_px
                    exit_reason = "target"
            else:
                if high[t] >= stop_px:
                    exit_px = stop_px
                    exit_reason = "stop"
                elif low[t] <= target_px:
                    exit_px = target_px
                    exit_reason = "target"

            if exit_px is None and (t - entry_bar) >= horizon:
                exit_px = close[t] - direction * (spread / 2 + slippage)
                exit_reason = "time"

            if exit_px is None:
                opp_sig = int(signals[t]) if np.isfinite(signals[t]) else 0
                opp_conf = confidences[t] if np.isfinite(confidences[t]) else 0.0
                if opp_sig == -direction and opp_conf > 0.70:
                    exit_px = close[t] - direction * (spread / 2 + slippage)
                    exit_reason = "reversal"

            if exit_px is not None:
                raw_pnl = direction * (exit_px - entry_px) * trade_size / entry_atr
                pnl = raw_pnl - commission
                equity += pnl
                trades.append(Trade(
                    entry_ts=entry_bar,
                    exit_ts=t,
                    direction=direction,
                    entry_px=entry_px,
                    exit_px=exit_px,
                    pnl=pnl,
                    bars_held=t - entry_bar,
                    size=trade_size,
                ))
                in_trade = False

        equity_curve.append(equity)

    equity_arr = np.array(equity_curve, dtype=np.float64)
    return trades, equity_arr


def backtest_metrics(trades: list[Trade], equity: np.ndarray) -> dict:
    if not trades:
        return compute_all(np.array([]), equity)
    pnl = np.array([t.pnl for t in trades])
    return compute_all(pnl, equity)
