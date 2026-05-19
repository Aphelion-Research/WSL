"""Toxicity alerting logic."""
import uuid
import duckdb
import pandas as pd
from pathlib import Path
from typing import List, Dict
from toxicity.config import (
    VPIN_THRESHOLD_HIGH,
    OFI_SIGMA_THRESHOLD,
    ADVERSE_SELECTION_THRESHOLD_BPS,
    TOXICITY_SCORE_THRESHOLD
)


def generate_alerts(metrics: pd.DataFrame, db_path: Path) -> List[Dict]:
    """Generate toxicity alerts based on thresholds.

    Args:
        metrics: DataFrame with toxicity metrics
        db_path: DuckDB path

    Returns:
        List of alert dicts
    """
    alerts = []

    for _, row in metrics.iterrows():
        timestamp = row['timestamp']

        # VPIN alert
        if row['vpin'] > VPIN_THRESHOLD_HIGH:
            alerts.append({
                'alert_id': str(uuid.uuid4())[:8],
                'timestamp': timestamp,
                'alert_type': 'vpin_spike',
                'severity': 'HIGH',
                'metric_value': row['vpin'],
                'threshold': VPIN_THRESHOLD_HIGH,
                'description': f"VPIN={row['vpin']:.3f} exceeds threshold {VPIN_THRESHOLD_HIGH}"
            })

        # OFI extreme alert
        if abs(row['ofi_1m']) > OFI_SIGMA_THRESHOLD:
            alerts.append({
                'alert_id': str(uuid.uuid4())[:8],
                'timestamp': timestamp,
                'alert_type': 'ofi_extreme',
                'severity': 'MEDIUM',
                'metric_value': row['ofi_1m'],
                'threshold': OFI_SIGMA_THRESHOLD,
                'description': f"OFI 1m={row['ofi_1m']:.2f} exceeds {OFI_SIGMA_THRESHOLD}σ"
            })

        # Adverse selection alert
        if row['adverse_selection_bps'] > ADVERSE_SELECTION_THRESHOLD_BPS:
            alerts.append({
                'alert_id': str(uuid.uuid4())[:8],
                'timestamp': timestamp,
                'alert_type': 'adverse_selection',
                'severity': 'HIGH',
                'metric_value': row['adverse_selection_bps'],
                'threshold': ADVERSE_SELECTION_THRESHOLD_BPS,
                'description': f"Adverse selection={row['adverse_selection_bps']:.2f} bps exceeds {ADVERSE_SELECTION_THRESHOLD_BPS}"
            })

        # Toxicity score alert
        if row['toxicity_score'] > TOXICITY_SCORE_THRESHOLD:
            alerts.append({
                'alert_id': str(uuid.uuid4())[:8],
                'timestamp': timestamp,
                'alert_type': 'toxic_flow_warning',
                'severity': 'CRITICAL',
                'metric_value': row['toxicity_score'],
                'threshold': TOXICITY_SCORE_THRESHOLD,
                'description': f"Toxicity score={row['toxicity_score']:.3f} exceeds {TOXICITY_SCORE_THRESHOLD}"
            })

    return alerts


def store_alerts(alerts: List[Dict], db_path: Path) -> None:
    """Store alerts to DuckDB and anomaly_log.

    Args:
        alerts: List of alert dicts
        db_path: DuckDB path
    """
    if not alerts:
        return

    conn = duckdb.connect(str(db_path))

    # Store to toxicity_alerts
    for alert in alerts:
        conn.execute("""
            INSERT INTO toxicity_alerts (alert_id, timestamp, alert_type, severity, metric_value, threshold, description)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [alert['alert_id'], alert['timestamp'], alert['alert_type'], alert['severity'],
              alert['metric_value'], alert['threshold'], alert['description']])

        # Also store to anomaly_log if table exists
        try:
            conn.execute("""
                INSERT INTO anomaly_log (timestamp, anomaly_type, severity, description, source)
                VALUES (?, ?, ?, ?, ?)
            """, [alert['timestamp'], alert['alert_type'], alert['severity'], alert['description'], 'toxicity_monitor'])
        except:
            pass  # anomaly_log might not exist

    conn.close()
