"""Model forensics: validate locked model outputs."""
import pandas as pd
import numpy as np
import json
from pathlib import Path
from typing import Dict, Any, Optional
from ..execution.simulator import simulate_trades, SimulationConfig
from ..data_contracts.validation import validate_features, validate_ohlcv
from .null_tests import run_null_tests
from .cost_sensitivity import run_cost_sensitivity
from .stability import compute_stability_metrics


def run_model_forensics(
    predictions: pd.Series,
    ohlcv: pd.DataFrame,
    config: SimulationConfig,
    threshold: float,
    atr: Optional[pd.Series] = None,
    features: Optional[pd.DataFrame] = None,
    output_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Run comprehensive model forensics.

    This function:
    1. Validates data contracts
    2. Converts predictions to signals
    3. Runs cost sensitivity tests
    4. Runs null hypothesis tests
    5. Computes stability metrics
    6. Outputs JSON report + terminal summary

    Args:
        predictions: Model predictions (probabilities or classes)
        ohlcv: OHLCV data
        config: Simulation config
        threshold: Prediction threshold for signals
        atr: ATR series (optional)
        features: Feature DataFrame for validation (optional)
        output_path: Path to save JSON report (optional)

    Returns:
        Dict with all forensic results
    """
    report = {
        "timestamp": pd.Timestamp.now().isoformat(),
        "config": {
            "threshold": threshold,
            "hold_bars": config.hold_bars,
            "stop_loss_atr_mult": config.stop_loss_atr_mult,
            "take_profit_atr_mult": config.take_profit_atr_mult,
            "cost_model": {
                "spread_points": config.cost_model.spread_points,
                "slippage_points": config.cost_model.slippage_points,
                "commission_per_lot": config.cost_model.commission_per_lot,
            },
        },
        "validation": {},
        "baseline": {},
        "cost_sensitivity": {},
        "null_tests": {},
        "stability": {},
        "verdict": "UNKNOWN",
    }

    # 1. Data contract validation
    try:
        ohlcv_validation = validate_ohlcv(ohlcv)
        report["validation"]["ohlcv"] = "PASS"
    except Exception as e:
        report["validation"]["ohlcv"] = f"FAIL: {str(e)}"
        report["verdict"] = "CONTAMINATED: OHLCV validation failed"
        if output_path:
            output_path.write_text(json.dumps(report, indent=2))
        return report

    if features is not None:
        try:
            feature_validation = validate_features(features, allow_label=False)
            report["validation"]["features"] = "PASS"
        except Exception as e:
            report["validation"]["features"] = f"FAIL: {str(e)}"
            report["verdict"] = "CONTAMINATED: Feature validation failed"
            if output_path:
                output_path.write_text(json.dumps(report, indent=2))
            return report

    # 2. Convert predictions to signals
    signals = pd.Series(0, index=predictions.index)
    signals[predictions > threshold] = 1  # Long signal
    # Note: No short signals in this baseline (can be extended)

    # 3. Baseline performance
    baseline_result = simulate_trades(signals, ohlcv, config, atr)
    report["baseline"]["metrics"] = baseline_result["metrics"]
    report["baseline"]["num_trades"] = len(baseline_result["trades"])

    # 4. Cost sensitivity
    cost_result = run_cost_sensitivity(signals, ohlcv, config, atr)
    report["cost_sensitivity"] = cost_result

    # 5. Null tests
    null_result = run_null_tests(signals, ohlcv, config, atr)
    report["null_tests"] = null_result

    # 6. Stability
    stability_result = compute_stability_metrics(
        baseline_result["trades"],
        baseline_result["equity_curve"],
    )
    report["stability"] = stability_result

    # 7. Verdict
    failures = []
    warnings = []

    # Check null tests
    if null_result["summary"]["verdict"] == "FAIL":
        failures.append("FAIL_NULL_TESTS")

    # Check cost sensitivity
    if not cost_result["summary"]["robust_to_2x_costs"]:
        warnings.append("NOT_ROBUST_2X_COSTS")

    # Check stability
    if "UNSTABLE" in stability_result["verdict"]:
        warnings.append("UNSTABLE")

    # Final verdict
    if failures:
        report["verdict"] = "REJECTED: " + ", ".join(failures)
    elif warnings:
        report["verdict"] = "WEAK: " + ", ".join(warnings)
    else:
        report["verdict"] = "VALIDATED"

    # 8. Save report
    if output_path:
        # Convert numpy types to native Python for JSON serialization
        def convert_types(obj):
            """Recursively convert numpy types to native Python."""
            if isinstance(obj, dict):
                return {k: convert_types(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_types(v) for v in obj]
            elif isinstance(obj, np.bool_):
                return bool(obj)
            elif isinstance(obj, (np.integer, np.int64)):
                return int(obj)
            elif isinstance(obj, (np.floating, np.float64)):
                return float(obj)
            else:
                return obj

        report_clean = convert_types(report)
        output_path.write_text(json.dumps(report_clean, indent=2))
        print(f"✓ Forensic report saved to {output_path}")

    # 9. Print terminal summary
    print("\n" + "=" * 60)
    print("MODEL FORENSICS REPORT")
    print("=" * 60)
    print(f"Verdict: {report['verdict']}")
    print(f"\nBaseline Performance:")
    print(f"  Trades: {report['baseline']['num_trades']}")
    print(f"  Sharpe: {report['baseline']['metrics']['sharpe']:.2f}")
    print(f"  Total PnL: ${report['baseline']['metrics']['total_pnl_net']:.2f}")
    print(f"  Win Rate: {report['baseline']['metrics']['win_rate']:.2%}")
    print(f"\nCost Sensitivity:")
    print(f"  Robust to 2x costs: {cost_result['summary']['robust_to_2x_costs']}")
    print(f"  Robust to 3x costs: {cost_result['summary']['robust_to_3x_costs']}")
    print(f"\nNull Tests:")
    print(f"  Better than null: {null_result['summary']['better_than_null']}/{len(null_result) - 2}")
    print(f"  Verdict: {null_result['summary']['verdict']}")
    print(f"\nStability:")
    print(f"  Top 5 trades: {stability_result['top_5_trades_pct']:.1f}% of PnL")
    print(f"  Verdict: {stability_result['verdict']}")
    print("=" * 60 + "\n")

    return report
