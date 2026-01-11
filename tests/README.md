# Example Reviewer Test Suite

Comprehensive test suite for the Example Reviewer system, with focus on GitHub Gist integration.

## Quick Start

```bash
# Run all tests (excluding integration tests)
python run_tests.py

# Run with verbose output
python run_tests.py -v

# Run specific test file
python run_tests.py tests/test_gist_parsing.py

# Run integration tests (requires GitHub API access)
python run_tests.py --integration
```

## Test Organization

### Test Files

| File | Purpose | API Access |
|------|---------|------------|
| `test_gist_parsing.py` | Gist shortcode parsing regression tests | No |
| `test_gist_cache.py` | Cache structure and validation tests | No (mocked) |
| `test_gist_database.py` | Database persistence tests | No (mocked) |
| `test_gist_integration.py` | Real GitHub API integration tests | **Yes** |
| `test_cli_paths.py` | CLI path resolution tests | No |

### Test Categories

1. **Unit Tests** (test_gist_parsing.py, test_cli_paths.py)
   - Fast, isolated tests
   - No external dependencies
   - Run by default

2. **Integration Tests** (test_gist_cache.py, test_gist_database.py)
   - Test component interactions
   - Use mocked API responses
   - Run by default

3. **API Integration Tests** (test_gist_integration.py)
   - Test real GitHub API
   - Require network access
   - **SKIPPED BY DEFAULT** - must opt-in with `--integration`

## Running Tests

### Default Behavior (Recommended)

```bash
# Run all tests except API integration
python run_tests.py
```

This runs:
- ✅ Parsing tests (13 tests)
- ✅ Cache tests (~10 tests)
- ✅ Database tests (~12 tests)
- ⏭️ Integration tests (SKIPPED)

### With Integration Tests

```bash
# Run ALL tests including real API calls
python run_tests.py --integration
```

**Requirements for integration tests:**
- Network connectivity
- GitHub API access
- Rate limits apply (60/hr without token, 5000/hr with GITHUB_TOKEN)

**Note**: Integration tests use a real Aspose gist and will make actual GitHub API requests.

### Specific Test Selection

```bash
# Run only parsing tests
python run_tests.py tests/test_gist_parsing.py

# Run only integration tests
python run_tests.py tests/test_gist_integration.py --integration

# Run specific test class
python run_tests.py tests/test_gist_parsing.py::TestGistShortcodeParsing

# Run specific test method
python run_tests.py tests/test_gist_parsing.py::TestGistShortcodeParsing::test_mixed_format_with_filename

# Run tests matching keyword
python run_tests.py -k "cache"

# Run tests with marker
python run_tests.py -m integration --integration
```

## Test Fixtures

### Shared Fixtures (`tests/fixtures/gist_fixtures.py`)

Centralized test data for consistent testing across all test files:

```python
from fixtures.gist_fixtures import (
    REAL_GIST_OWNER,      # "aspose-com-gists"
    REAL_GIST_ID,         # Real Aspose gist ID
    REAL_GIST_FILE,       # Specific C# filename
    MIXED_FORMAT_SHORTCODE,   # Hugo shortcode formats
    MALFORMED_SHORTCODES,     # Negative test cases
    # ... and more
)
```

### Pytest Fixtures

Standard pytest fixtures for temporary resources:

```python
def setup_method(self):
    """Create temporary database and cache for each test."""
    self.temp_dir = Path(tempfile.mkdtemp())
    self.temp_db = self.temp_dir / "test.db"
    self.cache_dir = self.temp_dir / "cache"

    self.db = Database(self.temp_db)
    self.service = GistService(cache_dir=self.cache_dir, db=self.db)
```

## Writing New Tests

### Adding Unit Tests

1. Create test file in `tests/` following naming: `test_<feature>.py`
2. Import required modules and fixtures
3. Create test classes grouping related tests
4. Use descriptive test names starting with `test_`

Example:

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from gist_service import GistService
from fixtures.gist_fixtures import MIXED_FORMAT_SHORTCODE

class TestNewFeature:
    """Test description."""

    def setup_method(self):
        """Setup runs before each test."""
        # Initialize resources

    def test_specific_behavior(self):
        """Test that X does Y when Z."""
        # Arrange
        # Act
        result = some_function()
        # Assert
        assert result == expected_value
```

### Adding Integration Tests

For tests requiring real GitHub API:

```python
import pytest

@pytest.mark.integration
class TestRealAPIFeature:
    """Integration test with real GitHub API."""

    def test_real_api_call(self):
        """Test description."""
        # Will be skipped unless --integration flag passed
        pass
```

### Test Best Practices

1. **Descriptive Names**: Test names should describe what is being tested
   - ✅ `test_mixed_format_with_filename`
   - ❌ `test_gist_1`

2. **Clear Assertions**: Use descriptive assertion messages
   ```python
   assert result is not None, "Mixed format shortcode should parse successfully"
   ```

3. **Arrange-Act-Assert**: Structure tests clearly
   ```python
   # Arrange
   shortcode = MIXED_FORMAT_SHORTCODE

   # Act
   result = service.parse_gist_shortcode(shortcode)

   # Assert
   assert result == expected_value
   ```

4. **Isolated Tests**: Each test should be independent
   - Use `setup_method()` for fresh resources
   - Don't rely on test execution order
   - Clean up temporary files

5. **Test Edge Cases**: Include boundary conditions
   ```python
   def test_empty_string_returns_none(self):
       result = service.parse_gist_shortcode("")
       assert result is None
   ```

## Regression Testing

### Purpose

Tests in this suite primarily serve as **regression prevention** for critical bugs discovered during development:

- **HARD-001 Bug**: Mixed-format shortcode parsing
  - Test: `test_mixed_format_with_filename`
  - Ensures `{{< gist owner id "file.cs" >}}` format always works

- **BLOCK-001 Bug**: CLI path resolution
  - Test: `test_cli_path_resolution_logic`
  - Ensures repository root is correctly identified

### Adding Regression Tests

When fixing a bug:

1. Create test that reproduces the bug (should fail initially)
2. Fix the bug
3. Verify test now passes
4. Add test to regression suite with comments explaining the bug

Example:

```python
def test_bug_123_mixed_quotes(self):
    """Regression test for bug #123: Mixed quotes not parsing.

    Bug: Shortcodes like {{< gist owner "id" file >}} would fail.
    Fix: Added pattern to handle mixed quoting.
    """
    shortcode = '{{< gist owner "id" file >}}'
    result = service.parse_gist_shortcode(shortcode)
    assert result is not None  # Should not fail
```

## Test Configuration

### pytest.ini

Main pytest configuration in repository root:

```ini
[pytest]
testpaths = tests
addopts = -v
```

### conftest.py

Pytest hooks for integration test handling:

- Adds `--integration` command line flag
- Skips integration tests by default
- Registers `@pytest.mark.integration` marker

## Continuous Integration

For CI/CD pipelines:

```bash
# Fast CI run (no API calls)
python run_tests.py

# Full validation (with API - use sparingly)
python run_tests.py --integration
```

**CI Recommendations:**
- Run default tests on every commit
- Run integration tests on pull requests only
- Set GITHUB_TOKEN in CI environment for higher rate limits

## Troubleshooting

### Import Errors

If you see `ModuleNotFoundError`:

```bash
# Use run_tests.py wrapper instead of pytest directly
python run_tests.py

# Or set PYTHONPATH manually
set PYTHONPATH=%CD%\src;%CD%\tests
pytest
```

### Integration Tests Not Running

Check:
1. Did you pass `--integration` flag?
2. Is network connectivity available?
3. Are you hitting GitHub rate limits? (Set GITHUB_TOKEN env var)

### Database Errors

Tests use temporary databases that are cleaned up automatically. If you see database errors:
- Check that `schema.sql` exists in repository root
- Verify SQLite is available
- Ensure write permissions in temp directory

## Test Metrics

Current test coverage (as of HARD-002):

| Category | Test Count | Status |
|----------|-----------|--------|
| Parsing Tests | 13 | ✅ All passing |
| Cache Tests | ~10 | ✅ All passing |
| Database Tests | ~12 | ✅ All passing |
| Integration Tests | ~10 | ✅ All passing (with --integration) |
| **Total** | **~45** | **✅ 100% pass rate** |

**Execution Speed:**
- Unit tests: ~0.2 seconds
- Cache/DB tests: ~0.5 seconds
- Integration tests: ~5-10 seconds (network dependent)

## Future Test Additions

Planned test areas (as development continues):

- [ ] CLI command tests
- [ ] Discovery phase tests
- [ ] Validation phase tests
- [ ] Patch generation tests
- [ ] Multi-family tests
- [ ] Error recovery tests
- [ ] Performance benchmarks

## Getting Help

- **Test failures**: Check test output for assertion details
- **Integration issues**: Verify GitHub API connectivity and rate limits
- **New test questions**: Reference existing tests as examples
- **CI/CD setup**: See `.github/workflows/` (when added)

---

**Last Updated**: 2026-01-11 (HARD-002)
**Maintained By**: Agent C (Test Specialist)
