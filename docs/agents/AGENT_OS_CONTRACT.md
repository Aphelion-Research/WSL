# Dominion Agent OS — Contract & API Guarantees

## What is Agent OS?

`dominion_agent/` is a local SQLite-backed operating system for code-editing agents. It enforces identity, task lifecycle, file locking, safety rules, adversarial review, and complexity budgets. No cloud. No AGI. No fake compliance.

---

## Core Invariants

1. **Sessions must exist before tasks** — every task must reference a valid active session.
2. **Tasks must exist before locks** — every lock must reference a valid task or session.
3. **No lock on secrets paths** — `secrets/`, `mt5.env`, `*_token_*`, `*_api_key_*` → raises `ValueError` unconditionally.
4. **No forbidden trading tokens** — `place_order`, `market_buy`, `OrderSend`, etc. are forbidden in task scope/commands/criteria. Use `check_no_trading.py` to verify.
5. **Evidence required to close** — `update_task_status(task_id, "done")` raises if no evidence provided (unless `force=True`).
6. **File locks are session-scoped** — a session may hold one lock per file; different sessions may hold concurrent read locks but not concurrent write/exclusive locks.

---

## Session Lifecycle

```
start_session(name, role) → Session
  │
  ├── heartbeat(session_id)        # every N minutes
  ├── end_session(session_id, "completed"|"failed"|"abandoned")
  │
  └── Tasks / Locks / Claims attached to session_id
```

Valid roles: `foundation`, `retrieval`, `truth`, `orchestrator`, `review`, `docs`, `test`, `operator`, `unknown`

Stale threshold: **30 minutes** without heartbeat → `is_stale=True`.

---

## Task Lifecycle

```
create_task(session_id, title, kind, scope, commands, criteria)
  │
  ├── update_task_status(task_id, "in_progress")
  ├── claim_task(task_id, session_id)          # register ownership
  ├── release_task(task_id, session_id)        # release ownership
  └── update_task_status(task_id, "done", evidence={...})
```

Valid task kinds: `code`, `research`, `review`, `docs`, `test`, `ops`, `audit`

Valid status transitions: `pending→in_progress→review→done|failed`, `failed→pending` (reopen)

---

## File Lock Conflict Matrix

| Requester ↓ \ Holder → | read | write | exclusive | review |
|-------------------------|------|-------|-----------|--------|
| **read**                | OK   | BLOCK | BLOCK     | OK     |
| **write**               | BLOCK| BLOCK | BLOCK     | BLOCK  |
| **exclusive**           | BLOCK| BLOCK | BLOCK     | BLOCK  |
| **review**              | OK   | BLOCK | BLOCK     | OK     |

Secrets paths block ALL modes unconditionally (raises `ValueError`).

---

## Store Injection Pattern

All API functions accept `store: Optional[AgentStore] = None`. If `None`, a store is created for the call and closed afterwards. For batched operations, pass a shared store:

```python
from dominion_agent.store import AgentStore
from dominion_agent.api import *

with AgentStore() as s:
    sess = start_session("agent-1", "orchestrator", store=s)
    task = create_task(sess.session_id, "My task", "code", store=s)
    lock = acquire_lock("src/main.py", sess.session_id, task.task_id, "write", store=s)
```

---

## Mutation Rules

- DB path: `~/.dominion/agent_os.db` (SQLite WAL mode, autocommit)
- ID prefixes: `sess_`, `task_`, `claim_`, `lock_`, `touch_`, `rev_`, `comp_`, `snap_`, `event_`
- All timestamps: Unix integers
- All JSON fields: always valid JSON (empty dict `{}` default, not NULL)
- migrations are idempotent — safe to run multiple times

---

## Safety Hard Stops

`safety.py::validate_task_payload(payload)` raises `ValueError` with details when:
- Any `scope_files` entry is a secrets path
- Any `commands` entry contains forbidden trading tokens
- Any `criteria` entry contains forbidden trading tokens
