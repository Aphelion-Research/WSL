# Phase 5 Native Core Startup Snapshot

## Timestamp
2026-05-14T15:50:47-04:00

## Git
```text
 M AGENT_HANDOFF.md
 M PROGRESS.md
 M dominion_agent/safety.py
 M reports/phase-5-consolidation-latest.md
?? reports/phase-5-native-core-start-20260514-155047.md
4f7d229ae1e14511f37b2958f2fd0d4a47daedca
```

## Repo Root
```text
/home/Martin/Dominion
DOMINION_ROOT=/home/Martin/Dominion
PYTHONPATH=
```

## Python Full Tests
```text
........................................................................ [ 18%]
........................................................................ [ 37%]
........................................................................ [ 55%]
........................................................................ [ 74%]
........................................................................ [ 93%]
...........................                                              [100%]
387 passed, 2 deselected in 53.71s
```

## Python Non-Integration Tests
```text
........................................................................ [ 18%]
........................................................................ [ 37%]
........................................................................ [ 55%]
........................................................................ [ 74%]
........................................................................ [ 93%]
...........................                                              [100%]
387 passed, 2 deselected in 54.39s
```

## Trading Guard
```text
PASS: no forbidden trading tokens outside allowlist
```

## Doctor Offline
```text
=== Foundation Checks ===
  PASS ignore_rules
  PASS manifest
  PASS cache
  PASS ragd_bridge
  PASS profiler
  PASS semantic_diff
  PASS ledger_schema
  WARN ragd_embed
  WARN ragd_chunker
  WARN ragd_hnsw
  PASS ragd_graph
  WARN ragd_vault
=== Platform Checks ===
  PASS ragd_reachable
  PASS dominion_health
  PASS domdata_notice
```

## Doctor Offline JSON
```json
{
  "checks": {
    "a2_error": "RAGD request failed for http://127.0.0.1:7474/memory/decisions?limit=1: <urlopen error [Errno 111] Connection refused>",
    "a2_trace_presence": true,
    "cache": {
      "status": "ok"
    },
    "domdata_notice": "skipped (offline)",
    "dominion_health": "skipped (offline)",
    "ignore_rules": {
      "secrets_blocked": true,
      "status": "ok"
    },
    "ledger_schema": {
      "status": "ok"
    },
    "manifest": {
      "status": "ok"
    },
    "profiler": {
      "status": "ok"
    },
    "ragd_bridge": {
      "reachable": false,
      "status": "ok"
    },
    "ragd_chunker": {
      "error": "<urlopen error [Errno 111] Connection refused>",
      "reachable": false,
      "status": "warn"
    },
    "ragd_embed": {
      "api_key_present": false,
      "cache": {
        "bytes": 0,
        "entries": 0,
        "path": "/home/Martin/.ragd/embed_cache.db",
        "profiles": []
      },
      "model": "voyage-code-2",
      "provider": "voyage",
      "status": "warn"
    },
    "ragd_graph": {
      "by_relation": {
        "calls": 149,
        "defines": 997,
        "imports": 69
      },
      "edges": 1215,
      "nodes": 1055,
      "status": "ok"
    },
    "ragd_hnsw": {
      "exists": false,
      "path": "/home/Martin/.ragd/hnsw_voyage_voyage-code-2_3072.bin",
      "status": "warn"
    },
    "ragd_reachable": "skipped (offline)",
    "ragd_vault": {
      "broken_links": 281,
      "invalid_frontmatter": 0,
      "notes": 874,
      "status": "warn"
    },
    "semantic_diff": {
      "status": "ok",
      "test_result": "format-only"
    }
  },
  "overall": "ok"
}
```

## Vault Doctor
```json
{
  "broken_links": [
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-13/test_second_scan_unchanged_fil0/repo/Test-L1-1db70634",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-14/test_rescan_detects_changed_fi0/Test-L1-fcb7bf32",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-14/test_rescan_detects_deleted_fi0/Test-L1-fd84a2ef",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-14/test_rescan_detects_new_file0/Test-L1-79591ae0",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-14/test_rescan_with_no_changes_pr0/Test-L1-443dd7b1",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-14/test_scan_idempotent_manifest_0/Test-L1-21648651",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-14/test_scan_populates_manifest0/Test-L1-d9b93aa1",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-14/test_scan_returns_trace_id0/Test-L1-67b67346",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-14/test_scan_secrets_not_indexed0/Test-L1-51460f5d",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-14/test_second_scan_unchanged_fil0/repo/Test-L1-cf24556a",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-15/test_rescan_detects_changed_fi0/Test-L1-3b741af6",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-15/test_rescan_detects_deleted_fi0/Test-L1-b11b47e0",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-15/test_rescan_detects_new_file0/Test-L1-953c9811",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-15/test_rescan_with_no_changes_pr0/Test-L1-b6e89bb9",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-15/test_scan_idempotent_manifest_0/Test-L1-ff39ff8f",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-15/test_scan_populates_manifest0/Test-L1-d27ef2d5",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-15/test_scan_returns_trace_id0/Test-L1-3d6ed95b",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-15/test_scan_secrets_not_indexed0/Test-L1-bc8dab38",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-15/test_second_scan_unchanged_fil0/repo/Test-L1-addc6d6e",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-19/test_rescan_detects_changed_fi0/Test-L1-1645c465",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-19/test_rescan_detects_deleted_fi0/Test-L1-cad18674",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-19/test_rescan_detects_new_file0/Test-L1-3091f503",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-19/test_rescan_with_no_changes_pr0/Test-L1-188faac7",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-19/test_scan_idempotent_manifest_0/Test-L1-adbab7c3",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-19/test_scan_populates_manifest0/Test-L1-a86d4ad6",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-19/test_scan_returns_trace_id0/Test-L1-5d95ec68",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-19/test_scan_secrets_not_indexed0/Test-L1-b4c3658a",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-19/test_second_scan_unchanged_fil0/repo/Test-L1-9ccb55b2",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-20/test_rescan_detects_changed_fi0/Test-L1-a32d69a8",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-20/test_rescan_detects_deleted_fi0/Test-L1-82f93776",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-20/test_rescan_detects_new_file0/Test-L1-342a0fbf",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-20/test_rescan_with_no_changes_pr0/Test-L1-7c463739",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-20/test_scan_idempotent_manifest_0/Test-L1-3163105c",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-20/test_scan_populates_manifest0/Test-L1-63c358d5",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-20/test_scan_returns_trace_id0/Test-L1-a1915274",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-20/test_scan_secrets_not_indexed0/Test-L1-555b85b2",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-20/test_second_scan_unchanged_fil0/repo/Test-L1-8fbd7073",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-21/test_rescan_detects_changed_fi0/Test-L1-fb1bb9c7",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-21/test_rescan_detects_deleted_fi0/Test-L1-e9343a4e",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-21/test_rescan_detects_new_file0/Test-L1-bcae0745",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-21/test_rescan_with_no_changes_pr0/Test-L1-a0cf580c",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-21/test_scan_idempotent_manifest_0/Test-L1-5a97d257",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-21/test_scan_populates_manifest0/Test-L1-f5ccabab",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-21/test_scan_returns_trace_id0/Test-L1-98976df3",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-21/test_scan_secrets_not_indexed0/Test-L1-2f7f84a5",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-21/test_second_scan_unchanged_fil0/repo/Test-L1-214e60c0",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-35/test_second_scan_unchanged_fil0/repo/Test-L1-f3f3197a",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-36/test_second_scan_unchanged_fil0/repo/Test-L1-21c05c76",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-37/test_second_scan_unchanged_fil0/repo/Test-L1-5ad44854",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-38/test_second_scan_unchanged_fil0/repo/Test-L1-bced3a4c",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-39/test_second_scan_unchanged_fil0/repo/Test-L1-193056f9",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-46/test_second_scan_unchanged_fil0/repo/Test-L1-e04d46cc",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-47/test_second_scan_unchanged_fil0/repo/Test-L1-29f27bc3",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-51/test_second_scan_unchanged_fil0/repo/Test-L1-8872dcb6",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-52/test_second_scan_unchanged_fil0/repo/Test-L1-70060606",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-53/test_second_scan_unchanged_fil0/repo/Test-L1-74da3326",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-56/test_second_scan_unchanged_fil0/repo/Test-L1-26c61145",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-53/test_integration_ingest_single0/tmp.pytest-of-Martin.pytest-53.test_integration_ingest_single0.test.foo-L2-edd9f885",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-53/test_second_scan_unchanged_fil0/repo/tmp.pytest-of-Martin.pytest-53.test_second_scan_unchanged_fil0.repo.main.main-L1-2dc49453",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-56/test_integration_ingest_single0/tmp.pytest-of-Martin.pytest-56.test_integration_ingest_single0.test.foo-L2-edd9f885",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-56/test_second_scan_unchanged_fil0/repo/tmp.pytest-of-Martin.pytest-56.test_second_scan_unchanged_fil0.repo.main.main-L1-2dc49453",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/get_json-L18-69eabaf9",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-14/test_rescan_detects_changed_fi0/src/add-L1-b758914f",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-14/test_rescan_detects_deleted_fi0/src/add-L1-6158978d",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-14/test_rescan_detects_new_file0/src/add-L1-5083b38e",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-14/test_rescan_with_no_changes_pr0/src/add-L1-54cc86a3",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-14/test_scan_idempotent_manifest_0/src/add-L1-a4123ba9",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-14/test_scan_populates_manifest0/src/add-L1-716aca5b",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-14/test_scan_returns_trace_id0/src/add-L1-75a88903",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-14/test_scan_secrets_not_indexed0/src/add-L1-17aaee96",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-15/test_rescan_detects_changed_fi0/src/add-L1-4a4b1835",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-15/test_rescan_detects_deleted_fi0/src/add-L1-518be2c8",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-15/test_rescan_detects_new_file0/src/add-L1-fde79386",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-15/test_rescan_with_no_changes_pr0/src/add-L1-2f285494",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-15/test_scan_idempotent_manifest_0/src/add-L1-94938201",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-15/test_scan_populates_manifest0/src/add-L1-215b3029",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-15/test_scan_returns_trace_id0/src/add-L1-9835895b",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-15/test_scan_secrets_not_indexed0/src/add-L1-479e1e74",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-19/test_rescan_detects_changed_fi0/src/add-L1-3fca6397",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-19/test_rescan_detects_deleted_fi0/src/add-L1-938fc098",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-19/test_rescan_detects_new_file0/src/add-L1-c8b8f6fb",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-19/test_rescan_with_no_changes_pr0/src/add-L1-58a572f8",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-19/test_scan_idempotent_manifest_0/src/add-L1-adbd5d1d",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-19/test_scan_populates_manifest0/src/add-L1-3cc158fb",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-19/test_scan_returns_trace_id0/src/add-L1-c60a0185",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-19/test_scan_secrets_not_indexed0/src/add-L1-75e95815",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-20/test_rescan_detects_changed_fi0/src/add-L1-ae093ab6",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-20/test_rescan_detects_deleted_fi0/src/add-L1-b7f26e26",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-20/test_rescan_detects_new_file0/src/add-L1-87acefbb",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-20/test_rescan_with_no_changes_pr0/src/add-L1-a1a71dc5",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-20/test_scan_idempotent_manifest_0/src/add-L1-490a3973",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-20/test_scan_populates_manifest0/src/add-L1-54e6c6e0",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-20/test_scan_returns_trace_id0/src/add-L1-386e3d36",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-20/test_scan_secrets_not_indexed0/src/add-L1-6fe23169",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-21/test_rescan_detects_changed_fi0/src/add-L1-28a051c4",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-21/test_rescan_detects_deleted_fi0/src/add-L1-cfa71104",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-21/test_rescan_detects_new_file0/src/add-L1-d046ff5d",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-21/test_rescan_with_no_changes_pr0/src/add-L1-1a73ef15",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-21/test_scan_idempotent_manifest_0/src/add-L1-470176a0",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-21/test_scan_populates_manifest0/src/add-L1-8ad47149",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-21/test_scan_returns_trace_id0/src/add-L1-f1282ab7",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-21/test_scan_secrets_not_indexed0/src/add-L1-99c6dd05",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-14/test_binary_files_not_indexed0/repo/file-L1-ad46d1fd",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-14/test_rescan_detects_changed_fi0/file-L1-2dd8a55b",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-14/test_rescan_detects_changed_fi0/src/file-L1-83e96d54",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-14/test_rescan_detects_deleted_fi0/file-L1-423d1114",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-14/test_rescan_detects_deleted_fi0/src/file-L1-867b3b2a",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-14/test_rescan_detects_new_file0/file-L1-556957d7",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-14/test_rescan_detects_new_file0/file-L1-f660ac9f",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-14/test_rescan_detects_new_file0/src/file-L1-506a1cf9",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-14/test_rescan_with_no_changes_pr0/file-L1-9ff65ea9",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-14/test_rescan_with_no_changes_pr0/src/file-L1-297c111e",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-14/test_scan_idempotent_manifest_0/file-L1-17a4adc6",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-14/test_scan_idempotent_manifest_0/src/file-L1-e84b153a",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-14/test_scan_populates_manifest0/file-L1-be64f9f8",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-14/test_scan_populates_manifest0/src/file-L1-d3839953",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-14/test_scan_returns_trace_id0/file-L1-9bad29b0",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-14/test_scan_returns_trace_id0/src/file-L1-90c498ce",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-14/test_scan_secrets_not_indexed0/file-L1-da5780eb",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-14/test_scan_secrets_not_indexed0/src/file-L1-69006a82",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-15/test_binary_files_not_indexed0/repo/file-L1-b7d74324",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-15/test_rescan_detects_changed_fi0/file-L1-fc508fd5",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-15/test_rescan_detects_changed_fi0/src/file-L1-a842e999",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-15/test_rescan_detects_deleted_fi0/file-L1-a6ceae21",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-15/test_rescan_detects_deleted_fi0/src/file-L1-8ccc537c",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-15/test_rescan_detects_new_file0/file-L1-fdde879e",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-15/test_rescan_detects_new_file0/file-L1-fea39990",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-15/test_rescan_detects_new_file0/src/file-L1-200f6272",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-15/test_rescan_with_no_changes_pr0/file-L1-2529bfed",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-15/test_rescan_with_no_changes_pr0/src/file-L1-725fbb9e",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-15/test_scan_idempotent_manifest_0/file-L1-fa77fe1a",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-15/test_scan_idempotent_manifest_0/src/file-L1-2652704e",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-15/test_scan_populates_manifest0/file-L1-5d74ba67",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-15/test_scan_populates_manifest0/src/file-L1-30e2dd9e",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-15/test_scan_returns_trace_id0/file-L1-1173db7a",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-15/test_scan_returns_trace_id0/src/file-L1-4239b8be",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-15/test_scan_secrets_not_indexed0/file-L1-be3ae501",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-15/test_scan_secrets_not_indexed0/src/file-L1-708b426f",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-19/test_binary_files_not_indexed0/repo/file-L1-2a8f79a4",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-19/test_rescan_detects_changed_fi0/file-L1-d8cd0711",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-19/test_rescan_detects_changed_fi0/src/file-L1-43c192c0",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-19/test_rescan_detects_deleted_fi0/file-L1-fbc4df9d",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-19/test_rescan_detects_deleted_fi0/src/file-L1-1d226b75",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-19/test_rescan_detects_new_file0/file-L1-2d7ecd98",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-19/test_rescan_detects_new_file0/file-L1-60c8d08d",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-19/test_rescan_detects_new_file0/src/file-L1-bb039ea3",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-19/test_rescan_with_no_changes_pr0/file-L1-538c44a6",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-19/test_rescan_with_no_changes_pr0/src/file-L1-9a8a5ecc",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-19/test_scan_idempotent_manifest_0/file-L1-1ac5dd91",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-19/test_scan_idempotent_manifest_0/src/file-L1-e7a71596",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-19/test_scan_populates_manifest0/file-L1-3fd1605f",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-19/test_scan_populates_manifest0/src/file-L1-3dda2540",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-19/test_scan_returns_trace_id0/file-L1-36602cbb",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-19/test_scan_returns_trace_id0/src/file-L1-c95ce47a",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-19/test_scan_secrets_not_indexed0/file-L1-91ca6fbd",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-19/test_scan_secrets_not_indexed0/src/file-L1-fbaead39",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-20/test_binary_files_not_indexed0/repo/file-L1-a38f34a5",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-20/test_rescan_detects_changed_fi0/file-L1-85e565b2",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-20/test_rescan_detects_changed_fi0/src/file-L1-5c95a8c8",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-20/test_rescan_detects_deleted_fi0/file-L1-340368e4",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-20/test_rescan_detects_deleted_fi0/src/file-L1-22234e36",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-20/test_rescan_detects_new_file0/file-L1-c936a510",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-20/test_rescan_detects_new_file0/file-L1-4eff3e6b",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-20/test_rescan_detects_new_file0/src/file-L1-2c6392e0",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-20/test_rescan_with_no_changes_pr0/file-L1-393bcdd6",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-20/test_rescan_with_no_changes_pr0/src/file-L1-30e145eb",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-20/test_scan_idempotent_manifest_0/file-L1-67525d5f",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-20/test_scan_idempotent_manifest_0/src/file-L1-7819a4be",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-20/test_scan_populates_manifest0/file-L1-53041762",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-20/test_scan_populates_manifest0/src/file-L1-ed42ea9e",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-20/test_scan_returns_trace_id0/file-L1-37b8f0b2",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-20/test_scan_returns_trace_id0/src/file-L1-c4e24962",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-20/test_scan_secrets_not_indexed0/file-L1-39b4d035",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-20/test_scan_secrets_not_indexed0/src/file-L1-4c1f3c05",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-21/test_binary_files_not_indexed0/repo/file-L1-84fdf898",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-21/test_rescan_detects_changed_fi0/file-L1-62941485",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-21/test_rescan_detects_changed_fi0/src/file-L1-b95d5c39",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-21/test_rescan_detects_deleted_fi0/file-L1-eb6c04cd",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-21/test_rescan_detects_deleted_fi0/src/file-L1-bea26cdb",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-21/test_rescan_detects_new_file0/file-L1-9a71ca85",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-21/test_rescan_detects_new_file0/file-L1-c3730b47",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-21/test_rescan_detects_new_file0/src/file-L1-503b9b03",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-21/test_rescan_with_no_changes_pr0/file-L1-d778273f",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-21/test_rescan_with_no_changes_pr0/src/file-L1-fcdccdfb",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-21/test_scan_idempotent_manifest_0/file-L1-c0e2e64e",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-21/test_scan_idempotent_manifest_0/src/file-L1-3ce00d0e",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-21/test_scan_populates_manifest0/file-L1-6dfdd1b7",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-21/test_scan_populates_manifest0/src/file-L1-788179e2",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-21/test_scan_returns_trace_id0/file-L1-c1b84ce4",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-21/test_scan_returns_trace_id0/src/file-L1-17e540eb",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-21/test_scan_secrets_not_indexed0/file-L1-2ed5acd1",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-21/test_scan_secrets_not_indexed0/src/file-L1-a1b449dc",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-14/test_integration_ingest_single0/foo-L2-fb214ec4",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-15/test_integration_ingest_single0/foo-L2-ea7883ec",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-19/test_integration_ingest_single0/foo-L2-bf17dbf3",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-20/test_integration_ingest_single0/foo-L2-e1c61757",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-21/test_integration_ingest_single0/foo-L2-37d0c979",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-22/test_integration_ingest_single0/foo-L2-53777c9c",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-29/test_integration_ingest_single0/foo-L2-82cab343",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-35/test_integration_ingest_single0/foo-L2-15af6266",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-36/test_integration_ingest_single0/foo-L2-b3a59f7b",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-37/test_integration_ingest_single0/foo-L2-e7a441ee",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-38/test_integration_ingest_single0/foo-L2-66bb0b2e",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-39/test_integration_ingest_single0/foo-L2-cc5323f1",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-46/test_integration_ingest_single0/foo-L2-6827ce66",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-47/test_integration_ingest_single0/foo-L2-a9ec4a72",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-51/test_integration_ingest_single0/foo-L2-73769e4b",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-52/test_integration_ingest_single0/foo-L2-d5ec6b23",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-14/test_rescan_detects_changed_fi0/key-L1-996e4a56",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-14/test_rescan_detects_deleted_fi0/key-L1-64d65bc2",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-14/test_rescan_detects_new_file0/key-L1-2a096300",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-14/test_rescan_with_no_changes_pr0/key-L1-20570a51",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-14/test_scan_idempotent_manifest_0/key-L1-98753dfe",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-14/test_scan_populates_manifest0/key-L1-6d9567d3",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-14/test_scan_returns_trace_id0/key-L1-ce26fa35",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-14/test_scan_secrets_not_indexed0/key-L1-dcd9f3c5",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-15/test_rescan_detects_changed_fi0/key-L1-f06817de",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-15/test_rescan_detects_deleted_fi0/key-L1-5c8c6fe1",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-15/test_rescan_detects_new_file0/key-L1-49403599",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-15/test_rescan_with_no_changes_pr0/key-L1-1fee37a5",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-15/test_scan_idempotent_manifest_0/key-L1-c0b317b9",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-15/test_scan_populates_manifest0/key-L1-91b2d83b",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-15/test_scan_returns_trace_id0/key-L1-ea6aa8f6",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-15/test_scan_secrets_not_indexed0/key-L1-30deea8c",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-19/test_rescan_detects_changed_fi0/key-L1-48ad0231",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-19/test_rescan_detects_deleted_fi0/key-L1-a6bb9371",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-19/test_rescan_detects_new_file0/key-L1-66e00e71",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-19/test_rescan_with_no_changes_pr0/key-L1-94105dd6",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-19/test_scan_idempotent_manifest_0/key-L1-45237298",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-19/test_scan_populates_manifest0/key-L1-b41cef2a",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-19/test_scan_returns_trace_id0/key-L1-4c133770",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-19/test_scan_secrets_not_indexed0/key-L1-2a1c06da",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-20/test_rescan_detects_changed_fi0/key-L1-fe1d7172",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-20/test_rescan_detects_deleted_fi0/key-L1-a5801746",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-20/test_rescan_detects_new_file0/key-L1-2da84489",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-20/test_rescan_with_no_changes_pr0/key-L1-d53d1056",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-20/test_scan_idempotent_manifest_0/key-L1-c6b38128",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-20/test_scan_populates_manifest0/key-L1-52d82211",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-20/test_scan_returns_trace_id0/key-L1-525663cd",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-20/test_scan_secrets_not_indexed0/key-L1-bc9e8432",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-21/test_rescan_detects_changed_fi0/key-L1-b6d213b3",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-21/test_rescan_detects_deleted_fi0/key-L1-be06f7aa",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-21/test_rescan_detects_new_file0/key-L1-8f8a82d3",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-21/test_rescan_with_no_changes_pr0/key-L1-29d15412",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-21/test_scan_idempotent_manifest_0/key-L1-48aca536",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-21/test_scan_populates_manifest0/key-L1-99d5b48f",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-21/test_scan_returns_trace_id0/key-L1-e7eeea36",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-21/test_scan_secrets_not_indexed0/key-L1-3d97b80d",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/main-L35-e901b03b",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-13/test_second_scan_unchanged_fil0/repo/main-L1-8c3aa95c",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-14/test_second_scan_unchanged_fil0/repo/main-L1-848af276",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-15/test_second_scan_unchanged_fil0/repo/main-L1-f3227bc2",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-19/test_second_scan_unchanged_fil0/repo/main-L1-f6cbb7c6",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-20/test_second_scan_unchanged_fil0/repo/main-L1-eb299b7a",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-21/test_second_scan_unchanged_fil0/repo/main-L1-1685aded",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-35/test_second_scan_unchanged_fil0/repo/main-L1-a6e02906",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-36/test_second_scan_unchanged_fil0/repo/main-L1-562118d3",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-37/test_second_scan_unchanged_fil0/repo/main-L1-ec92eb2c",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-38/test_second_scan_unchanged_fil0/repo/main-L1-230242eb",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-39/test_second_scan_unchanged_fil0/repo/main-L1-657a2a04",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-46/test_second_scan_unchanged_fil0/repo/main-L1-18f19a83",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-47/test_second_scan_unchanged_fil0/repo/main-L1-5b89b056",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-51/test_second_scan_unchanged_fil0/repo/main-L1-6ee2c647",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-52/test_second_scan_unchanged_fil0/repo/main-L1-3741b870",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/top_level-L1-17fd56b5",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-14/test_integration_ingest_single0/top_level-L1-60ab083e",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-15/test_integration_ingest_single0/top_level-L1-7e09c3f5",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-19/test_integration_ingest_single0/top_level-L1-cae93c6c",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-20/test_integration_ingest_single0/top_level-L1-2ffcc557",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-21/test_integration_ingest_single0/top_level-L1-609ce7a4",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-22/test_integration_ingest_single0/top_level-L1-f5742ce3",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-29/test_integration_ingest_single0/top_level-L1-eb7f6acc",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-35/test_integration_ingest_single0/top_level-L1-a42cd164",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-36/test_integration_ingest_single0/top_level-L1-aa14ad26",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-37/test_integration_ingest_single0/top_level-L1-603d0279",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-38/test_integration_ingest_single0/top_level-L1-b3efc134",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-39/test_integration_ingest_single0/top_level-L1-b2b806dc",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-46/test_integration_ingest_single0/top_level-L1-d3a99a8f",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-47/test_integration_ingest_single0/top_level-L1-56535f75",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-51/test_integration_ingest_single0/top_level-L1-cb6b4354",
    "_index/SYMBOL_INDEX.md -> symbols/tmp/pytest-of-Martin/pytest-52/test_integration_ingest_single0/top_level-L1-a8cbeaa0"
  ],
  "invalid_frontmatter": [],
  "mermaid_errors": [],
  "ok": false,
  "orphan_notes": [
    "_templates/Daily Changelog",
    "_templates/File Note",
    "_templates/Symbol Note"
  ],
  "total_notes": 874
}
```

## Complexity
```json
[
  {
    "package": "dominion_loader",
    "score": 83.5,
    "budget": 50.0,
    "over_budget": true,
    "warnings": [
      "Score 83.5 exceeds budget 50.0",
      "1 TEMP_ADAPTER(s) found \u2014 schedule removal",
      "9 broad exception handlers \u2014 hides errors",
      "19 untested modules"
    ],
    "remediation": [
      "dominion agent complexity budget --package dominion_loader",
      "Search for TEMP_ADAPTER comments and resolve them",
      "Replace broad `except Exception:` with specific exception types",
      "Add tests for untested modules in dominion_loader/tests/"
    ],
    "metrics": {
      "file_count": 38,
      "public_symbol_count": 68,
      "cli_command_count": 0,
      "test_count": 171,
      "todo_count": 2,
      "temp_adapter_count": 1,
      "broad_except_count": 9,
      "untested_module_count": 19,
      "large_file_penalty": 3.0,
      "average_file_lines": 160.5,
      "largest_file_lines": 369
    }
  },
  {
    "package": "dominion_ai",
    "score": 90.6,
    "budget": 130.0,
    "over_budget": false,
    "warnings": [
      "16 untested modules"
    ],
    "remediation": [
      "Add tests for untested modules in dominion_ai/tests/"
    ],
    "metrics": {
      "file_count": 30,
      "public_symbol_count": 52,
      "cli_command_count": 0,
      "test_count": 22,
      "todo_count": 1,
      "temp_adapter_count": 0,
      "broad_except_count": 1,
      "untested_module_count": 16,
      "large_file_penalty": 0.0,
      "average_file_lines": 44.0,
      "largest_file_lines": 164
    }
  },
  {
    "package": "dominion_agent",
    "score": 471.5,
    "budget": 350.0,
    "over_budget": true,
    "warnings": [
      "Score 471.5 exceeds budget 350.0",
      "6 TEMP_ADAPTER(s) found \u2014 schedule removal",
      "38 TODO/FIXME markers \u2014 technical debt accumulating",
      "29 broad exception handlers \u2014 hides errors",
      "20 untested modules",
      "Largest file has 628 lines \u2014 consider splitting"
    ],
    "remediation": [
      "dominion agent complexity budget --package dominion_agent",
      "Search for TEMP_ADAPTER comments and resolve them",
      "Address or assign TODO items before adding new features",
      "Replace broad `except Exception:` with specific exception types",
      "Add tests for untested modules in dominion_agent/tests/",
      "Split large files into focused, single-responsibility modules"
    ],
    "metrics": {
      "file_count": 32,
      "public_symbol_count": 74,
      "cli_command_count": 118,
      "test_count": 109,
      "todo_count": 38,
      "temp_adapter_count": 6,
      "broad_except_count": 29,
      "untested_module_count": 20,
      "large_file_penalty": 7.0,
      "average_file_lines": 210.1,
      "largest_file_lines": 628
    }
  },
  {
    "package": "ragd_embed",
    "score": 61.1,
    "budget": 75.0,
    "over_budget": false,
    "warnings": [
      "4 broad exception handlers \u2014 hides errors",
      "7 untested modules"
    ],
    "remediation": [
      "Replace broad `except Exception:` with specific exception types",
      "Add tests for untested modules in ragd_embed/tests/"
    ],
    "metrics": {
      "file_count": 13,
      "public_symbol_count": 22,
      "cli_command_count": 7,
      "test_count": 6,
      "todo_count": 0,
      "temp_adapter_count": 0,
      "broad_except_count": 4,
      "untested_module_count": 7,
      "large_file_penalty": 0.0,
      "average_file_lines": 47.5,
      "largest_file_lines": 162
    }
  },
  {
    "package": "ragd_hnsw",
    "score": 29.1,
    "budget": 75.0,
    "over_budget": false,
    "warnings": [
      "5 untested modules"
    ],
    "remediation": [
      "Add tests for untested modules in ragd_hnsw/tests/"
    ],
    "metrics": {
      "file_count": 8,
      "public_symbol_count": 7,
      "cli_command_count": 0,
      "test_count": 3,
      "todo_count": 0,
      "temp_adapter_count": 0,
      "broad_except_count": 2,
      "untested_module_count": 5,
      "large_file_penalty": 0.0,
      "average_file_lines": 48.9,
      "largest_file_lines": 138
    }
  },
  {
    "package": "ragd_chunker",
    "score": 61.5,
    "budget": 90.0,
    "over_budget": false,
    "warnings": [
      "10 untested modules"
    ],
    "remediation": [
      "Add tests for untested modules in ragd_chunker/tests/"
    ],
    "metrics": {
      "file_count": 16,
      "public_symbol_count": 15,
      "cli_command_count": 3,
      "test_count": 3,
      "todo_count": 0,
      "temp_adapter_count": 0,
      "broad_except_count": 0,
      "untested_module_count": 10,
      "large_file_penalty": 0.0,
      "average_file_lines": 28.7,
      "largest_file_lines": 110
    }
  },
  {
    "package": "ragd_graph",
    "score": 41.7,
    "budget": 75.0,
    "over_budget": false,
    "warnings": [],
    "remediation": [],
    "metrics": {
      "file_count": 4,
      "public_symbol_count": 9,
      "cli_command_count": 14,
      "test_count": 1,
      "todo_count": 0,
      "temp_adapter_count": 0,
      "broad_except_count": 0,
      "untested_module_count": 2,
      "large_file_penalty": 0.0,
      "average_file_lines": 61.8,
      "largest_file_lines": 169
    }
  },
  {
    "package": "ragd_vault",
    "score": 40.4,
    "budget": 100.0,
    "over_budget": false,
    "warnings": [
      "5 untested modules"
    ],
    "remediation": [
      "Add tests for untested modules in ragd_vault/tests/"
    ],
    "metrics": {
      "file_count": 8,
      "public_symbol_count": 13,
      "cli_command_count": 5,
      "test_count": 2,
      "todo_count": 0,
      "temp_adapter_count": 0,
      "broad_except_count": 1,
      "untested_module_count": 5,
      "large_file_penalty": 0.0,
      "average_file_lines": 64.0,
      "largest_file_lines": 180
    }
  },
  {
    "package": "ragd",
    "score": 51.9,
    "budget": 80.0,
    "over_budget": false,
    "warnings": [
      "7 TODO/FIXME markers \u2014 technical debt accumulating",
      "4 broad exception handlers \u2014 hides errors"
    ],
    "remediation": [
      "Address or assign TODO items before adding new features",
      "Replace broad `except Exception:` with specific exception types"
    ],
    "metrics": {
      "file_count": 5,
      "public_symbol_count": 13,
      "cli_command_count": 7,
      "test_count": 3,
      "todo_count": 7,
      "temp_adapter_count": 0,
      "broad_except_count": 4,
      "untested_module_count": 2,
      "large_file_penalty": 0.0,
      "average_file_lines": 90.4,
      "largest_file_lines": 258
    }
  },
  {
    "package": "domdata",
    "score": 209.2,
    "budget": 155.0,
    "over_budget": true,
    "warnings": [
      "Score 209.2 exceeds budget 155.0",
      "6 broad exception handlers \u2014 hides errors",
      "12 untested modules"
    ],
    "remediation": [
      "dominion agent complexity budget --package domdata",
      "Replace broad `except Exception:` with specific exception types",
      "Add tests for untested modules in domdata/tests/"
    ],
    "metrics": {
      "file_count": 16,
      "public_symbol_count": 54,
      "cli_command_count": 65,
      "test_count": 6,
      "todo_count": 0,
      "temp_adapter_count": 0,
      "broad_except_count": 6,
      "untested_module_count": 12,
      "large_file_penalty": 0.0,
      "average_file_lines": 68.2,
      "largest_file_lines": 258
    }
  },
  {
    "package": "research_os",
    "score": 196.2,
    "budget": 175.0,
    "over_budget": true,
    "warnings": [
      "Score 196.2 exceeds budget 175.0",
      "9 broad exception handlers \u2014 hides errors",
      "17 untested modules"
    ],
    "remediation": [
      "dominion agent complexity budget --package research_os",
      "Replace broad `except Exception:` with specific exception types",
      "Add tests for untested modules in research_os/tests/"
    ],
    "metrics": {
      "file_count": 26,
      "public_symbol_count": 69,
      "cli_command_count": 40,
      "test_count": 10,
      "todo_count": 0,
      "temp_adapter_count": 0,
      "broad_except_count": 9,
      "untested_module_count": 17,
      "large_file_penalty": 2.0,
      "average_file_lines": 63.9,
      "largest_file_lines": 367
    }
  },
  {
    "package": "scripts",
    "score": 336.5,
    "budget": 200.0,
    "over_budget": true,
    "warnings": [
      "Score 336.5 exceeds budget 200.0",
      "23 broad exception handlers \u2014 hides errors",
      "4 untested modules",
      "Largest file has 871 lines \u2014 consider splitting"
    ],
    "remediation": [
      "dominion agent complexity budget --package scripts",
      "Replace broad `except Exception:` with specific exception types",
      "Add tests for untested modules in scripts/tests/",
      "Split large files into focused, single-responsibility modules"
    ],
    "metrics": {
      "file_count": 4,
      "public_symbol_count": 50,
      "cli_command_count": 131,
      "test_count": 0,
      "todo_count": 2,
      "temp_adapter_count": 0,
      "broad_except_count": 23,
      "untested_module_count": 4,
      "large_file_penalty": 2.0,
      "average_file_lines": 280.8,
      "largest_file_lines": 871
    }
  },
  {
    "package": "tests",
    "score": 0.0,
    "budget": 20.0,
    "over_budget": false,
    "warnings": [],
    "remediation": [],
    "metrics": {
      "file_count": 0,
      "public_symbol_count": 0,
      "cli_command_count": 0,
      "test_count": 0,
      "todo_count": 0,
      "temp_adapter_count": 0,
      "broad_except_count": 0,
      "untested_module_count": 0,
      "large_file_penalty": 0.0,
      "average_file_lines": 0.0,
      "largest_file_lines": 0
    }
  }
]
```

## CMake Configure
```text
-- Configuring incomplete, errors occurred!
```
