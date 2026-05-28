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
  - tech-debt
  - refactoring
---

# Technical Debt Backlog

**Purpose:** Smaller debt items not tracked in [[TECH_DEBT_MAP]].

**Scope:** Code-level debt (duplicate code, poor naming, missing tests). Architecture debt → TECH_DEBT_MAP.

**Status:** 20 debt items (Phase 5).

---

## Debt Format

```markdown
### Debt Item (Priority)

**Location:** [File:line or module]
**Issue:** [What's wrong?]
**Impact:** [Why it matters]
**Fix:** [How to resolve]
**Effort:** [Time estimate]
```

---

## P1: Refactor Soon

### 1. Duplicate Feature Code (P1)

**Location:** `features/price.py`, `features/volume.py`

**Issue:** Returns calculation duplicated in 3 places.

**Impact:**
- DRY violation (bug fix requires 3 edits)
- 200 LOC duplicated

**Fix:**
```python
# Extract to common utility
def compute_returns(prices, periods=[1, 5, 15]):
    return {f'returns_{p}m': np.diff(prices, periods=p) / prices[:-p] 
            for p in periods}
```

**Effort:** 2 hours

**Scheduled:** Phase 6

---

### 2. Magic Numbers Everywhere (P1)

**Location:** 50+ files

**Issue:** Hardcoded constants (0.7 toxicity threshold, 3σ outliers, 100 Kalman window).

**Impact:**
- Hard to tune
- No single source of truth

**Fix:**
```python
# Create config.py
TOXICITY_THRESHOLD = 0.7
OUTLIER_SIGMA = 3.0
KALMAN_WINDOW = 100
```

**Effort:** 4 hours (find all, extract to config)

**Scheduled:** Phase 8

---

### 3. God Class (FeaturePipeline) (P1)

**Location:** `features/pipeline.py`

**Issue:** FeaturePipeline class 800 LOC, does everything (compute, validate, cache).

**Impact:**
- Hard to test (too many responsibilities)
- Hard to extend

**Fix:**
- Split into FeatureComputer, FeatureValidator, FeatureCache
- Compose in pipeline

**Effort:** 1 day

**Scheduled:** Phase 9 (when scaling to 100 assets)

---

## P2: Refactor Eventually

### 4. Poor Variable Names (P2)

**Location:** `kalman/filter.py:45`

**Issue:** `x`, `P`, `Q`, `R` (single-letter names).

**Impact:**
- Hard to read (what's P?)

**Fix:**
```python
# Before
x = ...
P = ...

# After
state = ...
covariance = ...
```

**Effort:** 30 min

**Scheduled:** Phase 8

---

### 5. Long Functions (>100 LOC) (P2)

**Location:** `data_pipeline/cli.py:run()` (150 LOC)

**Issue:** Single function does ingest + fuse + features + RAGD.

**Impact:**
- Hard to test individual steps
- Hard to parallelize

**Fix:**
- Extract subfunctions (ingest_step, fuse_step, feature_step)
- Orchestrate in main

**Effort:** 2 hours

**Scheduled:** Phase 11 (parallel pipeline)

---

### 6. No Type Hints (P2)

**Location:** 60% of functions lack type hints

**Issue:**
```python
def compute_returns(prices):  # What type is prices? ndarray? list?
    ...
```

**Impact:**
- IDE autocomplete broken
- Runtime errors (pass wrong type)

**Fix:**
```python
from typing import List
import numpy as np

def compute_returns(prices: np.ndarray) -> np.ndarray:
    ...
```

**Effort:** 1 week (add to all functions, enable mypy)

**Scheduled:** Phase 10

---

### 7. Commented-Out Code (P2)

**Location:** 20+ files

**Issue:** Old code commented, not deleted.

**Impact:**
- Clutter (confusing)
- Git history exists (no need to keep)

**Fix:**
- Delete commented code
- Rely on git for history

**Effort:** 1 hour

**Scheduled:** Phase 6 (cleanup sprint)

---

### 8. Inconsistent Error Handling (P2)

**Location:** Various

**Issue:**
- Some functions raise exceptions
- Some return None
- Some log + continue

**Impact:**
- Unpredictable behavior

**Fix:**
- Standardize: Raise for unrecoverable, return None for acceptable failures
- Document in coding standards

**Effort:** 2 days (audit + fix)

**Scheduled:** Phase 8

---

### 9. Missing Docstrings (P2)

**Location:** 30% of functions

**Issue:** No docstring.

**Impact:**
- Hard to use (what does this do?)

**Fix:**
```python
def compute_ofi(bid_size, ask_size):
    """Compute Order Flow Imbalance.
    
    Args:
        bid_size: Size at best bid
        ask_size: Size at best ask
    
    Returns:
        OFI value (positive = net buying)
    """
    ...
```

**Effort:** 1 week (add docstrings + enforce linting)

**Scheduled:** Phase 10

---

### 10. Inconsistent Naming (P2)

**Location:** Various

**Issue:**
- Some: `compute_feature()`
- Some: `calculate_feature()`
- Some: `get_feature()`

**Impact:**
- Hard to remember API

**Fix:**
- Standardize: `compute_*()` for calculations
- Document in coding standards

**Effort:** 2 hours

**Scheduled:** Phase 6

---

## P3: Low Priority

### 11. Dead Code (P3)

**Location:** `research/prototypes/` (old notebooks)

**Issue:** 10 notebooks never used.

**Impact:**
- Disk space (50MB)
- Confusion (which is current?)

**Fix:**
- Archive to `research/archive/`
- Delete if >1 year old

**Effort:** 30 min

**Scheduled:** Phase 6 cleanup

---

### 12. Hardcoded Paths (P3)

**Location:** `scripts/vault_sync.py:15`

**Issue:** `/home/Martin/Dominion/vault` hardcoded.

**Impact:**
- Breaks on different machine

**Fix:**
```python
VAULT_PATH = os.path.join(os.getcwd(), 'vault')
```

**Effort:** 15 min

**Scheduled:** Phase 6

---

### 13. Print Statements (Debug) (P3)

**Location:** 15 files

**Issue:** `print(f"Debug: {x}")` left in code.

**Impact:**
- Pollutes logs

**Fix:**
- Replace with `logger.debug()`

**Effort:** 30 min

**Scheduled:** Phase 6 cleanup

---

### 14. Unused Imports (P3)

**Location:** 40+ files

**Issue:** `import numpy as np` never used.

**Impact:**
- Clutter (minor)

**Fix:**
- Run autoflake (removes unused imports)

**Effort:** 5 min

**Scheduled:** Phase 6 (automated)

---

### 15. Long Lines (>120 chars) (P3)

**Location:** 100+ lines

**Issue:** Code exceeds 120 chars (horizontal scroll).

**Impact:**
- Hard to read

**Fix:**
- Reformat with black (line length=120)

**Effort:** 5 min

**Scheduled:** Phase 6 (automated)

---

### 16. No __init__.py in Some Packages (P3)

**Location:** `tests/fixtures/`

**Issue:** Missing `__init__.py` (not recognized as package).

**Impact:**
- Import errors (minor, workaround exists)

**Fix:**
- Add empty `__init__.py`

**Effort:** 2 min

**Scheduled:** Phase 6

---

### 17. Pytest Warnings (Deprecation) (P3)

**Location:** Test suite

**Issue:** 10 deprecation warnings (pandas, numpy).

**Impact:**
- Clutter in test output

**Fix:**
- Update deprecated API calls

**Effort:** 1 hour

**Scheduled:** Phase 8

---

### 18. No .editorconfig (P3)

**Location:** Root directory

**Issue:** No .editorconfig (inconsistent editor settings).

**Impact:**
- Tabs vs spaces (minor)

**Fix:**
```ini
# .editorconfig
root = true

[*.py]
indent_style = space
indent_size = 4
```

**Effort:** 5 min

**Scheduled:** Phase 6

---

### 19. No Pre-Commit Hooks (P3)

**Location:** `.git/hooks/`

**Issue:** Only post-commit (vault sync). No pre-commit (linting).

**Impact:**
- Linting errors discovered in CI (not locally)

**Fix:**
```bash
# .git/hooks/pre-commit
#!/bin/bash
black --check src/
flake8 src/
mypy src/
```

**Effort:** 15 min

**Scheduled:** Phase 6

---

### 20. Git Commit Messages (P3)

**Location:** Git history

**Issue:** Some commits vague ("fix bug", "update").

**Impact:**
- Hard to understand history

**Fix:**
- Enforce commit message convention (Conventional Commits)
- Use pre-commit hook to validate

**Effort:** 0 (future commits only)

**Scheduled:** Phase 6 (establish convention)

---

## Debt Paydown Schedule

### Phase 6 (Q2-Q3 2026) — Cleanup Sprint
- [ ] Duplicate feature code (#1)
- [ ] Commented-out code (#7)
- [ ] Inconsistent naming (#10)
- [ ] Dead code (#11)
- [ ] Hardcoded paths (#12)
- [ ] Print statements (#13)
- [ ] Unused imports (#14)
- [ ] Long lines (#15)
- [ ] Missing __init__.py (#16)
- [ ] .editorconfig (#18)
- [ ] Pre-commit hooks (#19)
- [ ] Commit message convention (#20)

**Effort:** 1 day (most automated)

---

### Phase 8 (Q4 2026 - Q1 2027)
- [ ] Magic numbers (#2)
- [ ] Poor variable names (#4)
- [ ] Inconsistent error handling (#8)
- [ ] Pytest warnings (#17)

**Effort:** 2 days

---

### Phase 9 (Q1-Q3 2027)
- [ ] God class (FeaturePipeline) (#3)

**Effort:** 1 day

---

### Phase 10 (Q4 2027 - Q1 2028)
- [ ] Type hints (#6)
- [ ] Missing docstrings (#9)

**Effort:** 2 weeks

---

### Phase 11 (Q2-Q3 2028)
- [ ] Long functions (#5)

**Effort:** 2 hours

---

## Automation Opportunities

**Linters (Phase 6):**
- black (formatting)
- flake8 (style)
- mypy (type checking)
- autoflake (unused imports)
- pydocstyle (docstrings)

**Pre-Commit Hooks (Phase 6):**
- Run linters before commit
- Reject if violations

**CI (Phase 10):**
- Enforce coverage >85%
- Enforce no linting errors

---

## Debt Metrics

**Current (Phase 5):**
- Code smells: 20 items
- Duplicated LOC: ~500 (estimate)
- Missing docstrings: ~30% of functions
- Type hints: ~40% of functions

**Target (Phase 10):**
- Code smells: <5 items
- Duplicated LOC: <100
- Missing docstrings: <10%
- Type hints: >90%

---

## Related Documentation

- [[TECH_DEBT_MAP]] — Architecture-level debt
- [[CODING_STANDARDS]] — Code quality guidelines
- [[BUG_BACKLOG]] — Known bugs
- [[FEATURE_BACKLOG]] — Feature requests

---

## Maintenance Notes

**Last Updated:** 2026-05-19 (Phase 5)

**Update Frequency:** Quarterly

**How to Add:**
1. Identify code smell during review
2. Document issue + fix
3. Prioritize (P1/P2/P3)
4. Schedule in appropriate phase
