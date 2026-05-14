---
title: scan
qualified_name: dominion_loader.scan.scan
symbol_type: function
filepath: /home/Martin/Dominion/dominion_loader/scan.py
line_start: 70
line_end: 312
parent_symbol: ''
is_public: true
tags:
- function
- python
- symbol
---

# `scan`

> **File**: [[files/dominion_loader/scan|scan.py]] | **Lines**: 70-312 | **Type**: `function`

## Docstring

Run a full scan of repo_root.

Args:
    dry_run: discover and hash but do NOT write to manifest or RAGD.
    force_full: force sha256 of every file (ignore mtime fast-path).
    once: run once and return (vs. watch mode — not implemented here).
    trace_id: explicit trace ID (auto-generated if None).
    manifest: inject a Manifest (for testing).
    bridge: inject a RagdBridge (for testing).
    ignore: inject an Ignore (for testing).

## Calls

- `Ignore`
- `LoadedFile`
- `Manifest`
- `ManifestEntry`
- `Path`
- `PriorEntry`
- `RagdBridge`
- `ScanStats`
- `add`
- `append`
- `as_posix`
- `classify`
- `close`
- `delete_paths`
- `discover`
- `document_id_for`
- `event`
- `finish_scan_run`
- `get`
- `hash_file`
- `ingest_paths`
- `int`
- `is_likely_binary`
- `isinstance`
- `len`
- `list_all_document_ids`
- `make_tracer`
- `mark_deleted`
- `mark_ragd_ingested`
- `monotonic`
- `new_trace_id`
- `relative_to`
- `resolve`
- `set`
- `span`
- `start_scan_run`
- `str`
- `time`
- `type`
- `upsert`

## Imports In File

- `__future__`
- `dataclasses`
- `dominion_loader.classify`
- `dominion_loader.discover`
- `dominion_loader.hashing`
- `dominion_loader.ignore`
- `dominion_loader.manifest`
- `dominion_loader.obs`
- `dominion_loader.ragd_bridge`
- `os`
- `pathlib`
- `time`
- `typing`
