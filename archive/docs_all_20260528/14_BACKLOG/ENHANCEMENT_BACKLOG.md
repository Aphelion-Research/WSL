---
doc_type: backlog
system: Dominion
ragd_priority: 4
audience:
  - maintainer
status: active
last_reviewed: 2026-05-19
tags:
  - backlog
  - enhancements
  - improvements
---

# Enhancement Backlog

**Purpose:** Non-feature improvements (UX, docs, tooling, performance).

**Scope:** Not bugs (→ BUG_BACKLOG), not features (→ FEATURE_BACKLOG), not major debt (→ TECH_DEBT_MAP).

**Status:** 25 enhancements (Phase 5).

---

## Enhancement Format

```markdown
### Enhancement Title (Category)

**Description:** [What to improve?]
**Value:** [Why?]
**Effort:** [Time estimate]
**Priority:** P1/P2/P3
```

---

## Categories

1. **Documentation** — Improve docs quality
2. **Tooling** — Developer experience
3. **Performance** — Speed/memory optimization
4. **Observability** — Monitoring/logging
5. **UX** — User interface improvements

---

## Documentation Enhancements

### 1. Auto-Generated API Docs (P2)

**Description:** Sphinx generates HTML docs from docstrings.

**Value:**
- Easier API exploration
- Searchable docs

**Effort:** 1 day (setup Sphinx + autodoc)

**Priority:** P2 (Phase 10)

---

### 2. Architecture Diagrams (Mermaid) (P2)

**Description:** Add 5 more diagrams (currently 1 in CONTROL_FLOW).

**Diagrams:**
- Multi-asset data flow
- Kalman filter bank architecture
- HMM training pipeline
- Risk management flow
- HA failover sequence

**Value:**
- Visual understanding

**Effort:** 4 hours (1 diagram = 1 hour)

**Priority:** P2 (Phase 6)

---

### 3. Video Walkthrough (P3)

**Description:** 30-min Loom video explaining Dominion architecture.

**Value:**
- Faster onboarding (if team scales)

**Effort:** 2 hours (record + edit)

**Priority:** P3 (Phase 14+, if team)

---

### 4. Interactive Notebooks (P3)

**Description:** Jupyter notebooks with embedded examples (backtest, feature analysis).

**Value:**
- Learn by doing

**Effort:** 1 day (5 notebooks)

**Priority:** P3 (Phase 6 research tools)

---

### 5. README Badges (P3)

**Description:** Add badges (test coverage, build status, license).

**Value:**
- Professional appearance

**Effort:** 15 min

**Priority:** P3 (Phase 6)

---

## Tooling Enhancements

### 6. Dev Container (Docker) (P2)

**Description:** Dockerfile + docker-compose for one-command setup.

**Value:**
- Consistent environment
- Faster onboarding

**Effort:** 4 hours

**Priority:** P2 (Phase 10)

---

### 7. Makefile (Task Runner) (P2)

**Description:** Makefile for common tasks (test, lint, run pipeline).

**Example:**
```makefile
test:
	pytest tests/ -v

lint:
	black src/
	flake8 src/

run:
	python -m data_pipeline.cli run
```

**Value:**
- Easier command discovery

**Effort:** 1 hour

**Priority:** P2 (Phase 6)

---

### 8. VSCode Workspace Settings (P3)

**Description:** .vscode/settings.json (recommended extensions, linting config).

**Value:**
- Consistent IDE experience

**Effort:** 30 min

**Priority:** P3 (Phase 6)

---

### 9. Git Aliases (P3)

**Description:** .gitconfig aliases for common workflows.

**Example:**
```ini
[alias]
	co = checkout
	br = branch
	ci = commit
	st = status
	logp = log --pretty=format:'%h %s' --graph
```

**Value:**
- Faster git workflows

**Effort:** 15 min

**Priority:** P3 (Phase 6)

---

### 10. Shell Autocomplete (P3)

**Description:** Bash completion for domdata CLI.

**Value:**
- Faster CLI usage

**Effort:** 1 hour

**Priority:** P3 (Phase 7)

---

## Performance Enhancements

### 11. Numba JIT Compilation (P2)

**Description:** Add @jit decorator to hot loops (feature calculation).

**Example:**
```python
from numba import jit

@jit(nopython=True)
def compute_returns(prices):
    return np.diff(prices) / prices[:-1]
```

**Value:**
- 2-5× speedup (hot loops)

**Effort:** 1 day (identify + annotate hot loops)

**Priority:** P2 (Phase 10)

---

### 12. Cython for Critical Paths (P3)

**Description:** Rewrite VPIN calculation in Cython.

**Value:**
- 10× speedup (vs Python)

**Effort:** 1 week (Cython learning curve)

**Priority:** P3 (Phase 11+, if bottleneck)

---

### 13. Database Query Optimization (P2)

**Description:** Add indexes, optimize queries.

**Current:**
```sql
SELECT * FROM gold_master WHERE symbol='GC=F' AND timestamp > '2026-01-01'
```

**Optimized:**
```sql
CREATE INDEX idx_symbol_timestamp ON gold_master(symbol, timestamp);
```

**Value:**
- 10× faster queries (large tables)

**Effort:** 2 hours

**Priority:** P2 (Phase 9)

---

### 14. Pandas Dtype Optimization (P3)

**Description:** Use category dtype for symbol (not object).

**Example:**
```python
df['symbol'] = df['symbol'].astype('category')  # 50% memory reduction
```

**Value:**
- 50% memory reduction (large dataframes)

**Effort:** 1 hour

**Priority:** P3 (Phase 11)

---

### 15. Lazy Loading (Features) (P3)

**Description:** Compute features on-demand (not all upfront).

**Value:**
- Faster startup (don't compute unused features)

**Effort:** 1 day (refactor feature pipeline)

**Priority:** P3 (Phase 11)

---

## Observability Enhancements

### 16. Prometheus Metrics (P2)

**Description:** Export metrics (pipeline latency, feature count, error rate).

**Value:**
- Real-time monitoring

**Effort:** 1 day

**Priority:** P2 (Phase 10)

---

### 17. Grafana Dashboards (P2)

**Description:** Pre-built dashboards (system health, performance).

**Value:**
- Visual monitoring

**Effort:** 1 day (after Prometheus)

**Priority:** P2 (Phase 10)

---

### 18. Structured Logging (JSON) (P3)

**Description:** Log JSON instead of plain text.

**Example:**
```python
logger.info({"event": "pipeline_start", "symbol": "GC=F", "timestamp": "2026-01-01"})
```

**Value:**
- Easier parsing (ELK, CloudWatch)

**Effort:** 2 hours

**Priority:** P3 (Phase 10)

---

### 19. Distributed Tracing (OpenTelemetry) (P3)

**Description:** Trace requests across components.

**Value:**
- Debug distributed pipeline (Phase 11+)

**Effort:** 1 week (setup + instrument)

**Priority:** P3 (Phase 11)

---

### 20. Health Check Endpoint (P2)

**Description:** HTTP endpoint `/health` (returns system status).

**Value:**
- Uptime monitoring (Pingdom, UptimeRobot)

**Effort:** 1 hour

**Priority:** P2 (Phase 7)

---

## UX Enhancements

### 21. CLI Progress Bars (P3)

**Description:** Show progress (tqdm) for long operations.

**Example:**
```python
from tqdm import tqdm
for symbol in tqdm(symbols, desc="Ingesting"):
    ingest(symbol)
```

**Value:**
- Better user experience

**Effort:** 1 hour

**Priority:** P3 (Phase 6)

---

### 22. Color-Coded Logs (P3)

**Description:** Error=red, Warning=yellow, Info=green.

**Value:**
- Easier visual scanning

**Effort:** 30 min (colorlog library)

**Priority:** P3 (Phase 6)

---

### 23. CLI Help Text Improvement (P3)

**Description:** Add examples to `--help` output.

**Example:**
```bash
$ domdata capture --help

Examples:
  domdata capture GC=F --duration 1h
  domdata capture ES=F --output /tmp/ticks/
```

**Value:**
- Faster CLI discovery

**Effort:** 1 hour

**Priority:** P3 (Phase 7)

---

### 24. Dashboard Dark Mode (P3)

**Description:** Streamlit dashboard dark theme.

**Value:**
- Eye strain reduction (night usage)

**Effort:** 30 min

**Priority:** P3 (Phase 10)

---

### 25. Email Digest (Daily Summary) (P2)

**Description:** Daily email (Sharpe, P&L, alerts).

**Value:**
- Quick performance check (mobile)

**Effort:** 2 hours

**Priority:** P2 (Phase 7)

---

## Enhancement Schedule

### Phase 6 (Q2-Q3 2026)
- [ ] Architecture diagrams (#2)
- [ ] README badges (#5)
- [ ] Makefile (#7)
- [ ] VSCode settings (#8)
- [ ] Git aliases (#9)
- [ ] CLI progress bars (#21)
- [ ] Color-coded logs (#22)

**Effort:** 1 day (mostly quick wins)

---

### Phase 7 (Q3-Q4 2026)
- [ ] Shell autocomplete (#10)
- [ ] Health check endpoint (#20)
- [ ] CLI help text (#23)
- [ ] Email digest (#25)

**Effort:** 1 day

---

### Phase 10 (Q4 2027 - Q1 2028)
- [ ] Auto-generated API docs (#1)
- [ ] Dev container (#6)
- [ ] Numba JIT (#11)
- [ ] Database query optimization (#13)
- [ ] Prometheus metrics (#16)
- [ ] Grafana dashboards (#17)
- [ ] Structured logging (#18)
- [ ] Dashboard dark mode (#24)

**Effort:** 1 week

---

### Phase 11 (Q2-Q3 2028)
- [ ] Pandas dtype optimization (#14)
- [ ] Lazy loading (#15)
- [ ] Distributed tracing (#19)

**Effort:** 1 week

---

### Deferred (Phase 14+)
- Video walkthrough (#3) — Only if team scales
- Interactive notebooks (#4) — Nice-to-have
- Cython rewrite (#12) — Only if bottleneck
- OpenTelemetry (#19) — Only if distributed

---

## Enhancement Metrics

**Total enhancements:** 25

**By Category:**
- Documentation: 5
- Tooling: 5
- Performance: 5
- Observability: 5
- UX: 5

**By Priority:**
- P2: 12 (medium value)
- P3: 13 (low priority)

**By Effort:**
- <1 hour: 10 items
- 1-4 hours: 10 items
- 1+ days: 5 items

---

## Triage Schedule

**Quarterly:** Review backlog, promote quick wins to roadmap.

**Last Triage:** 2026-05-19 (Phase 5)

**Next Triage:** 2026-08-19 (Phase 6 mid-point)

---

## Related Documentation

- [[FEATURE_BACKLOG]] — New features
- [[BUG_BACKLOG]] — Known bugs
- [[DEBT_BACKLOG]] — Code-level debt
- [[TECH_DEBT_MAP]] — Architecture debt

---

## Maintenance Notes

**Last Updated:** 2026-05-19 (Phase 5)

**Update Frequency:** Quarterly

**How to Add:**
1. Identify improvement opportunity
2. Categorize (docs/tooling/performance/observability/UX)
3. Estimate effort + priority
4. Add to backlog
5. Triage quarterly
