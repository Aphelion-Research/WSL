---
doc_type: quickstart
system: Dominion
ragd_priority: 8
audience:
  - ai_agent
  - maintainer
  - owner
status: current
last_reviewed: 2026-05-19
tags:
  - quickstart
  - getting-started
---

# Dominion Quick Start

**For Humans:** Read [HUMAN_README.md](../HUMAN_README.md)  
**For AI Agents:** Read [AGENT_README.md](../AGENT_README.md)  
**For System Overview:** Read [OVERVIEW.md](OVERVIEW.md)

---

## 60-Second Orientation

Dominion V2 = local-first quant research workstation.

**Core layers:**
1. **RAGD:** Persistent memory (7159 chunks)
2. **domdata:** MT5 data bridge (read-only)
3. **Data Pipeline:** 5 sources + 400+ features
4. **Microstructure:** LOB/Exec/TCA/Toxicity/Features
5. **Agent OS:** AI agent safety + lifecycle
6. **Vault:** 878-note Obsidian knowledge graph

**Status:** SOURCE_GREEN | LIVE_WARN (24 C++ tests passing, RAGD chunker/embed config incomplete)

---

## Validation (30 seconds)

```bash
cd ~/Dominion
python domdata/check_no_trading.py  # MUST output "PASS"
python scripts/dominion_cli.py doctor --json  # Check overall status
curl 127.0.0.1:7474/health          # Should output {"status":"ok"}
```

If `doctor` shows `overall: ok` → system is fully healthy.
If `doctor` shows `overall: warn` → check which subsystems need attention.

---

## Key Commands

```bash
# Platform health
dominion status                     # Quick status
dominion doctor --offline --json    # Health check
bash scripts/verify_live.sh         # Full validation (14 checks)

# RAGD operations
dominion search "agent workflow" --top-k 5
dominion ask "how does data pipeline work"
dominion trace <trace_id>

# Data pipeline
python -m data_pipeline.cli run
python -m data_pipeline.cli status
python -m data_pipeline.cli doctor
python -m data_pipeline.cli report

# Microstructure
python -m lob.cli compute
python -m exec_sim.cli run
python -m tca.cli analyze
python -m toxicity.cli compute
python -m exec_features.cli compute

# Vault
dominion vault status
dominion vault doctor --json

# Agent OS
dominion agent dashboard --json
dominion agent next --json

# Testing
python -m pytest -q                                    # All Python tests
ctest --test-dir ragd/build --output-on-failure        # All C++ tests
python domdata/check_no_trading.py                     # Trading safety
```

---

## First-Time Setup (Humans)

```bash
cd ~/Dominion
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
./scripts/bootstrap_python.sh
```

Verify:
```bash
python -m pytest -q  # Should pass
python domdata/check_no_trading.py  # Should pass
```

---

## First-Time Orientation (AI Agents)

1. **Read handoff:** `cat /home/Martin/Dominion/AGENT_HANDOFF.md`
2. **Query RAGD:** `python scripts/dominion_cli.py search "agent workflow" --top-k 5`
3. **Read agent manual:** `cat /home/Martin/Dominion/docs/AGENT_README.md`
4. **Understand workflow:** Read `docs/03_AGENT_OPERATIONS/AGENT_OPERATING_SYSTEM.md`
5. **Learn safety rules:** Read `docs/09_RISK_AND_SECURITY/AGENT_SAFETY_RULES.md`

---

## Common Tasks

### Task: Check Platform Health

```bash
bash scripts/verify_live.sh  # 14/14 checks should pass
```

### Task: Run Tests

```bash
python -m pytest -q
```

### Task: Query RAGD

```bash
python scripts/dominion_cli.py search "data pipeline" --top-k 5 --json
```

### Task: Update Documentation

```bash
# Edit docs/...
python scripts/dominion_cli.py vault doctor --json  # Check links
python scripts/dominion_cli.py scan  # Rebuild RAGD index
```

### Task: Add Feature

See [03_AGENT_OPERATIONS/AGENT_WORKFLOW.md](../03_AGENT_OPERATIONS/AGENT_WORKFLOW.md)

---

## Troubleshooting

### Tests Fail

```bash
# Check which tests fail
python -m pytest -v

# Run specific test
python -m pytest -v path/to/test.py::test_name
```

### RAGD Unreachable

```bash
# Check RAGD health
curl 127.0.0.1:7474/health

# Check tmux session
tmux attach -t ragd

# Restart RAGD (if needed)
pkill ragd
ragd/build/ragd --db data/ragd.db --host 127.0.0.1 --port 7474 --daemon
```

### Trading Check Fails

1. STOP immediately
2. Do NOT commit
3. Find trading code:
   ```bash
   grep -r "order_send\|order_check\|TRADE_ACTION" .
   ```
4. Remove trading code
5. Re-run check

---

## Next Steps

**Humans:**
- Browse [docs/INDEX.md](../INDEX.md) for full documentation
- Open Obsidian vault at `/home/Martin/Dominion/vault/`
- Read [06_ROADMAP/MASTER_ROADMAP.md](../06_ROADMAP/MASTER_ROADMAP.md) for future plans

**Agents:**
- Read [AGENT_README.md](../AGENT_README.md) completely
- Follow [AGENT_OPERATING_SYSTEM.md](../03_AGENT_OPERATIONS/AGENT_OPERATING_SYSTEM.md) workflow
- Query RAGD before every code change

---

## Resources

| Resource | Location |
|---|---|
| Repo Root | `/home/Martin/Dominion/` |
| Documentation | `docs/` |
| Vault | `vault/` |
| RAGD API | `http://127.0.0.1:7474/` |
| Main CLI | `python scripts/dominion_cli.py` |
| Data Pipeline | `python -m data_pipeline.cli` |
| Tests | `python -m pytest -q` |

---

**Status:** LIVE_GREEN ✓  
**Last Validated:** 2026-05-19  
**Next Review:** When new features added
