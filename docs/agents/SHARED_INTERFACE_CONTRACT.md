# Shared Interface Contract

## Agent 1 Scope (Foundation Interfaces)

Version: `agent-1.20260513`

### LoadedFile (v1.0.0)

`dominion_loader.scan.LoadedFile` — stable frozen dataclass consumed by Agent 2:

```
path: str              # absolute path (str, not Path)
relative_path: str     # relative to repo_root, no leading /
repo_root: str
size: int
mtime_ns: int
file_class: str        # "code"|"doc"|"config"|"data"|"binary"|"unknown"
language: str          # "python"|"cpp"|"markdown"|... (or "unknown")
content_hash: str      # real sha256 hex
document_id: str       # sha256(repo_root + "::" + relative_path)[:16]
trace_id: str
is_new: bool
is_changed: bool
```

### IngestResult (v1.0.0)

`dominion_loader.ragd_bridge.IngestResult`:
```
paths_submitted: int
chunks_indexed: int
already_current: int
duration_ms: float
error: Optional[str]
ok: bool           # derived: error is None
elapsed_s: float   # derived: duration_ms / 1000
```

### Public API (`dominion_loader.api`)

```python
iter_files(repo_root=None, *, force_full=False, trace_id=None) -> Iterator[LoadedFile]
get_manifest_entry(document_id) -> Optional[ManifestEntry]
list_changed_since(epoch: int) -> Iterator[ManifestEntry]
semantic_diff(old: bytes, new: bytes) -> str
hw_probe() -> HardwareProfile
cache_get(ns, key, *, fingerprint) -> Optional[CacheHit]
cache_put(ns, key, value, *, fingerprint) -> None
```

### Agent 2 Reserved Cache Namespaces

- `retrieval:` — retrieval result cache
- `context:` — assembled context cache
- `generation:` — generation output cache

---

## Agent 2 Additions

Version: `agent-2.20260513`

### Python API

`dominion_ai.api` exposes:

- `plan(query, hints=None) -> RetrievalPlan`
- `retrieve(plan) -> list[ScoredChunk]`
- `rerank(plan, chunks) -> list[ScoredChunk]`
- `assemble(plan, chunks, budget) -> AssembledContext`
- `score_confidence(plan, chunks) -> Confidence`
- `ask(query, generate=False, budget=None) -> AskResult`

`ScoredChunk` preserves `chunk_id`, `document_id`, `filepath`, `line_start`, `line_end`, `content`, `score`, `bm25_score`, `vector_score`, `rerank_score`, `rrf_score`, `confidence`, `content_hash`, and `citations`.

### Temporary Adapters

- `TEMP_ADAPTER(agent-1)` in `dominion_ai/ragd_client.py`: RAGD `/query` now returns `content_hash`, `repo_root`, `status`, `indexed_at`, and `modified_at`; only `document_id` remains a labeled compatibility fallback. Remove when RAGD REST returns loader-compatible `document_id`.
- `local_llm/governor.py` consumes `dominion_loader.api.hw_probe` when available. A labeled `TEMP_ADAPTER(agent-1)` fallback remains only for environments where that interface is absent.

### CLI

Agent 2 adds only additive commands:

- `dominion ask`
- `dominion search`
- `dominion explain`
- `dominion trace`
- `dominion eval`
- `dominion ledger list|show|search`
- `dominion graph query|neighbors|subgraph`
- `dominion bench`

Existing commands are preserved.

---

## Agent 3 Additions

Version: `agent-3.20260513`

### RAGD Delete Endpoint

`POST /index/delete`:

```json
{"paths":["/absolute/path.py"]}
```

Response:

```json
{
  "ok": true,
  "paths_submitted": 1,
  "files_marked_deleted": 1,
  "chunks_marked_deleted": 3,
  "errors": []
}
```

Semantics:

- Soft delete only: sets active chunk rows to `status='deleted'`.
- Query paths continue to filter `status='active'`.
- Missing paths are non-fatal and return zero deleted chunks.

### DeleteResult

`dominion_loader.ragd_bridge.DeleteResult`:

```python
paths_submitted: int
files_marked_deleted: int
chunks_marked_deleted: int
duration_ms: float
errors: list[dict[str, str]]
skipped: bool
reason: str | None
ok: bool
```

### Query Metadata

RAGD `/query` result fields added:

- `content_hash`
- `repo_root`
- `status`
- `indexed_at`
- `modified_at`

### Deep Doctor

`dominion doctor --deep [--json] [--offline] [--max-sample N]` returns:

```json
{
  "overall": "ok|warn|fail",
  "mode": "deep",
  "timestamp": "...",
  "root": "...",
  "checks": {
    "check_name": {
      "status": "pass|warn|fail|skip",
      "severity": "info|low|medium|high|critical",
      "detail": "...",
      "remedy": null,
      "evidence": {}
    }
  }
}
```

### Ignore Policy

- `dominion_loader.ignore.export_policy() -> dict`
- `dominion_loader.ignore.policy_hash() -> str`
- `dominion ignore policy --json`
- Generated snapshot: `config/dominion_ignore_policy.json`
