"""CLI for causal discovery engine."""
import sys
import argparse
import uuid
import duckdb
import pandas as pd
from datetime import datetime

from causal_engine.config import DUCKDB_PATH, PC_ALPHA, PC_TOP_N_FEATURES, TE_TOP_N_PAIRS
from causal_engine.pc_algorithm import pc_algorithm, extract_causal_paths
from causal_engine.dag import (
    init_dag_schema,
    store_dag,
    query_causal_predecessors,
    export_dag_to_json,
    send_dag_to_ragd,
    visualize_dag_ascii
)
from causal_engine.information import (
    compute_all_transfer_entropies,
    compute_mutual_information_scores
)


def cmd_run(args):
    """Run PC algorithm + transfer entropy computation."""
    print(f"Running causal discovery (alpha={PC_ALPHA}, top_n={PC_TOP_N_FEATURES})...")

    # Initialize schema
    init_dag_schema(DUCKDB_PATH)

    # Load top features from DuckDB
    conn = duckdb.connect(str(DUCKDB_PATH))

    query = f"""
        SELECT feature_name, AVG(ic_252) as avg_ic
        FROM features
        WHERE ic_updated_at IS NOT NULL
        GROUP BY feature_name
        ORDER BY ABS(avg_ic) DESC
        LIMIT {PC_TOP_N_FEATURES}
    """

    top_features = conn.execute(query).fetchdf()

    if top_features.empty:
        print("ERROR: No features with IC scores found in DuckDB")
        conn.close()
        return 1

    feature_names = top_features["feature_name"].tolist()
    print(f"Selected {len(feature_names)} features for causal discovery")

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
        print("ERROR: No feature data found")
        return 1

    # Combine into feature matrix
    feature_matrix = pd.concat(feature_data, axis=1)
    feature_matrix.columns = feature_names[:len(feature_data)]

    # Drop NaN
    feature_matrix = feature_matrix.dropna()

    print(f"Feature matrix: {feature_matrix.shape}")

    # Run PC algorithm
    print("Running PC algorithm...")
    adj_matrix, edge_info = pc_algorithm(feature_matrix, alpha=PC_ALPHA)

    n_edges = int(adj_matrix.sum() / 2)
    print(f"Discovered {n_edges} edges")

    # Store DAG
    run_id = f"causal_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    store_dag(adj_matrix, feature_matrix.columns.tolist(), edge_info, run_id, PC_ALPHA, DUCKDB_PATH)
    print(f"Stored DAG with run_id={run_id}")

    # Export to RAGD
    dag_json = export_dag_to_json(run_id, DUCKDB_PATH)
    if send_dag_to_ragd(dag_json):
        print("DAG sent to RAGD")

    # Compute transfer entropy
    print(f"Computing transfer entropy for top {TE_TOP_N_PAIRS} pairs...")
    te_results = compute_all_transfer_entropies(feature_matrix, TE_TOP_N_PAIRS)

    print("\nTop 5 Transfer Entropy Results:")
    print(te_results.sort_values("te_net", ascending=False).head())

    # Visualize
    print("\n" + visualize_dag_ascii(adj_matrix, feature_matrix.columns.tolist()))

    return 0


def cmd_show(args):
    """Show causal paths to gold."""
    target = args.target

    print(f"Causal predecessors of {target}:")
    print("=" * 60)

    predecessors = query_causal_predecessors(target, min_confidence=0.5, db_path=DUCKDB_PATH)

    if predecessors.empty:
        print("No causal DAG found. Run 'causal_engine.cli run' first.")
        return 1

    print(predecessors)

    return 0


def cmd_export(args):
    """Export DAG to JSON."""
    conn = duckdb.connect(str(DUCKDB_PATH))

    # Get latest run
    query = """
        SELECT run_id FROM causal_dag_runs
        ORDER BY computed_at DESC LIMIT 1
    """
    result = conn.execute(query).fetchone()
    conn.close()

    if not result:
        print("No causal DAG found")
        return 1

    run_id = result[0]

    dag_json = export_dag_to_json(run_id, DUCKDB_PATH)

    print(f"Exporting run_id={run_id}")

    import json
    print(json.dumps(dag_json, indent=2))

    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Causal Discovery Engine for Dominion"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # run command
    run_parser = subparsers.add_parser("run", help="Run PC algorithm + transfer entropy")
    run_parser.set_defaults(func=cmd_run)

    # show command
    show_parser = subparsers.add_parser("show", help="Show causal paths to target")
    show_parser.add_argument("--target", type=str, default="return_5", help="Target feature")
    show_parser.set_defaults(func=cmd_show)

    # export command
    export_parser = subparsers.add_parser("export", help="Export DAG to JSON")
    export_parser.set_defaults(func=cmd_export)

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
