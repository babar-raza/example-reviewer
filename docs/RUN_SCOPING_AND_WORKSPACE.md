# Run Scoping and Workspace Copy Mode

## Overview

This document describes the hardening implementations for run scoping and workspace copy mode in the Example Reviewer Pipeline. These features ensure:

- **Truthful reporting**: No mixing of results from different runs
- **Parallel runs**: Multiple runs can execute without interference
- **Read-only test paths**: Prevents accidental modification of test data
- **Deterministic behavior**: Reproducible results from clean state

## Run Scoping (Production-Grade Design)

### Architecture

The run scoping system uses a production-grade design that separates canonical example metadata from per-run state:

1. **`example_records`**: Canonical per-example metadata
   - Primary key: `example_id`
   - Contains: `family`, `file_path`, `original_code`, `created_at`, etc.
   - Stable across runs (no overwriting)

2. **`example_run_state`**: Per-run state for each example
   - Composite primary key: `(run_id, example_id)`
   - Contains: `status`, `failure_reason`, `compilable_code`, `verified_code`, `drift_score`, etc.
   - Isolated by run_id

3. **Run-scoped attempts**: `compile_attempts`, `runtime_attempts`, `markdown_edits`
   - All include `run_id` column
   - Foreign key to `run_records(run_id)` with `ON DELETE CASCADE`

### Schema Design

```sql
-- Canonical example metadata (stable across runs)
CREATE TABLE example_records (
    example_id TEXT PRIMARY KEY,
    family TEXT NOT NULL,
    file_path TEXT NOT NULL,
    original_code TEXT NOT NULL,
    -- ... other canonical fields
);

-- Per-run state (isolated by run_id)
CREATE TABLE example_run_state (
    run_id TEXT NOT NULL,
    example_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'discovered',
    failure_reason TEXT,
    compilable_code TEXT,
    verified_code TEXT,
    drift_score REAL DEFAULT 0.0,
    -- ... other per-run fields
    PRIMARY KEY (run_id, example_id),
    FOREIGN KEY (run_id) REFERENCES run_records(run_id) ON DELETE CASCADE,
    FOREIGN KEY (example_id) REFERENCES example_records(example_id) ON DELETE CASCADE
);

-- Run-scoped attempts
CREATE TABLE compile_attempts (
    attempt_id TEXT PRIMARY KEY,
    example_id TEXT NOT NULL,
    run_id TEXT,  -- Links to specific run
    -- ... other fields
    FOREIGN KEY (run_id) REFERENCES run_records(run_id) ON DELETE CASCADE
);
```

### Migration System

The database now includes a migration engine that:

1. **Tracks applied migrations** in `schema_migrations` table
2. **Applies migrations idempotently** from `migrations/` directory
3. **Runs automatically** on `Database.initialize_schema()`

Migrations are SQL files named `XXX_description.sql` (e.g., `008_run_scoping.sql`).

### Benefits

- ✅ No overwriting of `example_id` across runs
- ✅ Run-scoped queries are efficient (indexed by `run_id`)
- ✅ Clean separation of concerns (canonical vs. per-run state)
- ✅ Supports parallel runs without conflicts
- ✅ Accurate KPI calculations per run

## Workspace Copy Mode

### Overview

Workspace copy mode addresses the requirement that `test-content/` and other test paths are **strictly read-only**. When enabled, files in protected directories are copied to a workspace before modification.

### Protected Paths

The following paths are **strictly read-only** (enforced by `path_guard.py`):

- `test-data/`
- `test-examples/`
- `test-reference/`
- `test-content/` ⚠️ **NEW** - prevents manual edits to test content

### Usage

#### Enable workspace copy mode:

```bash
# Run with workspace copy mode
python -m src.cli.main run --family zip --use-workspace-copy

# Or use the short form
python -m src.cli.main run --family zip --workspace-copy
```

#### What happens:

1. **Detection**: Pipeline detects file is in `test-content/`
2. **Redirect**: Maps to `artifacts/workspace/<run_id>/content/...`
3. **Copy**: Copies original file to workspace (preserving structure)
4. **Modify**: All updates target the workspace copy
5. **Report**: Run artifacts record both original and workspace paths

### Path Guard

The `path_guard` module enforces read-only constraints:

```python
from src.core.path_guard import (
    is_read_only_path,      # Check if path is protected
    assert_write_allowed,   # Raise PermissionError if write blocked
    get_workspace_path,     # Get workspace copy path for protected file
)

# Example usage
if is_read_only_path(file_path):
    # Redirect to workspace
    workspace_path = get_workspace_path(
        file_path,
        workspace_root=Path("artifacts/workspace"),
        run_id=current_run_id
    )
    # Write to workspace_path instead
```

### Workspace Path Mapping

Protected paths are mapped to workspace as follows:

```
Original:  test-content/docs/example.md
Workspace: artifacts/workspace/<run_id>/content/docs/example.md

Original:  /home/user/repo/test-content/docs/example.md
Workspace: artifacts/workspace/<run_id>/content/docs/example.md
```

The mapping:
- **Extracts** the relative path after `test-content/`
- **Preserves** the directory structure
- **Isolates** by run_id
- **Handles** both relative and absolute paths

## Backfill Policy

### Overview

The backfill service respects read-only test paths by redirecting writes to `artifacts/backfill/`.

### Behavior

When backfilling test data or examples:

1. **Check target path**: Is it in `test-data/`, `test-examples/`, etc.?
2. **Redirect if read-only**: Write to `artifacts/backfill/<family>/test-data/...`
3. **Record mapping**: Store redirect in run artifacts
4. **Use in pipeline**: Pipeline components read from backfill path

### Example

```bash
# Backfill test data (respects read-only paths)
python -m src.cli.main backfill --family zip --targets test_data

# Output:
# Redirecting backfill from read-only path test-data/zip/...
# to artifacts: artifacts/backfill/zip/test-data/...
```

## Testing

### Running Tests

```bash
# Install test dependencies
pip install -r requirements-dev.txt

# Run all tests
pytest

# Run specific test module
pytest tests/test_path_guard.py -v
pytest tests/test_database_schema.py -v

# Run with coverage
pytest --cov=src tests/
```

### Test Coverage

- ✅ **Path Guard**: `tests/test_path_guard.py`
  - Read-only path detection
  - Write blocking
  - Workspace path mapping
  - Integration workflows

- ✅ **Database Schema**: `tests/test_database_schema.py`
  - Schema creation
  - Migration application
  - Run scoping structure
  - example_run_state composite key

## Phase-1 Local Workflow

### Fresh Database + Workspace Copy

To run Phase-1 (discovery + compilation) locally with proper hardening:

```bash
# 1. Clean database (fresh start)
rm data/example_reviewer.db

# 2. Run discovery and compilation with workspace copy
python -m src.cli.main run \
    --family zip \
    --use-workspace-copy \
    --max-examples 10 \
    --skip-runtime \
    --verbose

# 3. Check run artifacts
ls artifacts/workspace/  # Should contain run_id directories
```

### Verify Run Scoping

To verify runs are properly isolated:

```bash
# Run 1
python -m src.cli.main extract --family zip
python -m src.cli.main compile-verify --family zip

# Run 2 (on same database)
python -m src.cli.main extract --family zip
python -m src.cli.main compile-verify --family zip

# Query database to verify isolation
sqlite3 data/example_reviewer.db "SELECT run_id, COUNT(*) FROM example_run_state GROUP BY run_id;"
# Should show 2 distinct run_ids with separate counts
```

## Acceptance Checks

### ✅ Fresh DB Works

```bash
rm data/example_reviewer.db
python -m src.cli.main extract --family zip
# Should create schema, apply migrations, no SQL errors
```

### ✅ Two Sequential Runs Don't Mix

```bash
# Run 1
python -m src.cli.main run --family zip --max-examples 5

# Run 2
python -m src.cli.main run --family zip --max-examples 5

# Verify separate run_ids
sqlite3 data/example_reviewer.db "SELECT DISTINCT run_id FROM run_records;"
# Should show 2 different run_ids
```

### ✅ Workspace Copy Prevents test-content/ Writes

```bash
# Without workspace copy (should fail if trying to write)
python -m src.cli.main md-update --family zip --allow-md-write
# Should raise PermissionError if target is test-content/

# With workspace copy (should succeed)
python -m src.cli.main md-update --family zip --allow-md-write --use-workspace-copy
# Should write to artifacts/workspace/<run_id>/content/...
```

### ✅ Backfill Redirects Read-Only Paths

```bash
# Backfill test data (target is test-data/)
python -m src.cli.main backfill --family zip --targets test_data
# Should log: "Redirecting backfill from read-only path test-data/..."
# Files written to: artifacts/backfill/zip/test-data/...
```

## Implementation Status

### ✅ Completed

- [x] Production-grade run scoping schema (`example_run_state` table)
- [x] Migration engine with `schema_migrations` tracking
- [x] Migration 008: Run scoping tables and indexes
- [x] Workspace copy CLI flag (`--use-workspace-copy`)
- [x] Workspace copy plumbing (Orchestrator, Tools, CLI)
- [x] Path guard enforcement (all test-* paths protected)
- [x] Workspace path mapping (relative + absolute paths)
- [x] Backfill redirect for read-only paths
- [x] Tests for path guard, schema, migrations
- [x] Removed `__pycache__` from repository

### ⚠️ Deferred (Not Required for Phase-1)

- [ ] Full database method updates to use `example_run_state`
  - Current: Some methods still write to `example_records` fields that should be in `example_run_state`
  - Impact: Run scoping schema is in place, but queries need updates
  - When: Required before Phase-2 E2E execution

- [ ] Markdown service workspace copy integration
  - Current: Flag exists, path guard active
  - Impact: Need to wire workspace path through markdown update flow
  - When: Required for Phase-2 (md-update step)

## Migration Path

### For existing databases:

```bash
# Migrations apply automatically on next run
python -m src.cli.main extract --family zip

# Check migrations applied
sqlite3 data/example_reviewer.db "SELECT * FROM schema_migrations;"
# Should show: 008_run_scoping | Production-grade run scoping...
```

### For fresh development:

```bash
# Remove old DB
rm data/example_reviewer.db

# Run will create schema + apply migrations
python -m src.cli.main extract --family zip
```

## Troubleshooting

### "WRITE BLOCKED: Cannot write to read-only test path"

**Cause**: Attempting to write to `test-content/`, `test-data/`, etc. without workspace copy mode.

**Solution**: Add `--use-workspace-copy` flag:
```bash
python -m src.cli.main run --family zip --use-workspace-copy
```

### "Migration XXX failed"

**Cause**: Migration SQL has error or conflicts with existing schema.

**Solution**:
1. Check migration file in `migrations/`
2. Manually inspect database: `sqlite3 data/example_reviewer.db .schema`
3. If needed, remove migration record: `DELETE FROM schema_migrations WHERE migration_id = 'XXX';`
4. Fix migration SQL and re-run

### "No such column: run_id"

**Cause**: Migration 008 not applied yet.

**Solution**: Run `initialize_schema()` to apply migrations:
```bash
python -m src.cli.main extract --family zip
```

## References

- **Migration 008**: `migrations/008_run_scoping.sql`
- **Path Guard**: `src/core/path_guard.py`
- **Database Schema**: `src/core/database.py` (SCHEMA constant)
- **Tests**: `tests/test_path_guard.py`, `tests/test_database_schema.py`
- **CLI**: `src/cli/main.py` (--use-workspace-copy flag)
