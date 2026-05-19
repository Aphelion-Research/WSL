"""Feature store: compute, version, and track IC."""
import numpy as np
import pandas as pd
import duckdb
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional

from data_pipeline.config import DUCKDB_PATH, IC_WINDOW
from data_pipeline.features import price, microstructure, crossasset, cot_features, macro, regime, calendar


class FeatureStore:
    """Centralized feature computation and storage."""

    def __init__(self, db_path: Path = DUCKDB_PATH):
        self.db_path = db_path
        self.version = 1

    def compute_all_features(
        self,
        gold_df: pd.DataFrame,
        macro_df: pd.DataFrame,
        cot_df: pd.DataFrame,
    ) -> pd.DataFrame:
        """Compute all 400+ features.

        Args:
            gold_df: Gold price dataframe
            macro_df: Macro data
            cot_df: COT data

        Returns:
            DataFrame with all features
        """
        all_features = []

        # Price features (~80)
        all_features.append(price.compute_all_price_features(gold_df))

        # Microstructure features (~60)
        all_features.append(microstructure.compute_all_microstructure_features(gold_df))

        # Cross-asset features (~100)
        all_features.append(crossasset.compute_all_crossasset_features(gold_df, macro_df))

        # COT features (~30)
        # Merge COT with gold index (sort, reindex, forward fill)
        cot_indexed = cot_df.set_index("report_date").sort_index()
        cot_aligned = cot_indexed.reindex(gold_df.index).ffill()
        if not cot_aligned.empty:
            all_features.append(cot_features.compute_all_cot_features(cot_aligned))

        # Macro features (~60)
        all_features.append(macro.compute_all_macro_features(gold_df, macro_df))

        # Regime features (~40)
        all_features.append(regime.compute_all_regime_features(gold_df))

        # Calendar features (~30)
        all_features.append(calendar.compute_all_calendar_features(gold_df.index))

        # Concatenate all
        result = pd.concat(all_features, axis=1)

        return result

    def validate_features(self, features_df: pd.DataFrame) -> pd.DataFrame:
        """Validate features: remove NaN/inf, clip extreme values."""
        # Replace inf with NaN
        features_df = features_df.replace([np.inf, -np.inf], np.nan)

        # Clip extreme values (beyond 100 std)
        for col in features_df.columns:
            if features_df[col].dtype in [np.float64, np.float32]:
                mean = features_df[col].mean()
                std = features_df[col].std()
                if std > 0:
                    features_df[col] = features_df[col].clip(mean - 100 * std, mean + 100 * std)

        return features_df

    def compute_ic(self, features_df: pd.DataFrame, returns: pd.Series, window: int = IC_WINDOW) -> Dict[str, float]:
        """Compute Information Coefficient (IC) for each feature.

        IC = correlation of feature_value with next-bar return.
        """
        ic_dict = {}

        next_return = returns.shift(-1)  # Next bar return

        for col in features_df.columns:
            if col in ["regime_tactical", "regime_micro"]:
                # Skip categorical features
                continue

            # Rolling IC
            rolling_corr = features_df[col].rolling(window).corr(next_return)
            current_ic = rolling_corr.iloc[-1] if len(rolling_corr) > 0 else np.nan

            ic_dict[col] = current_ic if not np.isnan(current_ic) else 0.0

        return ic_dict

    def store_features(
        self,
        features_df: pd.DataFrame,
        ic_dict: Optional[Dict[str, float]] = None
    ) -> None:
        """Store features in DuckDB."""
        conn = duckdb.connect(str(self.db_path))

        for col in features_df.columns:
            if col in ["regime_tactical", "regime_micro"]:
                # Skip categorical for now
                continue

            feature_data = []
            for idx, value in features_df[col].items():
                if pd.notna(value):
                    feature_data.append({
                        "timestamp": idx,
                        "feature_name": col,
                        "feature_value": float(value),
                        "feature_version": self.version,
                        "ic_252": ic_dict.get(col, 0.0) if ic_dict else 0.0,
                        "ic_updated_at": datetime.now(),
                    })

            if feature_data:
                df = pd.DataFrame(feature_data)
                conn.execute("""
                    INSERT OR REPLACE INTO features
                    SELECT * FROM df
                """)

        conn.close()

    def get_feature_importance(self, top_n: int = 20) -> pd.DataFrame:
        """Get top N features by IC."""
        conn = duckdb.connect(str(self.db_path))

        query = f"""
            SELECT feature_name, AVG(ic_252) as avg_ic
            FROM features
            WHERE ic_updated_at IS NOT NULL
            GROUP BY feature_name
            ORDER BY ABS(avg_ic) DESC
            LIMIT {top_n}
        """

        result = conn.execute(query).fetchdf()
        conn.close()

        return result

    def flag_poor_features(self, threshold: float = 0.01) -> pd.DataFrame:
        """Flag features with |IC| < threshold."""
        conn = duckdb.connect(str(self.db_path))

        query = f"""
            SELECT feature_name, AVG(ic_252) as avg_ic
            FROM features
            WHERE ic_updated_at IS NOT NULL
            GROUP BY feature_name
            HAVING ABS(AVG(ic_252)) < {threshold}
            ORDER BY ABS(avg_ic)
        """

        result = conn.execute(query).fetchdf()
        conn.close()

        return result

    def promote_high_ic_features(self, threshold: float = 0.05) -> pd.DataFrame:
        """Promote features with |IC| > threshold."""
        conn = duckdb.connect(str(self.db_path))

        query = f"""
            SELECT feature_name, AVG(ic_252) as avg_ic
            FROM features
            WHERE ic_updated_at IS NOT NULL
            GROUP BY feature_name
            HAVING ABS(AVG(ic_252)) > {threshold}
            ORDER BY ABS(avg_ic) DESC
        """

        result = conn.execute(query).fetchdf()
        conn.close()

        return result
