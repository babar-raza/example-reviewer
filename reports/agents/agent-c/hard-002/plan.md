# Agent C Plan: HARD-002 Integration Test Suite

**Task**: Add comprehensive integration tests for gist functionality
**Priority**: P0 (BLOCKING for production readiness)
**Estimated Time**: 30-45 minutes

---

## Context

HARD-001 discovered two critical bugs:
1. CLI path resolution (BLOCK-001)
2. Mixed-format gist shortcode parsing

HARD-002 adds regression tests to prevent these bugs from recurring, plus validates all gist integration edge cases.

---

## Test Coverage Requirements

### 1. Gist Shortcode Parsing (Regression Tests)

**Test Cases**:
- ✅ All-quoted format: `{{< gist "owner" "id" "file.cs" >}}`
- ✅ Mixed format: `{{< gist owner id "file.cs" >}}` (HARD-001 bug)
- ✅ No filename (both formats)
- ✅ No spaces after `{{<`
- ❌ Malformed shortcodes (should return None)

**File**: `tests/test_gist_parsing.py`

### 2. Gist Fetching Integration

**Test Cases**:
- ✅ Fetch real public gist (requires GITHUB_TOKEN or public rate limit)
- ✅ Cache hit behavior (fetch once, verify cached)
- ✅ Cache miss behavior (verify API call)
- ❌ 404 gist (error handling)
- ❌ Rate limit handling (graceful degradation)
- ❌ Network timeout (configurable timeout)

**File**: `tests/test_gist_integration.py`
**Marker**: `@pytest.mark.integration` (opt-in with `--integration` flag)

### 3. Cache Structure Validation

**Test Cases**:
- ✅ JSON metadata file structure
- ✅ Raw file directory structure
- ✅ ETag storage and validation
- ✅ Cache directory creation
- ❌ Corrupted cache handling (HARD-003 focus, but basic test here)

**File**: `tests/test_gist_cache.py`

### 4. Database Integration

**Test Cases**:
- ✅ Gist metadata stored correctly
- ✅ Gist files recorded
- ✅ Snippet versions created
- ✅ Status tracking (success/failed/skipped)
- ✅ Multiple gists in single page

**File**: `tests/test_gist_database.py`

---

## Implementation Steps

### Step 1: Create Test Fixtures

**File**: `tests/fixtures/gist_fixtures.py`

```python
# Sample gist shortcodes for testing
MIXED_FORMAT_SHORTCODE = '{{< gist aspose-com-gists 78c04f45434d446c01e3543fdd084192 "Example.cs" >}}'
QUOTED_FORMAT_SHORTCODE = '{{< gist "aspose-com-gists" "78c04f45434d446c01e3543fdd084192" "Example.cs" >}}'
NO_FILENAME_SHORTCODE = '{{< gist aspose-com-gists 78c04f45434d446c01e3543fdd084192 >}}'

# Mock gist response (for unit tests)
MOCK_GIST_RESPONSE = {
    "id": "test123",
    "description": "Test Gist",
    "files": {
        "Example.cs": {
            "filename": "Example.cs",
            "language": "C#",
            "content": "// Test code"
        }
    }
}
```

### Step 2: Add Gist Parsing Tests

**File**: `tests/test_gist_parsing.py`

Tests GistService.parse_gist_shortcode() with all formats discovered in HARD-001.

**Acceptance**:
- All format variations parse correctly
- Malformed shortcodes return None
- No false positives
- 100% coverage of parse_gist_shortcode method

### Step 3: Add Integration Tests

**File**: `tests/test_gist_integration.py`

**CRITICAL**: These tests should be OPT-IN via pytest marker:

```python
@pytest.mark.integration
def test_fetch_real_gist():
    """Fetch a real gist from GitHub API."""
    # Uses the gist from HARD-001 for consistency
    ...
```

**Run with**: `pytest tests/test_gist_integration.py --integration`

**Skip without marker**: Tests skip gracefully with message about `--integration` flag

**Acceptance**:
- Real GitHub API call succeeds
- Cache directory created
- Database populated correctly
- Tests skip without `--integration` flag
- Clear documentation on when to run

### Step 4: Add Cache Tests

**File**: `tests/test_gist_cache.py`

Uses temp directories to validate cache structure without polluting real cache.

**Acceptance**:
- JSON structure validated
- Raw files written correctly
- ETag stored and retrieved
- Temp cleanup after tests

### Step 5: Add Database Tests

**File**: `tests/test_gist_database.py`

Uses in-memory SQLite database for fast, isolated testing.

**Acceptance**:
- All tables populated correctly
- Relationships maintained
- Status tracking works
- No side effects on real database

### Step 6: Update pytest Configuration

**File**: `pytest.ini` or `pyproject.toml`

```ini
[pytest]
markers =
    integration: marks tests as integration tests (deselect with '-m "not integration"')
    slow: marks tests as slow (deselect with '-m "not slow"')

# Default: skip integration tests
addopts = -m "not integration"
```

### Step 7: Update Documentation

**File**: `tests/README.md`

Document:
- How to run unit tests: `pytest`
- How to run integration tests: `pytest --integration`
- GitHub token setup (optional, uses public rate limit if not set)
- Test organization
- Writing new tests

### Step 8: Write Evidence

**File**: `reports/agents/agent-c/hard-002/evidence.md`

Include:
- Test coverage metrics
- Integration test execution output
- Regression validation (bugs from HARD-001 prevented)
- Documentation completeness
- Self-review scores

---

## Test Data Strategy

### Unit Tests (Mocked)
- Use fixtures for shortcode strings
- Mock GitHub API responses
- In-memory database
- Temp cache directories

### Integration Tests (Real API)
- Use known public gist from HARD-001
- Gist ID: `78c04f45434d446c01e3543fdd084192`
- Owner: `aspose-com-gists`
- File: `GenerateAndDisplayBarcode_ASP.NET_MVC_Barcode.cs`

**Rationale**: This gist is stable, public, and already validated in HARD-001.

---

## Success Metrics

### Coverage
- `test_gist_parsing.py`: 100% coverage of parse_gist_shortcode
- `test_gist_integration.py`: 90%+ coverage of fetch_gist (some error paths hard to test)
- `test_gist_cache.py`: 95%+ coverage of cache logic
- `test_gist_database.py`: 90%+ coverage of database operations

### Test Count
- Minimum 15 test cases
- Mix of positive and negative tests
- All HARD-001 bugs prevented by tests

### Documentation
- Clear README with examples
- pytest markers documented
- Integration test opt-in explained

---

## Acceptance Criteria

From HARD-002 requirements:

- [ ] Integration tests cover 5+ real API scenarios
- [ ] Tests pass with real GitHub API (when `--integration` flag used)
- [ ] Tests skip gracefully without flag
- [ ] Cache hit/miss behavior validated
- [ ] Error scenarios tested (404, timeout, rate limit)
- [ ] Documentation explains opt-in testing
- [ ] Regression tests for HARD-001 bugs
- [ ] pytest markers configured
- [ ] Evidence file complete

---

## Risks & Mitigations

**Risk**: GitHub rate limit during testing
**Mitigation**: Use cached gist from HARD-001, tests should pass without network

**Risk**: Tests too slow
**Mitigation**: Unit tests fast (mocked), integration tests opt-in only

**Risk**: Flaky network tests
**Mitigation**: Add retries with exponential backoff, skip on repeated failures

---

## Dependencies

- pytest >= 7.4.0
- pytest-asyncio (if async tests needed)
- HARD-001 complete (provides baseline gist for testing)
- Real database schema (tests against actual schema)

---

**Execute immediately after HARD-001**
