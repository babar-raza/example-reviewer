# CT-02 Implementation Plan: Execution Smoke Tests

## Overview
Create comprehensive smoke tests for all CLI commands to validate basic execution and catch import errors before they reach users.

## Objectives
1. Create `tests/test_cli_smoke.py` with comprehensive CLI smoke tests
2. Test all CLI commands for basic functionality
3. Verify no import/runtime errors occur
4. Ensure tests complete in < 30 seconds
5. Use subprocess for real CLI execution
6. Mock expensive operations (LLM, network)

## Specification Source
`plans/healing/cli-testing-system.md` lines 354-495

## Available CLI Commands (from --help)
- Main commands: scan, extract, compile-verify, compile-fix, runtime-verify, runtime-fix
- Management: md-update, final-review, commit, status, run, list-families, backfill
- Vector DB: clean-vector-db, visualize-drift, drift-trends

## Test Categories

### 1. Help Commands (5 tests)
- `test_main_help()` - Test `python -m src.cli.main --help`
- `test_run_help()` - Test `python -m src.cli.main run --help`
- `test_scan_help()` - Test `python -m src.cli.main scan --help`
- `test_compile_verify_help()` - Test `python -m src.cli.main compile-verify --help`
- `test_list_families_help()` - Test `python -m src.cli.main list-families --help`

### 2. Basic Execution Tests (5+ tests)
- `test_run_dry_run()` - Test run with --dry-run (no actual LLM calls)
- `test_list_families()` - Test listing families (reads config)
- `test_status_no_family()` - Test status without family filter
- `test_scan_with_temp_dir()` - Test scan with temporary directory
- `test_extract_dry_conditions()` - Test extract under dry conditions

### 3. Error Detection Tests (2 tests)
- `test_no_import_errors()` - Verify no ImportError in any command
- `test_proper_exit_codes()` - Verify exit codes are appropriate

### 4. Fixture Requirements
- Use existing `temp_workspace` fixture from conftest.py
- Use existing `cli_env` fixture for environment setup
- No additional fixtures needed

## Implementation Strategy

### Phase 1: Core Help Tests (15 min)
- Implement 5 help command tests
- Verify all return exit code 0
- Verify help text contains expected keywords

### Phase 2: Basic Execution Tests (30 min)
- Implement dry-run tests with minimal overhead
- Use --dry-run flags where available
- Mock file system operations where needed
- Ensure no actual LLM calls or network requests

### Phase 3: Error Detection (15 min)
- Add comprehensive import error checks
- Verify stderr output for error patterns
- Test exit code handling

### Phase 4: Testing & Validation (30 min)
- Run full test suite
- Verify < 30 second completion time
- Ensure all tests pass
- Document any edge cases

## Mock Strategy
- No actual mocking needed - use --dry-run flags and temporary directories
- Tests will use subprocess to invoke CLI (real execution)
- Expensive operations naturally skipped by using appropriate flags

## Expected Test Structure
```python
"""Smoke tests for CLI commands - catch import errors and basic execution issues."""
import subprocess
import pytest
from pathlib import Path

def test_main_help():
    """Test main --help works without import errors."""
    result = subprocess.run(
        ['python', '-m', 'src.cli.main', '--help'],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    assert '--help' in result.stdout
    assert 'ImportError' not in result.stderr
    assert 'NameError' not in result.stderr

# ... more tests
```

## Acceptance Criteria Checklist
- [ ] `pytest tests/test_cli_smoke.py -v` passes with 8+ tests
- [ ] All help commands return exit code 0
- [ ] All help commands display appropriate help text
- [ ] Basic execution tests complete without import errors
- [ ] Tests use temporary directories (no workspace pollution)
- [ ] Tests complete in < 30 seconds total
- [ ] Mock expensive operations (no actual LLM calls or network requests)

## Hard Rules Compliance
- ✅ No changes to CLI production code
- ✅ Tests use subprocess to invoke CLI (real execution)
- ✅ Mock expensive operations (LLM, network, file I/O)
- ✅ Tests complete quickly (< 30 seconds total)
- ✅ Tests use temporary directories (no pollution)

## Estimated Timeline
- Total: ~90 minutes
- Plan creation: 10 minutes
- Implementation: 60 minutes
- Testing & validation: 20 minutes

## Deliverables
1. `tests/test_cli_smoke.py` (~200 lines)
2. `reports/agents/agent-c/CT-02/run_20260117_012615/plan.md` (this file)
3. `reports/agents/agent-c/CT-02/run_20260117_012615/changes.md`
4. `reports/agents/agent-c/CT-02/run_20260117_012615/evidence.md`
5. `reports/agents/agent-c/CT-02/run_20260117_012615/self_review.md`

## Risk Assessment
- Low risk: Only creating new test files
- No production code changes
- Tests are isolated and use temporary directories
- All expensive operations avoided via flags

## Success Metrics
- All 8+ tests pass
- No import errors detected
- Tests complete in < 30 seconds
- Self-review scores ≥4/5 on all 12 dimensions
