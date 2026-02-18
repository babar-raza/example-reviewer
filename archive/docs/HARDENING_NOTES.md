# Hardening + Correctness Gates Implementation

**Date:** 2026-01-21
**Status:** Completed (Tasks A, C, D, E, F)
**Context:** Track 2 - Prevent cheating, ensure truthful results, enable workspace isolation

## Executive Summary

This document describes the safety guardrails and correctness improvements implemented in the Example Reviewer pipeline. These changes prevent accidental data corruption, enable run isolation, and ensure truthful reporting of validation results.

## Problem Statement

Prior to this hardening work, the pipeline had several vulnerabilities:

1. **Test content could be manually edited** - No protection on `test-content/` directory
2. **Cross-run data leakage** - Database queries mixed results from different runs
3. **SQL correctness bugs** - `get_runtime_kpis()` had parentheses issues causing incorrect counts
4. **Lack of workspace isolation** - No safe way to work with copies of test content
5. **Stub code confusion** - Unused stubs like `src/validation/orchestrator.py`

## Implemented Solutions

### Task A: Centralized Path Guard ✅

**Objective:** Single source of truth for write protection

**Created:**
- `src/core/path_guard.py` (188 lines)
  - `normalize_path()` - Normalize paths to forward slashes
  - `is_read_only_path()` - Detect protected directories
  - `assert_write_allowed()` - Enforcement point (raises `PermissionError`)
  - `get_workspace_path()` - Map read-only paths to workspace

**Protected Paths:**
```python
READ_ONLY_PREFIXES = (
    'test-data/',
    'test-examples/',
    'test-reference/',
    'test-content/',  # NEWLY PROTECTED
)
```

**Integrated Into:**
- `src/services/markdown_service.py` - Markdown update protection
- `src/services/backfill_service.py` - Backfill operation protection
- `src/_legacy/patching_service.py` - Patch operation protection

**Testing:**
- `tests/test_path_guard.py` (331 lines) - Comprehensive unit tests

**Impact:**
- Any write to `test-*` directories now raises clear `PermissionError`
- Error messages suggest using `--use-workspace-copy` flag
- All write operations are audited via debug logging

### Task C: Run Scoping to Database ✅

**Objective:** Add `run_id` to core tables for per-run isolation

**Created:**
- `migrations/008_run_scoping.sql` - Database schema migration

**Schema Changes:**
```sql
ALTER TABLE example_records ADD COLUMN run_id TEXT REFERENCES run_records(run_id) ON DELETE CASCADE;
ALTER TABLE compile_attempts ADD COLUMN run_id TEXT REFERENCES run_records(run_id) ON DELETE CASCADE;
ALTER TABLE runtime_attempts ADD COLUMN run_id TEXT REFERENCES run_records(run_id) ON DELETE CASCADE;
ALTER TABLE markdown_edits ADD COLUMN run_id TEXT REFERENCES run_records(run_id) ON DELETE CASCADE;
```

**Indexes Created:**
- `idx_example_run_family` - Fast queries by run and family
- `idx_example_run_status` - Fast queries by run and status
- `idx_compile_run`, `idx_runtime_run`, `idx_markdown_run` - Per-run lookups
- Composite indexes for common query patterns

**Database Methods Updated:**
1. **Save Methods** (added `run_id: Optional[str] = None` parameter):
   - `save_example()` - Line 415
   - `save_compile_attempt()` - Line 723
   - `save_runtime_attempt()` - Line 792
   - `save_markdown_edit()` - Line 939

2. **Query Methods** (added `run_id` filtering):
   - `get_examples_by_family()` - Line 488
   - `get_compile_attempts()` - Line 777
   - `get_runtime_attempts()` - Line 867

**Backward Compatibility:**
- All `run_id` parameters are `Optional[str] = None`
- Queries without `run_id` return all records (old behavior)
- Queries with `run_id` return only matching records (new behavior)
- Existing records with NULL `run_id` remain accessible

**Impact:**
- Each run is fully isolated in the database
- KPIs and metrics are truthful per-run
- No cross-run data leakage
- Enables parallel runs without interference

### Task D: Fix get_runtime_kpis() SQL Bug ✅

**Objective:** Fix SQL parentheses bug and add proper run_id filtering

**File:** `src/core/database.py` - Line 1501

**Bugs Fixed:**

1. **Missing parentheses around OR condition** (Line 1456):
   ```sql
   -- BEFORE (incorrect precedence):
   WHERE fd.phase = 'Phase C (Pre-Runtime)' OR fd.phase LIKE 'Phase C%' AND fd.run_id = ?

   -- AFTER (correct precedence):
   WHERE (fd.phase = 'Phase C (Pre-Runtime)' OR fd.phase LIKE 'Phase C%') AND fd.run_id = ?
   ```

2. **WHERE clause construction**:
   ```python
   # BEFORE - string concatenation with incorrect placement
   where_clause = " AND ".join(where_conditions)

   # AFTER - proper WHERE clause wrapping
   where_clause = ""
   if where_conditions:
       where_clause = " AND (" + " AND ".join(where_conditions) + ")"
   ```

3. **Verified count query parameterization**:
   ```python
   # BEFORE - missing parameter list construction
   verified_params = []

   # AFTER - proper parameter building
   verified_where_conditions = []
   verified_params = []
   if run_id:
       verified_where_conditions.append("er.run_id = ?")
       verified_params.append(run_id)
   if family:
       verified_where_conditions.append("er.family = ?")
       verified_params.append(family)
   ```

**Impact:**
- Runtime KPIs now return correct counts
- No SQL syntax errors
- Proper run_id filtering in all subqueries

### Task E: Remove Stubs and Rename Legacy ✅

**Objective:** Clean up unused code and signal deprecated modules

**Actions Taken:**

1. **Deleted stub file:**
   - `src/validation/orchestrator.py` (8-line unused stub)
   - Verified no imports before deletion

2. **Renamed legacy directory:**
   - `src/legacy_root/` → `src/_legacy/`
   - Underscore prefix signals deprecated/internal code

3. **Updated imports:**
   - `src/_legacy/persistent_fix_service.py` - Line 8
   - `archive/analysis-scripts/verify_multi_family.py` - Line 7

**Impact:**
- Codebase is cleaner
- No confusion from unused stubs
- Legacy code clearly marked as deprecated

### Task F: Repository Hygiene ✅

**Objective:** Improve repo organization and dependency management

**F.1: Updated `.gitignore`:**
- Added `*.pyo` to Python bytecode patterns
- Updated workspace ignore: `workspace/` (instead of `/workspace/runtime/`)
- Clearer comments about workspace copy mode

**F.2: Created `requirements.txt`:**
- Pinned all dependencies to exact versions (using `==`)
- Comprehensive list of production dependencies
- Clear categorization with comments

**Key Dependencies:**
```txt
pydantic==2.10.3
anthropic==0.40.0
openai==1.58.1
sqlalchemy==2.0.36
chromadb==0.5.23
sentence-transformers==3.3.1
gitpython==3.1.43
pytest==8.3.4
pytest-cov==6.0.0
```

**F.3: Created `requirements-dev.txt`:**
- References `requirements.txt` via `-r requirements.txt`
- Adds development tools:
  - `black==24.10.0` - Code formatting
  - `flake8==7.1.1` - Linting
  - `mypy==1.13.0` - Type checking
  - `pytest-xdist==3.6.1` - Parallel testing

**F.4: Updated `README.md`:**
- Added comprehensive "Safety Features" section
- Documented all 4 safety mechanisms
- Included usage examples with code blocks
- Positioned after Installation, before Usage

**Impact:**
- Reproducible builds with pinned dependencies
- Clear documentation of safety features
- Development tools standardized
- `.gitignore` prevents bytecode commits

## Architecture Decisions

### 1. Optional run_id Parameters

**Decision:** Make `run_id` optional (`Optional[str] = None`) in all database methods

**Rationale:**
- Backward compatibility with existing code
- Gradual rollout possible
- NULL `run_id` allowed for existing records
- Queries without `run_id` still work (return all records)

**Trade-offs:**
- Can't enforce run_id at database level (nullable column)
- Requires discipline to pass run_id in new code

### 2. Centralized Path Guard Module

**Decision:** Single `path_guard.py` module instead of per-service checks

**Rationale:**
- DRY (Don't Repeat Yourself) principle
- Single source of truth for read-only paths
- Easier to test and maintain
- Consistent error messages

**Trade-offs:**
- Extra import required in each service
- Slightly more abstraction

### 3. Workspace Copy Mode (Not Yet Implemented)

**Future Work:** Task B deferred - workspace copy mode CLI integration

**Planned Design:**
- `--use-workspace-copy` flag copies test-content/ to workspace/
- `get_workspace_path()` already implemented in path_guard
- File mapping updates example records
- Per-run diffs in `artifacts/diffs/<run_id>/`

## Testing Strategy

### Unit Tests Created

1. **`tests/test_path_guard.py`** (331 lines)
   - Path normalization (forward/backward slashes)
   - Read-only detection (all 4 prefixes)
   - Write blocking with PermissionError
   - Workspace path generation
   - Integration workflows

### Test Coverage Verified

- All `READ_ONLY_PREFIXES` tested
- Both relative and absolute paths
- Windows and Unix path styles
- Error message content verification

### Manual Testing

```bash
# Test path guard enforcement
python -c "from src.core.path_guard import assert_write_allowed; \
           assert_write_allowed('test-content/x.md')"
# Expected: PermissionError

# Test database migration applied
sqlite3 data/example_reviewer.db \
  "SELECT name FROM pragma_table_info('example_records') WHERE name='run_id'"
# Expected: run_id

# Test no changes to protected paths
git status test-content/
# Expected: nothing to commit
```

## Success Metrics

### Completed Checklist

✅ Writing to `test-content/` raises `PermissionError`
✅ Writing to `test-data/` raises `PermissionError`
✅ Writing to workspace/ succeeds
✅ Database has `run_id` columns in 4 tables
✅ `get_runtime_kpis()` returns correct counts
✅ No SQL syntax errors
✅ Queries without `run_id` work (backward compatible)
✅ No `__pycache__/` in git
✅ `requirements.txt` has pinned versions
✅ Legacy directory renamed to `_legacy/`
✅ README.md documents safety features

### Verification Commands

```bash
# Verify path guard works
python -c "from src.core.path_guard import assert_write_allowed; \
           assert_write_allowed('test-content/x.md', 'test')"

# Verify database schema
sqlite3 data/example_reviewer.db \
  "SELECT sql FROM sqlite_master WHERE name='example_records'" | grep run_id

# Verify no legacy_root references
grep -r "legacy_root" . --include="*.py" --exclude-dir=".git"

# Run unit tests
pytest tests/test_path_guard.py -v

# Verify .gitignore patterns
git check-ignore -v workspace/test.txt artifacts/workspace/test.txt
```

## Known Limitations

### Not Yet Implemented

1. **Task B: Workspace Copy Mode** - CLI integration deferred
   - `--use-workspace-copy` flag not yet wired up
   - `copy_to_workspace()` not yet in DiscoveryService
   - Orchestrator doesn't call workspace copy logic

2. **Task G: Polish** - Optional improvements deferred
   - `datetime.utcnow()` still used (not deprecated yet in Python 3.10)
   - UTF-8 encoding checks not performed

### Backward Compatibility Concerns

- **NULL run_id allowed:** Existing records have NULL `run_id`, which is valid
- **Queries without run_id:** Return all records (old + new)
- **Migration 008:** Additive only (no destructive changes)

## Rollback Procedure

### If Issues Found

```bash
# Restore database from backup
cp data/example_reviewer.db.backup data/example_reviewer.db

# Revert code changes
git checkout HEAD~1 src/core/path_guard.py
git checkout HEAD~1 src/core/database.py
git checkout HEAD~1 migrations/008_run_scoping.sql

# Re-run tests
pytest -v
```

### Database Migration Rollback

```sql
-- If migration 008 needs to be reverted:
ALTER TABLE example_records DROP COLUMN run_id;
ALTER TABLE compile_attempts DROP COLUMN run_id;
ALTER TABLE runtime_attempts DROP COLUMN run_id;
ALTER TABLE markdown_edits DROP COLUMN run_id;

DROP INDEX IF EXISTS idx_example_run_family;
DROP INDEX IF EXISTS idx_example_run_status;
DROP INDEX IF EXISTS idx_compile_run;
DROP INDEX IF EXISTS idx_runtime_run;
DROP INDEX IF EXISTS idx_markdown_run;
```

## Future Enhancements

### Short Term (Task B)

1. **Workspace Copy Mode Implementation:**
   - Add `--use-workspace-copy` CLI flag
   - Implement `DiscoveryService.copy_to_workspace()`
   - Update orchestrator to call copy logic
   - Update file paths in example records
   - Per-run diff directories

### Medium Term (Task G)

1. **Polish and Modernization:**
   - Replace `datetime.utcnow()` with `datetime.now(timezone.utc)`
   - Audit all `open()` calls for `encoding='utf-8'`
   - Add type hints to path_guard module

### Long Term

1. **Enhanced Run Management:**
   - CLI command to list all runs
   - CLI command to delete old runs (with CASCADE)
   - Run metadata (start time, duration, status)

2. **Workspace Management:**
   - Automatic workspace cleanup
   - Disk usage monitoring
   - Workspace archive/restore

## References

### Files Created

- `src/core/path_guard.py`
- `migrations/008_run_scoping.sql`
- `tests/test_path_guard.py`
- `requirements.txt`
- `requirements-dev.txt`
- `docs/HARDENING_NOTES.md` (this file)

### Files Modified

- `src/services/markdown_service.py`
- `src/services/backfill_service.py`
- `src/_legacy/patching_service.py` (formerly `src/legacy_root/patching_service.py`)
- `src/_legacy/persistent_fix_service.py`
- `archive/analysis-scripts/verify_multi_family.py`
- `src/core/database.py`
- `.gitignore`
- `README.md`

### Files Deleted

- `src/validation/orchestrator.py` (8-line stub)

### Directories Renamed

- `src/legacy_root/` → `src/_legacy/`

## Approval and Sign-off

**Implementation Date:** 2026-01-21
**Implementation Status:** Tasks A, C, D, E, F completed
**Deferred Tasks:** B (Workspace Copy Mode), G (Polish)
**Tests Passing:** ✅ All unit tests pass
**Documentation:** ✅ README.md updated, this document created

## Contact

For questions or issues related to these hardening changes:
- Check implementation details in this document
- Review unit tests in `tests/test_path_guard.py`
- Consult `src/core/path_guard.py` docstrings
- See `README.md` "Safety Features" section for user-facing docs
