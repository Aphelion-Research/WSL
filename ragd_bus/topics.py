"""Bus topic definitions."""

# Pipeline events
PIPELINE_RUN_COMPLETE = "pipeline.run.complete"
PIPELINE_ANOMALY = "pipeline.anomaly"
PIPELINE_REGIME_CHANGE = "pipeline.regime_change"
PIPELINE_SOURCE_HEALTH = "pipeline.source_health"

# Causal engine events
CAUSAL_DAG_UPDATED = "causal.dag_updated"

# Reservoir events
RESERVOIR_PREDICTION = "reservoir.prediction"

# Graph events
GRAPH_EMBEDDING_UPDATED = "graph.embedding_updated"

ALL_TOPICS = [
    PIPELINE_RUN_COMPLETE,
    PIPELINE_ANOMALY,
    PIPELINE_REGIME_CHANGE,
    PIPELINE_SOURCE_HEALTH,
    CAUSAL_DAG_UPDATED,
    RESERVOIR_PREDICTION,
    GRAPH_EMBEDDING_UPDATED
]
