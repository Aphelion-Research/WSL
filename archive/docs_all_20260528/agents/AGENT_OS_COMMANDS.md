# Dominion Agent OS — Command Reference

All commands: `python scripts/dominion_cli.py agent <COMMAND> [OPTIONS]`

Add `--json` to any command for machine-readable output.

---

## Session Commands

### `agent init`
Start a new agent session.
```
agent init --name NAME --role ROLE [--meta JSON] [--parent SESSION_ID] [--json]
```
Roles: `foundation`, `retrieval`, `truth`, `orchestrator`, `review`, `docs`, `test`, `operator`, `unknown`

### `agent heartbeat SESSION_ID`
Update last_heartbeat for a session.
```
agent heartbeat sess_abc123 [--json]
```

### `agent end SESSION_ID`
End a session with a terminal status.
```
agent end sess_abc123 --status completed|failed|abandoned [--summary TEXT] [--json]
```

### `agent sessions`
List sessions.
```
agent sessions [--active] [--stale] [--json]
```

### `agent session abandon SESSION_ID`
Force-abandon a session (emergency).
```
agent session abandon sess_abc123 [--json]
```

---

## Task Commands

### `agent task create`
```
agent task create --session SESSION_ID --title TITLE --kind KIND
  [--scope FILES] [--commands CMDS] [--criteria CRITERIA]
  [--priority 1-5] [--json]
```
Kinds: `code`, `research`, `review`, `docs`, `test`, `ops`, `audit`

### `agent task list`
```
agent task list --session SESSION_ID [--status STATUS] [--json]
```

### `agent task show TASK_ID`
```
agent task show task_abc123 [--json]
```

### `agent task claim TASK_ID`
```
agent task claim task_abc123 --session SESSION_ID [--json]
```

### `agent task release TASK_ID`
```
agent task release task_abc123 --session SESSION_ID [--json]
```

### `agent task status TASK_ID`
```
agent task status task_abc123 --status STATUS [--evidence JSON]
  [--force] [--json]
```

---

## Lock Commands

### `agent lock acquire`
```
agent lock acquire --file FILEPATH --session SESSION_ID
  [--task TASK_ID] [--mode read|write|exclusive|review]
  [--ttl SECONDS] [--note TEXT] [--json]
```

### `agent lock release LOCK_ID`
```
agent lock release lock_abc123 [--json]
```

### `agent locks`
```
agent locks [--file FILEPATH] [--session SESSION_ID] [--json]
```

---

## Analysis Commands

### `agent conflict check`
```
agent conflict check --file FILEPATH [--session SESSION_ID] [--json]
```
Checks: active write lock, dirty worktree, shared interface, secret path, overlapping task scope, migration collision.

### `agent impact --package PACKAGE`
```
agent impact --package PACKAGE [--json]
```
Returns required and optional validation commands for the given package.

### `agent prompt --task TASK_ID`
```
agent prompt --task task_abc123 [--json]
```
Compile a full structured prompt for the task (queries RAGD for context).

### `agent review --task TASK_ID`
```
agent review --task task_abc123 [--json]
```
Run adversarial review on a task. Returns findings, score, verdict.

---

## Architecture Commands

### `agent architecture refresh`
```
agent architecture refresh [--json]
```
Regenerates `docs/agents/LIVING_ARCHITECTURE.md`.

### `agent architecture show`
```
agent architecture show [--json]
```
Print current architecture snapshot.

---

## Complexity Commands

### `agent complexity report`
```
agent complexity report [--package PACKAGE] [--json]
```
Scan packages and report complexity scores vs budgets.

### `agent complexity budget --package PACKAGE`
```
agent complexity budget --package PACKAGE [--json]
```
Show detailed budget breakdown for a specific package.

---

## RAGD Commands

### `agent sync-ragd`
```
agent sync-ragd [--json]
```
Ping RAGD health endpoint and record event.

---

## Quick Start

```bash
# Start a session
python scripts/dominion_cli.py agent init --name my-agent --role orchestrator --json

# Create a task
python scripts/dominion_cli.py agent task create \
  --session sess_abc123 \
  --title "Refactor safety.py" \
  --kind code \
  --scope '["dominion_agent/safety.py"]' \
  --json

# Check for conflicts
python scripts/dominion_cli.py agent conflict check --file dominion_agent/safety.py --json

# Get complexity report
python scripts/dominion_cli.py agent complexity report --json
```
