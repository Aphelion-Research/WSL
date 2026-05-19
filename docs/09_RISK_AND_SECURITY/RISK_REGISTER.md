---
doc_type: safety
system: Dominion
ragd_priority: 8
audience:
  - ai_agent
  - maintainer
  - owner
  - auditor
status: current
last_reviewed: 2026-05-19
tags:
  - risk
  - security
  - safety
---

# Risk Register

**Purpose:** Catalog of known risks and mitigation strategies.

---

## Critical Risks (P0)

### R001: Trading Code Execution

**Risk:** Agent or human adds trading execution code.

**Impact:** CRITICAL — Could place real orders, lose money.

**Likelihood:** Low (multiple safeguards)

**Mitigation:**
- Forbidden token scanner blocks trading functions
- MT5 investor account (read-only)
- CLI guards block order commands
- Agent OS safety rules enforce no-trading
- Pre-commit hooks run trading check

**Detection:**
```bash
python domdata/check_no_trading.py
```

**Response:** STOP immediately, remove trading code, re-validate.

**Status:** Mitigated

---

### R002: Secret Leakage

**Risk:** Secrets committed to git or printed in logs.

**Impact:** CRITICAL — Compromised credentials, unauthorized access.

**Likelihood:** Low (multiple safeguards)

**Mitigation:**
- `secrets/` folder in .gitignore
- RAGD ignores `secrets/`
- Vault ignores `secrets/`
- Agent safety rules forbid reading secret contents
- Pre-commit hooks check for common secret patterns

**Detection:**
```bash
git log --all -- secrets/
grep -r "password\|api_key\|secret" docs/ logs/
```

**Response:** Remove from git history (`git filter-repo`), rotate secrets.

**Status:** Mitigated

---

## High Risks (P1)

### R003: RAGD Index Corruption

**Risk:** RAGD database corrupted or out of sync.

**Impact:** HIGH — Wrong context loaded, agents make bad decisions.

**Likelihood:** Medium (active development)

**Mitigation:**
- Periodic RAGD backups
- Content hash validation (detect stale chunks)
- Doctor checks for orphan chunks
- Rebuild capability (`dominion scan`)

**Detection:**
```bash
python scripts/dominion_cli.py doctor --deep --json
```

**Response:** Rebuild RAGD index from source files.

**Status:** Partially mitigated (need automated backups)

---

### R004: Stale Documentation

**Risk:** Docs diverge from code, mislead agents.

**Impact:** HIGH — Agents break systems based on wrong info.

**Likelihood:** High (rapid development)

**Mitigation:**
- `last_reviewed` date in frontmatter
- Doctor checks for stale docs (>90 days)
- ADRs for architectural changes
- Agent reports document changes

**Detection:**
```bash
find docs/ -name "*.md" -exec grep -L "last_reviewed: 2026" {} \;
```

**Response:** Review and update stale docs, mark as deprecated if obsolete.

**Status:** Partially mitigated (need automated staleness detection)

---

### R005: Platform Health Degradation

**Risk:** Tests fail, health checks fail, platform broken.

**Impact:** HIGH — Can't develop safely, may corrupt data.

**Likelihood:** Medium (complex system)

**Mitigation:**
- Comprehensive test suite (426 Python + 24 C++)
- Doctor checks (offline + live)
- Validation before every commit
- LIVE_GREEN status tracking

**Detection:**
```bash
python -m pytest -q
python scripts/dominion_cli.py doctor --offline --json
bash scripts/verify_live.sh
```

**Response:** Fix failing checks immediately, don't proceed until LIVE_GREEN.

**Status:** Mitigated

---

### R006: Agent Overreach

**Risk:** Agent makes large, risky changes without approval.

**Impact:** HIGH — Data loss, broken systems, wasted work.

**Likelihood:** Medium (depends on agent quality)

**Mitigation:**
- Agent OS safety rules (no destructive ops without approval)
- Adversary reviews agent output
- Complexity budgets limit change scope
- File locking prevents concurrent edits
- Human review of agent reports

**Detection:**
- Review agent diffs before merge
- Check agent report quality score
- Monitor complexity budget violations

**Response:** Revert unsafe changes, improve agent prompts, add safety rules.

**Status:** Partially mitigated (need more automated checks)

---

## Medium Risks (P2)

### R007: Performance Regression

**Risk:** New code slows down critical paths.

**Impact:** MEDIUM — Slower development, worse UX.

**Likelihood:** Medium (optimization not always priority)

**Mitigation:**
- Benchmarks for critical paths (scan, query, tests)
- Performance checks in QA checklist
- Profiling when slowness suspected

**Detection:**
```bash
# Native scan should be <50ms
time ragd/build/dominion-native-scan --root . --json

# RAGD query should be <100ms p95
time dominion search "test" --top-k 5

# Tests should be <20s
time python -m pytest -q
```

**Response:** Profile, optimize, or document as known limitation.

**Status:** Partially mitigated (need automated benchmarks)

---

### R008: Dependency Vulnerabilities

**Risk:** Vulnerable dependencies (CVEs).

**Impact:** MEDIUM — Security vulnerabilities, potential exploits.

**Likelihood:** Medium (dependencies update frequently)

**Mitigation:**
- Pin dependency versions in requirements.txt
- Periodic dependency updates
- Check for CVEs before adding new deps

**Detection:**
```bash
pip list --outdated
pip-audit  # If installed
```

**Response:** Update vulnerable deps, test thoroughly, commit.

**Status:** Partially mitigated (need automated CVE scanning)

---

### R009: Broken Obsidian Links

**Risk:** Vault links break, navigation fails.

**Impact:** MEDIUM — Poor UX, hard to find docs.

**Likelihood:** High (active doc development)

**Mitigation:**
- Vault doctor checks links
- Cross-link validation in CI (if configured)

**Detection:**
```bash
python scripts/dominion_cli.py vault doctor --json
```

**Response:** Fix broken links, update references.

**Status:** Mitigated (vault doctor operational)

---

### R010: RAGD Daemon Downtime

**Risk:** RAGD daemon crashes or becomes unreachable.

**Impact:** MEDIUM — Agents can't load context, development blocked.

**Likelihood:** Low (daemon is stable)

**Mitigation:**
- Run in tmux (survives shell exit)
- Health check endpoint
- Restart instructions in docs

**Detection:**
```bash
curl http://127.0.0.1:7474/health
```

**Response:** Restart daemon, check logs for root cause.

**Status:** Mitigated

---

## Low Risks (P3)

### R011: Test Flakiness

**Risk:** Tests sometimes fail randomly.

**Impact:** LOW — Wastes time, reduces confidence.

**Likelihood:** Low (tests are deterministic)

**Mitigation:**
- Avoid time-dependent tests
- Use temp files/databases
- Clean up after tests

**Detection:** Run tests multiple times, check for inconsistency.

**Response:** Fix flaky tests immediately.

**Status:** Mitigated

---

### R012: Large Files in Git

**Risk:** Accidentally commit large files (data, binaries).

**Impact:** LOW — Bloated repo, slow clones.

**Likelihood:** Low (.gitignore covers most)

**Mitigation:**
- .gitignore for common patterns (*.duckdb, *.db, data/)
- Pre-commit hooks check file sizes

**Detection:**
```bash
git ls-files | xargs du -h | sort -hr | head -20
```

**Response:** Remove from git history (`git filter-repo`), add to .gitignore.

**Status:** Mitigated

---

### R013: Orphan RAGD Chunks

**Risk:** Deleted files leave orphan chunks in RAGD.

**Impact:** LOW — Stale chunks pollute retrieval, waste storage.

**Likelihood:** High (active development)

**Mitigation:**
- RAGD soft-delete on file removal
- Doctor checks for orphans
- Periodic cleanup

**Detection:**
```bash
python scripts/dominion_cli.py doctor --deep --json | grep orphan
```

**Response:** Run cleanup script or rebuild RAGD index.

**Status:** Known issue (1600 orphan chunks exist, cleanup planned)

---

## Risk Matrix

| Risk | Impact | Likelihood | Priority | Status |
|---|---|---|---|---|
| R001: Trading code | Critical | Low | P0 | Mitigated |
| R002: Secret leakage | Critical | Low | P0 | Mitigated |
| R003: RAGD corruption | High | Medium | P1 | Partial |
| R004: Stale docs | High | High | P1 | Partial |
| R005: Health degradation | High | Medium | P1 | Mitigated |
| R006: Agent overreach | High | Medium | P1 | Partial |
| R007: Performance regression | Medium | Medium | P2 | Partial |
| R008: Dependency CVEs | Medium | Medium | P2 | Partial |
| R009: Broken links | Medium | High | P2 | Mitigated |
| R010: RAGD downtime | Medium | Low | P2 | Mitigated |
| R011: Test flakiness | Low | Low | P3 | Mitigated |
| R012: Large files | Low | Low | P3 | Mitigated |
| R013: Orphan chunks | Low | High | P3 | Known issue |

---

## Risk Treatment Plan

### Q3 2026 (Immediate)

- [ ] Add automated RAGD backups (R003)
- [ ] Add staleness detection (R004)
- [ ] Add automated agent safety checks (R006)
- [ ] Clean up orphan chunks (R013)

### Q4 2026

- [ ] Add automated CVE scanning (R008)
- [ ] Add automated benchmarks (R007)
- [ ] Add performance regression tests (R007)

### 2027

- [ ] Add chaos engineering tests (R003, R005)
- [ ] Add automated security audits (R001, R002, R008)
- [ ] Add multi-agent coordination safety (R006)

---

## Related Docs

- [AGENT_SAFETY_RULES.md](AGENT_SAFETY_RULES.md)
- [FAILURE_MODES.md](FAILURE_MODES.md)
- [SECURITY_NOTES.md](SECURITY_NOTES.md)
- [DATA_SAFETY.md](DATA_SAFETY.md)

---

## Retrieval Hints

- "risk"
- "what can go wrong"
- "known risks"
- "risk mitigation"
- "security risks"
