"""CLI for reservoir computing."""
import sys
import argparse
import duckdb
import numpy as np
import pandas as pd

from reservoir.config import DUCKDB_PATH, TOP_N_FEATURES_ESN
from reservoir.esn import MultiScaleESN
from reservoir.readout import RidgeReadout, train_test_split_esn, evaluate_readout


def cmd_train(args):
    """Train ESN on features."""
    print(f"Training ESN (top {TOP_N_FEATURES_ESN} features)...")

    # Load features
    conn = duckdb.connect(str(DUCKDB_PATH))

    # Get top features
    query = f"""
        SELECT feature_name FROM (
            SELECT feature_name, AVG(ic_252) as avg_ic
            FROM features
            WHERE ic_updated_at IS NOT NULL
            GROUP BY feature_name
            ORDER BY ABS(avg_ic) DESC
            LIMIT {TOP_N_FEATURES_ESN}
        )
    """
    top_features = conn.execute(query).fetchdf()

    if top_features.empty:
        print("ERROR: No features found")
        conn.close()
        return 1

    feature_names = top_features["feature_name"].tolist()

    # Load feature matrix
    feature_data = []
    for fname in feature_names:
        query = f"""
            SELECT timestamp, feature_value
            FROM features
            WHERE feature_name = '{fname}'
            ORDER BY timestamp
        """
        df = conn.execute(query).fetchdf()
        if not df.empty:
            feature_data.append(df.set_index("timestamp")["feature_value"])

    conn.close()

    if not feature_data:
        print("ERROR: No feature data")
        return 1

    # Combine + normalize
    X = pd.concat(feature_data, axis=1).dropna()
    X_normalized = (X - X.mean()) / (X.std() + 1e-8)

    # Target: next-bar return (approximated)
    y = X_normalized.iloc[:, 0].shift(-1).dropna()
    X_normalized = X_normalized.iloc[:-1]

    print(f"Data shape: {X_normalized.shape}")

    # Run ESN
    print("Running ESN...")
    esn = MultiScaleESN(n_inputs=X_normalized.shape[1])
    states = esn.run(X_normalized.values)

    # Train readout
    print("Training readout...")
    X_train, X_test, y_train, y_test = train_test_split_esn(states, y.values)

    readout = RidgeReadout()
    readout.fit(X_train, y_train)

    # Evaluate
    metrics = evaluate_readout(readout, X_test, y_test)

    print("\nResults:")
    print(f"  R²: {metrics['r2']:.4f}")
    print(f"  RMSE: {metrics['rmse']:.4f}")
    print(f"  Directional Accuracy: {metrics['directional_accuracy']:.2%}")
    print(f"  Best alpha: {metrics['best_alpha']}")

    return 0


def main():
    parser = argparse.ArgumentParser(description="Reservoir Computing CLI")

    subparsers = parser.add_subparsers(dest="command")

    train_parser = subparsers.add_parser("train", help="Train ESN")
    train_parser.set_defaults(func=cmd_train)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    try:
        return args.func(args)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
