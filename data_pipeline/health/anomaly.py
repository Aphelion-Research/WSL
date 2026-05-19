"""Anomaly detection and quarantine logic."""
import numpy as np
import pandas as pd
import duckdb
from pathlib import Path
from datetime import datetime
from typing import Tuple, Optional

from data_pipeline.config import DUCKDB_PATH, ANOMALY_Z_SCORE_FLAG, ANOMALY_Z_SCORE_QUARANTINE


class AnomalyDetector:
    """Detect and quarantine anomalies."""

    def __init__(self, db_path: Path = DUCKDB_PATH):
        self.db_path = db_path

    def detect_price_anomaly(
        self,
        price: float,
        historical_prices: pd.Series,
        window: int = 252
    ) -> Tuple[bool, bool, float]:
        """Detect price anomaly via z-score.

        Returns:
            (is_flagged, is_quarantined, z_score)
        """
        if len(historical_prices) < window:
            return False, False, 0.0

        recent = historical_prices.tail(window)
        mean = recent.mean()
        std = recent.std()

        if std > 0:
            z_score = abs(price - mean) / std
        else:
            z_score = 0.0

        is_flagged = z_score > ANOMALY_Z_SCORE_FLAG
        is_quarantined = z_score > ANOMALY_Z_SCORE_QUARANTINE

        return is_flagged, is_quarantined, z_score

    def detect_volume_anomaly(
        self,
        volume: float,
        historical_volumes: pd.Series,
        threshold: float = 5.0
    ) -> Tuple[bool, float]:
        """Detect volume anomaly (potential news event).

        Returns:
            (is_anomaly, z_score)
        """
        if len(historical_volumes) < 20:
            return False, 0.0

        mean = historical_volumes.mean()
        std = historical_volumes.std()

        if std > 0:
            z_score = (volume - mean) / std
        else:
            z_score = 0.0

        is_anomaly = z_score > threshold

        return is_anomaly, z_score

    def detect_source_divergence(
        self,
        source_price: float,
        fused_price: float,
        fused_confidence: float,
        threshold_sigma: float = 2.0
    ) -> bool:
        """Detect if source diverges from fused price.

        Returns:
            True if divergence > threshold_sigma
        """
        if fused_confidence <= 0:
            return False

        sigma = np.sqrt(1.0 / fused_confidence)
        deviation = abs(source_price - fused_price)

        return deviation > threshold_sigma * sigma

    def log_anomaly(
        self,
        timestamp: datetime,
        anomaly_type: str,
        description: str,
        severity: str,
        source: Optional[str] = None,
        value: Optional[float] = None
    ) -> None:
        """Log anomaly to DuckDB."""
        conn = duckdb.connect(str(self.db_path))

        insert_query = """
            INSERT OR REPLACE INTO anomaly_log
            (timestamp, anomaly_type, description, severity, source, value)
            VALUES (?, ?, ?, ?, ?, ?)
        """

        conn.execute(insert_query, [
            timestamp,
            anomaly_type,
            description,
            severity,
            source or "unknown",
            value or 0.0
        ])

        conn.close()

    def get_recent_anomalies(self, hours: int = 24) -> pd.DataFrame:
        """Get anomalies from last N hours."""
        conn = duckdb.connect(str(self.db_path))

        cutoff = datetime.now() - pd.Timedelta(hours=hours)

        query = f"""
            SELECT *
            FROM anomaly_log
            WHERE timestamp >= '{cutoff}'
            ORDER BY timestamp DESC
        """

        result = conn.execute(query).fetchdf()
        conn.close()

        return result

    def quarantine_bar(
        self,
        timestamp: datetime,
        source: str,
        reason: str
    ) -> None:
        """Quarantine a bar (mark for human review)."""
        self.log_anomaly(
            timestamp=timestamp,
            anomaly_type="quarantine",
            description=f"Bar quarantined: {reason}",
            severity="CRITICAL",
            source=source
        )
