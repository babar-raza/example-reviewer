-- Migration 013: Add authority_audit table for the Authorization Kernel (TC-EPIC1-01)
-- Purpose: Record every PolicyDecisionPoint.check() outcome (allow AND deny), making
--          Root Cause 1 (no single authority for "is this action allowed") empirically
--          falsifiable going forward -- an operator can query this table and see every
--          gate evaluation, not just the ones that happened to be logged elsewhere.
-- Context: reports/investigation/20260829_124758_production_readiness/FINDINGS_REGISTER.md
--          F-012, F-013, F-014; taskcards/TC-EPIC1-01.md

CREATE TABLE IF NOT EXISTS authority_audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    capability TEXT NOT NULL,
    resource TEXT,
    decision TEXT NOT NULL CHECK(decision IN ('allow', 'deny')),
    policy_id TEXT NOT NULL,
    run_id TEXT,
    reason TEXT,
    timestamp TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_authority_audit_run ON authority_audit(run_id);
CREATE INDEX IF NOT EXISTS idx_authority_audit_capability ON authority_audit(capability);

-- NOTE: Migration recording is handled automatically by the migration engine
-- DO NOT manually INSERT into schema_migrations here

-- NOTE for whoever lands TC-EPIC2-03: this table is intentionally NOT added to the
-- SCHEMA constant / base_tables allowlist in src/core/database.py, so that
-- _is_fresh_database()'s fresh-bootstrap path does not need to change for this
-- taskcard. TC-EPIC2-03 already touches _is_fresh_database() to fix the migration-007
-- views gap (F-038) -- when it does, add authority_audit to both SCHEMA and
-- base_tables in the same change so fresh clones get this table created via the
-- baseline path instead of relying on this migration file executing on a non-fresh DB.
