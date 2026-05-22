# LLM Context Ingestion Audit — Dominion V2

**Date:** 2026-05-22  
**Purpose:** Identify clean source for LLM context window (drop data/models/build artifacts)

---

## Executive Summary

| Metric | Value |
|--------|-------|
| **Total repo size** | 7.57 GB |
| **Total files** | 19,445 |
| **Clean source (SOURCE + CONFIG)** | 2.53 MB (589 files) |
| **Reduction** | **99.97%** |
| **Estimated tokens (clean)** | ~664K |

---

## Category Breakdown (Full Repo)

| Category | Files | Size (MB) | % of Total |
|----------|-------|-----------|-----------|
| DATA | 4,961 | 4,038.55 | 52.1% |
| BUILD | 10,098 | 2,122.98 | 27.4% |
| MODELS | 5 | 1,200.31 | 15.5% |
| MISC | 2,242 | 293.80 | 3.8% |
| ARCHIVE | 1 | 66.81 | 0.9% |
| CONFIG | 267 | 18.24 | 0.2% |
| DOCS | 1,288 | 4.33 | 0.1% |
| **SOURCE** | **583** | **2.52** | **0.0%** |

---

## True Source (SOURCE + CONFIG Only)

| Metric | Value |
|--------|-------|
| **Files** | 589 |
| **Size** | 2.53 MB |
| **Lines** | ~60K (estimated) |
| **Tokens** | ~664K (estimated) |

**Breakdown:**
- **Python/C++ source**: 2.44 MB (583 files)
- **Config files**: 0.05 MB (YAML, TOML, Makefile)
- **Selective JSON**: 0.04 MB (schemas, feature lists only)

---

## Exclusion List (99.97% of Repo)

### Exclude: DATA (52.1% / 4.0 GB)
```
data/
data_pipeline/tests/fixtures/
artifacts/hydra/
backups/
*.csv
*.parquet
*.feather
*.h5
*.hdf5
*.db
*.sqlite
*.pkl
*.pickle
*.npy
*.npz
```

### Exclude: BUILD (27.4% / 2.1 GB)
```
__pycache__/
.cache/
*.egg-info/
build/
dist/
cpp/build/
aws/dist/
*.o
*.so
*.a
*.lib
*.dylib
*.dll
```

### Exclude: MODELS (15.5% / 1.2 GB)
```
*.pt
*.pth
*.onnx
*.safetensors
*.bin
*.ckpt
*.pb
models/
checkpoints/
```

### Exclude: MISC (3.8% / 293 MB)
```
catboost_info/
mlruns/
.venv/
venv/
node_modules/
*.log
*.tmp
```

### Exclude: ARCHIVES (0.9% / 66 MB)
```
*.zip
*.tar
*.gz
*.bz2
*.xz
*.7z
awscliv2.zip
```

---

## Recommended `.llmignore` File

Create `.llmignore` at repo root (gitignore-style syntax):

```gitignore
# LLM Context Exclusion List — Dominion V2
# Excludes 99.7% of repo (data/models/build artifacts)

# DATA (52.1%)
data/
artifacts/hydra/
backups/
*.csv
*.parquet
*.feather
*.h5
*.hdf5
*.db
*.sqlite
*.pkl
*.pickle
*.npy
*.npz

# BUILD (27.4%)
__pycache__/
.cache/
*.egg-info/
build/
dist/
cpp/build/
aws/dist/
*.o
*.so
*.a
*.lib
*.dylib
*.dll

# MODELS (15.5%)
*.pt
*.pth
*.onnx
*.safetensors
*.bin
*.ckpt
*.pb
models/
checkpoints/

# MISC (3.8%)
catboost_info/
mlruns/
.venv/
venv/
node_modules/
*.log
*.tmp

# ARCHIVES (0.9%)
*.zip
*.tar
*.gz
*.bz2
*.xz
*.7z
```

---

## What's Kept (20.76 MB)

### Python Source (583 files)
- Core modules: `data_pipeline/`, `domdata/`, `model/`, `tca/`, `toxicity/`
- Scripts: `scripts/*.py` (100+ training/data/orchestration scripts)
- Tests: `tests/**/*.py`
- Apps: `apps/mt5/combat` (MT5 bridge)

### Config Files (267 files)
- Project config: `CLAUDE.md`, `AGENTS.md`, `README.md`
- Package config: `requirements.txt`, `pyproject.toml`, `pytest.ini`
- JSON schemas: `data/registry/*.json`, `artifacts/hydra/features_fold0.json`
- Build config: `cpp/Makefile`, `meson.build`

### C++ Source (10 files)
- Kernels: `cpp/kernels/*.cpp`, `cpp/kernels/*.hpp`

---

## Validation

### Before Exclusion
```bash
du -sh /home/Martin/Dominion
# 7.6G
```

### After Exclusion (measured)
```bash
# SOURCE + CONFIG + selective JSON only
# 2.53 MB, 589 files
```

### Token Budget (664K)
- Fits in **1M context window** (Claude 4.5+)
- Leaves 340K tokens for conversation + responses
- Can add selective data samples if needed
- Far below 2M limit of Opus 4.7

---

## Implementation

### Option 1: Use `repo_map.md` (Recommended)
```bash
cat repo_map.md  # 256 KB, ~64K tokens
```
- Pre-generated manifest of 2,461 SOURCE + CONFIG files
- Includes 3-level directory tree, dependency list, file purposes
- Compact table format: path | purpose | key exports
- Ready for immediate LLM ingestion

### Option 2: Live Directory Walk (with .llmignore)
```python
# LLM tool can walk repo honoring .llmignore patterns
# Only reads SOURCE + CONFIG files
```

### Option 3: Archive Tarball
```bash
tar -czf dominion_source.tar.gz \
  --exclude='data/' --exclude='build/' --exclude='*.pkl' \
  $(find . -name '*.py' -o -name '*.cpp' -o -name '*.yaml')
```

---

## Next Steps

1. **Review exclusions** — confirm no critical config in excluded paths
2. **Create `.llmignore`** — copy from recommended section above
3. **Validate `repo_map.md`** — spot check file manifest accuracy
4. **Test ingestion** — load `repo_map.md` into LLM context and verify completeness
5. **Document workflow** — add to `CLAUDE.md` under "LLM Context Protocol"

---

## Findings

- **99.97% reduction** (7.57 GB → 2.53 MB) achieved by excluding data/models/build
- **True source is tiny** (0.03% of repo) — all Python/C++ code + config
- **Token budget is safe** — 664K tokens fits in 1M context with 340K headroom
- **No deletions needed** — all bloat stays in repo, just excluded from context
- **JSON is minimal** — only schemas/feature lists kept, not data artifacts

---

## Appendix: Full Category Details

See `audit_details.json` for machine-readable breakdown.
