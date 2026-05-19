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
  - feature
  - implementation
---

# CODEX Feature Implementation Prompt

**Use Case:** Implement new feature  
**Complexity:** High  
**Duration:** 2-4 hours

---

## Context

You are implementing new feature in Dominion V2 repository.

User has requested: [FEATURE_NAME]

Repository: `/home/Martin/Dominion`

---

## Mission

Full feature lifecycle:
1. **Plan:** Query RAGD, understand architecture, design approach
2. **Implement:** Write code following patterns
3. **Test:** Write tests (aim 80%+ coverage)
4. **Document:** Update docs + vault
5. **Validate:** Run full validation suite
6. **Report:** Write final handoff

---

## Constraints

**Safety:**
- No trading code (`order_send`, `order_check`, `TRADE_ACTION_*`)
- No secrets in code
- No destructive operations without confirmation

**Architecture:**
- Follow existing patterns (check similar features first)
- Minimal dependencies (avoid new external packages if possible)
- Keep modules decoupled (Agent OS → RAGD → Data Pipeline independence)

**Code Quality:**
- Follow [[CODING_STANDARDS]]
- Type hints required
- Docstrings for public APIs
- Tests for all public functions

**Performance:**
- Profile if >10ms latency added
- No blocking operations in hot paths
- Lazy loading for heavy imports

---

## Workflow

### Phase 1: Plan (30-45 min)

**Step 1: Read handoff**
```bash
cat /home/Martin/Dominion/AGENT_HANDOFF.md
```

**Step 2: Query RAGD for context**
```bash
python scripts/dominion_cli.py search "[FEATURE_NAME]" --top-k 5
python scripts/dominion_cli.py search "similar to [FEATURE_NAME]" --top-k 3
python scripts/dominion_cli.py search "[MODULE_NAME] architecture" --top-k 3
```

**Step 3: Find similar features**
```bash
# Search for analogous implementations
grep -r "class [SimilarFeature]" --include="*.py"
find . -name "*[similar]*.py"
```

**Step 4: Review architecture docs**
Read:
- `docs/01_ARCHITECTURE/MODULE_MAP.md`
- `docs/01_ARCHITECTURE/DATA_FLOW.md`
- `docs/04_DEVELOPMENT/CODING_STANDARDS.md`

**Step 5: Design approach**
Write design notes (in scratch file or report):
- Files to create/modify
- Key classes/functions
- Data flow
- Integration points
- Test strategy

### Phase 2: Implement (1-2 hours)

**Step 6: Create files**
```bash
# Create module structure
mkdir -p [module_name]
touch [module_name]/__init__.py
touch [module_name]/[feature].py
touch [module_name]/config.py
```

**Step 7: Write core logic**
- Start with data structures (classes, schemas)
- Then core algorithm
- Then integration layer (CLI, API)
- Keep functions <50 lines

**Step 8: Add CLI (if user-facing)**
```python
# [module_name]/cli.py
import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--[param]", ...)
    args = parser.parse_args()
    # Call core logic
```

**Step 9: Add config (if needed)**
```python
# [module_name]/config.py
from pathlib import Path

[FEATURE]_CONFIG = {
    "param1": "value1",
    "param2": "value2"
}
```

### Phase 3: Test (30-60 min)

**Step 10: Write tests**
```bash
mkdir -p tests/[module_name]
touch tests/[module_name]/test_[feature].py
```

**Test template:**
```python
import pytest
from [module_name].[feature] import [Function]

def test_[function]_happy_path():
    result = [Function](valid_input)
    assert result.status == "ok"

def test_[function]_error_case():
    with pytest.raises(ValueError):
        [Function](invalid_input)

def test_[function]_edge_case():
    result = [Function](edge_input)
    assert result.value is not None
```

**Step 11: Run tests**
```bash
python -m pytest tests/[module_name]/ -v
```

### Phase 4: Document (20-30 min)

**Step 12: Update docs**
Create/update:
- `docs/05_FEATURES/[FEATURE_NAME]_FEATURE.md` (feature spec)
- `docs/01_ARCHITECTURE/MODULE_MAP.md` (add new module if created)
- `README.md` (if user-facing CLI)

**Step 13: Add docstrings**
```python
def feature_function(param: str) -> Result:
    """Brief one-liner.
    
    Longer description if needed.
    
    Args:
        param: Parameter description
        
    Returns:
        Result description
        
    Raises:
        ValueError: When invalid input
    """
```

**Step 14: Update vault**
```bash
python scripts/vault_sync.py
python scripts/dominion_cli.py vault doctor --json
```

### Phase 5: Validate (10-15 min)

**Step 15: Run full validation**
```bash
# Trading check (MANDATORY)
python domdata/check_no_trading.py

# All tests
python -m pytest -q

# C++ tests (if native code changed)
ctest --test-dir ragd/build --output-on-failure

# Platform health
python scripts/dominion_cli.py doctor --offline --json
```

**Step 16: Manual testing**
```bash
# Test CLI (if added)
python -m [module_name].cli --help
python -m [module_name].cli [test_command]

# Test API (if added)
python -c "from [module_name] import [feature]; print([feature]())"
```

### Phase 6: Finalize (15-20 min)

**Step 17: Update RAGD index**
```bash
python scripts/dominion_cli.py scan
```

**Step 18: Write final report**
Use [[CODEX_FINAL_REPORT_PROMPT]] or inline:

```markdown
# Feature Implementation Report: [FEATURE_NAME]

## What Changed
- Created: [files]
- Modified: [files]

## How It Works
[Brief description]

## Tests
- XX/XX passing
- Coverage: XX%

## Validation
- Trading check: PASS
- Platform health: [status]

## Known Limitations
[List any]

## Next Steps
[Suggested follow-ups]
```

---

## Validation

Feature complete when:
- [ ] Tests pass (aim 80%+ coverage)
- [ ] Trading check passes
- [ ] Platform health OK
- [ ] Docs updated
- [ ] Vault synced
- [ ] RAGD index rebuilt
- [ ] Manual testing confirms feature works
- [ ] Report written

---

## Output

1. **Code:** New/modified files
2. **Tests:** New test files (aim 80%+ coverage)
3. **Docs:** Feature spec + updated module docs
4. **Report:** Final handoff report

---

## Common Pitfalls

**Don't:**
- Skip planning phase (leads to rework)
- Write code before understanding architecture
- Forget tests (not optional)
- Leave TODOs in code (finish or create follow-up task)
- Skip validation (always run full suite)

**Do:**
- Query RAGD first (avoid reinventing wheel)
- Follow existing patterns (consistency > novelty)
- Write tests alongside code (not after)
- Keep functions small (<50 lines)
- Update docs immediately (not later)

---

## Follow-Up Prompts

After feature:
- If tests insufficient: [[CODEX_TESTING_PROMPT]]
- If docs incomplete: [[CODEX_DOC_UPDATE_PROMPT]]
- If performance concerns: Check profiling guide

---

## Retrieval Hints

- "implement feature"
- "feature implementation"
- "add new feature"
- "feature workflow"
