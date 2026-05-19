"""Tests for execution simulator."""
import pytest
import pandas as pd
import numpy as np
from exec_sim.strategies.vwap import VWAPStrategy
from exec_sim.strategies.twap import TWAPStrategy
from exec_sim.strategies.pov import POVStrategy
from exec_sim.impact.almgren_chriss import permanent_impact, temporary_impact, optimal_trajectory
from exec_sim.matching import walk_book, compute_slippage_bps


def test_vwap_slices_sum_to_target():
    """Test VWAP slices sum to target quantity."""
    start = pd.Timestamp('2024-01-01 09:00:00')
    end = pd.Timestamp('2024-01-01 15:00:00')

    strategy = VWAPStrategy(target_quantity=100.0, start_time=start, end_time=end)

    # Create market data
    timestamps = pd.date_range(start, end, freq='5min')
    market_data = pd.DataFrame({
        'timestamp': timestamps,
        'volume': np.random.uniform(10, 20, len(timestamps))
    })

    slices = strategy.generate_slices(market_data)

    total_qty = sum([s['quantity'] for s in slices])
    assert abs(total_qty - 100.0) < 0.01


def test_twap_uniform_slices():
    """Test TWAP creates uniform slice sizes."""
    start = pd.Timestamp('2024-01-01 09:00:00')
    end = pd.Timestamp('2024-01-01 10:00:00')

    strategy = TWAPStrategy(target_quantity=100.0, start_time=start, end_time=end, slice_interval_min=5)

    slices = strategy.generate_slices(pd.DataFrame())

    # Should have 60/5 = 12 slices of 100/12 each
    assert len(slices) == 12
    for s in slices:
        assert abs(s['quantity'] - 100.0/12) < 0.01


def test_almgren_chriss_impact_nonnegative():
    """Test impact functions return non-negative values."""
    adv = 1000000.0
    sigma = 0.2

    perm = permanent_impact(quantity=1000, adv=adv, sigma=sigma, T_hours=1.0)
    assert perm >= 0

    temp = temporary_impact(rate=100, adv=adv)
    assert temp >= 0


def test_walk_book_reduces_depth():
    """Test walk_book fills correctly."""
    book = [(2001.0, 10.0), (2001.5, 20.0), (2002.0, 15.0)]

    avg_price, filled, remaining = walk_book(price=2002.0, size=25.0, book=book, side='buy')

    assert filled == 25.0
    assert remaining == 0.0
    assert avg_price > 0


def test_fill_rate_bounded():
    """Test fill rate is <= 1.0."""
    book = [(2001.0, 10.0)]

    avg_price, filled, remaining = walk_book(price=2002.0, size=20.0, book=book, side='buy')

    fill_rate = filled / (filled + remaining)
    assert fill_rate <= 1.0


def test_slippage_bps_reasonable():
    """Test slippage is in reasonable range."""
    slippage = compute_slippage_bps(fill_price=2001.0, mid_price=2000.0, side='buy')

    # (2001 - 2000) / 2000 * 10000 = 5 bps
    assert abs(slippage - 5.0) < 0.1
    assert slippage < 100  # < 1%


def test_pov_strategy_slices():
    """Test POV strategy generates slices."""
    start = pd.Timestamp('2024-01-01 09:00:00')
    end = pd.Timestamp('2024-01-01 10:00:00')

    strategy = POVStrategy(target_quantity=100.0, start_time=start, end_time=end, pov_rate=0.1)

    timestamps = pd.date_range(start, end, freq='5min')
    market_data = pd.DataFrame({
        'timestamp': timestamps,
        'volume': [100.0] * len(timestamps)
    })

    slices = strategy.generate_slices(market_data)

    # Each slice should be 0.1 * 100 = 10.0
    assert len(slices) >= 1
    assert all(s['quantity'] <= 10.0 for s in slices)


def test_optimal_trajectory():
    """Test optimal trajectory computes."""
    traj = optimal_trajectory(Q=1000, T=1.0, adv=100000, sigma=0.2)

    assert len(traj) > 0
    assert sum(traj) == pytest.approx(1000, rel=0.01)
