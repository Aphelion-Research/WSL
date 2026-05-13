-- Migration 0003: Multi-agent memory ledger
-- Applied to: ~/.ragd/ragd.db (RAGD primary store)
-- Note: These tables are also created by dominion_loader/ledger.py at runtime.
-- Agent 2 can query ledger entries via direct RAGD DB access or future RAGD API.

PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS ledger_entries(
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id   TEXT NOT NULL DEFAULT '',
    kind         TEXT NOT NULL,
    payload_json TEXT NOT NULL DEFAULT '{}',
    content_hash TEXT NOT NULL UNIQUE,
    created_at   INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_ledger_kind
    ON ledger_entries(kind);

CREATE INDEX IF NOT EXISTS idx_ledger_session
    ON ledger_entries(session_id);

CREATE INDEX IF NOT EXISTS idx_ledger_created
    ON ledger_entries(created_at);

CREATE TABLE IF NOT EXISTS ledger_tags(
    entry_id INTEGER NOT NULL REFERENCES ledger_entries(id) ON DELETE CASCADE,
    tag      TEXT NOT NULL,
    PRIMARY KEY(entry_id, tag)
);

CREATE INDEX IF NOT EXISTS idx_ledger_tags_tag
    ON ledger_tags(tag);
