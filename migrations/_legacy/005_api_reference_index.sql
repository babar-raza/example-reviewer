-- Migration 005: API Reference Index
-- Purpose: Create database schema for storing parsed API reference documentation
-- Used by: API Index Builder to populate, API Reference Service to query

-- API Reference Index Table
CREATE TABLE IF NOT EXISTS api_reference (
    api_id INTEGER PRIMARY KEY AUTOINCREMENT,
    family TEXT NOT NULL,
    namespace TEXT NOT NULL,
    class_name TEXT NOT NULL,
    member_type TEXT NOT NULL CHECK(member_type IN ('constructor', 'method', 'property', 'field', 'event', 'class')),
    member_name TEXT,
    signature TEXT NOT NULL,
    description TEXT,
    example_code TEXT,
    notes TEXT,
    assembly_version TEXT,
    is_static BOOLEAN DEFAULT 0,
    is_readonly BOOLEAN DEFAULT 0,
    return_type TEXT,
    parameters TEXT,  -- JSON array of parameter info
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(family, class_name, member_type, member_name, signature)
);

-- Indexes for fast queries
CREATE INDEX IF NOT EXISTS idx_api_family ON api_reference(family);
CREATE INDEX IF NOT EXISTS idx_api_class ON api_reference(family, class_name);
CREATE INDEX IF NOT EXISTS idx_api_member ON api_reference(member_type, member_name);
CREATE INDEX IF NOT EXISTS idx_api_namespace ON api_reference(namespace);

-- View for quick class lookups
CREATE VIEW IF NOT EXISTS v_api_classes AS
SELECT DISTINCT family, namespace, class_name, assembly_version
FROM api_reference
WHERE member_type = 'class'
ORDER BY family, namespace, class_name;

-- Schema version update
INSERT OR IGNORE INTO schema_version (version, description, applied_at)
VALUES (5, 'API reference index for LLM context enrichment', datetime('now'));
