"""
Test: Fold-End Forward-Return Leakage
======================================
Verify that trades near fold end do NOT use forward returns beyond fold boundary.
"""
import pytest
import numpy as np
import sys
import tempfile
from pathlib import Path

# Mock validate_hydra_nonoverlap imports
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))


def test_fold_end_rejects_insufficient_horizon():
    """Test that trades are rejected when full horizon doesn't fit in fold."""
    # Import the trade generation function
    try:
        from validate_hydra_nonoverlap import trade_from_model_signals, Trade
    except ImportError:
        pytest.skip("validate_hydra_nonoverlap not available")

    # Create test data
    n_bars = 100
    horizon = 20
    predictions = np.full(n_bars, 0.7)  # all bullish signals
    returns = np.full(n_bars, 0.01)  # all positive returns
    test_start_idx = 0
    fold_num = 1

    # Generate trades
    trades = trade_from_model_signals(
        predictions=predictions,
        returns=returns,
        threshold=0.6,
        n_bars=n_bars,
        test_start_idx=test_start_idx,
        horizon=horizon,
        fold_num=fold_num,
        source="model"
    )

    # Check: Last trade should NOT use bars beyond fold end
    if len(trades) > 0:
        last_trade = trades[-1]
        # Last trade entry at bar i must satisfy: i + horizon <= n_bars
        # So last_trade.entry_bar should be <= n_bars - horizon
        max_allowed_entry = n_bars - horizon
        assert last_trade.entry_bar - test_start_idx <= max_allowed_entry, (
            f"Last trade enters at bar {last_trade.entry_bar - test_start_idx}, "
            f"but max allowed is {max_allowed_entry} (n_bars={n_bars}, horizon={horizon})"
        )

        # Check that no trade exits beyond fold end
        for trade in trades:
            exit_bar_rel = trade.exit_bar - test_start_idx
            assert exit_bar_rel < n_bars, (
                f"Trade exits at bar {exit_bar_rel}, beyond fold end {n_bars}"
            )


def test_baseline_rejects_insufficient_horizon():
    """Test that baseline trades also reject insufficient horizon."""
    try:
        from validate_hydra_nonoverlap import baseline_trades, Trade
    except ImportError:
        pytest.skip("validate_hydra_nonoverlap not available")

    n_bars = 100
    horizon = 20
    returns = np.full(n_bars, 0.01)
    test_start_idx = 0
    fold_num = 1

    trades = baseline_trades(
        returns=returns,
        n_bars=n_bars,
        test_start_idx=test_start_idx,
        horizon=horizon,
        fold_num=fold_num,
        direction=1,
        source="baseline_long"
    )

    # Check: Last trade should not extend beyond fold
    if len(trades) > 0:
        last_trade = trades[-1]
        max_allowed_entry = n_bars - horizon
        assert last_trade.entry_bar - test_start_idx <= max_allowed_entry, (
            f"Baseline last trade enters at bar {last_trade.entry_bar - test_start_idx}, "
            f"but max allowed is {max_allowed_entry}"
        )


def test_trade_count_matches_available_horizons():
    """Test that number of trades matches available complete horizons."""
    try:
        from validate_hydra_nonoverlap import trade_from_model_signals
    except ImportError:
        pytest.skip("validate_hydra_nonoverlap not available")

    n_bars = 100
    horizon = 20
    predictions = np.full(n_bars, 0.7)  # all signals
    returns = np.full(n_bars, 0.01)
    test_start_idx = 0

    trades = trade_from_model_signals(
        predictions=predictions,
        returns=returns,
        threshold=0.6,
        n_bars=n_bars,
        test_start_idx=test_start_idx,
        horizon=horizon,
        fold_num=1,
        source="model"
    )

    # Expected: floor(n_bars / horizon) complete horizons fit
    # n_bars=100, horizon=20 → 5 complete horizons (0-19, 20-39, 40-59, 60-79, 80-99)
    # But bar 80+20=100 exceeds n_bars, so only 4 trades (0-19, 20-39, 40-59, 60-79)
    expected_max_trades = (n_bars // horizon)
    if n_bars % horizon == 0:
        expected_max_trades -= 1  # last full period would exit at n_bars

    assert len(trades) <= expected_max_trades, (
        f"Expected <= {expected_max_trades} trades, got {len(trades)}"
    )
