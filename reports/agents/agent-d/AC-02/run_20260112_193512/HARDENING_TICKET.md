# HARDENING TICKET: AC-02

## Failing Dimensions
- Coverage, Correctness, Evidence, Test Quality, Maintainability, Safety, Security, Reliability, Observability, Performance, Compatibility, Docs/Specs Fidelity

## Missing Evidence/Tests/Docs
- CLI config hierarchy logic in `src/cli.py`
- `config/families/zip.json` auto_commit example
- `.env.example` `AUTO_COMMIT_ENABLED` documentation
- `test_auto_commit_config.py` results

## Next Actions
1. Implement config hierarchy in `src/cli.py` with `--auto-commit` / `--no-auto-commit`.
2. Update `config/families/zip.json` and `.env.example` with auto-commit settings.
3. Add `test_auto_commit_config.py` covering hierarchy and defaults.
4. Run tests and capture outputs in `evidence.md`.
5. Update `self_review.md` with evidence-backed scores >= 4 and clear Known Gaps.

## Update — 2026-01-12 20:39 PKT

Status: RESOLVED. Configuration hierarchy implemented and tests passing.
