# TASK_BACKLOG

## Canonical Backlog Snapshot
Generated: 2026-02-12 17:55 PKT

This file is the normalized orchestrator backlog. Legacy backlog content is preserved in `reports/TASK_BACKLOG.md` and is not replaced.

## Legacy Notes
- Prior DLL reflection migration backlog and task graph remains in `reports/TASK_BACKLOG.md`.
- This update adds currently active stabilization tasks discovered from:
  - `plans/healing/HEAL-2026-02-12-migration-008-run-id-duplicate-investigation.md`
  - `reports/agents/agent_c/MIG-008-TEST/run_20260212_175551/artifacts/pytest_full.log`
  - `src/core/database.py`
  - `migrations/008_run_scoping.sql`

## Active Workstreams (max 5 parallel)

### Workstream WS-MIG-008 (Database Migration Reliability)

#### ORCH-MIG-008-A (Agent A)
- ID: `ORCH-MIG-008-A`
- Scope: Architecture/discovery validation for migration bootstrap path and failure trigger map.
- Owner-Agent: Agent A (Discovery & Architecture)
- Affected Paths: `src/core/database.py`, `migrations/008_run_scoping.sql`, `plans/healing/HEAL-2026-02-12-migration-008-run-id-duplicate-investigation.md`
- Acceptance Criteria:
  - Root-cause path documented with file/line evidence.
  - Distinction between fresh DB baseline and upgrade DB migration behavior documented.
- Risk: Medium (incorrect diagnosis would misroute fixes).
- Required Tests: Evidence from focused pytest failures and migration code scan.
- Required Docs/Spec Updates: Update backlog/status references.

#### ORCH-MIG-008-B (Agent B)
- ID: `ORCH-MIG-008-B`
- Scope: Implement idempotent handling for migration 008 and fix fresh DB detection drift.
- Owner-Agent: Agent B (Implementation)
- Affected Paths: `src/core/database.py`
- Acceptance Criteria:
  - `Database.initialize_schema()` no longer fails with duplicate `run_id` when columns already exist.
  - Fresh DB baseline detection includes all current base schema tables.
- Risk: High (migration logic regression risk).
- Required Tests:
  - `venv\\Scripts\\python.exe -m pytest tests/test_database_schema.py -q`
  - `venv\\Scripts\\python.exe -m pytest tests/test_md_update_multiblock.py -q`
  - `venv\\Scripts\\python.exe -m pytest tests/test_sqlite_locking.py -q`
- Required Docs/Spec Updates: changelog + status + known gaps update.

#### ORCH-MIG-008-C (Agent C)
- ID: `ORCH-MIG-008-C`
- Scope: Verify regression closure with full test suite and capture evidence artifacts.
- Owner-Agent: Agent C (Tests & Verification)
- Affected Paths: `tests/`, `reports/agents/agent_c/MIG-008-TEST/run_20260212_175551/artifacts/`
- Acceptance Criteria:
  - Full test run green.
  - Previously failing migration-008 suites pass.
- Risk: Medium (false green due missing commands/evidence).
- Required Tests:
  - `venv\\Scripts\\python.exe -m pytest -q`
- Required Docs/Spec Updates: append evidence summary to `reports/STATUS.md`.

#### ORCH-MIG-008-D (Agent D)
- ID: `ORCH-MIG-008-D`
- Scope: Update docs/spec narrative to reflect resolved migration status and remaining warnings.
- Owner-Agent: Agent D (Docs & Specs)
- Affected Paths: `docs/known-gaps.md`, `reports/CHANGELOG.md`, `reports/STATUS.md`
- Acceptance Criteria:
  - Documentation no longer states migration 008 failures are active.
  - Remaining warnings are explicitly documented as open follow-up tasks.
- Risk: Low.
- Required Tests: N/A (doc task), reference test logs from Agent C.
- Required Docs/Spec Updates: required.

#### ORCH-MIG-008-E (Agent E)
- ID: `ORCH-MIG-008-E`
- Scope: Observability and ops follow-up for migration/pytest warning signals.
- Owner-Agent: Agent E (Observability & Ops)
- Affected Paths: `src/core/database.py`, `tests/test_validate_db_path_location.py`, `tests/test_validate_strict_context_no_examples.py`, `reports/STATUS.md`
- Acceptance Criteria:
  - Log surfaces for migration apply/failure confirmed.
  - Warning backlog items created for `PytestReturnNotNoneWarning` and asyncio loop-scope deprecation.
- Risk: Medium (warnings can become future failures).
- Required Tests: parse full pytest output and grep logging points.
- Required Docs/Spec Updates: status follow-up entries.

---

### Workstream WS-SR (Auto-Learn System Reliability)

**Generated**: 2026-02-12 (post-VFV validation)
**Source Plans**:
- `plans/healing/auto-learn-phase-trigger-fix.md`
- `plans/healing/learned-patterns-executable-fix-code.md`
- `plans/healing/runtime-examples-re-processing.md`
- `plans/healing/pattern-retirement-automation.md`
- `plans/healing/llm-final-review-config-fix.md`

**Context**: VFV validation runs revealed 5 critical gaps preventing auto-learn from working end-to-end:
- Auto-trigger not executing despite subprocess fix
- Patterns lack executable fix_code (rule-based limitation)
- Runtime failures excluded from re-processing
- Low performers not retired automatically
- Final review misconfigured (unavailable model)

#### SR-05 (Agent B) - Quick Win #1
- ID: `SR-05`
- Scope: Configure final review to use local Ollama fallback instead of unavailable gpt-oss.
- Owner-Agent: Agent B (Implementation)
- Affected Paths: `config/families/zip.json`, `config/families/words.json`
- Acceptance Criteria:
  - `final_review.model = "qwen2.5-coder:7b"` in both family configs.
  - Final review uses localhost:11434 (verified in logs).
  - No remote API calls for final review.
  - All 449 tests pass.
- Risk: Low (config-only change).
- Required Tests: `python -m pytest tests/ -q`
- Required Docs/Spec Updates: changelog entry.
- Estimated Time: 15 minutes

#### SR-03 (Agent B) - Quick Win #2
- ID: `SR-03`
- Scope: Include RUNTIME_FAILED examples in re-processing query when new patterns available.
- Owner-Agent: Agent B (Implementation)
- Affected Paths: `src/core/database.py`, `src/pipeline/orchestrator.py`
- Acceptance Criteria:
  - Query includes all 3 statuses: DISCOVERED, COMPILE_FAILED, RUNTIME_FAILED.
  - Run 2 logs show runtime examples re-processed.
  - All tests pass + new test validates runtime re-processing.
- Risk: Medium (query logic change).
- Required Tests: `python -m pytest tests/ -q`, new `tests/test_runtime_reprocessing.py`
- Required Docs/Spec Updates: inline comments + changelog.
- Estimated Time: 30 minutes

#### SR-01-A (Agent E)
- ID: `SR-01-A`
- Scope: Add debug logging to `_should_run_auto_learn()` and `_run_auto_learn_phase()` to diagnose why Phase F.5 doesn't trigger.
- Owner-Agent: Agent E (Observability & Ops)
- Affected Paths: `src/pipeline/orchestrator.py` (lines 739-773)
- Acceptance Criteria:
  - Logs show auto-learn config (enabled/disabled).
  - Logs show results dict 'success' value.
  - Logs show failed count calculation.
  - Logs show decision: "WILL RUN" or "SKIPPED because <reason>".
  - All 449 tests pass.
- Risk: Low (logging only, no logic changes).
- Required Tests: `python -m pytest tests/ -q`
- Required Docs/Spec Updates: none (logging instrumentation).
- Estimated Time: 1 hour

#### SR-01-B (Agent B) - BLOCKED
- ID: `SR-01-B`
- Scope: Fix auto-trigger root cause once identified by SR-01-A.
- Owner-Agent: Agent B (Implementation)
- Affected Paths: TBD (depends on SR-01-A findings)
- Acceptance Criteria: Phase F.5 executes automatically when failures detected.
- Risk: Medium (depends on root cause).
- Dependency: **Blocked on SR-01-A**
- Estimated Time: 1-2 hours

#### SR-02-A (Agent B)
- ID: `SR-02-A`
- Scope: Configure auto-learn to use remote LLM endpoint for pattern extraction.
- Owner-Agent: Agent B (Implementation)
- Affected Paths: `config/global.json`, `scripts/auto_learn.py`
- Acceptance Criteria:
  - `auto_learn.use_llm = true` in global config.
  - Auto-learn connects to remote endpoint (not localhost Ollama).
  - Token usage <100 per pattern.
  - All tests pass.
- Risk: Medium (LLM integration).
- Required Tests: `python -m pytest tests/ -q`, manual auto-learn run
- Required Docs/Spec Updates: changelog + token cost estimate.
- Estimated Time: 1 hour

#### SR-02-B (Agent B) - BLOCKED
- ID: `SR-02-B`
- Scope: Enhance LLMPatternExtractor to generate executable fix_code (regex_replace, using_directive, code_transform).
- Owner-Agent: Agent B (Implementation)
- Affected Paths: `scripts/auto_learn.py` (lines 142-234)
- Acceptance Criteria: Patterns stored with executable fix_type (not llm_prompt templates).
- Risk: High (pattern quality critical).
- Dependency: **Blocked on SR-02-A**
- Estimated Time: 2 hours

#### SR-02-C (Agent C) - BLOCKED
- ID: `SR-02-C`
- Scope: Validate Run 1 → Run 2 improvement with executable patterns.
- Owner-Agent: Agent C (Tests & Verification)
- Affected Paths: `scripts/validate_executable_patterns.py` (new)
- Acceptance Criteria: Run 2 shows ≥10 example improvement over Run 1.
- Risk: Medium (validation coverage).
- Dependency: **Blocked on SR-02-B**
- Estimated Time: 2 hours

#### SR-04-A (Agent B)
- ID: `SR-04-A`
- Scope: Add pattern retirement policy configuration.
- Owner-Agent: Agent B (Implementation)
- Affected Paths: `config/global.json`, `src/core/config.py`, family configs
- Acceptance Criteria: RetirementPolicyConfig model validates all fields.
- Risk: Low (config schema addition).
- Required Tests: `python -m pytest tests/test_retirement_config.py -v`
- Required Docs/Spec Updates: inline comments.
- Estimated Time: 1 hour

#### SR-04-B (Agent B) - BLOCKED
- ID: `SR-04-B`
- Scope: Implement automated pattern retirement logic.
- Owner-Agent: Agent B (Implementation)
- Affected Paths: `src/services/learned_patterns_service.py`, `scripts/auto_learn.py`
- Acceptance Criteria: Auto-learn retires patterns matching policy automatically.
- Risk: Medium (retirement logic correctness).
- Dependency: **Blocked on SR-04-A**
- Estimated Time: 2 hours

