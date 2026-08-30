-- Migration 015: Add run_manifests table (TC-EPIC3-05)
-- Purpose: Persist "what actually happened during this run" -- resolved NuGet
--          versions (TC-EPIC3-01), Docker image digest (TC-EPIC3-02), LLM call
--          reproducibility stats (TC-EPIC3-03), pattern_set_version
--          (TC-EPIC3-04), and circuit-breaker state at run start (TC-EPIC3-06)
--          -- so "why did this run behave this way" is answerable by a single
--          lookup instead of cross-referencing multiple log files.
-- Context: reports/investigation/20260829_124758_production_readiness/
--          taskcards/TC-EPIC3-05.md

CREATE TABLE IF NOT EXISTS run_manifests (
    run_id TEXT PRIMARY KEY,
    git_sha TEXT,
    resolved_nuget_versions TEXT,
    docker_image_digest TEXT,
    pattern_set_version INTEGER,
    circuit_breaker_state_at_start TEXT,
    llm_call_stats TEXT,
    per_example_elapsed_seconds TEXT,
    created_at TEXT NOT NULL,
    finalized_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_run_manifests_created ON run_manifests(created_at);

-- NOTE: Migration recording is handled automatically by the migration engine
-- DO NOT manually INSERT into schema_migrations here

-- NOTE (per the pattern established by migrations 013/014): this table IS
-- also added to the SCHEMA constant / base_tables allowlist in
-- src/core/database.py in this same change (TC-EPIC2-03 already generalized
-- fresh-DB migration verification and is the taskcard this note would
-- otherwise be addressed to) -- so fresh clones get this table created via
-- the baseline path, not by relying on this migration file executing on a
-- non-fresh DB.
