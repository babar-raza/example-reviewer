# Plan: AC-04 rollback mechanism

## Assumptions (verify)
- Git available for rollback operations.
- Database schema can be extended with rollback_history table.
- Patching service can store rollback entries after patching.

## Steps
1. Add rollback_history table to `schema.sql` and DB accessors in `src/database.py`.
2. Implement backup creation and rollback operations in `src/patching_service.py`.
3. Add rollback CLI command and `--create-backup` flag in `src/cli.py`.
4. Add tests in `test_patching_rollback.py`.
5. Run tests and capture evidence.

## Rollback Plan
- Revert schema and code changes; drop rollback_history table if needed.

## Tests to Add/Run
- `pytest test_patching_rollback.py -v`

## Done Means (Acceptance Checklist)
- [ ] Backup branch created with `--create-backup`
- [ ] Rollback history recorded and listable
- [ ] Rollback last operation works (git reset)
- [ ] Rollback single file works (git checkout)
- [ ] Tests pass and evidence captured

## Update — 2026-01-13 13:17 PKT

Status: COMPLETE

Acceptance checklist:
- [x] Backup branch created with `--create-backup`
- [x] Rollback history recorded and listable
- [x] Rollback last operation works (git reset)
- [x] Rollback single file works (git checkout)
- [x] Tests pass and evidence captured
