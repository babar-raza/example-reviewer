# Implementation Plan - IH-02: CLI Entry Point Fix

## Task Overview
Create top-level `cli` package to enable cleaner invocation pattern:
- Current: `python -m src.cli.main run --family zip`
- Target: `python -m cli run --family zip`

## Implementation Steps

### 1. Create CLI Package Structure (15 min)
- Create `cli/` directory at project root
- Create `cli/__init__.py` (import main from src.cli.main)
- Create `cli/__main__.py` (delegate to src.cli.main.main())

### 2. Update Documentation (60 min)
- Update README.md with new CLI examples
- Update all docs/*.md files with new CLI pattern
- Show both old and new patterns during transition period

### 3. Testing (30 min)
- Test new invocation: `python -m cli --help`
- Test backward compatibility: `python -m src.cli.main --help`
- Verify both produce identical output
- Test multiple commands (discover, run, status)

### 4. Documentation (15 min)
- Create evidence.md with test results
- Create changes.md with file list
- Create self_review.md with 12-dimension assessment

## Success Criteria
- Both invocation patterns work correctly
- All documentation updated consistently
- No functional regressions
- All tests pass
- All 12 quality dimensions ≥4/5

## Estimated Time
Total: 2 hours (within 3-hour budget)

## Files to Create
1. `cli/__init__.py` (NEW)
2. `cli/__main__.py` (NEW)

## Files to Update
1. `README.md`
2. All `docs/*.md` files with CLI examples
3. Evidence files in run folder

## Risk Assessment
- **Low Risk**: Simple wrapper pattern
- **Backward Compatible**: Old pattern still works
- **No Breaking Changes**: Pure addition of new entry point
