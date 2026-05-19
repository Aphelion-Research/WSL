"""Main pipeline orchestrator."""
import asyncio
import uuid
import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict
import pandas as pd
import duckdb

from data_pipeline.config import DUCKDB_PATH
from data_pipeline.schema import init_schema
from data_pipeline.sources import yahoo, fred, alphavantage, cot, domdata
from data_pipeline.fusion.kalman import KalmanFilterBank
from data_pipeline.fusion.bridge import reconstruct_ticks_from_bars
from data_pipeline.features.store import FeatureStore
from data_pipeline.health.monitor import PipelineMonitor
from data_pipeline.health.anomaly import AnomalyDetector
from data_pipeline.health.report import ReportGenerator


class Pipeline:
    """Main pipeline orchestrator."""

    def __init__(self, db_path: Path = DUCKDB_PATH):
        self.db_path = db_path
        self.run_id = str(uuid.uuid4())[:8]
        self.started_at = datetime.now()

        # Initialize components
        self.sources = {
            "yahoo": yahoo.YahooSource(),
            "fred": fred.FREDSource(),
            "alphavantage": alphavantage.AlphaVantageSource(),
            "cot": cot.COTSource(),
            "mt5": domdata.DomdataSource(),
        }

        self.kalman_bank = KalmanFilterBank()
        self.feature_store = FeatureStore(db_path)
        self.monitor = PipelineMonitor(db_path)
        self.anomaly_detector = AnomalyDetector(db_path)
        self.report_gen = ReportGenerator(db_path)

        self.errors: List[str] = []

    def init_db(self) -> None:
        """Initialize database schema."""
        init_schema(self.db_path)

    def log_run_start(self) -> None:
        """Log pipeline run start."""
        conn = duckdb.connect(str(self.db_path))

        insert_query = """
            INSERT INTO pipeline_runs (run_id, started_at, status)
            VALUES (?, ?, 'running')
        """

        conn.execute(insert_query, [self.run_id, self.started_at])
        conn.close()

    def log_run_complete(self, sources_fetched: int, features_computed: int) -> None:
        """Log pipeline run completion."""
        conn = duckdb.connect(str(self.db_path))

        update_query = """
            UPDATE pipeline_runs
            SET completed_at = ?,
                status = ?,
                sources_fetched = ?,
                features_computed = ?,
                errors_json = ?
            WHERE run_id = ?
        """

        status = "completed" if not self.errors else "completed_with_errors"
        errors_json = json.dumps(self.errors)

        conn.execute(update_query, [
            datetime.now(),
            status,
            sources_fetched,
            features_computed,
            errors_json,
            self.run_id
        ])

        conn.close()

    def fetch_sources(self, source_names: Optional[List[str]] = None) -> Dict[str, pd.DataFrame]:
        """Fetch data from all sources (parallel)."""
        if source_names is None:
            source_names = list(self.sources.keys())

        results = {}

        for name in source_names:
            if name not in self.sources:
                self.errors.append(f"Unknown source: {name}")
                continue

            source = self.sources[name]
            print(f"Fetching {name}...")

            try:
                df = source.fetch()
                results[name] = df

                # Update source health
                self.update_source_health(name, "OK", 0, source.error_count, source.trust_score)

            except Exception as e:
                error_msg = f"Failed to fetch {name}: {e}"
                self.errors.append(error_msg)
                print(f"ERROR: {error_msg}")

                # Update source health
                self.update_source_health(name, "FAILED", 0, source.error_count + 1, 0.0)

        return results

    def update_source_health(
        self,
        source: str,
        status: str,
        latency_ms: float,
        error_count: int,
        trust_score: float
    ) -> None:
        """Update source health in DuckDB."""
        conn = duckdb.connect(str(self.db_path))

        insert_query = """
            INSERT OR REPLACE INTO source_health
            (source, last_fetch, status, latency_ms, error_count, trust_score)
            VALUES (?, ?, ?, ?, ?, ?)
        """

        conn.execute(insert_query, [
            source,
            datetime.now(),
            status,
            latency_ms,
            error_count,
            trust_score
        ])

        conn.close()

    def store_raw_data(self, source_name: str, df: pd.DataFrame) -> None:
        """Store raw data in gold_raw table."""
        if df.empty:
            return

        conn = duckdb.connect(str(self.db_path))

        df_copy = df.copy()
        df_copy["source"] = source_name
        df_copy["fetch_time"] = datetime.now()
        df_copy["quality_score"] = 1.0  # Default quality

        # Insert into gold_raw
        conn.execute("""
            INSERT OR REPLACE INTO gold_raw
            SELECT source, timestamp, open, high, low, close, volume, fetch_time, quality_score
            FROM df_copy
        """)

        conn.close()

    def fuse_prices(self, raw_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """Fuse prices via Kalman filter bank."""
        print("Fusing prices via Kalman filter bank...")

        # Combine all gold sources
        gold_sources = ["yahoo", "alphavantage", "mt5"]
        all_gold = []

        for source in gold_sources:
            if source in raw_data and not raw_data[source].empty:
                df = raw_data[source].copy()
                df["source"] = source
                all_gold.append(df)

        if not all_gold:
            raise RuntimeError("No gold data to fuse")

        combined = pd.concat(all_gold, ignore_index=True)

        # Group by timestamp and fuse
        fused_data = []

        for ts, group in combined.groupby("timestamp"):
            observations = {row["source"]: row["close"] for _, row in group.iterrows()}

            fused_price, confidence, source_weights, anomaly_flag = self.kalman_bank.fuse(
                observations, ts
            )

            fused_data.append({
                "timestamp": ts,
                "fused_price": fused_price,
                "fused_confidence": confidence,
                "source_weights_json": json.dumps(source_weights),
                "anomaly_flag": anomaly_flag,
            })

        fused_df = pd.DataFrame(fused_data)

        # Store in gold_master
        conn = duckdb.connect(str(self.db_path))
        conn.execute("""
            INSERT OR REPLACE INTO gold_master
            SELECT timestamp, fused_price, fused_confidence, source_weights_json, anomaly_flag, NULL as regime
            FROM fused_df
        """)
        conn.close()

        return fused_df

    def reconstruct_ticks(self, fused_df: pd.DataFrame) -> None:
        """Reconstruct synthetic ticks."""
        print("Reconstructing ticks via Brownian bridge...")

        # Need OHLCV, but we only have fused price
        # Use first available raw source for OHLC structure
        conn = duckdb.connect(str(self.db_path))

        query = """
            SELECT timestamp, open, high, low, close
            FROM gold_raw
            WHERE source = 'yahoo'
            ORDER BY timestamp
        """

        ohlc_df = conn.execute(query).fetchdf()
        conn.close()

        if ohlc_df.empty:
            print("WARNING: No OHLC data for tick reconstruction")
            return

        # Reconstruct ticks (sample first 100 bars to save time)
        ticks_df = reconstruct_ticks_from_bars(ohlc_df.head(100), n_ticks=10)

        # Store in gold_ticks
        conn = duckdb.connect(str(self.db_path))
        conn.execute("""
            INSERT OR REPLACE INTO gold_ticks
            SELECT timestamp, bar_timestamp, tick_price, confidence
            FROM ticks_df
        """)
        conn.close()

    def store_macro_data(self, macro_df: pd.DataFrame) -> None:
        """Store macro data in DuckDB."""
        if macro_df.empty:
            return

        conn = duckdb.connect(str(self.db_path))
        conn.execute("""
            INSERT OR REPLACE INTO macro_data
            SELECT series_id, timestamp, value, series_name
            FROM macro_df
        """)
        conn.close()

    def store_cot_data(self, cot_df: pd.DataFrame) -> None:
        """Store COT data in DuckDB."""
        if cot_df.empty:
            return

        conn = duckdb.connect(str(self.db_path))
        conn.execute("""
            INSERT OR REPLACE INTO cot_data
            SELECT report_date, commercial_long, commercial_short,
                   noncommercial_long, noncommercial_short, open_interest,
                   net_commercial, speculator_sentiment
            FROM cot_df
        """)
        conn.close()

    def compute_features(self, gold_df: pd.DataFrame, macro_df: pd.DataFrame, cot_df: pd.DataFrame) -> int:
        """Compute all features."""
        print("Computing 400+ features...")

        features = self.feature_store.compute_all_features(gold_df, macro_df, cot_df)
        features = self.feature_store.validate_features(features)

        # Compute IC
        returns = gold_df["close"].pct_change()
        ic_dict = self.feature_store.compute_ic(features, returns)

        # Store features
        self.feature_store.store_features(features, ic_dict)

        # Store regime labels
        from data_pipeline.features.regime_storage import store_regime_labels
        regime_cols = [c for c in features.columns if 'regime' in c]
        if regime_cols:
            regime_df = features[regime_cols]
            store_regime_labels(regime_df)

        return len(features.columns)

    def run_health_checks(self) -> None:
        """Run health checks."""
        print("Running health checks...")

        # Staleness check
        staleness = self.monitor.check_staleness()
        for source, info in staleness.items():
            if info["is_stale"]:
                print(f"WARNING: {source} is stale")

        # Gap detection and filling
        gaps = self.monitor.detect_gaps()
        print(f"Found {len(gaps)} gaps")

        if gaps and len(gaps) <= 10:
            filled = self.monitor.fill_small_gaps()
            print(f"Filled {filled} small gaps")

    def generate_report(self) -> None:
        """Generate intelligence report."""
        print("Generating intelligence report...")

        report_text, filepath = self.report_gen.generate_and_store(self.run_id)

        print(f"Report written to {filepath}")

    def run(self, source_names: Optional[List[str]] = None) -> None:
        """Run full pipeline."""
        print(f"Starting pipeline run {self.run_id} at {self.started_at}")

        self.init_db()
        self.log_run_start()

        try:
            # Phase 1: Fetch sources
            raw_data = self.fetch_sources(source_names)
            sources_fetched = len(raw_data)

            # Store raw data
            for source_name, df in raw_data.items():
                if source_name in ["yahoo", "alphavantage", "mt5"]:
                    self.store_raw_data(source_name, df)
                elif source_name == "fred":
                    self.store_macro_data(df)
                elif source_name == "cot":
                    self.store_cot_data(df)

            # Phase 2: Fuse prices
            fused_df = self.fuse_prices(raw_data)

            # Phase 3: Reconstruct ticks
            self.reconstruct_ticks(fused_df)

            # Phase 4: Compute features
            conn = duckdb.connect(str(self.db_path))
            gold_df = conn.execute("SELECT timestamp, fused_price as close FROM gold_master ORDER BY timestamp").fetchdf()
            macro_df = conn.execute("SELECT * FROM macro_data").fetchdf()
            cot_df = conn.execute("SELECT * FROM cot_data").fetchdf()
            conn.close()

            gold_df = gold_df.set_index("timestamp")

            features_computed = self.compute_features(gold_df, macro_df, cot_df)

            # Phase 5: Health checks
            self.run_health_checks()

            # Phase 6: Generate report
            self.generate_report()

            # Log completion
            self.log_run_complete(sources_fetched, features_computed)

            print(f"Pipeline run {self.run_id} completed successfully")

        except Exception as e:
            error_msg = f"Pipeline failed: {e}"
            self.errors.append(error_msg)
            print(f"ERROR: {error_msg}")
            self.log_run_complete(0, 0)
            raise
