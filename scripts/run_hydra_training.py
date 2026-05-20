#!/usr/bin/env python3
"""HYDRA training runner CLI - Agent 2 entrypoint.

Usage:
    python scripts/run_hydra_training.py                    # Run with defaults
    python scripts/run_hydra_training.py --matrix path.parquet  # Custom matrix
    python scripts/run_hydra_training.py --mode scalp        # Train only scalp
    python scripts/run_hydra_training.py --no-gate-check    # Skip gate check (dangerous!)
"""
from __future__ import annotations

import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from hydra.training.hydra_runner import HydraRunner


def main():
    parser = argparse.ArgumentParser(description="HYDRA training runner (Agent 2)")

    parser.add_argument(
        "--matrix",
        type=str,
        default=None,
        help="Path to matrix parquet (default: data/dataset_v1.parquet)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Output directory for artifacts (default: artifacts/hydra)",
    )
    parser.add_argument(
        "--mode",
        type=str,
        default="all",
        choices=["all", "scalp", "day", "swing"],
        help="Which brains to train (default: all)",
    )
    parser.add_argument(
        "--no-gate-check",
        action="store_true",
        help="Skip training gate check (DANGEROUS - only use if Agent 1 verdict missing)",
    )

    args = parser.parse_args()

    # Create runner
    runner = HydraRunner(
        matrix_path=Path(args.matrix) if args.matrix else None,
        output_dir=Path(args.output_dir) if args.output_dir else None,
        check_gates=not args.no_gate_check,
        mode=args.mode,
    )

    print("\n" + "=" * 70)
    print("HYDRA TRAINING RUNNER (Agent 2)")
    print("=" * 70)
    print(f"Matrix: {runner.matrix_path}")
    print(f"Output: {runner.output_dir}")
    print(f"Mode: {args.mode}")
    print(f"Gate check: {not args.no_gate_check}")
    print("=" * 70 + "\n")

    # Run training
    try:
        metrics = runner.run()

        if "error" in metrics:
            print(f"\nERROR: {metrics['error']}")
            if "reason" in metrics:
                print(f"Reason: {metrics['reason']}")
            sys.exit(1)

        print("\nTraining completed successfully!")
        print(f"Sharpe: {metrics['sharpe']:.2f}")
        print(f"Win Rate: {metrics['win_rate']:.1%}")
        print(f"Profit: ${metrics['profit']:.0f}")
        print(f"Trades: {metrics['n_trades']}")

    except Exception as e:
        print(f"\nFATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
