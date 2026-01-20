# Changes

Status: In progress.

## Update — 2026-01-13 13:17 PKT

- Added rollback history table in `schema.sql` and DB accessors in `src/database.py`.
- Implemented backup creation and rollback operations in `src/patching_service.py`.
- Added rollback CLI command and `--create-backup` flag in `src/cli.py`.
- Added `test_patching_rollback.py` with 3 passing tests.
