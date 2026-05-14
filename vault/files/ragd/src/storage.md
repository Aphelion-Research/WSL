---
title: storage.cpp
filepath: /home/Martin/Dominion/ragd/src/storage.cpp
language: cpp
lines: 832
symbols: 60
public_symbols: 60
content_hash: e171ba69ef3e247
tags:
- cpp
- file
---

# storage.cpp

> **Language**: `cpp` | **Symbols**: 60

## Purpose

Defines 60 indexed symbol(s): top_level, throw_sqlite, text_or_empty, now_epoch, now_millis.

## Public Symbols

| Symbol | Type | Lines | Description |
|---|---|---:|---|
| [[symbols/ragd/src/top_level-L1-a9a82e31|top_level]] | block | 1-14 | top_level |
| [[symbols/ragd/src/throw_sqlite-L15-11980f3e|throw_sqlite]] | function | 15-18 | throw_sqlite |
| [[symbols/ragd/src/text_or_empty-L19-92df80f1|text_or_empty]] | function | 19-22 | text_or_empty |
| [[symbols/ragd/src/now_epoch-L23-ee143347|now_epoch]] | function | 23-26 | now_epoch |
| [[symbols/ragd/src/now_millis-L27-349e2b6f|now_millis]] | function | 27-30 | now_millis |
| [[symbols/ragd/src/table_has_column-L31-920d740b|table_has_column]] | function | 31-38 | table_has_column |
| [[symbols/ragd/src/add_column_if_missing-L39-e630fa64|add_column_if_missing]] | function | 39-42 | add_column_if_missing |
| [[symbols/ragd/src/sanitize_fts_query-L43-11c8d4e9|sanitize_fts_query]] | function | 43-62 | sanitize_fts_query |
| [[symbols/ragd/src/json_array_or_empty-L63-2d94f9b0|json_array_or_empty]] | function | 63-67 | json_array_or_empty |
| [[symbols/ragd/src/read_chunk_row-L68-858213cc|read_chunk_row]] | function | 68-88 | read_chunk_row |
| [[symbols/ragd/src/todo_to_json-L89-faba4645|todo_to_json]] | function | 89-107 | todo_to_json |
| [[symbols/ragd/src/session_to_json-L108-be28f516|session_to_json]] | function | 108-126 | session_to_json |
| [[symbols/ragd/src/now_utc-L127-fa6467d1|now_utc]] | function | 127-136 | now_utc |
| [[symbols/ragd/src/sha256ish-L137-3d5a3a31|sha256ish]] | function | 137-153 | sha256ish |
| [[symbols/ragd/src/Statement_bind-L154-ce126650|Statement::bind]] | function | 154-157 | Statement::bind |
| [[symbols/ragd/src/Statement_bind-L158-8e518700|Statement::bind]] | function | 158-161 | Statement::bind |
| [[symbols/ragd/src/Statement_bind-L162-c5f3f5e9|Statement::bind]] | function | 162-165 | Statement::bind |
| [[symbols/ragd/src/Statement_bind-L166-6fc0500a|Statement::bind]] | function | 166-169 | Statement::bind |
| [[symbols/ragd/src/Statement_bind_null-L170-6c560016|Statement::bind_null]] | function | 170-173 | Statement::bind_null |
| [[symbols/ragd/src/Statement_step_row-L174-8c38d950|Statement::step_row]] | function | 174-181 | Statement::step_row |
| [[symbols/ragd/src/Statement_step_done-L182-72bd67a8|Statement::step_done]] | function | 182-186 | Statement::step_done |
| [[symbols/ragd/src/Statement_column_int64-L187-873b96e4|Statement::column_int64]] | function | 187-187 | Statement::column_int64 |
| [[symbols/ragd/src/Statement_column_int-L188-c9cecdfe|Statement::column_int]] | function | 188-188 | Statement::column_int |
| [[symbols/ragd/src/Statement_column_double-L189-aa3262dd|Statement::column_double]] | function | 189-189 | Statement::column_double |
| [[symbols/ragd/src/Statement_column_text-L190-41f727ea|Statement::column_text]] | function | 190-195 | Statement::column_text |
| [[symbols/ragd/src/Storage_open-L196-4d9f8642|Storage::open]] | function | 196-199 | Storage::open |
| [[symbols/ragd/src/Storage_exec-L200-57087355|Storage::exec]] | function | 200-209 | Storage::exec |
| [[symbols/ragd/src/Storage_initialize-L210-cc29b509|Storage::initialize]] | function | 210-276 | Storage::initialize |
| [[symbols/ragd/src/Storage_health_check-L277-2175f77b|Storage::health_check]] | function | 277-281 | Storage::health_check |
| [[symbols/ragd/src/Storage_transaction-L282-a627a3bb|Storage::transaction]] | function | 282-292 | Storage::transaction |
| [[symbols/ragd/src/Storage_upsert_chunk-L293-a74df330|Storage::upsert_chunk]] | function | 293-362 | Storage::upsert_chunk |
| [[symbols/ragd/src/Storage_search_fts-L363-be66ab60|Storage::search_fts]] | function | 363-388 | Storage::search_fts |
| [[symbols/ragd/src/Storage_search_like-L389-5d3ec04d|Storage::search_like]] | function | 389-414 | Storage::search_like |
| [[symbols/ragd/src/Storage_recent_chunks-L415-6329cb03|Storage::recent_chunks]] | function | 415-422 | Storage::recent_chunks |
| [[symbols/ragd/src/Storage_get_chunk-L423-d063f98c|Storage::get_chunk]] | function | 423-429 | Storage::get_chunk |
| [[symbols/ragd/src/Storage_mark_file_deleted-L430-be9374bd|Storage::mark_file_deleted]] | function | 430-436 | Storage::mark_file_deleted |
| [[symbols/ragd/src/Storage_add_todo-L437-db6ee38d|Storage::add_todo]] | function | 437-464 | Storage::add_todo |
| [[symbols/ragd/src/Storage_list_todos-L465-13eb7791|Storage::list_todos]] | function | 465-468 | Storage::list_todos |
| [[symbols/ragd/src/Storage_list_todos_filtered-L469-82f9b77b|Storage::list_todos_filtered]] | function | 469-499 | Storage::list_todos_filtered |
| [[symbols/ragd/src/Storage_update_todo_status-L500-664f59ff|Storage::update_todo_status]] | function | 500-509 | Storage::update_todo_status |
| [[symbols/ragd/src/Storage_update_todo-L510-a985340b|Storage::update_todo]] | function | 510-520 | Storage::update_todo |
| [[symbols/ragd/src/Storage_start_session-L521-f9feea96|Storage::start_session]] | function | 521-534 | Storage::start_session |
| [[symbols/ragd/src/Storage_end_session-L535-8014ecfa|Storage::end_session]] | function | 535-544 | Storage::end_session |
| [[symbols/ragd/src/Storage_touch_file-L545-37d6eda6|Storage::touch_file]] | function | 545-554 | Storage::touch_file |
| [[symbols/ragd/src/Storage_add_decision-L555-6d4e3388|Storage::add_decision]] | function | 555-567 | Storage::add_decision |
| [[symbols/ragd/src/Storage_recent_decisions-L568-2b62bcaa|Storage::recent_decisions]] | function | 568-586 | Storage::recent_decisions |
| [[symbols/ragd/src/Storage_list_sessions-L587-6a522cc8|Storage::list_sessions]] | function | 587-615 | Storage::list_sessions |
| [[symbols/ragd/src/Storage_session_json-L616-27bcda2e|Storage::session_json]] | function | 616-648 | Storage::session_json |
| [[symbols/ragd/src/Storage_file_history_json-L649-3fbc486b|Storage::file_history_json]] | function | 649-660 | Storage::file_history_json |
| [[symbols/ragd/src/Storage_agent_timeline_json-L661-9d7a5277|Storage::agent_timeline_json]] | function | 661-667 | Storage::agent_timeline_json |
| [[symbols/ragd/src/Storage_add_bus_message-L668-c80ec23e|Storage::add_bus_message]] | function | 668-684 | Storage::add_bus_message |
| [[symbols/ragd/src/Storage_bus_messages_json-L685-f6133fa7|Storage::bus_messages_json]] | function | 685-703 | Storage::bus_messages_json |
| [[symbols/ragd/src/Storage_bus_locks_json-L704-ca13ec00|Storage::bus_locks_json]] | function | 704-713 | Storage::bus_locks_json |
| [[symbols/ragd/src/Storage_upsert_file_lock-L714-39446d88|Storage::upsert_file_lock]] | function | 714-731 | Storage::upsert_file_lock |
| [[symbols/ragd/src/Storage_add_dead_zone-L732-9c1cc7f7|Storage::add_dead_zone]] | function | 732-747 | Storage::add_dead_zone |
| [[symbols/ragd/src/Storage_dead_zones_json-L748-71362a7e|Storage::dead_zones_json]] | function | 748-758 | Storage::dead_zones_json |
| [[symbols/ragd/src/Storage_symbols_json-L759-99860c89|Storage::symbols_json]] | function | 759-772 | Storage::symbols_json |
| [[symbols/ragd/src/Storage_record_metric-L773-67e5743e|Storage::record_metric]] | function | 773-780 | Storage::record_metric |
| [[symbols/ragd/src/Storage_handoff_json-L781-e6f917cb|Storage::handoff_json]] | function | 781-808 | Storage::handoff_json |
| [[symbols/ragd/src/Storage_metrics_json-L809-e171ba69|Storage::metrics_json]] | function | 809-832 | Storage::metrics_json |

## Imports

- *(none indexed)*

## Call Graph

```mermaid
graph LR
    file --> symbols
```

## Recent Changes

> Content hash: `e171ba69ef3e247`. Last modified epoch: `-4659044606467787429`.
