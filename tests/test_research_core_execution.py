"""Test execution simulator."""
import pytest
import pandas as pd
import numpy as np
from research_core.execution import (
    simulate_trades,
    SimulationConfig,
    CostModel,
)


@pytest.fixture
def sample_ohlcv():
    """Create sample OHLCV data."""
    dates = pd.date_range("2024-01-01", periods=100, freq="5min")
    np.random.seed(42)

    close = 2000 + np.cumsum(np.random.randn(100) * 0.5)
    high = close + np.abs(np.random.randn(100) * 0.3)
    low = close - np.abs(np.random.randn(100) * 0.3)
    open_ = close + np.random.randn(100) * 0.2

    return pd.DataFrame({
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "spread": 0.3,
    }, index=dates)


def test_next_bar_entry_enforced(sample_ohlcv):
    """Entry should occur at bar i+1 after signal at bar i."""
    signals = pd.Series(0, index=sample_ohlcv.index)
    signals.iloc[10] = 1  # Signal at bar 10

    config = SimulationConfig(
        signal_at_bar_i_entry_at_bar_i_plus_n=1,
        hold_bars=5,
        cost_model=CostModel(spread_points=0, slippage_points=0, commission_per_lot=0),
    )

    result = simulate_trades(signals, sample_ohlcv, config)

    assert len(result["trades"]) == 1
    trade = result["trades"][0]

    # Entry should be at bar 11 (i+1)
    assert trade.signal_time == sample_ohlcv.index[10]
    assert trade.entry_time == sample_ohlcv.index[11]


def test_same_bar_entry_disabled_by_default(sample_ohlcv):
    """Same-bar entry should be disabled by default."""
    with pytest.raises(ValueError, match="Same-bar entry disabled"):
        config = SimulationConfig(
            signal_at_bar_i_entry_at_bar_i_plus_n=0,
            allow_same_bar_entry=False,
        )


def test_stop_loss_conservative(sample_ohlcv):
    """Stop loss should trigger conservatively."""
    signals = pd.Series(0, index=sample_ohlcv.index)
    signals.iloc[10] = 1  # Long signal

    # ATR for stop calculation
    atr = pd.Series(5.0, index=sample_ohlcv.index)

    config = SimulationConfig(
        signal_at_bar_i_entry_at_bar_i_plus_n=1,
        stop_loss_atr_mult=2.0,  # 2 ATR stop
        cost_model=CostModel(spread_points=0, slippage_points=0, commission_per_lot=0),
    )

    result = simulate_trades(signals, sample_ohlcv, config, atr=atr)

    # If stop hit, exit should be at stop price (not better)
    if len(result["trades"]) > 0:
        trade = result["trades"][0]
        if trade.exit_reason == "stop_loss":
            # For long: exit_price should be <= entry - 2*ATR
            assert trade.exit_price <= trade.entry_price - 2 * 5.0


def test_cost_sensitivity_worsens_with_higher_costs(sample_ohlcv):
    """Higher costs should worsen or maintain PnL, never improve."""
    signals = pd.Series(0, index=sample_ohlcv.index)
    signals.iloc[10] = 1
    signals.iloc[30] = 1
    signals.iloc[50] = 1

    # Baseline costs
    config_low = SimulationConfig(
        signal_at_bar_i_entry_at_bar_i_plus_n=1,
        hold_bars=10,
        cost_model=CostModel(spread_points=0.1, slippage_points=0.05, commission_per_lot=3),
    )

    # Higher costs
    config_high = SimulationConfig(
        signal_at_bar_i_entry_at_bar_i_plus_n=1,
        hold_bars=10,
        cost_model=CostModel(spread_points=0.3, slippage_points=0.15, commission_per_lot=9),
    )

    result_low = simulate_trades(signals, sample_ohlcv, config_low)
    result_high = simulate_trades(signals, sample_ohlcv, config_high)

    # High cost PnL should be <= low cost PnL
    assert result_high["metrics"]["total_pnl_net"] <= result_low["metrics"]["total_pnl_net"]


def test_hold_bars_exit(sample_ohlcv):
    """Hold bars exit should trigger at correct bar count."""
    signals = pd.Series(0, index=sample_ohlcv.index)
    signals.iloc[10] = 1

    config = SimulationConfig(
        signal_at_bar_i_entry_at_bar_i_plus_n=1,
        hold_bars=5,
        cost_model=CostModel(spread_points=0, slippage_points=0, commission_per_lot=0),
    )

    result = simulate_trades(signals, sample_ohlcv, config)

    assert len(result["trades"]) == 1
    trade = result["trades"][0]

    # Entry at bar 11, hold 5 bars → exit at bar 16
    expected_exit_idx = 11 + 5
    assert trade.exit_time == sample_ohlcv.index[expected_exit_idx]
    assert trade.exit_reason == "hold_bars"


def test_path_dependent_stop_tp_ambiguity(sample_ohlcv):
    """When both stop and TP possible in same bar, assume stop hit first (conservative)."""
    # Create specific bar where both stop and TP could hit
    ohlcv = sample_ohlcv.copy()

    # Set up a long entry at bar 10, with wide range at bar 11
    entry_price = ohlcv.iloc[11]["open"]
    stop_price = entry_price - 2.0
    tp_price = entry_price + 5.0

    # Bar 11: low enough to hit stop, high enough to hit TP
    ohlcv.loc[ohlcv.index[11], "low"] = stop_price - 0.5
    ohlcv.loc[ohlcv.index[11], "high"] = tp_price + 0.5

    signals = pd.Series(0, index=ohlcv.index)
    signals.iloc[10] = 1

    atr = pd.Series(1.0, index=ohlcv.index)

    config = SimulationConfig(
        signal_at_bar_i_entry_at_bar_i_plus_n=1,
        stop_loss_atr_mult=2.0,
        take_profit_atr_mult=5.0,
        cost_model=CostModel(spread_points=0, slippage_points=0, commission_per_lot=0),
    )

    result = simulate_trades(signals, ohlcv, config, atr=atr)

    if len(result["trades"]) > 0:
        trade = result["trades"][0]
        # Conservative: stop should hit first
        assert trade.exit_reason == "stop_loss"
