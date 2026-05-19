"""Feature computation and storage orchestrator."""
import pandas as pd
import duckdb
from pathlib import Path
from exec_features.spread_features import compute_spread_features
from exec_features.depth_features import compute_depth_features
from exec_features.flow_features import compute_flow_features
from exec_features.quote_features import compute_quote_features
from exec_features.trade_features import compute_trade_features


def compute_all_features(df: pd.DataFrame, ofi_df: pd.DataFrame = None) -> pd.DataFrame:
    """Compute all 50 execution features.

    Args:
        df: Input DataFrame with market data
        ofi_df: Optional pre-computed OFI data

    Returns:
        DataFrame with all features
    """
    if ofi_df is None:
        ofi_df = pd.DataFrame()

    # Compute feature groups
    spread_feats = compute_spread_features(df)
    depth_feats = compute_depth_features(df)
    flow_feats = compute_flow_features(df, ofi_df)
    quote_feats = compute_quote_features(df)
    trade_feats = compute_trade_features(df)

    # Concatenate
    all_features = pd.concat([
        df[['timestamp']],
        spread_feats,
        depth_feats,
        flow_feats,
        quote_feats,
        trade_feats
    ], axis=1)

    return all_features


def store_features(features_df: pd.DataFrame, db_path: Path) -> int:
    """Store features to DuckDB.

    Args:
        features_df: Features DataFrame
        db_path: DuckDB path

    Returns:
        Number of rows stored
    """
    conn = duckdb.connect(str(db_path))

    # Clear existing
    conn.execute("DELETE FROM execution_features")

    # Melt to long format (timestamp, feature_name, feature_value)
    melted = features_df.melt(id_vars=['timestamp'], var_name='feature_name', value_name='feature_value')
    melted['ic_60'] = 0.0  # placeholder
    melted['ic_updated_at'] = None
    melted['regime'] = None

    # Insert
    conn.execute("""
        INSERT INTO execution_features (timestamp, feature_name, feature_value, ic_60, ic_updated_at, regime)
        SELECT * FROM melted
    """, {"melted": melted})

    rows = conn.execute("SELECT COUNT(*) FROM execution_features").fetchone()[0]
    conn.close()

    return rows
