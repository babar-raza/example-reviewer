-- Migration 010: Add app_context field to example_records
-- Purpose: Track application context type (console, aspnet_core_minimal, mvc, webapi, library)
-- Context: Phase-2 Gate B remediation - prevent cross-context substitution
--
-- This migration adds app_context as a new nullable column for backward compatibility.
-- Existing records will have NULL app_context until re-discovered or backfilled.

-- Add app_context column to example_records
ALTER TABLE example_records ADD COLUMN app_context TEXT DEFAULT NULL;

-- Add app_context column to example_run_state (run-scoped execution state)
ALTER TABLE example_run_state ADD COLUMN app_context TEXT DEFAULT NULL;

-- Create index for efficient context-based filtering
CREATE INDEX IF NOT EXISTS idx_example_records_app_context ON example_records(app_context);
CREATE INDEX IF NOT EXISTS idx_example_run_state_app_context ON example_run_state(run_id, app_context);

-- NOTE: Migration recording is handled automatically by the migration engine
-- DO NOT manually INSERT into schema_migrations here
