---
doc_type: testing
system: Dominion
ragd_priority: 7
audience:
  - ai_agent
  - maintainer
status: current
last_reviewed: 2026-05-19
tags:
  - testing
  - qa
  - checklist
---

# QA Checklist

**Purpose:** Pre-release validation checklist.

---

## Before Every Release

### 1. Core Validation (MANDATORY)

- [ ] All Python tests pass: `python -m pytest -q` → 426+ passed
- [ ] All C++ tests pass: `ctest --test-dir ragd/build` → 24/24 passed
- [ ] Trading check: `python domdata/check_no_trading.py` → PASS
- [ ] Platform health: `dominion doctor --offline --json` → overall: warn or ok

### 2. Integration Tests

- [ ] RAGD daemon reachable: `curl 127.0.0.1:7474/health` → {"status":"ok"}
- [ ] RAGD query works: `dominion search "test" --top-k 3` → 3 results
- [ ] Data pipeline runs: `python -m data_pipeline.cli status` → no errors
- [ ] Vault integrity: `dominion vault doctor --json` → ok: true, 0 broken links

### 3. Safety Checks

- [ ] No trading code: grep for forbidden tokens → clean
- [ ] No secrets leaked: check git diffs → clean
- [ ] No hardcoded credentials: grep for passwords → clean
- [ ] File permissions: `ls -la secrets/` → 600 or 700

### 4. Performance Checks

- [ ] Native scan: <50ms for 1500 files
- [ ] RAGD query: <100ms p95
- [ ] Test suite: <20 seconds total
- [ ] No obvious performance regressions

### 5. Documentation

- [ ] AGENT_HANDOFF.md updated with current state
- [ ] README.md reflects current features
- [ ] New features documented in docs/05_FEATURES/
- [ ] Breaking changes noted in CHANGELOG (if exists)

### 6. Code Quality

- [ ] No commented-out code (except documented TODOs)
- [ ] No `print()` statements in production code
- [ ] No bare `except:` clauses
- [ ] Type hints on public functions
- [ ] Docstrings on non-trivial functions

### 7. Git Hygiene

- [ ] All commits follow conventional format
- [ ] No secrets in git history
- [ ] No merge conflicts
- [ ] Branch up to date with main

---

## Before Major Release (Phase Completion)

### 8. Extended Testing

- [ ] Run full test suite with coverage: `pytest --cov`
- [ ] Coverage >80% for critical modules
- [ ] Integration tests with real RAGD daemon
- [ ] Manual smoke testing of key workflows

### 9. Performance Benchmarks

- [ ] Run performance benchmarks
- [ ] Compare against baseline
- [ ] Document any regressions
- [ ] Profile if >10% slower

### 10. Security Audit

- [ ] No command injection vulnerabilities
- [ ] No SQL injection vulnerabilities
- [ ] No path traversal vulnerabilities
- [ ] Dependencies up to date (check for CVEs)
- [ ] Secrets management validated

### 11. Documentation Audit

- [ ] All docs have recent last_reviewed date
- [ ] No broken links in docs/
- [ ] Vault doctor reports 0 broken links
- [ ] RAGD_INGESTION_MANIFEST up to date

### 12. User Experience

- [ ] Error messages are clear
- [ ] CLI help text is accurate
- [ ] Validation commands work
- [ ] Example commands in docs are correct

---

## Before Public Release (If Applicable)

### 13. External Validation

- [ ] Third-party review (if available)
- [ ] Security audit by external auditor
- [ ] Load testing
- [ ] Stress testing

### 14. Legal

- [ ] License file present and correct
- [ ] No license violations in dependencies
- [ ] Attribution for third-party code
- [ ] No proprietary code included

### 15. Packaging

- [ ] README.md has clear installation instructions
- [ ] requirements.txt is complete
- [ ] Setup script works on fresh install
- [ ] Docker image builds (if applicable)

---

## Post-Release

### 16. Monitoring

- [ ] Check logs for errors
- [ ] Monitor RAGD health
- [ ] Check test results on main
- [ ] Verify no regressions reported

### 17. Documentation

- [ ] Update AGENT_HANDOFF.md with release status
- [ ] Write release report in reports/
- [ ] Update PROGRESS.md with milestone
- [ ] Tag release in git (if applicable)

---

## Checklist by Role

### Agent QA

- [ ] Core validation (tests, trading check, health)
- [ ] Safety checks (no trading, no secrets)
- [ ] Documentation updated
- [ ] Agent report written

### Maintainer QA

- [ ] Core validation
- [ ] Integration tests
- [ ] Performance checks
- [ ] Code quality
- [ ] Extended testing
- [ ] Security audit

### Owner QA

- [ ] All above
- [ ] User experience validation
- [ ] External review (if available)
- [ ] Legal compliance
- [ ] Post-release monitoring

---

## Emergency Release Checklist (Hotfix)

For critical bugs requiring immediate fix:

- [ ] Tests pass (at minimum: affected subsystem)
- [ ] Trading check passes
- [ ] No new security vulnerabilities
- [ ] Git commit documents urgency
- [ ] AGENT_HANDOFF.md updated
- [ ] Brief report written

**Skip** (defer to next regular release):
- Documentation audit
- Performance benchmarks
- Extended testing

---

## Failure Response

**If checklist fails:**

1. **Document failure:**
   - What check failed
   - Error output
   - Context

2. **Fix issue:**
   - Identify root cause
   - Apply fix
   - Re-run checklist

3. **Verify fix:**
   - All checks pass
   - No regressions introduced

4. **Document fix:**
   - Update handoff
   - Note in report

**Do NOT:**
- Skip failing checks
- Release with known failures
- Assume "it's probably fine"

---

## Automation

**Automate where possible:**

```bash
# Create qa-check.sh script
#!/bin/bash
set -e

echo "=== Core Validation ==="
python -m pytest -q
python domdata/check_no_trading.py
ctest --test-dir ragd/build --output-on-failure

echo "=== Integration Tests ==="
curl -s http://127.0.0.1:7474/health
python scripts/dominion_cli.py search "test" --top-k 1 > /dev/null

echo "=== Platform Health ==="
python scripts/dominion_cli.py doctor --offline --json

echo "=== All checks passed ==="
```

**Run before commit:**
```bash
./scripts/qa-check.sh
```

---

## Related Docs

- [TESTING_STRATEGY.md](TESTING_STRATEGY.md)
- [TESTING_GUIDE.md](../04_DEVELOPMENT/TESTING_GUIDE.md)
- [AGENT_SAFETY_RULES.md](../09_RISK_AND_SECURITY/AGENT_SAFETY_RULES.md)

---

## Retrieval Hints

- "QA checklist"
- "pre-release checklist"
- "validation checklist"
- "what to check before release"
