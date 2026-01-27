-- Migration 008: Production-grade run scoping with example_run_state table
-- Purpose: Enable per-run isolation and prevent cross-run data leakage
-- Context: Track 2 Hardening - workspace copy mode and run isolation
--
-- Design (production-grade):
-- - Keep example_records as canonical per-example metadata (no run_id)
-- - Create example_run_state table keyed by (run_id, example_id) for per-run state
-- - Add run_id to compile_attempts, runtime_attempts, markdown_edits
--
-- This allows:
-- - Truthful reporting (no mixing of results from different runs)
-- - Parallel runs without interference
-- - Run-specific artifact management
-- - Accurate KPI calculations per run
-- - Stable example_id across runs (no overwriting)

-- Create schema_migrations table if it doesn't exist (for migration tracking)
CREATE TABLE IF NOT EXISTS schema_migrations (
    migration_id TEXT PRIMARY KEY,
    description TEXT NOT NULL,
    applied_at TEXT NOT NULL
);

-- Create example_run_state table for per-run example state
-- This replaces the flawed "add run_id to example_records" approach
CREATE TABLE IF NOT EXISTS example_run_state (
    run_id TEXT NOT NULL,
    example_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'discovered',
    failure_reason TEXT,
    escalation_reason TEXT,
    compilable_code TEXT,
    verified_code TEXT,
    drift_score REAL DEFAULT 0.0,
    needs_human_review INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (run_id, example_id),
    FOREIGN KEY (run_id) REFERENCES run_records(run_id) ON DELETE CASCADE,
    FOREIGN KEY (example_id) REFERENCES example_records(example_id) ON DELETE CASCADE
);

-- Indexes for example_run_state
CREATE INDEX IF NOT EXISTS idx_run_state_run ON example_run_state(run_id);
CREATE INDEX IF NOT EXISTS idx_run_state_example ON example_run_state(example_id);
CREATE INDEX IF NOT EXISTS idx_run_state_status ON example_run_state(run_id, status);
CREATE INDEX IF NOT EXISTS idx_run_state_family ON example_run_state(run_id);

-- Add run_id to compile_attempts (if not already present)
-- This tracks which run each compilation attempt belongs to
ALTER TABLE compile_attempts ADD COLUMN run_id TEXT;

-- Add run_id to runtime_attempts (if not already present)
-- This tracks which run each runtime attempt belongs to
ALTER TABLE runtime_attempts ADD COLUMN run_id TEXT;

-- Add run_id to markdown_edits (if not already present)
-- This tracks which run each markdown edit belongs to
ALTER TABLE markdown_edits ADD COLUMN run_id TEXT;

-- Create indexes for efficient run-scoped queries
-- These indexes dramatically improve query performance when filtering by run_id

-- Index for quickly finding all compile attempts for a run
CREATE INDEX IF NOT EXISTS idx_compile_run ON compile_attempts(run_id);

-- Index for quickly finding all runtime attempts for a run
CREATE INDEX IF NOT EXISTS idx_runtime_run ON runtime_attempts(run_id);

-- Index for quickly finding all markdown edits for a run
CREATE INDEX IF NOT EXISTS idx_markdown_run ON markdown_edits(run_id);

-- Composite indexes for common query patterns

-- Query compile attempts by example and run
CREATE INDEX IF NOT EXISTS idx_compile_example_run ON compile_attempts(example_id, run_id);

-- Query runtime attempts by example and run
CREATE INDEX IF NOT EXISTS idx_runtime_example_run ON runtime_attempts(example_id, run_id);

-- Record migration
INSERT OR IGNORE INTO schema_migrations (migration_id, description, applied_at)
VALUES ('008_run_scoping', 'Production-grade run scoping with example_run_state', datetime('now'));

-- Notes on design:
-- - example_records remains canonical (family, file_path, original_code, etc.)
-- - example_run_state holds per-run state (status, failure_reason, compilable_code, etc.)
-- - This prevents overwriting across runs while keeping stable example_id
-- - Queries must join example_records with example_run_state for run-scoped results
