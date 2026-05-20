"""Performance metrics: Sharpe, Sortino, Calmar, PF, DD, WR, RR."""
from __future__ import annotations

import numpy as np


def sharpe_ratio(daily_returns: np.ndarray, periods: int = 252) -> float:
    if len(daily_returns) == 0:
        return 0.0
    std = np.std(daily_returns, ddof=1)
    if std < 1e-15:
        return np.inf if np.mean(daily_returns) > 0 else -np.inf
    return np.sqrt(periods) * np.mean(daily_returns) / std


def sortino_ratio(daily_returns: np.ndarray, periods: int = 252) -> float:
    if len(daily_returns) == 0:
        return 0.0
    downside = daily_returns[daily_returns < 0]
    if len(downside) == 0:
        return np.inf
    down_std = np.std(downside, ddof=1)
    if down_std < 1e-15:
        return np.inf
    return np.sqrt(periods) * np.mean(daily_returns) / down_std


def max_drawdown(equity: np.ndarray) -> float:
    if len(equity) == 0:
        return 0.0
    peak = np.maximum.accumulate(equity)
    dd = (peak - equity) / np.where(peak > 0, peak, 1.0)
    return float(np.max(dd))


def calmar_ratio(daily_returns: np.ndarray, equity: np.ndarray, periods: int = 252) -> float:
    mdd = max_drawdown(equity)
    if mdd < 1e-15:
        return np.inf
    annual_ret = np.mean(daily_returns) * periods
    return annual_ret / mdd


def profit_factor(pnl: np.ndarray) -> float:
    winners = pnl[pnl > 0].sum()
    losers = np.abs(pnl[pnl < 0].sum())
    if losers < 1e-15:
        return np.inf
    return winners / losers


def win_rate(pnl: np.ndarray) -> float:
    if len(pnl) == 0:
        return 0.0
    return float(np.sum(pnl > 0) / len(pnl))


def avg_rr(pnl: np.ndarray) -> float:
    winners = pnl[pnl > 0]
    losers = pnl[pnl < 0]
    if len(winners) == 0 or len(losers) == 0:
        return 0.0
    mean_win = np.mean(np.abs(winners))
    mean_loss = np.mean(np.abs(losers))
    if mean_loss < 1e-15:
        return np.inf
    return mean_win / mean_loss


def compute_all(pnl: np.ndarray, equity: np.ndarray) -> dict:
    if len(equity) < 2:
        return {
            "sharpe": 0.0, "sortino": 0.0, "calmar": 0.0,
            "max_dd": 0.0, "profit_factor": 0.0,
            "win_rate": 0.0, "rr": 0.0, "profit": 0.0, "n_trades": 0,
        }
    daily_ret = np.diff(equity) / np.where(equity[:-1] > 0, equity[:-1], 1.0)
    return {
        "sharpe": sharpe_ratio(daily_ret),
        "sortino": sortino_ratio(daily_ret),
        "calmar": calmar_ratio(daily_ret, equity),
        "max_dd": max_drawdown(equity),
        "profit_factor": profit_factor(pnl),
        "win_rate": win_rate(pnl),
        "rr": avg_rr(pnl),
        "profit": float(equity[-1] - equity[0]),
        "n_trades": len(pnl),
    }
