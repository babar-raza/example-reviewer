# Known Gaps and Repo Health Checklist

> Last verified: 2026-06-13

This document tracks structural gaps that may affect the project. Resolved items are marked accordingly.

## Missing Source Files Referenced by Imports or Bytecode

Some folders contain only `__pycache__` entries for modules that are not present as `.py` sources:

- `src/patching/` (missing the expected patching sources)
- `src/validation/analysis/` and `src/validation/fixing/`
- `src/discovery/` bytecode references `gist_service` and `snippet_locator`

If any runtime path imports these modules, you will get `ModuleNotFoundError`.

## ~~No Root README, Packaging, or Dependency Manifest~~ (RESOLVED)

All of the following now exist:

- `README.md` (740+ lines)
- `requirements.txt` (pinned dependencies, Python >= 3.10)
- `setup.py` (version 1.0.0, `python_requires=">=3.10"`)

Install: `pip install -r requirements.txt` or `pip install -e .`

## Config Schema Mismatch

Some family configs include fields that the current parser ignores (`namespace_policy`, `persistent_fix`, `dependency_resolution`).

If those features are desired, they must be added to `FamilyConfig` and `_parse_family_config`, and then wired into the relevant services.

## Windows-Specific Assumptions

- Some family configs contain absolute Windows paths (`D:/...`).
- The code writes temporary projects and executes `dotnet`, which requires a .NET SDK.

## ~~Minimal Test Coverage in This Archive~~ (RESOLVED)

The `tests/` directory contains 70+ test files covering unit tests, fallback scenarios, security baselines, and package smoke tests. Coverage threshold is enforced at 50% in CI.

**Remaining gap:** All tests use mocks; no integration tests exercise real external services (LLM, .NET SDK). See `tests/test_integration_real.py` for narrow integration tests that exercise real config loading and database creation without external deps.

## Checklist for Hardening

- [x] Add `README.md` with quickstart and prerequisites — see README.md (740+ lines)
- [x] Add dependency manifest (`requirements.txt` or `pyproject.toml`) — requirements.txt and setup.py present
- [x] Add tests and CI wiring — 70+ test files; CI in .gitlab-ci.yml
- [ ] Restore missing source modules or remove dead imports — `src/patching/`, `src/validation/analysis/`, `src/discovery/` still have only `__pycache__` with no `.py` sources
- [ ] Normalize config paths (no absolute machine-specific paths) — some `config/families/*.json` still use absolute Windows paths (`D:/...`)
- [ ] Document how artifacts and DB are stored and cleaned between runs

## How to Validate Safely

To validate the system safely, follow these steps:

1. **Ensure your content roots in the family config point to a small test dataset** (not a large real repo).
2. **Run discovery and extraction only**:
   ```bash
   PYTHONPATH=. python -m src.cli.main extract --family zip --max-files 5
   ```
3. **Run compilation verification with no LLM fixes**:
   ```bash
   PYTHONPATH=. python -m src.cli.main compile-verify --family zip --max-examples 20
   ```
4. **If you have `test-data/zip`, run runtime verification**:
   ```bash
   PYTHONPATH=. python -m src.cli.main runtime-verify --family zip --max-examples 20
   ```
5. **Do a dry-run markdown update**:
   ```bash
   PYTHONPATH=. python -m src.cli.main md-update --family zip --dry-run
   ```

Only after verifying diffs look correct should you enable writes:

- Set `config/global.json` -> `markdown_write.allow_markdown_write=true`
- Or pass `--allow-md-write`

## Backfill Workflow

If you want the system to populate caches for you:

```bash
PYTHONPATH=. python -m src.cli.main backfill --family zip --force
```

**Notes**:

- Backfill requires GitPython for repo cloning.
- Gist source backfill requires outbound network access.

## Cleaning Between Runs

- Remove `workspace/` if you want a clean build workspace.
- Keep `artifacts/` for debugging failed attempts.
- Use the DB run records to compare statistics and drift trends.
## Update — 2026-02-12 17:55 PKT

### What Changed
- DEPRECATED: Prior assumption that migration 008 failures are an active repo-wide blocker.
- Current state from verification logs:
  - Full test suite passes: `449 passed, 3 warnings`.
  - Migration bootstrap no longer fails on duplicate `run_id` for migration 008.

### Why
Migration reliability hardening was implemented in `src/core/database.py` to:
1. Skip duplicate-prone `ALTER TABLE ... ADD COLUMN run_id` statements in migration 008 when columns already exist.
2. Correct fresh DB baseline detection by aligning `_is_fresh_database()` base table inventory with current schema tables. **Note (2026-06-13):** The 2026-02-12 fix covered migration 008 but `work_queue` was still missing from `base_tables`, causing migration 009 to fail on fresh DBs. Fixed in this sprint by adding `work_queue` to `base_tables`.

### Evidence
- `reports/agents/agent_c/MIG-008-TEST/run_20260212_175551/artifacts/pytest_full.log`
- `reports/agents/agent_a/MIG-008-ARCH/run_20260212_175551/artifacts/database_migration_points.txt`
- `reports/agents/agent_a/MIG-008-ARCH/run_20260212_175551/artifacts/migration_008_run_id_alter.txt`

### Remaining Known Gaps
- `PytestReturnNotNoneWarning` appears in:
  - `tests/test_validate_db_path_location.py`
  - `tests/test_validate_strict_context_no_examples.py`
- `pytest_asyncio` warning about `asyncio_default_fixture_loop_scope` not explicitly set.

