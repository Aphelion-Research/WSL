---
doc_type: architecture
system: Dominion
ragd_priority: 8
audience:
  - ai_agent
  - maintainer
  - owner
status: current
last_reviewed: 2026-05-19
tags:
  - architecture
  - repo-structure
  - file-layout
---

# Repository Structure

## Top-Level Layout

```
/home/Martin/Dominion/
├── .git/                   # Git version control
├── .venv/                  # Python virtual environment
├── secrets/                # NEVER INDEX, NEVER COMMIT
├── docs/                   # Documentation brain (this system)
├── vault/                  # Obsidian vault (878 notes)
├── reports/                # Historical agent reports
├── scripts/                # CLI tools + helpers
├── tests/                  # Repo-level tests
├── config/                 # Configuration files
├── data/                   # Market data storage (DuckDB)
├── logs/                   # Application logs
├── backups/                # Backup snapshots
├── models/                 # ML model storage
├── prompts/                # Agent prompt templates
├── notes/                  # Scratch notes
├── tmp/                    # Temporary files
│
├── ragd/                   # Native C++ RAGD core
├── domdata/                # MT5 data bridge
├── data_pipeline/          # Multi-source data pipeline
├── dominion_agent/         # Agent OS
├── dominion_ai/            # RAG retrieval
├── dominion_loader/        # Scan + manifest
├── research_os/            # Web crawler
│
├── lob/                    # LOB reconstruction
├── exec_sim/               # Execution simulator
├── tca/                    # Transaction cost analysis
├── toxicity/               # Toxicity monitoring
├── exec_features/          # Execution alpha features
│
├── ragd_embed/             # Embedding pipeline
├── ragd_hnsw/              # HNSW vector index
├── ragd_chunker/           # AST chunker
├── ragd_graph/             # Graph memory
├── ragd_vault/             # Vault operations
├── ragd_bus/               # Agent bus
│
├── AGENT_HANDOFF.md        # Current state (READ FIRST)
├── AGENTS.md               # Platform contract
├── README.md               # Repo overview
├── PROGRESS.md             # Historical log
├── QUICKSTART.md           # Quick start
├── requirements.txt        # Python dependencies
└── pytest.ini              # Test configuration
```

## File Naming Conventions

- **Python modules:** `lowercase_with_underscores.py`
- **C++ files:** `lowercase_with_underscores.cpp`, `.h`, `.hpp`
- **Docs:** `UPPERCASE_WITH_UNDERSCORES.md` (top-level), `Title_Case.md` (subsystem)
- **Tests:** `test_*.py` for Python, `test_*.cpp` for C++
- **CLI scripts:** `*_cli.py` for main entry points
- **Config:** `*.yaml`, `*.json`, `*.env` (secrets only)

## Critical Files (Do Not Delete)

| File | Purpose | Why Critical |
|---|---|---|
| `AGENT_HANDOFF.md` | Current state handoff | Agents read this first |
| `AGENTS.md` | Platform contract | Safety rules + workflow |
| `secrets/mt5.env` | MT5 credentials | Only way to connect to MT5 |
| `config/forbidden_tokens.json` | Trading token blocklist | Safety boundary |
| `data/dominion.duckdb` | Market data storage | All historical data |
| `ragd/build/ragd` | RAGD daemon binary | Memory system |
| `scripts/dominion_cli.py` | Unified CLI | Main interface |
| `vault/Home.md` | Vault entry point | Obsidian navigation |

## Ignore Patterns

From `.gitignore`:

```
__pycache__/
*.py[cod]
.venv/
.env
secrets/
*.duckdb
*.db
*.db-shm
*.db-wal
logs/
tmp/
backups/
*.bak
.DS_Store
.pytest_cache/
*.egg-info/
dist/
build/
*.o
*.so
*.exe
awscliv2.zip
```

From RAGD ignore policy:
- `secrets/`
- `__pycache__/`
- `.venv/`
- `.git/`
- `*.pyc`, `*.pyo`, `*.pyd`
- `*.db`, `*.db-shm`, `*.db-wal`
- `logs/`, `tmp/`, `backups/`

## Size Guidelines

- **Source files:** Prefer <500 lines per file
- **Docs:** Prefer <5000 words per file
- **Tests:** One test file per module
- **Data files:** Store in `data/`, not in repo
- **Binary files:** Avoid committing (use external storage)

## Growth Expectations

Current (2026-05-19):
- ~20k Python LOC
- 795 C++ files
- 33 docs (expanding to 150+)
- 878 vault notes
- 7159 RAGD chunks

6-month projection:
- ~30k Python LOC
- 1000+ C++ files
- 150+ docs
- 2000+ vault notes
- 20,000+ RAGD chunks

## Backup Strategy

- **Code:** Git version control + GitHub
- **Data:** `backups/` folder (periodic snapshots)
- **Vault:** Git-tracked markdown files
- **RAGD DB:** Periodic SQLite dumps
- **Secrets:** NOT backed up (owner responsibility)

## Retrieval Hints

- "repo structure"
- "where are files located"
- "file naming conventions"
- "what to ignore"
- "critical files"
