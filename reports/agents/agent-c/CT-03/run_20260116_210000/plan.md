# CT-03 Implementation Plan: Runtime Matrix Tests

## Task Overview
Create comprehensive parameterized matrix tests for CLI option combinations to ensure all valid combinations work and invalid combinations are properly rejected.

## Current State Analysis

### Existing Infrastructure
- **tests/test_cli_smoke.py**: Basic smoke tests covering help commands and simple execution
- **tests/conftest.py**: Provides `temp_workspace` and `cli_env` fixtures
- **src/cli/main.py**: CLI entry point with argparse-based command handling

### CLI Run Command Options
From analysis of src/cli/main.py lines 139-150:
- `--family` (required): Family identifier
- `--max-examples`: Maximum examples to process
- `--skip-runtime`: Skip runtime verification phase
- `--skip-llm`: Skip LLM-based fixing
- `--dry-run`: Don't write changes

### Global Options
From lines 58-68:
- `--config-dir`: Path to family config directory
- `--db-path`: Path to database file
- `--workspace-dir`: Path to workspace directory
- `--verbose`: Enable verbose output
- `--json`: Output results as JSON

## Implementation Strategy

### 1. Test Structure
Create `tests/test_cli_matrix.py` with the following test categories:

#### A. Family and Max-Examples Combinations
- Test different families with varying max-examples values
- Validate family existence checking
- Test boundary conditions (0, 1, large numbers)

#### B. Flag Combinations
- Test individual flags: --skip-runtime, --skip-llm, --dry-run
- Test flag pairs: all 2-combination sets
- Test all flags together
- Ensure additive behavior (multiple flags don't conflict)

#### C. Value Parameter Ranges
- Test max-examples with different ranges (1, 5, 10)
- Test timeout values (if exposed in run command)
- Test invalid values (negative, zero where inappropriate)

#### D. Global Options Integration
- Test run command with custom --workspace-dir
- Test run command with custom --db-path
- Test --json output format
- Test --verbose flag

#### E. Incompatible Options Detection
- Test --dry-run with operations that would require writes
- Test mutually exclusive flags (if any)
- Verify appropriate error messages

### 2. Test Design Principles

#### Speed Optimization
- Use `--dry-run` for most tests to avoid actual processing
- Use `max-examples=1` to minimize work
- Mock or skip expensive operations
- Target < 2 minutes total runtime

#### Fixture Reuse
- Leverage `temp_workspace` from conftest.py
- Create new fixture `run_cli_with_timeout` for consistent invocation
- Share test data across parameterized tests

#### Assertions Strategy
- Check return code (0 for success, non-zero for failure)
- Verify no import errors (reuse from smoke tests)
- Check expected output patterns in stdout/stderr
- Validate JSON output structure when --json used

### 3. Test Matrix Coverage

#### Minimum 15 Parameterized Tests:
1. Family variations (zip, pdf, cells) x max-examples (1, 5)
2. Skip flags (5 combinations)
3. Dry-run combinations (3 variants)
4. Global option combinations (4 variants)
5. Invalid input detection (3 negative tests)

## Implementation Steps

1. Create test file with imports and helper functions
2. Implement run_cli helper (similar to smoke tests)
3. Add parameterized tests for family/max-examples
4. Add parameterized tests for flag combinations
5. Add value parameter range tests
6. Add global options integration tests
7. Add negative tests for invalid combinations
8. Run full test suite and optimize timing
9. Document results in evidence.md

## Expected Challenges

1. **Timing Constraint**: Need to keep all tests under 2 minutes
   - Mitigation: Use --dry-run extensively, minimize actual processing

2. **Family Dependencies**: Tests depend on config/families/*.json existing
   - Mitigation: Use temp_workspace with test_family config, or test against known families

3. **Subprocess Management**: Need proper timeout handling
   - Mitigation: Set reasonable timeouts (30s per test), use subprocess.run with timeout

4. **Output Validation**: Different commands produce different output formats
   - Mitigation: Use flexible assertions, check for key indicators rather than exact matches

## Success Criteria

- [ ] 15+ parameterized test cases
- [ ] All tests pass
- [ ] Total runtime < 2 minutes
- [ ] No import errors in any test
- [ ] Proper error detection for invalid inputs
- [ ] Clear test names and documentation
- [ ] Evidence document with actual test output
- [ ] Self-review scores ≥4/5 on all dimensions

## Timeline

1. Setup and infrastructure (30 min)
2. Family/max-examples tests (45 min)
3. Flag combination tests (45 min)
4. Value parameter and global option tests (45 min)
5. Negative tests and validation (30 min)
6. Test execution and optimization (45 min)
7. Documentation and evidence (45 min)

**Total**: ~6 hours (matches task estimate)
