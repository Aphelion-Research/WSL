"""Backtest evaluator - wrapper around hydra/backtest/engine_py.py."""
from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd

from hydra.config import BACKTEST, TARGET
from hydra.backtest.engine_py import run_backtest, backtest_metrics
from hydra.data.targets import wilder_atr


class BacktestEvaluator:
    """Evaluate trained models via backtesting."""

    def __init__(
        self,
        spread: float = BACKTEST.spread_pips,
        slippage: float = BACKTEST.slippage_pips,
        commission: float = BACKTEST.commission_rt,
        capital: float = BACKTEST.capital,
    ):
        """Initialize evaluator.

        Args:
            spread: Spread in dollars
            slippage: Slippage in dollars
            commission: Commission per round-turn
            capital: Starting capital
        """
        self.spread = spread
        self.slippage = slippage
        self.commission = commission
        self.capital = capital

    def evaluate(
        self,
        df: pd.DataFrame,
        signals: np.ndarray,
        confidences: np.ndarray,
        agreement_mult: Optional[np.ndarray] = None,
        high_col: str = "high",
        low_col: str = "low",
        close_col: str = "close",
    ) -> tuple[list, np.ndarray, dict]:
        """Run backtest on signals.

        Args:
            df: DataFrame with OHLC data
            signals: -1/0/+1 signals per bar
            confidences: [0,1] confidence per bar
            agreement_mult: Optional sizing multiplier
            high_col: High column name
            low_col: Low column name
            close_col: Close column name

        Returns:
            (trades, equity_curve, metrics_dict)
        """
        high = df[high_col].values.astype(np.float64)
        low = df[low_col].values.astype(np.float64)
        close = df[close_col].values.astype(np.float64)

        # Compute ATR
        atr = wilder_atr(high, low, close)

        # Run backtest
        trades, equity = run_backtest(
            close, high, low, atr,
            signals, confidences, agreement_mult,
            capital=self.capital,
            spread=self.spread,
            slippage=self.slippage,
            commission=self.commission,
        )

        # Compute metrics
        metrics = backtest_metrics(trades, equity)
        metrics["profit"] = equity[-1] - self.capital if len(equity) > 0 else 0.0

        return trades, equity, metrics

    def evaluate_walk_forward(
        self,
        df: pd.DataFrame,
        splits: list[tuple[np.ndarray, np.ndarray, np.ndarray]],
        predict_fn: callable,
    ) -> list[dict]:
        """Evaluate using walk-forward splits.

        Args:
            df: Full DataFrame
            splits: List of (train_idx, val_idx, test_idx) tuples
            predict_fn: Function that takes (X_train, y_train, X_test) and returns (signals, confidences)

        Returns:
            List of metrics dicts (one per fold)
        """
        results = []

        for fold_idx, (train_idx, val_idx, test_idx) in enumerate(splits):
            print(f"Evaluating fold {fold_idx + 1}/{len(splits)}...")

            # Get test data
            df_test = df.iloc[test_idx]

            # Predict (caller must implement predict_fn)
            signals, confidences = predict_fn(train_idx, val_idx, test_idx)

            # Backtest
            trades, equity, metrics = self.evaluate(
                df_test, signals, confidences
            )

            metrics["fold"] = fold_idx
            metrics["test_size"] = len(test_idx)
            results.append(metrics)

            print(f"  Fold {fold_idx + 1}: Sharpe={metrics['sharpe']:.2f}, "
                  f"WR={metrics['win_rate']:.1%}, Trades={metrics['n_trades']}")

        return results

    def aggregate_walk_forward_results(
        self,
        results: list[dict],
    ) -> dict:
        """Aggregate walk-forward results across folds.

        Args:
            results: List of metrics dicts from evaluate_walk_forward

        Returns:
            Aggregated metrics
        """
        if not results:
            return {}

        aggregated = {
            "n_folds": len(results),
            "sharpe_mean": float(np.mean([r["sharpe"] for r in results])),
            "sharpe_std": float(np.std([r["sharpe"] for r in results])),
            "win_rate_mean": float(np.mean([r["win_rate"] for r in results])),
            "win_rate_std": float(np.std([r["win_rate"] for r in results])),
            "profit_mean": float(np.mean([r["profit"] for r in results])),
            "profit_std": float(np.std([r["profit"] for r in results])),
            "profit_total": float(sum([r["profit"] for r in results])),
            "trades_total": sum([r["n_trades"] for r in results]),
        }

        return aggregated
