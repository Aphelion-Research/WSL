"""Training metrics - extend hydra/backtest/metrics.py with ML-specific metrics."""
from __future__ import annotations

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    log_loss,
)

from hydra.backtest.metrics import compute_all as compute_backtest_metrics


def compute_training_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_proba: np.ndarray | None = None,
) -> dict:
    """Compute ML classification metrics.

    Args:
        y_true: True labels (0 or 1)
        y_pred: Predicted labels (0 or 1)
        y_proba: Predicted probabilities [0,1] (optional)

    Returns:
        Dict of metrics
    """
    metrics = {}

    # Basic classification metrics
    metrics["accuracy"] = float(accuracy_score(y_true, y_pred))
    metrics["precision"] = float(precision_score(y_true, y_pred, zero_division=0))
    metrics["recall"] = float(recall_score(y_true, y_pred, zero_division=0))
    metrics["f1"] = float(f1_score(y_true, y_pred, zero_division=0))

    # Class distribution
    metrics["n_samples"] = len(y_true)
    metrics["n_positive"] = int(y_true.sum())
    metrics["n_negative"] = int((y_true == 0).sum())
    metrics["class_balance"] = float(y_true.mean())

    # Probabilistic metrics (if proba provided)
    if y_proba is not None:
        try:
            metrics["roc_auc"] = float(roc_auc_score(y_true, y_proba))
        except ValueError:
            metrics["roc_auc"] = 0.0

        try:
            metrics["log_loss"] = float(log_loss(y_true, y_proba))
        except ValueError:
            metrics["log_loss"] = np.inf

        # Calibration: mean predicted proba vs actual rate
        metrics["calibration"] = {
            "mean_proba": float(y_proba.mean()),
            "actual_rate": float(y_true.mean()),
            "calibration_error": float(abs(y_proba.mean() - y_true.mean())),
        }

    return metrics


def compute_cost_adjusted_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    spread: float = 0.30,
    slippage: float = 0.10,
    commission: float = 2.00,
    atr: float = 3.00,
    stop_mult: float = 1.0,
) -> dict:
    """Compute cost-aware profitability metrics.

    Args:
        y_true: True labels (1=long win, 0=short win)
        y_pred: Predicted labels
        spread: Spread in dollars
        slippage: Slippage in dollars
        commission: Round-trip commission
        atr: Average ATR
        stop_mult: Stop multiplier

    Returns:
        Dict of cost-aware metrics
    """
    # Total cost per trade
    total_cost = spread + slippage + commission

    # Profit per correct prediction (in ATR units)
    # Assumes 2:1 RR, so win = +2 ATR, loss = -1 ATR
    profit_per_win = 2.0 * atr - total_cost
    loss_per_loss = 1.0 * atr + total_cost

    # Compute expected profit
    correct = (y_true == y_pred)
    n_correct = correct.sum()
    n_incorrect = (~correct).sum()

    gross_profit = n_correct * profit_per_win
    gross_loss = n_incorrect * loss_per_loss
    net_profit = gross_profit - gross_loss

    # Metrics
    metrics = {
        "gross_profit": float(gross_profit),
        "gross_loss": float(gross_loss),
        "net_profit": float(net_profit),
        "profit_per_trade": float(net_profit / len(y_true)) if len(y_true) > 0 else 0.0,
        "cost_per_trade": float(total_cost),
        "cost_to_stop_ratio": float(total_cost / (stop_mult * atr)) if atr > 0 else np.inf,
        "break_even_accuracy": float(
            loss_per_loss / (profit_per_win + loss_per_loss)
        ) if (profit_per_win + loss_per_loss) > 0 else 0.5,
    }

    return metrics


def compute_all_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_proba: np.ndarray | None = None,
    trades: list | None = None,
    equity: np.ndarray | None = None,
    spread: float = 0.30,
    atr: float = 3.00,
) -> dict:
    """Compute all metrics (ML + backtest + cost-aware).

    Args:
        y_true: True labels
        y_pred: Predicted labels
        y_proba: Predicted probabilities
        trades: List of Trade objects (from backtest)
        equity: Equity curve array
        spread: Spread in dollars
        atr: Average ATR

    Returns:
        Combined metrics dict
    """
    metrics = {}

    # ML metrics
    metrics["ml"] = compute_training_metrics(y_true, y_pred, y_proba)

    # Cost-aware metrics
    metrics["cost_aware"] = compute_cost_adjusted_metrics(
        y_true, y_pred, spread=spread, atr=atr
    )

    # Backtest metrics (if provided)
    if trades is not None and equity is not None:
        pnl = np.array([t.pnl for t in trades]) if trades else np.array([])
        metrics["backtest"] = compute_backtest_metrics(pnl, equity)

    return metrics


def print_metrics_report(metrics: dict) -> None:
    """Pretty-print metrics report."""
    print("\n" + "=" * 70)
    print("TRAINING METRICS REPORT")
    print("=" * 70)

    if "ml" in metrics:
        print("\nML Classification Metrics:")
        print(f"  Accuracy:    {metrics['ml']['accuracy']:.2%}")
        print(f"  Precision:   {metrics['ml']['precision']:.2%}")
        print(f"  Recall:      {metrics['ml']['recall']:.2%}")
        print(f"  F1 Score:    {metrics['ml']['f1']:.2%}")
        if "roc_auc" in metrics["ml"]:
            print(f"  ROC AUC:     {metrics['ml']['roc_auc']:.3f}")
        print(f"  Samples:     {metrics['ml']['n_samples']:,}")
        print(f"  Class Bal:   {metrics['ml']['class_balance']:.1%} positive")

    if "cost_aware" in metrics:
        print("\nCost-Aware Metrics:")
        print(f"  Net Profit:       ${metrics['cost_aware']['net_profit']:.2f}")
        print(f"  Profit/Trade:     ${metrics['cost_aware']['profit_per_trade']:.2f}")
        print(f"  Cost/Trade:       ${metrics['cost_aware']['cost_per_trade']:.2f}")
        print(f"  Cost/Stop Ratio:  {metrics['cost_aware']['cost_to_stop_ratio']:.1%}")
        print(f"  Break-Even Acc:   {metrics['cost_aware']['break_even_accuracy']:.1%}")

    if "backtest" in metrics:
        print("\nBacktest Metrics:")
        print(f"  Sharpe:        {metrics['backtest']['sharpe']:.2f}")
        print(f"  Sortino:       {metrics['backtest']['sortino']:.2f}")
        print(f"  Calmar:        {metrics['backtest']['calmar']:.2f}")
        print(f"  Win Rate:      {metrics['backtest']['win_rate']:.1%}")
        print(f"  Avg RR:        {metrics['backtest']['rr']:.2f}")
        print(f"  Profit Factor: {metrics['backtest']['profit_factor']:.2f}")
        print(f"  Max Drawdown:  {metrics['backtest']['max_dd']:.1%}")
        print(f"  Trades:        {metrics['backtest']['n_trades']}")

    print("=" * 70 + "\n")
