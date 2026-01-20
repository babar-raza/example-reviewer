# Changes

Status: Not started. No files modified yet.

Planned files:
- `src/patching_service.py`
- `src/cli.py`
- `test_patching_auto_commit.py`

## Update — 2026-01-12 20:35 PKT

- Added auto-commit workflow in `src/patching_service.py` with git add/commit and SHA capture.
- Wired `--auto-commit` CLI flag and pass-through in `src/cli.py`.
- Added `test_patching_auto_commit.py` (5 tests) covering commit creation, dry-run, errors, and missing git.
