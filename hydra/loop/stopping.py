"""Hard-stop condition checker."""
from __future__ import annotations

from hydra.config import STOP


def hit_targets(metrics: dict) -> bool:
    """True when all four targets are simultaneously met."""
    return (
        metrics.get("sharpe", 0) >= STOP.sharpe_min
        and metrics.get("win_rate", 0) >= STOP.win_rate_min
        and metrics.get("rr", 0) >= STOP.rr_min
        and metrics.get("profit", 0) >= STOP.profit_min
    )


def edge_decayed(recent_trades_wr: float) -> bool:
    """True when rolling win rate has decayed below threshold."""
    return recent_trades_wr < STOP.edge_decay_wr


def drawdown_kill(max_dd: float) -> bool:
    """True when drawdown exceeds kill threshold."""
    return max_dd > STOP.dd_kill
