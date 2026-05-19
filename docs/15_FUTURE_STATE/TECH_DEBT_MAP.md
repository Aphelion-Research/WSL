---
doc_type: reference
system: Dominion
ragd_priority: 5
audience:
  - maintainer
  - developer
status: active
last_reviewed: 2026-05-19
tags:
  - tech-debt
  - maintenance
  - future
---

# Technical Debt Map

**Purpose:** Catalog of known technical debt + remediation plan.

**Status:** 18 debt items identified (Phase 5). Prioritized for Phase 6-14.

**Principle:** Ship fast (Phase 0-5), refactor strategically (Phase 6+).

---

## Debt Categories

1. **Architecture** — Design limitations (5 items)
2. **Performance** — Bottlenecks (4 items)
3. **Testing** — Coverage gaps (3 items)
4. **Documentation** — Missing/stale docs (2 items)
5. **Infrastructure** — Operational toil (4 items)

---

## Priority Levels

- **P1 (Critical):** Blocks scaling or production launch
- **P2 (High):** Impacts performance or reliability
- **P3 (Medium):** Quality-of-life improvements
- **P4 (Low):** Nice-to-have, defer indefinitely

---

## Architecture Debt

### 1. Single-Asset Hardcoding (P1)

**Symptom:** Pipeline assumes single asset (GC=F). Hard to extend to multi-asset.

**Location:**
- `data_pipeline/cli.py` — Hardcoded symbol="GC=F"
- `features/pipeline.py` — Single-asset assumptions
- `regime/hmm.py` — No per-asset regime

**Impact:**
- Blocks Phase 9 (multi-asset expansion)
- Requires refactor to support 12+ assets

**Remediation (Phase 8-9):**
```python
# Before (hardcoded)
def run_pipeline():
    ingest_ticks("GC=F")
    compute_features("GC=F")

# After (multi-asset)
def run_pipeline(symbols):
    for symbol in symbols:
        ingest_ticks(symbol)
        compute_features(symbol)
```

**Effort:** 2 weeks (refactor 10+ files)

**Scheduled:** Phase 9 (Q2 2027)

---

### 2. Synchronous Pipeline (P2)

**Symptom:** Pipeline runs serially (ingest → features → regime), slow for 100 assets.

**Location:**
- `data_pipeline/cli.py` — Sequential function calls
- No async/await or parallelization

**Impact:**
- 12 assets: 15 min (acceptable)
- 100 assets: 120 min (unacceptable)

**Remediation (Phase 11):**
- Introduce Ray/Dask for parallel execution
- Asset-level parallelism (100 workers)

**Effort:** 3 weeks (rewrite pipeline orchestration)

**Scheduled:** Phase 11 (Q2 2028)

---

### 3. No Strategy Abstraction (P2)

**Symptom:** Alpha model tightly coupled to pipeline. Hard to add new strategies.

**Location:**
- `alpha/` directory doesn't exist yet
- Models in notebooks, not production code

**Impact:**
- Blocks Phase 11 (multi-strategy framework)
- Need Strategy base class + polymorphism

**Remediation (Phase 6-7):**
```python
class Strategy(ABC):
    @abstractmethod
    def generate_signal(self, features):
        pass
    
    @abstractmethod
    def size_position(self, signal, volatility):
        pass

class AlphaStrategy(Strategy):
    def generate_signal(self, features):
        return self.model.predict(features)
```

**Effort:** 1 week (design + implement)

**Scheduled:** Phase 6 (Q2 2026)

---

### 4. Monolithic Config (P3)

**Symptom:** Configuration scattered across files (hardcoded constants).

**Location:**
- `config.py` — Partial config
- Many hardcoded values (timeouts, thresholds)

**Impact:**
- Hard to tune parameters
- Difficult to A/B test configurations

**Remediation (Phase 8):**
- Centralized config (YAML or TOML)
- Environment-specific configs (dev/staging/prod)

**Effort:** 1 week

**Scheduled:** Phase 8 (Q4 2026)

---

### 5. No Versioning (Models, Features) (P3)

**Symptom:** Model checkpoints not versioned. Features not tracked.

**Location:**
- `models/` directory lacks versioning
- No feature store

**Impact:**
- Can't reproduce historical predictions
- Model rollback difficult

**Remediation (Phase 10):**
- MLflow or similar (model registry)
- Feature store (Feast or custom)

**Effort:** 2 weeks

**Scheduled:** Phase 10 (Q4 2027)

---

## Performance Debt

### 6. Unoptimized Loops (P2)

**Symptom:** Some feature calculations use Python loops (slow).

**Location:**
- `features/microstructure.py` — OFI calculation (line 145)
- `features/volatility.py` — Rolling window (line 89)

**Impact:**
- 10-20% slower than vectorized
- Noticeable at 100 assets

**Remediation (Phase 10):**
- Rewrite with numpy/numba
- Benchmark before/after

**Effort:** 3 days

**Scheduled:** Phase 10 (Q4 2027)

---

### 7. No Caching (Intermediate Features) (P2)

**Symptom:** Recompute same features multiple times (e.g., returns used in 10 features).

**Location:**
- `features/pipeline.py` — No caching layer

**Impact:**
- 30% wasted computation
- Worse at 100 assets

**Remediation (Phase 11):**
- Redis cache (TTL 60s)
- Cache key: (symbol, timestamp, feature_name)

**Effort:** 1 week

**Scheduled:** Phase 11 (Q2 2028)

---

### 8. Database Not Indexed (P2)

**Symptom:** Queries slow on large tables (full table scan).

**Location:**
- `gold_master` table — No index on (symbol, timestamp)

**Impact:**
- Query time: 500ms (12 assets), 5s+ (100 assets)

**Remediation (Phase 9):**
```sql
CREATE INDEX idx_symbol_timestamp ON gold_master(symbol, timestamp);
```

**Effort:** 1 hour

**Scheduled:** Phase 9 (Q2 2027)

---

### 9. Memory Leaks (Possible) (P3)

**Symptom:** Long-running processes grow memory (not confirmed, suspected).

**Location:**
- `kalman/filter.py` — Covariance matrix accumulation?

**Impact:**
- Restart required every 7 days (anecdotal)

**Remediation (Phase 8):**
- Profile with memory_profiler
- Fix leaks if found

**Effort:** 2 days (investigation + fix)

**Scheduled:** Phase 8 (Q4 2026)

---

## Testing Debt

### 10. Low Coverage (Agent OS) (P3)

**Symptom:** Agent session management 65% coverage (target >85%).

**Location:**
- `agent/session.py` — Edge cases not tested
- `agent/handoff.py` — Error paths not tested

**Impact:**
- Bugs in agent workflows (low priority, agent-facing)

**Remediation (Phase 6):**
- Add 10 tests (edge cases, error handling)

**Effort:** 2 days

**Scheduled:** Phase 6 (Q2 2026)

---

### 11. No Load Testing (P2)

**Symptom:** Never tested 100 concurrent requests (RAGD API).

**Location:**
- RAGD REST API — No load tests

**Impact:**
- Unknown capacity (may crash under load)

**Remediation (Phase 10):**
- Locust or k6 (load testing tool)
- Target: 100 req/s (sustained)

**Effort:** 1 day

**Scheduled:** Phase 10 (Q4 2027)

---

### 12. No Chaos Testing (P3)

**Symptom:** Never tested failure scenarios (DB crash, network partition).

**Location:**
- Integration tests — Happy path only

**Impact:**
- Unknown resilience (may not recover from failures)

**Remediation (Phase 10):**
- Chaos Monkey style tests (random failures)

**Effort:** 3 days

**Scheduled:** Phase 10 (Q4 2027)

---

## Documentation Debt

### 13. Missing API Docs (P3)

**Symptom:** Python docstrings inconsistent, missing.

**Location:**
- 30% of functions lack docstrings
- No Sphinx-generated API docs

**Impact:**
- Onboarding slower (if team scales)

**Remediation (Phase 10):**
- Sphinx + autodoc
- Enforce docstring linting (pydocstyle)

**Effort:** 1 week

**Scheduled:** Phase 10 (Q4 2027)

---

### 14. Stale ADRs (P4)

**Symptom:** Some ADRs reference outdated architecture.

**Location:**
- ADR_0001, ADR_0002 (Phase 0) — Mention deprecated regex parser

**Impact:**
- Confusing for future maintainers

**Remediation (Phase 5-6):**
- Review + update ADRs annually
- Mark obsolete sections

**Effort:** 2 hours

**Scheduled:** Phase 6 (Q2 2026)

---

## Infrastructure Debt

### 15. Manual Deployment (P2)

**Symptom:** No CI/CD. Deploy via git pull + restart.

**Location:**
- Deployment process — Manual

**Impact:**
- Slow (30 min), error-prone
- Blocks rapid iteration

**Remediation (Phase 10):**
- GitHub Actions CI/CD
- Blue-green deployment

**Effort:** 1 week

**Scheduled:** Phase 10 (Q4 2027)

---

### 16. No Centralized Logging (P3)

**Symptom:** Logs scattered across files. No search, no retention.

**Location:**
- `logs/` directory — Plain text files
- No log aggregation

**Impact:**
- Debugging slow (grep across 100 files)

**Remediation (Phase 10):**
- ELK stack (Elasticsearch, Logstash, Kibana)
- Or: Cloud logging (AWS CloudWatch)

**Effort:** 3 days

**Scheduled:** Phase 10 (Q4 2027)

---

### 17. No Alerting (P2)

**Symptom:** Failures silent. Discover issues hours later.

**Location:**
- No monitoring, no alerts

**Impact:**
- Downtime unnoticed (bad for production)

**Remediation (Phase 7):**
- Prometheus + AlertManager
- Email/Slack alerts (critical: system crash, data loss)

**Effort:** 2 days

**Scheduled:** Phase 7 (Q3 2026)

---

### 18. Secrets in Code (Mitigated) (P4)

**Symptom:** Early versions had API keys in code (fixed Phase 2).

**Location:**
- `secrets/mt5.env` — Proper location now
- `.gitignore` excludes secrets/

**Impact:**
- None (already fixed)

**Remediation:**
- Already done (Phase 2)
- Future: Migrate to Vault (Phase 10)

**Effort:** 0 (monitoring only)

**Status:** Mitigated ✓

---

## Debt Remediation Schedule

### Phase 6 (Q2-Q3 2026)
- [x] Strategy abstraction (debt #3)
- [x] Low coverage (Agent OS) (debt #10)
- [x] Stale ADRs (debt #14)

### Phase 7 (Q3-Q4 2026)
- [ ] Alerting (debt #17)

### Phase 8 (Q4 2026 - Q1 2027)
- [ ] Monolithic config (debt #4)
- [ ] Memory leaks investigation (debt #9)

### Phase 9 (Q1-Q3 2027)
- [ ] Single-asset hardcoding (debt #1)
- [ ] Database indexing (debt #8)

### Phase 10 (Q4 2027 - Q1 2028)
- [ ] Model versioning (debt #5)
- [ ] Unoptimized loops (debt #6)
- [ ] Load testing (debt #11)
- [ ] Chaos testing (debt #12)
- [ ] API docs (debt #13)
- [ ] CI/CD (debt #15)
- [ ] Centralized logging (debt #16)

### Phase 11 (Q2-Q3 2028)
- [ ] Synchronous pipeline (debt #2)
- [ ] Feature caching (debt #7)

---

## Debt Metrics

**Current (Phase 5):**
- Total debt items: 18
- Critical (P1): 1
- High (P2): 7
- Medium (P3): 8
- Low (P4): 2

**Target (Phase 10):**
- Total debt items: <10
- Critical (P1): 0
- High (P2): <3

**Debt Ratio:**
- Debt LOC / Total LOC: ~15% (estimated)
- Target: <10% (Phase 10)

---

## Debt Principles

### 1. Ship Fast, Refactor Later
- Phase 0-5: Speed > perfection
- Phase 6+: Quality matters (production approaching)

### 2. Pay Debt Before It Compounds
- P1 debt: Fix immediately (blocks progress)
- P2 debt: Fix within 2 phases (before impacts scale)
- P3 debt: Fix opportunistically

### 3. No New P1 Debt
- Code reviews catch critical debt
- Refuse PR if introduces P1 debt

### 4. Measure Debt
- Track debt items (this doc)
- Review quarterly (add/close items)

---

## Debt vs Feature Trade-Off

**Question:** Fix debt or ship feature?

**Decision Matrix:**

| Debt Priority | Feature Priority | Decision |
|---|---|---|
| P1 | Any | Fix debt first |
| P2 | P1 feature | Ship feature, debt next sprint |
| P2 | P2+ feature | Fix debt first |
| P3+ | Any | Ship feature |

**Rationale:** P1 debt blocks future work. P2 debt compounds. P3+ debt tolerable.

---

## Related Documentation

- [[FUTURE_VISION]] — Long-term roadmap
- [[SCALING_STRATEGY]] — Scaling plan (addresses debt #1, #2, #7)
- [[TESTING_STRATEGY]] — Coverage targets (addresses debt #10, #11, #12)
- [[CODING_STANDARDS]] — Code quality guidelines

---

## Maintenance Notes

**Last Updated:** 2026-05-19 (Phase 5)

**Update Frequency:** Quarterly (or when new debt identified)

**How to Add Debt:**
1. Identify issue (code review, debugging, scaling blocker)
2. Add entry (category, priority, location, impact, remediation)
3. Assign to phase (schedule fix)
4. Track in GitHub issues (link from this doc)
