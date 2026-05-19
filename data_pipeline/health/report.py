"""Daily intelligence report generator."""
import json
import requests
import duckdb
import pandas as pd
from pathlib import Path
from datetime import datetime, date
from typing import Dict, Optional, Tuple

from data_pipeline.config import DUCKDB_PATH, RAGD_URL, REPORTS_DIR


class ReportGenerator:
    """Generate daily intelligence reports."""

    def __init__(self, db_path: Path = DUCKDB_PATH):
        self.db_path = db_path
        self.ragd_url = RAGD_URL

    def generate_report(self, run_id: str) -> str:
        """Generate comprehensive daily intelligence report."""
        conn = duckdb.connect(str(self.db_path))

        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append(f"BLACKMARK DOMINION PIPELINE INTELLIGENCE REPORT")
        report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append(f"Run ID: {run_id}")
        report_lines.append("=" * 80)
        report_lines.append("")

        # 1. Pipeline Status
        report_lines.append("## PIPELINE STATUS")
        report_lines.append("")

        source_health = conn.execute("SELECT * FROM source_health").fetchdf()
        if not source_health.empty:
            for _, row in source_health.iterrows():
                status_symbol = "✓" if row["status"] == "OK" else "✗"
                report_lines.append(
                    f"{status_symbol} {row['source']:15} | "
                    f"trust={row['trust_score']:.2f} | "
                    f"latency={row['latency_ms']:.0f}ms | "
                    f"errors={row['error_count']}"
                )
        report_lines.append("")

        # 2. Current Regime Stack
        report_lines.append("## CURRENT REGIME STACK")
        report_lines.append("")

        regime_query = """
            SELECT *
            FROM regime_labels
            ORDER BY timestamp DESC
            LIMIT 1
        """
        regime = conn.execute(regime_query).fetchdf()
        if not regime.empty:
            row = regime.iloc[0]
            report_lines.append(f"Tactical: {row.get('tactical_regime', 'N/A')}")
            report_lines.append(f"Micro: {row.get('micro_regime', 'N/A')}")
            report_lines.append(f"Confidence: {row.get('confidence', 0.0):.2f}")
        report_lines.append("")

        # 3. Top Features by IC
        report_lines.append("## TOP 5 FEATURES BY IC")
        report_lines.append("")

        ic_query = """
            SELECT feature_name, AVG(ic_252) as avg_ic
            FROM features
            WHERE ic_updated_at IS NOT NULL
            GROUP BY feature_name
            ORDER BY ABS(avg_ic) DESC
            LIMIT 5
        """
        top_features = conn.execute(ic_query).fetchdf()
        if not top_features.empty:
            for _, row in top_features.iterrows():
                report_lines.append(f"{row['feature_name']:40} | IC={row['avg_ic']:+.4f}")
        report_lines.append("")

        # 4. Anomalies (last 24h)
        report_lines.append("## ANOMALIES (LAST 24H)")
        report_lines.append("")

        anomaly_query = """
            SELECT *
            FROM anomaly_log
            WHERE timestamp >= CURRENT_TIMESTAMP - INTERVAL '1 day'
            ORDER BY timestamp DESC
            LIMIT 10
        """
        anomalies = conn.execute(anomaly_query).fetchdf()
        if not anomalies.empty:
            for _, row in anomalies.iterrows():
                report_lines.append(
                    f"{row['timestamp']} | {row['severity']:8} | "
                    f"{row['anomaly_type']:15} | {row['description']}"
                )
        else:
            report_lines.append("No anomalies detected.")
        report_lines.append("")

        # 5. COT Positioning Summary
        report_lines.append("## COT POSITIONING SUMMARY")
        report_lines.append("")

        cot_query = """
            SELECT *
            FROM cot_data
            ORDER BY report_date DESC
            LIMIT 1
        """
        cot = conn.execute(cot_query).fetchdf()
        if not cot.empty:
            row = cot.iloc[0]
            report_lines.append(f"Report Date: {row['report_date']}")
            report_lines.append(f"Net Commercial: {row['net_commercial']:,.0f}")
            report_lines.append(f"Speculator Sentiment: {row['speculator_sentiment']:.3f}")
            report_lines.append(f"Open Interest: {row['open_interest']:,.0f}")
        report_lines.append("")

        # 6. Macro Summary
        report_lines.append("## MACRO SUMMARY")
        report_lines.append("")

        macro_series = ["DGS10", "DFII10", "DTWEXBGS", "VIXCLS", "T10Y2Y"]
        for series_id in macro_series:
            query = f"""
                SELECT value
                FROM macro_data
                WHERE series_id = '{series_id}'
                ORDER BY timestamp DESC
                LIMIT 1
            """
            result = conn.execute(query).fetchone()
            if result:
                report_lines.append(f"{series_id:15} | {result[0]:.2f}")
        report_lines.append("")

        # 7. Gold Price vs Fused Estimate
        report_lines.append("## GOLD PRICE vs FUSED ESTIMATE")
        report_lines.append("")

        gold_query = """
            SELECT timestamp, fused_price, fused_confidence, anomaly_flag
            FROM gold_master
            ORDER BY timestamp DESC
            LIMIT 1
        """
        gold = conn.execute(gold_query).fetchdf()
        if not gold.empty:
            row = gold.iloc[0]
            report_lines.append(f"Latest: {row['timestamp']}")
            report_lines.append(f"Fused Price: ${row['fused_price']:.2f}")
            report_lines.append(f"Confidence: {row['fused_confidence']:.4f}")
            report_lines.append(f"Anomaly: {'YES' if row['anomaly_flag'] else 'NO'}")
        report_lines.append("")

        # 8. Feature Drift Warnings
        report_lines.append("## FEATURE DRIFT WARNINGS")
        report_lines.append("")
        report_lines.append("(Feature drift detection requires baseline)")
        report_lines.append("")

        conn.close()

        report_lines.append("=" * 80)
        report_lines.append("END OF REPORT")
        report_lines.append("=" * 80)

        return "\n".join(report_lines)

    def store_report(self, report_text: str, report_date: date) -> None:
        """Store report in DuckDB."""
        conn = duckdb.connect(str(self.db_path))

        insert_query = """
            INSERT OR REPLACE INTO intelligence_reports (report_date, report_text, ragd_stored)
            VALUES (?, ?, FALSE)
        """

        conn.execute(insert_query, [report_date, report_text])
        conn.close()

    def write_report_file(self, report_text: str, report_date: date) -> Path:
        """Write report to markdown file."""
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)

        filename = f"pipeline-{report_date.strftime('%Y%m%d')}.md"
        filepath = REPORTS_DIR / filename

        with open(filepath, 'w') as f:
            f.write(report_text)

        return filepath

    def send_to_ragd(self, report_text: str, report_date: date) -> bool:
        """Send report to RAGD for memory storage."""
        try:
            response = requests.post(
                f"{self.ragd_url}/memory/remember",
                json={
                    "text": report_text,
                    "tag": "daily_report",
                    "metadata": {
                        "report_date": report_date.isoformat(),
                        "source": "data_pipeline"
                    }
                },
                timeout=10
            )

            if response.status_code == 200:
                # Update ragd_stored flag
                conn = duckdb.connect(str(self.db_path))
                conn.execute("""
                    UPDATE intelligence_reports
                    SET ragd_stored = TRUE
                    WHERE report_date = ?
                """, [report_date])
                conn.close()

                return True
            else:
                return False

        except Exception as e:
            print(f"Failed to send report to RAGD: {e}")
            return False

    def generate_and_store(self, run_id: str) -> Tuple[str, Path]:
        """Generate report and store everywhere."""
        report_text = self.generate_report(run_id)
        report_date = date.today()

        # Store in DuckDB
        self.store_report(report_text, report_date)

        # Write to file
        filepath = self.write_report_file(report_text, report_date)

        # Send to RAGD
        self.send_to_ragd(report_text, report_date)

        return report_text, filepath
