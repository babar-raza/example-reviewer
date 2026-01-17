# Changes

Status: Not started. No files modified yet.

Planned files:
- `src/cli.py`
- `config/families/zip.json`
- `.env.example`
- `test_auto_commit_config.py`

## Update — 2026-01-12 20:39 PKT

- Implemented auto-commit config hierarchy and `--no-auto-commit` override in `src/cli.py`.
- Added `auto_commit` default to `config/families/zip.json`.
- Documented `AUTO_COMMIT_ENABLED` in `.env.example`.
- Added `test_auto_commit_config.py` (4 tests) for config precedence.
