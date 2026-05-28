# LLM Context Protocol — Dominion V2

**Date:** 2026-05-22  
**Status:** Active

---

## Quick Stats

| Metric | Value |
|--------|-------|
| **Total repo** | 7.57 GB (19,445 files) |
| **Clean source** | 2.53 MB (589 files) |
| **Reduction** | 99.97% |
| **Tokens (source)** | ~664K |
| **Tokens (map only)** | ~9K |

---

## Usage

### Option 1: Load `repo_map.md` (Recommended)
```bash
cat repo_map.md  # 37 KB, 9K tokens
```
Compact directory breakdown + file list with key exports. Navigate first, then read specific files.

### Option 2: Load Full Source (Deep Analysis)
```bash
# All Python/C++ source (664K tokens)
# Use when you need full implementation details
```

### Option 3: Hybrid
1. Load `repo_map.md` for navigation (9K tokens)
2. Ask LLM to identify 3-5 relevant files
3. Read only those files (saves 90% of token budget)

---

## What's Included (2.53 MB)

**Python source** (2.44 MB)  
- Core: `data_pipeline/`, `domdata/`, `model/`, `tca/`, `toxicity/`
- Scripts: `scripts/*.py` (100+ orchestration scripts)
- Tests: `tests/**/*.py`

**C++ kernels** (0.04 MB)  
- `cpp/kernels/*.cpp` (microstructure, rolling, statistical, technical)

**Config** (0.05 MB)  
- `requirements.txt`, `pyproject.toml`, `pytest.ini`
- `CLAUDE.md`, `AGENTS.md`, `README.md`
- Build: `Makefile`, `meson.build`

**Selective JSON** (0.04 MB)  
- `data/registry/semantic_column_mapping.json`
- `artifacts/hydra/features_fold0.json`
- `skills-lock.json`

---

## What's Excluded (7.57 GB)

`.llmignore` controls exclusion:

- **DATA** (52.1% / 4.0 GB) — CSVs, Parquet, HDF5, SQLite, backups
- **BUILD** (27.4% / 2.1 GB) — `__pycache__/`, `build/`, `dist/`, `*.o`, `*.so`
- **MODELS** (15.5% / 1.2 GB) — `*.pt`, `*.onnx`, `*.safetensors`, `*.bin`
- **MISC** (3.8% / 293 MB) — logs, venvs, `node_modules/`
- **ARCHIVES** (0.9% / 66 MB) — `*.zip`, `*.tar`, `*.gz`

---

## Token Budget (1M Context)

**With repo_map.md only:**
- Map: 9K tokens
- Conversation: 900K tokens
- Responses: 91K tokens

**With full source:**
- Source: 664K tokens
- Conversation: 300K tokens
- Responses: 36K tokens

**Hybrid (recommended):**
- Map: 9K tokens
- Selective files: 50-100K tokens
- Conversation: 800K tokens
- Responses: 91K tokens

---

## File Priority (Core Modules)

1. `domdata/` — MT5 data bridge (read-only safety)
2. `data_pipeline/features/` — feature engineering (price, macro, microstructure, regime)
3. `model/training/` — walk-forward training, cost-aware metrics
4. `model/validation/` — point-in-time safety, data quality gates
5. `tca/` — transaction cost attribution
6. `toxicity/` — order flow toxicity (VPIN, OFI, adverse selection)

---

## Key Scripts (Top 10)

1. `scripts/dominion_cli.py` — main CLI
2. `scripts/run_walk_forward_training.py` — backtest orchestrator
3. `scripts/build_master_dataset.py` — dataset builder
4. `scripts/expand_features_3k.py` — 3K feature expansion (C++ kernels)
5. `scripts/overnight_ensemble.py` — multi-model ensemble
6. `scripts/validate_master_dataset.py` — data quality checks
7. `scripts/regime_analysis.py` — market regime detection
8. `scripts/feature_stability.py` — feature drift monitoring
9. `scripts/dominion_health.py` — system health check
10. `scripts/codexrag.py` — RAGD query interface

---

## Critical Tests

1. `tests/training/test_labels.py` — triple-barrier label validation
2. `tests/training/test_splits.py` — walk-forward split safety
3. `tests/training/test_guardrails.py` — data quality gates
4. `domdata/tests/test_trading_blocked.py` — trading token safety

---

## Validation Commands

```bash
# Check source size
find . -name '*.py' -o -name '*.cpp' | xargs du -ch | tail -1

# Verify no trading tokens in source
python domdata/check_no_trading.py

# Health check
domdata doctor

# RAGD query
dominion ragd-query "topic"
```

---

## Next Steps

1. ✅ Audit complete (99.97% reduction)
2. ✅ `.llmignore` created
3. ✅ `repo_map.md` generated (37 KB, 9K tokens)
4. ⏸️ Test: Load `repo_map.md` into Claude, verify navigation works
5. ⏸️ Document: Add to `CLAUDE.md` workflow section
