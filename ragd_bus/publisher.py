"""Publisher for RAGD bus events."""
from typing import Dict, Optional
from ragd_bus.client import RAGDBusSync


class BusPublisher:
    """Simplified publisher for pipeline events."""

    def __init__(self, url: str = "ws://127.0.0.1:7474/bus"):
        self.client = RAGDBusSync(url)

    def publish_pipeline_complete(self, run_id: str, sources_fetched: int, features_computed: int) -> bool:
        """Publish pipeline run complete event."""
        return self.client.send("pipeline.run.complete", {
            "run_id": run_id,
            "sources_fetched": sources_fetched,
            "features_computed": features_computed
        })

    def publish_anomaly(self, timestamp: str, anomaly_type: str, severity: str, source: str) -> bool:
        """Publish anomaly detection event."""
        return self.client.send("pipeline.anomaly", {
            "timestamp": timestamp,
            "anomaly_type": anomaly_type,
            "severity": severity,
            "source": source
        })

    def publish_regime_change(self, timestamp: str, old_regime: str, new_regime: str) -> bool:
        """Publish regime change event."""
        return self.client.send("pipeline.regime_change", {
            "timestamp": timestamp,
            "old_regime": old_regime,
            "new_regime": new_regime
        })

    def publish_dag_updated(self, run_id: str, n_edges: int) -> bool:
        """Publish causal DAG update event."""
        return self.client.send("causal.dag_updated", {
            "run_id": run_id,
            "n_edges": n_edges
        })

    def test_connection(self) -> bool:
        """Test bus connectivity."""
        return self.client.test_connectivity()
