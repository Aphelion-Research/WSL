# HYDRA Dataset Audit - 2026-05-22

Status: STRUCTURE GREEN, SIGNAL NOT RE-TESTED

## Executive Summary

The old 70-feature blocker is stale for the current registry-gated M5 dataset. A fresh rebuild of `data/hydra_m5_dataset.parquet` produced 100,000 rows x 3,001 columns, 148 trainable non-label features, and a valid 90-feature semantic mapping. HYDRA quality gates allow training on this matrix.

The overnight pipeline did produce long-history Dukascopy data, but the status files overstate the final feature matrices. The usable long-history clean master is structurally valid after regenerating its missing schema manifest.

RAGD MCP context was unavailable during this audit: both `ragd_handoff_read` and `ragd_query` failed against `127.0.0.1:7474` with connection refused.

## Overnight Artifact Truth

| Artifact | Actual Status |
|---|---:|
| `data/mt5_history/XAUUSD_M5_dukascopy.parquet` | 782,825 rows x 9 cols |
| `data/mt5_history/XAUUSD_M5_MASTER.parquet` | 789,257 rows x 9 cols |
| `data/hydra_xauusd_m5_master.parquet` | 789,257 rows x 1,147 cols, broken source/time lineage |
| `data/hydra_xauusd_m5_master_clean.parquet` | 782,825 rows x 1,125 cols |
| `data/hydra_xauusd_m5_3k.parquet` | 100,000 rows x 1,580 cols |
| `data/hydra_xauusd_m5_advanced.parquet` | 100,000 rows x 4,865 cols |
| `data/hydra_xauusd_m5_selected.parquet` | 85,212 rows x 510 cols |

The claimed 850K-row / 5,500-feature overnight result is not present as a single validated matrix.

## Fixes Applied

- Rebuilt `data/hydra_m5_dataset.parquet` with `scripts/build_full_dataset.py`.
- Restored `data/registry/semantic_column_mapping.json` with 90 mapped Block B semantic features.
- Regenerated `data/hydra_xauusd_m5_master_schema.json`.
- Fixed `scripts/repair_master_dataset.py` so schema `columns` only lists columns present in the clean dataset; dropped dead features are now recorded under `excluded_columns`.
- Updated `tests/dataset/test_matrix_builder.py` for the current 50-column reserved allocation and numbered registry slots.
- Added `CLAUDE.md` to `config/forbidden_tokens.json` allowlist, matching `AGENTS.md`, so root-level safety documentation does not fail the trading-token scanner.

## Validation

```bash
python3 scripts/build_full_dataset.py --timeframe M5 --output data/hydra_m5_dataset.parquet --max-rows 100000 --run-gates
# PASS: 100000 x 3001, 148 trainable features, 90 mapped semantic features, TRAINING ALLOWED

python3 scripts/repair_master_dataset.py
# PASS: clean master 782825 rows, 1076 features, 48 labels, 22 excluded dead features

python3 scripts/validate_clean_dataset.py
# PASS: 17/17, MASTER_CLEAN_READY_FOR_RESEARCH

python3 -m pytest -q tests/dataset/test_matrix_builder.py
# PASS: 4 passed

python3 domdata/check_no_trading.py
# PASS: no forbidden trading tokens outside allowlist
```

## Remaining Work

- Do not treat the overnight 3K/advanced matrices as validated 850K-row deliverables; they are 100K-row derivatives.
- ML signal was not re-tested in this pass. Previous walk-forward results still show weak/no tradable edge near AUC 0.51 for the 100K registry-gated M5 dataset.
- Full point-in-time leakage validation is still stronger work than the current basic gate.
