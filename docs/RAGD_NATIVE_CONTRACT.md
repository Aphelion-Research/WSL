# RAGD Native Metadata Contract

RAGD query JSON preserves existing fields and adds native identity metadata.

Each normal query result includes:

- `chunk_id`: existing numeric RAGD chunk row ID.
- `stable_chunk_id`: SHA-256-derived stable chunk identity.
- `document_id`: SHA-256-derived stable document identity from `repo_root` and `relative_path`.
- `content_hash`: content identity for the indexed chunk.
- `repo_root`: repository root known at ingestion time.
- `filepath`: stored path.
- `relative_path`: repo-relative path when derivable.
- `lang` and `language`: language classification.
- `status`: normal queries only return `active` chunks.
- `indexed_at`: indexed epoch seconds when known.
- `modified_at`: source modified time when known.
- `source_subsystem`: currently `ragd`.
- `score_breakdown`: `total`, `bm25`, `vector`, and `rrf` score components.

Deletion contract:

- Storage search paths filter `status='active'`.
- `Storage::mark_file_deleted()` marks chunks deleted.
- Native manifest scans mark absent active files as `deleted` only after a completed transaction.
- Live RAGD deletion propagation remains storage/indexer-level; no new retrieval stack was introduced in Phase 5.

