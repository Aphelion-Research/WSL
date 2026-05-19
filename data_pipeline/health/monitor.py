"""Pipeline health monitoring."""
import numpy as np
import pandas as pd
import duckdb
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from scipy.stats import entropy

from data_pipeline.config import DUCKDB_PATH, STALENESS_THRESHOLDS, DRIFT_KL_THRESHOLD


class PipelineMonitor:
    """Monitor pipeline health: staleness, gaps, drift."""

    def __init__(self, db_path: Path = DUCKDB_PATH):
        self.db_path = db_path

    def check_staleness(self) -> Dict[str, Dict]:
        """Check if each source is stale."""
        conn = duckdb.connect(str(self.db_path))

        query = """
            SELECT source, last_fetch, status
            FROM source_health
        """

        result = conn.execute(query).fetchdf()
        conn.close()

        staleness_report = {}
        now = datetime.now()

        for _, row in result.iterrows():
            source = row["source"]
            last_fetch = row["last_fetch"]

            if pd.notna(last_fetch):
                age_seconds = (now - last_fetch).total_seconds()
                threshold = STALENESS_THRESHOLDS.get(source, 24 * 3600)

                is_stale = age_seconds > threshold

                staleness_report[source] = {
                    "last_fetch": last_fetch,
                    "age_seconds": age_seconds,
                    "threshold": threshold,
                    "is_stale": is_stale,
                    "status": "STALE" if is_stale else "OK",
                }
            else:
                staleness_report[source] = {
                    "last_fetch": None,
                    "age_seconds": None,
                    "threshold": STALENESS_THRESHOLDS.get(source, 24 * 3600),
                    "is_stale": True,
                    "status": "NEVER_FETCHED",
                }

        return staleness_report

    def detect_gaps(self, table: str = "gold_master", max_gap_bars: int = 5) -> List[Tuple[datetime, datetime]]:
        """Detect gaps in timeseries data."""
        conn = duckdb.connect(str(self.db_path))

        query = f"""
            SELECT timestamp
            FROM {table}
            ORDER BY timestamp
        """

        result = conn.execute(query).fetchdf()
        conn.close()

        if result.empty:
            return []

        timestamps = pd.to_datetime(result["timestamp"])
        gaps = []

        for i in range(1, len(timestamps)):
            prev_ts = timestamps.iloc[i - 1]
            curr_ts = timestamps.iloc[i]

            # Assume 1-minute bars
            expected_bars = (curr_ts - prev_ts).total_seconds() / 60

            if expected_bars > max_gap_bars:
                gaps.append((prev_ts, curr_ts))

        return gaps

    def fill_small_gaps(self, table: str = "gold_master", max_gap_bars: int = 5) -> int:
        """Fill small gaps using Brownian bridge interpolation."""
        gaps = self.detect_gaps(table, max_gap_bars)

        if not gaps:
            return 0

        conn = duckdb.connect(str(self.db_path))

        filled_count = 0

        for start_ts, end_ts in gaps:
            # Get bounding prices
            query_start = f"""
                SELECT fused_price
                FROM {table}
                WHERE timestamp = '{start_ts}'
            """
            query_end = f"""
                SELECT fused_price
                FROM {table}
                WHERE timestamp = '{end_ts}'
            """

            start_price = conn.execute(query_start).fetchone()
            end_price = conn.execute(query_end).fetchone()

            if start_price and end_price:
                start_price = start_price[0]
                end_price = end_price[0]

                # Interpolate linearly (simple bridge)
                n_bars = int((end_ts - start_ts).total_seconds() / 60) - 1

                if n_bars > 0 and n_bars <= max_gap_bars:
                    for i in range(1, n_bars + 1):
                        interp_ts = start_ts + timedelta(minutes=i)
                        interp_price = start_price + (end_price - start_price) * (i / (n_bars + 1))

                        # Insert into table
                        insert_query = f"""
                            INSERT OR IGNORE INTO {table} (timestamp, fused_price, fused_confidence, anomaly_flag)
                            VALUES ('{interp_ts}', {interp_price}, 0.1, FALSE)
                        """
                        conn.execute(insert_query)
                        filled_count += 1

        conn.close()

        return filled_count

    def detect_distribution_drift(self, feature_name: str, window: int = 252) -> Tuple[bool, float]:
        """Detect distribution drift via KL divergence."""
        conn = duckdb.connect(str(self.db_path))

        query = f"""
            SELECT feature_value
            FROM features
            WHERE feature_name = '{feature_name}'
            ORDER BY timestamp DESC
            LIMIT {window * 2}
        """

        result = conn.execute(query).fetchdf()
        conn.close()

        if len(result) < window * 2:
            return False, 0.0

        # Split into recent and baseline
        recent = result["feature_value"].iloc[:window].values
        baseline = result["feature_value"].iloc[window:].values

        # Compute histograms
        bins = 50
        hist_recent, _ = np.histogram(recent, bins=bins, density=True)
        hist_baseline, _ = np.histogram(baseline, bins=bins, density=True)

        # Add small epsilon to avoid log(0)
        hist_recent += 1e-10
        hist_baseline += 1e-10

        # Normalize
        hist_recent /= hist_recent.sum()
        hist_baseline /= hist_baseline.sum()

        # KL divergence
        kl = entropy(hist_recent, hist_baseline)

        is_drifting = kl > DRIFT_KL_THRESHOLD

        return is_drifting, kl

    def monitor_gold_dxy_correlation(self, window: int = 20) -> Tuple[bool, float]:
        """Monitor gold-DXY correlation for sign inversion."""
        conn = duckdb.connect(str(self.db_path))

        # Get gold prices
        gold_query = """
            SELECT timestamp, fused_price
            FROM gold_master
            ORDER BY timestamp DESC
            LIMIT 252
        """
        gold_df = conn.execute(gold_query).fetchdf()

        # Get DXY
        dxy_query = """
            SELECT timestamp, value
            FROM macro_data
            WHERE series_id = 'DTWEXBGS'
            ORDER BY timestamp DESC
            LIMIT 252
        """
        dxy_df = conn.execute(dxy_query).fetchdf()

        conn.close()

        if gold_df.empty or dxy_df.empty:
            return False, 0.0

        # Merge
        merged = pd.merge(gold_df, dxy_df, on="timestamp", how="inner")

        if len(merged) < window:
            return False, 0.0

        # Compute rolling correlation
        corr = merged["fused_price"].rolling(window).corr(merged["value"])

        if len(corr) < window:
            return False, 0.0

        recent_corr = corr.iloc[-window:]

        # Check for sign inversion (5+ days)
        if (recent_corr > 0).sum() >= 5:
            # Normally gold-DXY is negative, positive is anomaly
            return True, recent_corr.mean()

        return False, recent_corr.mean()

    def get_health_summary(self) -> Dict:
        """Get overall pipeline health summary."""
        staleness = self.check_staleness()
        gaps = self.detect_gaps()

        stale_sources = [s for s, info in staleness.items() if info["is_stale"]]

        summary = {
            "timestamp": datetime.now(),
            "staleness": staleness,
            "stale_sources": stale_sources,
            "gap_count": len(gaps),
            "gaps": gaps[:10],  # Top 10 gaps
            "overall_status": "OK" if not stale_sources and len(gaps) == 0 else "WARN",
        }

        return summary
