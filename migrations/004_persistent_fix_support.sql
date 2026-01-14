-- Migration 004: Persistent Fix Support
-- Adds tracking for iterative LLM-based code fixing with model fallback

-- Enable foreign keys
PRAGMA foreign_keys=ON;

-- ============================================================================
-- EXTEND EXISTING TABLES
-- ============================================================================

-- Add model and iteration tracking to fixes_applied
ALTER TABLE fixes_applied ADD COLUMN model_used TEXT;
ALTER TABLE fixes_applied ADD COLUMN iteration_count INTEGER DEFAULT 1;
ALTER TABLE fixes_applied ADD COLUMN context_inferred BOOLEAN DEFAULT 0;

-- Add model and session tracking to build_attempts
ALTER TABLE build_attempts ADD COLUMN model_used TEXT;
ALTER TABLE build_attempts ADD COLUMN fix_session_id TEXT;

-- ============================================================================
-- NEW TABLES
-- ============================================================================

-- Fix Sessions: Detailed tracking for persistent fix iterations
CREATE TABLE IF NOT EXISTS fix_sessions (
    session_id TEXT PRIMARY KEY,
    snippet_id INTEGER NOT NULL,
    run_id INTEGER NOT NULL,
    started_at TEXT NOT NULL DEFAULT (datetime('now')),
    completed_at TEXT,
    total_iterations INTEGER DEFAULT 0,
    models_tried TEXT,  -- JSON array of models attempted
    final_status TEXT CHECK(final_status IN ('success', 'max_iterations', 'infinite_loop', 'no_models', 'timeout')),
    context_inferred BOOLEAN DEFAULT 0,
    final_version_id INTEGER,
    error_history TEXT,  -- JSON array of error hashes for infinite loop detection
    duration_seconds INTEGER,
    notes TEXT,
    FOREIGN KEY (snippet_id) REFERENCES snippets(snippet_id) ON DELETE CASCADE,
    FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE,
    FOREIGN KEY (final_version_id) REFERENCES snippet_versions(version_id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_fix_sessions_snippet ON fix_sessions(snippet_id);
CREATE INDEX IF NOT EXISTS idx_fix_sessions_run ON fix_sessions(run_id);
CREATE INDEX IF NOT EXISTS idx_fix_sessions_status ON fix_sessions(final_status);
CREATE INDEX IF NOT EXISTS idx_fix_sessions_started ON fix_sessions(started_at);

-- ============================================================================
-- REPORTING VIEW
-- ============================================================================

-- Fix session statistics view
CREATE VIEW IF NOT EXISTS v_fix_session_statistics AS
SELECT
    fs.session_id,
    fs.snippet_id,
    fs.run_id,
    fs.final_status,
    fs.total_iterations,
    fs.models_tried,
    fs.context_inferred,
    fs.duration_seconds,
    s.status as snippet_status,
    p.relative_path,
    p.family,
    fs.started_at,
    fs.completed_at
FROM fix_sessions fs
JOIN snippets s ON fs.snippet_id = s.snippet_id
JOIN pages p ON s.page_id = p.page_id;

-- ============================================================================
-- SCHEMA VERSION UPDATE
-- ============================================================================

INSERT OR IGNORE INTO schema_version (version, description)
VALUES (4, 'Persistent fix support - iterative LLM fixing with model fallback');
