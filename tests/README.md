# Tests for Example Reviewer Pipeline

## Overview

This directory contains tests for the Example Reviewer Pipeline hardening features.

## Running Tests

```bash
# Install test dependencies
pip install -r requirements-dev.txt

# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_path_guard.py -v
pytest tests/test_database_schema.py -v

# Run with coverage
pytest --cov=src tests/
```

## Test Modules

### `test_path_guard.py`

Tests for the path guard module that enforces read-only constraints on test-* directories.

**Coverage:**
- `is_read_only_path()`: Detection of protected paths
- `assert_write_allowed()`: Write blocking enforcement
- `get_workspace_path()`: Workspace path mapping
- `normalize_path()`: Path normalization
- Integration workflows

**Key Tests:**
- tests/fixtures/content/, test-data/, test-examples/, tests/fixtures/reference/ are all protected
- ✅ Absolute and relative paths handled correctly
- ✅ Windows and Unix path separators normalized
- ✅ Workspace paths generated correctly
- ✅ Non-protected paths allowed

### `test_database_schema.py`

Tests for database schema creation and migration system.

**Coverage:**
- Schema initialization
- Migration application
- Run scoping structure
- Table existence and structure

**Key Tests:**
- ✅ All required tables created
- ✅ example_run_state has composite primary key (run_id, example_id)
- ✅ run_id columns added to compile_attempts, runtime_attempts, markdown_edits
- ✅ Migrations apply once and are idempotent

## Test Fixtures

### `temp_db`

Creates a temporary database for testing that is automatically cleaned up.

```python
def test_something(temp_db):
    db = Database(temp_db)
    db.initialize_schema()
    # ... test code
    # Database is automatically deleted after test
```

### `temp_workspace`

Creates a temporary workspace directory for testing.

```python
def test_workspace(temp_workspace):
    workspace_path = temp_workspace / "file.txt"
    # ... test code
    # Directory is automatically cleaned up after test
```

## Adding New Tests

When adding new tests:

1. **Follow naming convention**: `test_<module_name>.py`
2. **Use descriptive test names**: `test_<what_it_tests>`
3. **Group related tests**: Use test classes
4. **Add docstrings**: Explain what each test verifies
5. **Use fixtures**: Leverage `conftest.py` fixtures

Example:

```python
class TestMyFeature:
    """Tests for my new feature."""

    def test_basic_functionality(self, temp_db):
        """Test that basic functionality works as expected."""
        # Arrange
        ...
        # Act
        ...
        # Assert
        ...
```

## CI/CD Integration

Tests should be run in CI/CD pipelines before merging:

```bash
# Run tests with strict mode
pytest --strict-markers --tb=short

# Run with coverage requirements
pytest --cov=src --cov-report=term-missing --cov-fail-under=80
```

## Troubleshooting

### Import Errors

If you get import errors, ensure:
1. You're running from the project root
2. `src/` is in PYTHONPATH
3. Virtual environment is activated

### Test Failures

If tests fail:
1. Check that no database or workspace files are locked
2. Verify test fixtures are cleaning up properly
3. Run tests in verbose mode: `pytest -v`
4. Run a single test: `pytest tests/test_path_guard.py::TestIsReadOnlyPath::test_test_data_is_read_only -v`
