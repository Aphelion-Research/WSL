"""Store regime labels to DuckDB."""
import duckdb
import pandas as pd
from pathlib import Path
from datetime import datetime

from data_pipeline.config import DUCKDB_PATH


def store_regime_labels(
    regime_df: pd.DataFrame,
    db_path: Path = DUCKDB_PATH
) -> None:
    """Store regime labels in regime_labels table.

    Args:
        regime_df: DataFrame with columns: regime_tactical, regime_micro, confidence
        db_path: Path to DuckDB database
    """
    conn = duckdb.connect(str(db_path))

    # Prepare data for insertion
    records = []
    for idx, row in regime_df.iterrows():
        records.append({
            'timestamp': idx,
            'macro_regime': None,  # Not computed yet
            'structural_regime': None,  # Not computed yet
            'tactical_regime': row.get('regime_tactical', 'unknown'),
            'micro_regime': row.get('regime_micro', 'unknown'),
            'confidence': row.get('regime_prob_trend_up', 0.0)  # Use max prob as confidence
        })

    if records:
        df = pd.DataFrame(records)
        conn.execute("""
            INSERT OR REPLACE INTO regime_labels
            SELECT timestamp, macro_regime, structural_regime, tactical_regime, micro_regime, confidence
            FROM df
        """)

        print(f"Stored {len(records)} regime labels")

    conn.close()


def get_latest_regime(db_path: Path = DUCKDB_PATH) -> dict:
    """Get latest regime from regime_labels table."""
    conn = duckdb.connect(str(db_path))

    query = """
        SELECT * FROM regime_labels
        ORDER BY timestamp DESC
        LIMIT 1
    """

    result = conn.execute(query).fetchdf()
    conn.close()

    if result.empty:
        return {}

    return result.iloc[0].to_dict()
