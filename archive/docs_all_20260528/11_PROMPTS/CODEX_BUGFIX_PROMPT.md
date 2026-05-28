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
  - bugfix
  - debugging
---

# CODEX Bugfix Prompt

**Use Case:** Debug + fix bug  
**Complexity:** Medium  
**Duration:** 30-90 minutes

---

## Context

Bug reported: [BUG_DESCRIPTION]

Source: [Failing test | User report | Health check | Manual testing]

Repository: `/home/Martin/Dominion`

---

## Mission

1. Reproduce bug
2. Find root cause
3. Fix bug
4. Add regression test
5. Validate

---

## Workflow

### Step 1: Reproduce (10-15 min)

**If failing test:**
```bash
python -m pytest tests/[module]/test_[file].py::test_[name] -v
```

**If user report:**
Create reproduction script:
```python
# reproduce_bug.py
from [module] import [function]

# Minimal reproduction
result = [function](bug_triggering_input)
print(f"Result: {result}")  # Should show bug
```

**If health check:**
```bash
python scripts/dominion_cli.py doctor --offline --json
# Check which subsystem failing
```

**Confirm reproduction:**
- [ ] Bug triggers consistently
- [ ] Minimal reproduction case identified
- [ ] Expected vs actual behavior clear

### Step 2: Gather Context (10 min)

```bash
# Query RAGD for context
python scripts/dominion_cli.py search "[bug area]" --top-k 5
python scripts/dominion_cli.py search "[error message]" --top-k 3

# Check recent changes
git log --oneline [affected_file] | head -10

# Related code
grep -rn "[function_name]" [module]/
```

Read:
- Implementation file
- Tests (especially passing tests nearby)
- Related docs

### Step 3: Form Hypothesis (5 min)

**Common bug categories:**
- Off-by-one error
- Null/None handling
- Type mismatch
- Race condition
- Missing validation
- Incorrect assumption

**Hypothesis format:**
```
I believe the bug is caused by [X]
because [evidence].
I expect fixing [Y] will resolve it.
```

### Step 4: Debug (15-30 min)

**Add debug logging:**
```python
import logging
logger = logging.getLogger(__name__)

def buggy_function(param):
    logger.debug(f"Input: {param}")
    result = process(param)
    logger.debug(f"After process: {result}")
    return result
```

**Use debugger (if complex):**
```bash
python -m pdb reproduce_bug.py
# (Pdb) break [file]:[line]
# (Pdb) continue
# (Pdb) print variable
```

**Binary search:**
If bug introduced recently:
```bash
git bisect start
git bisect bad  # Current (broken)
git bisect good [known_good_commit]
# Test at each step
```

**Root cause identified when:**
- [ ] Exact line causing bug found
- [ ] Why line causes bug understood
- [ ] Fix approach clear

### Step 5: Fix (10-20 min)

**Make minimal fix:**
- Change only what's necessary
- No "while we're here" changes
- No refactoring (separate task)

**Example fix patterns:**

**Null check:**
```python
# Before
def process(data):
    return data.value

# After
def process(data):
    if data is None:
        return None
    return data.value
```

**Validation:**
```python
# Before
def set_threshold(value):
    self.threshold = value

# After
def set_threshold(value):
    if not 0 <= value <= 1:
        raise ValueError(f"Threshold must be 0-1, got {value}")
    self.threshold = value
```

**Type handling:**
```python
# Before
def process(items):
    return sum(items)

# After
def process(items):
    if not items:
        return 0
    return sum(items)
```

### Step 6: Add Regression Test (10 min)

```python
def test_bug_[issue_number]_[brief_description]():
    """Regression test for bug where [description].
    
    Bug: [Link to issue or description]
    Fixed: 2026-05-19
    """
    # Setup: reproduce bug conditions
    input_data = create_bug_triggering_input()
    
    # Execute: should not raise/fail now
    result = buggy_function(input_data)
    
    # Verify: correct behavior
    assert result == expected_value
```

### Step 7: Validate (10 min)

```bash
# Regression test passes
python -m pytest tests/[module]/test_[file].py::test_bug_[issue] -v

# All tests pass
python -m pytest -q

# Original reproduction fixed
python reproduce_bug.py  # Should work now

# Trading check
python domdata/check_no_trading.py

# Platform health
python scripts/dominion_cli.py doctor --offline --json
```

### Step 8: Document (5 min)

**Update if needed:**
- Known limitations section (if bug reveals edge case)
- Error handling docs
- Comments in code (only if fix non-obvious)

**Don't:**
- Document the bug itself (git history has it)
- Add TODO comments (either fix or create issue)

---

## Validation

Bug fixed when:
- [ ] Regression test passes
- [ ] All existing tests pass
- [ ] Original bug reproduction fails (bug gone)
- [ ] No new warnings/errors
- [ ] Root cause understood + documented in commit message

---

## Output

1. **Fix:** Modified file(s)
2. **Test:** New regression test
3. **Commit message:**
   ```
   fix: [brief description]
   
   Root cause: [explanation]
   Fix: [what changed]
   Test: [regression test added]
   
   Fixes #[issue_number]
   ```

---

## Common Pitfalls

**Don't:**
- Fix symptoms (fix root cause)
- Add complexity (simplest fix wins)
- Skip regression test (bug will return)
- Change behavior unnecessarily
- Leave debug code (remove logging/prints)

**Do:**
- Understand why bug exists
- Fix at source (not workaround)
- Test edge cases
- Check similar code (same bug elsewhere?)
- Update related tests

---

## Debugging Techniques

**Print debugging:**
```python
print(f"DEBUG: variable={variable!r}")  # !r shows type
```

**Assertion debugging:**
```python
assert condition, f"Expected {expected}, got {actual}"
```

**Exception context:**
```python
try:
    risky_operation()
except Exception as e:
    logger.error(f"Failed: {e}", exc_info=True)  # Full traceback
    raise
```

---

## Related Prompts

- [[CODEX_TESTING_PROMPT]] — Add tests after fix
- [[CODEX_REFACTOR_PROMPT]] — If fix reveals code smells

---

## Retrieval Hints

- "fix bug"
- "debug issue"
- "bugfix workflow"
- "regression test"
