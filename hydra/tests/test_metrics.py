"""Tests for backtest metrics."""
import numpy as np
import pytest

from hydra.backtest.metrics import (
    sharpe_ratio, sortino_ratio, max_drawdown,
    profit_factor, win_rate, avg_rr, calmar_ratio,
)


def test_sharpe_constant_returns():
    rets = np.full(100, 0.01)
    s = sharpe_ratio(rets)
    assert s == np.inf or s == -np.inf or s > 100


def test_sharpe_zero_std():
    rets = np.full(50, 0.01)
    assert sharpe_ratio(rets) == np.inf


def test_sharpe_negative_constant():
    rets = np.full(50, -0.01)
    assert sharpe_ratio(rets) == -np.inf


def test_sharpe_empty():
    assert sharpe_ratio(np.array([])) == 0.0


def test_win_rate_basic():
    pnl = np.array([100.0] * 60 + [-50.0] * 40)
    assert abs(win_rate(pnl) - 0.60) < 1e-10


def test_rr_basic():
    pnl = np.array([200.0, 200.0, 200.0, -100.0, -100.0])
    assert abs(avg_rr(pnl) - 2.0) < 1e-10


def test_max_drawdown_no_loss():
    equity = np.array([100.0, 110.0, 120.0, 130.0])
    assert max_drawdown(equity) == 0.0


def test_max_drawdown_50pct():
    equity = np.array([100.0, 200.0, 100.0, 150.0])
    assert abs(max_drawdown(equity) - 0.5) < 1e-10


def test_profit_factor_all_wins():
    pnl = np.array([100.0, 50.0, 200.0])
    assert profit_factor(pnl) == np.inf


def test_profit_factor_mixed():
    pnl = np.array([300.0, -100.0])
    assert abs(profit_factor(pnl) - 3.0) < 1e-10


def test_sortino_no_downside():
    rets = np.full(50, 0.01)
    assert sortino_ratio(rets) == np.inf


def test_calmar_no_drawdown():
    equity = np.linspace(100, 200, 100)
    rets = np.diff(equity) / equity[:-1]
    assert calmar_ratio(rets, equity) == np.inf


def test_equity_cumsum():
    pnl = np.array([100.0, -50.0, 200.0, -30.0])
    capital = 100_000.0
    equity = capital + np.cumsum(np.concatenate([[0], pnl]))
    assert equity[-1] == capital + pnl.sum()
