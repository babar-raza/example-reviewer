-- Migration 007: Failure Details Tracking for Analytics
-- Purpose: Enable structured failure tracking across all pipeline phases
-- Used by: Pipeline orchestrator and analytics queries
-- Context: Track 2 Swarm Orchestration - Agent F implementation

-- Failure details table for comprehensive failure tracking
CREATE TABLE IF NOT EXISTS failure_details (
    failure_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    example_id TEXT,
    phase TEXT NOT NULL,
    failure_category TEXT NOT NULL CHECK(failure_category IN (
        'timeout',
        'drift_exceeded',
        'api_context_missing',
        'llm_response_rejected',
        'escalated_to_review',
        'compile_error',
        'runtime_error',
        'review_failed',
        'other'
    )),
    error_category TEXT,
    error_message TEXT,
    resolution TEXT CHECK(resolution IN ('fixed', 'needs_review', 'abandoned', 'pending')),
    metadata TEXT,  -- JSON for additional context
    timestamp TEXT NOT NULL,
    FOREIGN KEY (run_id) REFERENCES run_records(run_id) ON DELETE CASCADE,
    FOREIGN KEY (example_id) REFERENCES example_records(example_id) ON DELETE SET NULL
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_failure_run_phase ON failure_details(run_id, phase);
CREATE INDEX IF NOT EXISTS idx_failure_category ON failure_details(failure_category);
CREATE INDEX IF NOT EXISTS idx_failure_error_category ON failure_details(error_category);
CREATE INDEX IF NOT EXISTS idx_failure_resolution ON failure_details(resolution);
CREATE INDEX IF NOT EXISTS idx_failure_timestamp ON failure_details(timestamp);
CREATE INDEX IF NOT EXISTS idx_failure_example ON failure_details(example_id);

-- View for failure analytics by category
CREATE VIEW IF NOT EXISTS v_failure_breakdown AS
SELECT
    failure_category,
    COUNT(*) as failure_count,
    COUNT(DISTINCT example_id) as affected_examples,
    COUNT(DISTINCT run_id) as affected_runs,
    COUNT(CASE WHEN resolution = 'fixed' THEN 1 END) as fixed_count,
    COUNT(CASE WHEN resolution = 'needs_review' THEN 1 END) as needs_review_count,
    COUNT(CASE WHEN resolution = 'abandoned' THEN 1 END) as abandoned_count,
    COUNT(CASE WHEN resolution = 'pending' THEN 1 END) as pending_count
FROM failure_details
GROUP BY failure_category
ORDER BY failure_count DESC;

-- View for top error types
CREATE VIEW IF NOT EXISTS v_top_error_types AS
SELECT
    error_category,
    failure_category,
    COUNT(*) as occurrence_count,
    COUNT(DISTINCT example_id) as affected_examples,
    COUNT(CASE WHEN resolution = 'fixed' THEN 1 END) as fixed_count,
    ROUND(100.0 * COUNT(CASE WHEN resolution = 'fixed' THEN 1 END) / COUNT(*), 2) as fix_rate_pct
FROM failure_details
WHERE error_category IS NOT NULL
GROUP BY error_category, failure_category
ORDER BY occurrence_count DESC;

-- View for resolution success rates
CREATE VIEW IF NOT EXISTS v_resolution_rates AS
SELECT
    phase,
    failure_category,
    COUNT(*) as total_failures,
    COUNT(CASE WHEN resolution = 'fixed' THEN 1 END) as fixed,
    COUNT(CASE WHEN resolution = 'needs_review' THEN 1 END) as needs_review,
    COUNT(CASE WHEN resolution = 'abandoned' THEN 1 END) as abandoned,
    COUNT(CASE WHEN resolution = 'pending' THEN 1 END) as pending,
    ROUND(100.0 * COUNT(CASE WHEN resolution = 'fixed' THEN 1 END) / COUNT(*), 2) as fix_rate_pct
FROM failure_details
GROUP BY phase, failure_category
ORDER BY phase, total_failures DESC;

-- Schema version update
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    description TEXT NOT NULL,
    applied_at TEXT NOT NULL DEFAULT (datetime('now'))
);

INSERT OR IGNORE INTO schema_version (version, description, applied_at)
VALUES (7, 'Failure details tracking for comprehensive analytics', datetime('now'));
