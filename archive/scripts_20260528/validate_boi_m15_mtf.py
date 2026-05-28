"""Validate BOI M15 MTF with research_core diagnostics.

Usage:
    python scripts/validate_boi_m15_mtf.py [--config CONFIG_PATH]
"""
import sys
import yaml
import json
import argparse
from pathlib import Path
import pandas as pd
import numpy as np
import xgboost as xgb

sys.path.insert(0, str(Path(__file__).parent.parent))

from boi.data import load_all_timeframes, split_by_date
from boi.features import build_all_features
from research_core.execution import simulate_trades, SimulationConfig, CostModel
from research_core.diagnostics import run_cost_sensitivity, run_null_tests, compute_stability_metrics


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default='config/models/boi_m15_mtf.yaml')
    args = parser.parse_args()

    print("=" * 60)
    print("BOI M15 MTF Validation")
    print("=" * 60)

    with open(args.config) as f:
        config = yaml.safe_load(f)

    output_dir = Path(config['output']['base_dir'])
    model_path = output_dir / config['output']['model_file']
    metadata_path = output_dir / config['output']['metadata_file']

    if not model_path.exists():
        print(f"✗ Model not found at {model_path}")
        print("  Run train_boi_m15_mtf.py first")
        return

    # Load metadata
    with open(metadata_path) as f:
        metadata = json.load(f)

    print(f"\nModel: {metadata['model_name']} v{metadata['version']}")
    print(f"Features: {metadata['feature_count']}")
    print(f"Trained: {metadata['trained_at']}")

    # Load data
    print("\nLoading data...")
    data = load_all_timeframes(config)
    m15 = data['m15']

    # Build features
    print("\nBuilding features...")
    features = build_all_features(
        m15,
        data.get('m5'),
        data.get('h1'),
        data.get('h4'),
        data.get('d1'),
    )

    # Load model
    print("\nLoading model...")
    model = xgb.Booster()
    model.load_model(str(model_path))

    # Split data
    splits = config['splits']
    train_features, val_features, oos_features = split_by_date(
        features,
        splits['train_start'], splits['train_end'],
        splits['val_start'], splits['val_end'],
        splits['oos_start'], splits['oos_end'],
    )
    train_m15, val_m15, oos_m15 = split_by_date(
        m15,
        splits['train_start'], splits['train_end'],
        splits['val_start'], splits['val_end'],
        splits['oos_start'], splits['oos_end'],
    )

    # Predict
    print("\nGenerating predictions...")
    dval = xgb.DMatrix(val_features.dropna())
    doos = xgb.DMatrix(oos_features.dropna())

    val_pred = model.predict(dval)  # Shape: (N, 3)
    oos_pred = model.predict(doos)

    # Convert to signals: use long prob - short prob
    val_signal_score = pd.Series(
        val_pred[:, 2] - val_pred[:, 0],  # long - short
        index=val_features.dropna().index
    )
    oos_signal_score = pd.Series(
        oos_pred[:, 2] - oos_pred[:, 0],
        index=oos_features.dropna().index
    )

    # Simple threshold: > 0 = long, < 0 = short, else skip
    val_signals = pd.Series(0, index=val_signal_score.index)
    val_signals[val_signal_score > 0.1] = 1  # Long
    val_signals[val_signal_score < -0.1] = -1  # Short (not used yet)

    oos_signals = pd.Series(0, index=oos_signal_score.index)
    oos_signals[oos_signal_score > 0.1] = 1
    oos_signals[oos_signal_score < -0.1] = -1

    # Compute ATR
    print("\nComputing ATR...")
    def compute_atr(df):
        tr = pd.concat([
            df['high'] - df['low'],
            (df['high'] - df['close'].shift(1)).abs(),
            (df['low'] - df['close'].shift(1)).abs()
        ], axis=1).max(axis=1)
        return tr.rolling(14).mean()

    val_atr = compute_atr(val_m15)
    oos_atr = compute_atr(oos_m15)

    # Configure simulation
    exec_config = config['execution']
    sim_config = SimulationConfig(
        signal_at_bar_i_entry_at_bar_i_plus_n=exec_config['entry_lag'],
        hold_bars=exec_config['hold_bars'],
        stop_loss_atr_mult=exec_config['stop_atr_mult'],
        take_profit_atr_mult=exec_config['target_atr_mult'],
        cost_model=CostModel(**exec_config['cost_model']),
        position_size_oz=exec_config['position_size_oz'],
    )

    # Run validation
    print("\n" + "=" * 60)
    print("VALIDATION SET")
    print("=" * 60)

    val_result = simulate_trades(val_signals, val_m15, sim_config, val_atr)
    print(f"\nBaseline:")
    print(f"  Trades: {len(val_result['trades'])}")
    print(f"  Sharpe: {val_result['metrics']['sharpe']:.2f}")
    print(f"  Total PnL: ${val_result['metrics']['total_pnl_net']:.2f}")
    print(f"  Win Rate: {val_result['metrics']['win_rate']:.1%}")

    # Cost sensitivity
    print("\nCost Sensitivity:")
    cost_result = run_cost_sensitivity(val_signals, val_m15, sim_config, val_atr)
    for mult in [0.0, 0.5, 1.0, 2.0, 3.0]:
        key = f"{mult}x"
        if key in cost_result:
            r = cost_result[key]
            print(f"  {key}: Sharpe {r['sharpe']:.2f}, PnL ${r['total_pnl_net']:.2f}")

    # Null tests
    print("\nNull Tests:")
    null_result = run_null_tests(val_signals, val_m15, sim_config, val_atr)
    print(f"  Original Sharpe: {null_result['summary']['original_sharpe']:.2f}")
    print(f"  Verdict: {null_result['summary']['verdict']}")

    # Stability
    stability = compute_stability_metrics(val_result['trades'], val_result['equity_curve'])
    print(f"\nStability:")
    print(f"  Top 5 trades: {stability['top_5_trades_pct']:.1f}% of PnL")
    print(f"  Verdict: {stability['verdict']}")

    # OOS
    print("\n" + "=" * 60)
    print("OOS")
    print("=" * 60)

    oos_result = simulate_trades(oos_signals, oos_m15, sim_config, oos_atr)
    print(f"\nBaseline:")
    print(f"  Trades: {len(oos_result['trades'])}")
    print(f"  Sharpe: {oos_result['metrics']['sharpe']:.2f}")
    print(f"  Total PnL: ${oos_result['metrics']['total_pnl_net']:.2f}")
    print(f"  Win Rate: {oos_result['metrics']['win_rate']:.1%}")

    # Cost sensitivity OOS
    print("\nCost Sensitivity:")
    cost_result_oos = run_cost_sensitivity(oos_signals, oos_m15, sim_config, oos_atr)
    for mult in [0.0, 0.5, 1.0, 2.0, 3.0]:
        key = f"{mult}x"
        if key in cost_result_oos:
            r = cost_result_oos[key]
            print(f"  {key}: Sharpe {r['sharpe']:.2f}, PnL ${r['total_pnl_net']:.2f}")

    # Null tests OOS
    print("\nNull Tests:")
    null_result_oos = run_null_tests(oos_signals, oos_m15, sim_config, oos_atr)
    print(f"  Original Sharpe: {null_result_oos['summary']['original_sharpe']:.2f}")
    print(f"  Verdict: {null_result_oos['summary']['verdict']}")

    # Stability OOS
    stability_oos = compute_stability_metrics(oos_result['trades'], oos_result['equity_curve'])
    print(f"\nStability:")
    print(f"  Top 5 trades: {stability_oos['top_5_trades_pct']:.1f}% of PnL")
    print(f"  Verdict: {stability_oos['verdict']}")

    # Save validation report
    report = {
        'model': metadata['model_name'],
        'validation_period': metadata['validation_period'],
        'oos_period': metadata['test_period'],
        'validation': {
            'baseline': val_result['metrics'],
            'cost_sensitivity': cost_result,
            'null_tests': null_result,
            'stability': stability,
        },
        'oos': {
            'baseline': oos_result['metrics'],
            'cost_sensitivity': cost_result_oos,
            'null_tests': null_result_oos,
            'stability': stability_oos,
        },
    }

    report_path = output_dir / config['output']['validation_report']
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    print(f"\n✓ Validation report saved to {report_path}")

    # Final verdict
    print("\n" + "=" * 60)
    print("VERDICT")
    print("=" * 60)

    criteria = config['validation']['rejection_criteria']
    failures = []

    # Check OOS metrics
    oos_metrics = oos_result['metrics']
    if oos_metrics['sharpe'] < criteria['min_sharpe']:
        failures.append(f"Sharpe {oos_metrics['sharpe']:.2f} < {criteria['min_sharpe']}")

    # Check cost robustness
    if cost_result_oos['2.0x']['total_pnl_net'] <= 0:
        failures.append("Not robust to 2x costs")

    # Check null tests
    if null_result_oos['summary']['verdict'] == 'FAIL':
        failures.append("Fails null tests")

    # Check stability
    if stability_oos['top_5_trades_pct'] > criteria['max_top5_contribution_pct']:
        failures.append(f"Top 5 trades {stability_oos['top_5_trades_pct']:.1f}% > {criteria['max_top5_contribution_pct']}%")

    if failures:
        print("❌ REJECTED")
        for f in failures:
            print(f"  - {f}")
    else:
        print("✅ VALIDATED (preliminary)")
        print("  Note: BOI v0 is research only, not production")

    print("=" * 60)


if __name__ == "__main__":
    main()
