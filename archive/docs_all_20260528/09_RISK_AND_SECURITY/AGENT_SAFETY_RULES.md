---
doc_type: safety
system: Dominion
ragd_priority: 10
audience:
  - ai_agent
status: current
last_reviewed: 2026-05-19
tags:
  - safety
  - security
  - agent
  - rules
---

# Agent Safety Rules

**CRITICAL:** All AI agents MUST follow these rules.

---

## Rule 1: No Trading Execution

**FORBIDDEN:**
- `MetaTrader5.order_send()`
- `MetaTrader5.order_check()`
- `TRADE_ACTION_DEAL`
- `TRADE_ACTION_PENDING`
- `POSITION_CLOSE`
- Any code that places, modifies, or closes orders

**ALLOWED:**
- `MetaTrader5.symbol_info()` (read-only)
- `MetaTrader5.copy_ticks_from()` (read-only)
- `MetaTrader5.copy_rates_from()` (read-only)
- Analysis, backtesting, simulation (no real orders)

**Validation:**
```bash
python domdata/check_no_trading.py  # MUST output "PASS"
```

**If check fails:**
1. STOP immediately
2. Do NOT commit
3. Remove ALL trading-related code
4. Run check again
5. Only proceed when check passes

---

## Rule 2: No Secret Leakage

**FORBIDDEN:**
- Reading `secrets/` folder contents
- Printing secret values
- Logging secrets
- Committing secrets to git
- Indexing secrets in RAGD
- Documenting secret values
- Copying secrets to clipboard

**ALLOWED:**
- Checking if `secrets/mt5.env` exists (boolean check only)
- Checking `secrets/` folder permissions
- Reading secret keys from environment variables (not printing values)

**Affected files:**
- `secrets/mt5.env` — MT5 credentials
- `secrets/*.key` — API keys
- `secrets/*.json` — Service credentials

**Detection:**
```bash
# Check if secrets leaked to git
git log --all -- secrets/

# Check if secrets in docs
grep -r "password\|secret\|credential" docs/
```

---

## Rule 3: No Destructive Operations Without Explicit Request

**FORBIDDEN (unless explicitly requested):**
- Deleting files
- Dropping database tables
- Killing processes
- `rm -rf`
- Overwriting uncommitted changes
- Force-pushing git
- Resetting git history
- Removing branches
- Deleting backups

**REQUIRED before destructive op:**
1. Confirm with human
2. Create backup if possible
3. Document why necessary
4. Provide undo instructions

---

## Rule 4: Preserve Working Systems

**CRITICAL SYSTEMS (do not break):**
- **domdata** — Only MT5 data source
- **RAGD daemon** — All agent context depends on it
- **Data pipeline** — All market data flows through it
- **Agent OS** — Safety and lifecycle management
- **Native core** — Performance-critical operations
- **Vault** — Knowledge graph integrity

**Validation before claiming success:**
```bash
python domdata/check_no_trading.py  # PASS
domdata xautick                     # Should return tick data
curl 127.0.0.1:7474/health          # {"status":"ok"}
python -m pytest -q                 # All tests pass
ctest --test-dir ragd/build         # All C++ tests pass
```

**If you break a critical system:**
1. Update `/AGENT_HANDOFF.md` with BROKEN status
2. Document what broke + how
3. Attempt revert to working state
4. Write incident report
5. Ask human for help

---

## Rule 5: Test Before Claiming Success

**MANDATORY validation:**
```bash
# Core validation (MUST PASS)
python domdata/check_no_trading.py
python -m pytest -q
ctest --test-dir ragd/build --output-on-failure  # If C++ changed

# Platform validation (RECOMMENDED)
bash scripts/verify_live.sh
python scripts/dominion_cli.py doctor --offline --json
python scripts/dominion_cli.py vault doctor --json
```

**Do NOT:**
- Skip tests
- Disable failing tests
- Claim "tests probably pass"
- Assume behavior without testing

---

## Rule 6: Make Minimal Diffs

**Prefer:**
- Small, focused changes
- One feature at a time
- Editing existing files over creating new ones
- Using existing patterns
- Incremental changes

**Avoid:**
- Massive rewrites
- "While I'm here" refactoring
- Changing unrelated code
- Creating duplicate functionality
- Over-engineering simple tasks

---

## Rule 7: Document Everything

**MANDATORY documentation:**
- Update `/AGENT_HANDOFF.md` after significant changes
- Update relevant docs in `docs/`
- Write report in `reports/`
- Add comments for non-obvious code
- Write ADR for architectural decisions

**Do NOT:**
- Make undocumented changes
- Leave handoff stale
- Skip report writing
- Assume next agent will understand

---

## Rule 8: Handle Errors Gracefully

**Best practices:**
- Fail closed, not open
- Log errors clearly
- Don't swallow exceptions
- Provide actionable error messages
- Validate inputs at boundaries

**Avoid:**
- Silent failures
- Generic error messages ("Error occurred")
- Swallowing exceptions with bare `except:`
- Continuing after critical errors

---

## Rule 9: No Security Vulnerabilities

**Check for:**
- Command injection
- SQL injection
- Path traversal
- XSS (if web UI added)
- Insecure deserialization
- OWASP Top 10 violations

**Validation:**
```bash
# Check for obvious vulnerabilities
grep -r "eval(" .
grep -r "exec(" .
grep -r "os.system(" .
grep -r "subprocess.call(.*shell=True" .
```

---

## Rule 10: Query RAGD Before Code Changes

**MANDATORY:**
```bash
# Query RAGD for task context
python scripts/dominion_cli.py search "<your task>" --top-k 5 --json

# Or via Python
from ragd.scripts.ragd_mcp_stdio import ragd_query
result = ragd_query("<task description>", top_k=5)
```

**Why:**
- Avoid duplicating existing solutions
- Learn from past agent decisions
- Understand current architecture
- Prevent breaking working systems
- Follow established patterns

**Do NOT:**
- Skip RAGD query
- Assume you know the codebase
- Hallucinate repo behavior
- Ignore retrieval results

---

## Safety Violation Response

**If you detect a safety violation:**
1. STOP immediately
2. Document the violation
3. Update `/AGENT_HANDOFF.md` with status: BROKEN
4. Revert unsafe changes
5. Run validation again
6. Write incident report
7. Ask human for guidance

**If another agent created the violation:**
1. Document in backlog or incident report
2. Do NOT propagate the violation
3. Fix if possible (following these rules)
4. Otherwise, escalate to human

---

## Checklist

Before claiming task complete:

- [ ] No trading execution code
- [ ] No secrets leaked
- [ ] No destructive ops without request
- [ ] Critical systems still work
- [ ] All tests pass
- [ ] Trading check passes
- [ ] Minimal diffs only
- [ ] Docs updated
- [ ] Errors handled gracefully
- [ ] No security vulnerabilities
- [ ] Queried RAGD before changes
- [ ] Handoff updated
- [ ] Report written

---

## Enforcement

These rules are enforced by:
- **Forbidden token scanner:** `domdata/check_no_trading.py`
- **Agent OS:** `dominion_agent/safety.py`
- **Adversary:** `dominion_agent/adversary.py`
- **Test suite:** 426 Python + 24 C++ tests
- **Platform health:** `dominion doctor` checks
- **Human review:** Final approval gate

---

## Related Docs

- [AGENT_README.md](../AGENT_README.md) — Agent operating manual
- [AGENT_OPERATING_SYSTEM.md](../03_AGENT_OPERATIONS/AGENT_OPERATING_SYSTEM.md) — Workflow
- [RISK_REGISTER.md](RISK_REGISTER.md) — Known risks
- [FAILURE_MODES.md](FAILURE_MODES.md) — What can go wrong

---

## Retrieval Hints

- "safety rules"
- "agent safety"
- "what agents must not do"
- "forbidden operations"
- "trading execution rules"
- "secret protection"
