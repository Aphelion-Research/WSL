"""Test diagnostic functions."""
import pytest
import pandas as pd
import numpy as np
from research_core.diagnostics import (
    run_null_tests,
    run_cost_sensitivity,
    compute_stability_metrics,
    NullTestType,
)
from research_core.execution import simulate_trades, SimulationConfig, CostModel, Trade


@pytest.fixture
def sample_ohlcv():
    """Create sample OHLCV data."""
    dates = pd.date_range("2024-01-01", periods=200, freq="5min")
    np.random.seed(42)

    close = 2000 + np.cumsum(np.random.randn(200) * 0.5)
    high = close + np.abs(np.random.randn(200) * 0.3)
    low = close - np.abs(np.random.randn(200) * 0.3)
    open_ = close + np.random.randn(200) * 0.2

    return pd.DataFrame({
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "spread": 0.3,
    }, index=dates)


def test_null_tests_support_random_shuffled(sample_ohlcv):
    """Null tests should support random and shuffled signals."""
    signals = pd.Series(0, index=sample_ohlcv.index)
    signals.iloc[10] = 1
    signals.iloc[30] = 1
    signals.iloc[50] = -1

    config = SimulationConfig(
        signal_at_bar_i_entry_at_bar_i_plus_n=1,
        hold_bars=10,
        cost_model=CostModel(spread_points=0.1, slippage_points=0.05, commission_per_lot=3),
    )

    result = run_null_tests(
        signals,
        sample_ohlcv,
        config,
        test_types=[NullTestType.RANDOM, NullTestType.SHUFFLED],
    )

    assert "original" in result
    assert "random" in result
    assert "shuffled" in result
    assert "summary" in result


def test_cost_sensitivity_degrades_with_costs(sample_ohlcv):
    """Cost sensitivity should show degradation as costs increase."""
    signals = pd.Series(0, index=sample_ohlcv.index)
    # Add multiple signals
    for i in range(10, 100, 20):
        signals.iloc[i] = 1

    config = SimulationConfig(
        signal_at_bar_i_entry_at_bar_i_plus_n=1,
        hold_bars=10,
        cost_model=CostModel.xauusd_baseline(),
    )

    result = run_cost_sensitivity(signals, sample_ohlcv, config)

    # Check that PnL degrades (or stays same) as costs increase
    pnl_0x = result["0.0x"]["total_pnl_net"]
    pnl_1x = result["1.0x"]["total_pnl_net"]
    pnl_2x = result["2.0x"]["total_pnl_net"]
    pnl_3x = result["3.0x"]["total_pnl_net"]

    assert pnl_1x <= pnl_0x
    assert pnl_2x <= pnl_1x
    assert pnl_3x <= pnl_2x


def test_stability_metrics_top_trades_concentration():
    """Stability metrics should compute top 5 trades concentration."""
    # Create trades with heavy concentration in top trade
    trades = [
        Trade(
            entry_time=pd.Timestamp("2024-01-01 10:00"),
            entry_price=2000,
            exit_time=pd.Timestamp("2024-01-01 11:00"),
            exit_price=2010,
            direction=1,
            size_oz=10,
            pnl_gross=100,
            cost=10,
            pnl_net=90,
            exit_reason="hold_bars",
            signal_time=pd.Timestamp("2024-01-01 10:00"),
        ),
        Trade(
            entry_time=pd.Timestamp("2024-01-01 12:00"),
            entry_price=2010,
            exit_time=pd.Timestamp("2024-01-01 13:00"),
            exit_price=2015,
            direction=1,
            size_oz=10,
            pnl_gross=50,
            cost=10,
            pnl_net=5,
            exit_reason="hold_bars",
            signal_time=pd.Timestamp("2024-01-01 12:00"),
        ),
    ]

    equity_curve = pd.Series([1000, 1090, 1095], index=pd.date_range("2024-01-01", periods=3, freq="1H"))

    result = compute_stability_metrics(trades, equity_curve)

    # Top 1 trade is 90/(90+5) = 94.7%
    assert result["top_5_trades_pct"] > 90


def test_validation_metadata_contamination():
    """Contaminated metadata (forbidden columns) should block VALIDATED verdict."""
    # This is tested indirectly via model_forensics
    # The validation step should catch forbidden columns and reject
    pass  # See test_research_core_contracts.py for direct validation tests
