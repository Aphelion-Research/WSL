"""Research Core: Honest validation foundation for Dominion V2.

Enforces:
- Point-in-time data contracts
- Conservative execution simulation
- Forensic diagnostics (cost sensitivity, null tests, stability)
- No optimization, no training, no claims

Usage:
    from research_core.data_contracts import validate_features, validate_ohlcv
    from research_core.execution import simulate_trades
    from research_core.diagnostics import run_cost_sensitivity, run_null_tests
"""

__version__ = "0.1.0"
