# Implementation Plan: HARD-003 - Cache Validation & Recovery

**Agent**: Agent B (Implementation Specialist)
**Task ID**: HARD-003
**Priority**: P1 (HIGH)
**Run ID**: run_20260111_203336
**Started**: 2026-01-11 20:33:36 UTC

---

## Objective

Implement defensive cache validation to detect and recover from corrupted cache files in the GistService, ensuring the system never crashes from cache corruption.

---

## Current State Analysis

### Existing Cache Structure (from code review)
- **Cache Location**: `cache_dir/{gist_id}.json`
- **Cache Schema**:
  ```json
  {
    "gist_id": "string",
    "etag": "string|null",
    "cached_at": "ISO8601 timestamp",
    "data": {
      "id": "string",
      "description": "string",
      "updated_at": "ISO8601",
      "files": {...}
    }
  }
  ```
- **Raw File Cache**: `cache_dir/{gist_id}/{filename}.raw`

### Current Cache Handling (gist_service.py:138-159)
- Basic try-catch on cache read
- Silent failure on corrupted cache (proceeds with fresh fetch)
- No logging of corruption events
- No proactive validation

### Existing Tests (test_gist_cache.py)
- Line 287-322: `test_corrupted_cache_file_triggers_fresh_fetch()`
  - Tests recovery from corrupted JSON
  - Verifies silent fallback to API fetch
  - **Does NOT verify logging or removal**

---

## Implementation Plan

### Phase 1: Implement verify_cache() Method

**Location**: `src/gist_service.py` (add to GistService class)

**Method Signature**:
```python
def verify_cache(self) -> Dict[str, Any]:
    """
    Verify cache integrity and remove corrupted files.

    Checks all .json cache files for:
    - Valid JSON structure
    - Required fields: gist_id, etag, cached_at, data
    - Valid cached_at timestamp format

    Returns:
        Dict with keys:
        - total_files: int (total cache files scanned)
        - valid_files: int (valid cache files)
        - corrupted_files: int (corrupted files removed)
        - removed_files: List[str] (paths of removed files)
        - errors: List[Dict] (file paths and error messages)
    """
```

**Validation Checks**:
1. JSON parsing (catch JSONDecodeError)
2. Required field presence: `gist_id`, `etag`, `cached_at`, `data`
3. `cached_at` is valid ISO8601 timestamp
4. `data` is dict and contains `files` key
5. Handle filesystem errors gracefully

**Logging Requirements**:
- WARNING level for each corrupted file detected
- Include full file path in log message
- Log removal action
- Example: `WARNING: Corrupted cache file detected: c:\...\cache\abc123.json - Invalid JSON, removing`

**Error Handling**:
- Catch filesystem permission errors
- Continue validation even if one file fails
- Report all errors in return dict

---

### Phase 2: Integrate with CLI

**Location**: `src/cli.py` (modify discover() method)

**Integration Point**: Line 57-110 (discover method)

**Approach**:
- Call `verify_cache()` BEFORE running discovery
- Log summary of verification
- Do NOT fail discovery if verification finds issues

**Optional Flag**: Add `--verify-cache` flag to discover command
- Default: True (always verify)
- Allow `--no-verify-cache` to skip (for performance)

---

### Phase 3: Create Comprehensive Tests

**New File**: `tests/test_cache_validation.py`

**Test Cases**:

1. **test_verify_cache_all_valid**
   - Setup: 3 valid cache files
   - Expected: All files reported as valid, none removed

2. **test_verify_cache_corrupted_json**
   - Setup: 1 valid, 2 corrupted (invalid JSON)
   - Expected: 2 files removed, logged at WARNING level

3. **test_verify_cache_missing_required_fields**
   - Setup: Cache files missing `gist_id`, `etag`, `cached_at`, `data`
   - Expected: Files removed, specific error messages

4. **test_verify_cache_invalid_timestamp**
   - Setup: Cache with invalid `cached_at` format
   - Expected: File removed, logged

5. **test_verify_cache_empty_directory**
   - Setup: Empty cache directory
   - Expected: Returns 0 total files, no errors

6. **test_verify_cache_filesystem_error**
   - Setup: Mock permission error on file removal
   - Expected: Error captured in return dict, continues processing

7. **test_verify_cache_logging**
   - Setup: Mix of valid and corrupted files
   - Expected: Verify WARNING logs contain file paths

8. **test_cli_integration_verify_cache**
   - Test: Full CLI discover command calls verify_cache
   - Expected: Verification runs before discovery starts

---

### Phase 4: Documentation

**New File**: `docs/operations.md`

**Sections**:
1. **Cache Overview**
   - Cache location and structure
   - Purpose of caching (rate limit reduction, performance)

2. **Cache Maintenance**
   - Automatic validation on `discover` command
   - Manual verification command (if implemented)
   - When to clear cache manually

3. **Troubleshooting**
   - Identifying cache corruption
   - Reading log messages
   - Manual cleanup procedures

4. **Cache Corruption Scenarios**
   - Power loss during write
   - Disk full
   - Concurrent access (future concern)

**Manual Cleanup Commands**:
```bash
# Remove all cache
rm -rf data/gist_cache/*

# Remove specific gist cache
rm -f data/gist_cache/{gist_id}.json
rm -rf data/gist_cache/{gist_id}/
```

---

## Implementation Order

1. Implement `verify_cache()` in `gist_service.py`
2. Create `test_cache_validation.py` with all test cases
3. Run tests, verify 100% pass
4. Integrate with CLI `discover()` method
5. Test CLI integration
6. Create `docs/operations.md`
7. Run full test suite to ensure no regressions
8. Generate evidence and self-review

---

## Success Criteria

- [ ] `verify_cache()` method implemented and tested
- [ ] All 8 unit tests passing
- [ ] CLI integration complete
- [ ] Operations documentation created
- [ ] No regressions in existing tests
- [ ] All logging at WARNING level includes file paths
- [ ] Self-review scores ≥4/5 on all 12 dimensions

---

## Risk Mitigation

### Risk 1: Breaking existing cache behavior
- **Mitigation**: Run existing `test_gist_cache.py` after each change
- **Rollback**: Keep original code in comments

### Risk 2: Performance impact on large cache directories
- **Mitigation**: Verify performance with 100 cache files (target <1s)
- **Test**: Create performance benchmark test

### Risk 3: Filesystem permission errors on Windows
- **Mitigation**: Test on Windows platform (current env)
- **Handle**: Graceful error handling, continue processing

---

## Notes

- Current working directory: `c:\Users\prora\OneDrive\Documents\GitHub\example-reviewer`
- Platform: Windows (win32)
- Python environment: Available (pytest confirmed)
- Database: SQLite at `data/examples.db`
- Cache directory: Configured per GistService instance (typically `data/gist_cache/`)

---

**Status**: READY TO IMPLEMENT
