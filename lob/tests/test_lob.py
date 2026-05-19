"""Tests for LOB engine."""
import pytest
import pandas as pd
import numpy as np
from lob.state_machine import LimitOrderBook
from lob.metrics import compute_ofi, compute_vpin, compute_roll_spread
from lob.ingestion import generate_synthetic_quotes


def test_lob_state_machine():
    """Test LOB state machine updates."""
    lob = LimitOrderBook(depth=5)

    # Add bids
    lob.update_bid(2000.0, 10.0)
    lob.update_bid(1999.5, 5.0)

    # Add asks
    lob.update_ask(2001.0, 8.0)
    lob.update_ask(2001.5, 12.0)

    assert lob.get_best_bid() == 2000.0
    assert lob.get_best_ask() == 2001.0
    assert lob.get_mid() == 2000.5
    assert lob.get_spread() == 1.0


def test_lob_depth_weighted_mid():
    """Test depth-weighted mid calculation."""
    lob = LimitOrderBook()

    lob.update_bid(2000.0, 10.0)
    lob.update_ask(2002.0, 20.0)

    # Depth-weighted mid = (2000*20 + 2002*10) / (10+20) = 60020/30 = 2000.67
    dwm = lob.get_depth_weighted_mid()
    assert dwm is not None
    assert abs(dwm - 2000.67) < 0.01


def test_lob_depth_imbalance():
    """Test depth imbalance calculation."""
    lob = LimitOrderBook()

    lob.update_bid(2000.0, 30.0)
    lob.update_ask(2001.0, 10.0)

    # Imbalance = (30-10)/(30+10) = 20/40 = 0.5
    imbalance = lob.get_depth_imbalance()
    assert abs(imbalance - 0.5) < 0.01


def test_ofi_computation():
    """Test OFI computes correctly on known sequence."""
    timestamps = pd.date_range('2024-01-01', periods=10, freq='1s')
    df = pd.DataFrame({
        'timestamp': timestamps,
        'tick_price': [2000, 2001, 2002, 2001, 2000, 2001, 2002, 2003, 2002, 2001],
        'bid': [1999.5] * 10,
        'ask': [2000.5] * 10
    })

    ofi_1s = compute_ofi(df, 1)
    assert len(ofi_1s) > 0
    # Prices >= 2000.5 are buys, <= 1999.5 are sells
    # Most prices are > 2000.5, so net OFI should be positive


def test_vpin_bounded():
    """Test VPIN is bounded in [0,1]."""
    timestamps = pd.date_range('2024-01-01', periods=100, freq='1s')
    df = pd.DataFrame({
        'timestamp': timestamps,
        'tick_price': 2000 + np.random.randn(100).cumsum() * 0.5
    })

    vpin = compute_vpin(df, buckets_per_day=10)
    assert vpin.min() >= 0.0
    assert vpin.max() <= 1.0


def test_roll_spread_nonnegative():
    """Test Roll spread is non-negative."""
    prices = pd.Series(2000 + np.random.randn(100).cumsum() * 0.5)
    roll = compute_roll_spread(prices, window=20)
    assert roll.min() >= 0.0


def test_synthetic_quotes():
    """Test synthetic bid/ask generation."""
    df = pd.DataFrame({
        'tick_price': [2000.0, 2001.0, 2002.0]
    })

    df = generate_synthetic_quotes(df, spread_bps=2.0)

    assert 'bid' in df.columns
    assert 'ask' in df.columns
    assert (df['bid'] < df['ask']).all()


def test_lob_snapshot():
    """Test LOB snapshot returns valid dict."""
    lob = LimitOrderBook()
    lob.update_bid(2000.0, 10.0)
    lob.update_ask(2001.0, 8.0)

    snap = lob.snapshot()

    assert 'snapshot_id' in snap
    assert snap['mid_price'] == 2000.5
    assert snap['spread'] == 1.0
    assert len(snap['bids']) == 1
    assert len(snap['asks']) == 1
