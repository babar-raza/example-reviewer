# Plan: AC-02 auto-commit configuration

## Assumptions (verify)
- `src/cli.py` loads family config and can be extended with new flags.
- `config/families/zip.json` exists and can include an `auto_commit` field.
- `.env.example` documents environment defaults.

## Steps
1. Inspect `src/cli.py` patch command argument parsing and config loading.
2. Add `--auto-commit` and `--no-auto-commit` flags with `None` default.
3. Implement config precedence: CLI flag > family config > env var > default.
4. Update `config/families/zip.json` to include `auto_commit` example.
5. Update `.env.example` with `AUTO_COMMIT_ENABLED`.
6. Add `test_auto_commit_config.py` covering hierarchy and default behavior.
7. Capture test evidence.

## Rollback Plan
- Revert edits in `src/cli.py`, `config/families/zip.json`, `.env.example`, and `test_auto_commit_config.py` using git or backups.

## Tests to Add/Run
- `pytest test_auto_commit_config.py -v`

## Done Means (Acceptance Checklist)
- [ ] CLI flag overrides family config and env var
- [ ] Env var used when no CLI or family config
- [ ] Default remains false (opt-in)
- [ ] Tests pass and evidence captured

## Dependencies
- AC-01 completion to avoid conflicts in `src/cli.py`

## Update — 2026-01-12 20:39 PKT

Status: COMPLETE

Acceptance checklist:
- [x] CLI flag overrides family config and env var
- [x] Env var used when no CLI or family config
- [x] Default remains false (opt-in)
- [x] Tests pass and evidence captured
