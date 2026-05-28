# Repository Cleanup - 2026-05-28

## Goal
Single-path codebase for Citadel terminal foundation.

## Changes

### Scripts (8 kept, 100 archived)
**Kept:**
- `him_live_tui.py` - Live TUI for manual trading
- `train_him_profit_max.py` - Model training
- `test_him_profit_max.py` - Model validation
- `test_him_tui_once.py` - TUI test
- `dominion_cli.py` - CLI interface
- `dominion_health.py` - Health checks
- `dominion_ui.py` - UI components
- `codexrag.py` - RAG system

**Archived:** 100 experimental/obsolete scripts → `archive/scripts_20260528/`

### Models
**Active:** `output_him_v2/him_profit_max.json` (profitable at prop firm costs)

**Archived:**
- All Him V2 variants → `archive/output_him_v2_old_20260528/`
- All other model outputs → `archive/output_*/`
- Models registry → `archive/models_old_20260528/`

### Data
**Kept:** `data/mt5_history/` (active MT5 feed via domdata)

**Archived:** All experimental datasets (5GB) → `archive/data_old_20260528/`
- HYDRA datasets
- Cross-asset data
- Crypto/macro/alternative data
- Feature fabric experiments

### Documentation
**Kept:**
- `README.md` - Project overview
- `CLAUDE.md` - AI agent config
- `AGENTS.md` - Platform contracts
- `HIM_PROFIT_MAX_RESULTS.md` - Latest profitable model

**Archived:**
- All research reports → `archive/docs_old_20260528/`
- Entire docs/ tree → `archive/docs_all_20260528/`

## Core Structure Remaining

```
Dominion/
├── research_core/          # Validation foundation (keep)
│   ├── execution/          # Backtesting simulator
│   ├── data_contracts/     # Point-in-time validation
│   └── __init__.py
├── scripts/                # 8 core scripts only
├── output_him_v2/          # him_profit_max.json only
├── data/mt5_history/       # Active MT5 data
├── domdata/                # MT5 bridge (keep)
└── archive/                # Everything else

README.md
CLAUDE.md
AGENTS.md
HIM_PROFIT_MAX_RESULTS.md
```

## Single Path Achieved

**Before:** 128 scripts, 21 output dirs, 170 docs, 5GB data sprawl
**After:** 8 scripts, 1 model, 1 data source, 4 docs

**Next:** Build Citadel terminal on this foundation.
