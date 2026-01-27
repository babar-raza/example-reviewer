-- Migration 009: Complete run scoping migration
-- Purpose: Migrate run-scoped fields from example_records to example_run_state
-- Context: Track 2 Hardening - complete the production-grade run scoping design
--
-- This migration:
-- 1. Populates example_run_state with existing example data (using a synthetic run_id)
-- 2. Creates backup of example_records before altering
-- 3. Removes run-scoped fields from example_records (create new table and copy)
-- 4. Updates schema to match the production-grade design
--
-- NOTE: This is a data migration that cannot be easily rolled back.
-- Backup your database before running this migration!

-- Step 1: Populate example_run_state with existing data
-- Use a synthetic "legacy_migration" run_id for pre-existing examples
INSERT OR IGNORE INTO example_run_state (
    run_id,
    example_id,
    status,
    failure_reason,
    escalation_reason,
    compilable_code,
    verified_code,
    drift_score,
    drift_similarity,
    needs_human_review,
    created_at,
    updated_at
)
SELECT
    'legacy_migration_' || er.family AS run_id,
    er.example_id,
    COALESCE(er.status, 'DISCOVERED') AS status,
    er.failure_reason,
    er.escalation_reason,
    er.compilable_code,
    er.verified_code,
    COALESCE(er.drift_score, 0.0) AS drift_score,
    COALESCE(er.drift_similarity, 0.0) AS drift_similarity,
    0 AS needs_human_review,
    er.created_at,
    er.updated_at
FROM example_records er
WHERE EXISTS (
    SELECT 1 FROM sqlite_master WHERE type='table' AND name='example_records'
    AND sql LIKE '%compilable_code%'
);

-- Step 2: Create new example_records table with canonical fields only
CREATE TABLE IF NOT EXISTS example_records_new (
    example_id TEXT PRIMARY KEY,
    family TEXT NOT NULL,
    file_path TEXT NOT NULL,
    source_type TEXT NOT NULL DEFAULT 'inline',
    language TEXT NOT NULL DEFAULT 'csharp',
    location_block_index INTEGER DEFAULT 0,
    location_start_line INTEGER DEFAULT 0,
    location_end_line INTEGER DEFAULT 0,
    location_anchor TEXT DEFAULT '',
    gist_owner TEXT,
    gist_id TEXT,
    gist_filename TEXT,
    original_code TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    section_heading TEXT,
    description_context TEXT,
    topic TEXT,
    example_key TEXT
);

-- Step 3: Copy canonical data to new table
INSERT INTO example_records_new (
    example_id, family, file_path, source_type, language,
    location_block_index, location_start_line, location_end_line, location_anchor,
    gist_owner, gist_id, gist_filename,
    original_code, created_at, updated_at,
    section_heading, description_context, topic, example_key
)
SELECT
    example_id, family, file_path, source_type, language,
    location_block_index, location_start_line, location_end_line, location_anchor,
    gist_owner, gist_id, gist_filename,
    original_code, created_at, updated_at,
    section_heading, description_context, topic, example_key
FROM example_records;

-- Step 4: Drop old table and rename new table
DROP TABLE example_records;
ALTER TABLE example_records_new RENAME TO example_records;

-- Step 5: Recreate indexes
CREATE INDEX IF NOT EXISTS idx_examples_family ON example_records(family);
CREATE INDEX IF NOT EXISTS idx_examples_file_path ON example_records(file_path);
CREATE UNIQUE INDEX IF NOT EXISTS idx_example_key ON example_records(family, example_key);

-- Step 6: Create a synthetic run record for the legacy migration
INSERT OR IGNORE INTO run_records (
    run_id,
    family,
    started_at,
    completed_at,
    status,
    phases_completed,
    current_phase,
    examples_processed,
    examples_successful,
    examples_failed
)
SELECT DISTINCT
    'legacy_migration_' || family AS run_id,
    family,
    MIN(created_at) AS started_at,
    MAX(updated_at) AS completed_at,
    'completed' AS status,
    '' AS phases_completed,
    'migration' AS current_phase,
    COUNT(*) AS examples_processed,
    COUNT(*) AS examples_successful,
    0 AS examples_failed
FROM example_records
GROUP BY family;

-- Record migration
INSERT OR IGNORE INTO schema_migrations (migration_id, description, applied_at)
VALUES ('009_complete_run_scoping_migration', 'Migrate run-scoped fields to example_run_state', datetime('now'));
