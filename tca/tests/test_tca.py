"""Tests for TCA."""
import pytest
from tca.attribution import compute_attribution
from tca.benchmarks import compute_benchmark_comparison


def test_attribution_sum():
    """Test attribution components sum to total."""
    attr = compute_attribution(
        decision_price=2000.0,
        arrival_price=2001.0,
        avg_fill_price=2001.5,
        quantity_target=100.0,
        quantity_filled=100.0,
        pre_trade_mid=1999.0,
        close_price=2002.0,
        side='buy'
    )

    # Components should sum to total
    total_computed = (
        attr['decision_cost_bps'] +
        attr['timing_cost_bps'] +
        attr['impact_cost_bps'] +
        attr['opportunity_cost_bps']
    )

    assert abs(total_computed - attr['total_cost_bps']) < 0.01


def test_attribution_decision_cost():
    """Test decision cost calculation."""
    attr = compute_attribution(
        decision_price=2000.0,
        arrival_price=2000.0,
        avg_fill_price=2000.0,
        quantity_target=100.0,
        quantity_filled=100.0,
        pre_trade_mid=1999.0,
        close_price=2000.0,
        side='buy'
    )

    # Decision cost = (2000 - 1999) / 1999 * 10000 ≈ 5 bps
    assert 4.5 < attr['decision_cost_bps'] < 5.5


def test_benchmark_comparison_sign():
    """Test benchmark comparison has correct sign."""
    bench = compute_benchmark_comparison(
        avg_fill_cost_bps=5.0,
        vwap_cost_bps=3.0,
        twap_cost_bps=4.0,
        regime='trending_up',
        hour_of_day=10
    )

    # vs_vwap = 5 - 3 = +2 (worse than VWAP, positive is bad)
    assert bench['vs_vwap_bps'] == pytest.approx(2.0)
    assert bench['vs_twap_bps'] == pytest.approx(1.0)


def test_regime_field():
    """Test regime field is stored."""
    bench = compute_benchmark_comparison(
        avg_fill_cost_bps=5.0,
        vwap_cost_bps=3.0,
        twap_cost_bps=4.0,
        regime='ranging',
        hour_of_day=14
    )

    assert bench['regime'] == 'ranging'
    assert bench['hour_of_day'] == 14
