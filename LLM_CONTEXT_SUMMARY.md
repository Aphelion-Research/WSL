# LLM Context Ingestion — Final Summary

**Date:** 2026-05-22  
**Status:** ✅ Complete (no files deleted, only exclusion list created)

---

## Results

| Metric | Before | After | Reduction |
|--------|--------|-------|-----------|
| **Size** | 7.57 GB | 2.53 MB | **99.97%** |
| **Files** | 19,445 | 589 | 96.97% |
| **Tokens** | ~2B | ~664K | 99.97% |

---

## What's Kept (2.53 MB / 589 files)

### Python Source (2.44 MB)
- Core modules: `data_pipeline/`, `domdata/`, `model/`, `tca/`, `toxicity/`
- Scripts: `scripts/*.py` (100+ training/orchestration scripts)
- Tests: `tests/**/*.py`
- Apps: `apps/mt5/combat` (MT5 bridge)

### C++ Source
- Kernels: `cpp/kernels/*.cpp` (microstructure, rolling, statistical, technical)

### Config (0.05 MB)
- Requirements: `requirements.txt`, `pyproject.toml`
- Build: `Makefile`, `meson.build`, `pytest.ini`
- Docs: `CLAUDE.md`, `AGENTS.md`, `README.md`

### Selective JSON (0.04 MB)
- `data/registry/semantic_column_mapping.json` (feature schemas)
- `artifacts/hydra/features_fold0.json` (feature lists)
- `skills-lock.json` (skill versions)

---

## What's Excluded (7.57 GB → 0 MB in context)

### DATA (52.1% / 4.0 GB)
- `data/` directory (CSVs, Parquet, HDF5, SQLite)
- `backups/` (old snapshots)
- `artifacts/hydra/` (training outputs)

### BUILD (27.4% / 2.1 GB)
- `__pycache__/`, `.cache/`, `build/`, `dist/`
- Compiled objects: `*.o`, `*.so`, `*.a`, `*.dll`

### MODELS (15.5% / 1.2 GB)
- Model weights: `*.pt`, `*.onnx`, `*.safetensors`, `*.bin`

### MISC (3.8% / 293 MB)
- Logs: `catboost_info/`, `mlruns/`, `*.log`
- Envs: `.venv/`, `venv/`, `node_modules/`

### ARCHIVES (0.9% / 66 MB)
- `awscliv2.zip`, other archives

---

## Deliverables

### 1. `.llmignore` (Exclusion List)
```bash
# Location: /home/Martin/Dominion/.llmignore
# Format: gitignore-style patterns
# Usage: LLM tools honor this file when ingesting repo
```

### 2. `repo_map.md` (Compact Manifest)
```bash
# Location: /home/Martin/Dominion/repo_map.md
# Size: 256 KB (~64K tokens)
# Contents:
#   - 3-level directory tree
#   - Dependency list (requirements.txt)
#   - File manifest (path | purpose | exports)
```

### 3. `llm_context_report.md` (Full Audit)
```bash
# Location: /home/Martin/Dominion/llm_context_report.md
# Details: Category breakdown, exclusion lists, validation
```

### 4. `audit_details.json` (Machine-Readable)
```bash
# Location: /home/Martin/Dominion/audit_details.json
# Format: JSON with category sizes
```

---

## Token Budget Analysis

### Context Window: 1M tokens (Claude Sonnet 4.5+)
- **Codebase:** 664K tokens
- **Conversation:** 300K tokens
- **Responses:** 36K tokens
- **Total:** 1M tokens ✅

### Alternative: 2M tokens (Claude Opus 4.7)
- **Codebase:** 664K tokens
- **Headroom:** 1.34M tokens (for long conversations, data samples)

---

## Validation

### Spot Check: Source Size
```bash
find /home/Martin/Dominion -type f \
  \( -name '*.py' -o -name '*.cpp' -o -name '*.hpp' \) \
  ! -path '*/__pycache__/*' ! -path '*/build/*' \
  | xargs du -ch | tail -1
# Output: 2.5M ✅
```

### Spot Check: Exclusion Works
```bash
# No data files in context
grep -r '\.csv\|\.parquet\|\.pkl' repo_map.md
# Output: (empty) ✅

# No build artifacts
grep -r '__pycache__\|\.so\|\.o' repo_map.md
# Output: (empty) ✅
```

---

## Usage Patterns

### Option 1: Load `repo_map.md` (Compact)
```python
# LLM prompt:
"""
Here is the Dominion V2 repository map (SOURCE + CONFIG only, no data/models):

{read repo_map.md}

Task: [your task here]
"""
```
**Best for:** Quick context, high-level navigation, finding files

### Option 2: Load Full Source (Deep)
```python
# LLM prompt:
"""
I need to understand the full implementation of [module].
Please read all Python files in data_pipeline/ and explain the architecture.
"""
```
**Best for:** Deep debugging, refactoring, architecture questions

### Option 3: Hybrid (Recommended)
```python
# Step 1: Load repo_map.md for navigation
# Step 2: Ask LLM to identify relevant files
# Step 3: Load only those 3-5 files for deep analysis
```
**Best for:** Most tasks (90% of use cases)

---

## Next Steps

1. ✅ **Audit complete** — no deletions needed
2. ✅ **Exclusion list created** (`.llmignore`)
3. ✅ **Compact map generated** (`repo_map.md`)
4. ⏸️ **Test ingestion** — load `repo_map.md` into Claude and verify
5. ⏸️ **Document workflow** — add to `CLAUDE.md` under "LLM Context Protocol"

---

## Key Insights

1. **Dominion is 99.97% data/artifacts, 0.03% source**
   - 7.57 GB → 2.53 MB by excluding non-source
   
2. **True source is tiny and token-efficient**
   - 589 files, 664K tokens (fits in 1M context easily)
   
3. **No deletions required**
   - All excluded files stay in repo
   - Only ignored for LLM context ingestion
   
4. **Selective JSON inclusion works**
   - Only schemas/feature lists kept
   - Not data artifacts (100s of MBs)
   
5. **`repo_map.md` is the best entry point**
   - 256 KB, 64K tokens
   - Full manifest with purposes
   - LLM can navigate to specific files as needed

---

## File Manifest Quick Reference

### Core Modules (Import Priority)
1. `domdata/` — MT5 data bridge (read-only)
2. `data_pipeline/` — feature engineering, data fusion, health monitoring
3. `model/` — training loop, cost-aware metrics, walk-forward validation
4. `tca/` — transaction cost attribution
5. `toxicity/` — order flow toxicity detection

### Key Scripts (Top 10)
1. `scripts/dominion_cli.py` — main CLI
2. `scripts/run_walk_forward_training.py` — backtest orchestrator
3. `scripts/build_master_dataset.py` — dataset builder
4. `scripts/expand_features_3k.py` — feature expansion (3K features)
5. `scripts/overnight_ensemble.py` — multi-model ensemble
6. `scripts/validate_master_dataset.py` — data quality checks
7. `scripts/regime_analysis.py` — market regime detection
8. `scripts/feature_stability.py` — feature drift monitoring
9. `scripts/dominion_health.py` — system health check
10. `scripts/codexrag.py` — RAGD query interface

### Tests (Critical)
1. `tests/training/test_labels.py` — triple-barrier label validation
2. `tests/training/test_splits.py` — walk-forward split safety
3. `tests/training/test_guardrails.py` — data quality gates
4. `domdata/tests/test_trading_blocked.py` — trading token safety

---

## Contact

- **Owners:** Matin, Dan
- **Questions:** See `QUICKSTART.md`, `AGENTS.md`
- **Issues:** Check `MORNING_CHECKLIST.md` for daily validation
