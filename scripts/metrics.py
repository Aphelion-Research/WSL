#!/usr/bin/env python3
"""Standard quant metrics for Dominion models.

Metrics:
- Sharpe ratio (annualized)
- Information Coefficient (IC)
- Turnover
- Maximum drawdown
- Win rate
- Profit factor
"""
import numpy as np
import pandas as pd
from typing import Dict, Tuple


def compute_sharpe(returns: pd.Series, risk_free_rate: float = 0.0, annualization_factor: int = 252) -> float:
    """Compute annualized Sharpe ratio.

    Args:
        returns: Series of returns
        risk_free_rate: Annual risk-free rate (default 0.0)
        annualization_factor: 252 for daily, 12 for monthly

    Returns:
        Annualized Sharpe ratio
    """
    if len(returns) == 0 or returns.std() == 0:
        return 0.0

    excess_returns = returns - risk_free_rate / annualization_factor
    return (excess_returns.mean() / excess_returns.std()) * np.sqrt(annualization_factor)


def compute_ic(predictions: pd.Series, actuals: pd.Series) -> Tuple[float, float]:
    """Compute Information Coefficient (Spearman rank correlation).

    Args:
        predictions: Model predictions
        actuals: Actual forward returns

    Returns:
        (IC, p-value)
    """
    from scipy.stats import spearmanr

    # Remove NaNs
    valid = ~(predictions.isna() | actuals.isna())
    if valid.sum() < 3:
        return 0.0, 1.0

    return spearmanr(predictions[valid], actuals[valid])


def compute_turnover(positions: pd.Series) -> float:
    """Compute average daily turnover.

    Args:
        positions: Series of position sizes (e.g., -1, 0, 1 for short, flat, long)

    Returns:
        Average daily turnover (0 to 2, where 2 = full flip every day)
    """
    if len(positions) < 2:
        return 0.0

    position_changes = positions.diff().abs()
    return position_changes.mean()


def compute_max_drawdown(cumulative_returns: pd.Series) -> Tuple[float, str, str]:
    """Compute maximum drawdown.

    Args:
        cumulative_returns: Cumulative returns (1 + ret).cumprod()

    Returns:
        (max_drawdown, start_date, end_date)
    """
    if len(cumulative_returns) == 0:
        return 0.0, None, None

    # Running maximum
    running_max = cumulative_returns.cummax()

    # Drawdown series
    drawdown = (cumulative_returns - running_max) / running_max

    # Maximum drawdown
    max_dd = drawdown.min()

    # Find start and end dates
    end_idx = drawdown.idxmin()
    start_idx = cumulative_returns[:end_idx].idxmax()

    return max_dd, start_idx, end_idx


def compute_win_rate(returns: pd.Series) -> float:
    """Compute win rate (fraction of positive returns).

    Args:
        returns: Series of returns

    Returns:
        Win rate (0 to 1)
    """
    if len(returns) == 0:
        return 0.0

    return (returns > 0).sum() / len(returns)


def compute_profit_factor(returns: pd.Series) -> float:
    """Compute profit factor (total wins / total losses).

    Args:
        returns: Series of returns

    Returns:
        Profit factor (ratio of gains to losses)
    """
    if len(returns) == 0:
        return 0.0

    wins = returns[returns > 0].sum()
    losses = abs(returns[returns < 0].sum())

    if losses == 0:
        return np.inf if wins > 0 else 0.0

    return wins / losses


def compute_all_metrics(
    predictions: pd.Series,
    actuals: pd.Series,
    returns: pd.Series = None,
    positions: pd.Series = None,
    risk_free_rate: float = 0.0,
) -> Dict[str, float]:
    """Compute all standard metrics.

    Args:
        predictions: Model predictions
        actuals: Actual forward returns
        returns: Strategy returns (optional)
        positions: Position series (optional)
        risk_free_rate: Annual risk-free rate

    Returns:
        Dict of metrics
    """
    metrics = {}

    # IC
    ic, ic_pval = compute_ic(predictions, actuals)
    metrics["ic"] = ic
    metrics["ic_pval"] = ic_pval

    # If returns provided, compute return-based metrics
    if returns is not None:
        metrics["sharpe"] = compute_sharpe(returns, risk_free_rate)
        metrics["mean_return"] = returns.mean() * 252  # Annualized
        metrics["volatility"] = returns.std() * np.sqrt(252)  # Annualized
        metrics["win_rate"] = compute_win_rate(returns)
        metrics["profit_factor"] = compute_profit_factor(returns)

        # Drawdown
        cum_returns = (1 + returns).cumprod()
        max_dd, dd_start, dd_end = compute_max_drawdown(cum_returns)
        metrics["max_drawdown"] = max_dd
        metrics["drawdown_start"] = str(dd_start) if dd_start else None
        metrics["drawdown_end"] = str(dd_end) if dd_end else None

    # If positions provided, compute turnover
    if positions is not None:
        metrics["turnover"] = compute_turnover(positions)

    return metrics


def print_metrics(metrics: Dict[str, float], title: str = "Metrics"):
    """Pretty-print metrics.

    Args:
        metrics: Dict of metrics
        title: Report title
    """
    print(f"\n{'=' * 60}")
    print(f"{title}")
    print(f"{'=' * 60}")

    # IC
    if "ic" in metrics:
        ic_star = "***" if metrics.get("ic_pval", 1.0) < 0.001 else "**" if metrics.get("ic_pval", 1.0) < 0.01 else "*" if metrics.get("ic_pval", 1.0) < 0.05 else ""
        print(f"IC (Spearman):        {metrics['ic']:>8.4f} {ic_star}")
        if "ic_pval" in metrics:
            print(f"  p-value:            {metrics['ic_pval']:>8.4f}")

    # Return metrics
    if "sharpe" in metrics:
        print(f"\nSharpe Ratio:         {metrics['sharpe']:>8.2f}")
        print(f"Mean Return (ann):    {metrics['mean_return']:>8.2%}")
        print(f"Volatility (ann):     {metrics['volatility']:>8.2%}")
        print(f"Win Rate:             {metrics['win_rate']:>8.2%}")
        print(f"Profit Factor:        {metrics['profit_factor']:>8.2f}")

    # Drawdown
    if "max_drawdown" in metrics:
        print(f"\nMax Drawdown:         {metrics['max_drawdown']:>8.2%}")
        if metrics.get("drawdown_start"):
            print(f"  Start:              {metrics['drawdown_start']}")
            print(f"  End:                {metrics['drawdown_end']}")

    # Turnover
    if "turnover" in metrics:
        print(f"\nTurnover (daily):     {metrics['turnover']:>8.4f}")

    print("=" * 60)


# Threshold targets for Dominion models
TARGETS = {
    "ic": {
        "excellent": 0.10,  # IC > 0.10 is publication-worthy
        "good": 0.05,  # IC > 0.05 is tradeable
        "acceptable": 0.02,  # IC > 0.02 is signal
        "poor": 0.00,  # IC ≤ 0.00 is noise
    },
    "sharpe": {
        "excellent": 2.0,  # Sharpe > 2.0 is institutional-grade
        "good": 1.0,  # Sharpe > 1.0 is profitable
        "acceptable": 0.5,  # Sharpe > 0.5 has signal
        "poor": 0.0,  # Sharpe ≤ 0.0 is losing
    },
    "max_drawdown": {
        "excellent": -0.05,  # Max DD > -5% is very stable
        "good": -0.10,  # Max DD > -10% is acceptable
        "acceptable": -0.20,  # Max DD > -20% is risky
        "poor": -0.50,  # Max DD < -50% is catastrophic
    },
    "turnover": {
        "excellent": 0.1,  # Turnover < 0.1 is low-frequency
        "good": 0.5,  # Turnover < 0.5 is medium-frequency
        "acceptable": 1.0,  # Turnover < 1.0 is high-frequency
        "poor": 2.0,  # Turnover > 2.0 is too expensive
    },
}


def evaluate_model(metrics: Dict[str, float]) -> Dict[str, str]:
    """Evaluate model performance against targets.

    Args:
        metrics: Dict of computed metrics

    Returns:
        Dict mapping metric -> rating (excellent/good/acceptable/poor)
    """
    ratings = {}

    for metric, thresholds in TARGETS.items():
        if metric not in metrics:
            continue

        value = metrics[metric]

        # IC, Sharpe: higher is better
        if metric in ["ic", "sharpe"]:
            if value >= thresholds["excellent"]:
                ratings[metric] = "excellent"
            elif value >= thresholds["good"]:
                ratings[metric] = "good"
            elif value >= thresholds["acceptable"]:
                ratings[metric] = "acceptable"
            else:
                ratings[metric] = "poor"

        # Max drawdown: less negative is better
        elif metric == "max_drawdown":
            if value >= thresholds["excellent"]:
                ratings[metric] = "excellent"
            elif value >= thresholds["good"]:
                ratings[metric] = "good"
            elif value >= thresholds["acceptable"]:
                ratings[metric] = "acceptable"
            else:
                ratings[metric] = "poor"

        # Turnover: lower is better
        elif metric == "turnover":
            if value <= thresholds["excellent"]:
                ratings[metric] = "excellent"
            elif value <= thresholds["good"]:
                ratings[metric] = "good"
            elif value <= thresholds["acceptable"]:
                ratings[metric] = "acceptable"
            else:
                ratings[metric] = "poor"

    return ratings


if __name__ == "__main__":
    # Example usage
    print("Dominion Metrics Module")
    print("=" * 60)
    print("\nTarget thresholds:")
    print("\nIC (Information Coefficient):")
    print(f"  Excellent:    > {TARGETS['ic']['excellent']}")
    print(f"  Good:         > {TARGETS['ic']['good']}")
    print(f"  Acceptable:   > {TARGETS['ic']['acceptable']}")
    print(f"  Poor:         ≤ {TARGETS['ic']['poor']}")

    print("\nSharpe Ratio:")
    print(f"  Excellent:    > {TARGETS['sharpe']['excellent']}")
    print(f"  Good:         > {TARGETS['sharpe']['good']}")
    print(f"  Acceptable:   > {TARGETS['sharpe']['acceptable']}")
    print(f"  Poor:         ≤ {TARGETS['sharpe']['poor']}")

    print("\nMax Drawdown:")
    print(f"  Excellent:    > {TARGETS['max_drawdown']['excellent']:.0%}")
    print(f"  Good:         > {TARGETS['max_drawdown']['good']:.0%}")
    print(f"  Acceptable:   > {TARGETS['max_drawdown']['acceptable']:.0%}")
    print(f"  Poor:         < {TARGETS['max_drawdown']['poor']:.0%}")

    print("\nTurnover (daily):")
    print(f"  Excellent:    < {TARGETS['turnover']['excellent']}")
    print(f"  Good:         < {TARGETS['turnover']['good']}")
    print(f"  Acceptable:   < {TARGETS['turnover']['acceptable']}")
    print(f"  Poor:         > {TARGETS['turnover']['poor']}")
