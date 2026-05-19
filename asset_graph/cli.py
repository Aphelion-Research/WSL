"""CLI for asset graph."""
import sys
import argparse
import json
import numpy as np
import pandas as pd
import duckdb

from asset_graph.config import DUCKDB_PATH, ASSET_NODES
from asset_graph.graph import (
    init_graph_schema,
    build_correlation_graph,
    store_graph_snapshot,
    store_graph_metrics
)
from asset_graph.gat import SimpleGAT


def cmd_build(args):
    """Build current graph snapshot."""
    print("Building asset graph...")

    init_graph_schema(DUCKDB_PATH)

    # Load asset data from macro_data (simplified — real impl would map features to assets)
    conn = duckdb.connect(str(DUCKDB_PATH))

    # For demo: use macro series as proxies
    series_map = {
        "dxy": "DTWEXBGS",
        "vix": "VIXCLS",
        "tips_yield": "DFII10",
        "crude": "DCOILWTICO",
        "cpi": "CPIAUCSL",
        "fed_funds": "FEDFUNDS",
        "yield_spread": "T10Y2Y"
    }

    data_dict = {}

    for asset, series_id in series_map.items():
        query = f"""
            SELECT timestamp, value
            FROM macro_data
            WHERE series_id = '{series_id}'
            ORDER BY timestamp
        """
        df = conn.execute(query).fetchdf()
        if not df.empty:
            data_dict[asset] = df.set_index("timestamp")["value"]

    # Add gold from gold_master
    gold_query = """
        SELECT timestamp, fused_price
        FROM gold_master
        ORDER BY timestamp
    """
    gold_df = conn.execute(gold_query).fetchdf()
    if not gold_df.empty:
        data_dict["gold"] = gold_df.set_index("timestamp")["fused_price"]

    conn.close()

    if len(data_dict) < 2:
        print("ERROR: Insufficient asset data")
        return 1

    # Combine
    asset_data = pd.DataFrame(data_dict).dropna()

    print(f"Loaded {asset_data.shape[1]} assets, {asset_data.shape[0]} timestamps")

    # Build graph
    adj_matrix, edge_weights = build_correlation_graph(asset_data)

    n_edges = int(adj_matrix.sum() / 2)
    print(f"Graph: {n_edges} edges")

    # Store
    latest_ts = asset_data.index[-1]
    store_graph_snapshot(
        adj_matrix,
        asset_data.columns.tolist(),
        edge_weights,
        latest_ts,
        edge_type="correlation",
        window_bars=len(asset_data)
    )

    store_graph_metrics(
        adj_matrix,
        asset_data.columns.tolist(),
        edge_weights,
        latest_ts
    )

    print("Graph stored in DuckDB")

    return 0


def cmd_show(args):
    """Show graph metrics."""
    conn = duckdb.connect(str(DUCKDB_PATH))

    query = """
        SELECT * FROM graph_metrics
        ORDER BY timestamp DESC
        LIMIT 1
    """

    metrics = conn.execute(query).fetchdf()
    conn.close()

    if metrics.empty:
        print("No graph metrics found. Run 'build' first.")
        return 1

    print("GRAPH METRICS:")
    print("=" * 60)
    print(metrics.to_string(index=False))

    return 0


def main():
    parser = argparse.ArgumentParser(description="Asset Graph CLI")

    subparsers = parser.add_subparsers(dest="command")

    build_parser = subparsers.add_parser("build", help="Build graph snapshot")
    build_parser.set_defaults(func=cmd_build)

    show_parser = subparsers.add_parser("show", help="Show graph metrics")
    show_parser.set_defaults(func=cmd_show)

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
