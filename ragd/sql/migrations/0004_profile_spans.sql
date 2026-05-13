-- Migration 0004: Self-profiling span store
-- Applied to: ~/.dominion/manifest.db
-- Note: These tables are also created by dominion_loader/profiler.py at runtime.
-- Stores performance span records for the foundation profiler (S01).

PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS profile_spans(
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    trace_id   TEXT NOT NULL DEFAULT '',
    stage      TEXT NOT NULL,
    duration_ms REAL NOT NULL DEFAULT 0.0,
    attrs_json TEXT NOT NULL DEFAULT '{}',
    recorded_at INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_profile_spans_stage
    ON profile_spans(stage);

CREATE INDEX IF NOT EXISTS idx_profile_spans_recorded_at
    ON profile_spans(recorded_at);

CREATE INDEX IF NOT EXISTS idx_profile_spans_trace_id
    ON profile_spans(trace_id);
