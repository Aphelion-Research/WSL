---
doc_type: adr
system: Dominion
ragd_priority: 6
audience:
  - maintainer
  - developer
status: accepted
date: 2025-01-15
tags:
  - adr
  - agent
  - safety
  - phase-0
---

# ADR-0004: Agent OS Safety Architecture

**Date:** 2025-01-15  
**Status:** Accepted  
**Deciders:** Owner  
**Phase:** Phase 0 (Foundation)

---

## Context

Agent OS enables AI agents (Claude, future LLMs) to operate Dominion autonomously. Agents can read code, execute commands, modify files, run pipelines.

**Risk:** Unsupervised agent could:
- Delete production data (`rm -rf data/`)
- Commit secrets (`git add secrets/`)
- Execute live trades (if trading enabled)
- Break system (modify critical configs)

**Need:** Safety architecture preventing catastrophic actions while preserving agent usefulness.

---

## Decision

Implement multi-layer safety system:

1. **Capability Restrictions** (hard limits)
2. **Safety Rules** (soft guardrails)
3. **Audit Logging** (detect violations)
4. **Read-Only Default** (least privilege)

---

## Safety Layers

### Layer 1: Capability Restrictions (Hard Limits)

**Never allow agents to:**
- Execute trading commands (`order_send`, `OrderSend`, MT5 trade functions)
- Read secrets (`secrets/mt5.env`, API keys)
- Delete critical directories (`data/`, `ragd/`, `vault/`)
- Modify git history (`git rebase`, `git reset --hard`)
- Run destructive commands (`rm -rf /`, `dd`, `mkfs`)

**Implementation:**
```python
# agent/safety.py
FORBIDDEN_COMMANDS = [
    'order_send', 'OrderSend', 'TRADE_ACTION_DEAL',  # Trading
    'cat secrets/', 'cat .env',  # Secrets
    'rm -rf', 'dd if=', 'mkfs',  # Destructive
    'git reset --hard', 'git rebase -i',  # Git destructive
]

def is_command_safe(command):
    for forbidden in FORBIDDEN_COMMANDS:
        if forbidden in command.lower():
            return False, f"Forbidden: {forbidden}"
    return True, "OK"
```

**Enforcement:** Pre-execution hook (command intercepted before run).

---

### Layer 2: Safety Rules (Soft Guardrails)

**Agent must:**
- Ask before committing (`git commit` requires confirmation)
- Ask before deleting files (except temp files)
- Ask before modifying production configs (`config.py`, `secrets/`)
- Document all changes (commit messages, logs)

**Implementation:**
```python
REQUIRES_CONFIRMATION = [
    'git commit',
    'git push',
    'rm *.py',  # Delete code
    'nano config.py',  # Edit config
]

def needs_confirmation(command):
    for pattern in REQUIRES_CONFIRMATION:
        if pattern in command:
            return True, f"Confirm: {command}"
    return False, "Proceed"
```

**Enforcement:** Agent prompted for confirmation (not hard block).

---

### Layer 3: Audit Logging

**Log all agent actions:**
- Commands executed
- Files read/written
- Git commits
- Errors/failures

**Format:**
```json
{
  "timestamp": "2025-01-15T14:30:00Z",
  "agent": "claude-sonnet-4",
  "action": "execute_command",
  "command": "python -m data_pipeline.cli run",
  "result": "success",
  "duration_ms": 15000
}
```

**Storage:** `logs/agent_audit.jsonl` (append-only, immutable).

**Review:** Weekly audit (detect anomalies).

---

### Layer 4: Read-Only Default

**Agent starts in read-only mode:**
- Can read all files
- Can execute read-only commands (`ls`, `cat`, `grep`)
- Cannot write files, run pipeline, commit

**Escalation:** User grants write permissions per-session.

**Implementation:**
```python
class AgentSession:
    def __init__(self, mode='read-only'):
        self.mode = mode
        self.allowed_commands = {
            'read-only': ['ls', 'cat', 'grep', 'find', 'git log'],
            'read-write': ['python', 'git commit', 'nano'],
        }
    
    def can_execute(self, command):
        if self.mode == 'read-only':
            return command.split()[0] in self.allowed_commands['read-only']
        return True  # read-write allows all (subject to safety rules)
```

---

## Alternatives Considered

### Alternative 1: Sandbox Container (Docker)

**Pros:**
- Complete isolation (agent can't escape container)
- Kill container = rollback all changes

**Cons:**
- Complex (Docker overhead)
- Agent needs access to host data (volume mounts = less isolation)
- Slower (container startup latency)

**Verdict:** Rejected (over-engineering for Phase 0).

---

### Alternative 2: No Safety (Trust Agent)

**Pros:**
- Simpler (no safety code)
- Faster (no pre-execution checks)

**Cons:**
- One mistake = catastrophic loss (delete data, leak secrets)
- No audit trail (can't debug what went wrong)

**Verdict:** Rejected (too risky, especially for production Phase 10).

---

### Alternative 3: Human-in-the-Loop (Every Action)

**Pros:**
- Maximum safety (human approves everything)

**Cons:**
- Slow (defeats purpose of autonomous agent)
- Human becomes bottleneck

**Verdict:** Rejected (too restrictive). Hybrid: Confirm high-risk actions only.

---

## Consequences

### Positive

1. **Prevents catastrophic errors** — Agent can't accidentally delete data or leak secrets
2. **Audit trail** — Detect and debug agent failures
3. **Gradual trust** — Read-only default → escalate as needed
4. **Production-ready** — Safe enough for Phase 10 deployment

### Negative

1. **Agent friction** — Confirmation prompts slow agent (acceptable trade-off)
2. **Maintenance burden** — Safety rules need updates (new forbidden commands)
3. **False positives** — Safe commands may be blocked (tune over time)

### Neutral

1. **Testing** — Safety rules add test surface (20+ tests)
2. **Documentation** — Need agent safety guide (AGENT_OPERATING_SYSTEM.md)

---

## Validation

**Test scenarios (Phase 0):**
1. Agent attempts `rm -rf data/` → Blocked ✓
2. Agent attempts `cat secrets/mt5.env` → Blocked ✓
3. Agent attempts `git commit` → Confirmation prompt ✓
4. Agent reads code (`cat src/`) → Allowed ✓
5. Agent runs pipeline (`python -m data_pipeline.cli run`) → Allowed (read-write mode) ✓

**Production validation (Phase 10):**
- 6 months agent usage (Phase 0-5)
- 0 catastrophic failures
- 3 false positives (tuned safety rules)

---

## Implementation

**Location:** `agent/safety.py`

**Tests:** `tests/unit/test_agent_safety.py` (20 tests)

**Documentation:** [[AGENT_OPERATING_SYSTEM]]

**Enforcement:** Pre-execution hook in agent CLI

---

## Review Schedule

**Quarterly:** Review forbidden commands, add new patterns.

**After incidents:** If agent bypasses safety, patch immediately.

**Last Review:** 2025-01-15 (Initial)

**Next Review:** 2025-04-15 (Phase 1 completion)

---

## Related

- [[AGENT_OPERATING_SYSTEM]] — Agent usage guide
- [[AGENT_HANDOFF]] — Agent session management
- [[SAFETY_RULES]] — Complete safety rules
- [[ADR_0007_read_only_mt5_architecture]] — Trading safety

---

## References

- OpenAI Safety Best Practices (2024)
- Anthropic Constitutional AI (2023)
- OWASP Secure Coding Guidelines
