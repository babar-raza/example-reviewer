# CT-04 Implementation Plan: CI Integration

**Agent**: Agent E (Observability & Ops)
**Task ID**: CT-04
**Priority**: P1 (HIGH - Automates validation)
**Start Time**: 2026-01-16 21:00:00

## Objective

Create GitHub Actions workflow to automatically run static analysis and smoke tests on every commit and pull request, catching CLI issues before they reach users.

## Implementation Steps

### Phase 1: Workflow Structure (10 min)
1. Create `.github/workflows/cli_tests.yml`
2. Define trigger conditions (push to main/develop/opus-example-reviewer-pipeline, PRs to main)
3. Set up workflow name and basic structure

### Phase 2: Static Analysis Job (20 min)
1. Configure ubuntu-latest runner
2. Add checkout action (v4)
3. Add Python setup action (v5) with version 3.10
4. Run analyze_cli_imports.py on key files:
   - src/cli/main.py (primary target)
   - src/pipeline/orchestrator.py (core service)
   - src/core/database.py (core service)
   - src/services/llm_service.py (core service)
5. No dependencies needed (static analysis)

### Phase 3: Smoke Tests Job (30 min)
1. Configure ubuntu-latest runner
2. Add checkout action (v4)
3. Add Python setup action (v5) with pip cache enabled
4. Install dependencies:
   - Upgrade pip
   - Install pytest, pytest-timeout
   - Install from requirements.txt
5. Run pytest on tests/test_cli_smoke.py with timeout
6. Run simple import analyzer test

### Phase 4: Matrix Tests Job (20 min)
1. Configure conditional execution (PRs only)
2. Same setup as smoke tests
3. Run pytest on tests/test_cli_matrix.py
4. Use continue-on-error (optional test suite)

### Phase 5: Validation (30 min)
1. Validate YAML syntax with Python yaml module
2. Check file exists and is well-formed
3. Verify all job names and steps are clear
4. Document validation results

### Phase 6: Testing (if possible) (10 min)
1. Create test branch
2. Commit workflow file
3. Push to GitHub
4. Check Actions tab for execution
5. Document results (or note if testing not possible)

### Phase 7: Documentation (30 min)
1. Complete changes.md with file listing
2. Complete evidence.md with validation output
3. Complete self_review.md with 12-dimension assessment
4. Ensure all dimensions score ≥4/5

## Key Design Decisions

1. **Trigger Branches**: Include opus-example-reviewer-pipeline (current branch) to test immediately
2. **Python Version**: Use 3.10 (stable, matches project requirements)
3. **Pip Cache**: Enable for faster CI runs (save/restore pip packages)
4. **Timeout**: 30s for smoke tests, 120s for matrix tests (prevent hanging)
5. **Continue on Error**: Matrix tests are optional, don't block PRs
6. **Action Versions**: Use latest stable (checkout@v4, setup-python@v5)

## Success Criteria

- [ ] Workflow file created at .github/workflows/cli_tests.yml
- [ ] YAML syntax validated successfully
- [ ] All three jobs defined with clear names
- [ ] Static analysis runs without dependencies
- [ ] Smoke tests run with proper dependencies and timeout
- [ ] Matrix tests conditional on PR events
- [ ] Evidence shows actual validation output
- [ ] All 12 self-review dimensions ≥4/5

## Risk Mitigation

- **Risk**: Workflow may not trigger immediately
  - **Mitigation**: Document validation, test locally if needed
- **Risk**: Dependencies may fail to install
  - **Mitigation**: Use pip cache, upgrade pip first
- **Risk**: Tests may timeout
  - **Mitigation**: Set reasonable timeouts (30s smoke, 120s matrix)
- **Risk**: Matrix tests may not exist yet
  - **Mitigation**: Use continue-on-error flag

## Timeline

- Phase 1-4: 80 minutes (implementation)
- Phase 5-6: 40 minutes (validation/testing)
- Phase 7: 30 minutes (documentation)
- **Total**: ~2.5 hours (within 2-3 hour estimate)

## References

- GitHub Actions docs: https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions
- setup-python cache: https://github.com/actions/setup-python#caching-packages-dependencies
- Static analyzer: scripts/analyze_cli_imports.py
- Smoke tests: tests/test_cli_smoke.py
