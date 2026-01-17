# Plan: AC-01 auto-commit core

## Assumptions (verify)
- `PatchingService.patch_verified_snippets()` returns a results dict with `modified_files`, `errors`, and `patches_applied`.
- CLI `patch` command uses `PatchingService` and can accept new flags.
- Git is available in the execution environment for real commits.

## Steps
1. Read `src/patching_service.py` to locate `patch_verified_snippets()` and results structure.
2. Add `auto_commit: bool = False` parameter and gate logic after successful patching.
3. Implement `_git_commit_changes()` with `git add`, `git commit`, and commit SHA retrieval.
4. Add error handling for missing git or failed commits (log warning, no crash).
5. Update `src/cli.py` to add `--auto-commit` flag and pass through.
6. Add `test_patching_auto_commit.py` using temp git repo for commits.
7. Capture test output evidence.

## Rollback Plan
- Revert edits in `src/patching_service.py`, `src/cli.py`, and `test_patching_auto_commit.py` using git or backups.

## Tests to Add/Run
- `pytest test_patching_auto_commit.py -v`

## Done Means (Acceptance Checklist)
- [ ] `--auto-commit` stages modified files and creates a commit
- [ ] Dry-run mode disables auto-commit
- [ ] Commit SHA returned in results
- [ ] Graceful handling when git unavailable or commit fails
- [ ] Tests pass and evidence captured

## Update — 2026-01-12 20:35 PKT

Status: COMPLETE

Acceptance checklist:
- [x] `--auto-commit` stages modified files and creates a commit
- [x] Dry-run mode disables auto-commit
- [x] Commit SHA returned in results
- [x] Graceful handling when git unavailable or commit fails
- [x] Tests pass and evidence captured
