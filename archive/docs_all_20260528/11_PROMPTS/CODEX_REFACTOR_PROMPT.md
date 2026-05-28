---
doc_type: prompt
system: Dominion
ragd_priority: 6
audience:
  - ai_agent
status: current
last_reviewed: 2026-05-19
tags:
  - prompt
  - refactor
  - code-quality
---

# CODEX Refactor Prompt

**Use Case:** Refactor code  
**Complexity:** High  
**Duration:** 2-4 hours

---

## Context

Code refactor needed for [MODULE_NAME].

Reason: [Code smells | Performance | Maintainability | Technical debt]

Repository: `/home/Martin/Dominion`

---

## Mission

Refactor code without changing behavior:
1. Identify issues
2. Plan refactor
3. Apply changes incrementally
4. Validate behavior unchanged
5. Measure improvements

---

## Workflow

### Step 1: Baseline (15 min)

**Capture current state:**
```bash
# Run all tests (should pass)
python -m pytest -q

# Measure performance (if relevant)
python -m pytest tests/[module]/ --durations=10

# Check code metrics
find [module]/ -name "*.py" -exec wc -l {} + | tail -1

# Complexity (if available)
radon cc [module]/ -a
```

Record:
- Test status (all passing)
- Performance baseline
- Line count
- Complexity scores

### Step 2: Identify Issues (15 min)

**Code smells:**
- Long functions (>50 lines)
- Duplicated code (copy-paste)
- Deep nesting (>3 levels)
- Magic numbers
- God classes (>500 lines)
- Circular imports

**Find patterns:**
```bash
# Long functions
grep -n "^def\|^    def" [module]/*.py | awk -F: '{print $1}' | uniq -c | sort -rn

# TODOs/FIXMEs
grep -rn "TODO\|FIXME\|HACK" [module]/

# Duplicated code (manual inspection)
```

### Step 3: Plan Refactor (15 min)

**Refactor catalog:**

| Smell | Refactor | Example |
|---|---|---|
| Long function | Extract method | Split into smaller functions |
| Duplicated code | Extract common | Move to shared utility |
| Magic numbers | Named constants | `THRESHOLD = 0.95` |
| Deep nesting | Early return | Guard clauses |
| God class | Split responsibilities | Separate concerns |
| Tight coupling | Dependency injection | Pass deps as args |

**Write plan:**
1. Refactor A (low risk, high value)
2. Refactor B
3. Refactor C

**Risk assessment:**
- Low risk: Rename, extract constant
- Medium risk: Extract function, split class
- High risk: Change data structures, alter control flow

### Step 4: Refactor Incrementally (1-2 hours)

**One change at a time:**

1. Make single refactor change
2. Run tests: `pytest tests/[module]/ -v`
3. If pass: commit
4. If fail: revert, debug, retry
5. Repeat

**Example: Extract function**

Before:
```python
def process_data(data):
    # 50 lines of processing
    result = []
    for item in data:
        # 10 lines
        processed = transform(item)
        # 10 lines
        validated = validate(processed)
        # 10 lines
        result.append(validated)
    return result
```

After:
```python
def process_data(data):
    return [process_item(item) for item in data]

def process_item(item):
    processed = transform(item)
    validated = validate(processed)
    return validated
```

**Example: Extract constant**

Before:
```python
if score > 0.95:
    return "excellent"
```

After:
```python
EXCELLENCE_THRESHOLD = 0.95

if score > EXCELLENCE_THRESHOLD:
    return "excellent"
```

### Step 5: Validate (15 min)

**After all refactors:**

```bash
# All tests pass
python -m pytest -q

# No behavior change (compare outputs)
python -m pytest tests/[module]/ -v --tb=short

# Performance not degraded (compare to baseline)
python -m pytest tests/[module]/ --durations=10

# Trading check
python domdata/check_no_trading.py
```

### Step 6: Measure Improvements (10 min)

**Compare before/after:**

| Metric | Before | After | Change |
|---|---|---|---|
| Lines of code | XX | XX | -XX |
| Function count | XX | XX | +XX |
| Avg function length | XX | XX | -XX |
| Complexity score | XX | XX | -XX |
| Test duration | XXs | XXs | -Xs |

### Step 7: Document (5 min)

Update if refactor changes:
- Public API signatures
- Module structure
- Performance characteristics

---

## Validation

Refactor complete when:
- [ ] All tests pass (same as baseline)
- [ ] Performance same or better
- [ ] Code metrics improved
- [ ] No new warnings/errors
- [ ] Behavior unchanged (manual spot-check)

---

## Output

1. **Refactored code:** Modified files
2. **Comparison:** Before/after metrics
3. **Report:** What changed, why, metrics

---

## Common Pitfalls

**Don't:**
- Change behavior (refactor = same behavior, better structure)
- Refactor without tests (tests prevent regressions)
- Make multiple changes at once (hard to debug)
- Introduce new dependencies
- Sacrifice readability for cleverness

**Do:**
- Commit after each safe change
- Run tests frequently
- Keep changes small
- Improve names while refactoring
- Leave code better than you found it

---

## Refactoring Patterns

**Extract Method:**
```python
# Before
def big_function():
    # 100 lines

# After
def big_function():
    step1()
    step2()
    step3()
```

**Replace Magic Number:**
```python
# Before
if timeout > 300:

# After
TIMEOUT_THRESHOLD_SECONDS = 300
if timeout > TIMEOUT_THRESHOLD_SECONDS:
```

**Early Return:**
```python
# Before
def process(data):
    if data:
        if valid(data):
            return transform(data)
    return None

# After
def process(data):
    if not data:
        return None
    if not valid(data):
        return None
    return transform(data)
```

---

## Related Prompts

- [[CODEX_TESTING_PROMPT]] — Add tests before refactoring
- [[CODEX_BUGFIX_PROMPT]] — Fix bugs revealed by refactor

---

## Retrieval Hints

- "refactor code"
- "code quality"
- "technical debt"
- "refactoring patterns"
