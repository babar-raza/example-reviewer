-- Migration 014: Add status_transitions table for the State Authority (TC-EPIC2-01)
-- Purpose: Record every StateAuthority.transition() outcome -- both successful writes
--          AND blocked/illegal attempts -- making Root Cause 2 (no single authority for
--          "is this a legal status change") empirically falsifiable going forward, the
--          same pattern TC-EPIC1-01's authority_audit table established for capability
--          checks.
-- Context: reports/investigation/20260829_124758_production_readiness/FINDINGS_REGISTER.md
--          (Root cause 2); taskcards/TC-EPIC2-01.md

CREATE TABLE IF NOT EXISTS status_transitions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    example_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    from_status TEXT,
    to_status TEXT NOT NULL,
    evidence_ref TEXT,
    timestamp TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_status_transitions_example ON status_transitions(example_id);
CREATE INDEX IF NOT EXISTS idx_status_transitions_run ON status_transitions(run_id);

-- NOTE: Migration recording is handled automatically by the migration engine
-- DO NOT manually INSERT into schema_migrations here

-- NOTE for whoever lands TC-EPIC2-03: this table is intentionally NOT added to the
-- SCHEMA constant / base_tables allowlist in src/core/database.py, for the same reason
-- migration 013's note gives for authority_audit -- so _is_fresh_database()'s
-- fresh-bootstrap path does not need to change for this taskcard. TC-EPIC2-03 already
-- touches _is_fresh_database()/SCHEMA to fix the migration-007 views gap (F-038) --
-- when it does, add status_transitions (alongside authority_audit) to both SCHEMA and
-- base_tables in the same change so fresh clones get this table created via the
-- baseline path instead of relying on this migration file executing on a non-fresh DB.
