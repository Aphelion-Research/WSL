"""Baseline gauntlet — dumb strategies the model must beat to prove edge.

Strategies:
  always_long, always_short, previous_bar_direction, momentum,
  mean_reversion, random_same_frequency, no_trade

All operate on bar-level returns with explicit cost deduction.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np


@dataclass
class BaselineResult:
    name: str
    n_trades: int
    win_rate: float
    total_return: float
    sharpe: float
    max_drawdown: float
    profit_factor: float
    avg_r: float


def _cost_per_trade(spread: float, slippage: float, commission: float) -> float:
    return spread + slippage + commission


def _compute_metrics(
    pnl: np.ndarray,
    name: str,
    bars_per_year: int = 252 * 24 * 12,  # M5 bars/year
) -> BaselineResult:
    if len(pnl) == 0:
        return BaselineResult(name=name, n_trades=0, win_rate=0.0,
                              total_return=0.0, sharpe=0.0, max_drawdown=0.0,
                              profit_factor=0.0, avg_r=0.0)

    n_trades = int(np.sum(pnl != 0))
    win_rate = float(np.sum(pnl > 0) / max(n_trades, 1))
    total_return = float(np.sum(pnl))

    equity = np.cumsum(pnl)
    peak = np.maximum.accumulate(equity)
    dd = peak - equity
    max_dd = float(np.max(dd)) if len(dd) > 0 else 0.0

    std = np.std(pnl[pnl != 0], ddof=1) if n_trades > 1 else 1e-15
    mean_pnl = np.mean(pnl[pnl != 0]) if n_trades > 0 else 0.0
    sharpe = float(mean_pnl / std * np.sqrt(min(n_trades, bars_per_year))) if std > 1e-15 else 0.0

    winners = pnl[pnl > 0]
    losers = pnl[pnl < 0]
    pf = float(winners.sum() / abs(losers.sum())) if len(losers) > 0 and losers.sum() != 0 else 0.0

    avg_win = float(np.mean(winners)) if len(winners) > 0 else 0.0
    avg_loss = float(np.mean(np.abs(losers))) if len(losers) > 0 else 1e-15
    avg_r = avg_win / avg_loss if avg_loss > 1e-15 else 0.0

    return BaselineResult(
        name=name,
        n_trades=n_trades,
        win_rate=win_rate,
        total_return=total_return,
        sharpe=sharpe,
        max_drawdown=max_dd,
        profit_factor=pf,
        avg_r=avg_r,
    )


def always_long(
    returns: np.ndarray,
    cost_per_bar: float = 0.0,
) -> BaselineResult:
    """Buy every bar, hold one bar."""
    pnl = returns - cost_per_bar
    return _compute_metrics(pnl, "always_long")


def always_short(
    returns: np.ndarray,
    cost_per_bar: float = 0.0,
) -> BaselineResult:
    """Sell every bar, hold one bar."""
    pnl = -returns - cost_per_bar
    return _compute_metrics(pnl, "always_short")


def previous_bar_direction(
    returns: np.ndarray,
    cost_per_trade: float = 0.0,
) -> BaselineResult:
    """Trade in direction of previous bar return."""
    if len(returns) < 2:
        return _compute_metrics(np.array([]), "previous_bar_direction")
    signals = np.sign(returns[:-1])
    trade_returns = signals * returns[1:]
    costs = np.where(signals != 0, cost_per_trade, 0.0)
    pnl = trade_returns - costs
    return _compute_metrics(pnl, "previous_bar_direction")


def momentum(
    returns: np.ndarray,
    lookback: int = 20,
    cost_per_trade: float = 0.0,
) -> BaselineResult:
    """Trade in direction of lookback-period cumulative return."""
    if len(returns) < lookback + 1:
        return _compute_metrics(np.array([]), "momentum")
    cum = np.cumsum(returns)
    mom_signal = cum[lookback:] - cum[:-lookback]
    signals = np.sign(mom_signal[:-1])
    trade_returns = signals * returns[lookback + 1:]
    costs = np.where(signals != 0, cost_per_trade, 0.0)
    pnl = trade_returns - costs
    return _compute_metrics(pnl, "momentum")


def mean_reversion(
    returns: np.ndarray,
    lookback: int = 20,
    cost_per_trade: float = 0.0,
) -> BaselineResult:
    """Trade against lookback-period cumulative return (fade move)."""
    if len(returns) < lookback + 1:
        return _compute_metrics(np.array([]), "mean_reversion")
    cum = np.cumsum(returns)
    mom_signal = cum[lookback:] - cum[:-lookback]
    signals = -np.sign(mom_signal[:-1])
    trade_returns = signals * returns[lookback + 1:]
    costs = np.where(signals != 0, cost_per_trade, 0.0)
    pnl = trade_returns - costs
    return _compute_metrics(pnl, "mean_reversion")


def random_same_frequency(
    returns: np.ndarray,
    trade_frequency: float = 0.5,
    cost_per_trade: float = 0.0,
    seed: int = 42,
) -> BaselineResult:
    """Random +1/-1 at same frequency as model would trade."""
    rng = np.random.default_rng(seed)
    mask = rng.random(len(returns)) < trade_frequency
    signals = np.where(mask, rng.choice([-1, 1], size=len(returns)), 0)
    trade_returns = signals * returns
    costs = np.where(signals != 0, cost_per_trade, 0.0)
    pnl = trade_returns - costs
    return _compute_metrics(pnl, "random_same_frequency")


def no_trade() -> BaselineResult:
    """Do nothing baseline."""
    return BaselineResult(
        name="no_trade",
        n_trades=0,
        win_rate=0.0,
        total_return=0.0,
        sharpe=0.0,
        max_drawdown=0.0,
        profit_factor=0.0,
        avg_r=0.0,
    )


def run_gauntlet(
    returns: np.ndarray,
    spread: float = 0.30,
    slippage: float = 0.10,
    commission: float = 2.0,
    atr: Optional[float] = None,
    trade_frequency: float = 0.5,
) -> list[BaselineResult]:
    """Run all baselines. Cost is in same units as returns (fractional).

    If atr is provided, cost_per_trade = (spread + slippage) / atr + commission_frac.
    Otherwise cost is raw pips divided by median absolute return as rough normalization.
    """
    if atr is not None and atr > 0:
        cost_bar = (spread + slippage) / atr
        cost_trade = cost_bar
    else:
        med_abs = np.median(np.abs(returns[returns != 0])) if np.any(returns != 0) else 1.0
        cost_trade = (spread + slippage) / (med_abs * 10000) if med_abs > 0 else 0.0
        cost_bar = cost_trade

    results = [
        always_long(returns, cost_bar),
        always_short(returns, cost_bar),
        previous_bar_direction(returns, cost_trade),
        momentum(returns, lookback=20, cost_per_trade=cost_trade),
        mean_reversion(returns, lookback=20, cost_per_trade=cost_trade),
        random_same_frequency(returns, trade_frequency, cost_trade),
        no_trade(),
    ]
    return results


def best_baseline(results: list[BaselineResult]) -> BaselineResult:
    """Return the strongest baseline by Sharpe."""
    return max(results, key=lambda r: r.sharpe)


def model_beats_baselines(
    model_sharpe: float,
    baseline_results: list[BaselineResult],
    margin: float = 0.0,
) -> tuple[bool, str]:
    """Check if model Sharpe exceeds all baselines by margin.

    Returns (beats, explanation).
    """
    best = best_baseline(baseline_results)
    beats = model_sharpe > best.sharpe + margin
    if beats:
        explanation = f"Model Sharpe {model_sharpe:.3f} > best baseline '{best.name}' {best.sharpe:.3f}"
    else:
        explanation = f"Model Sharpe {model_sharpe:.3f} <= best baseline '{best.name}' {best.sharpe:.3f}"
    return beats, explanation
