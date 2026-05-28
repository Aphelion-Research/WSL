# Schema Migration Guide

**Status:** LIVE_GREEN (Schema evolution protocol)  
**Last Updated:** 2026-05-19  
**Owner:** MatinDeevv  
**Related:** [BREAKING_CHANGE_PROTOCOL.md](BREAKING_CHANGE_PROTOCOL.md)

---

## Overview

**Philosophy:** Additive-only migrations. No destructive operations. No data loss.

**Migration Systems:**
- **Agent OS:** Sequential migrations (`dominion_agent/migrations.py`)
- **Manifest:** Column-add migrations (`dominion_loader/manifest.py`)
- **RAGD:** SQL migration files (`ragd/sql/migrations/*.sql`)

**Current Schema Versions:**
- Agent OS: v2 (fix_locks_unique_constraint)
- Manifest: v1 (ragd_ingested columns)
- RAGD: migrations 0002-0004 (kg_nodes, ledger_entries, profile_spans)

---

## Migration Principles

### Principle 1: Additive Only

**Rule:** Add columns/tables, never drop or rename.

**Why:** Avoids data loss. Old code continues working with new schema.

**Example (Good):**
```sql
-- Migration 2: Add ragd_ingested_at column
ALTER TABLE file_manifest ADD COLUMN ragd_ingested_at INTEGER;
```

**Example (Bad):**
```sql
-- DON'T DO THIS
ALTER TABLE file_manifest DROP COLUMN indexed_at;
ALTER TABLE file_manifest RENAME COLUMN mtime_ns TO modified_at;
```

**Workaround for Rename:**
1. Add new column
2. Backfill data from old column
3. Deprecate old column (leave in schema, stop using)
4. Remove old column in future major version (with explicit migration guide)

---

### Principle 2: Guarded Execution

**Rule:** Check if migration already applied before executing.

**Why:** Idempotent — safe to run multiple times.

**Example:**
```python
# dominion_loader/manifest.py:128-139
def _apply_migrations(self):
    for table, col, definition in _MIGRATIONS_V1:
        existing_cols = {
            row[1]
            for row in self._conn.execute(f"PRAGMA table_info({table})")
        }
        if col not in existing_cols:  # Guard: only add if missing
            self._conn.execute(
                f"ALTER TABLE {table} ADD COLUMN {col} {definition}"
            )
```

**Alternative (Migration Table):**
```python
# dominion_agent/migrations.py:215-240
def apply_migrations(conn):
    applied = {row["version"] for row in conn.execute(
        "SELECT version FROM agent_os_migrations"
    )}
    for version, name in _MIGRATIONS:
        if version in applied:  # Guard: skip if already applied
            continue
        sql = _MIGRATION_SQL[version]
        conn.executescript(sql)
        conn.execute(
            "INSERT INTO agent_os_migrations(version, name, applied_at) VALUES(?,?,?)",
            (version, name, int(time.time())),
        )
```

---

### Principle 3: Versioned Schema

**Rule:** Track schema version in `kv_store('schema_version')` or `migrations` table.

**Why:** Detect schema drift, ensure migrations applied.

**Example (Manifest):**
```python
# dominion_loader/manifest.py:23
CURRENT_SCHEMA_VERSION = 1

# dominion_loader/manifest.py:118-126
def _init_schema(self):
    self._conn.executescript(_SCHEMA_SQL)
    self._apply_migrations()
    version = self._conn.execute(
        "SELECT value FROM kv_store WHERE key='schema_version'"
    ).fetchone()
    if version is None:
        self._conn.execute(
            "INSERT OR REPLACE INTO kv_store(key, value) VALUES('schema_version', ?)",
            (str(CURRENT_SCHEMA_VERSION),),
        )
```

**Example (Agent OS):**
```python
# dominion_agent/migrations.py:19-23
CREATE TABLE IF NOT EXISTS agent_os_migrations(
    version INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    applied_at INTEGER NOT NULL
);
```

---

### Principle 4: No Breaking Changes

**Rule:** New columns must have defaults. Old code reads old columns.

**Why:** Allows gradual rollout. Old code (Agent 1) coexists with new code (Agent 2).

**Example (Good):**
```sql
-- Migration: Add ragd_ingested column with default
ALTER TABLE file_manifest ADD COLUMN ragd_ingested INTEGER NOT NULL DEFAULT 0;
```

**Example (Bad):**
```sql
-- DON'T DO THIS (no default → breaks old code)
ALTER TABLE file_manifest ADD COLUMN ragd_ingested INTEGER NOT NULL;
```

---

## Migration Workflow

### Step 1: Design Migration

**Checklist:**
- [ ] Additive only (no DROP, no RENAME)
- [ ] New columns have defaults
- [ ] No data loss
- [ ] Idempotent (safe to run multiple times)
- [ ] Versioned (migration number/name)

**Template:**
```python
# migrations.py
_MIGRATION_N_SQL = """
-- Migration N: <description>
BEGIN;

-- Add new table (IF NOT EXISTS)
CREATE TABLE IF NOT EXISTS new_table(
    id INTEGER PRIMARY KEY,
    ...
);

-- Add new column to existing table
ALTER TABLE existing_table ADD COLUMN new_col TYPE DEFAULT <value>;

-- Create index
CREATE INDEX IF NOT EXISTS idx_new_table_col ON new_table(col);

COMMIT;
"""
```

---

### Step 2: Write Migration Code

**Agent OS (Sequential Migrations):**
```python
# dominion_agent/migrations.py

# Add to _MIGRATIONS list
_MIGRATIONS = [
    (1, "init_agent_os"),
    (2, "fix_locks_unique_constraint"),
    (3, "add_review_verdict_column"),  # New migration
]

# Add SQL
_MIGRATION_3_SQL = """
BEGIN;
ALTER TABLE agent_reviews ADD COLUMN verdict TEXT DEFAULT 'unknown';
COMMIT;
"""

_MIGRATION_SQL = {
    1: _MIGRATION_1_SQL,
    2: _MIGRATION_2_SQL,
    3: _MIGRATION_3_SQL,  # Register
}
```

**Manifest (Column Migrations):**
```python
# dominion_loader/manifest.py

# Update version
CURRENT_SCHEMA_VERSION = 2

# Add to _MIGRATIONS_V1 list
_MIGRATIONS_V2 = [
    ("file_manifest", "ragd_ingested", "INTEGER NOT NULL DEFAULT 0"),
    ("file_manifest", "ragd_ingested_at", "INTEGER"),
    ("file_manifest", "embedding_version", "TEXT DEFAULT 'nomic-v1'"),  # New
]
```

**RAGD (SQL Files):**
```bash
# Create new migration file
cat > ragd/sql/migrations/0005_add_temporal_edges.sql <<EOF
-- Migration 0005: Temporal edges for time-travel queries
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS temporal_edges(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_id TEXT NOT NULL,
    to_id TEXT NOT NULL,
    relation TEXT NOT NULL,
    valid_from INTEGER NOT NULL,
    valid_to INTEGER,
    created_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_temporal_edges_valid
    ON temporal_edges(from_id, to_id, valid_from, valid_to);
EOF
```

---

### Step 3: Test Migration

**Manual Test:**
```bash
# 1. Create test DB with old schema
sqlite3 test.db <<EOF
CREATE TABLE file_manifest(
    document_id TEXT PRIMARY KEY,
    content_hash TEXT NOT NULL
);
INSERT INTO file_manifest VALUES('doc1', 'abc123');
EOF

# 2. Run migration (via Python)
python -c "
from dominion_loader.manifest import Manifest
m = Manifest('test.db')
entry = m.get('doc1')
print(entry)
# Verify new columns present (ragd_ingested, ragd_ingested_at)
"

# 3. Verify data preserved
sqlite3 test.db "SELECT * FROM file_manifest;"
# Expected: doc1 still present, new columns with defaults
```

**Automated Test:**
```python
# dominion_agent/tests/test_migrations.py
def test_migration_2_preserves_data(tmp_path):
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    
    # Create schema v1
    conn.execute(_MIGRATION_1_SQL)
    
    # Insert data
    conn.execute("INSERT INTO agent_file_locks VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                 ("lock1", "/a.py", "session1", "task1", "write", "active", 
                  123, None, None, ""))
    conn.commit()
    
    # Apply migration 2
    apply_migrations(conn)
    
    # Verify data preserved
    row = conn.execute("SELECT * FROM agent_file_locks WHERE lock_id='lock1'").fetchone()
    assert row is not None
    assert row[1] == "/a.py"  # filepath preserved
```

---

### Step 4: Deploy Migration

**Deployment Steps:**
1. Merge migration PR to main
2. Deploy new code (migration runs on first import)
3. Verify schema version updated (`SELECT * FROM agent_os_migrations`)
4. Monitor logs for migration errors

**Rollback Plan:**
- If migration fails, old code continues working (additive migrations don't break old code)
- Fix migration bug, redeploy
- No manual rollback needed

---

## Migration Patterns

### Pattern 1: Add Column

**Use Case:** Add optional metadata to existing table.

**Example:**
```sql
-- Add column with default
ALTER TABLE agent_tasks ADD COLUMN evidence_json TEXT DEFAULT '{}';
```

**Code Change:**
```python
# Before
@dataclass
class Task:
    task_id: str
    title: str

# After (backward compatible)
@dataclass
class Task:
    task_id: str
    title: str
    evidence_json: str = "{}"  # Default for old rows
```

---

### Pattern 2: Add Table

**Use Case:** New feature requires new storage.

**Example:**
```sql
-- Add table
CREATE TABLE IF NOT EXISTS agent_reviews(
    review_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at INTEGER NOT NULL
);

-- Add index
CREATE INDEX IF NOT EXISTS idx_reviews_task ON agent_reviews(task_id);
```

---

### Pattern 3: Add Index

**Use Case:** Query performance degraded, need index.

**Example:**
```sql
-- Add index (idempotent)
CREATE INDEX IF NOT EXISTS idx_tasks_status ON agent_tasks(status);
```

**Note:** Indexes are additive, no data loss. Safe to run multiple times.

---

### Pattern 4: Migrate Table (Rare)

**Use Case:** Constraint change requires table recreation (e.g., UNIQUE constraint).

**Example (Agent OS Migration 2):**
```sql
BEGIN;

-- Create new table with corrected UNIQUE constraint
CREATE TABLE IF NOT EXISTS agent_file_locks_v2(
    lock_id TEXT PRIMARY KEY,
    filepath TEXT NOT NULL,
    session_id TEXT NOT NULL,
    UNIQUE(filepath, session_id)  -- Fixed: was UNIQUE(filepath, status)
);

-- Copy data
INSERT OR IGNORE INTO agent_file_locks_v2
    SELECT * FROM agent_file_locks;

-- Drop old table
DROP TABLE IF EXISTS agent_file_locks;

-- Rename
ALTER TABLE agent_file_locks_v2 RENAME TO agent_file_locks;

COMMIT;
```

**Risks:**
- Data loss if INSERT fails (use IGNORE or REPLACE)
- Downtime during migration (locks table briefly)

**Mitigation:**
- Wrap in transaction (atomic)
- Test on backup DB first
- Run during low-traffic window

---

### Pattern 5: Backfill Data

**Use Case:** New column requires backfilling from existing data.

**Example:**
```sql
-- Add column
ALTER TABLE file_manifest ADD COLUMN embedding_version TEXT DEFAULT 'unknown';

-- Backfill (separate step, can be slow)
UPDATE file_manifest SET embedding_version='nomic-v1' WHERE indexed_at > 0;
```

**Note:** Backfill in separate migration (don't block initial migration on slow UPDATE).

---

## Migration Testing

### Test 1: Idempotency

**Goal:** Verify migration can run multiple times without error.

**Test:**
```bash
# Run migration 3 times
for i in {1..3}; do
  python -c "from dominion_agent.store import AgentStore; AgentStore()"
done

# Verify no errors, schema version still correct
```

---

### Test 2: Data Preservation

**Goal:** Verify existing data not lost.

**Test:**
```python
def test_migration_preserves_data():
    # Create DB with old schema + data
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE agent_tasks(task_id TEXT PRIMARY KEY, title TEXT)")
    conn.execute("INSERT INTO agent_tasks VALUES('t1', 'Test task')")
    
    # Apply migration
    apply_migrations(conn)
    
    # Verify data preserved
    row = conn.execute("SELECT * FROM agent_tasks WHERE task_id='t1'").fetchone()
    assert row["title"] == "Test task"
```

---

### Test 3: Backward Compatibility

**Goal:** Verify old code works with new schema.

**Test:**
```python
# Old code (doesn't know about new columns)
def create_task_v1(conn, task_id, title):
    conn.execute("INSERT INTO agent_tasks(task_id, title) VALUES(?,?)",
                 (task_id, title))

# Run old code after migration
conn = sqlite3.connect(":memory:")
apply_migrations(conn)  # New schema (v2) with evidence_json column
create_task_v1(conn, "t1", "Test")  # Old code (v1)

# Verify task created, new column has default
row = conn.execute("SELECT * FROM agent_tasks WHERE task_id='t1'").fetchone()
assert row["evidence_json"] == "{}"  # Default value
```

---

### Test 4: Forward Compatibility

**Goal:** Verify new code works with old schema (before migration).

**Test:**
```python
# New code (expects evidence_json column)
def create_task_v2(conn, task_id, title, evidence):
    conn.execute("INSERT INTO agent_tasks(task_id, title, evidence_json) VALUES(?,?,?)",
                 (task_id, title, evidence))

# Run new code before migration (should fail gracefully)
conn = sqlite3.connect(":memory:")
conn.execute("CREATE TABLE agent_tasks(task_id TEXT PRIMARY KEY, title TEXT)")

try:
    create_task_v2(conn, "t1", "Test", "{}")
except sqlite3.OperationalError as e:
    assert "no such column: evidence_json" in str(e)  # Expected error
```

**Mitigation:** Check column exists before inserting (defensive coding).

---

## Schema Inspection

### Inspect Agent OS Schema

```bash
# List tables
sqlite3 ~/.dominion/agent_os.db "SELECT name FROM sqlite_master WHERE type='table';"

# Show schema for agent_tasks
sqlite3 ~/.dominion/agent_os.db ".schema agent_tasks"

# List applied migrations
sqlite3 ~/.dominion/agent_os.db "SELECT * FROM agent_os_migrations;"
# Expected:
# 1|init_agent_os|1714320000
# 2|fix_locks_unique_constraint|1715280000
```

---

### Inspect Manifest Schema

```bash
# Show schema
sqlite3 ~/.dominion/manifest.db ".schema file_manifest"

# Check schema version
sqlite3 ~/.dominion/manifest.db "SELECT * FROM kv_store WHERE key='schema_version';"
# Expected: schema_version|1
```

---

### Inspect RAGD Schema

```bash
# List tables
sqlite3 ~/.ragd/ragd.db "SELECT name FROM sqlite_master WHERE type='table';"

# Show ledger schema
sqlite3 ~/.ragd/ragd.db ".schema ledger_entries"

# Check if migration 0003 applied
sqlite3 ~/.ragd/ragd.db "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='ledger_entries';"
# Expected: 1 (table exists)
```

---

## Migration History

### Agent OS Migrations

| Version | Name | Description | Applied |
|---------|------|-------------|---------|
| 1 | init_agent_os | Initial schema (sessions, tasks, claims, locks, touches, reviews, compilations, complexity, events) | 2026-04-15 |
| 2 | fix_locks_unique_constraint | Fix `agent_file_locks` UNIQUE constraint (was `UNIQUE(filepath, status)`, now `UNIQUE(filepath, session_id)`) | 2026-05-10 |

**Migration 2 Details:**
- **Problem:** `UNIQUE(filepath, status)` blocked multiple read locks on same file.
- **Solution:** Change to `UNIQUE(filepath, session_id)` (allows multiple sessions to read, prevents double-lock by same session).
- **Impact:** Requires table recreation (DROP + RENAME), wrapped in transaction for atomicity.

---

### Manifest Migrations

| Version | Columns Added | Description | Applied |
|---------|---------------|-------------|---------|
| 1 | ragd_ingested, ragd_ingested_at | Track RAGD ingestion status per file | 2026-03-20 |

**Migration 1 Details:**
- **Columns:** `ragd_ingested INTEGER NOT NULL DEFAULT 0`, `ragd_ingested_at INTEGER`
- **Use Case:** Agent OS needs to know which files ingested to RAGD (avoid re-indexing).
- **Backward Compat:** Old code ignores new columns, defaults to 0 (not ingested).

---

### RAGD Migrations

| File | Tables Added | Description | Applied |
|------|--------------|-------------|---------|
| 0002_kg_nodes_edges.sql | kg_nodes, kg_edges | Knowledge graph storage | 2026-02-10 |
| 0003_ledger_entries.sql | ledger_entries, ledger_tags | Multi-agent memory ledger | 2026-03-15 |
| 0004_profile_spans.sql | profile_spans | Query profiling traces | 2026-04-01 |

**Note:** RAGD migrations applied manually (not automatic). Run via:
```bash
sqlite3 ~/.ragd/ragd.db < ragd/sql/migrations/0003_ledger_entries.sql
```

---

## Troubleshooting

### Issue 1: Migration Not Applied

**Symptom:** Column missing after migration.

**Diagnosis:**
```bash
# Check if migration applied
sqlite3 ~/.dominion/agent_os.db "SELECT * FROM agent_os_migrations WHERE version=2;"
# If empty, migration not applied
```

**Fix:**
```python
# Force migration
from dominion_agent.store import AgentStore
store = AgentStore()  # Migrations run on __init__
```

---

### Issue 2: Migration Fails (Column Already Exists)

**Symptom:** `sqlite3.OperationalError: duplicate column name`

**Root Cause:** Migration not guarded (ran twice).

**Fix:** Add guard:
```python
def _apply_migrations(self):
    for table, col, definition in _MIGRATIONS_V1:
        existing_cols = {row[1] for row in self._conn.execute(f"PRAGMA table_info({table})")}
        if col not in existing_cols:  # Guard
            self._conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {definition}")
```

---

### Issue 3: Data Lost After Migration

**Symptom:** Rows missing after table recreation.

**Root Cause:** `INSERT` failed during migration 2 (table copy).

**Diagnosis:**
```sql
-- Check row count before/after
SELECT COUNT(*) FROM agent_file_locks;  -- Before migration
-- (run migration)
SELECT COUNT(*) FROM agent_file_locks;  -- After migration
```

**Fix:** Use `INSERT OR IGNORE` (skip duplicates) or `INSERT OR REPLACE` (overwrite duplicates).

---

### Issue 4: Schema Version Mismatch

**Symptom:** Code expects v2 schema, DB has v1.

**Diagnosis:**
```bash
sqlite3 ~/.dominion/manifest.db "SELECT value FROM kv_store WHERE key='schema_version';"
# Output: 1 (expected: 2)
```

**Fix:** Run migrations manually:
```python
from dominion_loader.manifest import Manifest
m = Manifest()  # Migrations run on __init__
```

---

## Best Practices

### Practice 1: Always Add Defaults

**Rule:** New columns must have `DEFAULT <value>` or be nullable.

**Why:** Old code doesn't provide new columns during INSERT.

**Example:**
```sql
-- Good
ALTER TABLE agent_tasks ADD COLUMN evidence_json TEXT DEFAULT '{}';

-- Bad (breaks old code)
ALTER TABLE agent_tasks ADD COLUMN evidence_json TEXT NOT NULL;
```

---

### Practice 2: Test on Backup First

**Rule:** Test migration on copy of production DB before deploying.

**Why:** Catch errors before production impact.

**Example:**
```bash
# Copy production DB
cp ~/.dominion/agent_os.db agent_os_backup.db

# Test migration
python -c "from dominion_agent.store import AgentStore; AgentStore('agent_os_backup.db')"

# Verify schema
sqlite3 agent_os_backup.db ".schema agent_tasks"
```

---

### Practice 3: Document Breaking Changes

**Rule:** If migration requires code changes, document in [BREAKING_CHANGE_PROTOCOL.md](BREAKING_CHANGE_PROTOCOL.md).

**Example:**
```markdown
# Breaking Change: agent_file_locks UNIQUE constraint

**Version:** Agent OS v2  
**Date:** 2026-05-10

**Change:** UNIQUE constraint changed from `(filepath, status)` to `(filepath, session_id)`.

**Impact:** Old code may fail to acquire read locks if new constraint violated.

**Migration:** Automatic (migration 2 recreates table).

**Action Required:** Update code that assumes `UNIQUE(filepath, status)`.
```

---

### Practice 4: Version APIs, Not Just Schemas

**Rule:** If migration changes API contract (e.g., required fields), bump API version.

**Example:**
```python
# Old API (v1)
def create_task(task_id, title):
    pass

# New API (v2)
def create_task(task_id, title, evidence=None):
    pass

# Support both
def create_task_v2(task_id, title, evidence="{}"):
    create_task(task_id, title)
    # Update evidence separately
```

---

## Related

- [BREAKING_CHANGE_PROTOCOL.md](BREAKING_CHANGE_PROTOCOL.md) — Breaking change handling
- [AGENT_OS_ARCHITECTURE.md](../01_ARCHITECTURE/AGENT_OS_ARCHITECTURE.md) — Agent OS schema design

---

**Last Updated:** 2026-05-19  
**Verified By:** Claude Code (Sonnet 4.5)  
**Review Status:** ✓ Migration patterns validated against Agent OS/Manifest/RAGD
