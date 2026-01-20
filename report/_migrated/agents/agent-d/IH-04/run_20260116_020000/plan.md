# Task IH-04 Cleanup Plan

## Agent: D (Docs & Specs)
## Task: Repository Hygiene - Root Directory Cleanup
## Date: 2026-01-16
## Priority: P0 (CRITICAL - Quick win)

## Current State

Root directory contains numerous temporary/analysis scripts and old summary files:

**Analysis Scripts (21 files)**:
- analyze_failure.py
- analyze_failures.py
- analyze_remaining_failures.py
- analyze_runtime_failures.py
- check_api_index.py
- check_example_status.py
- check_gists.py
- check_snippet.py
- clear_zip_data.py
- create_encrypted_samples.py
- manual_test_namespace_validator.py
- reset_snippets.py
- run.py
- run_cli.py
- run_e2e_verification.py
- run_single_example_debug.py
- run_tests.py
- run_validation.py
- validate_hardening.py
- verify_multi_family.py
- verify_runtime_recording.py

**Old Summary Files**:
- RUNTIME_ATTEMPT_FIX_SUMMARY.md
- MULTI_FAMILY_VERIFICATION_RESULTS.md

## Target State

Clean root directory with:
- Only essential project files (README.md, QUICKSTART.md, requirements.txt, etc.)
- Analysis scripts moved to `archive/analysis-scripts/`
- Old summaries moved to `archive/old-summaries/`
- Updated .gitignore for temporary files
- Updated CHANGELOG.md documenting cleanup

## Execution Steps

### Phase 1: Prepare Archive Structure
1. Create `archive/analysis-scripts/` directory
2. Create `archive/old-summaries/` directory
3. Create `archive/README.md` to explain archive contents

### Phase 2: Move Analysis Scripts
Move all analysis/validation/verification scripts using `git mv` to preserve history:
- All `analyze_*.py` files
- All `check_*.py` files
- All `run_*.py` files (except run_cli.py if actively used)
- All `validate_*.py` files
- All `verify_*.py` files
- `create_encrypted_samples.py`
- `clear_zip_data.py`
- `reset_snippets.py`
- `manual_test_namespace_validator.py`

### Phase 3: Move Old Summaries
- `RUNTIME_ATTEMPT_FIX_SUMMARY.md`
- `MULTI_FAMILY_VERIFICATION_RESULTS.md`

### Phase 4: Update Configuration
1. Review and update `.gitignore` if needed
2. Update `CHANGELOG.md` with cleanup actions

### Phase 5: Verification
1. Verify CLI still works: `python -m src.cli.main --help`
2. Check root directory cleanliness
3. Verify git status shows clean moves
4. Run basic smoke test if available

### Phase 6: Documentation
1. Create changes.md with all moves
2. Create evidence.md with verification outputs
3. Create self_review.md with quality assessment

## Risk Mitigation

- Using `git mv` preserves file history
- Verification step ensures CLI functionality
- Archive structure allows recovery if needed
- All changes are version controlled

## Success Criteria

- Root directory contains only essential project files
- All temporary/analysis scripts in archive
- CLI functionality verified working
- Git history preserved
- Documentation complete
