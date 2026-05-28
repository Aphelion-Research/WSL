---
doc_type: development
system: Dominion
ragd_priority: 7
audience:
  - ai_agent
  - maintainer
status: current
last_reviewed: 2026-05-19
tags:
  - development
  - git
  - commits
---

# Commit Guide

**Purpose:** Conventional commit format for Dominion.

---

## Format

```
<type>: <short description> (≤50 chars)

<body explaining WHY, not WHAT> (wrap at 72 chars)

- Bullet points OK
- Reference issues: Fixes #123, Closes #456

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

---

## Types

| Type | Meaning | Example |
|---|---|---|
| `feat` | New feature | `feat: add Kalman fusion for multi-source data` |
| `fix` | Bug fix | `fix: correct Brownian bridge boundary violation` |
| `docs` | Documentation only | `docs: update data pipeline architecture` |
| `refactor` | Code restructure (no behavior change) | `refactor: extract Kalman filter to separate class` |
| `test` | Add/update tests | `test: add convergence tests for Kalman filter` |
| `chore` | Maintenance (deps, config) | `chore: update yfinance to 0.2.40` |
| `perf` | Performance improvement | `perf: cache feature computation results` |
| `style` | Formatting (no logic change) | `style: format with black` |

---

## Examples

### Good Commits

```
feat: add Kalman fusion for multi-source data

Implements 6-timescale Kalman filter bank with dynamic trust scoring.
Handles Byzantine fault tolerance with 3+ source agreement.

Why: Single-source data is unreliable. Multi-source fusion with
outlier rejection provides institutional-grade data quality.

- Added kalman.py with KalmanFilter class
- Added tests for convergence and trust updates
- Updated data pipeline to use fusion
- Added DuckDB schema for fused prices

Closes #45

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

```
fix: correct Brownian bridge boundary violation

Brownian bridge was generating ticks outside [low, high] range when
volatility was high. Added constraint enforcement.

Why: Invalid ticks break downstream microstructure calculations.

Fixes #67

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

```
docs: update data pipeline architecture

Added Mermaid diagram for data flow and detailed Kalman fusion algorithm.

Why: New contributors need to understand multi-source fusion before
modifying the pipeline.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

---

### Bad Commits

```
fixed stuff
```
*Problem: What stuff? Why?*

```
feat: update code
```
*Problem: Vague. What code? What feature?*

```
feat: add feature X, fix bug Y, update docs Z
```
*Problem: Multiple unrelated changes. Split into 3 commits.*

```
WIP
```
*Problem: Never commit WIP to main.*

---

## Writing Good Commit Messages

### Short Description

- ≤50 chars
- Imperative mood: "add" not "added" or "adds"
- Lowercase except proper nouns
- No period at end
- Complete the sentence: "This commit will ..."

**Examples:**
- ✓ `feat: add Kalman fusion`
- ✗ `feat: Added kalman fusion.`
- ✗ `feat: This commit adds Kalman fusion`

### Body

- Wrap at 72 chars
- Explain **WHY**, not WHAT (code shows what)
- Bullet points OK for lists
- Reference issues/PRs
- Add context for future readers

**Good body:**
```
Why: Single-source data is unreliable due to API failures, stale data,
and conflicting prices. Multi-source fusion with Kalman filtering and
Byzantine fault tolerance provides institutional-grade reliability.

Alternative considered: Simple averaging, but doesn't handle outliers
or dynamic trust scoring.
```

**Bad body:**
```
Added some code for Kalman filters. Updated tests. Fixed bug.
```

---

## Atomic Commits

**One logical change per commit.**

**Good:**
- Commit 1: `feat: add Kalman filter class`
- Commit 2: `test: add Kalman filter tests`
- Commit 3: `feat: integrate Kalman filter into pipeline`

**Bad:**
- Commit 1: `feat: add Kalman filter and tests and integration and docs`

---

## When to Commit

**Commit when:**
- Feature is complete and tested
- Bug is fixed and tested
- Refactor is complete and tests pass
- Docs are updated

**Don't commit:**
- Broken code (unless explicitly WIP branch, not main)
- Failing tests
- Commented-out code
- Debugging print statements
- Secrets or API keys

---

## Commit Workflow

```bash
# 1. Make changes
vim data_pipeline/fusion.py

# 2. Run tests
python -m pytest -q

# 3. Run trading check
python domdata/check_no_trading.py

# 4. Stage changes
git add data_pipeline/fusion.py

# 5. Write commit message
git commit -m "feat: add Kalman fusion

Implements 6-timescale Kalman filter bank with dynamic trust scoring.

Why: Single-source data is unreliable. Multi-source fusion provides
institutional-grade reliability.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"

# 6. Push (if ready)
git push origin main
```

---

## Multi-Line Commits

**Use heredoc for readability:**

```bash
git commit -m "$(cat <<'EOF'
feat: add Kalman fusion for multi-source data

Implements 6-timescale Kalman filter bank with dynamic trust scoring.
Handles Byzantine fault tolerance with 3+ source agreement.

Why: Single-source data is unreliable due to API failures and
conflicting prices. Multi-source fusion provides institutional-grade
data quality.

- Added kalman.py with KalmanFilter class
- Added tests for convergence and trust updates
- Updated data pipeline to use fusion

Closes #45

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Amending Commits

**Only amend unpublished commits.**

```bash
# Add forgotten file
git add forgotten_file.py
git commit --amend --no-edit

# Fix commit message
git commit --amend -m "corrected message"
```

**Never amend published commits** (breaks history for others).

---

## Co-Authorship

**Always credit AI agents:**

```
Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

**Credit multiple authors:**

```
Co-Authored-By: Martin <martin@example.com>
Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

---

## Referencing Issues

```
Fixes #123        # Closes issue on merge
Closes #456       # Closes issue on merge
Refs #789         # References without closing
See #012          # References without closing
```

---

## Breaking Changes

**Use `BREAKING CHANGE:` footer:**

```
feat: change API response format

BREAKING CHANGE: /query endpoint now returns array of objects instead
of array of strings. Update all clients.

Migration:
  Old: ["chunk1", "chunk2"]
  New: [{"content": "chunk1"}, {"content": "chunk2"}]

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

---

## Validation

Before pushing:

- [ ] Commit message follows format
- [ ] Type is correct (feat/fix/docs/etc.)
- [ ] Short description ≤50 chars
- [ ] Body explains WHY (if non-obvious)
- [ ] Tests pass
- [ ] Trading check passes
- [ ] No secrets in diff
- [ ] Co-authored-by line present (for agent commits)

---

## Related Docs

- [DEVELOPMENT_GUIDE.md](DEVELOPMENT_GUIDE.md)
- [CODING_STANDARDS.md](CODING_STANDARDS.md)
- [BRANCHING_GUIDE.md](BRANCHING_GUIDE.md)

---

## Retrieval Hints

- "commit format"
- "commit message"
- "git commit"
- "how to commit"
- "conventional commits"
