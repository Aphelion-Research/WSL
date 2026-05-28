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
  - workflow
---

# Development Guide

## Getting Started

1. Read [/AGENT_HANDOFF.md](/AGENT_HANDOFF.md)
2. Query RAGD for task context
3. Read relevant docs
4. Inspect code
5. Make plan
6. Execute
7. Validate
8. Document
9. Commit

## Development Environment

**Required:**
- Python 3.11+
- WSL2/Debian (or Linux)
- CMake 3.20+
- GCC 11+ (for C++)
- Git

**Setup:**
```bash
cd ~/Dominion
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
./scripts/bootstrap_python.sh
```

## Coding Standards

- Python: PEP 8 (black formatter compatible)
- C++: C++17 standard
- Naming: `lowercase_with_underscores` for functions/variables
- Classes: `UpperCamelCase`
- Constants: `UPPER_CASE`
- Private members: `_leading_underscore`

## File Structure

- One module per file
- Tests in `<module>/tests/test_*.py`
- CLI in `<module>/cli.py` or `<module>_cli.py`
- Keep files under 500 lines when possible

## Error Handling

- Use exceptions for exceptional cases
- Log errors clearly with context
- Fail closed, not open
- Provide actionable error messages
- Don't swallow exceptions

## Testing

See [TESTING_GUIDE.md](TESTING_GUIDE.md) for full testing strategy.

Quick:
```bash
python -m pytest -q  # All tests
python -m pytest -q <module>/tests/  # Module tests
ctest --test-dir ragd/build  # C++ tests
```

## Documentation

- Update docs when behavior changes
- Add docstrings to public functions
- Use type hints
- Write ADRs for architectural decisions

## Git Workflow

- Work on main (small team)
- Make atomic commits
- Use conventional commit format
- Don't force-push to main
- Don't commit secrets or large binaries

## Validation

Before claiming done:
```bash
python domdata/check_no_trading.py  # PASS
python -m pytest -q                 # All pass
python scripts/dominion_cli.py doctor --offline --json  # warn or ok
```

## Related Docs

- [CODING_STANDARDS.md](CODING_STANDARDS.md)
- [TESTING_GUIDE.md](TESTING_GUIDE.md)
- [COMMIT_GUIDE.md](COMMIT_GUIDE.md)
- [DEBUGGING_GUIDE.md](DEBUGGING_GUIDE.md)

## Retrieval Hints

- "development guide"
- "how to develop"
- "coding standards"
- "setup environment"
