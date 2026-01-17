# CT-02 Implementation Plan

## Task Overview
Create pytest-based CLI smoke tests to catch import errors and basic execution failures before they reach users.

## Analysis

### Current CLI Structure
From `src/cli/main.py`:
- Main commands: scan, extract, compile-verify, compile-fix, runtime-verify, runtime-fix, md-update, final-review, commit, status, run, list-families, backfill
- Global options: --config-dir, --db-path, --workspace-dir, --verbose, --json
- Entry point: `python -m src.cli.main`

### Current conftest.py
Minimal fixtures exist. Need to add:
- Temporary workspace fixture
- Minimal config fixture
- CLI test helpers

## Implementation Approach

### 1. Create tests/test_cli_smoke.py
Structure:
```
- Test main --help
- Test each subcommand --help (12+ commands)
- Test basic execution with dry-run/minimal args
- Test no import errors in stderr
- All via subprocess for real CLI invocation
```

### 2. Update tests/conftest.py
Add fixtures:
- `temp_workspace`: Creates temp directory with minimal config structure
- `cli_env`: Environment variables for isolated testing
- Helper to create minimal family config

### 3. Test Categories

**Category A: Help Tests (fast, no side effects)**
- main --help
- Each subcommand --help

**Category B: Basic Execution Tests (with temp workspace)**
- run --family zip --dry-run --max-examples 1
- list-families
- status
- scan --family zip --max-files 1

**Category C: Import Error Detection**
- Check stderr for NameError, ImportError, ModuleNotFoundError
- Assert returncode != failure on help commands

## Risk Mitigation

1. **Timeout**: All subprocess calls have 30s timeout
2. **Isolation**: Use tempfile.TemporaryDirectory for no pollution
3. **Fast**: Only test --help and dry-run modes, no actual processing
4. **Safe**: No database modifications, no git operations

## Success Metrics

- 12+ tests created
- All tests pass
- Total execution time < 30 seconds
- No false positives (stable tests)
- No test pollution (clean temp dirs)

## Timeline

1. Create fixtures in conftest.py (30 min)
2. Write help tests (30 min)
3. Write basic execution tests (1 hour)
4. Test and debug (1 hour)
5. Documentation and evidence (30 min)

Total: ~3.5 hours
