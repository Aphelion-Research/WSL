#!/usr/bin/env python
"""Build HYDRA 3,000-column training matrix."""
import sys
from pathlib import Path

from dominion.matrix.builder import build_hydra_matrix
from dominion.quality.gates import run_all_gates, print_gate_report


def main():
    """Build matrix and run quality gates."""
    print("="*60)
    print("HYDRA 3,000-COLUMN MATRIX BUILDER")
    print("="*60)

    # Build matrix (full 50K rows)
    matrix = build_hydra_matrix(
        h1_data_path="/home/Martin/Dominion/data/mt5_history/XAUUSD_H1.parquet",
        output_path="/home/Martin/Dominion/data/hydra_matrix.parquet",
        max_rows=None  # Full dataset
    )

    print(f"\n✓ Matrix built: {matrix.height:,} rows x {matrix.width:,} columns")

    # Run quality gates
    training_allowed, results = run_all_gates(matrix)

    print_gate_report(results)

    # Save verdict
    verdict_path = Path("/home/Martin/Dominion/data/training_verdict.txt")
    with open(verdict_path, "w") as f:
        f.write("TRAINING_ALLOWED=true\n" if training_allowed else "TRAINING_ALLOWED=false\n")
        f.write(f"MATRIX_ROWS={matrix.height}\n")
        f.write(f"MATRIX_COLS={matrix.width}\n")
        f.write(f"TRAINABLE_FEATURES={len([c for c in matrix.columns if not c.startswith('Z4_') and c != 'time' and matrix[c].is_null().sum() / matrix.height < 0.95])}\n")

    print(f"\n✓ Verdict saved to {verdict_path}")

    return 0 if training_allowed else 1


if __name__ == "__main__":
    sys.exit(main())
