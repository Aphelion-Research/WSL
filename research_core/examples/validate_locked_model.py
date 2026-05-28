"""Example: Validate a locked model with research_core.

This script demonstrates forensic validation of a pre-trained model
without optimization or retraining.

Usage:
    python research_core/examples/validate_locked_model.py
"""
import pandas as pd
import numpy as np
import xgboost as xgb
from pathlib import Path
import sys

# Add repo root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from research_core.execution import SimulationConfig, CostModel
from research_core.diagnostics import run_model_forensics


def load_sample_data():
    """Load or create sample OHLCV data for demonstration."""
    # In real usage, load from domdata or parquet
    # Here we create synthetic data for demo

    dates = pd.date_range("2024-01-01", periods=1000, freq="5min")
    np.random.seed(42)

    close = 2000 + np.cumsum(np.random.randn(1000) * 0.5)
    high = close + np.abs(np.random.randn(1000) * 0.3)
    low = close - np.abs(np.random.randn(1000) * 0.3)
    open_ = close + np.random.randn(1000) * 0.2

    ohlcv = pd.DataFrame({
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "spread": 0.3,
    }, index=dates)

    return ohlcv


def load_locked_model():
    """Load a locked model (no retraining).

    In real usage:
        model = xgb.Booster()
        model.load_model("models/Him/Him_V2_MultiScale.json")

    For demo, we return mock predictions.
    """
    # Mock predictions (in real usage, load model and predict)
    n = 1000
    np.random.seed(42)

    # Simulate predictions with some signal
    predictions = np.random.uniform(0.3, 0.7, n)

    # Add some structure (not realistic, just for demo)
    predictions[::50] = 0.8  # Periodic strong signals

    return predictions


def main():
    """Run model forensics on locked model."""
    print("Loading data...")
    ohlcv = load_sample_data()

    print("Loading locked model predictions...")
    predictions = load_locked_model()
    predictions = pd.Series(predictions, index=ohlcv.index)

    print("Computing ATR...")
    tr = pd.concat([
        ohlcv["high"] - ohlcv["low"],
        (ohlcv["high"] - ohlcv["close"].shift(1)).abs(),
        (ohlcv["low"] - ohlcv["close"].shift(1)).abs(),
    ], axis=1).max(axis=1)
    atr = tr.rolling(14).mean()

    print("Configuring simulation...")
    config = SimulationConfig(
        signal_at_bar_i_entry_at_bar_i_plus_n=1,  # Next-bar entry
        hold_bars=16,  # 80 minutes (16 * 5min bars)
        stop_loss_atr_mult=10.0,  # Catastrophic stop only
        cost_model=CostModel.xauusd_baseline(),
        position_size_oz=10.0,  # 0.1 lot
    )

    print("\nRunning model forensics...")
    print("This will:")
    print("  1. Validate data contracts")
    print("  2. Run baseline simulation")
    print("  3. Test cost sensitivity (0x, 0.5x, 1x, 2x, 3x)")
    print("  4. Run null tests (random, shuffled, shifted, reversed)")
    print("  5. Compute stability metrics")
    print("  6. Generate verdict\n")

    output_path = Path("output_him_v2/forensic_demo_report.json")
    output_path.parent.mkdir(exist_ok=True, parents=True)

    report = run_model_forensics(
        predictions=predictions,
        ohlcv=ohlcv,
        config=config,
        threshold=0.55,  # Locked threshold
        atr=atr,
        output_path=output_path,
    )

    print(f"\nForensic analysis complete.")
    print(f"Report saved to: {output_path}")
    print(f"\nFinal verdict: {report['verdict']}")


if __name__ == "__main__":
    main()
