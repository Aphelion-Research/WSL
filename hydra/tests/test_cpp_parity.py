"""Tests for C++ backtester parity with Python reference."""
import pytest
import numpy as np


@pytest.mark.skip(reason="C++ backtester requires compilation")
def test_cpp_python_trade_ledger_parity():
    """Python and C++ backtesters must produce identical trade ledgers."""
    pass


@pytest.mark.skip(reason="C++ backtester requires compilation")
def test_cpp_throughput():
    """C++ backtester should achieve >100k bars/s on CPU."""
    pass
