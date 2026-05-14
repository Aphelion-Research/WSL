---
title: iter_loaded_files
qualified_name: dominion_loader.scan.iter_loaded_files
symbol_type: function
filepath: /home/Martin/Dominion/dominion_loader/scan.py
line_start: 315
line_end: 369
parent_symbol: ''
is_public: true
tags:
- function
- python
- symbol
---

# `iter_loaded_files`

> **File**: [[files/dominion_loader/scan|scan.py]] | **Lines**: 315-369 | **Type**: `function`

## Docstring

Yield LoadedFile for every indexable file under repo_root.

Does NOT write to manifest or RAGD. Pure read path for Agent 2 consumption.

## Calls

- `Ignore`
- `LoadedFile`
- `Manifest`
- `Path`
- `PriorEntry`
- `classify`
- `discover`
- `document_id_for`
- `get`
- `hash_file`
- `is_likely_binary`
- `isinstance`
- `new_trace_id`
- `resolve`
- `str`

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
