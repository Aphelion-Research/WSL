# Python API Reference

**Status:** LIVE_GREEN (Production Python APIs)  
**Last Updated:** 2026-05-19  
**Owner:** MatinDeevv  
**Packages:** `dominion_loader`, `dominion_agent`

---

## Overview

Dominion provides two main Python APIs:

1. **dominion_loader** — File ingestion, manifest tracking, semantic diff, hardware probing
2. **dominion_agent** — Agent OS (sessions, tasks, claims, locks, adversarial review)

Both follow **stable interface contracts** — breaking changes require version bumps + `INTERFACE(agent-N)` annotations.

---

## dominion_loader

**Purpose:** Read-only file ingestion for RAGD indexing.

**Installation:**
```bash
pip install -e ~/Dominion/dominion_loader
```

**Import:**
```python
import dominion_loader as dl
```

---

### Types

#### `LoadedFile`

```python
@dataclass
class LoadedFile:
    document_id: str  # SHA-256 hash
    file_path: str  # Absolute path
    content_bytes: bytes
    content_hash: str  # SHA-256 of content
    file_type: str  # "python" | "markdown" | "json" | "txt"
    classification: str  # "code" | "test" | "doc" | "config"
    symbols: List[str]  # Extracted function/class names (Python only)
    metadata: Dict[str, Any]  # Frontmatter (Markdown), package.json (JS)
```

---

#### `ManifestEntry`

```python
@dataclass
class ManifestEntry:
    document_id: str
    file_path: str
    content_hash: str
    indexed_at: int  # Unix timestamp
    file_type: str
    classification: str
    symbols_json: str  # JSON array
    metadata_json: str  # JSON object
```

---

#### `HardwareProfile`

```python
@dataclass
class HardwareProfile:
    cpu_count: int
    cpu_model: str
    total_memory_gb: float
    disk_type: str  # "ssd" | "hdd" | "unknown"
    has_cuda: bool
    platform: str  # "linux" | "darwin" | "windows"
```

---

#### `CacheHit`

```python
@dataclass
class CacheHit:
    value: bytes
    fingerprint: str
    cached_at: int  # Unix timestamp
```

---

#### `DiffClass`

```python
DiffClass = Literal["format-only", "comment-only", "whitespace-only", "functional"]
```

---

### Functions

#### `iter_files(repo_root: str, *, force_full: bool = False) -> Iterator[LoadedFile]`

Iterate all indexable files under `repo_root`.

**Args:**
- `repo_root` — Repository root path
- `force_full` — Force full scan (ignore manifest cache)

**Returns:** Iterator of `LoadedFile` in deterministic sorted order

**Behavior:**
- Respects `.domignore` rules
- Skips `__pycache__`, `.venv`, `node_modules`, `.git`
- Reads file content + extracts metadata
- **Does NOT write** to manifest or RAGD (read-only)

**Example:**
```python
for lf in dl.iter_files("/home/Martin/Dominion"):
    print(f"{lf.file_path}: {lf.file_type}, {len(lf.symbols)} symbols")
```

**Interface:** `INTERFACE(agent-1)` — stable, do not change signature without agent-2 sign-off

---

#### `get_manifest_entry(document_id: str) -> Optional[ManifestEntry]`

Retrieve manifest entry by document ID.

**Args:**
- `document_id` — SHA-256 hash (e.g., `"8d000eecff81cfa4"`)

**Returns:** `ManifestEntry` or `None` if not found

**Example:**
```python
entry = dl.get_manifest_entry("8d000eecff81cfa4")
if entry:
    print(f"File: {entry.file_path}, indexed at {entry.indexed_at}")
```

---

#### `list_changed_since(epoch: int) -> Iterator[ManifestEntry]`

Yield manifest entries where `indexed_at > epoch`.

**Args:**
- `epoch` — Unix timestamp (seconds)

**Returns:** Iterator of `ManifestEntry`

**Example:**
```python
import time
yesterday = int(time.time()) - 86400
for entry in dl.list_changed_since(yesterday):
    print(f"Changed: {entry.file_path}")
```

---

#### `semantic_diff(old: bytes, new: bytes) -> DiffClass`

Classify semantic difference between two file versions.

**Args:**
- `old` — Old file content (bytes)
- `new` — New file content (bytes)

**Returns:** `DiffClass` — one of:
- `"format-only"` — Only formatting changed (whitespace, indentation)
- `"comment-only"` — Only comments changed
- `"whitespace-only"` — Only whitespace changed
- `"functional"` — Code logic changed (or uncertain)

**Bias:** Conservative — returns `"functional"` when uncertain

**Example:**
```python
old = b"def foo():\n    return 42"
new = b"def foo():\n    return 42  # Added comment"
diff = dl.semantic_diff(old, new)
assert diff == "comment-only"
```

**Interface:** `INTERFACE(agent-1)` — stable

---

#### `hw_probe() -> HardwareProfile`

Return hardware profile for this machine.

**Returns:** `HardwareProfile`

**Example:**
```python
hw = dl.hw_probe()
print(f"CPU: {hw.cpu_model}, {hw.cpu_count} cores")
print(f"Memory: {hw.total_memory_gb:.1f} GB")
print(f"CUDA: {hw.has_cuda}")
```

**Interface:** `INTERFACE(agent-1)` — Agent 2 reads this to choose model strategy

---

#### `cache_get(namespace: str, key: str, *, fingerprint: str) -> Optional[CacheHit]`

Read from dominion cache.

**Args:**
- `namespace` — Cache namespace (e.g., `"retrieval"`, `"context"`)
- `key` — Cache key
- `fingerprint` — Expected fingerprint (SHA-256)

**Returns:** `CacheHit` or `None` if miss

**Raises:** `CacheCorruption` if fingerprint mismatch

**Example:**
```python
hit = dl.cache_get("retrieval", "query:kalman", fingerprint="abc123")
if hit:
    print(f"Cache hit: {len(hit.value)} bytes")
```

**Interface:** `INTERFACE(agent-1)` — Agent 2 may use `"retrieval:"` and `"context:"` namespaces

---

#### `cache_put(namespace: str, key: str, value: bytes, *, fingerprint: str) -> None`

Write to dominion cache.

**Args:**
- `namespace` — Cache namespace
- `key` — Cache key
- `value` — Value to cache (bytes)
- `fingerprint` — Fingerprint (SHA-256)

**Example:**
```python
dl.cache_put("retrieval", "query:kalman", b"result data", fingerprint="abc123")
```

---

## dominion_agent

**Purpose:** Agent OS for session tracking, task management, safety enforcement.

**Installation:**
```bash
pip install -e ~/Dominion/dominion_agent
```

**Import:**
```python
import dominion_agent as da
```

---

### Types

#### `Session`

```python
@dataclass
class Session:
    session_id: str  # "sess_<uuid>"
    agent_name: str
    role: str  # "research" | "implementation" | "review" | "maintenance"
    status: str  # "active" | "idle" | "completed" | "failed" | "abandoned"
    started_at: int  # Unix timestamp
    ended_at: int  # Unix timestamp or 0
    last_heartbeat: int  # Unix timestamp
    git_branch: str
    git_commit_start: str
    git_commit_end: str
    parent_session_id: str
    metadata: Dict[str, Any]
```

**Methods:**
```python
def is_stale(self, threshold_seconds: int = 1800) -> bool:
    """Return True if last_heartbeat > threshold_seconds ago."""
```

---

#### `Task`

```python
@dataclass
class Task:
    task_id: str  # "task_<uuid>"
    title: str
    description: str
    kind: str  # "feature" | "bugfix" | "refactor" | "research" | "maintenance"
    priority: int  # 1 (highest) to 10 (lowest)
    status: str  # "open" | "in_progress" | "blocked" | "done" | "abandoned"
    created_at: int
    updated_at: int
    claimed_by_session: str
    parent_task_id: str
    scope: Dict[str, Any]  # {"files": [...], "modules": [...]}
    validation: Dict[str, Any]  # {"commands": ["pytest", "dominion doctor"]}
    acceptance: Dict[str, Any]  # {"criteria": [...]}
    risk: Dict[str, Any]  # {"level": "low", "mitigations": [...]}
    tags: List[str]  # ["ml", "data-pipeline"]
    evidence: Dict[str, Any]  # {"commands": [...], "report": "..."}
```

---

#### `ClaimResult`

```python
@dataclass
class ClaimResult:
    claim_id: str  # "claim_<uuid>"
    task_id: str
    session_id: str
    claimed_at: int
    expires_at: int
```

---

#### `FileLock`

```python
@dataclass
class FileLock:
    lock_id: str  # "lock_<uuid>"
    session_id: str
    filepath: str
    mode: str  # "read" | "write"
    acquired_at: int
    released_at: int
    last_heartbeat: int
    status: str  # "active" | "released" | "expired"
```

---

#### `ReviewReport`

```python
@dataclass
class ReviewReport:
    review_id: str  # "rev_<uuid>"
    task_id: str
    verdict: str  # "approved" | "conditional" | "blocked"
    score: float  # 0-100, higher = more issues
    findings: List[ReviewFinding]
    commands: List[str]  # Commands to re-run
    summary: str
```

---

#### `ReviewFinding`

```python
@dataclass
class ReviewFinding:
    severity: str  # "critical" | "moderate" | "minor" | "info"
    type: str  # "claim_missing" | "forbidden_token" | "secret_scope" | etc.
    message: str
    remedy: str
```

---

#### `SafetyResult`

```python
@dataclass
class SafetyResult:
    ok: bool
    violations: List[str]
    redacted_payload: Dict[str, Any]
```

---

#### `ComplexityReport`

```python
@dataclass
class ComplexityReport:
    package: str
    score: float
    budget: float
    over_budget: bool
    metrics: ComplexityMetrics
    warnings: List[str]
    remediation: List[str]
```

---

#### `ComplexityMetrics`

```python
@dataclass
class ComplexityMetrics:
    file_count: int
    public_symbol_count: int
    cli_command_count: int
    test_count: int
    todo_count: int
    temp_adapter_count: int
    broad_except_count: int
    untested_module_count: int
    large_file_penalty: float
    average_file_lines: float
    largest_file_lines: int
    test_to_source_ratio: float
```

---

### Session Functions

#### `start_session(agent_name: str, role: str, metadata: Optional[dict] = None, *, store: Optional[AgentStore] = None, parent_session_id: str = "") -> Session`

Create new active agent session.

**Args:**
- `agent_name` — Agent identifier (e.g., `"claude-sonnet-4"`)
- `role` — `"research"` | `"implementation"` | `"review"` | `"maintenance"`
- `metadata` — Arbitrary JSON metadata
- `store` — AgentStore instance (creates new if None)
- `parent_session_id` — Parent session (for nested agents)

**Returns:** `Session`

**Example:**
```python
session = da.start_session("claude-sonnet-4", "implementation")
print(f"Started: {session.session_id}")
```

---

#### `heartbeat(session_id: str, *, store: Optional[AgentStore] = None) -> None`

Update `last_heartbeat` for session (prevents stale detection).

**Args:**
- `session_id` — Session ID
- `store` — AgentStore instance

**Raises:** `ValueError` if session not found

**Example:**
```python
da.heartbeat(session.session_id)
```

---

#### `end_session(session_id: str, status: str, summary: str = "", *, store: Optional[AgentStore] = None) -> Session`

End session with terminal status.

**Args:**
- `session_id` — Session ID
- `status` — `"completed"` | `"failed"` | `"abandoned"`
- `summary` — Summary text
- `store` — AgentStore instance

**Returns:** Updated `Session`

**Raises:** `ValueError` if session not found or not endable

**Example:**
```python
da.end_session(session.session_id, "completed", summary="Fixed bug X")
```

---

#### `get_session(session_id: str, *, store: Optional[AgentStore] = None) -> Optional[Session]`

Fetch session by ID.

---

#### `list_sessions(active_only: bool = False, stale_only: bool = False, stale_minutes: int = 30, *, store: Optional[AgentStore] = None) -> List[Session]`

List sessions with filters.

---

#### `abandon_session(session_id: str, reason: str = "", *, store: Optional[AgentStore] = None) -> Session`

Force-abandon session (for stale/orphaned sessions).

---

### Task Functions

#### `create_task(title: str, description: str = "", kind: str = "feature", priority: int = 5, scope: Optional[dict] = None, validation: Optional[dict] = None, acceptance: Optional[dict] = None, risk: Optional[dict] = None, tags: Optional[list] = None, *, store: Optional[AgentStore] = None) -> Task`

Create new task (runs safety validation first).

**Args:**
- `title` — Task title (required, non-empty)
- `description` — Task description
- `kind` — `"feature"` | `"bugfix"` | `"refactor"` | `"research"` | `"maintenance"`
- `priority` — 1 (highest) to 10 (lowest)
- `scope` — `{"files": [...], "modules": [...]}`
- `validation` — `{"commands": ["pytest", "dominion doctor"]}`
- `acceptance` — `{"criteria": [...]}`
- `risk` — `{"level": "low", "mitigations": [...]}`
- `tags` — `["ml", "data-pipeline"]`
- `store` — AgentStore instance

**Returns:** `Task`

**Raises:** `ValueError` if safety check fails (forbidden trading, secret paths, dangerous commands, empty title)

**Example:**
```python
task = da.create_task(
    title="Add momentum feature",
    kind="feature",
    scope={"files": ["domdata/features.py"], "modules": ["features"]},
    validation={"commands": ["pytest tests/test_features.py", "dominion doctor"]},
)
```

---

#### `update_task_status(task_id: str, new_status: str, evidence: Optional[dict] = None, *, store: Optional[AgentStore] = None, force: bool = False) -> Task`

Update task status (enforces transition rules).

**Args:**
- `task_id` — Task ID
- `new_status` — `"open"` | `"in_progress"` | `"blocked"` | `"done"` | `"abandoned"`
- `evidence` — Evidence dict (required for `"done"`)
- `store` — AgentStore instance
- `force` — Override transition rules (for reopening terminal states)

**Returns:** Updated `Task`

**Raises:** `ValueError` if invalid transition or missing evidence for `"done"`

**Example:**
```python
da.update_task_status(task.task_id, "in_progress")
# ... work ...
da.update_task_status(task.task_id, "done", evidence={
    "commands": [{"command": "pytest", "output": "42 passed"}],
    "report": "reports/momentum_feature.md",
})
```

---

#### `update_task_evidence(task_id: str, evidence: dict, *, store: Optional[AgentStore] = None) -> Task`

Attach evidence without changing status.

---

#### `get_task(task_id: str, *, store: Optional[AgentStore] = None) -> Optional[Task]`

Fetch task by ID.

---

#### `list_tasks(status: Optional[str] = None, limit: int = 50, *, store: Optional[AgentStore] = None) -> List[Task]`

List tasks filtered by status.

---

#### `record_touch(session_id: str, task_id: str, filepath: str, action: str, *, store: Optional[AgentStore] = None, git_commit: str = "", note: str = "") -> None`

Record file touch event.

**Args:**
- `session_id` — Session ID
- `task_id` — Task ID
- `filepath` — File path
- `action` — `"analyze"` | `"edit"` | `"create"` | `"delete"`
- `store` — AgentStore instance
- `git_commit` — Git commit SHA
- `note` — Note

**Example:**
```python
da.record_touch(session.session_id, task.task_id, "data_pipeline/pipeline.py", "edit", note="Added error handling")
```

---

### Claim Functions

#### `claim_task(session_id: str, task_id: str, timeout_seconds: int = 3600, *, store: Optional[AgentStore] = None) -> ClaimResult`

Acquire exclusive claim on task.

**Args:**
- `session_id` — Session ID
- `task_id` — Task ID
- `timeout_seconds` — Claim timeout (default: 1 hour)
- `store` — AgentStore instance

**Returns:** `ClaimResult`

**Raises:** `ValueError` if task not claimable or already claimed

**Example:**
```python
claim = da.claim_task(session.session_id, task.task_id, timeout_seconds=3600)
# ... work on task ...
da.release_task(claim.claim_id)
```

---

#### `release_task(claim_id: str, *, store: Optional[AgentStore] = None) -> None`

Release task claim.

---

#### `list_claims(active_only: bool = True, *, store: Optional[AgentStore] = None) -> List[ClaimResult]`

List claims.

---

### Lock Functions

#### `acquire_lock(session_id: str, filepath: str, mode: str, timeout_seconds: int = 3600, *, store: Optional[AgentStore] = None) -> FileLock`

Acquire file lock.

**Args:**
- `session_id` — Session ID
- `filepath` — File path
- `mode` — `"read"` | `"write"`
- `timeout_seconds` — Lock timeout
- `store` — AgentStore instance

**Returns:** `FileLock`

**Raises:** `ValueError` if lock conflict (write lock when read lock exists, or vice versa)

**Example:**
```python
lock = da.acquire_lock(session.session_id, "data_pipeline/pipeline.py", "write")
# ... edit file ...
da.release_lock(lock.lock_id)
```

---

#### `release_lock(lock_id: str, *, store: Optional[AgentStore] = None) -> None`

Release file lock.

---

#### `list_locks(active_only: bool = True, *, store: Optional[AgentStore] = None) -> List[FileLock]`

List locks.

---

#### `stale_locks(age_minutes: int = 30, *, store: Optional[AgentStore] = None) -> List[FileLock]`

List stale locks (no heartbeat for `age_minutes`).

---

#### `reap_expired_locks(*, store: Optional[AgentStore] = None) -> int`

Auto-release expired locks.

**Returns:** Count of reaped locks

---

### Adversarial Review

#### `run_adversarial_review(task_id: str, *, store: Optional[AgentStore] = None, strict: bool = False) -> ReviewReport`

Run structured checks on task before marking done.

**Args:**
- `task_id` — Task ID
- `store` — AgentStore instance
- `strict` — Strict mode (fails on large refactors outside scope)

**Returns:** `ReviewReport`

**Checks:**
1. Claim check (task had active claim)
2. Scope check (task had scope files)
3. Evidence check (evidence provided)
4. Validation commands check (commands specified)
5. Forbidden tokens scan (no `order_send`, `Position_Open` in changed files)
6. Secret paths check (no `secrets/`, `mt5.env` in scope)
7. Report exists check (report file referenced in evidence exists)
8. Doctor evidence check (`dominion doctor` in validation commands)
9. Pytest evidence check (pytest output in evidence if code changed)

**Verdict:**
- `"approved"` — all checks passed or minor warnings only
- `"conditional"` — some moderate issues, needs fix
- `"blocked"` — critical issues, must fix before merge

**Example:**
```python
review = da.run_adversarial_review(task.task_id, strict=True)
if review.verdict == "blocked":
    print(f"Task blocked: {review.summary}")
    for finding in review.findings:
        if finding.severity == "critical":
            print(f"  {finding.message}")
```

---

### Complexity Budget

#### `complexity_report(package: str, root: Optional[str] = None) -> ComplexityReport`

Compute complexity report for package.

**Args:**
- `package` — Package directory name (e.g., `"dominion_loader"`)
- `root` — Workspace root (default: cwd)

**Returns:** `ComplexityReport`

**Example:**
```python
report = da.complexity_report("dominion_ai")
if report.over_budget:
    print(f"Over budget: {report.score} > {report.budget}")
    for warning in report.warnings:
        print(f"  {warning}")
```

---

#### `all_packages_report(root: Optional[str] = None) -> List[ComplexityReport]`

Run complexity report for all budgeted packages.

**Example:**
```python
reports = da.all_packages_report()
for r in reports:
    if r.over_budget:
        print(f"{r.package}: {r.score} > {r.budget}")
```

---

### Other Functions

#### `sync_ragd(store: Optional[AgentStore] = None) -> dict`

Attempt RAGD health check and record event.

**Returns:** `{"ok": bool, "chunk_count": int, "status": str}`

**Example:**
```python
result = da.sync_ragd()
if not result["ok"]:
    print(f"RAGD unhealthy: {result['status']}")
```

---

#### `check_conflicts(*, store: Optional[AgentStore] = None) -> ConflictReport`

Detect conflicts (multiple agents editing same file).

---

#### `analyze_impact(task_id: str, *, store: Optional[AgentStore] = None) -> ImpactReport`

Analyze task impact (files touched, modules affected).

---

#### `compile_prompt(task_id: str, *, store: Optional[AgentStore] = None) -> PromptCompilation`

Compile prompt for task (gathers context from RAGD + manifest).

---

#### `refresh_architecture(*, store: Optional[AgentStore] = None) -> None`

Refresh architecture diagrams (regenerate from code).

---

#### `show_architecture(*, store: Optional[AgentStore] = None) -> str`

Show architecture as ASCII diagram.

---

### Constants

#### `COMPLEXITY_BUDGETS`

```python
COMPLEXITY_BUDGETS: Dict[str, float] = {
    "dominion_loader": 50.0,
    "dominion_ai": 130.0,
    "dominion_agent": 350.0,
    "domdata": 155.0,
    "research_os": 175.0,
    "scripts": 200.0,
    "tests": 20.0,
}
```

---

#### `TASK_TRANSITIONS`

```python
TASK_TRANSITIONS: Dict[str, Set[str]] = {
    "open": {"in_progress", "blocked", "abandoned"},
    "in_progress": {"done", "blocked", "abandoned"},
    "blocked": {"open", "abandoned"},
    "done": set(),  # terminal
    "abandoned": set(),  # terminal
}
```

---

#### `VALID_ROLES`

```python
VALID_ROLES: Set[str] = {"research", "implementation", "review", "maintenance"}
```

---

#### `VALID_SESSION_STATUSES`

```python
VALID_SESSION_STATUSES: Set[str] = {"active", "idle", "completed", "failed", "abandoned"}
```

---

#### `VALID_TASK_STATUSES`

```python
VALID_TASK_STATUSES: Set[str] = {"open", "in_progress", "blocked", "done", "abandoned"}
```

---

#### `VALID_TASK_KINDS`

```python
VALID_TASK_KINDS: Set[str] = {"feature", "bugfix", "refactor", "research", "maintenance"}
```

---

#### `VALID_LOCK_MODES`

```python
VALID_LOCK_MODES: Set[str] = {"read", "write"}
```

---

#### `VALID_REVIEW_VERDICTS`

```python
VALID_REVIEW_VERDICTS: Set[str] = {"approved", "conditional", "blocked"}
```

---

## Usage Examples

### Full Agent Workflow

```python
import dominion_agent as da

# Start session
session = da.start_session("claude-sonnet-4", "implementation")

# Create task
task = da.create_task(
    title="Add retry logic to data pipeline",
    kind="feature",
    scope={"files": ["data_pipeline/pipeline.py"], "modules": ["data_pipeline"]},
    validation={"commands": ["pytest tests/test_pipeline.py", "dominion doctor"]},
)

# Claim task
claim = da.claim_task(session.session_id, task.task_id)

# Update status
da.update_task_status(task.task_id, "in_progress")

# ... do work ...

# Record file touches
da.record_touch(session.session_id, task.task_id, "data_pipeline/pipeline.py", "edit")

# Update status with evidence
da.update_task_status(task.task_id, "done", evidence={
    "commands": [
        {"command": "pytest tests/test_pipeline.py", "output": "42 passed"},
        {"command": "dominion doctor", "output": "overall=warn"}
    ],
    "report": "reports/retry_logic_feature.md",
})

# Release claim
da.release_task(claim.claim_id)

# Adversarial review
review = da.run_adversarial_review(task.task_id)
if review.verdict == "approved":
    print("Task approved!")
else:
    print(f"Task {review.verdict}: {review.summary}")

# End session
da.end_session(session.session_id, "completed", summary="Added retry logic")
```

---

### File Ingestion

```python
import dominion_loader as dl

# Iterate files
for lf in dl.iter_files("/home/Martin/Dominion"):
    if lf.file_type == "python" and lf.classification == "code":
        print(f"{lf.file_path}: {len(lf.symbols)} symbols")

# Semantic diff
old = b"def foo():\n    return 42"
new = b"def foo():\n    return 42  # comment"
diff = dl.semantic_diff(old, new)
assert diff == "comment-only"

# Hardware probe
hw = dl.hw_probe()
print(f"CPU: {hw.cpu_model}, CUDA: {hw.has_cuda}")
```

---

### Complexity Check

```python
import dominion_agent as da

# Check all packages
reports = da.all_packages_report()
for r in reports:
    if r.over_budget:
        print(f"{r.package}: {r.score:.1f} > {r.budget:.1f}")
        for warning in r.warnings:
            print(f"  {warning}")
        for remedy in r.remediation:
            print(f"  Action: {remedy}")
```

---

## Error Handling

**ValueError:** Invalid arguments (empty title, invalid status transition, forbidden trading content, secret paths)

**CacheCorruption:** Cache fingerprint mismatch (dominion_loader)

**Example:**
```python
try:
    task = da.create_task("enable live trading")
except ValueError as e:
    print(f"Safety violation: {e}")
```

---

## Performance

| Function | Typical Latency | Notes |
|----------|----------------|-------|
| `start_session` | <5ms | SQLite INSERT |
| `create_task` | <10ms | Safety check + INSERT |
| `claim_task` | <10ms | Check + INSERT |
| `update_task_status` | <5ms | UPDATE |
| `run_adversarial_review` | 50-200ms | File scans + DB reads |
| `complexity_report` | 100-500ms | AST parsing |
| `iter_files` | 1-5s | Directory traversal |
| `semantic_diff` | <1ms | AST comparison (Python only) |

---

## Related

- [RAGD_REST_API.md](RAGD_REST_API.md) — RAGD HTTP endpoints
- [AGENT_OS_ARCHITECTURE.md](../01_ARCHITECTURE/AGENT_OS_ARCHITECTURE.md) — Agent OS internals
- [CLI_REFERENCE.md](CLI_REFERENCE.md) — CLI commands wrapping these APIs

---

**Last Updated:** 2026-05-19  
**Verified By:** Claude Code (Sonnet 4.5)  
**Review Status:** ✓ All functions tested + examples validated
