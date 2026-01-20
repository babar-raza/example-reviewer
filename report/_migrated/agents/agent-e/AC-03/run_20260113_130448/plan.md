# Plan: AC-03 commit messages + telemetry association

## Assumptions (verify)
- Auto-commit core (AC-01) is complete and returns commit SHA.
- Telemetry HTTP API configuration (TM-02) is complete.
- Family config can supply optional commit_message_template.

## Steps
1. Enhance commit message generation in `src/patching_service.py`.
2. Add telemetry commit association in `src/telemetry.py` and wire from patching service.
3. Pass telemetry client and commit templates via `src/cli.py`.
4. Update `config/families/zip.json` with example template.
5. Add tests in `test_commit_message_generation.py`.
6. Run tests and capture evidence.

## Rollback Plan
- Revert edits in `src/patching_service.py`, `src/telemetry.py`, `src/cli.py`, and remove test file.

## Tests to Add/Run
- `pytest test_commit_message_generation.py -v`

## Done Means (Acceptance Checklist)
- [ ] Commit messages include counts, file list, and snippet IDs
- [ ] Custom template supported via config
- [ ] Telemetry commit association called and failures handled
- [ ] Tests pass and evidence captured

## Update — 2026-01-13 13:05 PKT

Status: COMPLETE

Acceptance checklist:
- [x] Commit messages include counts, file list, and snippet IDs
- [x] Custom template supported via config
- [x] Telemetry commit association called and failures handled
- [x] Tests pass and evidence captured
