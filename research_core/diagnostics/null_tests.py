"""Null hypothesis tests for signal validation."""
import pandas as pd
import numpy as np
from enum import Enum
from typing import Dict, Any, Callable
from ..execution.simulator import simulate_trades, SimulationConfig


class NullTestType(Enum):
    """Null test types."""

    RANDOM = "random"  # Completely random signals
    SHUFFLED = "shuffled"  # Shuffle original signals
    SHIFTED_1 = "shifted_1"  # Shift signals forward by 1 bar
    SHIFTED_5 = "shifted_5"  # Shift signals forward by 5 bars
    SHIFTED_20 = "shifted_20"  # Shift signals forward by 20 bars
    REVERSED = "reversed"  # Reverse signal direction (long<->short)


def generate_null_signals(
    original_signals: pd.Series,
    test_type: NullTestType,
    seed: int = 42,
) -> pd.Series:
    """Generate null hypothesis signals.

    Args:
        original_signals: Original signal series
        test_type: Type of null test
        seed: Random seed

    Returns:
        Series of null signals
    """
    np.random.seed(seed)

    if test_type == NullTestType.RANDOM:
        # Random signals with same frequency as original
        n_signals = (original_signals != 0).sum()
        n_long = (original_signals == 1).sum()
        n_short = (original_signals == -1).sum()

        # Random indices
        signal_indices = np.random.choice(len(original_signals), size=n_signals, replace=False)
        signals = pd.Series(0, index=original_signals.index)

        # Assign long/short randomly
        long_indices = signal_indices[: n_long]
        short_indices = signal_indices[n_long :]
        signals.iloc[long_indices] = 1
        signals.iloc[short_indices] = -1

        return signals

    elif test_type == NullTestType.SHUFFLED:
        # Shuffle original signals
        shuffled = original_signals.values.copy()
        np.random.shuffle(shuffled)
        return pd.Series(shuffled, index=original_signals.index)

    elif test_type == NullTestType.SHIFTED_1:
        return original_signals.shift(1, fill_value=0)

    elif test_type == NullTestType.SHIFTED_5:
        return original_signals.shift(5, fill_value=0)

    elif test_type == NullTestType.SHIFTED_20:
        return original_signals.shift(20, fill_value=0)

    elif test_type == NullTestType.REVERSED:
        # Reverse signal direction
        return -original_signals

    else:
        raise ValueError(f"Unknown null test type: {test_type}")


def run_null_tests(
    original_signals: pd.Series,
    ohlcv: pd.DataFrame,
    config: SimulationConfig,
    atr: pd.Series = None,
    test_types: list = None,
) -> Dict[str, Any]:
    """Run null hypothesis tests.

    Args:
        original_signals: Original signals
        ohlcv: OHLCV data
        config: Simulation config
        atr: ATR series (optional)
        test_types: List of NullTestType to run (default: all)

    Returns:
        Dict with results for each test type
    """
    if test_types is None:
        test_types = list(NullTestType)

    results = {}

    # Run original
    original_result = simulate_trades(original_signals, ohlcv, config, atr)
    results["original"] = {
        "metrics": original_result["metrics"],
        "num_trades": len(original_result["trades"]),
    }

    # Run null tests
    for test_type in test_types:
        null_signals = generate_null_signals(original_signals, test_type)
        null_result = simulate_trades(null_signals, ohlcv, config, atr)

        results[test_type.value] = {
            "metrics": null_result["metrics"],
            "num_trades": len(null_result["trades"]),
        }

    # Compute comparison
    original_sharpe = results["original"]["metrics"]["sharpe"]
    null_sharpes = [results[t.value]["metrics"]["sharpe"] for t in test_types]

    results["summary"] = {
        "original_sharpe": original_sharpe,
        "null_sharpes": null_sharpes,
        "better_than_null": sum(1 for s in null_sharpes if original_sharpe > s),
        "worse_than_null": sum(1 for s in null_sharpes if original_sharpe < s),
        "verdict": "PASS" if original_sharpe > max(null_sharpes) else "FAIL",
    }

    return results
