"""Stability metrics for strategy evaluation."""
import pandas as pd
import numpy as np
from typing import Dict, Any, List
from ..execution.simulator import Trade


def compute_stability_metrics(
    trades: List[Trade],
    equity_curve: pd.Series,
) -> Dict[str, Any]:
    """Compute stability metrics.

    Args:
        trades: List of Trade objects
        equity_curve: Equity curve series

    Returns:
        Dict with stability metrics
    """
    if len(trades) == 0:
        return {
            "monthly_pf": {},
            "quarterly_sharpe": {},
            "yearly_return": {},
            "top_5_trades_pct": 0.0,
            "longest_win_streak": 0,
            "longest_loss_streak": 0,
            "verdict": "NO_TRADES",
        }

    # Convert trades to DataFrame
    trade_df = pd.DataFrame([
        {
            "time": t.exit_time,
            "pnl_net": t.pnl_net,
        }
        for t in trades
    ])
    trade_df["time"] = pd.to_datetime(trade_df["time"])
    trade_df = trade_df.set_index("time")

    # Monthly profit factor
    monthly_pf = {}
    for month, group in trade_df.groupby(pd.Grouper(freq="M")):
        wins = group[group["pnl_net"] > 0]["pnl_net"].sum()
        losses = -group[group["pnl_net"] < 0]["pnl_net"].sum()
        pf = wins / losses if losses > 0 else np.inf
        monthly_pf[month.strftime("%Y-%m")] = pf

    # Quarterly Sharpe
    quarterly_sharpe = {}
    for quarter, group in trade_df.groupby(pd.Grouper(freq="Q")):
        if len(group) > 1:
            sharpe = group["pnl_net"].mean() / group["pnl_net"].std()
            quarterly_sharpe[quarter.strftime("%Y-Q%q")] = sharpe

    # Yearly return
    yearly_return = {}
    for year, group in trade_df.groupby(pd.Grouper(freq="Y")):
        yearly_return[year.strftime("%Y")] = group["pnl_net"].sum()

    # Top 5 trades concentration
    sorted_pnls = sorted([t.pnl_net for t in trades], reverse=True)
    top_5_sum = sum(sorted_pnls[:5]) if len(sorted_pnls) >= 5 else sum(sorted_pnls)
    total_pnl = sum([t.pnl_net for t in trades])
    top_5_pct = (top_5_sum / total_pnl * 100) if total_pnl > 0 else 0.0

    # Win/loss streaks
    pnls = [t.pnl_net for t in trades]
    current_streak = 0
    longest_win_streak = 0
    longest_loss_streak = 0

    for pnl in pnls:
        if pnl > 0:
            if current_streak > 0:
                current_streak += 1
            else:
                current_streak = 1
            longest_win_streak = max(longest_win_streak, current_streak)
        else:
            if current_streak < 0:
                current_streak -= 1
            else:
                current_streak = -1
            longest_loss_streak = max(longest_loss_streak, -current_streak)

    # Verdict
    warnings = []
    if top_5_pct > 50:
        warnings.append("HIGH_CONCENTRATION")
    if len(monthly_pf) > 3 and sum(1 for pf in monthly_pf.values() if pf < 1.0) / len(monthly_pf) > 0.3:
        warnings.append("UNSTABLE_MONTHLY")

    verdict = "STABLE" if not warnings else "UNSTABLE: " + ", ".join(warnings)

    return {
        "monthly_pf": monthly_pf,
        "quarterly_sharpe": quarterly_sharpe,
        "yearly_return": yearly_return,
        "top_5_trades_pct": top_5_pct,
        "longest_win_streak": longest_win_streak,
        "longest_loss_streak": longest_loss_streak,
        "verdict": verdict,
    }
