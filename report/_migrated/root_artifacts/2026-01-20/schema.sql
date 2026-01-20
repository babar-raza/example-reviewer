-- Aspose Example Review System - Database Schema
-- SQLite 3 with WAL mode for crash resilience

-- Enable WAL mode and foreign keys
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

-- ============================================================================
-- CORE TABLES
-- ============================================================================

-- Pages: Markdown files containing code snippets
CREATE TABLE IF NOT EXISTS pages (
    page_id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT NOT NULL UNIQUE,
    relative_path TEXT NOT NULL,
    site TEXT NOT NULL CHECK(site IN ('blog', 'docs', 'kb', 'reference', 'products')),
    family TEXT NOT NULL,
    language TEXT NOT NULL DEFAULT 'en',
    state TEXT NOT NULL DEFAULT 'unscanned' CHECK(state IN ('unscanned', 'scanned', 'validated', 'patched', 'deployed')),
    content_hash TEXT,
    last_scanned_at TEXT,
    last_validated_at TEXT,
    last_patched_at TEXT,
    snippet_count INTEGER DEFAULT 0,
    verified_snippet_count INTEGER DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_pages_family ON pages(family);
CREATE INDEX IF NOT EXISTS idx_pages_state ON pages(state);
CREATE INDEX IF NOT EXISTS idx_pages_site ON pages(site);
CREATE INDEX IF NOT EXISTS idx_pages_language ON pages(language);

-- Snippets: Individual code snippets within pages
CREATE TABLE IF NOT EXISTS snippets (
    snippet_id INTEGER PRIMARY KEY AUTOINCREMENT,
    page_id INTEGER NOT NULL,
    snippet_ordinal INTEGER NOT NULL,
    locator_json TEXT NOT NULL,
    snippet_type TEXT NOT NULL CHECK(snippet_type IN ('fence', 'gist')),
    language TEXT,
    status TEXT NOT NULL DEFAULT 'unverified' CHECK(status IN ('unverified', 'verified', 'needs-fix', 'skipped')),
    first_seen_at TEXT NOT NULL DEFAULT (datetime('now')),
    last_validated_at TEXT,
    validation_attempts INTEGER DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (page_id) REFERENCES pages(page_id) ON DELETE CASCADE,
    UNIQUE(page_id, snippet_ordinal)
);

CREATE INDEX IF NOT EXISTS idx_snippets_page ON snippets(page_id);
CREATE INDEX IF NOT EXISTS idx_snippets_status ON snippets(status);
CREATE INDEX IF NOT EXISTS idx_snippets_type ON snippets(snippet_type);

-- Snippet Versions: Track all versions of a snippet (original, fixed, current)
CREATE TABLE IF NOT EXISTS snippet_versions (
    version_id INTEGER PRIMARY KEY AUTOINCREMENT,
    snippet_id INTEGER NOT NULL,
    version_type TEXT NOT NULL CHECK(version_type IN ('original', 'fixed', 'current', 'before_fix')),
    code_content TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    created_by TEXT,
    notes TEXT,
    FOREIGN KEY (snippet_id) REFERENCES snippets(snippet_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_versions_snippet ON snippet_versions(snippet_id);
CREATE INDEX IF NOT EXISTS idx_versions_type ON snippet_versions(version_type);

-- ============================================================================
-- EXECUTION TRACKING
-- ============================================================================

-- Runs: Execution sessions (discovery, validation, patching)
CREATE TABLE IF NOT EXISTS runs (
    run_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_type TEXT NOT NULL CHECK(run_type IN ('discovery', 'validation', 'patching', 'verification')),
    family TEXT NOT NULL,
    started_at TEXT NOT NULL DEFAULT (datetime('now')),
    completed_at TEXT,
    status TEXT NOT NULL DEFAULT 'running' CHECK(status IN ('running', 'completed', 'failed', 'cancelled')),
    pages_processed INTEGER DEFAULT 0,
    snippets_processed INTEGER DEFAULT 0,
    config_snapshot TEXT,
    error_message TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_runs_family ON runs(family);
CREATE INDEX IF NOT EXISTS idx_runs_type ON runs(run_type);
CREATE INDEX IF NOT EXISTS idx_runs_status ON runs(status);

-- Run Events: Detailed event log for runs
CREATE TABLE IF NOT EXISTS run_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    severity TEXT NOT NULL CHECK(severity IN ('debug', 'info', 'warning', 'error')),
    message TEXT NOT NULL,
    details_json TEXT,
    occurred_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_events_run ON run_events(run_id);
CREATE INDEX IF NOT EXISTS idx_events_severity ON run_events(severity);
CREATE INDEX IF NOT EXISTS idx_events_occurred ON run_events(occurred_at);

-- ============================================================================
-- VALIDATION TRACKING
-- ============================================================================

-- Snippet Issues: Detected problems in snippets
CREATE TABLE IF NOT EXISTS snippet_issues (
    issue_id INTEGER PRIMARY KEY AUTOINCREMENT,
    snippet_id INTEGER NOT NULL,
    issue_type TEXT NOT NULL,
    description TEXT NOT NULL,
    detected_at TEXT NOT NULL DEFAULT (datetime('now')),
    resolved_at TEXT,
    severity TEXT CHECK(severity IN ('info', 'warning', 'error')),
    FOREIGN KEY (snippet_id) REFERENCES snippets(snippet_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_issues_snippet ON snippet_issues(snippet_id);
CREATE INDEX IF NOT EXISTS idx_issues_resolved ON snippet_issues(resolved_at);

-- Fixes Applied: Track all fixes applied to snippets
CREATE TABLE IF NOT EXISTS fixes_applied (
    fix_id INTEGER PRIMARY KEY AUTOINCREMENT,
    snippet_id INTEGER NOT NULL,
    issue_id INTEGER,
    fix_type TEXT NOT NULL CHECK(fix_type IN ('pattern', 'ollama', 'manual')),
    description TEXT NOT NULL,
    before_version_id INTEGER,
    after_version_id INTEGER,
    applied_at TEXT NOT NULL DEFAULT (datetime('now')),
    successful BOOLEAN NOT NULL,
    model_used TEXT,
    iteration_count INTEGER DEFAULT 1,
    context_inferred BOOLEAN DEFAULT 0,
    FOREIGN KEY (snippet_id) REFERENCES snippets(snippet_id) ON DELETE CASCADE,
    FOREIGN KEY (issue_id) REFERENCES snippet_issues(issue_id) ON DELETE SET NULL,
    FOREIGN KEY (before_version_id) REFERENCES snippet_versions(version_id),
    FOREIGN KEY (after_version_id) REFERENCES snippet_versions(version_id)
);

CREATE INDEX IF NOT EXISTS idx_fixes_snippet ON fixes_applied(snippet_id);
CREATE INDEX IF NOT EXISTS idx_fixes_type ON fixes_applied(fix_type);
CREATE INDEX IF NOT EXISTS idx_fixes_successful ON fixes_applied(successful);

-- Build Attempts: Compilation attempts
CREATE TABLE IF NOT EXISTS build_attempts (
    attempt_id INTEGER PRIMARY KEY AUTOINCREMENT,
    snippet_id INTEGER NOT NULL,
    version_id INTEGER NOT NULL,
    run_id INTEGER NOT NULL,
    success BOOLEAN NOT NULL,
    compiler_output TEXT,
    error_count INTEGER DEFAULT 0,
    warning_count INTEGER DEFAULT 0,
    attempted_at TEXT NOT NULL DEFAULT (datetime('now')),
    model_used TEXT,
    fix_session_id TEXT,
    FOREIGN KEY (snippet_id) REFERENCES snippets(snippet_id) ON DELETE CASCADE,
    FOREIGN KEY (version_id) REFERENCES snippet_versions(version_id) ON DELETE CASCADE,
    FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_attempts_snippet ON build_attempts(snippet_id);
CREATE INDEX IF NOT EXISTS idx_attempts_success ON build_attempts(success);
CREATE INDEX IF NOT EXISTS idx_attempts_run ON build_attempts(run_id);

-- Fix Sessions: Detailed tracking for persistent fix iterations
CREATE TABLE IF NOT EXISTS fix_sessions (
    session_id TEXT PRIMARY KEY,
    snippet_id INTEGER NOT NULL,
    run_id INTEGER NOT NULL,
    started_at TEXT NOT NULL DEFAULT (datetime('now')),
    completed_at TEXT,
    total_iterations INTEGER DEFAULT 0,
    models_tried TEXT,
    final_status TEXT CHECK(final_status IN ('success', 'max_iterations', 'infinite_loop', 'no_models', 'timeout')),
    context_inferred BOOLEAN DEFAULT 0,
    final_version_id INTEGER,
    error_history TEXT,
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
-- REPORTING VIEWS
-- ============================================================================

-- Active snippets (not skipped)
CREATE VIEW IF NOT EXISTS v_active_snippets AS
SELECT
    s.snippet_id,
    s.snippet_ordinal,
    s.status,
    s.snippet_type,
    s.language,
    s.validation_attempts,
    p.page_id,
    p.file_path,
    p.relative_path,
    p.family,
    p.language as page_language,
    p.site
FROM snippets s
JOIN pages p ON s.page_id = p.page_id
WHERE s.status != 'skipped';

-- Run statistics
CREATE VIEW IF NOT EXISTS v_run_statistics AS
SELECT
    r.run_id,
    r.run_type,
    r.family,
    r.status,
    r.started_at,
    r.completed_at,
    r.pages_processed,
    r.snippets_processed,
    CAST((julianday(COALESCE(r.completed_at, datetime('now'))) - julianday(r.started_at)) * 86400 AS INTEGER) as duration_seconds,
    COUNT(CASE WHEN re.severity = 'error' THEN 1 END) as error_count,
    COUNT(CASE WHEN re.severity = 'warning' THEN 1 END) as warning_count,
    COUNT(CASE WHEN re.severity = 'info' THEN 1 END) as info_count
FROM runs r
LEFT JOIN run_events re ON r.run_id = re.run_id
GROUP BY r.run_id;

-- Pages needing attention
CREATE VIEW IF NOT EXISTS v_pages_needing_attention AS
SELECT
    p.page_id,
    p.file_path,
    p.relative_path,
    p.family,
    p.language,
    p.state,
    COUNT(s.snippet_id) as total_snippets,
    COUNT(CASE WHEN s.status = 'needs-fix' THEN 1 END) as needs_fix_count,
    COUNT(CASE WHEN s.status = 'verified' THEN 1 END) as verified_count,
    COUNT(CASE WHEN s.status = 'unverified' THEN 1 END) as unverified_count
FROM pages p
LEFT JOIN snippets s ON p.page_id = s.page_id
WHERE p.state IN ('scanned', 'validated')
GROUP BY p.page_id
HAVING needs_fix_count > 0 OR unverified_count > 0;

-- Snippet validation summary
CREATE VIEW IF NOT EXISTS v_snippet_validation_summary AS
SELECT
    s.snippet_id,
    s.status,
    p.relative_path,
    p.family,
    COUNT(DISTINCT ba.attempt_id) as build_attempts,
    COUNT(DISTINCT fa.fix_id) as fixes_applied,
    COUNT(DISTINCT si.issue_id) as issues_detected,
    MAX(ba.attempted_at) as last_build_at,
    (SELECT version_type FROM snippet_versions sv
     WHERE sv.snippet_id = s.snippet_id
     ORDER BY sv.created_at DESC LIMIT 1) as current_version_type
FROM snippets s
JOIN pages p ON s.page_id = p.page_id
LEFT JOIN build_attempts ba ON s.snippet_id = ba.snippet_id
LEFT JOIN fixes_applied fa ON s.snippet_id = fa.snippet_id
LEFT JOIN snippet_issues si ON s.snippet_id = si.snippet_id
GROUP BY s.snippet_id;

-- Fix session statistics
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
-- TRIGGERS FOR AUTO-UPDATE
-- ============================================================================

-- Auto-update pages.updated_at
CREATE TRIGGER IF NOT EXISTS trg_pages_updated_at
AFTER UPDATE ON pages
FOR EACH ROW
BEGIN
    UPDATE pages SET updated_at = datetime('now') WHERE page_id = NEW.page_id;
END;

-- Auto-update snippets.updated_at
CREATE TRIGGER IF NOT EXISTS trg_snippets_updated_at
AFTER UPDATE ON snippets
FOR EACH ROW
BEGIN
    UPDATE snippets SET updated_at = datetime('now') WHERE snippet_id = NEW.snippet_id;
END;

-- Auto-update snippet counts on pages
CREATE TRIGGER IF NOT EXISTS trg_update_page_snippet_count_insert
AFTER INSERT ON snippets
FOR EACH ROW
BEGIN
    UPDATE pages
    SET snippet_count = snippet_count + 1
    WHERE page_id = NEW.page_id;
END;

CREATE TRIGGER IF NOT EXISTS trg_update_page_snippet_count_delete
AFTER DELETE ON snippets
FOR EACH ROW
BEGIN
    UPDATE pages
    SET snippet_count = snippet_count - 1
    WHERE page_id = OLD.page_id;
END;

-- Auto-update verified snippet count
CREATE TRIGGER IF NOT EXISTS trg_update_verified_count_insert
AFTER INSERT ON snippets
FOR EACH ROW WHEN NEW.status = 'verified'
BEGIN
    UPDATE pages
    SET verified_snippet_count = verified_snippet_count + 1
    WHERE page_id = NEW.page_id;
END;

CREATE TRIGGER IF NOT EXISTS trg_update_verified_count_update
AFTER UPDATE OF status ON snippets
FOR EACH ROW
BEGIN
    UPDATE pages
    SET verified_snippet_count = verified_snippet_count +
        CASE WHEN NEW.status = 'verified' THEN 1 ELSE 0 END -
        CASE WHEN OLD.status = 'verified' THEN 1 ELSE 0 END
    WHERE page_id = NEW.page_id;
END;

-- ============================================================================
-- GIST SUPPORT TABLES
-- ============================================================================

-- Gists: Metadata for GitHub Gists
CREATE TABLE IF NOT EXISTS gists (
    gist_id TEXT PRIMARY KEY,
    owner TEXT NOT NULL,
    description TEXT,
    is_public BOOLEAN NOT NULL DEFAULT 1,
    updated_at TEXT,
    etag TEXT,
    last_fetched_at TEXT NOT NULL DEFAULT (datetime('now')),
    last_status TEXT CHECK(last_status IN ('success', 'not_found', 'rate_limited', 'error')),
    last_error TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_gists_owner ON gists(owner);
CREATE INDEX IF NOT EXISTS idx_gists_last_fetched ON gists(last_fetched_at);
CREATE INDEX IF NOT EXISTS idx_gists_status ON gists(last_status);

-- Gist Files: Individual files within a gist
CREATE TABLE IF NOT EXISTS gist_files (
    gist_id TEXT NOT NULL,
    filename TEXT NOT NULL,
    raw_url TEXT NOT NULL,
    language TEXT,
    content TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    file_size INTEGER,
    fetched_at TEXT NOT NULL DEFAULT (datetime('now')),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (gist_id) REFERENCES gists(gist_id) ON DELETE CASCADE,
    PRIMARY KEY (gist_id, filename)
);

CREATE INDEX IF NOT EXISTS idx_gist_files_language ON gist_files(language);
CREATE INDEX IF NOT EXISTS idx_gist_files_hash ON gist_files(content_hash);

-- ============================================================================
-- INITIAL DATA
-- ============================================================================

-- Schema version tracking
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL DEFAULT (datetime('now')),
    description TEXT
);

INSERT OR IGNORE INTO schema_version (version, description)
VALUES (1, 'Initial schema - core tables, views, triggers');

INSERT OR IGNORE INTO schema_version (version, description)
VALUES (2, 'Gist support - gists and gist_files tables');

-- ============================================================================
-- GIST PUBLISHING SUPPORT (Phase 5)
-- ============================================================================

-- Gist Publications: Track published gists when code changes
CREATE TABLE IF NOT EXISTS gist_publications (
    publication_id INTEGER PRIMARY KEY AUTOINCREMENT,
    snippet_id INTEGER NOT NULL,
    old_gist_id TEXT,
    old_gist_owner TEXT,
    old_gist_filename TEXT,
    new_gist_id TEXT NOT NULL,
    new_gist_owner TEXT NOT NULL,
    new_gist_filename TEXT NOT NULL,
    new_gist_url TEXT NOT NULL,
    new_gist_raw_url TEXT NOT NULL,
    published_at TEXT NOT NULL DEFAULT (datetime('now')),
    status TEXT NOT NULL CHECK(status IN ('success', 'failed', 'pending')),
    error_message TEXT,
    code_hash TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (snippet_id) REFERENCES snippets(snippet_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_publications_snippet ON gist_publications(snippet_id);
CREATE INDEX IF NOT EXISTS idx_publications_old_gist ON gist_publications(old_gist_id);
CREATE INDEX IF NOT EXISTS idx_publications_new_gist ON gist_publications(new_gist_id);
CREATE INDEX IF NOT EXISTS idx_publications_status ON gist_publications(status);

-- Rollback history for patching operations
CREATE TABLE IF NOT EXISTS rollback_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    family TEXT,
    commit_sha TEXT,
    backup_branch TEXT,
    backup_commit TEXT,
    description TEXT,
    modified_files TEXT
);

CREATE INDEX IF NOT EXISTS idx_rollback_created_at ON rollback_history(created_at);
CREATE INDEX IF NOT EXISTS idx_rollback_family ON rollback_history(family);

-- Schema version update
INSERT OR IGNORE INTO schema_version (version, description)
VALUES (3, 'Gist publishing support - gist_publications table');

INSERT OR IGNORE INTO schema_version (version, description)
VALUES (4, 'Persistent fix support - iterative LLM fixing with model fallback');

INSERT OR IGNORE INTO schema_version (version, description)
VALUES (5, 'Rollback history support for patching operations');

-- ============================================================================
-- RUNTIME EXECUTION TRACKING (Phase 2)
-- ============================================================================

-- Execution Results: Store runtime execution results
CREATE TABLE IF NOT EXISTS execution_results (
    execution_id INTEGER PRIMARY KEY AUTOINCREMENT,
    snippet_id INTEGER NOT NULL,
    run_id INTEGER NOT NULL,

    -- Execution status
    success BOOLEAN NOT NULL,
    exit_code INTEGER,
    duration_ms INTEGER,

    -- Output capture
    stdout TEXT,
    stderr TEXT,

    -- Exception detection
    exception_type TEXT,
    exception_message TEXT,
    stack_trace TEXT,

    -- Additional metadata
    output_files_json TEXT,
    memory_peak_kb INTEGER,

    created_at TEXT NOT NULL DEFAULT (datetime('now')),

    FOREIGN KEY (snippet_id) REFERENCES snippets(snippet_id) ON DELETE CASCADE,
    FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_execution_results_snippet ON execution_results(snippet_id, run_id);
CREATE INDEX IF NOT EXISTS idx_execution_results_success ON execution_results(success);
CREATE INDEX IF NOT EXISTS idx_execution_results_created ON execution_results(created_at);

-- Schema version update
INSERT OR IGNORE INTO schema_version (version, description)
VALUES (6, 'Runtime execution tracking - execution_results table');

