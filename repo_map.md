# Dominion V2 Repository Map
**Generated:** 2026-05-22
**Scope:** SOURCE + CONFIG files only (excludes data/models/build artifacts)

## Directory Structure (3 levels)
```
./
apps/
  mt5/
    combat
artifacts/
  hydra/
    features_fold0.json
asset_graph/
  tests/
    __init__.py
    test_graph.py
aws/
  dist/
    awscli
backups/
  20260511-212017/
    Dominion
catboost_info/
causal_engine/
  tests/
    __init__.py
    test_pc.py
config/
cpp/
  build/
    CMakeFiles
    Makefile
  kernels/
    microstructure.cpp
    microstructure.hpp
    module.cpp
    rolling.cpp
    rolling.hpp
    statistical.cpp
    statistical.hpp
    technical.cpp
    technical.hpp
data/
  hydra_binary_288b/
    meta.json
  mt5_history/
    XAUUSD_D1.json
    XAUUSD_D1_raw.json
    XAUUSD_H1.json
    XAUUSD_H4.json
    XAUUSD_H4_raw.json
    _fetch_temp.py
    inventory.json
  registry/
    semantic_column_mapping.json
data_pipeline/
  features/
    __init__.py
    calendar.py
    cot_features.py
    crossasset.py
    macro.py
    microstructure.py
    price.py
    regime.py
    regime_storage.py
    store.py
  fusion/
    __init__.py
    bridge.py
    conflict.py
    kalman.py
  health/
    __init__.py
    anomaly.py
    monitor.py
    report.py
  sources/
    __init__.py
    alphavantage.py
    base.py
    cot.py
    domdata.py
    fred.py
    yahoo.py
  tests/
    __init__.py
    test_features.py
    test_fusion.py
    test_health.py
    test_sources.py
domdata/
  domdata_pkg/
    __init__.py
    cli.py
    collector.py
    commands.py
    config.py
    convert.py
    forbidden_tokens.py
    mt5_client.py
    safety.py
    serializers.py
    ... (1 more)
  tests/
    test_check_no_trading.py
    test_config.py
    test_safety.py
    test_serializers.py
dominion/
  dataset/
    __init__.py
    contracts.py
    m5_requirements.py
    registries.py
    registries_old.py
    semantic_names.py
  features/
    __init__.py
    cpp_bridge.py
  joins/
    __init__.py
    point_in_time.py
  matrix/
    __init__.py
    builder.py
  quality/
    __init__.py
    gates.py
dominion_agent/
  tests/
    test_adversary.py
    test_cli.py
    test_complexity.py
    test_conflicts.py
    test_e2e_smoke.py
    test_impact.py
    test_locks.py
    test_sessions.py
    test_store.py
    test_tasks.py
    ... (1 more)
dominion_ai/
  tests/
    eval_fixtures
    test_budget.py
    test_confidence.py
    test_context.py
    test_contract_scored_chunk.py
    test_contract_trace_join.py
    test_ragd_client.py
    test_rerank.py
    test_retrieval.py
    test_trace.py
    ... (4 more)
dominion_loader/
  tests/
    test_bench.py
    test_cache.py
    test_classify.py
    test_contract_loaded_file.py
    test_contract_ragd_ingestion.py
    test_doctor.py
    test_graph.py
    test_ignore.py
    test_scan.py
    test_truth_doctor.py
    ... (8 more)
exec_features/
  tests/
    __init__.py
    test_exec_features.py
exec_sim/
  impact/
    __init__.py
    almgren_chriss.py
  strategies/
    __init__.py
    base.py
    pov.py
    twap.py
    vwap.py
  tests/
    __init__.py
    test_sim.py
hydra/
  backtest/
    __init__.py
    cpp
    engine_py.py
    metrics.py
  brains/
    __init__.py
    day.py
    scalp.py
    swing.py
  data/
    __init__.py
    cv.py
    features.py
    features_stationary.py
    loader.py
    normalize.py
    targets.py
  data_sources/
    __init__.py
    __main__.py
    base.py
    duckdb_provider.py
    dukascopy_provider.py
    mt5_provider.py
    registry.py
    yahoo_provider.py
  export/
    __init__.py
    fuse.py
    quantize.py
    to_onnx.py
  labels/
    __init__.py
    triple_barrier.py
  loop/
    __init__.py
    improver.py
    stopping.py
    strategies.py
  models/
    __init__.py
    base.py
    forests.py
    gbm.py
    linear.py
    moe.py
    neural.py
    stacking.py
  ragd/
    __init__.py
    memory.py
  signals/
    __init__.py
    adversary.py
    core.py
    ensemble.py
    filters.py
  storage/
    __init__.py
    duckdb_writer.py
  telemetry/
    __init__.py
    recorder.py
    schema.py
  tests/
    __init__.py
    test_backtester.py
    test_cpp_parity.py
    test_ensemble.py
    test_metrics.py
    test_onnx.py
  training/
    __init__.py
    backtest.py
    guardrails.py
    hydra_runner.py
    metrics.py
    splits.py
  utils/
    __init__.py
    atomic.py
    eta.py
    system_monitor.py
lob/
  tests/
    __init__.py
    test_lob.py
ragd/
  build/
    CMakeFiles
    Makefile
    _deps
    tests
  examples/
    mcp_call_example.json
  include/
    dominion_native
    ragd
  scripts/
    __init__.py
    config.default.json
    ragd_maintenance.py
    ragd_mcp_stdio.py
  src/
    agent_memory.cpp
    bm25.cpp
    config.cpp
    dead_zone.cpp
    http_api.cpp
    intent_router.cpp
    main.cpp
    native
    temporal.cpp
    todo_engine.cpp
    ... (7 more)
  tests/
    test_agent_memory.cpp
    test_bm25.cpp
    test_indexer.cpp
    test_maintenance_report.py
    test_mcp_server.cpp
    test_rag_engine.cpp
    test_session_bus.cpp
    test_storage.cpp
    test_vector_store.cpp
    test_watcher.cpp
    ... (6 more)
  tools/
    dominion_native_cli.cpp
    native_doctor_main.cpp
    native_manifest_main.cpp
    native_scan_main.cpp
    native_vault_doctor_main.cpp
ragd_bus/
  tests/
    __init__.py
    test_bus.py
ragd_chunker/
  languages/
    __init__.py
    cpp.py
    go.py
    javascript.py
    python.py
    rust.py
    typescript.py
  tests/
    fixtures
    test_cpp_chunker.py
    test_metadata.py
    test_python_chunker.py
ragd_embed/
  providers/
    __init__.py
    ollama.py
    openai.py
    voyage.py
  tests/
    test_batcher.py
    test_cache.py
    test_config.py
    test_ollama.py
    test_pipeline.py
ragd_graph/
  tests/
    test_graph.py
ragd_hnsw/
  tests/
    test_index.py
    test_sync.py
ragd_vault/
  tests/
    test_note_generation.py
    test_vault_doctor.py
reports/
  eval/
    tiny-20260513-214846.json
    tiny-20260513-215612.json
research/
research_os/
  adapters/
    base.py
    browser_adapter.py
    registry.py
    requests_adapter.py
  tests/
    test_adapters.py
    test_chunker.py
    test_config.py
    test_db.py
    test_extractor.py
    test_fetcher.py
    test_normalize_quality.py
    test_scheduler.py
reservoir/
  tests/
    __init__.py
    test_esn.py
runs/
  hydra_9year_final_20260519_230411/
    data_coverage.json
  hydra_9year_final_20260519_230435/
    data_coverage.json
  hydra_9year_final_20260519_230459/
    checkpoints
    config_used.yaml
    data_coverage.json
    final_oos_result.json
  hydra_data_20260519_230339/
    data_coverage.json
  hydra_equal_thirds_20260519_231440/
    split_manifest.json
  hydra_equal_thirds_20260519_232841/
    checkpoints
    final_test_result.json
    oos_diagnostics
    split_manifest.json
    telemetry
  hydra_equal_thirds_20260520_102128/
    split_manifest.json
    telemetry
  hydra_equal_thirds_20260520_102446/
    checkpoints
    final_test_result.json
    split_manifest.json
    telemetry
  models/
    hydra_long.bin.meta.json
    hydra_short.bin.meta.json
scripts/
tca/
  tests/
    __init__.py
    test_tca.py
tests/
  dataset/
    test_matrix_builder.py
  training/
    __init__.py
    test_guardrails.py
    test_labels.py
    test_splits.py
tmp/
toxicity/
  tests/
    __init__.py
    test_toxicity.py
```

## Dependencies
```
duckdb>=1.0.0
polars>=0.20.0
PyYAML>=6.0
requests>=2.31.0
numpy>=1.26.0
voyageai>=0.2.0
openai>=1.0.0
tree-sitter>=0.21.0
tree-sitter-python>=0.21.0
tree-sitter-cpp>=0.22.0
tree-sitter-typescript>=0.21.0
tree-sitter-javascript>=0.21.0
tree-sitter-rust>=0.21.0
tree-sitter-go>=0.21.0
hnswlib>=0.8.0
pytest>=8.0.0
```

## Stats
- **Files:** 2,461
- **Lines (source):** ~195,240
- **Size:** 122.81 MB
- **Tokens (est):** ~32,194,314

## File Manifest
Path | Purpose | Key Exports
-----|---------|------------
`apps/mt5/combat/wineprefix/drive_c/windows/system.ini` | Configuration for windows | -
`apps/mt5/combat/wineprefix/drive_c/windows/system32/winevulkan.json` | Configuration for system32 | -
`apps/mt5/combat/wineprefix/drive_c/windows/syswow64/winevulkan.json` | Configuration for syswow64 | -
`apps/mt5/combat/wineprefix/drive_c/windows/win.ini` | Configuration for windows | -
`artifacts/hydra/features_fold0.json` | Configuration for hydra | -
`asset_graph/__init__.py` |   Init   | -
`asset_graph/cli.py` | CLI interface | cmd_build, cmd_show, main
`asset_graph/config.py` | Configuration for asset_graph | -
`asset_graph/gat.py` | Gat | SimpleGAT, attention, forward, fit
`asset_graph/graph.py` | Graph | init_graph_schema, build_correlation_graph, store_graph_snapshot, compute_node_centrality, compute_isolation_score
`asset_graph/tests/__init__.py` |   Init   | -
`asset_graph/tests/test_graph.py` | Tests for graph | test_correlation_graph, test_node_centrality
`audit_details.json` | Configuration for dominion | -
`audit_repo.py` | Audit Repo | categorize_file, main
`aws/dist/awscli/botocore/data/accessanalyzer/2019-11-01/endpoint-rule-set-1.json` | Configuration for 2019-11-01 | -
`aws/dist/awscli/botocore/data/accessanalyzer/2019-11-01/paginators-1.json` | Configuration for 2019-11-01 | -
`aws/dist/awscli/botocore/data/accessanalyzer/2019-11-01/paginators-1.sdk-extras.json` | Configuration for 2019-11-01 | -
`aws/dist/awscli/botocore/data/accessanalyzer/2019-11-01/service-2.json` | Configuration for 2019-11-01 | -
`aws/dist/awscli/botocore/data/account/2021-02-01/endpoint-rule-set-1.json` | Configuration for 2021-02-01 | -
`aws/dist/awscli/botocore/data/account/2021-02-01/paginators-1.json` | Configuration for 2021-02-01 | -
`aws/dist/awscli/botocore/data/account/2021-02-01/service-2.json` | Configuration for 2021-02-01 | -
`aws/dist/awscli/botocore/data/account/2021-02-01/waiters-2.json` | Configuration for 2021-02-01 | -
`aws/dist/awscli/botocore/data/acm/2015-12-08/endpoint-rule-set-1.json` | Configuration for 2015-12-08 | -
`aws/dist/awscli/botocore/data/acm/2015-12-08/paginators-1.json` | Configuration for 2015-12-08 | -
`aws/dist/awscli/botocore/data/acm/2015-12-08/service-2.json` | Configuration for 2015-12-08 | -
`aws/dist/awscli/botocore/data/acm/2015-12-08/waiters-2.json` | Configuration for 2015-12-08 | -
`aws/dist/awscli/botocore/data/acm-pca/2017-08-22/endpoint-rule-set-1.json` | Configuration for 2017-08-22 | -
`aws/dist/awscli/botocore/data/acm-pca/2017-08-22/paginators-1.json` | Configuration for 2017-08-22 | -
`aws/dist/awscli/botocore/data/acm-pca/2017-08-22/service-2.json` | Configuration for 2017-08-22 | -
`aws/dist/awscli/botocore/data/acm-pca/2017-08-22/waiters-2.json` | Configuration for 2017-08-22 | -
`aws/dist/awscli/botocore/data/aiops/2018-05-10/endpoint-rule-set-1.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/aiops/2018-05-10/paginators-1.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/aiops/2018-05-10/service-2.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/aiops/2018-05-10/waiters-2.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/amp/2020-08-01/endpoint-rule-set-1.json` | Configuration for 2020-08-01 | -
`aws/dist/awscli/botocore/data/amp/2020-08-01/paginators-1.json` | Configuration for 2020-08-01 | -
`aws/dist/awscli/botocore/data/amp/2020-08-01/service-2.json` | Configuration for 2020-08-01 | -
`aws/dist/awscli/botocore/data/amp/2020-08-01/waiters-2.json` | Configuration for 2020-08-01 | -
`aws/dist/awscli/botocore/data/amplify/2017-07-25/endpoint-rule-set-1.json` | Configuration for 2017-07-25 | -
`aws/dist/awscli/botocore/data/amplify/2017-07-25/paginators-1.json` | Configuration for 2017-07-25 | -
`aws/dist/awscli/botocore/data/amplify/2017-07-25/service-2.json` | Configuration for 2017-07-25 | -
`aws/dist/awscli/botocore/data/amplifybackend/2020-08-11/endpoint-rule-set-1.json` | Configuration for 2020-08-11 | -
`aws/dist/awscli/botocore/data/amplifybackend/2020-08-11/paginators-1.json` | Configuration for 2020-08-11 | -
`aws/dist/awscli/botocore/data/amplifybackend/2020-08-11/service-2.json` | Configuration for 2020-08-11 | -
`aws/dist/awscli/botocore/data/amplifyuibuilder/2021-08-11/endpoint-rule-set-1.json` | Configuration for 2021-08-11 | -
`aws/dist/awscli/botocore/data/amplifyuibuilder/2021-08-11/paginators-1.json` | Configuration for 2021-08-11 | -
`aws/dist/awscli/botocore/data/amplifyuibuilder/2021-08-11/service-2.json` | Configuration for 2021-08-11 | -
`aws/dist/awscli/botocore/data/amplifyuibuilder/2021-08-11/waiters-2.json` | Configuration for 2021-08-11 | -
`aws/dist/awscli/botocore/data/apigateway/2015-07-09/endpoint-rule-set-1.json` | Configuration for 2015-07-09 | -
`aws/dist/awscli/botocore/data/apigateway/2015-07-09/paginators-1.json` | Configuration for 2015-07-09 | -
`aws/dist/awscli/botocore/data/apigateway/2015-07-09/service-2.json` | Configuration for 2015-07-09 | -
`aws/dist/awscli/botocore/data/apigatewaymanagementapi/2018-11-29/endpoint-rule-set-1.json` | Configuration for 2018-11-29 | -
`aws/dist/awscli/botocore/data/apigatewaymanagementapi/2018-11-29/paginators-1.json` | Configuration for 2018-11-29 | -
`aws/dist/awscli/botocore/data/apigatewaymanagementapi/2018-11-29/service-2.json` | Configuration for 2018-11-29 | -
`aws/dist/awscli/botocore/data/apigatewayv2/2018-11-29/endpoint-rule-set-1.json` | Configuration for 2018-11-29 | -
`aws/dist/awscli/botocore/data/apigatewayv2/2018-11-29/paginators-1.json` | Configuration for 2018-11-29 | -
`aws/dist/awscli/botocore/data/apigatewayv2/2018-11-29/service-2.json` | Configuration for 2018-11-29 | -
`aws/dist/awscli/botocore/data/appconfig/2019-10-09/endpoint-rule-set-1.json` | Configuration for 2019-10-09 | -
`aws/dist/awscli/botocore/data/appconfig/2019-10-09/paginators-1.json` | Configuration for 2019-10-09 | -
`aws/dist/awscli/botocore/data/appconfig/2019-10-09/service-2.json` | Configuration for 2019-10-09 | -
`aws/dist/awscli/botocore/data/appconfig/2019-10-09/waiters-2.json` | Configuration for 2019-10-09 | -
`aws/dist/awscli/botocore/data/appconfigdata/2021-11-11/endpoint-rule-set-1.json` | Configuration for 2021-11-11 | -
`aws/dist/awscli/botocore/data/appconfigdata/2021-11-11/paginators-1.json` | Configuration for 2021-11-11 | -
`aws/dist/awscli/botocore/data/appconfigdata/2021-11-11/service-2.json` | Configuration for 2021-11-11 | -
`aws/dist/awscli/botocore/data/appfabric/2023-05-19/endpoint-rule-set-1.json` | Configuration for 2023-05-19 | -
`aws/dist/awscli/botocore/data/appfabric/2023-05-19/paginators-1.json` | Configuration for 2023-05-19 | -
`aws/dist/awscli/botocore/data/appfabric/2023-05-19/service-2.json` | Configuration for 2023-05-19 | -
`aws/dist/awscli/botocore/data/appfabric/2023-05-19/waiters-2.json` | Configuration for 2023-05-19 | -
`aws/dist/awscli/botocore/data/appflow/2020-08-23/endpoint-rule-set-1.json` | Configuration for 2020-08-23 | -
`aws/dist/awscli/botocore/data/appflow/2020-08-23/paginators-1.json` | Configuration for 2020-08-23 | -
`aws/dist/awscli/botocore/data/appflow/2020-08-23/service-2.json` | Configuration for 2020-08-23 | -
`aws/dist/awscli/botocore/data/appintegrations/2020-07-29/endpoint-rule-set-1.json` | Configuration for 2020-07-29 | -
`aws/dist/awscli/botocore/data/appintegrations/2020-07-29/paginators-1.json` | Configuration for 2020-07-29 | -
`aws/dist/awscli/botocore/data/appintegrations/2020-07-29/service-2.json` | Configuration for 2020-07-29 | -
`aws/dist/awscli/botocore/data/application-autoscaling/2016-02-06/endpoint-rule-set-1.json` | Configuration for 2016-02-06 | -
`aws/dist/awscli/botocore/data/application-autoscaling/2016-02-06/paginators-1.json` | Configuration for 2016-02-06 | -
`aws/dist/awscli/botocore/data/application-autoscaling/2016-02-06/service-2.json` | Configuration for 2016-02-06 | -
`aws/dist/awscli/botocore/data/application-insights/2018-11-25/endpoint-rule-set-1.json` | Configuration for 2018-11-25 | -
`aws/dist/awscli/botocore/data/application-insights/2018-11-25/paginators-1.json` | Configuration for 2018-11-25 | -
`aws/dist/awscli/botocore/data/application-insights/2018-11-25/service-2.json` | Configuration for 2018-11-25 | -
`aws/dist/awscli/botocore/data/application-signals/2024-04-15/endpoint-rule-set-1.json` | Configuration for 2024-04-15 | -
`aws/dist/awscli/botocore/data/application-signals/2024-04-15/paginators-1.json` | Configuration for 2024-04-15 | -
`aws/dist/awscli/botocore/data/application-signals/2024-04-15/paginators-1.sdk-extras.json` | Configuration for 2024-04-15 | -
`aws/dist/awscli/botocore/data/application-signals/2024-04-15/service-2.json` | Configuration for 2024-04-15 | -
`aws/dist/awscli/botocore/data/application-signals/2024-04-15/waiters-2.json` | Configuration for 2024-04-15 | -
`aws/dist/awscli/botocore/data/applicationcostprofiler/2020-09-10/endpoint-rule-set-1.json` | Configuration for 2020-09-10 | -
`aws/dist/awscli/botocore/data/applicationcostprofiler/2020-09-10/paginators-1.json` | Configuration for 2020-09-10 | -
`aws/dist/awscli/botocore/data/applicationcostprofiler/2020-09-10/service-2.json` | Configuration for 2020-09-10 | -
`aws/dist/awscli/botocore/data/appmesh/2019-01-25/endpoint-rule-set-1.json` | Configuration for 2019-01-25 | -
`aws/dist/awscli/botocore/data/appmesh/2019-01-25/paginators-1.json` | Configuration for 2019-01-25 | -
`aws/dist/awscli/botocore/data/appmesh/2019-01-25/service-2.json` | Configuration for 2019-01-25 | -
`aws/dist/awscli/botocore/data/apprunner/2020-05-15/endpoint-rule-set-1.json` | Configuration for 2020-05-15 | -
`aws/dist/awscli/botocore/data/apprunner/2020-05-15/paginators-1.json` | Configuration for 2020-05-15 | -
`aws/dist/awscli/botocore/data/apprunner/2020-05-15/service-2.json` | Configuration for 2020-05-15 | -
`aws/dist/awscli/botocore/data/appstream/2016-12-01/endpoint-rule-set-1.json` | Configuration for 2016-12-01 | -
`aws/dist/awscli/botocore/data/appstream/2016-12-01/paginators-1.json` | Configuration for 2016-12-01 | -
`aws/dist/awscli/botocore/data/appstream/2016-12-01/service-2.json` | Configuration for 2016-12-01 | -
`aws/dist/awscli/botocore/data/appstream/2016-12-01/waiters-2.json` | Configuration for 2016-12-01 | -
`aws/dist/awscli/botocore/data/appsync/2017-07-25/endpoint-rule-set-1.json` | Configuration for 2017-07-25 | -
`aws/dist/awscli/botocore/data/appsync/2017-07-25/paginators-1.json` | Configuration for 2017-07-25 | -
`aws/dist/awscli/botocore/data/appsync/2017-07-25/service-2.json` | Configuration for 2017-07-25 | -
`aws/dist/awscli/botocore/data/arc-region-switch/2022-07-26/endpoint-rule-set-1.json` | Configuration for 2022-07-26 | -
`aws/dist/awscli/botocore/data/arc-region-switch/2022-07-26/paginators-1.json` | Configuration for 2022-07-26 | -
`aws/dist/awscli/botocore/data/arc-region-switch/2022-07-26/paginators-1.sdk-extras.json` | Configuration for 2022-07-26 | -
`aws/dist/awscli/botocore/data/arc-region-switch/2022-07-26/service-2.json` | Configuration for 2022-07-26 | -
`aws/dist/awscli/botocore/data/arc-region-switch/2022-07-26/waiters-2.json` | Configuration for 2022-07-26 | -
`aws/dist/awscli/botocore/data/arc-zonal-shift/2022-10-30/endpoint-rule-set-1.json` | Configuration for 2022-10-30 | -
`aws/dist/awscli/botocore/data/arc-zonal-shift/2022-10-30/paginators-1.json` | Configuration for 2022-10-30 | -
`aws/dist/awscli/botocore/data/arc-zonal-shift/2022-10-30/service-2.json` | Configuration for 2022-10-30 | -
`aws/dist/awscli/botocore/data/arc-zonal-shift/2022-10-30/waiters-2.json` | Configuration for 2022-10-30 | -
`aws/dist/awscli/botocore/data/artifact/2018-05-10/endpoint-rule-set-1.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/artifact/2018-05-10/paginators-1.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/artifact/2018-05-10/service-2.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/artifact/2018-05-10/waiters-2.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/athena/2017-05-18/endpoint-rule-set-1.json` | Configuration for 2017-05-18 | -
`aws/dist/awscli/botocore/data/athena/2017-05-18/paginators-1.json` | Configuration for 2017-05-18 | -
`aws/dist/awscli/botocore/data/athena/2017-05-18/service-2.json` | Configuration for 2017-05-18 | -
`aws/dist/awscli/botocore/data/auditmanager/2017-07-25/endpoint-rule-set-1.json` | Configuration for 2017-07-25 | -
`aws/dist/awscli/botocore/data/auditmanager/2017-07-25/paginators-1.json` | Configuration for 2017-07-25 | -
`aws/dist/awscli/botocore/data/auditmanager/2017-07-25/service-2.json` | Configuration for 2017-07-25 | -
`aws/dist/awscli/botocore/data/autoscaling/2011-01-01/endpoint-rule-set-1.json` | Configuration for 2011-01-01 | -
`aws/dist/awscli/botocore/data/autoscaling/2011-01-01/paginators-1.json` | Configuration for 2011-01-01 | -
`aws/dist/awscli/botocore/data/autoscaling/2011-01-01/paginators-1.sdk-extras.json` | Configuration for 2011-01-01 | -
`aws/dist/awscli/botocore/data/autoscaling/2011-01-01/service-2.json` | Configuration for 2011-01-01 | -
`aws/dist/awscli/botocore/data/autoscaling-plans/2018-01-06/endpoint-rule-set-1.json` | Configuration for 2018-01-06 | -
`aws/dist/awscli/botocore/data/autoscaling-plans/2018-01-06/paginators-1.json` | Configuration for 2018-01-06 | -
`aws/dist/awscli/botocore/data/autoscaling-plans/2018-01-06/service-2.json` | Configuration for 2018-01-06 | -
`aws/dist/awscli/botocore/data/b2bi/2022-06-23/endpoint-rule-set-1.json` | Configuration for 2022-06-23 | -
`aws/dist/awscli/botocore/data/b2bi/2022-06-23/paginators-1.json` | Configuration for 2022-06-23 | -
`aws/dist/awscli/botocore/data/b2bi/2022-06-23/service-2.json` | Configuration for 2022-06-23 | -
`aws/dist/awscli/botocore/data/b2bi/2022-06-23/waiters-2.json` | Configuration for 2022-06-23 | -
`aws/dist/awscli/botocore/data/backup/2018-11-15/endpoint-rule-set-1.json` | Configuration for 2018-11-15 | -
`aws/dist/awscli/botocore/data/backup/2018-11-15/paginators-1.json` | Configuration for 2018-11-15 | -
`aws/dist/awscli/botocore/data/backup/2018-11-15/paginators-1.sdk-extras.json` | Configuration for 2018-11-15 | -
`aws/dist/awscli/botocore/data/backup/2018-11-15/service-2.json` | Configuration for 2018-11-15 | -
`aws/dist/awscli/botocore/data/backup-gateway/2021-01-01/endpoint-rule-set-1.json` | Configuration for 2021-01-01 | -
`aws/dist/awscli/botocore/data/backup-gateway/2021-01-01/paginators-1.json` | Configuration for 2021-01-01 | -
`aws/dist/awscli/botocore/data/backup-gateway/2021-01-01/service-2.json` | Configuration for 2021-01-01 | -
`aws/dist/awscli/botocore/data/backupsearch/2018-05-10/endpoint-rule-set-1.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/backupsearch/2018-05-10/paginators-1.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/backupsearch/2018-05-10/service-2.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/backupsearch/2018-05-10/waiters-2.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/batch/2016-08-10/endpoint-rule-set-1.json` | Configuration for 2016-08-10 | -
`aws/dist/awscli/botocore/data/batch/2016-08-10/paginators-1.json` | Configuration for 2016-08-10 | -
`aws/dist/awscli/botocore/data/batch/2016-08-10/service-2.json` | Configuration for 2016-08-10 | -
`aws/dist/awscli/botocore/data/bcm-dashboards/2025-08-18/endpoint-rule-set-1.json` | Configuration for 2025-08-18 | -
`aws/dist/awscli/botocore/data/bcm-dashboards/2025-08-18/paginators-1.json` | Configuration for 2025-08-18 | -
`aws/dist/awscli/botocore/data/bcm-dashboards/2025-08-18/service-2.json` | Configuration for 2025-08-18 | -
`aws/dist/awscli/botocore/data/bcm-dashboards/2025-08-18/waiters-2.json` | Configuration for 2025-08-18 | -
`aws/dist/awscli/botocore/data/bcm-data-exports/2023-11-26/endpoint-rule-set-1.json` | Configuration for 2023-11-26 | -
`aws/dist/awscli/botocore/data/bcm-data-exports/2023-11-26/paginators-1.json` | Configuration for 2023-11-26 | -
`aws/dist/awscli/botocore/data/bcm-data-exports/2023-11-26/service-2.json` | Configuration for 2023-11-26 | -
`aws/dist/awscli/botocore/data/bcm-pricing-calculator/2024-06-19/endpoint-rule-set-1.json` | Configuration for 2024-06-19 | -
`aws/dist/awscli/botocore/data/bcm-pricing-calculator/2024-06-19/paginators-1.json` | Configuration for 2024-06-19 | -
`aws/dist/awscli/botocore/data/bcm-pricing-calculator/2024-06-19/service-2.json` | Configuration for 2024-06-19 | -
`aws/dist/awscli/botocore/data/bcm-pricing-calculator/2024-06-19/waiters-2.json` | Configuration for 2024-06-19 | -
`aws/dist/awscli/botocore/data/bcm-recommended-actions/2024-11-14/endpoint-rule-set-1.json` | Configuration for 2024-11-14 | -
`aws/dist/awscli/botocore/data/bcm-recommended-actions/2024-11-14/paginators-1.json` | Configuration for 2024-11-14 | -
`aws/dist/awscli/botocore/data/bcm-recommended-actions/2024-11-14/service-2.json` | Configuration for 2024-11-14 | -
`aws/dist/awscli/botocore/data/bcm-recommended-actions/2024-11-14/waiters-2.json` | Configuration for 2024-11-14 | -
`aws/dist/awscli/botocore/data/bedrock/2023-04-20/endpoint-rule-set-1.json` | Configuration for 2023-04-20 | -
`aws/dist/awscli/botocore/data/bedrock/2023-04-20/paginators-1.json` | Configuration for 2023-04-20 | -
`aws/dist/awscli/botocore/data/bedrock/2023-04-20/service-2.json` | Configuration for 2023-04-20 | -
`aws/dist/awscli/botocore/data/bedrock/2023-04-20/waiters-2.json` | Configuration for 2023-04-20 | -
`aws/dist/awscli/botocore/data/bedrock-agent/2023-06-05/endpoint-rule-set-1.json` | Configuration for 2023-06-05 | -
`aws/dist/awscli/botocore/data/bedrock-agent/2023-06-05/paginators-1.json` | Configuration for 2023-06-05 | -
`aws/dist/awscli/botocore/data/bedrock-agent/2023-06-05/service-2.json` | Configuration for 2023-06-05 | -
`aws/dist/awscli/botocore/data/bedrock-agent/2023-06-05/waiters-2.json` | Configuration for 2023-06-05 | -
`aws/dist/awscli/botocore/data/bedrock-agent-runtime/2023-07-26/endpoint-rule-set-1.json` | Configuration for 2023-07-26 | -
`aws/dist/awscli/botocore/data/bedrock-agent-runtime/2023-07-26/paginators-1.json` | Configuration for 2023-07-26 | -
`aws/dist/awscli/botocore/data/bedrock-agent-runtime/2023-07-26/paginators-1.sdk-extras.json` | Configuration for 2023-07-26 | -
`aws/dist/awscli/botocore/data/bedrock-agent-runtime/2023-07-26/service-2.json` | Configuration for 2023-07-26 | -
`aws/dist/awscli/botocore/data/bedrock-agent-runtime/2023-07-26/waiters-2.json` | Configuration for 2023-07-26 | -
`aws/dist/awscli/botocore/data/bedrock-agentcore/2024-02-28/endpoint-rule-set-1.json` | Configuration for 2024-02-28 | -
`aws/dist/awscli/botocore/data/bedrock-agentcore/2024-02-28/paginators-1.json` | Configuration for 2024-02-28 | -
`aws/dist/awscli/botocore/data/bedrock-agentcore/2024-02-28/service-2.json` | Configuration for 2024-02-28 | -
`aws/dist/awscli/botocore/data/bedrock-agentcore/2024-02-28/waiters-2.json` | Configuration for 2024-02-28 | -
`aws/dist/awscli/botocore/data/bedrock-agentcore-control/2023-06-05/endpoint-rule-set-1.json` | Configuration for 2023-06-05 | -
`aws/dist/awscli/botocore/data/bedrock-agentcore-control/2023-06-05/paginators-1.json` | Configuration for 2023-06-05 | -
`aws/dist/awscli/botocore/data/bedrock-agentcore-control/2023-06-05/service-2.json` | Configuration for 2023-06-05 | -
`aws/dist/awscli/botocore/data/bedrock-agentcore-control/2023-06-05/waiters-2.json` | Configuration for 2023-06-05 | -
`aws/dist/awscli/botocore/data/bedrock-data-automation/2023-07-26/endpoint-rule-set-1.json` | Configuration for 2023-07-26 | -
`aws/dist/awscli/botocore/data/bedrock-data-automation/2023-07-26/paginators-1.json` | Configuration for 2023-07-26 | -
`aws/dist/awscli/botocore/data/bedrock-data-automation/2023-07-26/service-2.json` | Configuration for 2023-07-26 | -
`aws/dist/awscli/botocore/data/bedrock-data-automation-runtime/2024-06-13/endpoint-rule-set-1.json` | Configuration for 2024-06-13 | -
`aws/dist/awscli/botocore/data/bedrock-data-automation-runtime/2024-06-13/paginators-1.json` | Configuration for 2024-06-13 | -
`aws/dist/awscli/botocore/data/bedrock-data-automation-runtime/2024-06-13/service-2.json` | Configuration for 2024-06-13 | -
`aws/dist/awscli/botocore/data/bedrock-runtime/2023-09-30/endpoint-rule-set-1.json` | Configuration for 2023-09-30 | -
`aws/dist/awscli/botocore/data/bedrock-runtime/2023-09-30/paginators-1.json` | Configuration for 2023-09-30 | -
`aws/dist/awscli/botocore/data/bedrock-runtime/2023-09-30/service-2.json` | Configuration for 2023-09-30 | -
`aws/dist/awscli/botocore/data/bedrock-runtime/2023-09-30/waiters-2.json` | Configuration for 2023-09-30 | -
`aws/dist/awscli/botocore/data/billing/2023-09-07/endpoint-rule-set-1.json` | Configuration for 2023-09-07 | -
`aws/dist/awscli/botocore/data/billing/2023-09-07/paginators-1.json` | Configuration for 2023-09-07 | -
`aws/dist/awscli/botocore/data/billing/2023-09-07/service-2.json` | Configuration for 2023-09-07 | -
`aws/dist/awscli/botocore/data/billing/2023-09-07/waiters-2.json` | Configuration for 2023-09-07 | -
`aws/dist/awscli/botocore/data/billingconductor/2021-07-30/endpoint-rule-set-1.json` | Configuration for 2021-07-30 | -
`aws/dist/awscli/botocore/data/billingconductor/2021-07-30/paginators-1.json` | Configuration for 2021-07-30 | -
`aws/dist/awscli/botocore/data/billingconductor/2021-07-30/service-2.json` | Configuration for 2021-07-30 | -
`aws/dist/awscli/botocore/data/billingconductor/2021-07-30/waiters-2.json` | Configuration for 2021-07-30 | -
`aws/dist/awscli/botocore/data/braket/2019-09-01/endpoint-rule-set-1.json` | Configuration for 2019-09-01 | -
`aws/dist/awscli/botocore/data/braket/2019-09-01/paginators-1.json` | Configuration for 2019-09-01 | -
`aws/dist/awscli/botocore/data/braket/2019-09-01/service-2.json` | Configuration for 2019-09-01 | -
`aws/dist/awscli/botocore/data/budgets/2016-10-20/endpoint-rule-set-1.json` | Configuration for 2016-10-20 | -
`aws/dist/awscli/botocore/data/budgets/2016-10-20/paginators-1.json` | Configuration for 2016-10-20 | -
`aws/dist/awscli/botocore/data/budgets/2016-10-20/service-2.json` | Configuration for 2016-10-20 | -
`aws/dist/awscli/botocore/data/ce/2017-10-25/endpoint-rule-set-1.json` | Configuration for 2017-10-25 | -
`aws/dist/awscli/botocore/data/ce/2017-10-25/paginators-1.json` | Configuration for 2017-10-25 | -
`aws/dist/awscli/botocore/data/ce/2017-10-25/paginators-1.sdk-extras.json` | Configuration for 2017-10-25 | -
`aws/dist/awscli/botocore/data/ce/2017-10-25/service-2.json` | Configuration for 2017-10-25 | -
`aws/dist/awscli/botocore/data/chatbot/2017-10-11/endpoint-rule-set-1.json` | Configuration for 2017-10-11 | -
`aws/dist/awscli/botocore/data/chatbot/2017-10-11/paginators-1.json` | Configuration for 2017-10-11 | -
`aws/dist/awscli/botocore/data/chatbot/2017-10-11/service-2.json` | Configuration for 2017-10-11 | -
`aws/dist/awscli/botocore/data/chime/2018-05-01/endpoint-rule-set-1.json` | Configuration for 2018-05-01 | -
`aws/dist/awscli/botocore/data/chime/2018-05-01/paginators-1.json` | Configuration for 2018-05-01 | -
`aws/dist/awscli/botocore/data/chime/2018-05-01/service-2.json` | Configuration for 2018-05-01 | -
`aws/dist/awscli/botocore/data/chime-sdk-identity/2021-04-20/endpoint-rule-set-1.json` | Configuration for 2021-04-20 | -
`aws/dist/awscli/botocore/data/chime-sdk-identity/2021-04-20/paginators-1.json` | Configuration for 2021-04-20 | -
`aws/dist/awscli/botocore/data/chime-sdk-identity/2021-04-20/service-2.json` | Configuration for 2021-04-20 | -
`aws/dist/awscli/botocore/data/chime-sdk-media-pipelines/2021-07-15/endpoint-rule-set-1.json` | Configuration for 2021-07-15 | -
`aws/dist/awscli/botocore/data/chime-sdk-media-pipelines/2021-07-15/paginators-1.json` | Configuration for 2021-07-15 | -
`aws/dist/awscli/botocore/data/chime-sdk-media-pipelines/2021-07-15/service-2.json` | Configuration for 2021-07-15 | -
`aws/dist/awscli/botocore/data/chime-sdk-meetings/2021-07-15/endpoint-rule-set-1.json` | Configuration for 2021-07-15 | -
`aws/dist/awscli/botocore/data/chime-sdk-meetings/2021-07-15/paginators-1.json` | Configuration for 2021-07-15 | -
`aws/dist/awscli/botocore/data/chime-sdk-meetings/2021-07-15/service-2.json` | Configuration for 2021-07-15 | -
`aws/dist/awscli/botocore/data/chime-sdk-messaging/2021-05-15/endpoint-rule-set-1.json` | Configuration for 2021-05-15 | -
`aws/dist/awscli/botocore/data/chime-sdk-messaging/2021-05-15/paginators-1.json` | Configuration for 2021-05-15 | -
`aws/dist/awscli/botocore/data/chime-sdk-messaging/2021-05-15/service-2.json` | Configuration for 2021-05-15 | -
`aws/dist/awscli/botocore/data/chime-sdk-voice/2022-08-03/endpoint-rule-set-1.json` | Configuration for 2022-08-03 | -
`aws/dist/awscli/botocore/data/chime-sdk-voice/2022-08-03/paginators-1.json` | Configuration for 2022-08-03 | -
`aws/dist/awscli/botocore/data/chime-sdk-voice/2022-08-03/service-2.json` | Configuration for 2022-08-03 | -
`aws/dist/awscli/botocore/data/cleanrooms/2022-02-17/endpoint-rule-set-1.json` | Configuration for 2022-02-17 | -
`aws/dist/awscli/botocore/data/cleanrooms/2022-02-17/paginators-1.json` | Configuration for 2022-02-17 | -
`aws/dist/awscli/botocore/data/cleanrooms/2022-02-17/service-2.json` | Configuration for 2022-02-17 | -
`aws/dist/awscli/botocore/data/cleanrooms/2022-02-17/waiters-2.json` | Configuration for 2022-02-17 | -
`aws/dist/awscli/botocore/data/cleanroomsml/2023-09-06/endpoint-rule-set-1.json` | Configuration for 2023-09-06 | -
`aws/dist/awscli/botocore/data/cleanroomsml/2023-09-06/paginators-1.json` | Configuration for 2023-09-06 | -
`aws/dist/awscli/botocore/data/cleanroomsml/2023-09-06/service-2.json` | Configuration for 2023-09-06 | -
`aws/dist/awscli/botocore/data/cleanroomsml/2023-09-06/waiters-2.json` | Configuration for 2023-09-06 | -
`aws/dist/awscli/botocore/data/cloud9/2017-09-23/endpoint-rule-set-1.json` | Configuration for 2017-09-23 | -
`aws/dist/awscli/botocore/data/cloud9/2017-09-23/paginators-1.json` | Configuration for 2017-09-23 | -
`aws/dist/awscli/botocore/data/cloud9/2017-09-23/service-2.json` | Configuration for 2017-09-23 | -
`aws/dist/awscli/botocore/data/cloudcontrol/2021-09-30/endpoint-rule-set-1.json` | Configuration for 2021-09-30 | -
`aws/dist/awscli/botocore/data/cloudcontrol/2021-09-30/paginators-1.json` | Configuration for 2021-09-30 | -
`aws/dist/awscli/botocore/data/cloudcontrol/2021-09-30/paginators-1.sdk-extras.json` | Configuration for 2021-09-30 | -
`aws/dist/awscli/botocore/data/cloudcontrol/2021-09-30/service-2.json` | Configuration for 2021-09-30 | -
`aws/dist/awscli/botocore/data/cloudcontrol/2021-09-30/waiters-2.json` | Configuration for 2021-09-30 | -
`aws/dist/awscli/botocore/data/clouddirectory/2017-01-11/endpoint-rule-set-1.json` | Configuration for 2017-01-11 | -
`aws/dist/awscli/botocore/data/clouddirectory/2017-01-11/paginators-1.json` | Configuration for 2017-01-11 | -
`aws/dist/awscli/botocore/data/clouddirectory/2017-01-11/service-2.json` | Configuration for 2017-01-11 | -
`aws/dist/awscli/botocore/data/cloudformation/2010-05-15/endpoint-rule-set-1.json` | Configuration for 2010-05-15 | -
`aws/dist/awscli/botocore/data/cloudformation/2010-05-15/paginators-1.json` | Configuration for 2010-05-15 | -
`aws/dist/awscli/botocore/data/cloudformation/2010-05-15/service-2.json` | Configuration for 2010-05-15 | -
`aws/dist/awscli/botocore/data/cloudformation/2010-05-15/waiters-2.json` | Configuration for 2010-05-15 | -
`aws/dist/awscli/botocore/data/cloudfront/2020-05-31/endpoint-rule-set-1.json` | Configuration for 2020-05-31 | -
`aws/dist/awscli/botocore/data/cloudfront/2020-05-31/paginators-1.json` | Configuration for 2020-05-31 | -
`aws/dist/awscli/botocore/data/cloudfront/2020-05-31/service-2.json` | Configuration for 2020-05-31 | -
`aws/dist/awscli/botocore/data/cloudfront/2020-05-31/waiters-2.json` | Configuration for 2020-05-31 | -
`aws/dist/awscli/botocore/data/cloudfront-keyvaluestore/2022-07-26/endpoint-rule-set-1.json` | Configuration for 2022-07-26 | -
`aws/dist/awscli/botocore/data/cloudfront-keyvaluestore/2022-07-26/paginators-1.json` | Configuration for 2022-07-26 | -
`aws/dist/awscli/botocore/data/cloudfront-keyvaluestore/2022-07-26/service-2.json` | Configuration for 2022-07-26 | -
`aws/dist/awscli/botocore/data/cloudhsm/2014-05-30/endpoint-rule-set-1.json` | Configuration for 2014-05-30 | -
`aws/dist/awscli/botocore/data/cloudhsm/2014-05-30/paginators-1.json` | Configuration for 2014-05-30 | -
`aws/dist/awscli/botocore/data/cloudhsm/2014-05-30/service-2.json` | Configuration for 2014-05-30 | -
`aws/dist/awscli/botocore/data/cloudhsmv2/2017-04-28/endpoint-rule-set-1.json` | Configuration for 2017-04-28 | -
`aws/dist/awscli/botocore/data/cloudhsmv2/2017-04-28/paginators-1.json` | Configuration for 2017-04-28 | -
`aws/dist/awscli/botocore/data/cloudhsmv2/2017-04-28/service-2.json` | Configuration for 2017-04-28 | -
`aws/dist/awscli/botocore/data/cloudsearch/2013-01-01/endpoint-rule-set-1.json` | Configuration for 2013-01-01 | -
`aws/dist/awscli/botocore/data/cloudsearch/2013-01-01/paginators-1.json` | Configuration for 2013-01-01 | -
`aws/dist/awscli/botocore/data/cloudsearch/2013-01-01/service-2.json` | Configuration for 2013-01-01 | -
`aws/dist/awscli/botocore/data/cloudsearchdomain/2013-01-01/endpoint-rule-set-1.json` | Configuration for 2013-01-01 | -
`aws/dist/awscli/botocore/data/cloudsearchdomain/2013-01-01/paginators-1.json` | Configuration for 2013-01-01 | -
`aws/dist/awscli/botocore/data/cloudsearchdomain/2013-01-01/service-2.json` | Configuration for 2013-01-01 | -
`aws/dist/awscli/botocore/data/cloudtrail/2013-11-01/endpoint-rule-set-1.json` | Configuration for 2013-11-01 | -
`aws/dist/awscli/botocore/data/cloudtrail/2013-11-01/paginators-1.json` | Configuration for 2013-11-01 | -
`aws/dist/awscli/botocore/data/cloudtrail/2013-11-01/service-2.json` | Configuration for 2013-11-01 | -
`aws/dist/awscli/botocore/data/cloudtrail-data/2021-08-11/endpoint-rule-set-1.json` | Configuration for 2021-08-11 | -
`aws/dist/awscli/botocore/data/cloudtrail-data/2021-08-11/paginators-1.json` | Configuration for 2021-08-11 | -
`aws/dist/awscli/botocore/data/cloudtrail-data/2021-08-11/service-2.json` | Configuration for 2021-08-11 | -
`aws/dist/awscli/botocore/data/cloudwatch/2010-08-01/endpoint-rule-set-1.json` | Configuration for 2010-08-01 | -
`aws/dist/awscli/botocore/data/cloudwatch/2010-08-01/paginators-1.json` | Configuration for 2010-08-01 | -
`aws/dist/awscli/botocore/data/cloudwatch/2010-08-01/service-2.json` | Configuration for 2010-08-01 | -
`aws/dist/awscli/botocore/data/cloudwatch/2010-08-01/waiters-2.json` | Configuration for 2010-08-01 | -
`aws/dist/awscli/botocore/data/codeartifact/2018-09-22/endpoint-rule-set-1.json` | Configuration for 2018-09-22 | -
`aws/dist/awscli/botocore/data/codeartifact/2018-09-22/paginators-1.json` | Configuration for 2018-09-22 | -
`aws/dist/awscli/botocore/data/codeartifact/2018-09-22/paginators-1.sdk-extras.json` | Configuration for 2018-09-22 | -
`aws/dist/awscli/botocore/data/codeartifact/2018-09-22/service-2.json` | Configuration for 2018-09-22 | -
`aws/dist/awscli/botocore/data/codebuild/2016-10-06/endpoint-rule-set-1.json` | Configuration for 2016-10-06 | -
`aws/dist/awscli/botocore/data/codebuild/2016-10-06/paginators-1.json` | Configuration for 2016-10-06 | -
`aws/dist/awscli/botocore/data/codebuild/2016-10-06/service-2.json` | Configuration for 2016-10-06 | -
`aws/dist/awscli/botocore/data/codecatalyst/2022-09-28/endpoint-rule-set-1.json` | Configuration for 2022-09-28 | -
`aws/dist/awscli/botocore/data/codecatalyst/2022-09-28/paginators-1.json` | Configuration for 2022-09-28 | -
`aws/dist/awscli/botocore/data/codecatalyst/2022-09-28/service-2.json` | Configuration for 2022-09-28 | -
`aws/dist/awscli/botocore/data/codecatalyst/2022-09-28/waiters-2.json` | Configuration for 2022-09-28 | -
`aws/dist/awscli/botocore/data/codecommit/2015-04-13/endpoint-rule-set-1.json` | Configuration for 2015-04-13 | -
`aws/dist/awscli/botocore/data/codecommit/2015-04-13/paginators-1.json` | Configuration for 2015-04-13 | -
`aws/dist/awscli/botocore/data/codecommit/2015-04-13/service-2.json` | Configuration for 2015-04-13 | -
`aws/dist/awscli/botocore/data/codeconnections/2023-12-01/endpoint-rule-set-1.json` | Configuration for 2023-12-01 | -
`aws/dist/awscli/botocore/data/codeconnections/2023-12-01/paginators-1.json` | Configuration for 2023-12-01 | -
`aws/dist/awscli/botocore/data/codeconnections/2023-12-01/service-2.json` | Configuration for 2023-12-01 | -
`aws/dist/awscli/botocore/data/codedeploy/2014-10-06/endpoint-rule-set-1.json` | Configuration for 2014-10-06 | -
`aws/dist/awscli/botocore/data/codedeploy/2014-10-06/paginators-1.json` | Configuration for 2014-10-06 | -
`aws/dist/awscli/botocore/data/codedeploy/2014-10-06/service-2.json` | Configuration for 2014-10-06 | -
`aws/dist/awscli/botocore/data/codedeploy/2014-10-06/waiters-2.json` | Configuration for 2014-10-06 | -
`aws/dist/awscli/botocore/data/codeguru-reviewer/2019-09-19/endpoint-rule-set-1.json` | Configuration for 2019-09-19 | -
`aws/dist/awscli/botocore/data/codeguru-reviewer/2019-09-19/paginators-1.json` | Configuration for 2019-09-19 | -
`aws/dist/awscli/botocore/data/codeguru-reviewer/2019-09-19/service-2.json` | Configuration for 2019-09-19 | -
`aws/dist/awscli/botocore/data/codeguru-reviewer/2019-09-19/waiters-2.json` | Configuration for 2019-09-19 | -
`aws/dist/awscli/botocore/data/codeguru-security/2018-05-10/endpoint-rule-set-1.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/codeguru-security/2018-05-10/paginators-1.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/codeguru-security/2018-05-10/service-2.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/codeguru-security/2018-05-10/waiters-2.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/codeguruprofiler/2019-07-18/endpoint-rule-set-1.json` | Configuration for 2019-07-18 | -
`aws/dist/awscli/botocore/data/codeguruprofiler/2019-07-18/paginators-1.json` | Configuration for 2019-07-18 | -
`aws/dist/awscli/botocore/data/codeguruprofiler/2019-07-18/service-2.json` | Configuration for 2019-07-18 | -
`aws/dist/awscli/botocore/data/codepipeline/2015-07-09/endpoint-rule-set-1.json` | Configuration for 2015-07-09 | -
`aws/dist/awscli/botocore/data/codepipeline/2015-07-09/paginators-1.json` | Configuration for 2015-07-09 | -
`aws/dist/awscli/botocore/data/codepipeline/2015-07-09/service-2.json` | Configuration for 2015-07-09 | -
`aws/dist/awscli/botocore/data/codestar-connections/2019-12-01/endpoint-rule-set-1.json` | Configuration for 2019-12-01 | -
`aws/dist/awscli/botocore/data/codestar-connections/2019-12-01/paginators-1.json` | Configuration for 2019-12-01 | -
`aws/dist/awscli/botocore/data/codestar-connections/2019-12-01/service-2.json` | Configuration for 2019-12-01 | -
`aws/dist/awscli/botocore/data/codestar-notifications/2019-10-15/endpoint-rule-set-1.json` | Configuration for 2019-10-15 | -
`aws/dist/awscli/botocore/data/codestar-notifications/2019-10-15/paginators-1.json` | Configuration for 2019-10-15 | -
`aws/dist/awscli/botocore/data/codestar-notifications/2019-10-15/service-2.json` | Configuration for 2019-10-15 | -
`aws/dist/awscli/botocore/data/cognito-identity/2014-06-30/endpoint-rule-set-1.json` | Configuration for 2014-06-30 | -
`aws/dist/awscli/botocore/data/cognito-identity/2014-06-30/paginators-1.json` | Configuration for 2014-06-30 | -
`aws/dist/awscli/botocore/data/cognito-identity/2014-06-30/service-2.json` | Configuration for 2014-06-30 | -
`aws/dist/awscli/botocore/data/cognito-idp/2016-04-18/endpoint-rule-set-1.json` | Configuration for 2016-04-18 | -
`aws/dist/awscli/botocore/data/cognito-idp/2016-04-18/paginators-1.json` | Configuration for 2016-04-18 | -
`aws/dist/awscli/botocore/data/cognito-idp/2016-04-18/service-2.json` | Configuration for 2016-04-18 | -
`aws/dist/awscli/botocore/data/cognito-sync/2014-06-30/endpoint-rule-set-1.json` | Configuration for 2014-06-30 | -
`aws/dist/awscli/botocore/data/cognito-sync/2014-06-30/paginators-1.json` | Configuration for 2014-06-30 | -
`aws/dist/awscli/botocore/data/cognito-sync/2014-06-30/service-2.json` | Configuration for 2014-06-30 | -
`aws/dist/awscli/botocore/data/comprehend/2017-11-27/endpoint-rule-set-1.json` | Configuration for 2017-11-27 | -
`aws/dist/awscli/botocore/data/comprehend/2017-11-27/paginators-1.json` | Configuration for 2017-11-27 | -
`aws/dist/awscli/botocore/data/comprehend/2017-11-27/service-2.json` | Configuration for 2017-11-27 | -
`aws/dist/awscli/botocore/data/comprehendmedical/2018-10-30/endpoint-rule-set-1.json` | Configuration for 2018-10-30 | -
`aws/dist/awscli/botocore/data/comprehendmedical/2018-10-30/paginators-1.json` | Configuration for 2018-10-30 | -
`aws/dist/awscli/botocore/data/comprehendmedical/2018-10-30/service-2.json` | Configuration for 2018-10-30 | -
`aws/dist/awscli/botocore/data/compute-optimizer/2019-11-01/endpoint-rule-set-1.json` | Configuration for 2019-11-01 | -
`aws/dist/awscli/botocore/data/compute-optimizer/2019-11-01/paginators-1.json` | Configuration for 2019-11-01 | -
`aws/dist/awscli/botocore/data/compute-optimizer/2019-11-01/service-2.json` | Configuration for 2019-11-01 | -
`aws/dist/awscli/botocore/data/compute-optimizer-automation/2025-09-22/endpoint-rule-set-1.json` | Configuration for 2025-09-22 | -
`aws/dist/awscli/botocore/data/compute-optimizer-automation/2025-09-22/paginators-1.json` | Configuration for 2025-09-22 | -
`aws/dist/awscli/botocore/data/compute-optimizer-automation/2025-09-22/service-2.json` | Configuration for 2025-09-22 | -
`aws/dist/awscli/botocore/data/compute-optimizer-automation/2025-09-22/waiters-2.json` | Configuration for 2025-09-22 | -
`aws/dist/awscli/botocore/data/config/2014-11-12/endpoint-rule-set-1.json` | Configuration for 2014-11-12 | -
`aws/dist/awscli/botocore/data/config/2014-11-12/paginators-1.json` | Configuration for 2014-11-12 | -
`aws/dist/awscli/botocore/data/config/2014-11-12/service-2.json` | Configuration for 2014-11-12 | -
`aws/dist/awscli/botocore/data/connect/2017-08-08/endpoint-rule-set-1.json` | Configuration for 2017-08-08 | -
`aws/dist/awscli/botocore/data/connect/2017-08-08/paginators-1.json` | Configuration for 2017-08-08 | -
`aws/dist/awscli/botocore/data/connect/2017-08-08/service-2.json` | Configuration for 2017-08-08 | -
`aws/dist/awscli/botocore/data/connect-contact-lens/2020-08-21/endpoint-rule-set-1.json` | Configuration for 2020-08-21 | -
`aws/dist/awscli/botocore/data/connect-contact-lens/2020-08-21/paginators-1.json` | Configuration for 2020-08-21 | -
`aws/dist/awscli/botocore/data/connect-contact-lens/2020-08-21/service-2.json` | Configuration for 2020-08-21 | -
`aws/dist/awscli/botocore/data/connectcampaigns/2021-01-30/endpoint-rule-set-1.json` | Configuration for 2021-01-30 | -
`aws/dist/awscli/botocore/data/connectcampaigns/2021-01-30/paginators-1.json` | Configuration for 2021-01-30 | -
`aws/dist/awscli/botocore/data/connectcampaigns/2021-01-30/service-2.json` | Configuration for 2021-01-30 | -
`aws/dist/awscli/botocore/data/connectcampaignsv2/2024-04-23/endpoint-rule-set-1.json` | Configuration for 2024-04-23 | -
`aws/dist/awscli/botocore/data/connectcampaignsv2/2024-04-23/paginators-1.json` | Configuration for 2024-04-23 | -
`aws/dist/awscli/botocore/data/connectcampaignsv2/2024-04-23/service-2.json` | Configuration for 2024-04-23 | -
`aws/dist/awscli/botocore/data/connectcases/2022-10-03/endpoint-rule-set-1.json` | Configuration for 2022-10-03 | -
`aws/dist/awscli/botocore/data/connectcases/2022-10-03/paginators-1.json` | Configuration for 2022-10-03 | -
`aws/dist/awscli/botocore/data/connectcases/2022-10-03/paginators-1.sdk-extras.json` | Configuration for 2022-10-03 | -
`aws/dist/awscli/botocore/data/connectcases/2022-10-03/service-2.json` | Configuration for 2022-10-03 | -
`aws/dist/awscli/botocore/data/connectcases/2022-10-03/waiters-2.json` | Configuration for 2022-10-03 | -
`aws/dist/awscli/botocore/data/connecthealth/2025-01-29/endpoint-rule-set-1.json` | Configuration for 2025-01-29 | -
`aws/dist/awscli/botocore/data/connecthealth/2025-01-29/paginators-1.json` | Configuration for 2025-01-29 | -
`aws/dist/awscli/botocore/data/connecthealth/2025-01-29/service-2.json` | Configuration for 2025-01-29 | -
`aws/dist/awscli/botocore/data/connecthealth/2025-01-29/waiters-2.json` | Configuration for 2025-01-29 | -
`aws/dist/awscli/botocore/data/connectparticipant/2018-09-07/endpoint-rule-set-1.json` | Configuration for 2018-09-07 | -
`aws/dist/awscli/botocore/data/connectparticipant/2018-09-07/paginators-1.json` | Configuration for 2018-09-07 | -
`aws/dist/awscli/botocore/data/connectparticipant/2018-09-07/service-2.json` | Configuration for 2018-09-07 | -
`aws/dist/awscli/botocore/data/controlcatalog/2018-05-10/endpoint-rule-set-1.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/controlcatalog/2018-05-10/paginators-1.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/controlcatalog/2018-05-10/service-2.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/controlcatalog/2018-05-10/waiters-2.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/controltower/2018-05-10/endpoint-rule-set-1.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/controltower/2018-05-10/paginators-1.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/controltower/2018-05-10/service-2.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/controltower/2018-05-10/waiters-2.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/cost-optimization-hub/2022-07-26/endpoint-rule-set-1.json` | Configuration for 2022-07-26 | -
`aws/dist/awscli/botocore/data/cost-optimization-hub/2022-07-26/paginators-1.json` | Configuration for 2022-07-26 | -
`aws/dist/awscli/botocore/data/cost-optimization-hub/2022-07-26/paginators-1.sdk-extras.json` | Configuration for 2022-07-26 | -
`aws/dist/awscli/botocore/data/cost-optimization-hub/2022-07-26/service-2.json` | Configuration for 2022-07-26 | -
`aws/dist/awscli/botocore/data/cost-optimization-hub/2022-07-26/waiters-2.json` | Configuration for 2022-07-26 | -
`aws/dist/awscli/botocore/data/cur/2017-01-06/endpoint-rule-set-1.json` | Configuration for 2017-01-06 | -
`aws/dist/awscli/botocore/data/cur/2017-01-06/paginators-1.json` | Configuration for 2017-01-06 | -
`aws/dist/awscli/botocore/data/cur/2017-01-06/service-2.json` | Configuration for 2017-01-06 | -
`aws/dist/awscli/botocore/data/customer-profiles/2020-08-15/endpoint-rule-set-1.json` | Configuration for 2020-08-15 | -
`aws/dist/awscli/botocore/data/customer-profiles/2020-08-15/paginators-1.json` | Configuration for 2020-08-15 | -
`aws/dist/awscli/botocore/data/customer-profiles/2020-08-15/paginators-1.sdk-extras.json` | Configuration for 2020-08-15 | -
`aws/dist/awscli/botocore/data/customer-profiles/2020-08-15/service-2.json` | Configuration for 2020-08-15 | -
`aws/dist/awscli/botocore/data/databrew/2017-07-25/endpoint-rule-set-1.json` | Configuration for 2017-07-25 | -
`aws/dist/awscli/botocore/data/databrew/2017-07-25/paginators-1.json` | Configuration for 2017-07-25 | -
`aws/dist/awscli/botocore/data/databrew/2017-07-25/service-2.json` | Configuration for 2017-07-25 | -
`aws/dist/awscli/botocore/data/dataexchange/2017-07-25/endpoint-rule-set-1.json` | Configuration for 2017-07-25 | -
`aws/dist/awscli/botocore/data/dataexchange/2017-07-25/paginators-1.json` | Configuration for 2017-07-25 | -
`aws/dist/awscli/botocore/data/dataexchange/2017-07-25/service-2.json` | Configuration for 2017-07-25 | -
`aws/dist/awscli/botocore/data/dataexchange/2017-07-25/waiters-2.json` | Configuration for 2017-07-25 | -
`aws/dist/awscli/botocore/data/datapipeline/2012-10-29/endpoint-rule-set-1.json` | Configuration for 2012-10-29 | -
`aws/dist/awscli/botocore/data/datapipeline/2012-10-29/paginators-1.json` | Configuration for 2012-10-29 | -
`aws/dist/awscli/botocore/data/datapipeline/2012-10-29/service-2.json` | Configuration for 2012-10-29 | -
`aws/dist/awscli/botocore/data/datasync/2018-11-09/endpoint-rule-set-1.json` | Configuration for 2018-11-09 | -
`aws/dist/awscli/botocore/data/datasync/2018-11-09/paginators-1.json` | Configuration for 2018-11-09 | -
`aws/dist/awscli/botocore/data/datasync/2018-11-09/service-2.json` | Configuration for 2018-11-09 | -
`aws/dist/awscli/botocore/data/datazone/2018-05-10/endpoint-rule-set-1.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/datazone/2018-05-10/paginators-1.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/datazone/2018-05-10/paginators-1.sdk-extras.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/datazone/2018-05-10/service-2.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/datazone/2018-05-10/waiters-2.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/dax/2017-04-19/endpoint-rule-set-1.json` | Configuration for 2017-04-19 | -
`aws/dist/awscli/botocore/data/dax/2017-04-19/paginators-1.json` | Configuration for 2017-04-19 | -
`aws/dist/awscli/botocore/data/dax/2017-04-19/service-2.json` | Configuration for 2017-04-19 | -
`aws/dist/awscli/botocore/data/deadline/2023-10-12/endpoint-rule-set-1.json` | Configuration for 2023-10-12 | -
`aws/dist/awscli/botocore/data/deadline/2023-10-12/paginators-1.json` | Configuration for 2023-10-12 | -
`aws/dist/awscli/botocore/data/deadline/2023-10-12/paginators-1.sdk-extras.json` | Configuration for 2023-10-12 | -
`aws/dist/awscli/botocore/data/deadline/2023-10-12/service-2.json` | Configuration for 2023-10-12 | -
`aws/dist/awscli/botocore/data/deadline/2023-10-12/waiters-2.json` | Configuration for 2023-10-12 | -
`aws/dist/awscli/botocore/data/detective/2018-10-26/endpoint-rule-set-1.json` | Configuration for 2018-10-26 | -
`aws/dist/awscli/botocore/data/detective/2018-10-26/paginators-1.json` | Configuration for 2018-10-26 | -
`aws/dist/awscli/botocore/data/detective/2018-10-26/service-2.json` | Configuration for 2018-10-26 | -
`aws/dist/awscli/botocore/data/devicefarm/2015-06-23/endpoint-rule-set-1.json` | Configuration for 2015-06-23 | -
`aws/dist/awscli/botocore/data/devicefarm/2015-06-23/paginators-1.json` | Configuration for 2015-06-23 | -
`aws/dist/awscli/botocore/data/devicefarm/2015-06-23/service-2.json` | Configuration for 2015-06-23 | -
`aws/dist/awscli/botocore/data/devops-agent/2026-01-01/endpoint-rule-set-1.json` | Configuration for 2026-01-01 | -
`aws/dist/awscli/botocore/data/devops-agent/2026-01-01/paginators-1.json` | Configuration for 2026-01-01 | -
`aws/dist/awscli/botocore/data/devops-agent/2026-01-01/service-2.json` | Configuration for 2026-01-01 | -
`aws/dist/awscli/botocore/data/devops-guru/2020-12-01/endpoint-rule-set-1.json` | Configuration for 2020-12-01 | -
`aws/dist/awscli/botocore/data/devops-guru/2020-12-01/paginators-1.json` | Configuration for 2020-12-01 | -
`aws/dist/awscli/botocore/data/devops-guru/2020-12-01/service-2.json` | Configuration for 2020-12-01 | -
`aws/dist/awscli/botocore/data/directconnect/2012-10-25/endpoint-rule-set-1.json` | Configuration for 2012-10-25 | -
`aws/dist/awscli/botocore/data/directconnect/2012-10-25/paginators-1.json` | Configuration for 2012-10-25 | -
`aws/dist/awscli/botocore/data/directconnect/2012-10-25/service-2.json` | Configuration for 2012-10-25 | -
`aws/dist/awscli/botocore/data/discovery/2015-11-01/endpoint-rule-set-1.json` | Configuration for 2015-11-01 | -
`aws/dist/awscli/botocore/data/discovery/2015-11-01/paginators-1.json` | Configuration for 2015-11-01 | -
`aws/dist/awscli/botocore/data/discovery/2015-11-01/service-2.json` | Configuration for 2015-11-01 | -
`aws/dist/awscli/botocore/data/dlm/2018-01-12/endpoint-rule-set-1.json` | Configuration for 2018-01-12 | -
`aws/dist/awscli/botocore/data/dlm/2018-01-12/paginators-1.json` | Configuration for 2018-01-12 | -
`aws/dist/awscli/botocore/data/dlm/2018-01-12/service-2.json` | Configuration for 2018-01-12 | -
`aws/dist/awscli/botocore/data/dms/2016-01-01/endpoint-rule-set-1.json` | Configuration for 2016-01-01 | -
`aws/dist/awscli/botocore/data/dms/2016-01-01/paginators-1.json` | Configuration for 2016-01-01 | -
`aws/dist/awscli/botocore/data/dms/2016-01-01/service-2.json` | Configuration for 2016-01-01 | -
`aws/dist/awscli/botocore/data/dms/2016-01-01/waiters-2.json` | Configuration for 2016-01-01 | -
`aws/dist/awscli/botocore/data/docdb/2014-10-31/endpoint-rule-set-1.json` | Configuration for 2014-10-31 | -
`aws/dist/awscli/botocore/data/docdb/2014-10-31/paginators-1.json` | Configuration for 2014-10-31 | -
`aws/dist/awscli/botocore/data/docdb/2014-10-31/service-2.json` | Configuration for 2014-10-31 | -
`aws/dist/awscli/botocore/data/docdb/2014-10-31/service-2.sdk-extras.json` | Configuration for 2014-10-31 | -
`aws/dist/awscli/botocore/data/docdb/2014-10-31/waiters-2.json` | Configuration for 2014-10-31 | -
`aws/dist/awscli/botocore/data/docdb-elastic/2022-11-28/endpoint-rule-set-1.json` | Configuration for 2022-11-28 | -
`aws/dist/awscli/botocore/data/docdb-elastic/2022-11-28/paginators-1.json` | Configuration for 2022-11-28 | -
`aws/dist/awscli/botocore/data/docdb-elastic/2022-11-28/service-2.json` | Configuration for 2022-11-28 | -
`aws/dist/awscli/botocore/data/drs/2020-02-26/endpoint-rule-set-1.json` | Configuration for 2020-02-26 | -
`aws/dist/awscli/botocore/data/drs/2020-02-26/paginators-1.json` | Configuration for 2020-02-26 | -
`aws/dist/awscli/botocore/data/drs/2020-02-26/service-2.json` | Configuration for 2020-02-26 | -
`aws/dist/awscli/botocore/data/ds/2015-04-16/endpoint-rule-set-1.json` | Configuration for 2015-04-16 | -
`aws/dist/awscli/botocore/data/ds/2015-04-16/paginators-1.json` | Configuration for 2015-04-16 | -
`aws/dist/awscli/botocore/data/ds/2015-04-16/service-2.json` | Configuration for 2015-04-16 | -
`aws/dist/awscli/botocore/data/ds/2015-04-16/waiters-2.json` | Configuration for 2015-04-16 | -
`aws/dist/awscli/botocore/data/ds-data/2023-05-31/endpoint-rule-set-1.json` | Configuration for 2023-05-31 | -
`aws/dist/awscli/botocore/data/ds-data/2023-05-31/paginators-1.json` | Configuration for 2023-05-31 | -
`aws/dist/awscli/botocore/data/ds-data/2023-05-31/paginators-1.sdk-extras.json` | Configuration for 2023-05-31 | -
`aws/dist/awscli/botocore/data/ds-data/2023-05-31/service-2.json` | Configuration for 2023-05-31 | -
`aws/dist/awscli/botocore/data/dsql/2018-05-10/endpoint-rule-set-1.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/dsql/2018-05-10/paginators-1.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/dsql/2018-05-10/service-2.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/dsql/2018-05-10/waiters-2.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/dynamodb/2012-08-10/endpoint-rule-set-1.json` | Configuration for 2012-08-10 | -
`aws/dist/awscli/botocore/data/dynamodb/2012-08-10/paginators-1.json` | Configuration for 2012-08-10 | -
`aws/dist/awscli/botocore/data/dynamodb/2012-08-10/service-2.json` | Configuration for 2012-08-10 | -
`aws/dist/awscli/botocore/data/dynamodb/2012-08-10/waiters-2.json` | Configuration for 2012-08-10 | -
`aws/dist/awscli/botocore/data/dynamodbstreams/2012-08-10/endpoint-rule-set-1.json` | Configuration for 2012-08-10 | -
`aws/dist/awscli/botocore/data/dynamodbstreams/2012-08-10/paginators-1.json` | Configuration for 2012-08-10 | -
`aws/dist/awscli/botocore/data/dynamodbstreams/2012-08-10/service-2.json` | Configuration for 2012-08-10 | -
`aws/dist/awscli/botocore/data/ebs/2019-11-02/endpoint-rule-set-1.json` | Configuration for 2019-11-02 | -
`aws/dist/awscli/botocore/data/ebs/2019-11-02/paginators-1.json` | Configuration for 2019-11-02 | -
`aws/dist/awscli/botocore/data/ebs/2019-11-02/service-2.json` | Configuration for 2019-11-02 | -
`aws/dist/awscli/botocore/data/ec2/2016-11-15/endpoint-rule-set-1.json` | Configuration for 2016-11-15 | -
`aws/dist/awscli/botocore/data/ec2/2016-11-15/paginators-1.json` | Configuration for 2016-11-15 | -
`aws/dist/awscli/botocore/data/ec2/2016-11-15/paginators-1.sdk-extras.json` | Configuration for 2016-11-15 | -
`aws/dist/awscli/botocore/data/ec2/2016-11-15/service-2.json` | Configuration for 2016-11-15 | -
`aws/dist/awscli/botocore/data/ec2/2016-11-15/waiters-2.json` | Configuration for 2016-11-15 | -
`aws/dist/awscli/botocore/data/ec2-instance-connect/2018-04-02/endpoint-rule-set-1.json` | Configuration for 2018-04-02 | -
`aws/dist/awscli/botocore/data/ec2-instance-connect/2018-04-02/paginators-1.json` | Configuration for 2018-04-02 | -
`aws/dist/awscli/botocore/data/ec2-instance-connect/2018-04-02/service-2.json` | Configuration for 2018-04-02 | -
`aws/dist/awscli/botocore/data/ecr/2015-09-21/endpoint-rule-set-1.json` | Configuration for 2015-09-21 | -
`aws/dist/awscli/botocore/data/ecr/2015-09-21/paginators-1.json` | Configuration for 2015-09-21 | -
`aws/dist/awscli/botocore/data/ecr/2015-09-21/service-2.json` | Configuration for 2015-09-21 | -
`aws/dist/awscli/botocore/data/ecr/2015-09-21/waiters-2.json` | Configuration for 2015-09-21 | -
`aws/dist/awscli/botocore/data/ecr-public/2020-10-30/endpoint-rule-set-1.json` | Configuration for 2020-10-30 | -
`aws/dist/awscli/botocore/data/ecr-public/2020-10-30/paginators-1.json` | Configuration for 2020-10-30 | -
`aws/dist/awscli/botocore/data/ecr-public/2020-10-30/service-2.json` | Configuration for 2020-10-30 | -
`aws/dist/awscli/botocore/data/ecs/2014-11-13/endpoint-rule-set-1.json` | Configuration for 2014-11-13 | -
`aws/dist/awscli/botocore/data/ecs/2014-11-13/paginators-1.json` | Configuration for 2014-11-13 | -
`aws/dist/awscli/botocore/data/ecs/2014-11-13/service-2.json` | Configuration for 2014-11-13 | -
`aws/dist/awscli/botocore/data/ecs/2014-11-13/waiters-2.json` | Configuration for 2014-11-13 | -
`aws/dist/awscli/botocore/data/efs/2015-02-01/endpoint-rule-set-1.json` | Configuration for 2015-02-01 | -
`aws/dist/awscli/botocore/data/efs/2015-02-01/paginators-1.json` | Configuration for 2015-02-01 | -
`aws/dist/awscli/botocore/data/efs/2015-02-01/service-2.json` | Configuration for 2015-02-01 | -
`aws/dist/awscli/botocore/data/eks/2017-11-01/endpoint-rule-set-1.json` | Configuration for 2017-11-01 | -
`aws/dist/awscli/botocore/data/eks/2017-11-01/paginators-1.json` | Configuration for 2017-11-01 | -
`aws/dist/awscli/botocore/data/eks/2017-11-01/service-2.json` | Configuration for 2017-11-01 | -
`aws/dist/awscli/botocore/data/eks/2017-11-01/service-2.sdk-extras.json` | Configuration for 2017-11-01 | -
`aws/dist/awscli/botocore/data/eks/2017-11-01/waiters-2.json` | Configuration for 2017-11-01 | -
`aws/dist/awscli/botocore/data/eks-auth/2023-11-26/endpoint-rule-set-1.json` | Configuration for 2023-11-26 | -
`aws/dist/awscli/botocore/data/eks-auth/2023-11-26/paginators-1.json` | Configuration for 2023-11-26 | -
`aws/dist/awscli/botocore/data/eks-auth/2023-11-26/service-2.json` | Configuration for 2023-11-26 | -
`aws/dist/awscli/botocore/data/eks-auth/2023-11-26/waiters-2.json` | Configuration for 2023-11-26 | -
`aws/dist/awscli/botocore/data/elasticache/2015-02-02/endpoint-rule-set-1.json` | Configuration for 2015-02-02 | -
`aws/dist/awscli/botocore/data/elasticache/2015-02-02/paginators-1.json` | Configuration for 2015-02-02 | -
`aws/dist/awscli/botocore/data/elasticache/2015-02-02/service-2.json` | Configuration for 2015-02-02 | -
`aws/dist/awscli/botocore/data/elasticache/2015-02-02/waiters-2.json` | Configuration for 2015-02-02 | -
`aws/dist/awscli/botocore/data/elasticbeanstalk/2010-12-01/endpoint-rule-set-1.json` | Configuration for 2010-12-01 | -
`aws/dist/awscli/botocore/data/elasticbeanstalk/2010-12-01/paginators-1.json` | Configuration for 2010-12-01 | -
`aws/dist/awscli/botocore/data/elasticbeanstalk/2010-12-01/service-2.json` | Configuration for 2010-12-01 | -
`aws/dist/awscli/botocore/data/elasticbeanstalk/2010-12-01/waiters-2.json` | Configuration for 2010-12-01 | -
`aws/dist/awscli/botocore/data/elb/2012-06-01/endpoint-rule-set-1.json` | Configuration for 2012-06-01 | -
`aws/dist/awscli/botocore/data/elb/2012-06-01/paginators-1.json` | Configuration for 2012-06-01 | -
`aws/dist/awscli/botocore/data/elb/2012-06-01/service-2.json` | Configuration for 2012-06-01 | -
`aws/dist/awscli/botocore/data/elb/2012-06-01/waiters-2.json` | Configuration for 2012-06-01 | -
`aws/dist/awscli/botocore/data/elbv2/2015-12-01/endpoint-rule-set-1.json` | Configuration for 2015-12-01 | -
`aws/dist/awscli/botocore/data/elbv2/2015-12-01/paginators-1.json` | Configuration for 2015-12-01 | -
`aws/dist/awscli/botocore/data/elbv2/2015-12-01/service-2.json` | Configuration for 2015-12-01 | -
`aws/dist/awscli/botocore/data/elbv2/2015-12-01/waiters-2.json` | Configuration for 2015-12-01 | -
`aws/dist/awscli/botocore/data/elementalinference/2018-11-14/endpoint-rule-set-1.json` | Configuration for 2018-11-14 | -
`aws/dist/awscli/botocore/data/elementalinference/2018-11-14/paginators-1.json` | Configuration for 2018-11-14 | -
`aws/dist/awscli/botocore/data/elementalinference/2018-11-14/service-2.json` | Configuration for 2018-11-14 | -
`aws/dist/awscli/botocore/data/elementalinference/2018-11-14/waiters-2.json` | Configuration for 2018-11-14 | -
`aws/dist/awscli/botocore/data/emr/2009-03-31/endpoint-rule-set-1.json` | Configuration for 2009-03-31 | -
`aws/dist/awscli/botocore/data/emr/2009-03-31/paginators-1.json` | Configuration for 2009-03-31 | -
`aws/dist/awscli/botocore/data/emr/2009-03-31/service-2.json` | Configuration for 2009-03-31 | -
`aws/dist/awscli/botocore/data/emr/2009-03-31/waiters-2.json` | Configuration for 2009-03-31 | -
`aws/dist/awscli/botocore/data/emr-containers/2020-10-01/endpoint-rule-set-1.json` | Configuration for 2020-10-01 | -
`aws/dist/awscli/botocore/data/emr-containers/2020-10-01/paginators-1.json` | Configuration for 2020-10-01 | -
`aws/dist/awscli/botocore/data/emr-containers/2020-10-01/service-2.json` | Configuration for 2020-10-01 | -
`aws/dist/awscli/botocore/data/emr-serverless/2021-07-13/endpoint-rule-set-1.json` | Configuration for 2021-07-13 | -
`aws/dist/awscli/botocore/data/emr-serverless/2021-07-13/paginators-1.json` | Configuration for 2021-07-13 | -
`aws/dist/awscli/botocore/data/emr-serverless/2021-07-13/service-2.json` | Configuration for 2021-07-13 | -
`aws/dist/awscli/botocore/data/endpoints.json` | Configuration for data | -
`aws/dist/awscli/botocore/data/entityresolution/2018-05-10/endpoint-rule-set-1.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/entityresolution/2018-05-10/paginators-1.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/entityresolution/2018-05-10/service-2.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/es/2015-01-01/endpoint-rule-set-1.json` | Configuration for 2015-01-01 | -
`aws/dist/awscli/botocore/data/es/2015-01-01/paginators-1.json` | Configuration for 2015-01-01 | -
`aws/dist/awscli/botocore/data/es/2015-01-01/service-2.json` | Configuration for 2015-01-01 | -
`aws/dist/awscli/botocore/data/events/2015-10-07/endpoint-rule-set-1.json` | Configuration for 2015-10-07 | -
`aws/dist/awscli/botocore/data/events/2015-10-07/paginators-1.json` | Configuration for 2015-10-07 | -
`aws/dist/awscli/botocore/data/events/2015-10-07/service-2.json` | Configuration for 2015-10-07 | -
`aws/dist/awscli/botocore/data/evs/2023-07-27/endpoint-rule-set-1.json` | Configuration for 2023-07-27 | -
`aws/dist/awscli/botocore/data/evs/2023-07-27/paginators-1.json` | Configuration for 2023-07-27 | -
`aws/dist/awscli/botocore/data/evs/2023-07-27/service-2.json` | Configuration for 2023-07-27 | -
`aws/dist/awscli/botocore/data/evs/2023-07-27/waiters-2.json` | Configuration for 2023-07-27 | -
`aws/dist/awscli/botocore/data/finspace/2021-03-12/endpoint-rule-set-1.json` | Configuration for 2021-03-12 | -
`aws/dist/awscli/botocore/data/finspace/2021-03-12/paginators-1.json` | Configuration for 2021-03-12 | -
`aws/dist/awscli/botocore/data/finspace/2021-03-12/service-2.json` | Configuration for 2021-03-12 | -
`aws/dist/awscli/botocore/data/finspace-data/2020-07-13/endpoint-rule-set-1.json` | Configuration for 2020-07-13 | -
`aws/dist/awscli/botocore/data/finspace-data/2020-07-13/paginators-1.json` | Configuration for 2020-07-13 | -
`aws/dist/awscli/botocore/data/finspace-data/2020-07-13/service-2.json` | Configuration for 2020-07-13 | -
`aws/dist/awscli/botocore/data/firehose/2015-08-04/endpoint-rule-set-1.json` | Configuration for 2015-08-04 | -
`aws/dist/awscli/botocore/data/firehose/2015-08-04/paginators-1.json` | Configuration for 2015-08-04 | -
`aws/dist/awscli/botocore/data/firehose/2015-08-04/service-2.json` | Configuration for 2015-08-04 | -
`aws/dist/awscli/botocore/data/fis/2020-12-01/endpoint-rule-set-1.json` | Configuration for 2020-12-01 | -
`aws/dist/awscli/botocore/data/fis/2020-12-01/paginators-1.json` | Configuration for 2020-12-01 | -
`aws/dist/awscli/botocore/data/fis/2020-12-01/service-2.json` | Configuration for 2020-12-01 | -
`aws/dist/awscli/botocore/data/fms/2018-01-01/endpoint-rule-set-1.json` | Configuration for 2018-01-01 | -
`aws/dist/awscli/botocore/data/fms/2018-01-01/paginators-1.json` | Configuration for 2018-01-01 | -
`aws/dist/awscli/botocore/data/fms/2018-01-01/service-2.json` | Configuration for 2018-01-01 | -
`aws/dist/awscli/botocore/data/forecast/2018-06-26/endpoint-rule-set-1.json` | Configuration for 2018-06-26 | -
`aws/dist/awscli/botocore/data/forecast/2018-06-26/paginators-1.json` | Configuration for 2018-06-26 | -
`aws/dist/awscli/botocore/data/forecast/2018-06-26/service-2.json` | Configuration for 2018-06-26 | -
`aws/dist/awscli/botocore/data/forecastquery/2018-06-26/endpoint-rule-set-1.json` | Configuration for 2018-06-26 | -
`aws/dist/awscli/botocore/data/forecastquery/2018-06-26/paginators-1.json` | Configuration for 2018-06-26 | -
`aws/dist/awscli/botocore/data/forecastquery/2018-06-26/service-2.json` | Configuration for 2018-06-26 | -
`aws/dist/awscli/botocore/data/frauddetector/2019-11-15/endpoint-rule-set-1.json` | Configuration for 2019-11-15 | -
`aws/dist/awscli/botocore/data/frauddetector/2019-11-15/paginators-1.json` | Configuration for 2019-11-15 | -
`aws/dist/awscli/botocore/data/frauddetector/2019-11-15/service-2.json` | Configuration for 2019-11-15 | -
`aws/dist/awscli/botocore/data/freetier/2023-09-07/endpoint-rule-set-1.json` | Configuration for 2023-09-07 | -
`aws/dist/awscli/botocore/data/freetier/2023-09-07/paginators-1.json` | Configuration for 2023-09-07 | -
`aws/dist/awscli/botocore/data/freetier/2023-09-07/service-2.json` | Configuration for 2023-09-07 | -
`aws/dist/awscli/botocore/data/freetier/2023-09-07/waiters-2.json` | Configuration for 2023-09-07 | -
`aws/dist/awscli/botocore/data/fsx/2018-03-01/endpoint-rule-set-1.json` | Configuration for 2018-03-01 | -
`aws/dist/awscli/botocore/data/fsx/2018-03-01/paginators-1.json` | Configuration for 2018-03-01 | -
`aws/dist/awscli/botocore/data/fsx/2018-03-01/service-2.json` | Configuration for 2018-03-01 | -
`aws/dist/awscli/botocore/data/gamelift/2015-10-01/endpoint-rule-set-1.json` | Configuration for 2015-10-01 | -
`aws/dist/awscli/botocore/data/gamelift/2015-10-01/paginators-1.json` | Configuration for 2015-10-01 | -
`aws/dist/awscli/botocore/data/gamelift/2015-10-01/service-2.json` | Configuration for 2015-10-01 | -
`aws/dist/awscli/botocore/data/gameliftstreams/2018-05-10/endpoint-rule-set-1.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/gameliftstreams/2018-05-10/paginators-1.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/gameliftstreams/2018-05-10/service-2.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/gameliftstreams/2018-05-10/waiters-2.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/geo-maps/2020-11-19/endpoint-rule-set-1.json` | Configuration for 2020-11-19 | -
`aws/dist/awscli/botocore/data/geo-maps/2020-11-19/paginators-1.json` | Configuration for 2020-11-19 | -
`aws/dist/awscli/botocore/data/geo-maps/2020-11-19/service-2.json` | Configuration for 2020-11-19 | -
`aws/dist/awscli/botocore/data/geo-maps/2020-11-19/waiters-2.json` | Configuration for 2020-11-19 | -
`aws/dist/awscli/botocore/data/geo-places/2020-11-19/endpoint-rule-set-1.json` | Configuration for 2020-11-19 | -
`aws/dist/awscli/botocore/data/geo-places/2020-11-19/paginators-1.json` | Configuration for 2020-11-19 | -
`aws/dist/awscli/botocore/data/geo-places/2020-11-19/service-2.json` | Configuration for 2020-11-19 | -
`aws/dist/awscli/botocore/data/geo-places/2020-11-19/waiters-2.json` | Configuration for 2020-11-19 | -
`aws/dist/awscli/botocore/data/geo-routes/2020-11-19/endpoint-rule-set-1.json` | Configuration for 2020-11-19 | -
`aws/dist/awscli/botocore/data/geo-routes/2020-11-19/paginators-1.json` | Configuration for 2020-11-19 | -
`aws/dist/awscli/botocore/data/geo-routes/2020-11-19/service-2.json` | Configuration for 2020-11-19 | -
`aws/dist/awscli/botocore/data/geo-routes/2020-11-19/waiters-2.json` | Configuration for 2020-11-19 | -
`aws/dist/awscli/botocore/data/glacier/2012-06-01/endpoint-rule-set-1.json` | Configuration for 2012-06-01 | -
`aws/dist/awscli/botocore/data/glacier/2012-06-01/paginators-1.json` | Configuration for 2012-06-01 | -
`aws/dist/awscli/botocore/data/glacier/2012-06-01/service-2.json` | Configuration for 2012-06-01 | -
`aws/dist/awscli/botocore/data/glacier/2012-06-01/waiters-2.json` | Configuration for 2012-06-01 | -
`aws/dist/awscli/botocore/data/globalaccelerator/2018-08-08/endpoint-rule-set-1.json` | Configuration for 2018-08-08 | -
`aws/dist/awscli/botocore/data/globalaccelerator/2018-08-08/paginators-1.json` | Configuration for 2018-08-08 | -
`aws/dist/awscli/botocore/data/globalaccelerator/2018-08-08/service-2.json` | Configuration for 2018-08-08 | -
`aws/dist/awscli/botocore/data/glue/2017-03-31/endpoint-rule-set-1.json` | Configuration for 2017-03-31 | -
`aws/dist/awscli/botocore/data/glue/2017-03-31/paginators-1.json` | Configuration for 2017-03-31 | -
`aws/dist/awscli/botocore/data/glue/2017-03-31/paginators-1.sdk-extras.json` | Configuration for 2017-03-31 | -
`aws/dist/awscli/botocore/data/glue/2017-03-31/service-2.json` | Configuration for 2017-03-31 | -
`aws/dist/awscli/botocore/data/grafana/2020-08-18/endpoint-rule-set-1.json` | Configuration for 2020-08-18 | -
`aws/dist/awscli/botocore/data/grafana/2020-08-18/paginators-1.json` | Configuration for 2020-08-18 | -
`aws/dist/awscli/botocore/data/grafana/2020-08-18/paginators-1.sdk-extras.json` | Configuration for 2020-08-18 | -
`aws/dist/awscli/botocore/data/grafana/2020-08-18/service-2.json` | Configuration for 2020-08-18 | -
`aws/dist/awscli/botocore/data/grafana/2020-08-18/waiters-2.json` | Configuration for 2020-08-18 | -
`aws/dist/awscli/botocore/data/greengrass/2017-06-07/endpoint-rule-set-1.json` | Configuration for 2017-06-07 | -
`aws/dist/awscli/botocore/data/greengrass/2017-06-07/paginators-1.json` | Configuration for 2017-06-07 | -
`aws/dist/awscli/botocore/data/greengrass/2017-06-07/service-2.json` | Configuration for 2017-06-07 | -
`aws/dist/awscli/botocore/data/greengrassv2/2020-11-30/endpoint-rule-set-1.json` | Configuration for 2020-11-30 | -
`aws/dist/awscli/botocore/data/greengrassv2/2020-11-30/paginators-1.json` | Configuration for 2020-11-30 | -
`aws/dist/awscli/botocore/data/greengrassv2/2020-11-30/service-2.json` | Configuration for 2020-11-30 | -
`aws/dist/awscli/botocore/data/groundstation/2019-05-23/endpoint-rule-set-1.json` | Configuration for 2019-05-23 | -
`aws/dist/awscli/botocore/data/groundstation/2019-05-23/paginators-1.json` | Configuration for 2019-05-23 | -
`aws/dist/awscli/botocore/data/groundstation/2019-05-23/service-2.json` | Configuration for 2019-05-23 | -
`aws/dist/awscli/botocore/data/groundstation/2019-05-23/waiters-2.json` | Configuration for 2019-05-23 | -
`aws/dist/awscli/botocore/data/guardduty/2017-11-28/endpoint-rule-set-1.json` | Configuration for 2017-11-28 | -
`aws/dist/awscli/botocore/data/guardduty/2017-11-28/paginators-1.json` | Configuration for 2017-11-28 | -
`aws/dist/awscli/botocore/data/guardduty/2017-11-28/service-2.json` | Configuration for 2017-11-28 | -
`aws/dist/awscli/botocore/data/health/2016-08-04/endpoint-rule-set-1.json` | Configuration for 2016-08-04 | -
`aws/dist/awscli/botocore/data/health/2016-08-04/paginators-1.json` | Configuration for 2016-08-04 | -
`aws/dist/awscli/botocore/data/health/2016-08-04/service-2.json` | Configuration for 2016-08-04 | -
`aws/dist/awscli/botocore/data/healthlake/2017-07-01/endpoint-rule-set-1.json` | Configuration for 2017-07-01 | -
`aws/dist/awscli/botocore/data/healthlake/2017-07-01/paginators-1.json` | Configuration for 2017-07-01 | -
`aws/dist/awscli/botocore/data/healthlake/2017-07-01/service-2.json` | Configuration for 2017-07-01 | -
`aws/dist/awscli/botocore/data/healthlake/2017-07-01/waiters-2.json` | Configuration for 2017-07-01 | -
`aws/dist/awscli/botocore/data/iam/2010-05-08/endpoint-rule-set-1.json` | Configuration for 2010-05-08 | -
`aws/dist/awscli/botocore/data/iam/2010-05-08/paginators-1.json` | Configuration for 2010-05-08 | -
`aws/dist/awscli/botocore/data/iam/2010-05-08/service-2.json` | Configuration for 2010-05-08 | -
`aws/dist/awscli/botocore/data/iam/2010-05-08/waiters-2.json` | Configuration for 2010-05-08 | -
`aws/dist/awscli/botocore/data/identitystore/2020-06-15/endpoint-rule-set-1.json` | Configuration for 2020-06-15 | -
`aws/dist/awscli/botocore/data/identitystore/2020-06-15/paginators-1.json` | Configuration for 2020-06-15 | -
`aws/dist/awscli/botocore/data/identitystore/2020-06-15/service-2.json` | Configuration for 2020-06-15 | -
`aws/dist/awscli/botocore/data/imagebuilder/2019-12-02/endpoint-rule-set-1.json` | Configuration for 2019-12-02 | -
`aws/dist/awscli/botocore/data/imagebuilder/2019-12-02/paginators-1.json` | Configuration for 2019-12-02 | -
`aws/dist/awscli/botocore/data/imagebuilder/2019-12-02/paginators-1.sdk-extras.json` | Configuration for 2019-12-02 | -
`aws/dist/awscli/botocore/data/imagebuilder/2019-12-02/service-2.json` | Configuration for 2019-12-02 | -
`aws/dist/awscli/botocore/data/importexport/2010-06-01/endpoint-rule-set-1.json` | Configuration for 2010-06-01 | -
`aws/dist/awscli/botocore/data/importexport/2010-06-01/paginators-1.json` | Configuration for 2010-06-01 | -
`aws/dist/awscli/botocore/data/importexport/2010-06-01/service-2.json` | Configuration for 2010-06-01 | -
`aws/dist/awscli/botocore/data/inspector/2016-02-16/endpoint-rule-set-1.json` | Configuration for 2016-02-16 | -
`aws/dist/awscli/botocore/data/inspector/2016-02-16/paginators-1.json` | Configuration for 2016-02-16 | -
`aws/dist/awscli/botocore/data/inspector/2016-02-16/service-2.json` | Configuration for 2016-02-16 | -
`aws/dist/awscli/botocore/data/inspector-scan/2023-08-08/endpoint-rule-set-1.json` | Configuration for 2023-08-08 | -
`aws/dist/awscli/botocore/data/inspector-scan/2023-08-08/paginators-1.json` | Configuration for 2023-08-08 | -
`aws/dist/awscli/botocore/data/inspector-scan/2023-08-08/service-2.json` | Configuration for 2023-08-08 | -
`aws/dist/awscli/botocore/data/inspector2/2020-06-08/endpoint-rule-set-1.json` | Configuration for 2020-06-08 | -
`aws/dist/awscli/botocore/data/inspector2/2020-06-08/paginators-1.json` | Configuration for 2020-06-08 | -
`aws/dist/awscli/botocore/data/inspector2/2020-06-08/paginators-1.sdk-extras.json` | Configuration for 2020-06-08 | -
`aws/dist/awscli/botocore/data/inspector2/2020-06-08/service-2.json` | Configuration for 2020-06-08 | -
`aws/dist/awscli/botocore/data/interconnect/2022-07-26/endpoint-rule-set-1.json` | Configuration for 2022-07-26 | -
`aws/dist/awscli/botocore/data/interconnect/2022-07-26/paginators-1.json` | Configuration for 2022-07-26 | -
`aws/dist/awscli/botocore/data/interconnect/2022-07-26/service-2.json` | Configuration for 2022-07-26 | -
`aws/dist/awscli/botocore/data/interconnect/2022-07-26/waiters-2.json` | Configuration for 2022-07-26 | -
`aws/dist/awscli/botocore/data/internetmonitor/2021-06-03/endpoint-rule-set-1.json` | Configuration for 2021-06-03 | -
`aws/dist/awscli/botocore/data/internetmonitor/2021-06-03/paginators-1.json` | Configuration for 2021-06-03 | -
`aws/dist/awscli/botocore/data/internetmonitor/2021-06-03/service-2.json` | Configuration for 2021-06-03 | -
`aws/dist/awscli/botocore/data/internetmonitor/2021-06-03/waiters-2.json` | Configuration for 2021-06-03 | -
`aws/dist/awscli/botocore/data/invoicing/2024-12-01/endpoint-rule-set-1.json` | Configuration for 2024-12-01 | -
`aws/dist/awscli/botocore/data/invoicing/2024-12-01/paginators-1.json` | Configuration for 2024-12-01 | -
`aws/dist/awscli/botocore/data/invoicing/2024-12-01/service-2.json` | Configuration for 2024-12-01 | -
`aws/dist/awscli/botocore/data/invoicing/2024-12-01/waiters-2.json` | Configuration for 2024-12-01 | -
`aws/dist/awscli/botocore/data/iot/2015-05-28/endpoint-rule-set-1.json` | Configuration for 2015-05-28 | -
`aws/dist/awscli/botocore/data/iot/2015-05-28/paginators-1.json` | Configuration for 2015-05-28 | -
`aws/dist/awscli/botocore/data/iot/2015-05-28/service-2.json` | Configuration for 2015-05-28 | -
`aws/dist/awscli/botocore/data/iot-data/2015-05-28/endpoint-rule-set-1.json` | Configuration for 2015-05-28 | -
`aws/dist/awscli/botocore/data/iot-data/2015-05-28/paginators-1.json` | Configuration for 2015-05-28 | -
`aws/dist/awscli/botocore/data/iot-data/2015-05-28/service-2.json` | Configuration for 2015-05-28 | -
`aws/dist/awscli/botocore/data/iot-jobs-data/2017-09-29/endpoint-rule-set-1.json` | Configuration for 2017-09-29 | -
`aws/dist/awscli/botocore/data/iot-jobs-data/2017-09-29/paginators-1.json` | Configuration for 2017-09-29 | -
`aws/dist/awscli/botocore/data/iot-jobs-data/2017-09-29/service-2.json` | Configuration for 2017-09-29 | -
`aws/dist/awscli/botocore/data/iot-managed-integrations/2025-03-03/endpoint-rule-set-1.json` | Configuration for 2025-03-03 | -
`aws/dist/awscli/botocore/data/iot-managed-integrations/2025-03-03/paginators-1.json` | Configuration for 2025-03-03 | -
`aws/dist/awscli/botocore/data/iot-managed-integrations/2025-03-03/service-2.json` | Configuration for 2025-03-03 | -
`aws/dist/awscli/botocore/data/iotdeviceadvisor/2020-09-18/endpoint-rule-set-1.json` | Configuration for 2020-09-18 | -
`aws/dist/awscli/botocore/data/iotdeviceadvisor/2020-09-18/paginators-1.json` | Configuration for 2020-09-18 | -
`aws/dist/awscli/botocore/data/iotdeviceadvisor/2020-09-18/service-2.json` | Configuration for 2020-09-18 | -
`aws/dist/awscli/botocore/data/iotevents/2018-07-27/endpoint-rule-set-1.json` | Configuration for 2018-07-27 | -
`aws/dist/awscli/botocore/data/iotevents/2018-07-27/paginators-1.json` | Configuration for 2018-07-27 | -
`aws/dist/awscli/botocore/data/iotevents/2018-07-27/service-2.json` | Configuration for 2018-07-27 | -
`aws/dist/awscli/botocore/data/iotevents-data/2018-10-23/endpoint-rule-set-1.json` | Configuration for 2018-10-23 | -
`aws/dist/awscli/botocore/data/iotevents-data/2018-10-23/paginators-1.json` | Configuration for 2018-10-23 | -
`aws/dist/awscli/botocore/data/iotevents-data/2018-10-23/service-2.json` | Configuration for 2018-10-23 | -
`aws/dist/awscli/botocore/data/iotfleetwise/2021-06-17/endpoint-rule-set-1.json` | Configuration for 2021-06-17 | -
`aws/dist/awscli/botocore/data/iotfleetwise/2021-06-17/paginators-1.json` | Configuration for 2021-06-17 | -
`aws/dist/awscli/botocore/data/iotfleetwise/2021-06-17/service-2.json` | Configuration for 2021-06-17 | -
`aws/dist/awscli/botocore/data/iotfleetwise/2021-06-17/waiters-2.json` | Configuration for 2021-06-17 | -
`aws/dist/awscli/botocore/data/iotsecuretunneling/2018-10-05/endpoint-rule-set-1.json` | Configuration for 2018-10-05 | -
`aws/dist/awscli/botocore/data/iotsecuretunneling/2018-10-05/paginators-1.json` | Configuration for 2018-10-05 | -
`aws/dist/awscli/botocore/data/iotsecuretunneling/2018-10-05/service-2.json` | Configuration for 2018-10-05 | -
`aws/dist/awscli/botocore/data/iotsitewise/2019-12-02/endpoint-rule-set-1.json` | Configuration for 2019-12-02 | -
`aws/dist/awscli/botocore/data/iotsitewise/2019-12-02/paginators-1.json` | Configuration for 2019-12-02 | -
`aws/dist/awscli/botocore/data/iotsitewise/2019-12-02/paginators-1.sdk-extras.json` | Configuration for 2019-12-02 | -
`aws/dist/awscli/botocore/data/iotsitewise/2019-12-02/service-2.json` | Configuration for 2019-12-02 | -
`aws/dist/awscli/botocore/data/iotsitewise/2019-12-02/waiters-2.json` | Configuration for 2019-12-02 | -
`aws/dist/awscli/botocore/data/iotthingsgraph/2018-09-06/endpoint-rule-set-1.json` | Configuration for 2018-09-06 | -
`aws/dist/awscli/botocore/data/iotthingsgraph/2018-09-06/paginators-1.json` | Configuration for 2018-09-06 | -
`aws/dist/awscli/botocore/data/iotthingsgraph/2018-09-06/service-2.json` | Configuration for 2018-09-06 | -
`aws/dist/awscli/botocore/data/iottwinmaker/2021-11-29/endpoint-rule-set-1.json` | Configuration for 2021-11-29 | -
`aws/dist/awscli/botocore/data/iottwinmaker/2021-11-29/paginators-1.json` | Configuration for 2021-11-29 | -
`aws/dist/awscli/botocore/data/iottwinmaker/2021-11-29/service-2.json` | Configuration for 2021-11-29 | -
`aws/dist/awscli/botocore/data/iottwinmaker/2021-11-29/waiters-2.json` | Configuration for 2021-11-29 | -
`aws/dist/awscli/botocore/data/iotwireless/2020-11-22/endpoint-rule-set-1.json` | Configuration for 2020-11-22 | -
`aws/dist/awscli/botocore/data/iotwireless/2020-11-22/paginators-1.json` | Configuration for 2020-11-22 | -
`aws/dist/awscli/botocore/data/iotwireless/2020-11-22/service-2.json` | Configuration for 2020-11-22 | -
`aws/dist/awscli/botocore/data/ivs/2020-07-14/endpoint-rule-set-1.json` | Configuration for 2020-07-14 | -
`aws/dist/awscli/botocore/data/ivs/2020-07-14/paginators-1.json` | Configuration for 2020-07-14 | -
`aws/dist/awscli/botocore/data/ivs/2020-07-14/service-2.json` | Configuration for 2020-07-14 | -
`aws/dist/awscli/botocore/data/ivs-realtime/2020-07-14/endpoint-rule-set-1.json` | Configuration for 2020-07-14 | -
`aws/dist/awscli/botocore/data/ivs-realtime/2020-07-14/paginators-1.json` | Configuration for 2020-07-14 | -
`aws/dist/awscli/botocore/data/ivs-realtime/2020-07-14/service-2.json` | Configuration for 2020-07-14 | -
`aws/dist/awscli/botocore/data/ivs-realtime/2020-07-14/waiters-2.json` | Configuration for 2020-07-14 | -
`aws/dist/awscli/botocore/data/ivschat/2020-07-14/endpoint-rule-set-1.json` | Configuration for 2020-07-14 | -
`aws/dist/awscli/botocore/data/ivschat/2020-07-14/paginators-1.json` | Configuration for 2020-07-14 | -
`aws/dist/awscli/botocore/data/ivschat/2020-07-14/service-2.json` | Configuration for 2020-07-14 | -
`aws/dist/awscli/botocore/data/ivschat/2020-07-14/waiters-2.json` | Configuration for 2020-07-14 | -
`aws/dist/awscli/botocore/data/kafka/2018-11-14/endpoint-rule-set-1.json` | Configuration for 2018-11-14 | -
`aws/dist/awscli/botocore/data/kafka/2018-11-14/paginators-1.json` | Configuration for 2018-11-14 | -
`aws/dist/awscli/botocore/data/kafka/2018-11-14/service-2.json` | Configuration for 2018-11-14 | -
`aws/dist/awscli/botocore/data/kafkaconnect/2021-09-14/endpoint-rule-set-1.json` | Configuration for 2021-09-14 | -
`aws/dist/awscli/botocore/data/kafkaconnect/2021-09-14/paginators-1.json` | Configuration for 2021-09-14 | -
`aws/dist/awscli/botocore/data/kafkaconnect/2021-09-14/service-2.json` | Configuration for 2021-09-14 | -
`aws/dist/awscli/botocore/data/kafkaconnect/2021-09-14/waiters-2.json` | Configuration for 2021-09-14 | -
`aws/dist/awscli/botocore/data/kendra/2019-02-03/endpoint-rule-set-1.json` | Configuration for 2019-02-03 | -
`aws/dist/awscli/botocore/data/kendra/2019-02-03/paginators-1.json` | Configuration for 2019-02-03 | -
`aws/dist/awscli/botocore/data/kendra/2019-02-03/service-2.json` | Configuration for 2019-02-03 | -
`aws/dist/awscli/botocore/data/kendra-ranking/2022-10-19/endpoint-rule-set-1.json` | Configuration for 2022-10-19 | -
`aws/dist/awscli/botocore/data/kendra-ranking/2022-10-19/paginators-1.json` | Configuration for 2022-10-19 | -
`aws/dist/awscli/botocore/data/kendra-ranking/2022-10-19/service-2.json` | Configuration for 2022-10-19 | -
`aws/dist/awscli/botocore/data/keyspaces/2022-02-10/endpoint-rule-set-1.json` | Configuration for 2022-02-10 | -
`aws/dist/awscli/botocore/data/keyspaces/2022-02-10/paginators-1.json` | Configuration for 2022-02-10 | -
`aws/dist/awscli/botocore/data/keyspaces/2022-02-10/service-2.json` | Configuration for 2022-02-10 | -
`aws/dist/awscli/botocore/data/keyspaces/2022-02-10/waiters-2.json` | Configuration for 2022-02-10 | -
`aws/dist/awscli/botocore/data/keyspacesstreams/2024-09-09/endpoint-rule-set-1.json` | Configuration for 2024-09-09 | -
`aws/dist/awscli/botocore/data/keyspacesstreams/2024-09-09/paginators-1.json` | Configuration for 2024-09-09 | -
`aws/dist/awscli/botocore/data/keyspacesstreams/2024-09-09/paginators-1.sdk-extras.json` | Configuration for 2024-09-09 | -
`aws/dist/awscli/botocore/data/keyspacesstreams/2024-09-09/service-2.json` | Configuration for 2024-09-09 | -
`aws/dist/awscli/botocore/data/kinesis/2013-12-02/endpoint-rule-set-1.json` | Configuration for 2013-12-02 | -
`aws/dist/awscli/botocore/data/kinesis/2013-12-02/paginators-1.json` | Configuration for 2013-12-02 | -
`aws/dist/awscli/botocore/data/kinesis/2013-12-02/service-2.json` | Configuration for 2013-12-02 | -
`aws/dist/awscli/botocore/data/kinesis/2013-12-02/waiters-2.json` | Configuration for 2013-12-02 | -
`aws/dist/awscli/botocore/data/kinesis-video-archived-media/2017-09-30/endpoint-rule-set-1.json` | Configuration for 2017-09-30 | -
`aws/dist/awscli/botocore/data/kinesis-video-archived-media/2017-09-30/paginators-1.json` | Configuration for 2017-09-30 | -
`aws/dist/awscli/botocore/data/kinesis-video-archived-media/2017-09-30/service-2.json` | Configuration for 2017-09-30 | -
`aws/dist/awscli/botocore/data/kinesis-video-media/2017-09-30/endpoint-rule-set-1.json` | Configuration for 2017-09-30 | -
`aws/dist/awscli/botocore/data/kinesis-video-media/2017-09-30/paginators-1.json` | Configuration for 2017-09-30 | -
`aws/dist/awscli/botocore/data/kinesis-video-media/2017-09-30/service-2.json` | Configuration for 2017-09-30 | -
`aws/dist/awscli/botocore/data/kinesis-video-signaling/2019-12-04/endpoint-rule-set-1.json` | Configuration for 2019-12-04 | -
`aws/dist/awscli/botocore/data/kinesis-video-signaling/2019-12-04/paginators-1.json` | Configuration for 2019-12-04 | -
`aws/dist/awscli/botocore/data/kinesis-video-signaling/2019-12-04/service-2.json` | Configuration for 2019-12-04 | -
`aws/dist/awscli/botocore/data/kinesis-video-webrtc-storage/2018-05-10/endpoint-rule-set-1.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/kinesis-video-webrtc-storage/2018-05-10/paginators-1.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/kinesis-video-webrtc-storage/2018-05-10/service-2.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/kinesisanalytics/2015-08-14/endpoint-rule-set-1.json` | Configuration for 2015-08-14 | -
`aws/dist/awscli/botocore/data/kinesisanalytics/2015-08-14/paginators-1.json` | Configuration for 2015-08-14 | -
`aws/dist/awscli/botocore/data/kinesisanalytics/2015-08-14/service-2.json` | Configuration for 2015-08-14 | -
`aws/dist/awscli/botocore/data/kinesisanalyticsv2/2018-05-23/endpoint-rule-set-1.json` | Configuration for 2018-05-23 | -
`aws/dist/awscli/botocore/data/kinesisanalyticsv2/2018-05-23/paginators-1.json` | Configuration for 2018-05-23 | -
`aws/dist/awscli/botocore/data/kinesisanalyticsv2/2018-05-23/service-2.json` | Configuration for 2018-05-23 | -
`aws/dist/awscli/botocore/data/kinesisvideo/2017-09-30/endpoint-rule-set-1.json` | Configuration for 2017-09-30 | -
`aws/dist/awscli/botocore/data/kinesisvideo/2017-09-30/paginators-1.json` | Configuration for 2017-09-30 | -
`aws/dist/awscli/botocore/data/kinesisvideo/2017-09-30/service-2.json` | Configuration for 2017-09-30 | -
`aws/dist/awscli/botocore/data/kms/2014-11-01/endpoint-rule-set-1.json` | Configuration for 2014-11-01 | -
`aws/dist/awscli/botocore/data/kms/2014-11-01/paginators-1.json` | Configuration for 2014-11-01 | -
`aws/dist/awscli/botocore/data/kms/2014-11-01/service-2.json` | Configuration for 2014-11-01 | -
`aws/dist/awscli/botocore/data/lakeformation/2017-03-31/endpoint-rule-set-1.json` | Configuration for 2017-03-31 | -
`aws/dist/awscli/botocore/data/lakeformation/2017-03-31/paginators-1.json` | Configuration for 2017-03-31 | -
`aws/dist/awscli/botocore/data/lakeformation/2017-03-31/paginators-1.sdk-extras.json` | Configuration for 2017-03-31 | -
`aws/dist/awscli/botocore/data/lakeformation/2017-03-31/service-2.json` | Configuration for 2017-03-31 | -
`aws/dist/awscli/botocore/data/lambda/2015-03-31/endpoint-rule-set-1.json` | Configuration for 2015-03-31 | -
`aws/dist/awscli/botocore/data/lambda/2015-03-31/paginators-1.json` | Configuration for 2015-03-31 | -
`aws/dist/awscli/botocore/data/lambda/2015-03-31/paginators-1.sdk-extras.json` | Configuration for 2015-03-31 | -
`aws/dist/awscli/botocore/data/lambda/2015-03-31/service-2.json` | Configuration for 2015-03-31 | -
`aws/dist/awscli/botocore/data/lambda/2015-03-31/waiters-2.json` | Configuration for 2015-03-31 | -
`aws/dist/awscli/botocore/data/launch-wizard/2018-05-10/endpoint-rule-set-1.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/launch-wizard/2018-05-10/paginators-1.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/launch-wizard/2018-05-10/service-2.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/launch-wizard/2018-05-10/waiters-2.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/lex-models/2017-04-19/endpoint-rule-set-1.json` | Configuration for 2017-04-19 | -
`aws/dist/awscli/botocore/data/lex-models/2017-04-19/paginators-1.json` | Configuration for 2017-04-19 | -
`aws/dist/awscli/botocore/data/lex-models/2017-04-19/service-2.json` | Configuration for 2017-04-19 | -
`aws/dist/awscli/botocore/data/lex-runtime/2016-11-28/endpoint-rule-set-1.json` | Configuration for 2016-11-28 | -
`aws/dist/awscli/botocore/data/lex-runtime/2016-11-28/paginators-1.json` | Configuration for 2016-11-28 | -
`aws/dist/awscli/botocore/data/lex-runtime/2016-11-28/service-2.json` | Configuration for 2016-11-28 | -
`aws/dist/awscli/botocore/data/lexv2-models/2020-08-07/endpoint-rule-set-1.json` | Configuration for 2020-08-07 | -
`aws/dist/awscli/botocore/data/lexv2-models/2020-08-07/paginators-1.json` | Configuration for 2020-08-07 | -
`aws/dist/awscli/botocore/data/lexv2-models/2020-08-07/service-2.json` | Configuration for 2020-08-07 | -
`aws/dist/awscli/botocore/data/lexv2-models/2020-08-07/waiters-2.json` | Configuration for 2020-08-07 | -
`aws/dist/awscli/botocore/data/lexv2-runtime/2020-08-07/endpoint-rule-set-1.json` | Configuration for 2020-08-07 | -
`aws/dist/awscli/botocore/data/lexv2-runtime/2020-08-07/paginators-1.json` | Configuration for 2020-08-07 | -
`aws/dist/awscli/botocore/data/lexv2-runtime/2020-08-07/service-2.json` | Configuration for 2020-08-07 | -
`aws/dist/awscli/botocore/data/license-manager/2018-08-01/endpoint-rule-set-1.json` | Configuration for 2018-08-01 | -
`aws/dist/awscli/botocore/data/license-manager/2018-08-01/paginators-1.json` | Configuration for 2018-08-01 | -
`aws/dist/awscli/botocore/data/license-manager/2018-08-01/service-2.json` | Configuration for 2018-08-01 | -
`aws/dist/awscli/botocore/data/license-manager-linux-subscriptions/2018-05-10/endpoint-rule-set-1.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/license-manager-linux-subscriptions/2018-05-10/paginators-1.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/license-manager-linux-subscriptions/2018-05-10/service-2.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/license-manager-user-subscriptions/2018-05-10/endpoint-rule-set-1.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/license-manager-user-subscriptions/2018-05-10/paginators-1.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/license-manager-user-subscriptions/2018-05-10/service-2.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/license-manager-user-subscriptions/2018-05-10/waiters-2.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/lightsail/2016-11-28/endpoint-rule-set-1.json` | Configuration for 2016-11-28 | -
`aws/dist/awscli/botocore/data/lightsail/2016-11-28/paginators-1.json` | Configuration for 2016-11-28 | -
`aws/dist/awscli/botocore/data/lightsail/2016-11-28/service-2.json` | Configuration for 2016-11-28 | -
`aws/dist/awscli/botocore/data/location/2020-11-19/endpoint-rule-set-1.json` | Configuration for 2020-11-19 | -
`aws/dist/awscli/botocore/data/location/2020-11-19/paginators-1.json` | Configuration for 2020-11-19 | -
`aws/dist/awscli/botocore/data/location/2020-11-19/paginators-1.sdk-extras.json` | Configuration for 2020-11-19 | -
`aws/dist/awscli/botocore/data/location/2020-11-19/service-2.json` | Configuration for 2020-11-19 | -
`aws/dist/awscli/botocore/data/location/2020-11-19/waiters-2.json` | Configuration for 2020-11-19 | -
`aws/dist/awscli/botocore/data/logs/2014-03-28/endpoint-rule-set-1.json` | Configuration for 2014-03-28 | -
`aws/dist/awscli/botocore/data/logs/2014-03-28/paginators-1.json` | Configuration for 2014-03-28 | -
`aws/dist/awscli/botocore/data/logs/2014-03-28/paginators-1.sdk-extras.json` | Configuration for 2014-03-28 | -
`aws/dist/awscli/botocore/data/logs/2014-03-28/service-2.json` | Configuration for 2014-03-28 | -
`aws/dist/awscli/botocore/data/lookoutequipment/2020-12-15/endpoint-rule-set-1.json` | Configuration for 2020-12-15 | -
`aws/dist/awscli/botocore/data/lookoutequipment/2020-12-15/paginators-1.json` | Configuration for 2020-12-15 | -
`aws/dist/awscli/botocore/data/lookoutequipment/2020-12-15/service-2.json` | Configuration for 2020-12-15 | -
`aws/dist/awscli/botocore/data/m2/2021-04-28/endpoint-rule-set-1.json` | Configuration for 2021-04-28 | -
`aws/dist/awscli/botocore/data/m2/2021-04-28/paginators-1.json` | Configuration for 2021-04-28 | -
`aws/dist/awscli/botocore/data/m2/2021-04-28/service-2.json` | Configuration for 2021-04-28 | -
`aws/dist/awscli/botocore/data/machinelearning/2014-12-12/endpoint-rule-set-1.json` | Configuration for 2014-12-12 | -
`aws/dist/awscli/botocore/data/machinelearning/2014-12-12/paginators-1.json` | Configuration for 2014-12-12 | -
`aws/dist/awscli/botocore/data/machinelearning/2014-12-12/service-2.json` | Configuration for 2014-12-12 | -
`aws/dist/awscli/botocore/data/machinelearning/2014-12-12/waiters-2.json` | Configuration for 2014-12-12 | -
`aws/dist/awscli/botocore/data/macie2/2020-01-01/endpoint-rule-set-1.json` | Configuration for 2020-01-01 | -
`aws/dist/awscli/botocore/data/macie2/2020-01-01/paginators-1.json` | Configuration for 2020-01-01 | -
`aws/dist/awscli/botocore/data/macie2/2020-01-01/service-2.json` | Configuration for 2020-01-01 | -
`aws/dist/awscli/botocore/data/macie2/2020-01-01/waiters-2.json` | Configuration for 2020-01-01 | -
`aws/dist/awscli/botocore/data/mailmanager/2023-10-17/endpoint-rule-set-1.json` | Configuration for 2023-10-17 | -
`aws/dist/awscli/botocore/data/mailmanager/2023-10-17/paginators-1.json` | Configuration for 2023-10-17 | -
`aws/dist/awscli/botocore/data/mailmanager/2023-10-17/service-2.json` | Configuration for 2023-10-17 | -
`aws/dist/awscli/botocore/data/mailmanager/2023-10-17/waiters-2.json` | Configuration for 2023-10-17 | -
`aws/dist/awscli/botocore/data/managedblockchain/2018-09-24/endpoint-rule-set-1.json` | Configuration for 2018-09-24 | -
`aws/dist/awscli/botocore/data/managedblockchain/2018-09-24/paginators-1.json` | Configuration for 2018-09-24 | -
`aws/dist/awscli/botocore/data/managedblockchain/2018-09-24/service-2.json` | Configuration for 2018-09-24 | -
`aws/dist/awscli/botocore/data/managedblockchain-query/2023-05-04/endpoint-rule-set-1.json` | Configuration for 2023-05-04 | -
`aws/dist/awscli/botocore/data/managedblockchain-query/2023-05-04/paginators-1.json` | Configuration for 2023-05-04 | -
`aws/dist/awscli/botocore/data/managedblockchain-query/2023-05-04/service-2.json` | Configuration for 2023-05-04 | -
`aws/dist/awscli/botocore/data/managedblockchain-query/2023-05-04/waiters-2.json` | Configuration for 2023-05-04 | -
`aws/dist/awscli/botocore/data/marketplace-agreement/2020-03-01/endpoint-rule-set-1.json` | Configuration for 2020-03-01 | -
`aws/dist/awscli/botocore/data/marketplace-agreement/2020-03-01/paginators-1.json` | Configuration for 2020-03-01 | -
`aws/dist/awscli/botocore/data/marketplace-agreement/2020-03-01/service-2.json` | Configuration for 2020-03-01 | -
`aws/dist/awscli/botocore/data/marketplace-agreement/2020-03-01/waiters-2.json` | Configuration for 2020-03-01 | -
`aws/dist/awscli/botocore/data/marketplace-catalog/2018-09-17/endpoint-rule-set-1.json` | Configuration for 2018-09-17 | -
`aws/dist/awscli/botocore/data/marketplace-catalog/2018-09-17/paginators-1.json` | Configuration for 2018-09-17 | -
`aws/dist/awscli/botocore/data/marketplace-catalog/2018-09-17/service-2.json` | Configuration for 2018-09-17 | -
`aws/dist/awscli/botocore/data/marketplace-deployment/2023-01-25/endpoint-rule-set-1.json` | Configuration for 2023-01-25 | -
`aws/dist/awscli/botocore/data/marketplace-deployment/2023-01-25/paginators-1.json` | Configuration for 2023-01-25 | -
`aws/dist/awscli/botocore/data/marketplace-deployment/2023-01-25/service-2.json` | Configuration for 2023-01-25 | -
`aws/dist/awscli/botocore/data/marketplace-discovery/2026-02-05/endpoint-rule-set-1.json` | Configuration for 2026-02-05 | -
`aws/dist/awscli/botocore/data/marketplace-discovery/2026-02-05/paginators-1.json` | Configuration for 2026-02-05 | -
`aws/dist/awscli/botocore/data/marketplace-discovery/2026-02-05/paginators-1.sdk-extras.json` | Configuration for 2026-02-05 | -
`aws/dist/awscli/botocore/data/marketplace-discovery/2026-02-05/service-2.json` | Configuration for 2026-02-05 | -
`aws/dist/awscli/botocore/data/marketplace-discovery/2026-02-05/waiters-2.json` | Configuration for 2026-02-05 | -
`aws/dist/awscli/botocore/data/marketplace-entitlement/2017-01-11/endpoint-rule-set-1.json` | Configuration for 2017-01-11 | -
`aws/dist/awscli/botocore/data/marketplace-entitlement/2017-01-11/paginators-1.json` | Configuration for 2017-01-11 | -
`aws/dist/awscli/botocore/data/marketplace-entitlement/2017-01-11/service-2.json` | Configuration for 2017-01-11 | -
`aws/dist/awscli/botocore/data/marketplace-reporting/2018-05-10/endpoint-rule-set-1.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/marketplace-reporting/2018-05-10/paginators-1.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/marketplace-reporting/2018-05-10/service-2.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/marketplace-reporting/2018-05-10/waiters-2.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/marketplacecommerceanalytics/2015-07-01/endpoint-rule-set-1.json` | Configuration for 2015-07-01 | -
`aws/dist/awscli/botocore/data/marketplacecommerceanalytics/2015-07-01/paginators-1.json` | Configuration for 2015-07-01 | -
`aws/dist/awscli/botocore/data/marketplacecommerceanalytics/2015-07-01/service-2.json` | Configuration for 2015-07-01 | -
`aws/dist/awscli/botocore/data/mediaconnect/2018-11-14/endpoint-rule-set-1.json` | Configuration for 2018-11-14 | -
`aws/dist/awscli/botocore/data/mediaconnect/2018-11-14/paginators-1.json` | Configuration for 2018-11-14 | -
`aws/dist/awscli/botocore/data/mediaconnect/2018-11-14/service-2.json` | Configuration for 2018-11-14 | -
`aws/dist/awscli/botocore/data/mediaconnect/2018-11-14/waiters-2.json` | Configuration for 2018-11-14 | -
`aws/dist/awscli/botocore/data/mediaconvert/2017-08-29/endpoint-rule-set-1.json` | Configuration for 2017-08-29 | -
`aws/dist/awscli/botocore/data/mediaconvert/2017-08-29/paginators-1.json` | Configuration for 2017-08-29 | -
`aws/dist/awscli/botocore/data/mediaconvert/2017-08-29/paginators-1.sdk-extras.json` | Configuration for 2017-08-29 | -
`aws/dist/awscli/botocore/data/mediaconvert/2017-08-29/service-2.json` | Configuration for 2017-08-29 | -
`aws/dist/awscli/botocore/data/medialive/2017-10-14/endpoint-rule-set-1.json` | Configuration for 2017-10-14 | -
`aws/dist/awscli/botocore/data/medialive/2017-10-14/paginators-1.json` | Configuration for 2017-10-14 | -
`aws/dist/awscli/botocore/data/medialive/2017-10-14/service-2.json` | Configuration for 2017-10-14 | -
`aws/dist/awscli/botocore/data/medialive/2017-10-14/waiters-2.json` | Configuration for 2017-10-14 | -
`aws/dist/awscli/botocore/data/mediapackage/2017-10-12/endpoint-rule-set-1.json` | Configuration for 2017-10-12 | -
`aws/dist/awscli/botocore/data/mediapackage/2017-10-12/paginators-1.json` | Configuration for 2017-10-12 | -
`aws/dist/awscli/botocore/data/mediapackage/2017-10-12/service-2.json` | Configuration for 2017-10-12 | -
`aws/dist/awscli/botocore/data/mediapackage-vod/2018-11-07/endpoint-rule-set-1.json` | Configuration for 2018-11-07 | -
`aws/dist/awscli/botocore/data/mediapackage-vod/2018-11-07/paginators-1.json` | Configuration for 2018-11-07 | -
`aws/dist/awscli/botocore/data/mediapackage-vod/2018-11-07/service-2.json` | Configuration for 2018-11-07 | -
`aws/dist/awscli/botocore/data/mediapackagev2/2022-12-25/endpoint-rule-set-1.json` | Configuration for 2022-12-25 | -
`aws/dist/awscli/botocore/data/mediapackagev2/2022-12-25/paginators-1.json` | Configuration for 2022-12-25 | -
`aws/dist/awscli/botocore/data/mediapackagev2/2022-12-25/service-2.json` | Configuration for 2022-12-25 | -
`aws/dist/awscli/botocore/data/mediapackagev2/2022-12-25/waiters-2.json` | Configuration for 2022-12-25 | -
`aws/dist/awscli/botocore/data/mediastore/2017-09-01/endpoint-rule-set-1.json` | Configuration for 2017-09-01 | -
`aws/dist/awscli/botocore/data/mediastore/2017-09-01/paginators-1.json` | Configuration for 2017-09-01 | -
`aws/dist/awscli/botocore/data/mediastore/2017-09-01/service-2.json` | Configuration for 2017-09-01 | -
`aws/dist/awscli/botocore/data/mediastore-data/2017-09-01/endpoint-rule-set-1.json` | Configuration for 2017-09-01 | -
`aws/dist/awscli/botocore/data/mediastore-data/2017-09-01/paginators-1.json` | Configuration for 2017-09-01 | -
`aws/dist/awscli/botocore/data/mediastore-data/2017-09-01/service-2.json` | Configuration for 2017-09-01 | -
`aws/dist/awscli/botocore/data/mediatailor/2018-04-23/endpoint-rule-set-1.json` | Configuration for 2018-04-23 | -
`aws/dist/awscli/botocore/data/mediatailor/2018-04-23/paginators-1.json` | Configuration for 2018-04-23 | -
`aws/dist/awscli/botocore/data/mediatailor/2018-04-23/service-2.json` | Configuration for 2018-04-23 | -
`aws/dist/awscli/botocore/data/medical-imaging/2023-07-19/endpoint-rule-set-1.json` | Configuration for 2023-07-19 | -
`aws/dist/awscli/botocore/data/medical-imaging/2023-07-19/paginators-1.json` | Configuration for 2023-07-19 | -
`aws/dist/awscli/botocore/data/medical-imaging/2023-07-19/paginators-1.sdk-extras.json` | Configuration for 2023-07-19 | -
`aws/dist/awscli/botocore/data/medical-imaging/2023-07-19/service-2.json` | Configuration for 2023-07-19 | -
`aws/dist/awscli/botocore/data/medical-imaging/2023-07-19/waiters-2.json` | Configuration for 2023-07-19 | -
`aws/dist/awscli/botocore/data/memorydb/2021-01-01/endpoint-rule-set-1.json` | Configuration for 2021-01-01 | -
`aws/dist/awscli/botocore/data/memorydb/2021-01-01/paginators-1.json` | Configuration for 2021-01-01 | -
`aws/dist/awscli/botocore/data/memorydb/2021-01-01/service-2.json` | Configuration for 2021-01-01 | -
`aws/dist/awscli/botocore/data/meteringmarketplace/2016-01-14/endpoint-rule-set-1.json` | Configuration for 2016-01-14 | -
`aws/dist/awscli/botocore/data/meteringmarketplace/2016-01-14/paginators-1.json` | Configuration for 2016-01-14 | -
`aws/dist/awscli/botocore/data/meteringmarketplace/2016-01-14/service-2.json` | Configuration for 2016-01-14 | -
`aws/dist/awscli/botocore/data/mgh/2017-05-31/endpoint-rule-set-1.json` | Configuration for 2017-05-31 | -
`aws/dist/awscli/botocore/data/mgh/2017-05-31/paginators-1.json` | Configuration for 2017-05-31 | -
`aws/dist/awscli/botocore/data/mgh/2017-05-31/service-2.json` | Configuration for 2017-05-31 | -
`aws/dist/awscli/botocore/data/mgn/2020-02-26/endpoint-rule-set-1.json` | Configuration for 2020-02-26 | -
`aws/dist/awscli/botocore/data/mgn/2020-02-26/paginators-1.json` | Configuration for 2020-02-26 | -
`aws/dist/awscli/botocore/data/mgn/2020-02-26/service-2.json` | Configuration for 2020-02-26 | -
`aws/dist/awscli/botocore/data/mgn/2020-02-26/waiters-2.json` | Configuration for 2020-02-26 | -
`aws/dist/awscli/botocore/data/migration-hub-refactor-spaces/2021-10-26/endpoint-rule-set-1.json` | Configuration for 2021-10-26 | -
`aws/dist/awscli/botocore/data/migration-hub-refactor-spaces/2021-10-26/paginators-1.json` | Configuration for 2021-10-26 | -
`aws/dist/awscli/botocore/data/migration-hub-refactor-spaces/2021-10-26/service-2.json` | Configuration for 2021-10-26 | -
`aws/dist/awscli/botocore/data/migrationhub-config/2019-06-30/endpoint-rule-set-1.json` | Configuration for 2019-06-30 | -
`aws/dist/awscli/botocore/data/migrationhub-config/2019-06-30/paginators-1.json` | Configuration for 2019-06-30 | -
`aws/dist/awscli/botocore/data/migrationhub-config/2019-06-30/service-2.json` | Configuration for 2019-06-30 | -
`aws/dist/awscli/botocore/data/migrationhuborchestrator/2021-08-28/endpoint-rule-set-1.json` | Configuration for 2021-08-28 | -
`aws/dist/awscli/botocore/data/migrationhuborchestrator/2021-08-28/paginators-1.json` | Configuration for 2021-08-28 | -
`aws/dist/awscli/botocore/data/migrationhuborchestrator/2021-08-28/service-2.json` | Configuration for 2021-08-28 | -
`aws/dist/awscli/botocore/data/migrationhuborchestrator/2021-08-28/waiters-2.json` | Configuration for 2021-08-28 | -
`aws/dist/awscli/botocore/data/migrationhubstrategy/2020-02-19/endpoint-rule-set-1.json` | Configuration for 2020-02-19 | -
`aws/dist/awscli/botocore/data/migrationhubstrategy/2020-02-19/paginators-1.json` | Configuration for 2020-02-19 | -
`aws/dist/awscli/botocore/data/migrationhubstrategy/2020-02-19/paginators-1.sdk-extras.json` | Configuration for 2020-02-19 | -
`aws/dist/awscli/botocore/data/migrationhubstrategy/2020-02-19/service-2.json` | Configuration for 2020-02-19 | -
`aws/dist/awscli/botocore/data/mpa/2022-07-26/endpoint-rule-set-1.json` | Configuration for 2022-07-26 | -
`aws/dist/awscli/botocore/data/mpa/2022-07-26/paginators-1.json` | Configuration for 2022-07-26 | -
`aws/dist/awscli/botocore/data/mpa/2022-07-26/service-2.json` | Configuration for 2022-07-26 | -
`aws/dist/awscli/botocore/data/mpa/2022-07-26/waiters-2.json` | Configuration for 2022-07-26 | -
`aws/dist/awscli/botocore/data/mq/2017-11-27/endpoint-rule-set-1.json` | Configuration for 2017-11-27 | -
`aws/dist/awscli/botocore/data/mq/2017-11-27/paginators-1.json` | Configuration for 2017-11-27 | -
`aws/dist/awscli/botocore/data/mq/2017-11-27/service-2.json` | Configuration for 2017-11-27 | -
`aws/dist/awscli/botocore/data/mturk/2017-01-17/endpoint-rule-set-1.json` | Configuration for 2017-01-17 | -
`aws/dist/awscli/botocore/data/mturk/2017-01-17/paginators-1.json` | Configuration for 2017-01-17 | -
`aws/dist/awscli/botocore/data/mturk/2017-01-17/service-2.json` | Configuration for 2017-01-17 | -
`aws/dist/awscli/botocore/data/mwaa/2020-07-01/endpoint-rule-set-1.json` | Configuration for 2020-07-01 | -
`aws/dist/awscli/botocore/data/mwaa/2020-07-01/paginators-1.json` | Configuration for 2020-07-01 | -
`aws/dist/awscli/botocore/data/mwaa/2020-07-01/service-2.json` | Configuration for 2020-07-01 | -
`aws/dist/awscli/botocore/data/mwaa-serverless/2024-07-26/endpoint-rule-set-1.json` | Configuration for 2024-07-26 | -
`aws/dist/awscli/botocore/data/mwaa-serverless/2024-07-26/paginators-1.json` | Configuration for 2024-07-26 | -
`aws/dist/awscli/botocore/data/mwaa-serverless/2024-07-26/service-2.json` | Configuration for 2024-07-26 | -
`aws/dist/awscli/botocore/data/mwaa-serverless/2024-07-26/waiters-2.json` | Configuration for 2024-07-26 | -
`aws/dist/awscli/botocore/data/neptune/2014-10-31/endpoint-rule-set-1.json` | Configuration for 2014-10-31 | -
`aws/dist/awscli/botocore/data/neptune/2014-10-31/paginators-1.json` | Configuration for 2014-10-31 | -
`aws/dist/awscli/botocore/data/neptune/2014-10-31/service-2.json` | Configuration for 2014-10-31 | -
`aws/dist/awscli/botocore/data/neptune/2014-10-31/service-2.sdk-extras.json` | Configuration for 2014-10-31 | -
`aws/dist/awscli/botocore/data/neptune/2014-10-31/waiters-2.json` | Configuration for 2014-10-31 | -
`aws/dist/awscli/botocore/data/neptune-graph/2023-11-29/endpoint-rule-set-1.json` | Configuration for 2023-11-29 | -
`aws/dist/awscli/botocore/data/neptune-graph/2023-11-29/paginators-1.json` | Configuration for 2023-11-29 | -
`aws/dist/awscli/botocore/data/neptune-graph/2023-11-29/service-2.json` | Configuration for 2023-11-29 | -
`aws/dist/awscli/botocore/data/neptune-graph/2023-11-29/waiters-2.json` | Configuration for 2023-11-29 | -
`aws/dist/awscli/botocore/data/neptunedata/2023-08-01/endpoint-rule-set-1.json` | Configuration for 2023-08-01 | -
`aws/dist/awscli/botocore/data/neptunedata/2023-08-01/paginators-1.json` | Configuration for 2023-08-01 | -
`aws/dist/awscli/botocore/data/neptunedata/2023-08-01/service-2.json` | Configuration for 2023-08-01 | -
`aws/dist/awscli/botocore/data/network-firewall/2020-11-12/endpoint-rule-set-1.json` | Configuration for 2020-11-12 | -
`aws/dist/awscli/botocore/data/network-firewall/2020-11-12/paginators-1.json` | Configuration for 2020-11-12 | -
`aws/dist/awscli/botocore/data/network-firewall/2020-11-12/paginators-1.sdk-extras.json` | Configuration for 2020-11-12 | -
`aws/dist/awscli/botocore/data/network-firewall/2020-11-12/service-2.json` | Configuration for 2020-11-12 | -
`aws/dist/awscli/botocore/data/networkflowmonitor/2023-04-19/endpoint-rule-set-1.json` | Configuration for 2023-04-19 | -
`aws/dist/awscli/botocore/data/networkflowmonitor/2023-04-19/paginators-1.json` | Configuration for 2023-04-19 | -
`aws/dist/awscli/botocore/data/networkflowmonitor/2023-04-19/paginators-1.sdk-extras.json` | Configuration for 2023-04-19 | -
`aws/dist/awscli/botocore/data/networkflowmonitor/2023-04-19/service-2.json` | Configuration for 2023-04-19 | -
`aws/dist/awscli/botocore/data/networkflowmonitor/2023-04-19/waiters-2.json` | Configuration for 2023-04-19 | -
`aws/dist/awscli/botocore/data/networkmanager/2019-07-05/endpoint-rule-set-1.json` | Configuration for 2019-07-05 | -
`aws/dist/awscli/botocore/data/networkmanager/2019-07-05/paginators-1.json` | Configuration for 2019-07-05 | -
`aws/dist/awscli/botocore/data/networkmanager/2019-07-05/service-2.json` | Configuration for 2019-07-05 | -
`aws/dist/awscli/botocore/data/networkmonitor/2023-08-01/endpoint-rule-set-1.json` | Configuration for 2023-08-01 | -
`aws/dist/awscli/botocore/data/networkmonitor/2023-08-01/paginators-1.json` | Configuration for 2023-08-01 | -
`aws/dist/awscli/botocore/data/networkmonitor/2023-08-01/service-2.json` | Configuration for 2023-08-01 | -
`aws/dist/awscli/botocore/data/networkmonitor/2023-08-01/waiters-2.json` | Configuration for 2023-08-01 | -
`aws/dist/awscli/botocore/data/notifications/2018-05-10/endpoint-rule-set-1.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/notifications/2018-05-10/paginators-1.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/notifications/2018-05-10/service-2.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/notifications/2018-05-10/waiters-2.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/notificationscontacts/2018-05-10/endpoint-rule-set-1.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/notificationscontacts/2018-05-10/paginators-1.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/notificationscontacts/2018-05-10/service-2.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/notificationscontacts/2018-05-10/waiters-2.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/nova-act/2025-08-22/endpoint-rule-set-1.json` | Configuration for 2025-08-22 | -
`aws/dist/awscli/botocore/data/nova-act/2025-08-22/paginators-1.json` | Configuration for 2025-08-22 | -
`aws/dist/awscli/botocore/data/nova-act/2025-08-22/service-2.json` | Configuration for 2025-08-22 | -
`aws/dist/awscli/botocore/data/nova-act/2025-08-22/waiters-2.json` | Configuration for 2025-08-22 | -
`aws/dist/awscli/botocore/data/oam/2022-06-10/endpoint-rule-set-1.json` | Configuration for 2022-06-10 | -
`aws/dist/awscli/botocore/data/oam/2022-06-10/paginators-1.json` | Configuration for 2022-06-10 | -
`aws/dist/awscli/botocore/data/oam/2022-06-10/service-2.json` | Configuration for 2022-06-10 | -
`aws/dist/awscli/botocore/data/observabilityadmin/2018-05-10/endpoint-rule-set-1.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/observabilityadmin/2018-05-10/paginators-1.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/observabilityadmin/2018-05-10/service-2.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/observabilityadmin/2018-05-10/waiters-2.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/odb/2024-08-20/endpoint-rule-set-1.json` | Configuration for 2024-08-20 | -
`aws/dist/awscli/botocore/data/odb/2024-08-20/paginators-1.json` | Configuration for 2024-08-20 | -
`aws/dist/awscli/botocore/data/odb/2024-08-20/service-2.json` | Configuration for 2024-08-20 | -
`aws/dist/awscli/botocore/data/odb/2024-08-20/waiters-2.json` | Configuration for 2024-08-20 | -
`aws/dist/awscli/botocore/data/omics/2022-11-28/endpoint-rule-set-1.json` | Configuration for 2022-11-28 | -
`aws/dist/awscli/botocore/data/omics/2022-11-28/paginators-1.json` | Configuration for 2022-11-28 | -
`aws/dist/awscli/botocore/data/omics/2022-11-28/service-2.json` | Configuration for 2022-11-28 | -
`aws/dist/awscli/botocore/data/omics/2022-11-28/waiters-2.json` | Configuration for 2022-11-28 | -
`aws/dist/awscli/botocore/data/opensearch/2021-01-01/endpoint-rule-set-1.json` | Configuration for 2021-01-01 | -
`aws/dist/awscli/botocore/data/opensearch/2021-01-01/paginators-1.json` | Configuration for 2021-01-01 | -
`aws/dist/awscli/botocore/data/opensearch/2021-01-01/service-2.json` | Configuration for 2021-01-01 | -
`aws/dist/awscli/botocore/data/opensearchserverless/2021-11-01/endpoint-rule-set-1.json` | Configuration for 2021-11-01 | -
`aws/dist/awscli/botocore/data/opensearchserverless/2021-11-01/paginators-1.json` | Configuration for 2021-11-01 | -
`aws/dist/awscli/botocore/data/opensearchserverless/2021-11-01/service-2.json` | Configuration for 2021-11-01 | -
`aws/dist/awscli/botocore/data/opensearchserverless/2021-11-01/waiters-2.json` | Configuration for 2021-11-01 | -
`aws/dist/awscli/botocore/data/organizations/2016-11-28/endpoint-rule-set-1.json` | Configuration for 2016-11-28 | -
`aws/dist/awscli/botocore/data/organizations/2016-11-28/paginators-1.json` | Configuration for 2016-11-28 | -
`aws/dist/awscli/botocore/data/organizations/2016-11-28/paginators-1.sdk-extras.json` | Configuration for 2016-11-28 | -
`aws/dist/awscli/botocore/data/organizations/2016-11-28/service-2.json` | Configuration for 2016-11-28 | -
`aws/dist/awscli/botocore/data/osis/2022-01-01/endpoint-rule-set-1.json` | Configuration for 2022-01-01 | -
`aws/dist/awscli/botocore/data/osis/2022-01-01/paginators-1.json` | Configuration for 2022-01-01 | -
`aws/dist/awscli/botocore/data/osis/2022-01-01/service-2.json` | Configuration for 2022-01-01 | -
`aws/dist/awscli/botocore/data/outposts/2019-12-03/endpoint-rule-set-1.json` | Configuration for 2019-12-03 | -
`aws/dist/awscli/botocore/data/outposts/2019-12-03/paginators-1.json` | Configuration for 2019-12-03 | -
`aws/dist/awscli/botocore/data/outposts/2019-12-03/paginators-1.sdk-extras.json` | Configuration for 2019-12-03 | -
`aws/dist/awscli/botocore/data/outposts/2019-12-03/service-2.json` | Configuration for 2019-12-03 | -
`aws/dist/awscli/botocore/data/panorama/2019-07-24/endpoint-rule-set-1.json` | Configuration for 2019-07-24 | -
`aws/dist/awscli/botocore/data/panorama/2019-07-24/paginators-1.json` | Configuration for 2019-07-24 | -
`aws/dist/awscli/botocore/data/panorama/2019-07-24/service-2.json` | Configuration for 2019-07-24 | -
`aws/dist/awscli/botocore/data/partitions.json` | Configuration for data | -
`aws/dist/awscli/botocore/data/partnercentral-account/2025-04-04/endpoint-rule-set-1.json` | Configuration for 2025-04-04 | -
`aws/dist/awscli/botocore/data/partnercentral-account/2025-04-04/paginators-1.json` | Configuration for 2025-04-04 | -
`aws/dist/awscli/botocore/data/partnercentral-account/2025-04-04/service-2.json` | Configuration for 2025-04-04 | -
`aws/dist/awscli/botocore/data/partnercentral-account/2025-04-04/waiters-2.json` | Configuration for 2025-04-04 | -
`aws/dist/awscli/botocore/data/partnercentral-benefits/2018-05-10/endpoint-rule-set-1.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/partnercentral-benefits/2018-05-10/paginators-1.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/partnercentral-benefits/2018-05-10/service-2.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/partnercentral-benefits/2018-05-10/waiters-2.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/partnercentral-channel/2024-03-18/endpoint-rule-set-1.json` | Configuration for 2024-03-18 | -
`aws/dist/awscli/botocore/data/partnercentral-channel/2024-03-18/paginators-1.json` | Configuration for 2024-03-18 | -
`aws/dist/awscli/botocore/data/partnercentral-channel/2024-03-18/service-2.json` | Configuration for 2024-03-18 | -
`aws/dist/awscli/botocore/data/partnercentral-channel/2024-03-18/waiters-2.json` | Configuration for 2024-03-18 | -
`aws/dist/awscli/botocore/data/partnercentral-selling/2022-07-26/endpoint-rule-set-1.json` | Configuration for 2022-07-26 | -
`aws/dist/awscli/botocore/data/partnercentral-selling/2022-07-26/paginators-1.json` | Configuration for 2022-07-26 | -
`aws/dist/awscli/botocore/data/partnercentral-selling/2022-07-26/service-2.json` | Configuration for 2022-07-26 | -
`aws/dist/awscli/botocore/data/partnercentral-selling/2022-07-26/waiters-2.json` | Configuration for 2022-07-26 | -
`aws/dist/awscli/botocore/data/payment-cryptography/2021-09-14/endpoint-rule-set-1.json` | Configuration for 2021-09-14 | -
`aws/dist/awscli/botocore/data/payment-cryptography/2021-09-14/paginators-1.json` | Configuration for 2021-09-14 | -
`aws/dist/awscli/botocore/data/payment-cryptography/2021-09-14/service-2.json` | Configuration for 2021-09-14 | -
`aws/dist/awscli/botocore/data/payment-cryptography/2021-09-14/waiters-2.json` | Configuration for 2021-09-14 | -
`aws/dist/awscli/botocore/data/payment-cryptography-data/2022-02-03/endpoint-rule-set-1.json` | Configuration for 2022-02-03 | -
`aws/dist/awscli/botocore/data/payment-cryptography-data/2022-02-03/paginators-1.json` | Configuration for 2022-02-03 | -
`aws/dist/awscli/botocore/data/payment-cryptography-data/2022-02-03/service-2.json` | Configuration for 2022-02-03 | -
`aws/dist/awscli/botocore/data/payment-cryptography-data/2022-02-03/waiters-2.json` | Configuration for 2022-02-03 | -
`aws/dist/awscli/botocore/data/pca-connector-ad/2018-05-10/endpoint-rule-set-1.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/pca-connector-ad/2018-05-10/paginators-1.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/pca-connector-ad/2018-05-10/service-2.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/pca-connector-scep/2018-05-10/endpoint-rule-set-1.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/pca-connector-scep/2018-05-10/paginators-1.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/pca-connector-scep/2018-05-10/service-2.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/pca-connector-scep/2018-05-10/waiters-2.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/pcs/2023-02-10/endpoint-rule-set-1.json` | Configuration for 2023-02-10 | -
`aws/dist/awscli/botocore/data/pcs/2023-02-10/paginators-1.json` | Configuration for 2023-02-10 | -
`aws/dist/awscli/botocore/data/pcs/2023-02-10/service-2.json` | Configuration for 2023-02-10 | -
`aws/dist/awscli/botocore/data/pcs/2023-02-10/waiters-2.json` | Configuration for 2023-02-10 | -
`aws/dist/awscli/botocore/data/personalize/2018-05-22/endpoint-rule-set-1.json` | Configuration for 2018-05-22 | -
`aws/dist/awscli/botocore/data/personalize/2018-05-22/paginators-1.json` | Configuration for 2018-05-22 | -
`aws/dist/awscli/botocore/data/personalize/2018-05-22/service-2.json` | Configuration for 2018-05-22 | -
`aws/dist/awscli/botocore/data/personalize-events/2018-03-22/endpoint-rule-set-1.json` | Configuration for 2018-03-22 | -
`aws/dist/awscli/botocore/data/personalize-events/2018-03-22/paginators-1.json` | Configuration for 2018-03-22 | -
`aws/dist/awscli/botocore/data/personalize-events/2018-03-22/service-2.json` | Configuration for 2018-03-22 | -
`aws/dist/awscli/botocore/data/personalize-runtime/2018-05-22/endpoint-rule-set-1.json` | Configuration for 2018-05-22 | -
`aws/dist/awscli/botocore/data/personalize-runtime/2018-05-22/paginators-1.json` | Configuration for 2018-05-22 | -
`aws/dist/awscli/botocore/data/personalize-runtime/2018-05-22/service-2.json` | Configuration for 2018-05-22 | -
`aws/dist/awscli/botocore/data/pi/2018-02-27/endpoint-rule-set-1.json` | Configuration for 2018-02-27 | -
`aws/dist/awscli/botocore/data/pi/2018-02-27/paginators-1.json` | Configuration for 2018-02-27 | -
`aws/dist/awscli/botocore/data/pi/2018-02-27/service-2.json` | Configuration for 2018-02-27 | -
`aws/dist/awscli/botocore/data/pinpoint/2016-12-01/endpoint-rule-set-1.json` | Configuration for 2016-12-01 | -
`aws/dist/awscli/botocore/data/pinpoint/2016-12-01/service-2.json` | Configuration for 2016-12-01 | -
`aws/dist/awscli/botocore/data/pinpoint-email/2018-07-26/endpoint-rule-set-1.json` | Configuration for 2018-07-26 | -
`aws/dist/awscli/botocore/data/pinpoint-email/2018-07-26/paginators-1.json` | Configuration for 2018-07-26 | -
`aws/dist/awscli/botocore/data/pinpoint-email/2018-07-26/service-2.json` | Configuration for 2018-07-26 | -
`aws/dist/awscli/botocore/data/pinpoint-sms-voice/2018-09-05/endpoint-rule-set-1.json` | Configuration for 2018-09-05 | -
`aws/dist/awscli/botocore/data/pinpoint-sms-voice/2018-09-05/service-2.json` | Configuration for 2018-09-05 | -
`aws/dist/awscli/botocore/data/pinpoint-sms-voice-v2/2022-03-31/endpoint-rule-set-1.json` | Configuration for 2022-03-31 | -
`aws/dist/awscli/botocore/data/pinpoint-sms-voice-v2/2022-03-31/paginators-1.json` | Configuration for 2022-03-31 | -
`aws/dist/awscli/botocore/data/pinpoint-sms-voice-v2/2022-03-31/paginators-1.sdk-extras.json` | Configuration for 2022-03-31 | -
`aws/dist/awscli/botocore/data/pinpoint-sms-voice-v2/2022-03-31/service-2.json` | Configuration for 2022-03-31 | -
`aws/dist/awscli/botocore/data/pinpoint-sms-voice-v2/2022-03-31/waiters-2.json` | Configuration for 2022-03-31 | -
`aws/dist/awscli/botocore/data/pipes/2015-10-07/endpoint-rule-set-1.json` | Configuration for 2015-10-07 | -
`aws/dist/awscli/botocore/data/pipes/2015-10-07/paginators-1.json` | Configuration for 2015-10-07 | -
`aws/dist/awscli/botocore/data/pipes/2015-10-07/service-2.json` | Configuration for 2015-10-07 | -
`aws/dist/awscli/botocore/data/pipes/2015-10-07/waiters-2.json` | Configuration for 2015-10-07 | -
`aws/dist/awscli/botocore/data/polly/2016-06-10/endpoint-rule-set-1.json` | Configuration for 2016-06-10 | -
`aws/dist/awscli/botocore/data/polly/2016-06-10/paginators-1.json` | Configuration for 2016-06-10 | -
`aws/dist/awscli/botocore/data/polly/2016-06-10/service-2.json` | Configuration for 2016-06-10 | -
`aws/dist/awscli/botocore/data/pricing/2017-10-15/endpoint-rule-set-1.json` | Configuration for 2017-10-15 | -
`aws/dist/awscli/botocore/data/pricing/2017-10-15/paginators-1.json` | Configuration for 2017-10-15 | -
`aws/dist/awscli/botocore/data/pricing/2017-10-15/service-2.json` | Configuration for 2017-10-15 | -
`aws/dist/awscli/botocore/data/pricing/2017-10-15/waiters-2.json` | Configuration for 2017-10-15 | -
`aws/dist/awscli/botocore/data/proton/2020-07-20/endpoint-rule-set-1.json` | Configuration for 2020-07-20 | -
`aws/dist/awscli/botocore/data/proton/2020-07-20/paginators-1.json` | Configuration for 2020-07-20 | -
`aws/dist/awscli/botocore/data/proton/2020-07-20/service-2.json` | Configuration for 2020-07-20 | -
`aws/dist/awscli/botocore/data/proton/2020-07-20/waiters-2.json` | Configuration for 2020-07-20 | -
`aws/dist/awscli/botocore/data/qapps/2023-11-27/endpoint-rule-set-1.json` | Configuration for 2023-11-27 | -
`aws/dist/awscli/botocore/data/qapps/2023-11-27/paginators-1.json` | Configuration for 2023-11-27 | -
`aws/dist/awscli/botocore/data/qapps/2023-11-27/service-2.json` | Configuration for 2023-11-27 | -
`aws/dist/awscli/botocore/data/qapps/2023-11-27/waiters-2.json` | Configuration for 2023-11-27 | -
`aws/dist/awscli/botocore/data/qbusiness/2023-11-27/endpoint-rule-set-1.json` | Configuration for 2023-11-27 | -
`aws/dist/awscli/botocore/data/qbusiness/2023-11-27/paginators-1.json` | Configuration for 2023-11-27 | -
`aws/dist/awscli/botocore/data/qbusiness/2023-11-27/paginators-1.sdk-extras.json` | Configuration for 2023-11-27 | -
`aws/dist/awscli/botocore/data/qbusiness/2023-11-27/service-2.json` | Configuration for 2023-11-27 | -
`aws/dist/awscli/botocore/data/qbusiness/2023-11-27/waiters-2.json` | Configuration for 2023-11-27 | -
`aws/dist/awscli/botocore/data/qconnect/2020-10-19/endpoint-rule-set-1.json` | Configuration for 2020-10-19 | -
`aws/dist/awscli/botocore/data/qconnect/2020-10-19/paginators-1.json` | Configuration for 2020-10-19 | -
`aws/dist/awscli/botocore/data/qconnect/2020-10-19/service-2.json` | Configuration for 2020-10-19 | -
`aws/dist/awscli/botocore/data/qconnect/2020-10-19/waiters-2.json` | Configuration for 2020-10-19 | -
`aws/dist/awscli/botocore/data/quicksight/2018-04-01/endpoint-rule-set-1.json` | Configuration for 2018-04-01 | -
`aws/dist/awscli/botocore/data/quicksight/2018-04-01/paginators-1.json` | Configuration for 2018-04-01 | -
`aws/dist/awscli/botocore/data/quicksight/2018-04-01/paginators-1.sdk-extras.json` | Configuration for 2018-04-01 | -
`aws/dist/awscli/botocore/data/quicksight/2018-04-01/service-2.json` | Configuration for 2018-04-01 | -
`aws/dist/awscli/botocore/data/ram/2018-01-04/endpoint-rule-set-1.json` | Configuration for 2018-01-04 | -
`aws/dist/awscli/botocore/data/ram/2018-01-04/paginators-1.json` | Configuration for 2018-01-04 | -
`aws/dist/awscli/botocore/data/ram/2018-01-04/service-2.json` | Configuration for 2018-01-04 | -
`aws/dist/awscli/botocore/data/rbin/2021-06-15/endpoint-rule-set-1.json` | Configuration for 2021-06-15 | -
`aws/dist/awscli/botocore/data/rbin/2021-06-15/paginators-1.json` | Configuration for 2021-06-15 | -
`aws/dist/awscli/botocore/data/rbin/2021-06-15/service-2.json` | Configuration for 2021-06-15 | -
`aws/dist/awscli/botocore/data/rds/2014-10-31/endpoint-rule-set-1.json` | Configuration for 2014-10-31 | -
`aws/dist/awscli/botocore/data/rds/2014-10-31/paginators-1.json` | Configuration for 2014-10-31 | -
`aws/dist/awscli/botocore/data/rds/2014-10-31/paginators-1.sdk-extras.json` | Configuration for 2014-10-31 | -
`aws/dist/awscli/botocore/data/rds/2014-10-31/service-2.json` | Configuration for 2014-10-31 | -
`aws/dist/awscli/botocore/data/rds/2014-10-31/service-2.sdk-extras.json` | Configuration for 2014-10-31 | -
`aws/dist/awscli/botocore/data/rds/2014-10-31/waiters-2.json` | Configuration for 2014-10-31 | -
`aws/dist/awscli/botocore/data/rds-data/2018-08-01/endpoint-rule-set-1.json` | Configuration for 2018-08-01 | -
`aws/dist/awscli/botocore/data/rds-data/2018-08-01/paginators-1.json` | Configuration for 2018-08-01 | -
`aws/dist/awscli/botocore/data/rds-data/2018-08-01/service-2.json` | Configuration for 2018-08-01 | -
`aws/dist/awscli/botocore/data/redshift/2012-12-01/endpoint-rule-set-1.json` | Configuration for 2012-12-01 | -
`aws/dist/awscli/botocore/data/redshift/2012-12-01/paginators-1.json` | Configuration for 2012-12-01 | -
`aws/dist/awscli/botocore/data/redshift/2012-12-01/service-2.json` | Configuration for 2012-12-01 | -
`aws/dist/awscli/botocore/data/redshift/2012-12-01/waiters-2.json` | Configuration for 2012-12-01 | -
`aws/dist/awscli/botocore/data/redshift-data/2019-12-20/endpoint-rule-set-1.json` | Configuration for 2019-12-20 | -
`aws/dist/awscli/botocore/data/redshift-data/2019-12-20/paginators-1.json` | Configuration for 2019-12-20 | -
`aws/dist/awscli/botocore/data/redshift-data/2019-12-20/paginators-1.sdk-extras.json` | Configuration for 2019-12-20 | -
`aws/dist/awscli/botocore/data/redshift-data/2019-12-20/service-2.json` | Configuration for 2019-12-20 | -
`aws/dist/awscli/botocore/data/redshift-serverless/2021-04-21/endpoint-rule-set-1.json` | Configuration for 2021-04-21 | -
`aws/dist/awscli/botocore/data/redshift-serverless/2021-04-21/paginators-1.json` | Configuration for 2021-04-21 | -
`aws/dist/awscli/botocore/data/redshift-serverless/2021-04-21/service-2.json` | Configuration for 2021-04-21 | -
`aws/dist/awscli/botocore/data/rekognition/2016-06-27/endpoint-rule-set-1.json` | Configuration for 2016-06-27 | -
`aws/dist/awscli/botocore/data/rekognition/2016-06-27/paginators-1.json` | Configuration for 2016-06-27 | -
`aws/dist/awscli/botocore/data/rekognition/2016-06-27/service-2.json` | Configuration for 2016-06-27 | -
`aws/dist/awscli/botocore/data/rekognition/2016-06-27/waiters-2.json` | Configuration for 2016-06-27 | -
`aws/dist/awscli/botocore/data/repostspace/2022-05-13/endpoint-rule-set-1.json` | Configuration for 2022-05-13 | -
`aws/dist/awscli/botocore/data/repostspace/2022-05-13/paginators-1.json` | Configuration for 2022-05-13 | -
`aws/dist/awscli/botocore/data/repostspace/2022-05-13/service-2.json` | Configuration for 2022-05-13 | -
`aws/dist/awscli/botocore/data/repostspace/2022-05-13/waiters-2.json` | Configuration for 2022-05-13 | -
`aws/dist/awscli/botocore/data/resiliencehub/2020-04-30/endpoint-rule-set-1.json` | Configuration for 2020-04-30 | -
`aws/dist/awscli/botocore/data/resiliencehub/2020-04-30/paginators-1.json` | Configuration for 2020-04-30 | -
`aws/dist/awscli/botocore/data/resiliencehub/2020-04-30/service-2.json` | Configuration for 2020-04-30 | -
`aws/dist/awscli/botocore/data/resource-explorer-2/2022-07-28/endpoint-rule-set-1.json` | Configuration for 2022-07-28 | -
`aws/dist/awscli/botocore/data/resource-explorer-2/2022-07-28/paginators-1.json` | Configuration for 2022-07-28 | -
`aws/dist/awscli/botocore/data/resource-explorer-2/2022-07-28/paginators-1.sdk-extras.json` | Configuration for 2022-07-28 | -
`aws/dist/awscli/botocore/data/resource-explorer-2/2022-07-28/service-2.json` | Configuration for 2022-07-28 | -
`aws/dist/awscli/botocore/data/resource-explorer-2/2022-07-28/waiters-2.json` | Configuration for 2022-07-28 | -
`aws/dist/awscli/botocore/data/resource-groups/2017-11-27/endpoint-rule-set-1.json` | Configuration for 2017-11-27 | -
`aws/dist/awscli/botocore/data/resource-groups/2017-11-27/paginators-1.json` | Configuration for 2017-11-27 | -
`aws/dist/awscli/botocore/data/resource-groups/2017-11-27/paginators-1.sdk-extras.json` | Configuration for 2017-11-27 | -
`aws/dist/awscli/botocore/data/resource-groups/2017-11-27/service-2.json` | Configuration for 2017-11-27 | -
`aws/dist/awscli/botocore/data/resourcegroupstaggingapi/2017-01-26/endpoint-rule-set-1.json` | Configuration for 2017-01-26 | -
`aws/dist/awscli/botocore/data/resourcegroupstaggingapi/2017-01-26/paginators-1.json` | Configuration for 2017-01-26 | -
`aws/dist/awscli/botocore/data/resourcegroupstaggingapi/2017-01-26/service-2.json` | Configuration for 2017-01-26 | -
`aws/dist/awscli/botocore/data/rolesanywhere/2018-05-10/endpoint-rule-set-1.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/rolesanywhere/2018-05-10/paginators-1.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/rolesanywhere/2018-05-10/service-2.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/rolesanywhere/2018-05-10/waiters-2.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/route53/2013-04-01/endpoint-rule-set-1.json` | Configuration for 2013-04-01 | -
`aws/dist/awscli/botocore/data/route53/2013-04-01/paginators-1.json` | Configuration for 2013-04-01 | -
`aws/dist/awscli/botocore/data/route53/2013-04-01/service-2.json` | Configuration for 2013-04-01 | -
`aws/dist/awscli/botocore/data/route53/2013-04-01/waiters-2.json` | Configuration for 2013-04-01 | -
`aws/dist/awscli/botocore/data/route53-recovery-cluster/2019-12-02/endpoint-rule-set-1.json` | Configuration for 2019-12-02 | -
`aws/dist/awscli/botocore/data/route53-recovery-cluster/2019-12-02/paginators-1.json` | Configuration for 2019-12-02 | -
`aws/dist/awscli/botocore/data/route53-recovery-cluster/2019-12-02/service-2.json` | Configuration for 2019-12-02 | -
`aws/dist/awscli/botocore/data/route53-recovery-control-config/2020-11-02/endpoint-rule-set-1.json` | Configuration for 2020-11-02 | -
`aws/dist/awscli/botocore/data/route53-recovery-control-config/2020-11-02/paginators-1.json` | Configuration for 2020-11-02 | -
`aws/dist/awscli/botocore/data/route53-recovery-control-config/2020-11-02/service-2.json` | Configuration for 2020-11-02 | -
`aws/dist/awscli/botocore/data/route53-recovery-control-config/2020-11-02/waiters-2.json` | Configuration for 2020-11-02 | -
`aws/dist/awscli/botocore/data/route53-recovery-readiness/2019-12-02/endpoint-rule-set-1.json` | Configuration for 2019-12-02 | -
`aws/dist/awscli/botocore/data/route53-recovery-readiness/2019-12-02/paginators-1.json` | Configuration for 2019-12-02 | -
`aws/dist/awscli/botocore/data/route53-recovery-readiness/2019-12-02/service-2.json` | Configuration for 2019-12-02 | -
`aws/dist/awscli/botocore/data/route53domains/2014-05-15/endpoint-rule-set-1.json` | Configuration for 2014-05-15 | -
`aws/dist/awscli/botocore/data/route53domains/2014-05-15/paginators-1.json` | Configuration for 2014-05-15 | -
`aws/dist/awscli/botocore/data/route53domains/2014-05-15/service-2.json` | Configuration for 2014-05-15 | -
`aws/dist/awscli/botocore/data/route53globalresolver/2022-09-27/endpoint-rule-set-1.json` | Configuration for 2022-09-27 | -
`aws/dist/awscli/botocore/data/route53globalresolver/2022-09-27/paginators-1.json` | Configuration for 2022-09-27 | -
`aws/dist/awscli/botocore/data/route53globalresolver/2022-09-27/service-2.json` | Configuration for 2022-09-27 | -
`aws/dist/awscli/botocore/data/route53globalresolver/2022-09-27/waiters-2.json` | Configuration for 2022-09-27 | -
`aws/dist/awscli/botocore/data/route53profiles/2018-05-10/endpoint-rule-set-1.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/route53profiles/2018-05-10/paginators-1.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/route53profiles/2018-05-10/service-2.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/route53resolver/2018-04-01/endpoint-rule-set-1.json` | Configuration for 2018-04-01 | -
`aws/dist/awscli/botocore/data/route53resolver/2018-04-01/paginators-1.json` | Configuration for 2018-04-01 | -
`aws/dist/awscli/botocore/data/route53resolver/2018-04-01/paginators-1.sdk-extras.json` | Configuration for 2018-04-01 | -
`aws/dist/awscli/botocore/data/route53resolver/2018-04-01/service-2.json` | Configuration for 2018-04-01 | -
`aws/dist/awscli/botocore/data/rtbfabric/2023-05-15/endpoint-rule-set-1.json` | Configuration for 2023-05-15 | -
`aws/dist/awscli/botocore/data/rtbfabric/2023-05-15/paginators-1.json` | Configuration for 2023-05-15 | -
`aws/dist/awscli/botocore/data/rtbfabric/2023-05-15/service-2.json` | Configuration for 2023-05-15 | -
`aws/dist/awscli/botocore/data/rtbfabric/2023-05-15/waiters-2.json` | Configuration for 2023-05-15 | -
`aws/dist/awscli/botocore/data/rum/2018-05-10/endpoint-rule-set-1.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/rum/2018-05-10/paginators-1.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/rum/2018-05-10/service-2.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/rum/2018-05-10/waiters-2.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/s3/2006-03-01/endpoint-rule-set-1.json` | Configuration for 2006-03-01 | -
`aws/dist/awscli/botocore/data/s3/2006-03-01/paginators-1.json` | Configuration for 2006-03-01 | -
`aws/dist/awscli/botocore/data/s3/2006-03-01/paginators-1.sdk-extras.json` | Configuration for 2006-03-01 | -
`aws/dist/awscli/botocore/data/s3/2006-03-01/service-2.json` | Configuration for 2006-03-01 | -
`aws/dist/awscli/botocore/data/s3/2006-03-01/service-2.sdk-extras.json` | Configuration for 2006-03-01 | -
`aws/dist/awscli/botocore/data/s3/2006-03-01/waiters-2.json` | Configuration for 2006-03-01 | -
`aws/dist/awscli/botocore/data/s3control/2018-08-20/endpoint-rule-set-1.json` | Configuration for 2018-08-20 | -
`aws/dist/awscli/botocore/data/s3control/2018-08-20/paginators-1.json` | Configuration for 2018-08-20 | -
`aws/dist/awscli/botocore/data/s3control/2018-08-20/service-2.json` | Configuration for 2018-08-20 | -
`aws/dist/awscli/botocore/data/s3files/2025-05-05/endpoint-rule-set-1.json` | Configuration for 2025-05-05 | -
`aws/dist/awscli/botocore/data/s3files/2025-05-05/paginators-1.json` | Configuration for 2025-05-05 | -
`aws/dist/awscli/botocore/data/s3files/2025-05-05/service-2.json` | Configuration for 2025-05-05 | -
`aws/dist/awscli/botocore/data/s3files/2025-05-05/waiters-2.json` | Configuration for 2025-05-05 | -
`aws/dist/awscli/botocore/data/s3outposts/2017-07-25/endpoint-rule-set-1.json` | Configuration for 2017-07-25 | -
`aws/dist/awscli/botocore/data/s3outposts/2017-07-25/paginators-1.json` | Configuration for 2017-07-25 | -
`aws/dist/awscli/botocore/data/s3outposts/2017-07-25/service-2.json` | Configuration for 2017-07-25 | -
`aws/dist/awscli/botocore/data/s3tables/2018-05-10/endpoint-rule-set-1.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/s3tables/2018-05-10/paginators-1.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/s3tables/2018-05-10/service-2.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/s3tables/2018-05-10/waiters-2.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/s3vectors/2025-07-15/endpoint-rule-set-1.json` | Configuration for 2025-07-15 | -
`aws/dist/awscli/botocore/data/s3vectors/2025-07-15/paginators-1.json` | Configuration for 2025-07-15 | -
`aws/dist/awscli/botocore/data/s3vectors/2025-07-15/service-2.json` | Configuration for 2025-07-15 | -
`aws/dist/awscli/botocore/data/s3vectors/2025-07-15/waiters-2.json` | Configuration for 2025-07-15 | -
`aws/dist/awscli/botocore/data/sagemaker/2017-07-24/endpoint-rule-set-1.json` | Configuration for 2017-07-24 | -
`aws/dist/awscli/botocore/data/sagemaker/2017-07-24/paginators-1.json` | Configuration for 2017-07-24 | -
`aws/dist/awscli/botocore/data/sagemaker/2017-07-24/paginators-1.sdk-extras.json` | Configuration for 2017-07-24 | -
`aws/dist/awscli/botocore/data/sagemaker/2017-07-24/service-2.json` | Configuration for 2017-07-24 | -
`aws/dist/awscli/botocore/data/sagemaker/2017-07-24/waiters-2.json` | Configuration for 2017-07-24 | -
`aws/dist/awscli/botocore/data/sagemaker-a2i-runtime/2019-11-07/endpoint-rule-set-1.json` | Configuration for 2019-11-07 | -
`aws/dist/awscli/botocore/data/sagemaker-a2i-runtime/2019-11-07/paginators-1.json` | Configuration for 2019-11-07 | -
`aws/dist/awscli/botocore/data/sagemaker-a2i-runtime/2019-11-07/service-2.json` | Configuration for 2019-11-07 | -
`aws/dist/awscli/botocore/data/sagemaker-edge/2020-09-23/endpoint-rule-set-1.json` | Configuration for 2020-09-23 | -
`aws/dist/awscli/botocore/data/sagemaker-edge/2020-09-23/paginators-1.json` | Configuration for 2020-09-23 | -
`aws/dist/awscli/botocore/data/sagemaker-edge/2020-09-23/service-2.json` | Configuration for 2020-09-23 | -
`aws/dist/awscli/botocore/data/sagemaker-featurestore-runtime/2020-07-01/endpoint-rule-set-1.json` | Configuration for 2020-07-01 | -
`aws/dist/awscli/botocore/data/sagemaker-featurestore-runtime/2020-07-01/paginators-1.json` | Configuration for 2020-07-01 | -
`aws/dist/awscli/botocore/data/sagemaker-featurestore-runtime/2020-07-01/service-2.json` | Configuration for 2020-07-01 | -
`aws/dist/awscli/botocore/data/sagemaker-geospatial/2020-05-27/endpoint-rule-set-1.json` | Configuration for 2020-05-27 | -
`aws/dist/awscli/botocore/data/sagemaker-geospatial/2020-05-27/paginators-1.json` | Configuration for 2020-05-27 | -
`aws/dist/awscli/botocore/data/sagemaker-geospatial/2020-05-27/service-2.json` | Configuration for 2020-05-27 | -
`aws/dist/awscli/botocore/data/sagemaker-metrics/2022-09-30/endpoint-rule-set-1.json` | Configuration for 2022-09-30 | -
`aws/dist/awscli/botocore/data/sagemaker-metrics/2022-09-30/paginators-1.json` | Configuration for 2022-09-30 | -
`aws/dist/awscli/botocore/data/sagemaker-metrics/2022-09-30/service-2.json` | Configuration for 2022-09-30 | -
`aws/dist/awscli/botocore/data/sagemaker-runtime/2017-05-13/endpoint-rule-set-1.json` | Configuration for 2017-05-13 | -
`aws/dist/awscli/botocore/data/sagemaker-runtime/2017-05-13/paginators-1.json` | Configuration for 2017-05-13 | -
`aws/dist/awscli/botocore/data/sagemaker-runtime/2017-05-13/service-2.json` | Configuration for 2017-05-13 | -
`aws/dist/awscli/botocore/data/savingsplans/2019-06-28/endpoint-rule-set-1.json` | Configuration for 2019-06-28 | -
`aws/dist/awscli/botocore/data/savingsplans/2019-06-28/paginators-1.json` | Configuration for 2019-06-28 | -
`aws/dist/awscli/botocore/data/savingsplans/2019-06-28/service-2.json` | Configuration for 2019-06-28 | -
`aws/dist/awscli/botocore/data/scheduler/2021-06-30/endpoint-rule-set-1.json` | Configuration for 2021-06-30 | -
`aws/dist/awscli/botocore/data/scheduler/2021-06-30/paginators-1.json` | Configuration for 2021-06-30 | -
`aws/dist/awscli/botocore/data/scheduler/2021-06-30/service-2.json` | Configuration for 2021-06-30 | -
`aws/dist/awscli/botocore/data/schemas/2019-12-02/endpoint-rule-set-1.json` | Configuration for 2019-12-02 | -
`aws/dist/awscli/botocore/data/schemas/2019-12-02/paginators-1.json` | Configuration for 2019-12-02 | -
`aws/dist/awscli/botocore/data/schemas/2019-12-02/service-2.json` | Configuration for 2019-12-02 | -
`aws/dist/awscli/botocore/data/schemas/2019-12-02/waiters-2.json` | Configuration for 2019-12-02 | -
`aws/dist/awscli/botocore/data/sdb/2009-04-15/endpoint-rule-set-1.json` | Configuration for 2009-04-15 | -
`aws/dist/awscli/botocore/data/sdb/2009-04-15/paginators-1.json` | Configuration for 2009-04-15 | -
`aws/dist/awscli/botocore/data/sdb/2009-04-15/service-2.json` | Configuration for 2009-04-15 | -
`aws/dist/awscli/botocore/data/secretsmanager/2017-10-17/endpoint-rule-set-1.json` | Configuration for 2017-10-17 | -
`aws/dist/awscli/botocore/data/secretsmanager/2017-10-17/paginators-1.json` | Configuration for 2017-10-17 | -
`aws/dist/awscli/botocore/data/secretsmanager/2017-10-17/service-2.json` | Configuration for 2017-10-17 | -
`aws/dist/awscli/botocore/data/secretsmanager/2017-10-17/service-2.sdk-extras.json` | Configuration for 2017-10-17 | -
`aws/dist/awscli/botocore/data/security-ir/2018-05-10/endpoint-rule-set-1.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/security-ir/2018-05-10/paginators-1.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/security-ir/2018-05-10/paginators-1.sdk-extras.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/security-ir/2018-05-10/service-2.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/security-ir/2018-05-10/waiters-2.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/securityagent/2025-09-06/endpoint-rule-set-1.json` | Configuration for 2025-09-06 | -
`aws/dist/awscli/botocore/data/securityagent/2025-09-06/paginators-1.json` | Configuration for 2025-09-06 | -
`aws/dist/awscli/botocore/data/securityagent/2025-09-06/service-2.json` | Configuration for 2025-09-06 | -
`aws/dist/awscli/botocore/data/securityagent/2025-09-06/waiters-2.json` | Configuration for 2025-09-06 | -
`aws/dist/awscli/botocore/data/securityhub/2018-10-26/endpoint-rule-set-1.json` | Configuration for 2018-10-26 | -
`aws/dist/awscli/botocore/data/securityhub/2018-10-26/paginators-1.json` | Configuration for 2018-10-26 | -
`aws/dist/awscli/botocore/data/securityhub/2018-10-26/paginators-1.sdk-extras.json` | Configuration for 2018-10-26 | -
`aws/dist/awscli/botocore/data/securityhub/2018-10-26/service-2.json` | Configuration for 2018-10-26 | -
`aws/dist/awscli/botocore/data/securitylake/2018-05-10/endpoint-rule-set-1.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/securitylake/2018-05-10/paginators-1.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/securitylake/2018-05-10/paginators-1.sdk-extras.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/securitylake/2018-05-10/service-2.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/serverlessrepo/2017-09-08/endpoint-rule-set-1.json` | Configuration for 2017-09-08 | -
`aws/dist/awscli/botocore/data/serverlessrepo/2017-09-08/paginators-1.json` | Configuration for 2017-09-08 | -
`aws/dist/awscli/botocore/data/serverlessrepo/2017-09-08/service-2.json` | Configuration for 2017-09-08 | -
`aws/dist/awscli/botocore/data/service-quotas/2019-06-24/endpoint-rule-set-1.json` | Configuration for 2019-06-24 | -
`aws/dist/awscli/botocore/data/service-quotas/2019-06-24/paginators-1.json` | Configuration for 2019-06-24 | -
`aws/dist/awscli/botocore/data/service-quotas/2019-06-24/service-2.json` | Configuration for 2019-06-24 | -
`aws/dist/awscli/botocore/data/servicecatalog/2015-12-10/endpoint-rule-set-1.json` | Configuration for 2015-12-10 | -
`aws/dist/awscli/botocore/data/servicecatalog/2015-12-10/paginators-1.json` | Configuration for 2015-12-10 | -
`aws/dist/awscli/botocore/data/servicecatalog/2015-12-10/service-2.json` | Configuration for 2015-12-10 | -
`aws/dist/awscli/botocore/data/servicecatalog-appregistry/2020-06-24/endpoint-rule-set-1.json` | Configuration for 2020-06-24 | -
`aws/dist/awscli/botocore/data/servicecatalog-appregistry/2020-06-24/paginators-1.json` | Configuration for 2020-06-24 | -
`aws/dist/awscli/botocore/data/servicecatalog-appregistry/2020-06-24/service-2.json` | Configuration for 2020-06-24 | -
`aws/dist/awscli/botocore/data/servicediscovery/2017-03-14/endpoint-rule-set-1.json` | Configuration for 2017-03-14 | -
`aws/dist/awscli/botocore/data/servicediscovery/2017-03-14/paginators-1.json` | Configuration for 2017-03-14 | -
`aws/dist/awscli/botocore/data/servicediscovery/2017-03-14/paginators-1.sdk-extras.json` | Configuration for 2017-03-14 | -
`aws/dist/awscli/botocore/data/servicediscovery/2017-03-14/service-2.json` | Configuration for 2017-03-14 | -
`aws/dist/awscli/botocore/data/ses/2010-12-01/endpoint-rule-set-1.json` | Configuration for 2010-12-01 | -
`aws/dist/awscli/botocore/data/ses/2010-12-01/paginators-1.json` | Configuration for 2010-12-01 | -
`aws/dist/awscli/botocore/data/ses/2010-12-01/service-2.json` | Configuration for 2010-12-01 | -
`aws/dist/awscli/botocore/data/ses/2010-12-01/waiters-2.json` | Configuration for 2010-12-01 | -
`aws/dist/awscli/botocore/data/sesv2/2019-09-27/endpoint-rule-set-1.json` | Configuration for 2019-09-27 | -
`aws/dist/awscli/botocore/data/sesv2/2019-09-27/paginators-1.json` | Configuration for 2019-09-27 | -
`aws/dist/awscli/botocore/data/sesv2/2019-09-27/service-2.json` | Configuration for 2019-09-27 | -
`aws/dist/awscli/botocore/data/shield/2016-06-02/endpoint-rule-set-1.json` | Configuration for 2016-06-02 | -
`aws/dist/awscli/botocore/data/shield/2016-06-02/paginators-1.json` | Configuration for 2016-06-02 | -
`aws/dist/awscli/botocore/data/shield/2016-06-02/service-2.json` | Configuration for 2016-06-02 | -
`aws/dist/awscli/botocore/data/signer/2017-08-25/endpoint-rule-set-1.json` | Configuration for 2017-08-25 | -
`aws/dist/awscli/botocore/data/signer/2017-08-25/paginators-1.json` | Configuration for 2017-08-25 | -
`aws/dist/awscli/botocore/data/signer/2017-08-25/service-2.json` | Configuration for 2017-08-25 | -
`aws/dist/awscli/botocore/data/signer/2017-08-25/waiters-2.json` | Configuration for 2017-08-25 | -
`aws/dist/awscli/botocore/data/signer-data/2017-08-25/endpoint-rule-set-1.json` | Configuration for 2017-08-25 | -
`aws/dist/awscli/botocore/data/signer-data/2017-08-25/paginators-1.json` | Configuration for 2017-08-25 | -
`aws/dist/awscli/botocore/data/signer-data/2017-08-25/service-2.json` | Configuration for 2017-08-25 | -
`aws/dist/awscli/botocore/data/signer-data/2017-08-25/waiters-2.json` | Configuration for 2017-08-25 | -
`aws/dist/awscli/botocore/data/signin/2023-01-01/endpoint-rule-set-1.json` | Configuration for 2023-01-01 | -
`aws/dist/awscli/botocore/data/signin/2023-01-01/paginators-1.json` | Configuration for 2023-01-01 | -
`aws/dist/awscli/botocore/data/signin/2023-01-01/service-2.json` | Configuration for 2023-01-01 | -
`aws/dist/awscli/botocore/data/simpledbv2/2025-09-26/endpoint-rule-set-1.json` | Configuration for 2025-09-26 | -
`aws/dist/awscli/botocore/data/simpledbv2/2025-09-26/paginators-1.json` | Configuration for 2025-09-26 | -
`aws/dist/awscli/botocore/data/simpledbv2/2025-09-26/service-2.json` | Configuration for 2025-09-26 | -
`aws/dist/awscli/botocore/data/simpledbv2/2025-09-26/waiters-2.json` | Configuration for 2025-09-26 | -
`aws/dist/awscli/botocore/data/simspaceweaver/2022-10-28/endpoint-rule-set-1.json` | Configuration for 2022-10-28 | -
`aws/dist/awscli/botocore/data/simspaceweaver/2022-10-28/paginators-1.json` | Configuration for 2022-10-28 | -
`aws/dist/awscli/botocore/data/simspaceweaver/2022-10-28/service-2.json` | Configuration for 2022-10-28 | -
`aws/dist/awscli/botocore/data/snow-device-management/2021-08-04/endpoint-rule-set-1.json` | Configuration for 2021-08-04 | -
`aws/dist/awscli/botocore/data/snow-device-management/2021-08-04/paginators-1.json` | Configuration for 2021-08-04 | -
`aws/dist/awscli/botocore/data/snow-device-management/2021-08-04/service-2.json` | Configuration for 2021-08-04 | -
`aws/dist/awscli/botocore/data/snowball/2016-06-30/endpoint-rule-set-1.json` | Configuration for 2016-06-30 | -
`aws/dist/awscli/botocore/data/snowball/2016-06-30/paginators-1.json` | Configuration for 2016-06-30 | -
`aws/dist/awscli/botocore/data/snowball/2016-06-30/service-2.json` | Configuration for 2016-06-30 | -
`aws/dist/awscli/botocore/data/sns/2010-03-31/endpoint-rule-set-1.json` | Configuration for 2010-03-31 | -
`aws/dist/awscli/botocore/data/sns/2010-03-31/paginators-1.json` | Configuration for 2010-03-31 | -
`aws/dist/awscli/botocore/data/sns/2010-03-31/service-2.json` | Configuration for 2010-03-31 | -
`aws/dist/awscli/botocore/data/socialmessaging/2024-01-01/endpoint-rule-set-1.json` | Configuration for 2024-01-01 | -
`aws/dist/awscli/botocore/data/socialmessaging/2024-01-01/paginators-1.json` | Configuration for 2024-01-01 | -
`aws/dist/awscli/botocore/data/socialmessaging/2024-01-01/service-2.json` | Configuration for 2024-01-01 | -
`aws/dist/awscli/botocore/data/sqs/2012-11-05/endpoint-rule-set-1.json` | Configuration for 2012-11-05 | -
`aws/dist/awscli/botocore/data/sqs/2012-11-05/paginators-1.json` | Configuration for 2012-11-05 | -
`aws/dist/awscli/botocore/data/sqs/2012-11-05/service-2.json` | Configuration for 2012-11-05 | -
`aws/dist/awscli/botocore/data/ssm/2014-11-06/endpoint-rule-set-1.json` | Configuration for 2014-11-06 | -
`aws/dist/awscli/botocore/data/ssm/2014-11-06/paginators-1.json` | Configuration for 2014-11-06 | -
`aws/dist/awscli/botocore/data/ssm/2014-11-06/service-2.json` | Configuration for 2014-11-06 | -
`aws/dist/awscli/botocore/data/ssm/2014-11-06/waiters-2.json` | Configuration for 2014-11-06 | -
`aws/dist/awscli/botocore/data/ssm-contacts/2021-05-03/endpoint-rule-set-1.json` | Configuration for 2021-05-03 | -
`aws/dist/awscli/botocore/data/ssm-contacts/2021-05-03/paginators-1.json` | Configuration for 2021-05-03 | -
`aws/dist/awscli/botocore/data/ssm-contacts/2021-05-03/service-2.json` | Configuration for 2021-05-03 | -
`aws/dist/awscli/botocore/data/ssm-guiconnect/2021-05-01/endpoint-rule-set-1.json` | Configuration for 2021-05-01 | -
`aws/dist/awscli/botocore/data/ssm-guiconnect/2021-05-01/paginators-1.json` | Configuration for 2021-05-01 | -
`aws/dist/awscli/botocore/data/ssm-guiconnect/2021-05-01/service-2.json` | Configuration for 2021-05-01 | -
`aws/dist/awscli/botocore/data/ssm-incidents/2018-05-10/endpoint-rule-set-1.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/ssm-incidents/2018-05-10/paginators-1.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/ssm-incidents/2018-05-10/service-2.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/ssm-incidents/2018-05-10/waiters-2.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/ssm-quicksetup/2018-05-10/endpoint-rule-set-1.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/ssm-quicksetup/2018-05-10/paginators-1.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/ssm-quicksetup/2018-05-10/service-2.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/ssm-sap/2018-05-10/endpoint-rule-set-1.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/ssm-sap/2018-05-10/paginators-1.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/ssm-sap/2018-05-10/service-2.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/sso/2019-06-10/endpoint-rule-set-1.json` | Configuration for 2019-06-10 | -
`aws/dist/awscli/botocore/data/sso/2019-06-10/paginators-1.json` | Configuration for 2019-06-10 | -
`aws/dist/awscli/botocore/data/sso/2019-06-10/service-2.json` | Configuration for 2019-06-10 | -
`aws/dist/awscli/botocore/data/sso-admin/2020-07-20/endpoint-rule-set-1.json` | Configuration for 2020-07-20 | -
`aws/dist/awscli/botocore/data/sso-admin/2020-07-20/paginators-1.json` | Configuration for 2020-07-20 | -
`aws/dist/awscli/botocore/data/sso-admin/2020-07-20/service-2.json` | Configuration for 2020-07-20 | -
`aws/dist/awscli/botocore/data/sso-admin/2020-07-20/waiters-2.json` | Configuration for 2020-07-20 | -
`aws/dist/awscli/botocore/data/sso-oidc/2019-06-10/endpoint-rule-set-1.json` | Configuration for 2019-06-10 | -
`aws/dist/awscli/botocore/data/sso-oidc/2019-06-10/paginators-1.json` | Configuration for 2019-06-10 | -
`aws/dist/awscli/botocore/data/sso-oidc/2019-06-10/service-2.json` | Configuration for 2019-06-10 | -
`aws/dist/awscli/botocore/data/stepfunctions/2016-11-23/endpoint-rule-set-1.json` | Configuration for 2016-11-23 | -
`aws/dist/awscli/botocore/data/stepfunctions/2016-11-23/paginators-1.json` | Configuration for 2016-11-23 | -
`aws/dist/awscli/botocore/data/stepfunctions/2016-11-23/service-2.json` | Configuration for 2016-11-23 | -
`aws/dist/awscli/botocore/data/storagegateway/2013-06-30/endpoint-rule-set-1.json` | Configuration for 2013-06-30 | -
`aws/dist/awscli/botocore/data/storagegateway/2013-06-30/paginators-1.json` | Configuration for 2013-06-30 | -
`aws/dist/awscli/botocore/data/storagegateway/2013-06-30/service-2.json` | Configuration for 2013-06-30 | -
`aws/dist/awscli/botocore/data/sts/2011-06-15/endpoint-rule-set-1.json` | Configuration for 2011-06-15 | -
`aws/dist/awscli/botocore/data/sts/2011-06-15/paginators-1.json` | Configuration for 2011-06-15 | -
`aws/dist/awscli/botocore/data/sts/2011-06-15/service-2.json` | Configuration for 2011-06-15 | -
`aws/dist/awscli/botocore/data/supplychain/2024-01-01/endpoint-rule-set-1.json` | Configuration for 2024-01-01 | -
`aws/dist/awscli/botocore/data/supplychain/2024-01-01/paginators-1.json` | Configuration for 2024-01-01 | -
`aws/dist/awscli/botocore/data/supplychain/2024-01-01/service-2.json` | Configuration for 2024-01-01 | -
`aws/dist/awscli/botocore/data/support/2013-04-15/endpoint-rule-set-1.json` | Configuration for 2013-04-15 | -
`aws/dist/awscli/botocore/data/support/2013-04-15/paginators-1.json` | Configuration for 2013-04-15 | -
`aws/dist/awscli/botocore/data/support/2013-04-15/service-2.json` | Configuration for 2013-04-15 | -
`aws/dist/awscli/botocore/data/support-app/2021-08-20/endpoint-rule-set-1.json` | Configuration for 2021-08-20 | -
`aws/dist/awscli/botocore/data/support-app/2021-08-20/paginators-1.json` | Configuration for 2021-08-20 | -
`aws/dist/awscli/botocore/data/support-app/2021-08-20/service-2.json` | Configuration for 2021-08-20 | -
`aws/dist/awscli/botocore/data/sustainability/2018-05-10/endpoint-rule-set-1.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/sustainability/2018-05-10/paginators-1.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/sustainability/2018-05-10/service-2.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/swf/2012-01-25/endpoint-rule-set-1.json` | Configuration for 2012-01-25 | -
`aws/dist/awscli/botocore/data/swf/2012-01-25/paginators-1.json` | Configuration for 2012-01-25 | -
`aws/dist/awscli/botocore/data/swf/2012-01-25/service-2.json` | Configuration for 2012-01-25 | -
`aws/dist/awscli/botocore/data/synthetics/2017-10-11/endpoint-rule-set-1.json` | Configuration for 2017-10-11 | -
`aws/dist/awscli/botocore/data/synthetics/2017-10-11/paginators-1.json` | Configuration for 2017-10-11 | -
`aws/dist/awscli/botocore/data/synthetics/2017-10-11/service-2.json` | Configuration for 2017-10-11 | -
`aws/dist/awscli/botocore/data/taxsettings/2018-05-10/endpoint-rule-set-1.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/taxsettings/2018-05-10/paginators-1.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/taxsettings/2018-05-10/service-2.json` | Configuration for 2018-05-10 | -
`aws/dist/awscli/botocore/data/textract/2018-06-27/endpoint-rule-set-1.json` | Configuration for 2018-06-27 | -
`aws/dist/awscli/botocore/data/textract/2018-06-27/paginators-1.json` | Configuration for 2018-06-27 | -
`aws/dist/awscli/botocore/data/textract/2018-06-27/service-2.json` | Configuration for 2018-06-27 | -
`aws/dist/awscli/botocore/data/timestream-influxdb/2023-01-27/endpoint-rule-set-1.json` | Configuration for 2023-01-27 | -
`aws/dist/awscli/botocore/data/timestream-influxdb/2023-01-27/paginators-1.json` | Configuration for 2023-01-27 | -
`aws/dist/awscli/botocore/data/timestream-influxdb/2023-01-27/service-2.json` | Configuration for 2023-01-27 | -
`aws/dist/awscli/botocore/data/timestream-query/2018-11-01/endpoint-rule-set-1.json` | Configuration for 2018-11-01 | -
`aws/dist/awscli/botocore/data/timestream-query/2018-11-01/paginators-1.json` | Configuration for 2018-11-01 | -
`aws/dist/awscli/botocore/data/timestream-query/2018-11-01/service-2.json` | Configuration for 2018-11-01 | -
`aws/dist/awscli/botocore/data/timestream-write/2018-11-01/endpoint-rule-set-1.json` | Configuration for 2018-11-01 | -
`aws/dist/awscli/botocore/data/timestream-write/2018-11-01/paginators-1.json` | Configuration for 2018-11-01 | -
`aws/dist/awscli/botocore/data/timestream-write/2018-11-01/service-2.json` | Configuration for 2018-11-01 | -
`aws/dist/awscli/botocore/data/tnb/2008-10-21/endpoint-rule-set-1.json` | Configuration for 2008-10-21 | -
`aws/dist/awscli/botocore/data/tnb/2008-10-21/paginators-1.json` | Configuration for 2008-10-21 | -
`aws/dist/awscli/botocore/data/tnb/2008-10-21/service-2.json` | Configuration for 2008-10-21 | -
`aws/dist/awscli/botocore/data/transcribe/2017-10-26/endpoint-rule-set-1.json` | Configuration for 2017-10-26 | -
`aws/dist/awscli/botocore/data/transcribe/2017-10-26/paginators-1.json` | Configuration for 2017-10-26 | -
`aws/dist/awscli/botocore/data/transcribe/2017-10-26/service-2.json` | Configuration for 2017-10-26 | -
`aws/dist/awscli/botocore/data/transcribe/2017-10-26/waiters-2.json` | Configuration for 2017-10-26 | -
`aws/dist/awscli/botocore/data/transfer/2018-11-05/endpoint-rule-set-1.json` | Configuration for 2018-11-05 | -
`aws/dist/awscli/botocore/data/transfer/2018-11-05/paginators-1.json` | Configuration for 2018-11-05 | -
`aws/dist/awscli/botocore/data/transfer/2018-11-05/service-2.json` | Configuration for 2018-11-05 | -
`aws/dist/awscli/botocore/data/transfer/2018-11-05/waiters-2.json` | Configuration for 2018-11-05 | -
`aws/dist/awscli/botocore/data/translate/2017-07-01/endpoint-rule-set-1.json` | Configuration for 2017-07-01 | -
`aws/dist/awscli/botocore/data/translate/2017-07-01/paginators-1.json` | Configuration for 2017-07-01 | -
`aws/dist/awscli/botocore/data/translate/2017-07-01/service-2.json` | Configuration for 2017-07-01 | -
`aws/dist/awscli/botocore/data/trustedadvisor/2022-09-15/endpoint-rule-set-1.json` | Configuration for 2022-09-15 | -
`aws/dist/awscli/botocore/data/trustedadvisor/2022-09-15/paginators-1.json` | Configuration for 2022-09-15 | -
`aws/dist/awscli/botocore/data/trustedadvisor/2022-09-15/service-2.json` | Configuration for 2022-09-15 | -
`aws/dist/awscli/botocore/data/trustedadvisor/2022-09-15/waiters-2.json` | Configuration for 2022-09-15 | -
`aws/dist/awscli/botocore/data/uxc/2024-07-01/endpoint-rule-set-1.json` | Configuration for 2024-07-01 | -
`aws/dist/awscli/botocore/data/uxc/2024-07-01/paginators-1.json` | Configuration for 2024-07-01 | -
`aws/dist/awscli/botocore/data/uxc/2024-07-01/service-2.json` | Configuration for 2024-07-01 | -
`aws/dist/awscli/botocore/data/uxc/2024-07-01/waiters-2.json` | Configuration for 2024-07-01 | -
`aws/dist/awscli/botocore/data/verifiedpermissions/2021-12-01/endpoint-rule-set-1.json` | Configuration for 2021-12-01 | -
`aws/dist/awscli/botocore/data/verifiedpermissions/2021-12-01/paginators-1.json` | Configuration for 2021-12-01 | -
`aws/dist/awscli/botocore/data/verifiedpermissions/2021-12-01/service-2.json` | Configuration for 2021-12-01 | -
`aws/dist/awscli/botocore/data/verifiedpermissions/2021-12-01/waiters-2.json` | Configuration for 2021-12-01 | -
`aws/dist/awscli/botocore/data/voice-id/2021-09-27/endpoint-rule-set-1.json` | Configuration for 2021-09-27 | -
`aws/dist/awscli/botocore/data/voice-id/2021-09-27/paginators-1.json` | Configuration for 2021-09-27 | -
`aws/dist/awscli/botocore/data/voice-id/2021-09-27/service-2.json` | Configuration for 2021-09-27 | -
`aws/dist/awscli/botocore/data/vpc-lattice/2022-11-30/endpoint-rule-set-1.json` | Configuration for 2022-11-30 | -
`aws/dist/awscli/botocore/data/vpc-lattice/2022-11-30/paginators-1.json` | Configuration for 2022-11-30 | -
`aws/dist/awscli/botocore/data/vpc-lattice/2022-11-30/service-2.json` | Configuration for 2022-11-30 | -
`aws/dist/awscli/botocore/data/vpc-lattice/2022-11-30/waiters-2.json` | Configuration for 2022-11-30 | -
`aws/dist/awscli/botocore/data/waf/2015-08-24/endpoint-rule-set-1.json` | Configuration for 2015-08-24 | -
`aws/dist/awscli/botocore/data/waf/2015-08-24/paginators-1.json` | Configuration for 2015-08-24 | -
`aws/dist/awscli/botocore/data/waf/2015-08-24/service-2.json` | Configuration for 2015-08-24 | -
`aws/dist/awscli/botocore/data/waf-regional/2016-11-28/endpoint-rule-set-1.json` | Configuration for 2016-11-28 | -
`aws/dist/awscli/botocore/data/waf-regional/2016-11-28/paginators-1.json` | Configuration for 2016-11-28 | -
`aws/dist/awscli/botocore/data/waf-regional/2016-11-28/service-2.json` | Configuration for 2016-11-28 | -
`aws/dist/awscli/botocore/data/wafv2/2019-07-29/endpoint-rule-set-1.json` | Configuration for 2019-07-29 | -
`aws/dist/awscli/botocore/data/wafv2/2019-07-29/paginators-1.json` | Configuration for 2019-07-29 | -
`aws/dist/awscli/botocore/data/wafv2/2019-07-29/service-2.json` | Configuration for 2019-07-29 | -
`aws/dist/awscli/botocore/data/wellarchitected/2020-03-31/endpoint-rule-set-1.json` | Configuration for 2020-03-31 | -
`aws/dist/awscli/botocore/data/wellarchitected/2020-03-31/paginators-1.json` | Configuration for 2020-03-31 | -
`aws/dist/awscli/botocore/data/wellarchitected/2020-03-31/service-2.json` | Configuration for 2020-03-31 | -
`aws/dist/awscli/botocore/data/wickr/2024-02-01/endpoint-rule-set-1.json` | Configuration for 2024-02-01 | -
`aws/dist/awscli/botocore/data/wickr/2024-02-01/paginators-1.json` | Configuration for 2024-02-01 | -
`aws/dist/awscli/botocore/data/wickr/2024-02-01/service-2.json` | Configuration for 2024-02-01 | -
`aws/dist/awscli/botocore/data/wickr/2024-02-01/waiters-2.json` | Configuration for 2024-02-01 | -
`aws/dist/awscli/botocore/data/wisdom/2020-10-19/endpoint-rule-set-1.json` | Configuration for 2020-10-19 | -
`aws/dist/awscli/botocore/data/wisdom/2020-10-19/paginators-1.json` | Configuration for 2020-10-19 | -
`aws/dist/awscli/botocore/data/wisdom/2020-10-19/service-2.json` | Configuration for 2020-10-19 | -
`aws/dist/awscli/botocore/data/workdocs/2016-05-01/endpoint-rule-set-1.json` | Configuration for 2016-05-01 | -
`aws/dist/awscli/botocore/data/workdocs/2016-05-01/paginators-1.json` | Configuration for 2016-05-01 | -
`aws/dist/awscli/botocore/data/workdocs/2016-05-01/service-2.json` | Configuration for 2016-05-01 | -
`aws/dist/awscli/botocore/data/workmail/2017-10-01/endpoint-rule-set-1.json` | Configuration for 2017-10-01 | -
`aws/dist/awscli/botocore/data/workmail/2017-10-01/paginators-1.json` | Configuration for 2017-10-01 | -
`aws/dist/awscli/botocore/data/workmail/2017-10-01/service-2.json` | Configuration for 2017-10-01 | -
`aws/dist/awscli/botocore/data/workmailmessageflow/2019-05-01/endpoint-rule-set-1.json` | Configuration for 2019-05-01 | -
`aws/dist/awscli/botocore/data/workmailmessageflow/2019-05-01/paginators-1.json` | Configuration for 2019-05-01 | -
`aws/dist/awscli/botocore/data/workmailmessageflow/2019-05-01/service-2.json` | Configuration for 2019-05-01 | -
`aws/dist/awscli/botocore/data/workspaces/2015-04-08/endpoint-rule-set-1.json` | Configuration for 2015-04-08 | -
`aws/dist/awscli/botocore/data/workspaces/2015-04-08/paginators-1.json` | Configuration for 2015-04-08 | -
`aws/dist/awscli/botocore/data/workspaces/2015-04-08/service-2.json` | Configuration for 2015-04-08 | -
`aws/dist/awscli/botocore/data/workspaces-instances/2022-07-26/endpoint-rule-set-1.json` | Configuration for 2022-07-26 | -
`aws/dist/awscli/botocore/data/workspaces-instances/2022-07-26/paginators-1.json` | Configuration for 2022-07-26 | -
`aws/dist/awscli/botocore/data/workspaces-instances/2022-07-26/service-2.json` | Configuration for 2022-07-26 | -
`aws/dist/awscli/botocore/data/workspaces-instances/2022-07-26/waiters-2.json` | Configuration for 2022-07-26 | -
`aws/dist/awscli/botocore/data/workspaces-thin-client/2023-08-22/endpoint-rule-set-1.json` | Configuration for 2023-08-22 | -
`aws/dist/awscli/botocore/data/workspaces-thin-client/2023-08-22/paginators-1.json` | Configuration for 2023-08-22 | -
`aws/dist/awscli/botocore/data/workspaces-thin-client/2023-08-22/service-2.json` | Configuration for 2023-08-22 | -
`aws/dist/awscli/botocore/data/workspaces-web/2020-07-08/endpoint-rule-set-1.json` | Configuration for 2020-07-08 | -
`aws/dist/awscli/botocore/data/workspaces-web/2020-07-08/paginators-1.json` | Configuration for 2020-07-08 | -
`aws/dist/awscli/botocore/data/workspaces-web/2020-07-08/service-2.json` | Configuration for 2020-07-08 | -
`aws/dist/awscli/botocore/data/workspaces-web/2020-07-08/waiters-2.json` | Configuration for 2020-07-08 | -
`aws/dist/awscli/botocore/data/xray/2016-04-12/endpoint-rule-set-1.json` | Configuration for 2016-04-12 | -
`aws/dist/awscli/botocore/data/xray/2016-04-12/paginators-1.json` | Configuration for 2016-04-12 | -
`aws/dist/awscli/botocore/data/xray/2016-04-12/service-2.json` | Configuration for 2016-04-12 | -
`aws/dist/awscli/customizations/wizard/wizards/configure/_main.yml` | Configuration for configure | -
`aws/dist/awscli/customizations/wizard/wizards/dynamodb/new-table.yml` | Configuration for dynamodb | -
`aws/dist/awscli/customizations/wizard/wizards/events/new-rule.yml` | Configuration for events | -
`aws/dist/awscli/customizations/wizard/wizards/iam/new-role.yml` | Configuration for iam | -
`aws/dist/awscli/customizations/wizard/wizards/lambda/new-function.yml` | Configuration for lambda | -
`aws/dist/awscli/data/cli.json` | Configuration for data | -
`aws/dist/awscli/data/metadata.json` | Configuration for data | -
`aws/dist/awscli/topics/topic-tags.json` | Configuration for topics | -
`backups/20260511-212017/Dominion/domdata/domdata.py` | Domdata | parse_dt, to_jsonable, emit, load_mt5, connect
`catboost_info/catboost_training.json` | Configuration for catboost_info | -
`causal_engine/__init__.py` |   Init   | -
`causal_engine/cli.py` | CLI interface | cmd_run, cmd_show, cmd_export, main
`causal_engine/config.py` | Configuration for causal_engine | -
`causal_engine/dag.py` | Dag | init_dag_schema, store_dag, query_causal_predecessors, export_dag_to_json, send_dag_to_ragd
`causal_engine/information.py` | Information | transfer_entropy, conditional_entropy_knn, compute_all_transfer_entropies, compute_mutual_information_scores
`causal_engine/pc_algorithm.py` | Pc Algorithm | fisher_z_test, partial_correlation, pc_algorithm, extract_causal_paths, compute_causal_strength
`causal_engine/tests/__init__.py` |   Init   | -
`causal_engine/tests/test_pc.py` | Tests for pc | test_pc_finds_independence_uncorrelated, test_pc_finds_dependence_correlated, test_fisher_z_test, test_partial_correlation
`config/dominion_ignore_policy.json` | Configuration for config | -
`config/forbidden_tokens.json` | Configuration for config | -
`cpp/CMakeLists.txt` | Cmakelists | -
`cpp/build/CMakeFiles/3.31.6/CompilerIdCXX/CMakeCXXCompilerId.cpp` | Cmakecxxcompilerid | -
`cpp/build/CMakeFiles/CMakeConfigureLog.yaml` | Configuration for cmakefiles | -
`cpp/build/Makefile` | Makefile | -
`cpp/hydra_288b_fast_train.cpp` | Training for hydra_288b_fast_train | -
`cpp/kernels/microstructure.cpp` | Microstructure | -
`cpp/kernels/microstructure.hpp` | Microstructure | -
`cpp/kernels/module.cpp` | Module | -
`cpp/kernels/rolling.cpp` | Rolling | -
`cpp/kernels/rolling.hpp` | Rolling | -
`cpp/kernels/statistical.cpp` | Statistical | -
`cpp/kernels/statistical.hpp` | Statistical | -
`cpp/kernels/technical.cpp` | Technical | -
`cpp/kernels/technical.hpp` | Technical | -
`data/dataset_v1_metadata.json` | Configuration for data | -
`data/hydra_binary_288b/meta.json` | Configuration for hydra_binary_288b | -
`data/hydra_xauusd_m5_master_schema.json` | Configuration for data | -
`data/mt5_history/XAUUSD_D1.json` | Configuration for mt5_history | -
`data/mt5_history/XAUUSD_D1_raw.json` | Configuration for mt5_history | -
`data/mt5_history/XAUUSD_H1.json` | Configuration for mt5_history | -
`data/mt5_history/XAUUSD_H4.json` | Configuration for mt5_history | -
`data/mt5_history/XAUUSD_H4_raw.json` | Configuration for mt5_history | -
`data/mt5_history/_fetch_temp.py` | Fetches _temp data | -
`data/mt5_history/inventory.json` | Configuration for mt5_history | -
`data/registry/semantic_column_mapping.json` | Configuration for registry | -
`data_pipeline/__init__.py` |   Init   | -
`data_pipeline/cli.py` | CLI interface | cmd_run, cmd_status, cmd_doctor, cmd_report, cmd_backfill
`data_pipeline/config.py` | Configuration for data_pipeline | -
`data_pipeline/features/__init__.py` |   Init   | -
`data_pipeline/features/calendar.py` | Calendar | compute_day_of_week, compute_week_of_month, compute_month_of_year, compute_quarter, compute_month_end
`data_pipeline/features/cot_features.py` | Cot Features | compute_cot_percentiles, compute_cot_momentum, compute_hedger_ratio, compute_spec_concentration, compute_oi_features
`data_pipeline/features/crossasset.py` | Crossasset | compute_rolling_correlation, compute_rolling_beta, compute_lead_lag, compute_granger, compute_partial_correlation
`data_pipeline/features/macro.py` | Macro | compute_real_yield_features, compute_yield_curve_features, compute_breakeven_features, compute_dxy_momentum, compute_fed_features
`data_pipeline/features/microstructure.py` | Microstructure | compute_roll_spread, compute_corwin_schultz, compute_amihud, compute_kyle_lambda, compute_vpin
`data_pipeline/features/price.py` | Price | compute_returns, compute_rolling_stats, compute_sharpe, compute_drawdown, compute_hurst
`data_pipeline/features/regime.py` | Regime | detect_tactical_regime_hmm, detect_micro_regime, compute_regime_duration, compute_regime_transition, compute_historical_return_by_regime
`data_pipeline/features/regime_storage.py` | Regime Storage | store_regime_labels, get_latest_regime
`data_pipeline/features/store.py` | Store | FeatureStore, compute_all_features, validate_features, compute_ic, store_features
`data_pipeline/fusion/__init__.py` |   Init   | -
`data_pipeline/fusion/bridge.py` | Bridge | brownian_bridge, reconstruct_ticks_from_bars
`data_pipeline/fusion/conflict.py` | Conflict | resolve_conflict, detect_anomaly
`data_pipeline/fusion/kalman.py` | Kalman | KalmanFilter, KalmanFilterBank, predict, update, init_trust
`data_pipeline/health/__init__.py` |   Init   | -
`data_pipeline/health/anomaly.py` | Anomaly | AnomalyDetector, detect_price_anomaly, detect_volume_anomaly, detect_source_divergence, log_anomaly
`data_pipeline/health/monitor.py` | Monitor | PipelineMonitor, check_staleness, detect_gaps, fill_small_gaps, detect_distribution_drift
`data_pipeline/health/report.py` | Report | ReportGenerator, generate_report, store_report, write_report_file, send_to_ragd
`data_pipeline/pipeline.py` | Pipeline | Pipeline, init_db, log_run_start, log_run_complete, fetch_sources
`data_pipeline/schema.py` | Schema | init_schema
`data_pipeline/sources/__init__.py` |   Init   | -
`data_pipeline/sources/alphavantage.py` | Alphavantage | AlphaVantageSource, fetch, validate
`data_pipeline/sources/base.py` | Base | DataSource, fetch, validate, health, mark_success
`data_pipeline/sources/cot.py` | Cot | COTSource, fetch, validate
`data_pipeline/sources/domdata.py` | Domdata | DomdataSource, fetch, validate
`data_pipeline/sources/fred.py` | Fred | FREDSource, fetch, validate
`data_pipeline/sources/yahoo.py` | Yahoo | YahooSource, fetch, validate
`data_pipeline/tests/__init__.py` |   Init   | -
`data_pipeline/tests/test_features.py` | Tests for features | test_compute_returns, test_compute_hurst, test_compute_autocorr, test_feature_store_validation, test_feature_ic_computation
`data_pipeline/tests/test_fusion.py` | Tests for fusion | test_kalman_filter_converges, test_kalman_filter_bank_trust_update, test_brownian_bridge_respects_ohlc, test_conflict_resolution_quarantine, test_anomaly_detection
`data_pipeline/tests/test_health.py` | Tests for health | test_anomaly_detector_price, test_anomaly_detector_volume, test_source_divergence_detection
`data_pipeline/tests/test_sources.py` | Tests for sources | test_yahoo_source_validate, test_domdata_source_graceful_degradation, test_yahoo_source_retry
`domdata/check_no_trading.py` | Validates domdata | should_scan, scan_repo, main
`domdata/domdata.py` | Domdata | -
`domdata/domdata_pkg/__init__.py` |   Init   | -
`domdata/domdata_pkg/cli.py` | CLI interface | add_common, add_output, main
`domdata/domdata_pkg/collector.py` | Collector | utc_now, iso_now, resolve_root, hour_path, append_jsonl
`domdata/domdata_pkg/commands.py` | Commands | doctor, version, terminal_info, account_info, symbols_get
`domdata/domdata_pkg/config.py` | Configuration for domdata_pkg | DomdataConfig, read_config, mask_value, doctor_rows
`domdata/domdata_pkg/convert.py` | Convert | convert_xau, duckdb_init, duckdb_summary
`domdata/domdata_pkg/forbidden_tokens.py` | Forbidden Tokens | -
`domdata/domdata_pkg/health.py` | Health | -
`domdata/domdata_pkg/mt5_client.py` | MT5_CLIENT interface | parse_dt, load_mt5, connect, shutdown, timeframe
`domdata/domdata_pkg/safety.py` | Safety | apply_read_only_guard, blocked_command, notice
`domdata/domdata_pkg/serializers.py` | Serializers | to_jsonable, rows_from, stable_json, emit
`domdata/tests/test_check_no_trading.py` | Tests for check_no_trading | test_should_scan_python_file, test_should_scan_rejects_pycache, test_should_scan_rejects_git, test_should_scan_rejects_build, test_should_scan_allowlisted_filename_shallow
`domdata/tests/test_config.py` | Tests for config | test_password_masked, test_missing_mask
`domdata/tests/test_safety.py` | Tests for safety | test_blocked_commands_include_trading_words, test_blocked_command_exits_nonzero
`domdata/tests/test_serializers.py` | Tests for serializers | test_namedtuple_to_jsonable, test_rows_from_scalar
`dominion/__init__.py` |   Init   | -
`dominion/dataset/__init__.py` |   Init   | -
`dominion/dataset/contracts.py` | Contracts | ValidationResult, DataContract, PointInTimeContract, ShapeContract, NullContract
`dominion/dataset/m5_requirements.py` | M5_REQUIREMENTS interface | M5Status, check_m5_parquet, check_m5_duckdb, require_m5_or_block
`dominion/dataset/registries.py` | Registries | SourceStatus, FeatureType, ColumnSpec, HydraRegistry, columns
`dominion/dataset/registries_old.py` | Registries Old | SourceStatus, FeatureType, ColumnSpec, HydraRegistry, columns
`dominion/dataset/semantic_names.py` | Semantic Names | SemanticName, generate_ohlcv_names, generate_rolling_names, generate_technical_names, generate_time_names
`dominion/features/__init__.py` |   Init   | -
`dominion/features/cpp_bridge.py` | Cpp Bridge | ensure_cpp_available, rolling_mean, rolling_std, rolling_zscore, ema
`dominion/joins/__init__.py` |   Init   | -
`dominion/joins/point_in_time.py` | Point In Time | asof_join_backward, multi_asof_join, validate_no_future_leakage
`dominion/matrix/__init__.py` |   Init   | -
`dominion/matrix/builder.py` | Builds builder | MatrixBuilder, build_hydra_matrix, build
`dominion/quality/__init__.py` |   Init   | -
`dominion/quality/gates.py` | Gates | GateResult, QualityGates, run_all_gates, print_gate_report, check_shape
`dominion_agent/__init__.py` |   Init   | -
`dominion_agent/adversary.py` | Adversary | run_adversarial_review
`dominion_agent/api.py` | Api | sync_ragd
`dominion_agent/architecture.py` | Architecture | refresh_architecture, show_architecture
`dominion_agent/claims.py` | Claims | claim_task, release_task, list_claims
`dominion_agent/cli.py` | CLI interface | build_agent_subparser, cmd_agent
`dominion_agent/complexity.py` | Complexity | complexity_report, all_packages_report
`dominion_agent/conflicts.py` | Conflicts | check_conflicts
`dominion_agent/dashboard.py` | Dashboard | build_dashboard, build_next, format_dashboard_human
`dominion_agent/impact.py` | Impact | _Rule, analyze_impact
`dominion_agent/locks.py` | Locks | acquire_lock, release_lock, list_locks, stale_locks, reap_expired_locks
`dominion_agent/migrations.py` | Migrations | apply_migrations
`dominion_agent/prompt_compiler.py` | Prompt Compiler | compile_prompt
`dominion_agent/reports.py` | Reports | session_to_dict, task_to_dict, claim_to_dict, lock_to_dict, conflict_report_to_dict
`dominion_agent/safety.py` | Safety | is_secret_path, redact_path, is_forbidden_trading_task, validate_task_payload
`dominion_agent/sessions.py` | Sessions | start_session, heartbeat, end_session, get_session, list_sessions
`dominion_agent/store.py` | Store | AgentStore, conn, db_path, close
`dominion_agent/tasks.py` | Tasks | create_task, get_task, list_tasks, update_task_status, update_task_evidence
`dominion_agent/tests/test_adversary.py` | Tests for adversary | test_missing_validation_found, test_missing_evidence_detected, test_forbidden_token_in_scope_file, test_task_not_found_gives_blocked, test_clean_task_accepts
`dominion_agent/tests/test_cli.py` | Tests for cli | _Args, test_cli_init_returns_session, test_cli_sessions_command, test_cli_task_create_and_list, test_cli_task_show_not_found
`dominion_agent/tests/test_complexity.py` | Tests for complexity | test_scan_empty_dir, test_scan_counts_files, test_scan_counts_todos, test_scan_counts_temp_adapters, test_scan_counts_broad_excepts
`dominion_agent/tests/test_conflicts.py` | Tests for conflicts | test_active_write_lock_detected, test_active_read_lock_no_conflict, test_secret_path_conflict, test_shared_interface_file, test_no_conflicts_clean
`dominion_agent/tests/test_e2e_smoke.py` | Tests for e2e_smoke | store, test_full_workflow, test_secret_paths_rejected, test_secret_path_detection, test_dashboard_returns_valid_schema
`dominion_agent/tests/test_impact.py` | Tests for impact | test_ragd_files_require_cmake, test_domdata_files_require_no_trading_check, test_dominion_loader_requires_pytest, test_dominion_ai_files, test_empty_files_low_risk
`dominion_agent/tests/test_locks.py` | Tests for locks | test_acquire_write_lock, test_release_lock, test_acquire_read_lock, test_write_write_conflict, test_read_read_no_conflict
`dominion_agent/tests/test_prompt_compiler.py` | Tests for prompt_compiler | test_prompt_contains_task_id, test_prompt_contains_mission, test_prompt_contains_safety_rules, test_prompt_contains_done_criteria, test_prompt_contains_validation_commands
`dominion_agent/tests/test_sessions.py` | Tests for sessions | test_start_session_returns_session, test_start_session_invalid_role, test_start_session_invalid_name, test_start_session_with_metadata, test_start_session_persists
`dominion_agent/tests/test_store.py` | Tests for store | test_store_creates_db_file, test_store_context_manager, test_store_conn_is_row_factory, test_migrations_idempotent, test_all_tables_created
`dominion_agent/tests/test_tasks.py` | Tests for tasks | test_create_task_basic, test_create_task_with_scope, test_create_task_invalid_kind, test_create_task_forbidden_title, test_create_task_empty_title
`dominion_agent/tui.py` | TUI interface | render_agent_panels
`dominion_agent/types.py` | Types | Session, Task, ClaimResult, FileLock, LockResult
`dominion_agent/validators.py` | Validators | validate_session_status, validate_role, validate_task_status, validate_task_kind, validate_lock_mode
`dominion_ai/__init__.py` |   Init   | -
`dominion_ai/api.py` | Api | ask
`dominion_ai/bench.py` | Bench | run_suite
`dominion_ai/budget.py` | Budget | estimate_tokens, chunk_value, compress_chunk, optimize
`dominion_ai/cli.py` | CLI interface | print_json, cmd_search, cmd_ask, cmd_explain, cmd_trace
`dominion_ai/confidence.py` | Confidence | score_confidence
`dominion_ai/context.py` | Context | assemble
`dominion_ai/eval.py` | Eval | run_eval
`dominion_ai/ledger.py` | Ledger | LedgerEntry, list_entries, show_entry, search_entries, entries_to_dict
`dominion_ai/obs.py` | Obs | new_trace_id, trace_path, emit_span, span
`dominion_ai/planner.py` | Planner | plan
`dominion_ai/ragd_client.py` | RAGD_CLIENT interface | RagdError, RagdClient, parse_chunk, parse_chunks, chunk_by_id
`dominion_ai/rerank.py` | Rerank | rerank
`dominion_ai/retrieval.py` | Retrieval | retrieve
`dominion_ai/safety.py` | Safety | is_secret_path, redact_path, redact_secret_mentions
`dominion_ai/tests/eval_fixtures/tiny/meta.json` | Configuration for tiny | -
`dominion_ai/tests/test_budget.py` | Tests for budget | test_budget_preserves_high_value_chunk
`dominion_ai/tests/test_cli.py` | Tests for cli | test_cli_parses_new_subcommands
`dominion_ai/tests/test_confidence.py` | Tests for confidence | test_confidence_refuses_empty, test_confidence_ok_with_matching_chunk
`dominion_ai/tests/test_context.py` | Tests for context | test_assemble_preserves_citations_and_budget
`dominion_ai/tests/test_contract_scored_chunk.py` | Tests for contract_scored_chunk | test_scored_chunk_schema_stable
`dominion_ai/tests/test_contract_trace_join.py` | Tests for contract_trace_join | test_trace_join_schema_uses_trace_id
`dominion_ai/tests/test_eval.py` | Tests for eval | test_eval_bundle_roundtrip
`dominion_ai/tests/test_ledger.py` | Tests for ledger | FakeClient, test_ledger_filters_kind_and_search, decisions
`dominion_ai/tests/test_planner.py` | Tests for planner | test_golden_handoff_plan, test_planner_filters_python
`dominion_ai/tests/test_ragd_client.py` | Tests for ragd_client | test_parse_chunk_filters_secrets, test_parse_chunk_fallback_hashes_missing_content_hash, test_parse_chunk_redacts_secret_mentions_in_content, test_parse_chunk_uses_real_content_hash, test_parse_chunk_uses_real_document_id
`dominion_ai/tests/test_rerank.py` | Tests for rerank | test_heuristic_rerank_promotes_term_hits
`dominion_ai/tests/test_retrieval.py` | Tests for retrieval | FakeClient, test_retrieve_rrf_merges_sources, query
`dominion_ai/tests/test_trace.py` | Tests for trace | test_trace_renders_spans
`dominion_ai/trace.py` | Trace | load_trace, render_trace, latest_traces
`dominion_ai/types.py` | Types | RetrievalPlan, Citation, ScoredChunk, ContextSection, AssembledContext
`dominion_loader/__init__.py` |   Init   | -
`dominion_loader/api.py` | Api | iter_files, get_manifest_entry, list_changed_since, semantic_diff, hw_probe
`dominion_loader/bench.py` | Bench | BenchResult, register_suite, run_suite, list_suites, p50
`dominion_loader/cache.py` | Cache | CacheCorruption, CacheHit, Cache, get, put
`dominion_loader/chunking_hooks.py` | Chunking Hooks | Chunk, register_chunker, chunker_for, list_registered, clear_registry
`dominion_loader/classify.py` | Classify | classify, is_likely_binary
`dominion_loader/cli.py` | CLI interface | cmd_scan_native, cmd_scan, cmd_cache, cmd_manifest, cmd_loader_bench
`dominion_loader/discover.py` | Discover | DiscoveredFile, DiscoveryError, discover
`dominion_loader/graph.py` | Graph | KGNode, KGEdge, KnowledgeGraph, ingest_from_ragd, add_node
`dominion_loader/hashing.py` | Hashing | HashResult, PriorEntry, document_id_for, chunk_id_for, hash_file
`dominion_loader/hw_probe.py` | Hw Probe | HardwareProfile, hw_probe, hw_probe_json
`dominion_loader/ignore.py` | Ignore | Ignore, export_policy, policy_hash, match, match_size
`dominion_loader/ledger.py` | Ledger | LedgerEntry, Ledger, append, query_kind, stats
`dominion_loader/manifest.py` | Manifest | ManifestEntry, Manifest, _Transaction, get, upsert
`dominion_loader/obs.py` | Obs | new_trace_id, Tracer, _NullTracer, get_tracer, set_tracer
`dominion_loader/profiler.py` | Profiler | ProfileSpan, Profiler, span, report, close
`dominion_loader/ragd_bridge.py` | Ragd Bridge | IngestResult, DeleteResult, RagdBridge, ok, elapsed_s
`dominion_loader/scan.py` | Scan | LoadedFile, ScanStats, scan, iter_loaded_files
`dominion_loader/semantic_diff.py` | Semantic Diff | semantic_diff
`dominion_loader/tests/test_bench.py` | Tests for bench | test_bench_result_percentiles, test_bench_result_to_dict, test_bench_result_empty_runs, test_register_and_list_suite, test_run_suite_emits_json
`dominion_loader/tests/test_cache.py` | Tests for cache | null_tracer, cache, test_put_and_get, test_get_missing_returns_none, test_namespace_isolation
`dominion_loader/tests/test_chunking_hooks.py` | Tests for chunking_hooks | clean_registry, test_register_and_retrieve, test_chunker_for_unknown_returns_none, test_list_registered_reflects_registry, test_hooks_disabled_returns_none
`dominion_loader/tests/test_classify.py` | Tests for classify | test_classify_extension, test_is_likely_binary_text, test_is_likely_binary_null_bytes, test_is_likely_binary_missing
`dominion_loader/tests/test_contract_loaded_file.py` | Tests for contract_loaded_file | null_tracer, small_repo, test_loaded_file_has_required_fields, test_loaded_file_is_frozen, test_document_id_stable_across_scans
`dominion_loader/tests/test_contract_ragd_ingestion.py` | Tests for contract_ragd_ingestion | test_ingest_result_has_required_fields, test_ingest_result_ok_property, test_ingest_result_elapsed_s, test_ingest_result_to_dict_serializable, test_ingest_result_to_dict_schema
`dominion_loader/tests/test_discover.py` | Tests for discover | synthetic_repo, test_discovers_source_files, test_secrets_never_discovered, test_git_never_discovered, test_pycache_never_discovered
`dominion_loader/tests/test_doctor.py` | Tests for doctor | run_dominion, test_doctor_runs_without_crash, test_doctor_json_output_valid, test_doctor_checks_foundation_components, test_doctor_ignore_rules_always_passes
`dominion_loader/tests/test_graph.py` | Tests for graph | kg, test_add_and_get_node, test_get_missing_node, test_add_node_idempotent, test_list_nodes_filtered_by_kind
`dominion_loader/tests/test_hashing.py` | Tests for hashing | setup_function, test_document_id_stable, test_document_id_different_paths, test_document_id_length, test_chunk_id_stable
`dominion_loader/tests/test_hw_probe.py` | Tests for hw_probe | test_hw_probe_returns_profile, test_hw_probe_cpu_count_positive, test_hw_probe_ram_bytes_positive, test_hw_probe_platform_known, test_hw_probe_gpu_fields_consistent
`dominion_loader/tests/test_ignore.py` | Tests for ignore | ignore, test_must_ignore, test_must_not_ignore, test_secrets_rule_immutable, test_secrets_not_overridable
`dominion_loader/tests/test_ledger.py` | Tests for ledger | ledger, test_append_returns_id, test_append_idempotent_on_same_content, test_append_different_payload_different_entry, test_invalid_kind_raises
`dominion_loader/tests/test_manifest.py` | Tests for manifest | make_entry, manifest, test_schema_creates_tables, test_schema_version_recorded, test_migration_idempotent
`dominion_loader/tests/test_ragd_bridge.py` | Tests for ragd_bridge | null_tracer, test_ingest_paths_empty_list, test_bridge_disabled_returns_no_op, test_health_mock_ok, test_health_mock_down
`dominion_loader/tests/test_scan.py` | Tests for scan | null_tracer, FakeBridge, small_repo, test_scan_dry_run_returns_stats, test_scan_populates_manifest
`dominion_loader/tests/test_semantic_diff.py` | Tests for semantic_diff | test_identical_is_format_only, test_trailing_whitespace_is_whitespace_only, test_extra_blank_lines_is_format_only, test_add_python_comment_is_comment_only, test_add_cpp_line_comment_is_comment_only
`dominion_loader/tests/test_truth_doctor.py` | Tests for truth_doctor | test_deep_doctor_reports_missing_query_metadata, test_deep_doctor_detects_deleted_chunk_leak, test_deep_doctor_reports_cache_corruption, test_deep_doctor_reports_temp_adapters, test_deep_doctor_offline_skips_ragd
`dominion_loader/truth_doctor.py` | Truth Doctor | CmdResult, DoctorDeps, run_deep_doctor
`exec_features/__init__.py` |   Init   | -
`exec_features/cli.py` | CLI interface | load_lob_data, cmd_compute, cmd_top, cmd_decay, main
`exec_features/config.py` | Configuration for exec_features | -
`exec_features/depth_features.py` | Depth Features | compute_depth_features
`exec_features/flow_features.py` | Flow Features | compute_flow_features
`exec_features/ic_tracker.py` | Ic Tracker | compute_ic, compute_forward_returns, update_ic_for_features, check_feature_decay
`exec_features/quote_features.py` | Quote Features | compute_quote_features
`exec_features/schema.py` | Schema | init_exec_features_schema
`exec_features/spread_features.py` | Spread Features | compute_spread_features
`exec_features/store.py` | Store | compute_all_features, store_features
`exec_features/tests/__init__.py` |   Init   | -
`exec_features/tests/test_exec_features.py` | Tests for exec_features | test_spread_features_count, test_depth_features_count, test_flow_features_count, test_compute_all_features, test_ic_bounded
`exec_features/trade_features.py` | Trade Features | compute_trade_features
`exec_sim/__init__.py` |   Init   | -
`exec_sim/cli.py` | CLI interface | load_market_data, cmd_run, cmd_report, main
`exec_sim/config.py` | Configuration for exec_sim | -
`exec_sim/impact/__init__.py` |   Init   | -
`exec_sim/impact/almgren_chriss.py` | Almgren Chriss | permanent_impact, temporary_impact, total_cost, optimal_trajectory
`exec_sim/matching.py` | Matching | walk_book, compute_slippage_bps
`exec_sim/schema.py` | Schema | init_exec_sim_schema
`exec_sim/strategies/__init__.py` |   Init   | -
`exec_sim/strategies/base.py` | Base | ExecutionStrategy, generate_slices, remaining_quantity
`exec_sim/strategies/pov.py` | Pov | POVStrategy, generate_slices
`exec_sim/strategies/twap.py` | Twap | TWAPStrategy, generate_slices
`exec_sim/strategies/vwap.py` | Vwap | VWAPStrategy, generate_slices
`exec_sim/tests/__init__.py` |   Init   | -
`exec_sim/tests/test_sim.py` | Tests for sim | test_vwap_slices_sum_to_target, test_twap_uniform_slices, test_almgren_chriss_impact_nonnegative, test_walk_book_reduces_depth, test_fill_rate_bounded
`generate_repo_map.py` | Generate Repo Map | is_source_or_config, extract_python_exports, guess_purpose, build_dir_tree, main
`hydra/__init__.py` |   Init   | -
`hydra/backtest/__init__.py` |   Init   | -
`hydra/backtest/cpp/CMakeLists.txt` | Cmakelists | -
`hydra/backtest/cpp/backtester.cpp` | Tests for backtester | -
`hydra/backtest/cpp/backtester.hpp` | Tests for backtester | -
`hydra/backtest/cpp/duckdb_loader.cpp` | Duckdb Loader | -
`hydra/backtest/cpp/main.cpp` | Main | -
`hydra/backtest/cpp/onnx_runner.cpp` | Onnx Runner | -
`hydra/backtest/engine_py.py` | Engine Py | Trade, kelly_size, run_backtest, backtest_metrics
`hydra/backtest/metrics.py` | Metrics | sharpe_ratio, sortino_ratio, max_drawdown, calmar_ratio, profit_factor
`hydra/backtest_3year.py` | Tests for back3year | CostScenario, ModeConfig, load_data, make_labels, build_features
`hydra/backtest_9year_final.py` | Tests for back9year_final | CostScenario, ModeConfig, Trade, make_labels, build_features
`hydra/backtest_walkforward.py` | Tests for backwalkforward | CostScenario, ModeConfig, Trade, compute_atr, make_labels_pct
`hydra/backtest_walkforward_v2.py` | Tests for backwalkforward_v2 | CostScenario, ModeConfig, Trade, compute_atr, make_labels_pct
`hydra/brains/__init__.py` |   Init   | -
`hydra/brains/day.py` | Day | DayBrain, fit, set_bma_weights, predict, predict_proba
`hydra/brains/scalp.py` | Scalp | ScalpBrain, fit, set_bma_weights, predict, predict_proba
`hydra/brains/swing.py` | Swing | SwingBrain, fit, set_bma_weights, predict, predict_proba
`hydra/cli.py` | CLI interface | cmd_train, cmd_predict, cmd_report, cmd_backtest, cmd_export
`hydra/config.py` | Configuration for hydra | TargetConfig, CVConfig, FeatureConfig, EnsembleConfig, BacktestConfig
`hydra/data/__init__.py` |   Init   | -
`hydra/data/cv.py` | Cv | walk_forward_splits
`hydra/data/features.py` | Features | mi_select, ic_filter, select_features, esn_features, gat_features
`hydra/data/features_stationary.py` | Features Stationary | compute_log_returns, compute_rolling_zscore, compute_atr_pct, compute_drawdown_pct, compute_realized_vol
`hydra/data/loader.py` | Loader | get_connection, load_bars, load_features, load_macro, load_cot
`hydra/data/normalize.py` | Normalize | RobustScaler, fit, transform, fit_transform, save
`hydra/data/targets.py` | Targets | wilder_atr, triple_barrier_long, triple_barrier_short, make_targets
`hydra/data_sources/__init__.py` |   Init   | -
`hydra/data_sources/__main__.py` |   Main   | -
`hydra/data_sources/base.py` | Base | CoverageReport, FetchResult, NormalizeResult, QualityReport, DataProvider
`hydra/data_sources/duckdb_provider.py` | Duckdb Provider | DuckDBProvider, probe, fetch, normalize, validate
`hydra/data_sources/dukascopy_provider.py` | Dukascopy Provider | DukascopyProvider, probe, fetch, normalize, validate
`hydra/data_sources/mt5_provider.py` | Mt5 Provider | MT5Provider, probe, fetch, normalize, validate
`hydra/data_sources/registry.py` | Registry | compute_date_range, run_audit, fetch_missing, main
`hydra/data_sources/yahoo_provider.py` | Yahoo Provider | YahooProvider, probe, fetch, normalize, validate
`hydra/download_mt5_history.py` | Download Mt5 History | fetch_timeframe, convert_to_parquet, main
`hydra/export/__init__.py` |   Init   | -
`hydra/export/fuse.py` | Fuse | fuse_ensemble_onnx
`hydra/export/quantize.py` | Quantize | quantize_model
`hydra/export/to_onnx.py` | To Onnx | export_sklearn_to_onnx, export_lgbm_to_onnx, export_xgb_to_onnx, export_catboost_to_onnx, export_pytorch_to_onnx
`hydra/labels/__init__.py` |   Init   | -
`hydra/labels/triple_barrier.py` | Triple Barrier | LabelMetadata, detect_session, session_spread, TripleBarrierLabeler, compute_label_statistics
`hydra/loop/__init__.py` |   Init   | -
`hydra/loop/improver.py` | Improver | HydraImprover, run
`hydra/loop/stopping.py` | Stopping | hit_targets, edge_decayed, drawdown_kill
`hydra/loop/strategies.py` | Strategies | Strategy, threshold_tuning, refit_bma, add_boosting_rounds, rerun_feature_selection
`hydra/models/__init__.py` |   Init   | -
`hydra/models/base.py` | Base | ModelWrapper, fit, predict_proba, warm_update, feature_importance
`hydra/models/forests.py` | Forests | RFModel, ETModel, HGBModel, fit, predict_proba
`hydra/models/gbm.py` | Gbm | LGBMModel, XGBModel, CatBoostModel, fit, predict_proba
`hydra/models/linear.py` | Linear | LRModel, GNBModel, LDAModel, fit, predict_proba
`hydra/models/moe.py` | Moe | MixtureOfExperts, fit, predict_proba
`hydra/models/neural.py` | Neural | MLPModel, LSTMModel, TCNModel, fit, predict_proba
`hydra/models/stacking.py` | Stacking | StackingEnsemble, fit, predict_proba, predict_base
`hydra/oos_forensic_replay.py` | Oos Forensic Replay | CostScenario, ModeConfig, Trade, make_labels, build_features
`hydra/progress.py` | Progress | load_state, find_latest_log, tail_file, find_latest_events, render_rich
`hydra/ragd/__init__.py` |   Init   | -
`hydra/ragd/memory.py` | Memory | remember, recall, emit_event
`hydra/run_100.py` | Run 100 | -
`hydra/runtime_state.py` | Runtime State | read_state, write_state, update_state, set_phase, set_idle
`hydra/signals/__init__.py` |   Init   | -
`hydra/signals/adversary.py` | Adversary | HydraAdversary, fit, should_veto, veto_mask
`hydra/signals/core.py` | Core | fuse_brains, agreement_multiplier, conflict_resolution, five_gate_check
`hydra/signals/ensemble.py` | Ensemble | bma_weights, bma_predict, threshold_signal
`hydra/signals/filters.py` | Filters | permutation_entropy_gate, cot_filter, toxicity_gate, spread_gate
`hydra/storage/__init__.py` |   Init   | -
`hydra/storage/duckdb_writer.py` | Duckdb Writer | HydraDB, write_iteration, write_trades, write_model, write_final
`hydra/telemetry/__init__.py` |   Init   | -
`hydra/telemetry/recorder.py` | Recorder | TelemetryRecorder, record_iteration, record_system_snapshot
`hydra/telemetry/schema.py` | Schema | empty_packet
`hydra/tests/__init__.py` |   Init   | -
`hydra/tests/test_backtester.py` | Tests for backtester | test_kelly_size_basic, test_kelly_size_low_confidence, test_all_longs_profitable_in_uptrend, test_no_signal_no_trades, test_stop_fill_at_stop_price
`hydra/tests/test_cpp_parity.py` | Tests for cpp_parity | test_cpp_python_trade_ledger_parity, test_cpp_throughput
`hydra/tests/test_ensemble.py` | Tests for ensemble | test_bma_weights_sum_to_one, test_bma_weights_higher_sharpe_higher_weight, test_bma_predict_weighted_average, test_bma_predict_single_model, test_threshold_signal_long
`hydra/tests/test_metrics.py` | Tests for metrics | test_sharpe_constant_returns, test_sharpe_zero_std, test_sharpe_negative_constant, test_sharpe_empty, test_win_rate_basic
`hydra/tests/test_onnx.py` | Tests for onnx | test_fuse_onnx_roundtrip, test_quantize_preserves_accuracy
`hydra/training/__init__.py` |   Init   | -
`hydra/training/backtest.py` | Tests for backtest | BacktestEvaluator, evaluate, evaluate_walk_forward, aggregate_walk_forward_results
`hydra/training/guardrails.py` | Guardrails | GateVerdictResult, TrainingGuardrails, check_training_allowed, exclude_non_features, check_gate_verdict
`hydra/training/hydra_runner.py` | Hydra Runner | HydraRunner, load_and_validate, generate_labels, prepare_features, train
`hydra/training/metrics.py` | Metrics | compute_training_metrics, compute_cost_adjusted_metrics, compute_all_metrics, print_metrics_report
`hydra/training/splits.py` | Splits | SplitMetadata, compute_embargo_purge, ChronologicalSplit, validate_split_safety, split
`hydra/utils/__init__.py` |   Init   | -
`hydra/utils/atomic.py` | Atomic | atomic_write_json, safe_read_json
`hydra/utils/eta.py` | Eta | ETAEstimator, update, eta_seconds, eta_human, throughput
`hydra/utils/system_monitor.py` | System Monitor | get_system_stats
`lob/__init__.py` |   Init   | -
`lob/cli.py` | CLI interface | cmd_compute, cmd_metrics, cmd_vpin, main
`lob/config.py` | Configuration for lob | -
`lob/ingestion.py` | Ingestion | load_gold_ticks, generate_synthetic_quotes, compute_roll_spread, prepare_lob_data
`lob/metrics.py` | Metrics | compute_ofi, compute_vpin, compute_roll_spread, compute_corwin_schultz_spread, compute_all_metrics
`lob/schema.py` | Schema | init_lob_schema
`lob/state_machine.py` | State Machine | LimitOrderBook, update_bid, update_ask, get_best_bid, get_best_ask
`lob/tests/__init__.py` |   Init   | -
`lob/tests/test_lob.py` | Tests for lob | test_lob_state_machine, test_lob_depth_weighted_mid, test_lob_depth_imbalance, test_ofi_computation, test_vpin_bounded
`look.py` | Look | get_process_info, parse_runtime, get_real_progress, get_log_tail, format_eta
`pytest.ini` | Tests for pytest | -
`ragd/CMakeLists.txt` | Cmakelists | -
`ragd/__init__.py` |   Init   | -
`ragd/build/CMakeFiles/3.31.6/CompilerIdCXX/CMakeCXXCompilerId.cpp` | Cmakecxxcompilerid | -
`ragd/build/CMakeFiles/CMakeConfigureLog.yaml` | Configuration for cmakefiles | -
`ragd/build/Makefile` | Makefile | -
`ragd/build/_deps/cpp_httplib-build/Makefile` | Makefile | -
`ragd/build/_deps/cpp_httplib-src/CMakeLists.txt` | Cmakelists | -
`ragd/build/_deps/cpp_httplib-src/Dockerfile` | Dockerfile | -
`ragd/build/_deps/cpp_httplib-src/benchmark/Makefile` | Makefile | -
`ragd/build/_deps/cpp_httplib-src/benchmark/cpp-httplib/main.cpp` | Main | -
`ragd/build/_deps/cpp_httplib-src/benchmark/cpp-httplib-base/httplib.h` | Httplib | -
`ragd/build/_deps/cpp_httplib-src/benchmark/cpp-httplib-base/main.cpp` | Main | -
`ragd/build/_deps/cpp_httplib-src/benchmark/crow/crow_all.h` | Crow All | -
`ragd/build/_deps/cpp_httplib-src/benchmark/crow/main.cpp` | Main | -
`ragd/build/_deps/cpp_httplib-src/docker/main.cc` | Main | -
`ragd/build/_deps/cpp_httplib-src/docker-compose.yml` | Configuration for cpp_httplib-src | -
`ragd/build/_deps/cpp_httplib-src/example/Makefile` | Makefile | -
`ragd/build/_deps/cpp_httplib-src/example/benchmark.cc` | Benchmark | -
`ragd/build/_deps/cpp_httplib-src/example/client.cc` | CLIENT interface | -
`ragd/build/_deps/cpp_httplib-src/example/hello.cc` | Hello | -
`ragd/build/_deps/cpp_httplib-src/example/one_time_request.cc` | One Time Request | -
`ragd/build/_deps/cpp_httplib-src/example/redirect.cc` | Redirect | -
`ragd/build/_deps/cpp_httplib-src/example/server.cc` | Server | -
`ragd/build/_deps/cpp_httplib-src/example/server_and_client.cc` | SERVER_AND_CLIENT interface | -
`ragd/build/_deps/cpp_httplib-src/example/simplecli.cc` | SIMPLECLI interface | -
`ragd/build/_deps/cpp_httplib-src/example/simplesvr.cc` | Simplesvr | -
`ragd/build/_deps/cpp_httplib-src/example/ssecli.cc` | SSECLI interface | -
`ragd/build/_deps/cpp_httplib-src/example/ssesvr.cc` | Ssesvr | -
`ragd/build/_deps/cpp_httplib-src/example/upload.cc` | Upload | -
`ragd/build/_deps/cpp_httplib-src/httplib.h` | Httplib | -
`ragd/build/_deps/cpp_httplib-src/meson.build` | Meson | -
`ragd/build/_deps/cpp_httplib-src/split.py` | Split | -
`ragd/build/_deps/cpp_httplib-src/test/CMakeLists.txt` | Cmakelists | -
`ragd/build/_deps/cpp_httplib-src/test/Makefile` | Makefile | -
`ragd/build/_deps/cpp_httplib-src/test/fuzzing/CMakeLists.txt` | Cmakelists | -
`ragd/build/_deps/cpp_httplib-src/test/fuzzing/Makefile` | Makefile | -
`ragd/build/_deps/cpp_httplib-src/test/fuzzing/server_fuzzer.cc` | Server Fuzzer | -
`ragd/build/_deps/cpp_httplib-src/test/fuzzing/standalone_fuzz_target_runner.cpp` | Standalone Fuzz Target Runner | -
`ragd/build/_deps/cpp_httplib-src/test/gtest/gtest-all.cc` | Tests for gtest-all | -
`ragd/build/_deps/cpp_httplib-src/test/gtest/gtest.h` | Tests for gtest | -
`ragd/build/_deps/cpp_httplib-src/test/gtest/gtest_main.cc` | Tests for gmain | -
`ragd/build/_deps/cpp_httplib-src/test/include_httplib.cc` | Include Httplib | -
`ragd/build/_deps/cpp_httplib-src/test/meson.build` | Meson | -
`ragd/build/_deps/cpp_httplib-src/test/proxy/Dockerfile` | Dockerfile | -
`ragd/build/_deps/cpp_httplib-src/test/proxy/docker-compose.yml` | Configuration for proxy | -
`ragd/build/_deps/cpp_httplib-src/test/test.cc` | Tests for test | -
`ragd/build/_deps/cpp_httplib-src/test/test_proxy.cc` | Tests for proxy | -
`ragd/build/_deps/cpp_httplib-src/test/www/dir/meson.build` | Meson | -
`ragd/build/_deps/cpp_httplib-src/test/www/meson.build` | Meson | -
`ragd/build/_deps/cpp_httplib-src/test/www2/dir/meson.build` | Meson | -
`ragd/build/_deps/cpp_httplib-src/test/www3/dir/meson.build` | Meson | -
`ragd/build/_deps/cpp_httplib-subbuild/CMakeFiles/CMakeConfigureLog.yaml` | Configuration for cmakefiles | -
`ragd/build/_deps/cpp_httplib-subbuild/CMakeFiles/cpp_httplib-populate.dir/Labels.json` | Configuration for cpp_httplib-populate.dir | -
`ragd/build/_deps/cpp_httplib-subbuild/CMakeLists.txt` | Cmakelists | -
`ragd/build/_deps/cpp_httplib-subbuild/Makefile` | Makefile | -
`ragd/build/_deps/nlohmann_json-build/Makefile` | Makefile | -
`ragd/build/_deps/nlohmann_json-src/CMakeLists.txt` | Cmakelists | -
`ragd/build/_deps/nlohmann_json-src/include/nlohmann/adl_serializer.hpp` | Adl Serializer | -
`ragd/build/_deps/nlohmann_json-src/include/nlohmann/byte_container_with_subtype.hpp` | Byte Container With Subtype | -
`ragd/build/_deps/nlohmann_json-src/include/nlohmann/detail/abi_macros.hpp` | Abi Macros | -
`ragd/build/_deps/nlohmann_json-src/include/nlohmann/detail/conversions/from_json.hpp` | From Json | -
`ragd/build/_deps/nlohmann_json-src/include/nlohmann/detail/conversions/to_chars.hpp` | To Chars | -
`ragd/build/_deps/nlohmann_json-src/include/nlohmann/detail/conversions/to_json.hpp` | To Json | -
`ragd/build/_deps/nlohmann_json-src/include/nlohmann/detail/exceptions.hpp` | Exceptions | -
`ragd/build/_deps/nlohmann_json-src/include/nlohmann/detail/hash.hpp` | Hash | -
`ragd/build/_deps/nlohmann_json-src/include/nlohmann/detail/input/binary_reader.hpp` | Binary Reader | -
`ragd/build/_deps/nlohmann_json-src/include/nlohmann/detail/input/input_adapters.hpp` | Input Adapters | -
`ragd/build/_deps/nlohmann_json-src/include/nlohmann/detail/input/json_sax.hpp` | Json Sax | -
`ragd/build/_deps/nlohmann_json-src/include/nlohmann/detail/input/lexer.hpp` | Lexer | -
`ragd/build/_deps/nlohmann_json-src/include/nlohmann/detail/input/parser.hpp` | Parser | -
`ragd/build/_deps/nlohmann_json-src/include/nlohmann/detail/input/position_t.hpp` | Position T | -
`ragd/build/_deps/nlohmann_json-src/include/nlohmann/detail/iterators/internal_iterator.hpp` | Internal Iterator | -
`ragd/build/_deps/nlohmann_json-src/include/nlohmann/detail/iterators/iter_impl.hpp` | Iter Impl | -
`ragd/build/_deps/nlohmann_json-src/include/nlohmann/detail/iterators/iteration_proxy.hpp` | Iteration Proxy | -
`ragd/build/_deps/nlohmann_json-src/include/nlohmann/detail/iterators/iterator_traits.hpp` | Iterator Traits | -
`ragd/build/_deps/nlohmann_json-src/include/nlohmann/detail/iterators/json_reverse_iterator.hpp` | Json Reverse Iterator | -
`ragd/build/_deps/nlohmann_json-src/include/nlohmann/detail/iterators/primitive_iterator.hpp` | Primitive Iterator | -
`ragd/build/_deps/nlohmann_json-src/include/nlohmann/detail/json_custom_base_class.hpp` | Json Custom Base Class | -
`ragd/build/_deps/nlohmann_json-src/include/nlohmann/detail/json_pointer.hpp` | Json Pointer | -
`ragd/build/_deps/nlohmann_json-src/include/nlohmann/detail/json_ref.hpp` | Json Ref | -
`ragd/build/_deps/nlohmann_json-src/include/nlohmann/detail/macro_scope.hpp` | Macro Scope | -
`ragd/build/_deps/nlohmann_json-src/include/nlohmann/detail/macro_unscope.hpp` | Macro Unscope | -
`ragd/build/_deps/nlohmann_json-src/include/nlohmann/detail/meta/call_std/begin.hpp` | Begin | -
`ragd/build/_deps/nlohmann_json-src/include/nlohmann/detail/meta/call_std/end.hpp` | End | -
`ragd/build/_deps/nlohmann_json-src/include/nlohmann/detail/meta/cpp_future.hpp` | Cpp Future | -
`ragd/build/_deps/nlohmann_json-src/include/nlohmann/detail/meta/detected.hpp` | Detected | -
`ragd/build/_deps/nlohmann_json-src/include/nlohmann/detail/meta/identity_tag.hpp` | Identity Tag | -
`ragd/build/_deps/nlohmann_json-src/include/nlohmann/detail/meta/is_sax.hpp` | Is Sax | -
`ragd/build/_deps/nlohmann_json-src/include/nlohmann/detail/meta/std_fs.hpp` | Std Fs | -
`ragd/build/_deps/nlohmann_json-src/include/nlohmann/detail/meta/type_traits.hpp` | Type Traits | -
`ragd/build/_deps/nlohmann_json-src/include/nlohmann/detail/meta/void_t.hpp` | Void T | -
`ragd/build/_deps/nlohmann_json-src/include/nlohmann/detail/output/binary_writer.hpp` | Binary Writer | -
`ragd/build/_deps/nlohmann_json-src/include/nlohmann/detail/output/output_adapters.hpp` | Output Adapters | -
`ragd/build/_deps/nlohmann_json-src/include/nlohmann/detail/output/serializer.hpp` | Serializer | -
`ragd/build/_deps/nlohmann_json-src/include/nlohmann/detail/string_concat.hpp` | String Concat | -
`ragd/build/_deps/nlohmann_json-src/include/nlohmann/detail/string_escape.hpp` | String Escape | -
`ragd/build/_deps/nlohmann_json-src/include/nlohmann/detail/value_t.hpp` | Value T | -
`ragd/build/_deps/nlohmann_json-src/include/nlohmann/json.hpp` | Json | -
`ragd/build/_deps/nlohmann_json-src/include/nlohmann/json_fwd.hpp` | Json Fwd | -
`ragd/build/_deps/nlohmann_json-src/include/nlohmann/ordered_map.hpp` | Ordered Map | -
`ragd/build/_deps/nlohmann_json-src/include/nlohmann/thirdparty/hedley/hedley.hpp` | Hedley | -
`ragd/build/_deps/nlohmann_json-src/include/nlohmann/thirdparty/hedley/hedley_undef.hpp` | Hedley Undef | -
`ragd/build/_deps/nlohmann_json-src/single_include/nlohmann/json.hpp` | Json | -
`ragd/build/_deps/nlohmann_json-src/single_include/nlohmann/json_fwd.hpp` | Json Fwd | -
`ragd/build/_deps/nlohmann_json-subbuild/CMakeFiles/CMakeConfigureLog.yaml` | Configuration for cmakefiles | -
`ragd/build/_deps/nlohmann_json-subbuild/CMakeFiles/nlohmann_json-populate.dir/Labels.json` | Configuration for nlohmann_json-populate.dir | -
`ragd/build/_deps/nlohmann_json-subbuild/CMakeLists.txt` | Cmakelists | -
`ragd/build/_deps/nlohmann_json-subbuild/Makefile` | Makefile | -
`ragd/build/tests/Makefile` | Makefile | -
`ragd/examples/mcp_call_example.json` | Configuration for examples | -
`ragd/include/dominion_native/agent_conflicts.hpp` | Agent Conflicts | -
`ragd/include/dominion_native/agent_locks.hpp` | Agent Locks | -
`ragd/include/dominion_native/content_hash.hpp` | Content Hash | -
`ragd/include/dominion_native/doctor.hpp` | Doctor | -
`ragd/include/dominion_native/file_classifier.hpp` | File Classifier | -
`ragd/include/dominion_native/forbidden_tokens.hpp` | Forbidden Tokens | -
`ragd/include/dominion_native/ignore_policy.hpp` | Ignore Policy | -
`ragd/include/dominion_native/manifest_store.hpp` | Manifest Store | -
`ragd/include/dominion_native/path_normalizer.hpp` | Path Normalizer | -
`ragd/include/dominion_native/report.hpp` | Report | -
`ragd/include/dominion_native/scan_plan.hpp` | Scan Plan | -
`ragd/include/dominion_native/vault_doctor.hpp` | Vault Doctor | -
`ragd/include/dominion_native/version.hpp` | Version | -
`ragd/include/ragd/agent_memory.h` | Agent Memory | -
`ragd/include/ragd/bm25.h` | Bm25 | -
`ragd/include/ragd/config.h` | Configuration for ragd | -
`ragd/include/ragd/dead_zone.h` | Dead Zone | -
`ragd/include/ragd/http_api.h` | Http Api | -
`ragd/include/ragd/indexer.h` | Indexer | -
`ragd/include/ragd/intent_router.h` | Intent Router | -
`ragd/include/ragd/mcp_server.h` | Mcp Server | -
`ragd/include/ragd/rag_engine.h` | Rag Engine | -
`ragd/include/ragd/session_bus.h` | Session Bus | -
`ragd/include/ragd/sqlite_compat.h` | Sqlite Compat | -
`ragd/include/ragd/storage.h` | Storage | -
`ragd/include/ragd/temporal.h` | Temporal | -
`ragd/include/ragd/todo_engine.h` | Todo Engine | -
`ragd/include/ragd/types.h` | Types | -
`ragd/include/ragd/vector_store.h` | Vector Store | -
`ragd/include/ragd/watcher.h` | Watcher | -
`ragd/scripts/__init__.py` |   Init   | -
`ragd/scripts/config.default.json` | Configuration for scripts | -
`ragd/scripts/ragd_maintenance.py` | Ragd Maintenance | Report, build_report, cleanup_duplicates, cmd_report, cmd_cleanup_duplicates
`ragd/scripts/ragd_mcp_stdio.py` | Ragd Mcp Stdio | ragd_query, ragd_handoff_read, ragd_todo_list, ragd_remember, ragd_todo_add
`ragd/src/agent_memory.cpp` | Agent Memory | -
`ragd/src/bm25.cpp` | Bm25 | -
`ragd/src/config.cpp` | Configuration for src | -
`ragd/src/dead_zone.cpp` | Dead Zone | -
`ragd/src/http_api.cpp` | Http Api | -
`ragd/src/indexer.cpp` | Indexer | -
`ragd/src/intent_router.cpp` | Intent Router | -
`ragd/src/main.cpp` | Main | -
`ragd/src/mcp_server.cpp` | Mcp Server | -
`ragd/src/native/agent_conflicts.cpp` | Agent Conflicts | -
`ragd/src/native/agent_locks.cpp` | Agent Locks | -
`ragd/src/native/content_hash.cpp` | Content Hash | -
`ragd/src/native/doctor.cpp` | Doctor | -
`ragd/src/native/file_classifier.cpp` | File Classifier | -
`ragd/src/native/forbidden_tokens.cpp` | Forbidden Tokens | -
`ragd/src/native/ignore_policy.cpp` | Ignore Policy | -
`ragd/src/native/manifest_store.cpp` | Manifest Store | -
`ragd/src/native/path_normalizer.cpp` | Path Normalizer | -
`ragd/src/native/report.cpp` | Report | -
`ragd/src/native/scan_plan.cpp` | Scan Plan | -
`ragd/src/native/vault_doctor.cpp` | Vault Doctor | -
`ragd/src/rag_engine.cpp` | Rag Engine | -
`ragd/src/session_bus.cpp` | Session Bus | -
`ragd/src/storage.cpp` | Storage | -
`ragd/src/temporal.cpp` | Temporal | -
`ragd/src/todo_engine.cpp` | Todo Engine | -
`ragd/src/vector_store.cpp` | Vector Store | -
`ragd/src/watcher.cpp` | Watcher | -
`ragd/tests/CMakeLists.txt` | Cmakelists | -
`ragd/tests/native/test_agent_conflicts.cpp` | Tests for agent_conflicts | -
`ragd/tests/native/test_agent_locks.cpp` | Tests for agent_locks | -
`ragd/tests/native/test_content_hash.cpp` | Tests for content_hash | -
`ragd/tests/native/test_doctor.cpp` | Tests for doctor | -
`ragd/tests/native/test_file_classifier.cpp` | Tests for file_classifier | -
`ragd/tests/native/test_forbidden_tokens.cpp` | Tests for forbidden_tokens | -
`ragd/tests/native/test_ignore_policy.cpp` | Tests for ignore_policy | -
`ragd/tests/native/test_manifest_store.cpp` | Tests for manifest_store | -
`ragd/tests/native/test_path_normalizer.cpp` | Tests for path_normalizer | -
`ragd/tests/native/test_scan_plan.cpp` | Tests for scan_plan | -
`ragd/tests/native/test_vault_doctor.cpp` | Tests for vault_doctor | -
`ragd/tests/test_agent_memory.cpp` | Tests for agent_memory | -
`ragd/tests/test_bm25.cpp` | Tests for bm25 | -
`ragd/tests/test_dead_zone.cpp` | Tests for dead_zone | -
`ragd/tests/test_indexer.cpp` | Tests for indexer | -
`ragd/tests/test_intent_router.cpp` | Tests for intent_router | -
`ragd/tests/test_maintenance_report.py` | Tests for maintenance_report | test_report_empty_db, test_duplicate_detection_and_dry_run, test_apply_marks_deleted
`ragd/tests/test_mcp_server.cpp` | Tests for mcp_server | -
`ragd/tests/test_rag_engine.cpp` | Tests for rag_engine | -
`ragd/tests/test_session_bus.cpp` | Tests for session_bus | -
`ragd/tests/test_storage.cpp` | Tests for storage | -
`ragd/tests/test_temporal.cpp` | Tests for temporal | -
`ragd/tests/test_todo_engine.cpp` | Tests for todo_engine | -
`ragd/tests/test_vector_store.cpp` | Tests for vector_store | -
`ragd/tests/test_watcher.cpp` | Tests for watcher | -
`ragd/tools/dominion_native_cli.cpp` | DOMINION_NATIVE_CLI interface | -
`ragd/tools/native_doctor_main.cpp` | Native Doctor Main | -
`ragd/tools/native_manifest_main.cpp` | Native Manifest Main | -
`ragd/tools/native_scan_main.cpp` | Native Scan Main | -
`ragd/tools/native_vault_doctor_main.cpp` | Native Vault Doctor Main | -
`ragd_bus/__init__.py` |   Init   | -
`ragd_bus/client.py` | CLIENT interface | RAGDBusClient, RAGDBusSync, send, test_connectivity
`ragd_bus/publisher.py` | Publisher | BusPublisher, publish_pipeline_complete, publish_anomaly, publish_regime_change, publish_dag_updated
`ragd_bus/tests/__init__.py` |   Init   | -
`ragd_bus/tests/test_bus.py` | Tests for bus | test_bus_client_init, test_bus_connect_fail, test_sync_client
`ragd_bus/topics.py` | Topics | -
`ragd_chunker/__init__.py` |   Init   | -
`ragd_chunker/chunker.py` | Chunker | ASTChunk, content_hash, module_name, chunk_file, to_dict
`ragd_chunker/config.py` | Configuration for ragd_chunker | -
`ragd_chunker/languages/__init__.py` |   Init   | -
`ragd_chunker/languages/cpp.py` | Cpp | chunk_cpp
`ragd_chunker/languages/go.py` | Go | chunk_go
`ragd_chunker/languages/javascript.py` | Javascript | chunk_javascript
`ragd_chunker/languages/python.py` | Python | chunk_python
`ragd_chunker/languages/rust.py` | Rust | chunk_rust
`ragd_chunker/languages/typescript.py` | Typescript | chunk_typescript
`ragd_chunker/metadata.py` | Metadata | python_imports, python_calls, python_docstring
`ragd_chunker/service.py` | Service | Handler, main, do_GET, do_POST, log_message
`ragd_chunker/tests/fixtures/sample.cpp` | Sample | -
`ragd_chunker/tests/fixtures/sample.py` | Sample | Greeter, helper, greet
`ragd_chunker/tests/test_cpp_chunker.py` | Tests for cpp_chunker | test_cpp_chunker_extracts_class_and_function
`ragd_chunker/tests/test_metadata.py` | Tests for metadata | test_python_metadata_extracts_docstring_imports_calls
`ragd_chunker/tests/test_python_chunker.py` | Tests for python_chunker | test_python_chunker_symbols_and_boundaries
`ragd_embed/__init__.py` |   Init   | -
`ragd_embed/batcher.py` | Batcher | BatchStats, EmbedBatcher, embed_in_batches
`ragd_embed/cache.py` | Cache | EmbeddingCache, close, get, put, stats
`ragd_embed/cli.py` | CLI interface | cmd_run, cmd_stats, cmd_doctor, build_parser, main
`ragd_embed/config.py` | Configuration for ragd_embed | EmbedConfig, load_config
`ragd_embed/pipeline.py` | Pipeline | ChunkInput, EmbedRunStats, provider_from_config, chunk_text, load_chunks_from_ragd
`ragd_embed/providers/__init__.py` |   Init   | EmbedProvider, embed_batch, health
`ragd_embed/providers/ollama.py` | Ollama | OllamaProvider, embed_batch, health
`ragd_embed/providers/openai.py` | Openai | OpenAIProvider, embed_batch, health
`ragd_embed/providers/voyage.py` | Voyage | VoyageProvider, embed_batch, health
`ragd_embed/tests/test_batcher.py` | Tests for batcher | FlakyProvider, test_batches_split_and_retry, embed_batch, health
`ragd_embed/tests/test_cache.py` | Tests for cache | test_cache_hit_and_provider_miss
`ragd_embed/tests/test_config.py` | Tests for config | test_provider_resolved_from_env, test_missing_key_raises_clear_error, test_ollama_provider_config
`ragd_embed/tests/test_ollama.py` | Tests for ollama | test_ollama_provider_init, test_ollama_provider_custom_base_url, test_ollama_api_key_ignored, test_ollama_embed_batch_single_text, test_ollama_embed_batch_multiple_texts
`ragd_embed/tests/test_pipeline.py` | Tests for pipeline | FakeProvider, test_unchanged_chunks_produce_zero_api_calls, test_changed_chunks_call_provider_once, embed_batch, health
`ragd_graph/__init__.py` |   Init   | -
`ragd_graph/cli.py` | CLI interface | main
`ragd_graph/graph.py` | Graph | GraphStats, default_db, build_graph, stats, callers
`ragd_graph/tests/test_graph.py` | Tests for graph | test_build_graph_from_chunks
`ragd_hnsw/__init__.py` |   Init   | -
`ragd_hnsw/config.py` | Configuration for ragd_hnsw | default_index_path
`ragd_hnsw/index.py` | Index | HNSWIndex, build, add, mark_deleted, query
`ragd_hnsw/query.py` | Query | semantic_query
`ragd_hnsw/semantic_server.py` | Semantic Server | Handler, main, do_GET, do_POST, log_message
`ragd_hnsw/sync.py` | Sync | SyncStats, sync_index
`ragd_hnsw/tests/test_index.py` | Tests for index | test_build_query_save_load, test_atomic_write_preserves_old_index, fail_replace
`ragd_hnsw/tests/test_sync.py` | Tests for sync | test_sync_adds_active_and_skips_missing
`ragd_vault/__init__.py` |   Init   | -
`ragd_vault/builder.py` | Builds builder | build_vault
`ragd_vault/cli.py` | CLI interface | default_vault, main
`ragd_vault/doctor.py` | Doctor | VaultDoctorReport, inspect_vault
`ragd_vault/model.py` | Model | SymbolInfo, FileInfo, default_ragd_db, safe_name, load_index
`ragd_vault/repair.py` | Repair | RepairReport, repair_vault
`ragd_vault/sync.py` | Sync | sync_vault
`ragd_vault/tests/test_note_generation.py` | Tests for note_generation | test_file_and_symbol_notes_are_valid
`ragd_vault/tests/test_vault_doctor.py` | Tests for vault_doctor | test_vault_doctor_catches_broken_links_and_frontmatter
`reports/baseline_results_v1.json` | Configuration for reports | -
`reports/dataset_v1_manifest.json` | Configuration for reports | -
`reports/eval/tiny-20260513-214846.json` | Configuration for eval | -
`reports/eval/tiny-20260513-215612.json` | Configuration for eval | -
`reports/feature_stability_v1.json` | Configuration for reports | -
`reports/hydra_cpp_288b_summary.json` | Configuration for reports | -
`reports/label_baseline_sanity.json` | Configuration for reports | -
`reports/master_validation_report.json` | Configuration for reports | -
`reports/regime_analysis_v1.json` | Configuration for reports | -
`reports/temporal_split_v1.json` | Configuration for reports | -
`reports/training_validation_clean_report.json` | Configuration for reports | -
`reports/training_validation_report.json` | Configuration for reports | -
`research/sources.yaml` | Configuration for research | -
`research_os/__init__.py` |   Init   | -
`research_os/adapters/base.py` | Base | FetchConfig, FetchAdapter, fetch
`research_os/adapters/browser_adapter.py` | Browser Adapter | BrowserAdapter, fetch
`research_os/adapters/registry.py` | Registry | available_adapters, resolve_adapter, default_config
`research_os/adapters/requests_adapter.py` | Requests Adapter | RequestsAdapter, fetch
`research_os/chunker.py` | Chunker | chunk_markdown
`research_os/cleaner.py` | Cleaner | strip_noise, clean_text, html_to_text_fallback
`research_os/cli.py` | CLI interface | cmd_init, cmd_status, cmd_doctor, cmd_add_source, cmd_list_sources
`research_os/config.py` | Configuration for research_os | ResearchPaths, paths, ensure_dirs, write_default_sources, load_sources
`research_os/db.py` | Db | utc_now, connect, initialize, upsert_source, import_sources
`research_os/extractor.py` | Extractor | extract
`research_os/fetcher.py` | Fetches fetcher data | content_hash, safe_name, validate_url_for_source
`research_os/models.py` | Models | Source, FetchResult, ExtractedDocument, DocumentChunk
`research_os/normalize.py` | Normalize | NormalizationResult, normalize_raw_text
`research_os/ollama_client.py` | OLLAMA_CLIENT interface | summarize
`research_os/quality.py` | Quality | QualityReport, assess_quality
`research_os/ragd_client.py` | RAGD_CLIENT interface | health, mcp_call, try_index_path
`research_os/scheduler.py` | Scheduler | run
`research_os/tests/test_adapters.py` | Tests for adapters | test_browser_adapter_unavailable_returns_actionable_error
`research_os/tests/test_chunker.py` | Tests for chunker | test_chunk_markdown_by_heading
`research_os/tests/test_config.py` | Tests for config | test_default_sources_roundtrip
`research_os/tests/test_db.py` | Tests for db | test_db_sources_jobs_documents
`research_os/tests/test_extractor.py` | Tests for extractor | test_extract_markdown_metadata
`research_os/tests/test_fetcher.py` | Tests for fetcher | test_validate_url_blocks_outside_host, test_validate_url_allows_source_path
`research_os/tests/test_normalize_quality.py` | Tests for normalize_quality | test_normalize_html_deterministic, test_quality_score_basic_cases
`research_os/tests/test_scheduler.py` | Tests for scheduler | test_next_jobs_respects_limit
`reservoir/__init__.py` |   Init   | -
`reservoir/cli.py` | CLI interface | cmd_train, main
`reservoir/config.py` | Configuration for reservoir | -
`reservoir/esn.py` | Esn | EchoStateNetwork, MultiScaleESN, reset, step, run
`reservoir/readout.py` | Readout | RidgeReadout, train_test_split_esn, evaluate_readout, fit, predict
`reservoir/tests/__init__.py` |   Init   | -
`reservoir/tests/test_esn.py` | Tests for esn | test_esn_state_update, test_esn_spectral_radius, test_esn_washout, test_multiscale_esn
`runs/hydra_9year_final_20260519_230411/data_coverage.json` | Configuration for hydra_9year_final_20260519_230411 | -
`runs/hydra_9year_final_20260519_230435/data_coverage.json` | Configuration for hydra_9year_final_20260519_230435 | -
`runs/hydra_9year_final_20260519_230459/checkpoints/best_validation_config.json` | Configuration for checkpoints | -
`runs/hydra_9year_final_20260519_230459/checkpoints/iteration_10.json` | Configuration for checkpoints | -
`runs/hydra_9year_final_20260519_230459/checkpoints/state_latest.json` | Tests for state_latest | -
`runs/hydra_9year_final_20260519_230459/config_used.yaml` | Configuration for hydra_9year_final_20260519_230459 | -
`runs/hydra_9year_final_20260519_230459/data_coverage.json` | Configuration for hydra_9year_final_20260519_230459 | -
`runs/hydra_9year_final_20260519_230459/final_oos_result.json` | Configuration for hydra_9year_final_20260519_230459 | -
`runs/hydra_data_20260519_230339/data_coverage.json` | Configuration for hydra_data_20260519_230339 | -
`runs/hydra_equal_thirds_20260519_231440/split_manifest.json` | Configuration for hydra_equal_thirds_20260519_231440 | -
`runs/hydra_equal_thirds_20260519_232841/checkpoints/state_latest.json` | Tests for state_latest | -
`runs/hydra_equal_thirds_20260519_232841/final_test_result.json` | Tests for final_result | -
`runs/hydra_equal_thirds_20260519_232841/oos_diagnostics/oos_probability_summary.json` | Configuration for oos_diagnostics | -
`runs/hydra_equal_thirds_20260519_232841/split_manifest.json` | Configuration for hydra_equal_thirds_20260519_232841 | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_001.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_002.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_003.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_004.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_005.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_006.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_007.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_008.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_009.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_010.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_011.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_012.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_013.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_014.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_015.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_016.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_017.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_018.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_019.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_020.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_021.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_022.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_023.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_024.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_025.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_026.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_027.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_028.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_029.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_030.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_031.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_032.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_033.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_034.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_035.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_036.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_037.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_038.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_039.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_040.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_041.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_042.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_043.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_044.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_045.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_046.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_047.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_048.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_049.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_050.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_051.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_052.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_053.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_054.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_055.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_056.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_057.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_058.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_059.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_060.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_061.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_062.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_063.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_064.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_065.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_066.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_067.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_068.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_069.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_070.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_071.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_072.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_073.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_074.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_075.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_076.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_077.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_078.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_079.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_080.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_081.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_082.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_083.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_084.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_085.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_086.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_087.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_088.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_089.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_090.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_091.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_092.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_093.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_094.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_095.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_096.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_097.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_098.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_099.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260519_232841/telemetry/packets/iteration_100.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102128/split_manifest.json` | Configuration for hydra_equal_thirds_20260520_102128 | -
`runs/hydra_equal_thirds_20260520_102128/telemetry/packets/iteration_001.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102128/telemetry/packets/iteration_002.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102128/telemetry/packets/iteration_003.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102128/telemetry/packets/iteration_004.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102128/telemetry/packets/iteration_005.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102128/telemetry/packets/iteration_006.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102128/telemetry/packets/iteration_007.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/checkpoints/state_latest.json` | Tests for state_latest | -
`runs/hydra_equal_thirds_20260520_102446/final_test_result.json` | Tests for final_result | -
`runs/hydra_equal_thirds_20260520_102446/split_manifest.json` | Configuration for hydra_equal_thirds_20260520_102446 | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_001.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_002.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_003.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_004.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_005.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_006.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_007.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_008.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_009.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_010.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_011.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_012.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_013.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_014.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_015.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_016.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_017.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_018.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_019.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_020.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_021.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_022.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_023.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_024.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_025.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_026.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_027.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_028.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_029.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_030.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_031.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_032.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_033.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_034.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_035.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_036.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_037.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_038.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_039.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_040.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_041.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_042.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_043.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_044.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_045.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_046.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_047.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_048.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_049.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_050.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_051.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_052.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_053.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_054.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_055.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_056.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_057.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_058.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_059.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_060.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_061.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_062.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_063.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_064.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_065.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_066.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_067.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_068.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_069.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_070.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_071.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_072.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_073.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_074.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_075.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_076.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_077.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_078.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_079.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_080.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_081.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_082.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_083.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_084.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_085.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_086.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_087.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_088.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_089.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_090.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_091.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_092.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_093.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_094.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_095.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_096.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_097.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_098.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_099.json` | Configuration for packets | -
`runs/hydra_equal_thirds_20260520_102446/telemetry/packets/iteration_100.json` | Configuration for packets | -
`runs/hydra_runtime_state.json` | Configuration for runs | -
`runs/models/hydra_long.bin.meta.json` | Configuration for models | -
`runs/models/hydra_short.bin.meta.json` | Configuration for models | -
`runs/multi_training_research_20260520_190957_metadata.json` | Configuration for runs | -
`runs/walk_forward_summary_20260520_193621.json` | Configuration for runs | -
`runs/walk_forward_summary_20260520_201851.json` | Configuration for runs | -
`scripts/build_dataset_v1.py` | Builds dataset_v1 | pivot_features, join_to_gold_master, add_target_variables, drop_nan_rows, temporal_split
`scripts/build_full_dataset.py` | Builds full_dataset | load_gold_ohlcv, load_macro, load_cot, load_regime, asof_join_safe
`scripts/build_hydra_matrix.py` | Builds hydra_matrix | main
`scripts/build_master_dataset.py` | Builds master_dataset | strip_tz, to_naive, safe_merge, rsi, atr
`scripts/build_master_extended.py` | Builds master_extended | strip_tz, to_naive, safe_merge, rsi, atr
`scripts/codexrag.py` | Codexrag | query, main
`scripts/compile_source.py` | Compile Source | compile_dir, compile_scripts, main
`scripts/cost_aware_training_288b.py` | Training for cost_aware_training_288b | compute_trading_metrics, compute_classification_metrics
`scripts/dominion_cli.py` | DOMINION_CLI interface | run, http_json, ragd_health, tmux_sessions, research_counts
`scripts/dominion_health.py` | Dominion Health | run, which, latest_file, last_json, dir_size
`scripts/dominion_ui.py` | DOMINION_UI interface | run, render, main
`scripts/expand_features_3k.py` | Expand Features 3K | load_base, add_lag_features, add_rolling_sweeps, add_pairwise_ratios, add_percentile_ranks
`scripts/expand_features_3k_chunked.py` | Expand Features 3K Chunked | load_base_chunked, compute_lags, add_lag_features, compute_rolling, add_rolling_sweeps
`scripts/expand_features_3k_turbo.py` | Expand Features 3K Turbo | load_base, compute_lags_parallel, add_lag_features, compute_rolling_parallel, add_rolling_sweeps
`scripts/export_hydra_288b_binary.py` | Export Hydra 288B Binary | main
`scripts/feature_stability.py` | Feature Stability | compute_rolling_ic, detect_ic_decay, main
`scripts/fetch_alternative_data.py` | Fetches alternative_data data | fetch_gpr, fetch_epu, fetch_etf_flows, fetch_physical_gold, main
`scripts/fetch_cot.py` | Fetches cot data | main
`scripts/fetch_cross_asset.py` | Fetches cross_asset data | fetch_ticker, fetch_binance_daily, main
`scripts/fetch_crypto_binance.py` | Fetches crypto_binance data | fetch_binance_daily, main
`scripts/fetch_dukascopy_robust.py` | Fetches dukascopy_robust data | fetch_hour, fetch_day, main
`scripts/fetch_extended_cross_asset.py` | Fetches extended_cross_asset data | fetch_ticker, main
`scripts/fetch_extended_fred.py` | Fetches extended_fred data | fetch_fred_csv, main
`scripts/fetch_m5_history.py` | Fetches m5_history data | fetch_m5_batch, fetch_all_m5, validate_m5_data, main
`scripts/fetch_macro_data.py` | Fetches macro_data data | fetch_fred_csv, main
`scripts/fetch_mt5_chunks.py` | Fetches mt5_chunks data | fetch_chunk, main
`scripts/fetch_price_data.py` | Fetches price_data data | fetch_dukascopy_hour, ticks_to_m5, fetch_day, main
`scripts/fetch_price_fast.py` | Fetches price_fast data | fetch_day_data, main
`scripts/hydra_rich_runner.py` | Hydra Rich Runner | HydraState, build_command, render_dashboard, tail_progress, handle_event
`scripts/hydra_train_fixed_commission_288b.py` | Training for hydra_fixed_commission_288b | get_memory_mb, get_cpu_percent, elapsed, log_event, heartbeat
`scripts/label_baseline_sanity_audit.py` | Label Baseline Sanity Audit | -
`scripts/m5_feature_expansion.py` | M5 Feature Expansion | compute_returns, compute_volatility_range, compute_technical_expanded, compute_spread_volume, add_all_expanded_features
`scripts/metrics.py` | Metrics | compute_sharpe, compute_ic, compute_turnover, compute_max_drawdown, compute_win_rate
`scripts/overnight_backtest.py` | Tests for overnight_backtest | backtest
`scripts/overnight_data_quality.py` | Overnight data_quality | analyze_quality, main
`scripts/overnight_ensemble.py` | Overnight ensemble | train_ensemble
`scripts/overnight_feature_engineering.py` | Overnight feature_engineering | add_fourier_features, add_wavelet_features, add_entropy_features, add_fractal_dimension, add_microstructure_proxies
`scripts/overnight_feature_selection.py` | Overnight feature_selection | select_features
`scripts/overnight_hyperopt.py` | Overnight hyperopt | hyperopt_lightgbm
`scripts/overnight_models.py` | Overnight models | train_all_models
`scripts/overnight_multilabel.py` | Overnight multilabel | train_all_horizons
`scripts/regime_analysis.py` | Regime Analysis | add_micro_regime, compute_strategy_returns, main, clean_for_json
`scripts/repair_master_dataset.py` | Repair Master Dataset | -
`scripts/run_hydra_training.py` | Training for run_hydra_training | main
`scripts/run_multiple_training.py` | Training for run_multiple_training | load_dataset, train_single_run, main
`scripts/run_training_final.py` | Training for run_training_final | load_data, walk_forward_split, evaluate, train_model, main
`scripts/run_walk_forward_training.py` | Training for run_walk_forward_training | load_dataset, create_chronological_folds, validate_fold_data, compute_cost_aware_metrics, compute_baselines
`scripts/summarize_hydra_results.py` | Summarize Hydra Results | load_results, main
`scripts/temporal_split.py` | Temporal Split | compute_split_dates, list_available_features, validate_split, main
`scripts/train_baselines.py` | Training for baselines | load_data, prepare_features, train_ridge, train_random_forest, compute_strategy_returns
`scripts/training_validation.py` | Training for training_validation | compute_metrics
`scripts/training_validation_clean.py` | Training for training_validation_clean | compute_metrics
`scripts/validate_clean_dataset.py` | Validate Clean Dataset | check
`scripts/validate_master_dataset.py` | Validate Master Dataset | check
`scripts/vault_sync.py` | Vault Sync | parse_frontmatter, inject_synced_timestamp, sync_file, sync_all, main
`scripts/verify_direction_results.py` | Validates scripts | exists_size, first_nonempty, fnum
`scripts/verify_model_artifacts.py` | Validates scripts | check_artifact, main
`skills-lock.json` | Configuration for dominion | -
`tca/__init__.py` |   Init   | -
`tca/analytics.py` | Analytics | regime_breakdown, time_of_day_heatmap, waterfall_summary
`tca/attribution.py` | Attribution | compute_attribution
`tca/benchmarks.py` | Benchmarks | load_sim_benchmark, compute_benchmark_comparison
`tca/cli.py` | CLI interface | cmd_analyze, cmd_report, cmd_heatmap, main
`tca/config.py` | Configuration for tca | -
`tca/schema.py` | Schema | init_tca_schema
`tca/tests/__init__.py` |   Init   | -
`tca/tests/test_tca.py` | Tests for tca | test_attribution_sum, test_attribution_decision_cost, test_benchmark_comparison_sign, test_regime_field
`tests/dataset/test_matrix_builder.py` | Tests for matrix_builder | test_registry_exact_3000, test_registry_summary, test_build_small_matrix, test_quality_gates
`tests/training/__init__.py` |   Init   | -
`tests/training/test_guardrails.py` | Tests for guardrails | test_check_gate_verdict_missing, test_check_gate_verdict_pass, test_check_gate_verdict_fail, test_check_data_quality_pass, test_check_data_quality_fail
`tests/training/test_labels.py` | Tests for labels | test_session_detection, test_session_spread, test_triple_barrier_basic, test_triple_barrier_both_hit, test_min_hold_bars
`tests/training/test_splits.py` | Tests for splits | test_compute_embargo_purge, test_chronological_split_expanding, test_chronological_split_oos, test_validate_split_safety, test_split_safety_fails_on_overlap
`tmp/ragd_mcp_smoke.py` | Ragd Mcp Smoke | main
`toxicity/__init__.py` |   Init   | -
`toxicity/adverse.py` | Adverse | compute_adverse_selection, compute_toxicity_score
`toxicity/alerts.py` | Alerts | generate_alerts, store_alerts
`toxicity/cli.py` | CLI interface | cmd_compute, cmd_status, cmd_alerts, main
`toxicity/config.py` | Configuration for toxicity | -
`toxicity/ofi.py` | Ofi | compute_ofi_features
`toxicity/schema.py` | Schema | init_toxicity_schema
`toxicity/tests/__init__.py` |   Init   | -
`toxicity/tests/test_toxicity.py` | Tests for toxicity | test_vpin_bounded, test_ofi_sign, test_adverse_selection_formula, test_toxicity_score_bounded
`toxicity/vpin.py` | Vpin | compute_vpin_detailed