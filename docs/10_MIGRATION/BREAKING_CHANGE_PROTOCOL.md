# Breaking Change Protocol

**Status:** LIVE_GREEN (Breaking change handling)  
**Last Updated:** 2026-05-19  
**Owner:** MatinDeevv  
**Related:** [SCHEMA_MIGRATION_GUIDE.md](SCHEMA_MIGRATION_GUIDE.md), [DEPRECATED_FEATURES.md](../05_FEATURES/DEPRECATED_FEATURES.md)

---

## Overview

**Definition:** Breaking change = change that breaks existing code/workflows without modification.

**Philosophy:** Avoid breaking changes. When unavoidable, provide migration path + grace period.

**Historical Breaking Changes:** 2 major (Bedrock → Ollama, agent_file_locks UNIQUE constraint)

**Current Policy:**
- **Pre-production (Phase 0-5):** Breaking changes allowed (rapid iteration)
- **Production (Phase 6+):** Breaking changes require deprecation cycle (grace period ≥1 phase)

---

## Breaking Change Classification

### Severity 1: API Contract Change (Critical)

**Definition:** Function signature, return type, or error behavior changes.

**Examples:**
- Required parameter added
- Return type changed
- Exception type changed
- Endpoint removed

**Impact:** Immediate code failure.

**Example:**
```python
# Before (API v1)
def create_task(task_id: str, title: str):
    pass

# After (API v2) — BREAKING
def create_task(task_id: str, title: str, evidence: str):  # New required param
    pass

# Old code fails:
create_task("t1", "Test")  # TypeError: missing required argument 'evidence'
```

**Mitigation:** Add default value.
```python
# Fixed (backward compatible)
def create_task(task_id: str, title: str, evidence: str = "{}"):
    pass
```

---

### Severity 2: Schema Change (High)

**Definition:** Database schema changes that break existing queries.

**Examples:**
- Column removed
- Column renamed
- Table removed
- Constraint changed

**Impact:** Query failures, data loss risk.

**Example:**
```sql
-- Before
CREATE TABLE agent_file_locks(
    filepath TEXT NOT NULL,
    UNIQUE(filepath, status)
);

-- After — BREAKING (Migration 2)
CREATE TABLE agent_file_locks(
    filepath TEXT NOT NULL,
    UNIQUE(filepath, session_id)  -- Changed constraint
);
```

**Impact:** Code assuming `UNIQUE(filepath, status)` may violate new constraint.

**Mitigation:** See [SCHEMA_MIGRATION_GUIDE.md](SCHEMA_MIGRATION_GUIDE.md).

---

### Severity 3: Configuration Change (Medium)

**Definition:** Environment variable, config file format, or default value changes.

**Examples:**
- Env var renamed
- Config format changed (JSON → YAML)
- Default value changed
- Required config added

**Impact:** Silent failures, wrong behavior.

**Example:**
```python
# Before
RAGD_EMBED_PROVIDER = os.environ.get("RAGD_EMBED_PROVIDER", "bedrock")

# After — BREAKING
RAGD_EMBED_PROVIDER = os.environ.get("RAGD_EMBED_PROVIDER", "ollama")  # Default changed
```

**Impact:** Users with `bedrock` provider see unexpected behavior (calls Ollama instead).

**Mitigation:** Warn when old default detected.
```python
if "RAGD_EMBED_PROVIDER" not in os.environ:
    warnings.warn("RAGD_EMBED_PROVIDER not set, defaulting to 'ollama'. Set explicitly to suppress warning.")
```

---

### Severity 4: Data Format Change (Medium)

**Definition:** Serialization format, file format, or protocol changes.

**Examples:**
- JSON schema changed
- Parquet schema changed
- API request/response format changed
- Binary protocol version changed

**Impact:** Deserialization failures, data corruption.

**Example:**
```json
// Before (v1)
{
  "task_id": "t1",
  "title": "Test"
}

// After (v2) — BREAKING
{
  "id": "t1",        // Renamed: task_id → id
  "title": "Test",
  "evidence": {}     // New required field
}
```

**Impact:** Old code fails to parse v2 JSON (missing `task_id` key).

**Mitigation:** Version protocol, support both.
```python
def parse_task(data: dict):
    # Support both v1 (task_id) and v2 (id)
    task_id = data.get("id") or data.get("task_id")
    return Task(task_id=task_id, title=data["title"])
```

---

### Severity 5: Deprecation (Low)

**Definition:** Feature marked deprecated but still works.

**Examples:**
- Function deprecated (still callable, emits warning)
- Feature flag deprecated
- Old API endpoint deprecated (new endpoint available)

**Impact:** Warning logged, no immediate failure.

**Example:**
```python
# Deprecated function
@deprecated("Use create_task_v2() instead. Will be removed in v3.0.")
def create_task_v1(task_id, title):
    warnings.warn("create_task_v1 deprecated, use create_task_v2")
    return create_task_v2(task_id, title)
```

**Migration:** Users get warning, update at convenience.

---

## Breaking Change Process

### Step 1: Identify Breaking Change

**Checklist:**
- [ ] Does it change API signature?
- [ ] Does it change schema (column/table)?
- [ ] Does it change config defaults?
- [ ] Does it change data format?
- [ ] Does old code fail with new code?

**If YES to any:** Breaking change.

---

### Step 2: Assess Impact

**Questions:**
- How many users affected? (Dominion: single-user system → low impact)
- How difficult to migrate? (1 hour vs 1 week)
- Can it be avoided? (add default, keep old API)

**Severity Matrix:**

| Change Type | Impact | Migration Time | Severity |
|-------------|--------|----------------|----------|
| API contract | High | 1 week | Critical |
| Schema | High | 1 day | High |
| Config | Medium | 1 hour | Medium |
| Data format | Medium | 1 day | Medium |
| Deprecation | Low | On schedule | Low |

---

### Step 3: Design Migration Path

**Good Migration Path:**
- Old code continues working (backward compatible)
- New code uses new API
- Clear migration steps documented
- Migration automated (script/tool)

**Bad Migration Path:**
- Old code breaks immediately
- Manual steps required
- No documentation
- Data loss risk

**Example (Good):**
```python
# Step 1: Deprecate old API (v2.0)
@deprecated("Use create_task_v2() instead. Removed in v3.0.")
def create_task_v1(task_id, title):
    return create_task_v2(task_id, title, evidence="{}")

# Step 2: Add new API (v2.0)
def create_task_v2(task_id, title, evidence="{}"):
    pass

# Step 3: Remove old API (v3.0, 6 months later)
# delete create_task_v1
```

---

### Step 4: Announce Breaking Change

**Where to Announce:**
1. Git commit message (BREAKING: prefix)
2. CHANGELOG.md (if exists)
3. This file (BREAKING_CHANGE_PROTOCOL.md)
4. ADR (if architectural decision)

**Commit Message Template:**
```
BREAKING: change description

- What changed
- Why it changed
- Migration path
- Deprecation timeline

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

**Example:**
```
BREAKING: replace AWS Bedrock with Ollama for embeddings

- DELETE ragd_embed/providers/bedrock.py
- ADD ragd_embed/providers/ollama.py
- UPDATE config: RAGD_EMBED_PROVIDER default "bedrock" → "ollama"

**Why:** Ollama runs locally (no AWS credentials), faster (73 emb/s), no cost.

**Migration:** Update ~/.bashrc:
  export RAGD_EMBED_PROVIDER=ollama
  export RAGD_EMBED_MODEL=nomic-embed-text
  unset AWS_PROFILE

**Deprecation:** Bedrock support removed immediately (no deprecation period, Phase 0-5 rapid iteration policy).

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

---

### Step 5: Implement Migration

**Migration Types:**

**Type 1: Automatic (Zero Effort)**
```python
# Code auto-migrates (backward compatible)
def create_task(task_id, title, evidence="{}"):  # Default value
    pass

# Old code works:
create_task("t1", "Test")  # Uses default evidence="{}"
```

**Type 2: Semi-Automatic (Migration Script)**
```bash
# scripts/migrate_to_ollama.sh
#!/bin/bash
# Migrate Bedrock → Ollama config

if grep -q "RAGD_EMBED_PROVIDER=bedrock" ~/.bashrc; then
  sed -i 's/RAGD_EMBED_PROVIDER=bedrock/RAGD_EMBED_PROVIDER=ollama/' ~/.bashrc
  echo "Migrated RAGD_EMBED_PROVIDER to ollama"
fi

# Remove AWS vars
sed -i '/AWS_PROFILE/d' ~/.bashrc
```

**Type 3: Manual (Migration Guide)**
```markdown
# Migration: Bedrock → Ollama

1. Install Ollama: `curl https://ollama.ai/install.sh | sh`
2. Pull model: `ollama pull nomic-embed-text`
3. Update config: `export RAGD_EMBED_PROVIDER=ollama`
4. Remove AWS config: `unset AWS_PROFILE`
5. Rebuild RAGD index: `ragd index rebuild`
```

---

### Step 6: Grace Period

**Pre-Production (Phase 0-5):** No grace period (rapid iteration).

**Production (Phase 6+):** Grace period ≥1 phase (1-3 months).

**Grace Period Schedule:**

| Severity | Grace Period | Example |
|----------|--------------|---------|
| Critical (API) | 2 phases | 6 months |
| High (Schema) | 1 phase | 3 months |
| Medium (Config) | 1 phase | 3 months |
| Low (Deprecation) | 2 phases | 6 months |

**During Grace Period:**
- Old API still works (emits deprecation warning)
- New API available
- Migration guide published
- Tests cover both old + new API

---

### Step 7: Remove Old Code

**After Grace Period:**
1. Remove deprecated API
2. Remove migration compatibility code
3. Remove tests for old API
4. Update documentation

**Example:**
```python
# v2.0 (deprecation)
@deprecated("Use create_task_v2() instead. Removed in v3.0.")
def create_task_v1(task_id, title):
    return create_task_v2(task_id, title, evidence="{}")

# v3.0 (removal, 6 months later)
# delete create_task_v1
```

---

## Breaking Change Examples

### Example 1: Bedrock → Ollama (2026-05-18)

**Severity:** Medium (Configuration Change)

**What Changed:**
- Deleted `ragd_embed/providers/bedrock.py`
- Added `ragd_embed/providers/ollama.py`
- Changed default `RAGD_EMBED_PROVIDER` from "bedrock" to "ollama"

**Why:**
- Ollama runs locally (no AWS credentials required)
- Faster batching (73 emb/s vs Bedrock ~30 emb/s)
- No API costs
- Model: nomic-embed-text (768-dim, 274MB)

**Impact:**
- Users with Bedrock config stop working (AWS credentials invalid)
- Users without config auto-switch to Ollama (may fail if Ollama not installed)

**Migration:**
```bash
# 1. Install Ollama
curl https://ollama.ai/install.sh | sh

# 2. Pull model
ollama pull nomic-embed-text

# 3. Update ~/.bashrc
export RAGD_EMBED_PROVIDER=ollama
export RAGD_EMBED_MODEL=nomic-embed-text
unset AWS_PROFILE

# 4. Rebuild RAGD index (embeddings regenerated)
cd ~/Dominion/ragd/build && ./ragd index rebuild
```

**Grace Period:** None (Phase 0-5 rapid iteration policy).

**Lessons Learned:**
- Breaking changes acceptable in pre-production
- Migration guide in commit message
- Automated testing verified new provider

---

### Example 2: agent_file_locks UNIQUE Constraint (2026-05-10)

**Severity:** High (Schema Change)

**What Changed:**
- Changed `agent_file_locks` UNIQUE constraint from `(filepath, status)` to `(filepath, session_id)`

**Why:**
- Old constraint blocked multiple read locks on same file
- New constraint allows concurrent reads, prevents double-lock by same session

**Impact:**
- Code assuming `UNIQUE(filepath, status)` may violate new constraint
- Old DB incompatible with new schema

**Migration:**
```sql
-- Automatic (Migration 2)
BEGIN;

CREATE TABLE agent_file_locks_v2(
    lock_id TEXT PRIMARY KEY,
    filepath TEXT NOT NULL,
    session_id TEXT NOT NULL,
    UNIQUE(filepath, session_id)  -- New constraint
);

INSERT OR IGNORE INTO agent_file_locks_v2 SELECT * FROM agent_file_locks;
DROP TABLE agent_file_locks;
ALTER TABLE agent_file_locks_v2 RENAME TO agent_file_locks;

COMMIT;
```

**Grace Period:** None (automatic migration on first run).

**Code Changes Required:** None (backward compatible).

---

### Example 3: Simple Average → Kalman Fusion (Q2 2025)

**Severity:** Medium (Algorithm Change)

**What Changed:**
- Replaced simple average fusion with Kalman filter bank
- Deleted `data_pipeline/fusion/simple_average.py`

**Why:**
- Kalman filter 62% error reduction (0.12% vs 0.32% RMSE)
- Dynamic trust scoring adapts to source reliability

**Impact:**
- Fusion output changes (better accuracy)
- Old scripts using `fuse_simple()` break

**Migration:**
```python
# Before
from data_pipeline.fusion.simple_average import fuse_simple
prices = fuse_simple(sources)

# After
from data_pipeline.fusion.kalman import KalmanFilterBank
bank = KalmanFilterBank(sources)
prices = bank.fuse()
```

**Grace Period:** 1 month (Q2 2025).

**Deprecation:**
```python
# simple_average.py (deprecated)
@deprecated("Use KalmanFilterBank instead. Removed in Phase 3.")
def fuse_simple(sources):
    warnings.warn("fuse_simple deprecated, use KalmanFilterBank")
    return np.mean(sources, axis=0)
```

---

## Avoiding Breaking Changes

### Strategy 1: Add Defaults

**Pattern:** New parameters get defaults.

**Example:**
```python
# Breaking
def create_task(task_id, title, evidence):  # New required param
    pass

# Fixed (backward compatible)
def create_task(task_id, title, evidence="{}"):  # Default value
    pass
```

---

### Strategy 2: Deprecate + Redirect

**Pattern:** Old function calls new function.

**Example:**
```python
# Old API (deprecated)
@deprecated("Use create_task_v2() instead")
def create_task(task_id, title):
    return create_task_v2(task_id, title, evidence="{}")

# New API
def create_task_v2(task_id, title, evidence="{}"):
    pass
```

---

### Strategy 3: Support Both Versions

**Pattern:** Detect version, handle both.

**Example:**
```python
def parse_task(data):
    # Support v1 (task_id) and v2 (id)
    task_id = data.get("id") or data.get("task_id")
    return Task(task_id=task_id, title=data["title"])
```

---

### Strategy 4: Add, Don't Remove

**Pattern:** Add new column/table, keep old one.

**Example:**
```sql
-- Don't rename column (breaking)
-- ALTER TABLE file_manifest RENAME COLUMN mtime_ns TO modified_at;

-- Instead: add new column, backfill, deprecate old
ALTER TABLE file_manifest ADD COLUMN modified_at INTEGER;
UPDATE file_manifest SET modified_at = mtime_ns;
-- Keep mtime_ns (deprecated but functional)
```

---

## Communication

### Pre-Breaking Change Checklist

**Before Merging:**
- [ ] Document breaking change (this file)
- [ ] Write migration guide
- [ ] Update ADR (if architectural)
- [ ] Add BREAKING: prefix to commit
- [ ] Update DEPRECATED_FEATURES.md (if deprecation)
- [ ] Test migration on backup DB

---

### Commit Message Format

```
BREAKING: <short description>

- <change 1>
- <change 2>
- <change 3>

**Why:** <reason for breaking change>

**Impact:** <who/what affected>

**Migration:** <step-by-step migration guide>

**Grace Period:** <deprecation timeline, or "None" if immediate>

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

---

### Post-Breaking Change

**After Merge:**
1. Monitor logs for migration errors
2. Verify schema version updated
3. Check health endpoints
4. Update documentation indexes

---

## Rolling Back Breaking Changes

### Rollback Strategy

**If Breaking Change Causes Production Issue:**

1. **Revert commit** (if within 24h)
```bash
git revert <commit-hash>
git push
```

2. **Restore DB backup** (if schema migration)
```bash
cp ~/Dominion/backups/agent_os_20260518.db ~/.dominion/agent_os.db
```

3. **Document rollback** (lessons learned)
```markdown
# Rollback: agent_file_locks Migration 2

**Date:** 2026-05-11  
**Reason:** Migration caused lock contention (unexpected behavior).  
**Action:** Reverted to schema v1, fixed migration bug, redeployed.  
**Lesson:** Test migrations on production-sized DB (not just empty DB).
```

---

## Related

- [SCHEMA_MIGRATION_GUIDE.md](SCHEMA_MIGRATION_GUIDE.md) — Schema migration patterns
- [DEPRECATED_FEATURES.md](../05_FEATURES/DEPRECATED_FEATURES.md) — Deprecated feature registry
- [AGENT_OS_ARCHITECTURE.md](../01_ARCHITECTURE/AGENT_OS_ARCHITECTURE.md) — Agent OS design

---

**Last Updated:** 2026-05-19  
**Verified By:** Claude Code (Sonnet 4.5)  
**Review Status:** ✓ Breaking change protocol validated against historical examples
