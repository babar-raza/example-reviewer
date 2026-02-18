# tests/ - Unit Tests

639 unit tests covering all pipeline components.

## Running Tests

```bash
# Run all tests
pytest tests/ -v --timeout=120

# Run specific test file
pytest tests/test_path_guard.py -v

# Run with coverage
pytest tests/ --cov=src --cov-report=term-missing
```

## Test Fixtures

- `fixtures/content/` - Sample markdown content (read-only, enforced by path_guard)
- `fixtures/reference/` - API reference docs (read-only)
- `conftest.py` - Shared pytest fixtures (`temp_db`, `temp_workspace`)

## Key Test Files

| Test File | What It Covers |
|-----------|---------------|
| `test_path_guard.py` | Write protection on test directories |
| `test_database_schema.py` | Schema creation and migrations |
| `test_config_loading.py` | Configuration loading and validation |
| `test_learned_patterns_service.py` | Auto-learned pattern application |
| `test_fixture_resolver_service.py` | Test data resolution (44 tests) |
| `test_semantic_signature_service.py` | Drift prevention signatures |
| `test_auto_learn_executable_patterns.py` | LLM pattern extraction |
| `test_workspace_copy.py` | Workspace copy mode |

## Naming Convention

- File: `test_<module_name>.py`
- Class: `Test<Feature>`
- Method: `test_<what_it_tests>`
