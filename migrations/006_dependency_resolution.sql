-- Migration 006: Automatic NuGet Dependency Resolution
-- Purpose: Enable automatic detection and installation of NuGet dependencies
-- Used by: DependencyResolver to map namespaces to packages and track resolutions
-- Context: Solves PDF family 0% success rate and enables robust handling of external dependencies

-- Namespace to Package mapping table
CREATE TABLE IF NOT EXISTS namespace_to_package (
    mapping_id INTEGER PRIMARY KEY AUTOINCREMENT,
    namespace TEXT NOT NULL,
    package_name TEXT NOT NULL,
    package_version TEXT,
    source TEXT NOT NULL CHECK(source IN ('bcl', 'manual', 'inference', 'nuget_api')),
    confidence REAL DEFAULT 1.0,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(namespace, package_name)
);

CREATE INDEX IF NOT EXISTS idx_namespace_lookup ON namespace_to_package(namespace);
CREATE INDEX IF NOT EXISTS idx_package_lookup ON namespace_to_package(package_name);
CREATE INDEX IF NOT EXISTS idx_namespace_source ON namespace_to_package(source);

-- Dependency resolution tracking per snippet
CREATE TABLE IF NOT EXISTS dependency_resolutions (
    resolution_id INTEGER PRIMARY KEY AUTOINCREMENT,
    snippet_id INTEGER NOT NULL,
    run_id INTEGER,
    namespace TEXT NOT NULL,
    package_name TEXT,
    package_version TEXT,
    resolution_status TEXT NOT NULL CHECK(resolution_status IN ('detected', 'resolved', 'failed', 'bcl')),
    resolution_source TEXT,  -- 'bcl', 'heuristic', 'database', 'nuget_api'
    confidence REAL,
    error_message TEXT,
    detected_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (snippet_id) REFERENCES snippets(snippet_id) ON DELETE CASCADE,
    FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_dep_resolution_snippet ON dependency_resolutions(snippet_id);
CREATE INDEX IF NOT EXISTS idx_dep_resolution_run ON dependency_resolutions(run_id);
CREATE INDEX IF NOT EXISTS idx_dep_resolution_status ON dependency_resolutions(resolution_status);

-- View for dependency resolution summary by family
CREATE VIEW IF NOT EXISTS v_dependency_resolution_summary AS
SELECT
    p.family,
    dr.resolution_status,
    dr.resolution_source,
    COUNT(DISTINCT dr.snippet_id) as snippet_count,
    COUNT(DISTINCT dr.namespace) as namespace_count,
    AVG(dr.confidence) as avg_confidence
FROM dependency_resolutions dr
JOIN snippets s ON dr.snippet_id = s.snippet_id
JOIN pages p ON s.page_id = p.page_id
GROUP BY p.family, dr.resolution_status, dr.resolution_source
ORDER BY p.family, dr.resolution_status;

-- Schema version update
INSERT OR IGNORE INTO schema_version (version, description, applied_at)
VALUES (6, 'Automatic NuGet dependency resolution system', datetime('now'));
