# Task Backlog: Gist Hardening

**Created**: 2026-01-11
**Plan Source**: plans/from_chat/20260111_gist_hardening.md
**Orchestrator**: Task normalization and agent assignment

---

## ✅ EMERGENCY BLOCKER - RESOLVED

**ID**: BLOCK-001
**Status**: COMPLETE - Committed to main (01fdfc7)
**Discovered**: Agent C during HARD-001 execution
**Resolved By**: Agent B
**Impact**: Was blocking all testing activities - NOW UNBLOCKED

See: reports/EMERGENCY_BLOCK-001.md
Evidence: reports/agents/agent-b/block-001/evidence.md

---

## Workstream Summary

**Total Tasks**: 6 (5 original + 1 emergency blocker - RESOLVED)
**Current Status**: BLOCK-001 complete, HARD-001 ready to resume
**Critical Path**: HARD-001 (complete E2E) → HARD-002 (integration tests) → Final Review

---

## Task 0: CLI Path Resolution Bug Fix (BLOCKER)

**ID**: BLOCK-001
**Scope**: Fix CLI repo_root calculation that points outside repository
**Owner**: Agent B (Implementation)
**Priority**: P0 (EMERGENCY - blocks everything)
**Risk**: LOW (one-line fix)

**Paths**:
- src/cli.py (UPDATE - line 29)
- tests/test_cli_paths.py (NEW)
- reports/agents/agent-b/block-001/evidence.md (NEW)

**Criteria**:
1. repo_root points to repository root directory
2. config_dir points to <repo>/config/families/
3. content_dir points to <repo>/content/
4. Discovery command finds config in correct location
5. Unit test validates path resolution
6. Evidence shows before/after paths

**Fix**: Change line 29 from `self.repo_root = self.script_dir.parent.parent` to `self.repo_root = self.script_dir`

**Tests**: tests/test_cli_paths.py
**Docs**: None needed (bug fix)

**Self-Review Focus**: Correctness (paths now valid), Safety (no regression), Evidence (clear before/after)

---

## Task 1: End-to-End Smoke Test

**ID**: HARD-001
**Scope**: Prove gist support works end-to-end with real GitHub API
**Owner**: Agent C (Tests & Verification)
**Priority**: P0 (BLOCKING)
**Risk**: RESOLVED
**Status**: ✅ COMPLETE - Full E2E validated, 2 critical bugs fixed (commits 01fdfc7, 3841547)
**Final Evidence**: reports/agents/agent-c/hard-001/evidence_final.md

**Paths**:
- config/families/test.json (NEW)
- test-content/gist-smoke.md (NEW)
- cache/gists/ (verify creation)
- data/examples.db (verify entries)
- reports/agents/agent-c/hard-001/evidence.md (NEW)

**Criteria**:
1. Gist fetched successfully from real GitHub API
2. Cache directory structure verified (JSON + raw files)
3. Database entries correct (gists + gist_files tables)
4. Patch dry-run shows correct replacement logic
5. All commands complete without errors
6. Evidence file contains full command output

**Tests**: tests/test_e2e_smoke.py (NEW)
**Docs**: README update with smoke test instructions

**Self-Review Focus**: Evidence (must have real API logs), Correctness (E2E workflow), Robustness (error handling)

---

## Task 2: Integration Test Suite

**ID**: HARD-002
**Scope**: Add opt-in integration tests with real GitHub API
**Owner**: Agent C (Tests & Verification)
**Priority**: P0 (BLOCKING)
**Risk**: RESOLVED
**Status**: ✅ COMPLETE - 54 tests, 100% passing, 5.0/5 score (commits c475b88, 91d6dc1)
**Final Evidence**: reports/agents/agent-c/hard-002/evidence.md

**Paths**:
- tests/test_gist_integration.py (NEW)
- tests/README.md (UPDATE)
- pytest.ini or pyproject.toml (UPDATE markers)
- reports/agents/agent-c/hard-002/evidence.md (NEW)

**Criteria**:
1. Integration tests cover 5+ real API scenarios
2. Tests pass with real GitHub API (when token available)
3. Tests skip gracefully without token
4. Cache hit/miss behavior validated
5. Error scenarios tested (404, timeout, rate limit)
6. Documentation explains opt-in testing

**Tests**: Self-contained in test_gist_integration.py
**Docs**: tests/README.md integration testing section

**Dependencies**: HARD-001 (smoke test provides baseline)

**Self-Review Focus**: Test Quality (coverage depth), Robustness (error scenarios), Docs Fidelity (clear instructions)

---

## Task 3: Cache Validation & Recovery

**ID**: HARD-003
**Scope**: Add cache integrity checking and recovery mechanisms
**Owner**: Agent B (Implementation)
**Priority**: P1 (HIGH)
**Risk**: RESOLVED
**Status**: ✅ COMPLETE - 13 tests, verify_cache() implemented, 5.0/5 score
**Final Evidence**: reports/agents/agent-b/hard-003/run_20260111_203336/evidence.md

**Paths**:
- src/gist_service.py (UPDATE - add verify_cache method)
- src/cli.py (UPDATE - call verify_cache on discover)
- tests/test_cache_validation.py (NEW)
- docs/operations.md (NEW)
- reports/agents/agent-b/hard-003/evidence.md (NEW)

**Criteria**:
1. verify_cache() detects corrupted JSON files
2. Corrupted files removed automatically with logging
3. Unit tests cover valid cache, corrupted JSON, missing files
4. Operations doc explains cache maintenance
5. No crashes from cache corruption
6. Warnings logged with file paths

**Tests**: tests/test_cache_validation.py with mocked filesystem
**Docs**: docs/operations.md cache maintenance section

**Dependencies**: None (can run in parallel)

**Self-Review Focus**: Reliability (corruption handling), Safety (no data loss), Maintainability (clear logging)

---

## Task 4: Security & Operations Documentation

**ID**: HARD-004
**Scope**: Add production-ready security and ops documentation
**Owner**: Agent D (Docs & Specs)
**Priority**: P1 (HIGH)
**Risk**: RESOLVED
**Status**: ✅ COMPLETE - 1507 lines docs, all validated, 5.0/5 score
**Final Evidence**: reports/agents/agent-d/hard-004/run_20260111_143000/evidence.md

**Paths**:
- docs/security.md (NEW)
- docs/operations.md (NEW or UPDATE from HARD-003)
- docs/configuration.md (UPDATE - add security references)
- README.md (UPDATE - add links)
- reports/agents/agent-d/hard-004/evidence.md (NEW)

**Criteria**:
1. GITHUB_TOKEN scopes documented clearly
2. Cache size monitoring commands provided
3. Database cleanup queries tested and documented
4. Troubleshooting guide covers 5+ common issues
5. Security doc reviewed for completeness
6. Links added to main README

**Tests**: None (documentation only, but validate all commands work)
**Docs**: Self-contained (creating documentation)

**Dependencies**: HARD-003 (operations.md coordination)

**Self-Review Focus**: Docs Fidelity (completeness), Security (thorough coverage), Maintainability (clear procedures)

---

## Task 5: Performance Benchmarking

**ID**: HARD-005
**Scope**: Validate performance at scale (100+ gists)
**Owner**: Agent E (Observability & Ops)
**Priority**: P2 (MEDIUM)
**Risk**: RESOLVED
**Status**: ✅ COMPLETE - 5 benchmarks, all passing, 4.92/5 score (59/60)
**Final Evidence**: reports/agents/agent-e/hard-005/run_20260111_205027/evidence.md

**Paths**:
- tests/benchmark_gist_performance.py (NEW)
- docs/performance.md (NEW)
- reports/agents/agent-e/hard-005/evidence.md (NEW)
- reports/agents/agent-e/hard-005/artifacts/benchmark_results.json (NEW)

**Criteria**:
1. Benchmark runs with 100+ gists
2. Cache hit rate measured (expect >80%)
3. Fetch time per gist documented (expect <2s)
4. Database query performance acceptable (expect <100ms)
5. Memory usage reasonable (expect <500MB for 100 gists)
6. Baseline documented for future regression testing

**Tests**: Benchmark script with performance assertions
**Docs**: docs/performance.md with baseline metrics

**Dependencies**: HARD-001 (needs working E2E for realistic test)

**Self-Review Focus**: Performance (realistic workload), Observability (metrics captured), Evidence (measurements documented)

---

## Parallel Execution Strategy

### Wave 1 (Start Immediately)
- **HARD-001** (Agent C) - BLOCKING, must complete first
- **HARD-003** (Agent B) - Can run in parallel
- **HARD-004** (Agent D) - Can run in parallel

### Wave 2 (After HARD-001 Complete) - READY TO EXECUTE
- **HARD-002** (Agent C) - ✅ COMPLETE (5.0/5)
- **HARD-003** (Agent B) - READY TO START
- **HARD-004** (Agent D) - READY TO START
- **HARD-005** (Agent E) - Depends on HARD-001 working E2E

### Wave 3 (Final Integration)
- Orchestrator reviews all self-reviews
- Routes back any <4/5 scores for hardening
- Merges when all pass

**Estimated Timeline**:
- Wave 1: 2-3 hours (parallel)
- Wave 2: 1-2 hours (parallel)
- Wave 3: 30 minutes (review + merge)

---

## Success Metrics

**Target**: All tasks complete with self-review scores ≥4/5

**Current Baseline** (from merge self-review):
- Thoroughness: 3.5/5 → Target 4.5/5 (HARD-001 evidence)
- Production grading: 3/5 → Target 4.5/5 (HARD-001, HARD-002)
- Testability: 3/5 → Target 4.5/5 (HARD-002)
- Robustness: 3/5 → Target 4.5/5 (HARD-002, HARD-003)
- Observability: 3/5 → Target 4.5/5 (HARD-005)

**Hard Gate**: No task proceeds to merge with ANY dimension <4/5

---

**Status**: Wave 1 COMPLETE, Wave 2 in progress
**Next Action**: Spawn HARD-003, HARD-004, HARD-005

---

## Update Log

### 2026-01-11 [Orchestrator Update]

**HARD-002 COMPLETE**:
- Agent C completed comprehensive test suite
- 54 tests, 100% passing (1.79s execution)
- 3 bugs discovered and fixed during testing
- Self-review score: 5.0/5 (all 12 dimensions)
- Evidence: reports/agents/agent-c/hard-002/evidence.md
- Commits: c475b88, 91d6dc1

**Wave 2 Status**:
- HARD-002: ✅ COMPLETE (5.0/5) - Integration tests
- HARD-003: ✅ COMPLETE (5.0/5) - Cache validation
- HARD-004: ✅ COMPLETE (5.0/5) - Security & ops docs
- HARD-005: ✅ COMPLETE (4.92/5) - Performance benchmarking

**Wave 2 Result**: ALL TASKS COMPLETE - 100% pass rate, zero routing-backs

**Next**: Wave 3 - Final orchestrator review and merge

---

### 2026-01-11 [Wave 2 Complete]

**HARD-003 COMPLETE** (Agent B):
- verify_cache() method (131 lines)
- 13 comprehensive tests (all passing)
- docs/operations.md cache section
- Self-review: 5.0/5 (all 12 dimensions)
- Evidence: reports/agents/agent-b/hard-003/run_20260111_203336/evidence.md

**HARD-004 COMPLETE** (Agent D):
- docs/security.md (527 lines)
- docs/operations.md (980 lines)
- README.md and configuration.md updated
- 30+ commands validated, 10+ queries tested
- Self-review: 5.0/5 (all 12 dimensions)
- Evidence: reports/agents/agent-d/hard-004/run_20260111_143000/evidence.md

**Wave 2 Summary**:
- All 4 tasks complete (HARD-002, HARD-003, HARD-004, HARD-005)
- Exceptional quality scores (avg 4.98/5)
- Zero routing-backs required
- Agent coordination seamless (B/D on operations.md)

### 2026-01-11 [Wave 2 Final - All Tasks Complete]

**HARD-005 COMPLETE** (Agent E):
- 5 comprehensive benchmarks (all passing)
- Performance baselines established (all targets exceeded)
- docs/performance.md (698 lines)
- tests/benchmark_gist_performance.py (590 lines)
- Self-review: 4.92/5 (59/60, only compatibility 4/5)
- Evidence: reports/agents/agent-e/hard-005/run_20260111_205027/evidence.md

**Wave 2 Complete**:
- 4/4 tasks complete (100% completion rate)
- Average score: 4.98/5 (exceeds 4.0/5 threshold)
- Zero tasks required routing-back
- All acceptance criteria met or exceeded
- Production-ready deliverables

**Quality Metrics**:
- HARD-002: 54 tests, 5.0/5 score
- HARD-003: 13 tests, 5.0/5 score
- HARD-004: 1507 lines docs, 5.0/5 score
- HARD-005: 5 benchmarks, 4.92/5 score

**Orchestrator Assessment**: ✅ READY FOR WAVE 3 (Final Integration Review)

---
---

# Task Backlog: Fix Remaining Snippet Failures

**Created**: 2026-01-12 13:52
**Plan Source**: plans/from_chat/20260112_134500_fix_remaining_snippets.md
**Orchestrator**: Snippet validation failure resolution

---

## Workstream Allocation (Max 5 parallel)

| Workstream | Owner Agent | Tasks | Priority | Can Start |
|------------|-------------|-------|----------|-----------|
| **WS1: Investigation** | A (Discovery) | T1, T2, T3 | HIGH | YES |
| **WS2: Context Inference Fix** | B (Implementation) | T4, T5, T6 | HIGH | After WS1 |
| **WS3: Pattern Enhancement** | B (Implementation) | T7, T8 | HIGH | After WS1 |
| **WS4: Integration Testing** | C (Tests) | T9, T10, T11 | HIGH | After WS2, WS3 |
| **WS5: Documentation** | D (Docs) | T12, T13 | MEDIUM | After WS4 |

---

## Task Details

### T1: Investigate Snippet 136
**ID**: T1
**Scope**: Investigation
**Owner**: Agent A (Discovery)
**Priority**: HIGH
**Status**: READY

**Impacted Paths**:
- `data/examples.db` (read snippet 136 data)
- `src/validation_orchestrator.py` (context inference logic)
- `src/persistent_fix_service.py` (context inference usage)

**Acceptance Criteria**:
- [ ] Original code retrieved from database
- [ ] Latest compilation errors retrieved (Run 29)
- [ ] Generated code with malformed structure retrieved
- [ ] Malformed structure confirmed (using inside class)
- [ ] Evidence document created with findings

**Risk**: LOW
**Tests**: Database query validation
**Docs**: `reports/agents/discovery/snippet_136_investigation/evidence.md`

**Commands**:
```bash
./venv/Scripts/python.exe -c "import sys; sys.path.insert(0, 'src'); from pathlib import Path; from database import Database; db = Database(Path('data/examples.db')); db.connect(); cursor = db._conn.execute('SELECT code_content FROM snippet_versions WHERE snippet_id = 136 AND version_type = \"original\"'); print('ORIGINAL:', cursor.fetchone()[0]); cursor = db._conn.execute('SELECT compiler_output FROM build_attempts WHERE run_id = 29 AND snippet_id = 136 ORDER BY attempted_at DESC LIMIT 1'); print('ERRORS:', cursor.fetchone()[0]); cursor = db._conn.execute('SELECT sv.code_content FROM build_attempts ba JOIN snippet_versions sv ON ba.version_id = sv.version_id WHERE ba.run_id = 29 AND ba.snippet_id = 136 ORDER BY ba.attempted_at DESC LIMIT 1'); print('GENERATED:', cursor.fetchone()[0])"
```

---

### T2: Locate Context Inference Logic
**ID**: T2
**Scope**: Code discovery
**Owner**: Agent A (Discovery)
**Priority**: HIGH
**Status**: READY

**Impacted Paths**:
- `src/validation_orchestrator.py` (likely location)
- `src/persistent_fix_service.py` (usage)
- `src/workspace_manager.py` (potential location)

**Acceptance Criteria**:
- [ ] Context inference code location identified
- [ ] Current wrapper generation logic documented
- [ ] enable_context_inference config flag found
- [ ] Gap analysis: current vs correct behavior
- [ ] Evidence document created

**Risk**: LOW
**Tests**: Code reading and analysis
**Docs**: `reports/agents/discovery/snippet_136_investigation/evidence.md` (append)

**Commands**:
```bash
grep -rn "context.*inference" src/ --include="*.py"
grep -rn "enable_context_inference" config/ src/
grep -rn "def.*wrap\|def.*infer" src/ --include="*.py"
```

---

### T3: Investigate Snippets 139 & 140
**ID**: T3
**Scope**: Investigation
**Owner**: Agent A (Discovery)
**Priority**: HIGH
**Status**: READY

**Impacted Paths**:
- `data/examples.db` (read snippets 139, 140 data)
- Run 29 build attempts and fix sessions

**Acceptance Criteria**:
- [ ] Original code retrieved for both snippets
- [ ] Compilation errors retrieved (Run 29)
- [ ] All LLM attempts and code evolution retrieved
- [ ] Error patterns identified and classified
- [ ] Required API patterns identified
- [ ] Evidence document created with patterns needed

**Risk**: MEDIUM (patterns may not be obvious)
**Tests**: Database query validation, pattern analysis
**Docs**: `reports/agents/discovery/snippets_139_140_investigation/evidence.md`

**Commands**:
```bash
./venv/Scripts/python.exe -c "import sys; sys.path.insert(0, 'src'); from pathlib import Path; from database import Database; db = Database(Path('data/examples.db')); db.connect(); for snippet_id in [139, 140]: print(f'\\n=== SNIPPET {snippet_id} ==='); cursor = db._conn.execute('SELECT code_content FROM snippet_versions WHERE snippet_id = ? AND version_type = \"original\"', (snippet_id,)); print('ORIGINAL:', cursor.fetchone()[0]); cursor = db._conn.execute('SELECT attempted_at, compiler_output FROM build_attempts WHERE run_id = 29 AND snippet_id = ? ORDER BY attempted_at', (snippet_id,)); print('ERRORS:'); [print(f'  Attempt {i+1}:', row[1][:200]) for i, row in enumerate(cursor.fetchall())]"
```

---

### T4-T13: [Full task definitions in plan file]
See `plans/from_chat/20260112_134500_fix_remaining_snippets.md` for complete task specifications.

---

## Progress Tracking

| Task | Status | Owner | Progress | Blockers |
|------|--------|-------|----------|----------|
| T1 | READY | A | 0% | None |
| T2 | READY | A | 0% | None |
| T3 | READY | A | 0% | None |
| T4 | BLOCKED | B | 0% | T1, T2 |
| T5 | BLOCKED | B | 0% | T4 |
| T6 | BLOCKED | B | 0% | T5 |
| T7 | BLOCKED | B | 0% | T3 |
| T8 | BLOCKED | B | 0% | T7 |
| T9 | BLOCKED | C | 0% | T5, T6, T7, T8 |
| T10 | BLOCKED | C | 0% | T9 |
| T11 | BLOCKED | C | 0% | T10 |
| T12 | BLOCKED | D | 0% | T10 |
| T13 | BLOCKED | D | 0% | T10, T12 |

---

## Critical Path

T1,T2,T3 → T4 → T5 → T6 + (T7 → T8) → T9 → T10 → T11 | T12 → T13

**Estimated Critical Path**: ~2.5 hours

---

**Status**: WS1 (Investigation) READY TO START
**Next Action**: Spawn Agent A for T1, T2, T3 (can run in parallel)

## Update — 2026-01-12 19:34 PKT

# Task Backlog: Telemetry & Auto-Commit Healing

**Created**: 2026-01-12 19:34
**Plan Sources**: `plans/healing/telemetry-fixes.md`, `plans/healing/auto-commit.md`
**Orchestrator**: Telemetry + auto-commit recovery

---

## Workstream Allocation (Max 5 parallel)

| Workstream | Owner Agent | Tasks | Priority | Can Start | Notes |
|------------|-------------|-------|----------|-----------|-------|
| **WS1: Telemetry Core** | B (Implementation) | TM-01 | P0 | YES | Shared `src/telemetry.py` changes; gate other telemetry tasks |
| **WS2: Auto-Commit Core** | A (Discovery/Implementation) | AC-01 | P0 | YES | Adds git staging + commit in patch flow |
| **WS3: Telemetry Config** | E (Observability/Ops) | TM-02 | P0 | AFTER TM-01 | Avoid merge conflicts in `src/telemetry.py` |
| **WS4: Telemetry Tests** | C (Tests) | TM-03 | P1 | AFTER TM-01, TM-02 | Tests depend on finalized telemetry API |
| **WS5: Auto-Commit Config** | D (Docs/Specs) | AC-02 | P1 | AFTER AC-01 | CLI changes share `src/cli.py` |

---

## Task TM-01: Implement record_timing()

**ID**: TM-01
**Scope**: Add timing metric recording + aggregation for telemetry
**Owner-Agent**: Agent B (Implementation)
**Priority**: P0 (Critical)
**Status**: COMPLETE (run_20260112_193512)

**Affected Paths**:
- `src/telemetry.py`
- `src/persistent_fix_service.py`
- `test_telemetry_timing.py`

**Acceptance Criteria**:
- `record_timing()` exists and no runtime `AttributeError`
- Timing metrics aggregated (min/max/avg/count) in `metrics.json`
- Timing events logged to NDJSON with `timing_recorded`
- HTTP API includes timing metrics in `metrics_json` when configured
- Tests pass: `pytest test_telemetry_timing.py -v`

**Risk**: HIGH (runtime crash blocker)
**Required Tests**: `pytest test_telemetry_timing.py -v`
**Required Docs/Specs**: `src/telemetry.py` docstrings aligned with `docs/local-telemetry.md`

---

## Task TM-02: Add HTTP API Configuration

**ID**: TM-02
**Scope**: Configure telemetry HTTP API integration (env + CLI)
**Owner-Agent**: Agent E (Observability & Ops)
**Priority**: P0 (Critical)
**Status**: COMPLETE (run_20260112_193512)
**Dependencies**: TM-01 (shared telemetry module)

**Affected Paths**:
- `src/cli.py`
- `src/telemetry.py`
- `.env.example`
- `test_telemetry_config.py`

**Acceptance Criteria**:
- Env vars + `--telemetry-url` supported with override hierarchy
- HTTP POST/PATCH per `docs/local-telemetry.md` schema
- Auth headers and timeout respected
- Idempotent POST and 429 handling are graceful
- Tests pass: `pytest test_telemetry_config.py -v`

**Risk**: HIGH (API integration required for telemetry)
**Required Tests**: `pytest test_telemetry_config.py -v`
**Required Docs/Specs**: `.env.example` updates, telemetry docstrings

---

## Task TM-03: Telemetry Validation Tests

**ID**: TM-03
**Scope**: Comprehensive telemetry test suite (95%+ coverage)
**Owner-Agent**: Agent C (Tests & Verification)
**Priority**: P1 (High)
**Status**: COMPLETE (run_20260112_193512)
**Dependencies**: TM-01, TM-02

**Affected Paths**:
- `tests/test_telemetry.py`
- `tests/conftest.py` (if needed)
- `tests/fixtures/telemetry/` (if needed)

**Acceptance Criteria**:
- 95%+ coverage on `src/telemetry.py`
- All context managers + lifecycle tested
- API schema compliance + idempotency + auth + rate limiting tested
- Tests pass: `pytest tests/test_telemetry.py -v --cov=src/telemetry`

**Risk**: MEDIUM (large test surface area)
**Required Tests**: `pytest tests/test_telemetry.py -v --cov=src/telemetry --cov-report=term-missing`
**Required Docs/Specs**: Tests act as spec for telemetry usage

---

## Task AC-01: Auto-Commit Core

**ID**: AC-01
**Scope**: Git staging + commit automation after patching
**Owner-Agent**: Agent A (Discovery & Architecture)
**Priority**: P0 (Critical)
**Status**: COMPLETE (run_20260112_193512)

**Affected Paths**:
- `src/patching_service.py`
- `src/cli.py`
- `test_patching_auto_commit.py`

**Acceptance Criteria**:
- `--auto-commit` stages modified files and creates commit
- Dry-run mode disables auto-commit
- Commit SHA captured and reported
- Graceful failure when git missing or commit fails
- Tests pass: `pytest test_patching_auto_commit.py -v`

**Risk**: MEDIUM (git operations in production)
**Required Tests**: `pytest test_patching_auto_commit.py -v`
**Required Docs/Specs**: CLI help text + docstrings for auto-commit behavior

---

## Task AC-02: Auto-Commit Configuration

**ID**: AC-02
**Scope**: Config hierarchy for auto-commit enablement
**Owner-Agent**: Agent D (Docs & Specs)
**Priority**: P1 (High)
**Status**: COMPLETE (run_20260112_193512)
**Dependencies**: AC-01 (core functionality)

**Affected Paths**:
- `src/cli.py`
- `config/families/zip.json`
- `.env.example`
- `test_auto_commit_config.py`

**Acceptance Criteria**:
- Hierarchy: CLI flag > family config > env var > default
- `--no-auto-commit` explicitly disables
- Config + env docs updated
- Tests pass: `pytest test_auto_commit_config.py -v`

**Risk**: LOW (config-only logic)
**Required Tests**: `pytest test_auto_commit_config.py -v`
**Required Docs/Specs**: `.env.example`, family config note

---

## Queued Tasks (Next Wave)

### TM-04: Extend Metric Support
**ID**: TM-04
**Owner-Agent**: Agent B (Implementation)
**Status**: COMPLETE (run_20260112_204632)
**Affected Paths**: `src/telemetry.py`, `test_telemetry_metrics.py`
**Required Tests**: `pytest test_telemetry_metrics.py -v`
**Required Docs/Specs**: telemetry docstrings (`docs/local-telemetry.md` alignment)

### AC-03: Smart Commit Messages + Telemetry Association
**ID**: AC-03
**Owner-Agent**: Agent E (Observability & Ops)
**Status**: COMPLETE (run_20260113_130448)
**Affected Paths**: `src/patching_service.py`, `src/cli.py`, `src/telemetry.py`, `test_commit_message_generation.py`
**Required Tests**: `pytest test_commit_message_generation.py -v`
**Required Docs/Specs**: telemetry commit association docstrings

### AC-04: Rollback Mechanism
**ID**: AC-04
**Owner-Agent**: Agent A (Discovery & Architecture)
**Status**: COMPLETE (run_20260113_131624)
**Affected Paths**: `src/cli.py`, `src/patching_service.py`, `src/database.py`, `schema.sql`, `test_patching_rollback.py`
**Required Tests**: `pytest test_patching_rollback.py -v`
**Required Docs/Specs**: CLI help text and rollback docstrings

## Update — 2026-01-12 20:07 PKT

- TM-01 completed by Agent B with timing metrics aggregation, persistent fix duration recording, and 4 passing tests.
- Evidence: `reports/agents/agent-b/TM-01/run_20260112_193512/evidence.md`

## Update — 2026-01-12 20:21 PKT

- TM-02 completed by Agent E with HTTP API configuration, CLI overrides, and 9 passing tests.
- TM-03 is now READY (TM-01 + TM-02 complete).
- Evidence: `reports/agents/agent-e/TM-02/run_20260112_193512/evidence.md`

## Update — 2026-01-12 20:28 PKT

- TM-03 completed by Agent C with 31 tests and 100% coverage on `src/telemetry.py`.
- Evidence: `reports/agents/agent-c/TM-03/run_20260112_193512/evidence.md`

## Update — 2026-01-12 20:35 PKT

- AC-01 completed by Agent A with auto-commit core logic and 5 passing tests.
- AC-02 is now READY (AC-01 complete).
- Evidence: `reports/agents/agent-a/AC-01/run_20260112_193512/evidence.md`

## Update — 2026-01-12 20:39 PKT

- AC-02 completed by Agent D with config hierarchy, env var documentation, and 4 passing tests.
- Evidence: `reports/agents/agent-d/AC-02/run_20260112_193512/evidence.md`

## Update — 2026-01-12 20:47 PKT

- TM-04 completed by Agent B with advanced metrics support and 5 passing tests.
- Evidence: `reports/agents/agent-b/TM-04/run_20260112_204632/evidence.md`

## Update — 2026-01-13 13:05 PKT

- AC-03 completed by Agent E with commit message generation and telemetry commit association.
- Evidence: `reports/agents/agent-e/AC-03/run_20260113_130448/evidence.md`

## Update — 2026-01-13 13:17 PKT

- AC-04 completed by Agent A with rollback mechanism and 3 passing tests.
- Evidence: `reports/agents/agent-a/AC-04/run_20260113_131624/evidence.md`

---
---

# Task Backlog: Comprehensive System Robustness

**Created**: 2026-01-13 15:30 PKT
**Plan Source**: C:\Users\prora\.claude\plans\agile-wiggling-pie.md (PART 2: COMPREHENSIVE ROBUSTNESS PLAN)
**Orchestrator**: Multi-family validation & robustness improvements
**Goal**: Make system robust enough to handle ANY .NET C# code across all families

---

## Executive Summary

**Context**: Current system has 50% verification rate (2/4 snippets on ZIP family). System fails on:
- Cross-domain APIs (Aspose + framework mixing)
- Modern .NET patterns (top-level statements, minimal APIs)
- Oscillating error loops
- Limited testing scope (only ZIP family)

**Goal**: Expand to 16 families (~2000-4000 snippets) and fix 5 fundamental limitations.

**Three-Phase Approach**:
1. **Phase 1**: Multi-Family Indexing & Sampling (Weeks 1-3) - 160 sample snippets
2. **Phase 2**: Robustness Improvements (Weeks 4-6) - 5 core system fixes
3. **Phase 3**: API Reference Optimization (Week 7) - Configuration enhancements

**Expected Outcome**: 50-65% verification rate across all families

---

## Workstream Allocation (Max 5 parallel)

| Workstream | Owner Agent | Tasks | Priority | Can Start |
|------------|-------------|-------|----------|-----------|
| **WS1: Multi-Family Setup** | A (Discovery) | ROB-01, ROB-02 | P0 | YES |
| **WS2: Sampling & Analysis** | C (Tests) | ROB-03, ROB-04 | P0 | After WS1 |
| **WS3: Namespace Isolation** | B (Implementation) | ROB-05, ROB-06 | P0 | After WS2 |
| **WS4: Modern .NET Support** | B (Implementation) | ROB-07, ROB-08 | P0 | Parallel with WS3 |
| **WS5: Loop Detection & Docs** | E (Observability) | ROB-09, ROB-10 | P1 | After WS3, WS4 |

---

## Phase 1: Multi-Family Indexing & Sampling Tasks

### Task ROB-01: Create Family Configurations (Tier 1) ✅ COMPLETE

**ID**: ROB-01
**Scope**: Create config files for 6 Tier 1 families (words, pdf, cells, slides, email, imaging)
**Owner-Agent**: Agent A (Discovery & Architecture)
**Priority**: P0 (Critical)
**Status**: COMPLETE (2026-01-13 15:42 PKT)
**Quality Score**: 4.96/5
**Risk**: LOW (configuration-only)
**Evidence**: [reports/agents/agent-a/ROB-01/run_20260113_153500/EVIDENCE.md](reports/agents/agent-a/ROB-01/run_20260113_153500/EVIDENCE.md)

**Affected Paths**:
- `config/families/words.json` (CREATED ✅)
- `config/families/pdf.json` (CREATED ✅)
- `config/families/cells.json` (CREATED ✅)
- `config/families/slides.json` (CREATED ✅)
- `config/families/email.json` (CREATED ✅)
- `config/families/imaging.json` (CREATED ✅)
- `config/global.json` (CREATED ✅)

**Acceptance Criteria**:
- [x] 6 family config files created with complete structure
- [x] Each config includes: content_pattern (kb path), nuget_config, code_defaults, persistent_fix settings
- [x] namespace_policy section added to each (whitelist mode)
- [x] global.json created with API reference path: `D:\onedrive\Documents\GitHub\aspose.net\content\references.aspose.net`
- [x] All configs validated (valid JSON, no syntax errors) - 7/7 passing
- [x] Evidence document with all file paths and validation

**Required Tests**: JSON validation, schema compliance check
**Required Docs/Specs**: `config/families/README.md` (update with new families)

**Template Reference** (from plan, lines 2188-2229):
```json
{
  "family": "{family}",
  "display_name": "Aspose.{Family} for .NET",
  "content_pattern": {
    "kb": "**/{family}/en/**/*.md"
  },
  "namespace_policy": {
    "mode": "whitelist",
    "allowed_namespaces": ["Aspose.{Family}", "System", "System.IO"]
  }
}
```

---

### Task ROB-02: Discovery & API Index Build (Tier 1) ✅ COMPLETE

**ID**: ROB-02
**Scope**: Run discovery for kb.aspose.net content + build API indexes for 6 Tier 1 families
**Owner-Agent**: Agent A (Discovery & Architecture)
**Priority**: P0 (Critical)
**Status**: COMPLETE (2026-01-13 16:05 PKT)
**Quality Score**: 4.92/5
**Risk**: MEDIUM (depends on content repository availability)
**Evidence**: [reports/agents/agent-a/ROB-02/run_20260113_154500/EVIDENCE.md](reports/agents/agent-a/ROB-02/run_20260113_154500/EVIDENCE.md)

**Affected Paths**:
- `data/examples.db` (UPDATED - pages, snippets tables: 345 KB pages, 1,301 KB snippets ✅)
- `data/examples.db` (UPDATED - api_reference table: 770 API classes, 3,456 API members ✅)
- Content: `D:\onedrive\Documents\GitHub\aspose.net\content\kb.aspose.net\{family}\en\` (VERIFIED ✅)
- API Ref: `D:\onedrive\Documents\GitHub\aspose.net\reference.aspose.net\{family}\en\` (VERIFIED ✅)

**Acceptance Criteria**:
- [x] Discovery completed for 6 families with kb.aspose.net content
- [x] Database query confirms page counts (actual: 6-95 pages per family based on real content)
- [x] Database query confirms snippet counts (actual: 22-484 per family based on real content)
- [x] API indexes built for all 6 families
- [x] API index stats query shows class counts (actual: 1-561 classes per family)
- [x] Evidence document with all discovery outputs and stats

**Commands** (from plan, lines 2252-2282):
```bash
# Discovery
python src/cli.py discover --family words --content-root "D:\onedrive\Documents\GitHub\aspose.net\content"
# ... repeat for pdf, cells, slides, email, imaging

# API Index Build
python src/cli.py build-api-index --family words --reference-root "D:\onedrive\Documents\GitHub\aspose.net\content\references.aspose.net"
# ... repeat for all families

# Verification
python -c "import sqlite3; conn = sqlite3.connect('data/examples.db'); cursor = conn.execute('SELECT family, COUNT(*) FROM pages WHERE site=\"kb\" GROUP BY family'); print(list(cursor.fetchall()))"
```

**Required Tests**: Discovery output validation, database integrity checks
**Required Docs/Specs**: Discovery stats report

---

### Task ROB-03: Sampling Strategy & Test Execution

**ID**: ROB-03
**Scope**: Execute sampling validation (15 snippets per Tier 1 family = 90 total)
**Owner-Agent**: Agent C (Tests & Verification)
**Priority**: P0 (Critical)
**Status**: READY (unblocked 2026-01-13 16:05 PKT - ROB-02 complete ✅)
**Risk**: HIGH (real LLM/API calls, long runtime ~30-60 min)

**Affected Paths**:
- `data/examples.db` (build_attempts, fix_sessions, snippet_versions - Run 31+)
- `artifacts/runs/run_YYYYMMDD_HHMMSS_*/` (validation artifacts)

**Acceptance Criteria**:
- [ ] 90 snippets validated (15 per family × 6 families)
- [ ] Validation completion rate ≥90% (no crashes)
- [ ] Database records created for all attempts
- [ ] Verification success rate measured per family
- [ ] Average iterations tracked per family
- [ ] Infinite loop rate calculated per family
- [ ] Evidence document with comprehensive stats

**Sampling Criteria** (from plan, lines 2288-2292):
- 40% Random samples
- 30% Complex snippets (multi-class usage, longer code)
- 30% Previously failed patterns

**Commands** (from plan, lines 2293-2318):
```bash
python src/cli.py validate --family words --max-snippets 15 --content-root "D:\onedrive\Documents\GitHub\aspose.net\content"
# ... repeat for each Tier 1 family
```

**Required Tests**: Validation orchestration test, sampling selection verification
**Required Docs/Specs**: Sampling report with per-family breakdowns

---

### Task ROB-04: Failure Pattern Analysis

**ID**: ROB-04
**Scope**: Analyze sampling results to identify systematic failure patterns
**Owner-Agent**: Agent C (Tests & Verification)
**Priority**: P0 (Critical)
**Status**: BLOCKED (needs ROB-03)
**Risk**: LOW (analysis-only)

**Affected Paths**:
- `reports/agents/agent-c/ROB-04/run_YYYYMMDD_HHMMSS/failure_analysis.md` (NEW)
- `reports/agents/agent-c/ROB-04/run_YYYYMMDD_HHMMSS/artifacts/failure_patterns.json` (NEW)

**Acceptance Criteria**:
- [ ] Failure distribution by family analyzed (query from plan lines 2325-2336)
- [ ] Common error patterns identified across families (query from plan lines 2338-2349)
- [ ] Top 5 error categories classified (API mismatches, structural, cross-domain, context)
- [ ] Systematic issues documented (not one-off failures)
- [ ] Recommendations for Phase 2 robustness improvements
- [ ] Evidence document with all query results and analysis

**Analysis Queries** (from plan, lines 2322-2349):
```sql
-- Failure Distribution
SELECT p.family, s.status, COUNT(*) as snippet_count,
       ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (PARTITION BY p.family), 1) as pct
FROM snippets s
JOIN pages p ON s.page_id = p.page_id
WHERE p.site = 'kb'
GROUP BY p.family, s.status;

-- Common Error Patterns
SELECT p.family, COUNT(DISTINCT s.snippet_id) as snippets_with_errors,
       SUBSTR(ba.compiler_output, 1, 100) as sample_error
FROM build_attempts ba
JOIN snippets s ON ba.snippet_id = s.snippet_id
JOIN pages p ON s.page_id = p.page_id
WHERE ba.success = 0 AND p.site = 'kb'
GROUP BY p.family, sample_error
ORDER BY snippets_with_errors DESC LIMIT 20;
```

**Red Flags** (from plan, lines 2380-2383):
- Infinite loop rate >70%
- Zero verifications after 15 samples
- Consistent "type not found" for core APIs

**Required Tests**: Query validation, pattern classification accuracy
**Required Docs/Specs**: Failure analysis report with recommendations

---

## Phase 2: System Robustness Improvement Tasks

### Task ROB-05: Implement Namespace Validator

**ID**: ROB-05
**Scope**: Create namespace validation system to prevent cross-domain API mixing
**Owner-Agent**: Agent B (Implementation)
**Priority**: P0 (Critical - fixes Snippet 139 failure mode)
**Status**: BLOCKED (needs ROB-04 analysis)
**Risk**: MEDIUM (integration with fix loop)

**Affected Paths**:
- `src/namespace_validator.py` (NEW - ~200 lines)
- `src/persistent_fix_service.py` (MODIFY - integrate validator after LLM fix)
- `src/ollama_integration.py` (MODIFY - add namespace policy to prompts)
- `config/families/zip.json` (MODIFY - add namespace_policy section)
- `tests/test_namespace_validator.py` (NEW - ~150 lines)

**Acceptance Criteria**:
- [ ] NamespaceValidator class implemented with validate_code() method
- [ ] Whitelist mode: only allowed namespaces permitted
- [ ] Blacklist mode: forbidden namespaces blocked
- [ ] Validation result includes violations + suggestions
- [ ] Integration in persistent_fix_service.py after LLM generates code
- [ ] Prompt enhancement includes namespace policy section
- [ ] Unit tests cover: whitelist enforcement, blacklist enforcement, suggestions
- [ ] Evidence document with test results and integration verification

**Implementation Reference** (from plan, lines 2398-2518):
- Class structure defined
- Integration points specified
- Config schema provided

**Required Tests**:
```bash
pytest tests/test_namespace_validator.py -v
# Expected: 10+ tests covering whitelist, blacklist, conditional allow
```

**Required Docs/Specs**: Namespace policy documentation in family config schema

---

### Task ROB-06: Test Namespace Validator with Snippet 139

**ID**: ROB-06
**Scope**: Validate that namespace validator prevents snippet 139 infinite loop
**Owner-Agent**: Agent C (Tests & Verification)
**Priority**: P0 (Critical)
**Status**: BLOCKED (needs ROB-05)
**Risk**: MEDIUM (depends on LLM behavior)

**Affected Paths**:
- `data/examples.db` (snippet 139 - reset to unverified)
- `artifacts/runs/run_YYYYMMDD_HHMMSS_*/` (Run 32+)
- `reports/agents/agent-c/ROB-06/run_YYYYMMDD_HHMMSS/evidence.md` (NEW)

**Acceptance Criteria**:
- [ ] Snippet 139 reset to unverified status
- [ ] Validation run with namespace validator enabled
- [ ] Namespace violations detected and logged
- [ ] LLM receives namespace policy in prompt
- [ ] Snippet 139 status changes to 'verified' (or iterations ≤5 if still needs-fix)
- [ ] No infinite loop (max 5 iterations vs previous 6+)
- [ ] Evidence document with full validation trace

**Expected Behavior** (from plan analysis):
- Validator catches `Microsoft.AspNetCore.Builder` usage
- Prompt includes explicit namespace policy
- LLM either removes forbidden using OR adds conditional pattern
- Compilation succeeds within 3-5 iterations

**Required Tests**: Integration test for snippet 139 validation
**Required Docs/Specs**: Validation report comparing Run 30 (failed) vs Run 32+ (with validator)

---

### Task ROB-07: Implement Code Pattern Detector

**ID**: ROB-07
**Scope**: Create pattern detector for modern .NET (top-level statements, minimal APIs)
**Owner-Agent**: Agent B (Implementation)
**Priority**: P0 (Critical - fixes Snippet 140 failure mode)
**Status**: BLOCKED (needs ROB-04 analysis)
**Risk**: MEDIUM (complex pattern detection logic)

**Affected Paths**:
- `src/code_pattern_detector.py` (NEW - ~250 lines)
- `src/persistent_fix_service.py` (MODIFY - replace _needs_context logic)
- `tests/test_pattern_detector.py` (NEW - ~150 lines)

**Acceptance Criteria**:
- [ ] CodePatternDetector class implemented with detect_pattern() method
- [ ] Detects 6 patterns: complete_program, top_level_statements, minimal_api, class_only, method_only, fragment
- [ ] Top-level statement detection: identifies C# 9+ patterns (var at root, await, etc.)
- [ ] Minimal API detection: identifies WebApplication.CreateBuilder patterns
- [ ] Returns CodeStructure with needs_wrapping + recommended_wrapper
- [ ] Integration in persistent_fix_service.py replaces _needs_context
- [ ] Unit tests cover all 6 pattern types + edge cases
- [ ] Evidence document with test results and pattern examples

**Implementation Reference** (from plan, lines 2526-2651):
- Enum structure defined
- Detection heuristics specified
- Integration approach provided

**Required Tests**:
```bash
pytest tests/test_pattern_detector.py -v
# Expected: 15+ tests covering all patterns, edge cases (comments, strings, mixed)
```

**Required Docs/Specs**: Pattern detection documentation in architecture.md

---

### Task ROB-08: Test Pattern Detector with Snippet 140

**ID**: ROB-08
**Scope**: Validate that pattern detector prevents snippet 140 wrapper errors
**Owner-Agent**: Agent C (Tests & Verification)
**Priority**: P0 (Critical)
**Status**: BLOCKED (needs ROB-07)
**Risk**: LOW (snippet 140 likely still unfixable due to runtime dependencies)

**Affected Paths**:
- `data/examples.db` (snippet 140 - reset to unverified)
- `artifacts/runs/run_YYYYMMDD_HHMMSS_*/` (Run 33+)
- `reports/agents/agent-c/ROB-08/run_YYYYMMDD_HHMMSS/evidence.md` (NEW)

**Acceptance Criteria**:
- [ ] Snippet 140 reset to unverified status
- [ ] Validation run with pattern detector enabled
- [ ] Pattern detected as TOP_LEVEL_STATEMENTS or FRAGMENT
- [ ] No class wrapper applied (if top-level detected)
- [ ] Compilation errors changed (no CS8803 wrapper errors)
- [ ] New error analysis: runtime dependency (app variable) vs wrapper issue
- [ ] Evidence document with before/after error comparison

**Expected Behavior** (from plan analysis):
- Pattern detector identifies top-level statements
- Context inference skips wrapping
- Snippet still fails BUT with different error (missing `app` variable, not wrapper error)
- Confirms pattern detector working correctly even if snippet unfixable

**Required Tests**: Integration test for snippet 140 validation
**Required Docs/Specs**: Validation report with error evolution analysis

---

### Task ROB-09: Enhanced Infinite Loop Detection

**ID**: ROB-09
**Scope**: Implement multi-strategy infinite loop detection (4 strategies)
**Owner-Agent**: Agent E (Observability & Ops)
**Priority**: P1 (High)
**Status**: BLOCKED (needs ROB-04 analysis)
**Risk**: LOW (enhancement to existing logic)

**Affected Paths**:
- `src/persistent_fix_service.py` (MODIFY - replace _detect_infinite_loop, lines 597-619)
- `tests/test_infinite_loop_detection.py` (NEW - ~100 lines)

**Acceptance Criteria**:
- [ ] Strategy 1: Identical errors (existing - keep working)
- [ ] Strategy 2: Oscillating errors (A→B→A→B pattern)
- [ ] Strategy 3: Error set repetition (same set of error codes repeated 3+)
- [ ] Strategy 4: No progress (error count not decreasing over 3 iterations)
- [ ] All strategies integrated in _detect_infinite_loop method
- [ ] Telemetry logs which strategy triggered
- [ ] Unit tests cover all 4 strategies + combinations
- [ ] Evidence document with strategy effectiveness analysis

**Implementation Reference** (from plan, lines 2653-2729):
- 4 strategies defined
- Code structure provided

**Required Tests**:
```bash
pytest tests/test_infinite_loop_detection.py -v
# Expected: 8+ tests (2 per strategy)
```

**Required Docs/Specs**: Infinite loop detection documentation in operations.md

---

### Task ROB-10: Documentation & Summary

**ID**: ROB-10
**Scope**: Update architecture docs and create comprehensive summary report
**Owner-Agent**: Agent D (Docs & Specs)
**Priority**: P1 (High)
**Status**: BLOCKED (needs ROB-05, ROB-07, ROB-09 complete)
**Risk**: LOW (documentation-only)

**Affected Paths**:
- `docs/validation.md` (UPDATE - add namespace validation, pattern detection sections)
- `docs/architecture.md` (UPDATE - add robustness improvements overview)
- `reports/COMPREHENSIVE_ROBUSTNESS_SUMMARY.md` (NEW)

**Acceptance Criteria**:
- [ ] validation.md updated with namespace validator section
- [ ] validation.md updated with pattern detector section
- [ ] validation.md updated with enhanced loop detection section
- [ ] architecture.md updated with robustness layer diagram
- [ ] Comprehensive summary report created with:
  - Multi-family sampling results (90 snippets)
  - Verification rate improvement (before/after)
  - Snippet 139 resolution (namespace validator)
  - Snippet 140 analysis (pattern detector behavior)
  - Infinite loop rate reduction
- [ ] Evidence document with all doc updates validated

**Required Tests**: Documentation accuracy verification, link checking
**Required Docs/Specs**: Self-contained (creating documentation)

---

## Phase 3: API Reference Optimization (Optional - If Time Permits)

**Note**: Phase 3 tasks (global config, path discovery, token budget management) are lower priority. Only execute if Phase 1-2 complete successfully AND time allows.

---

## Parallel Execution Strategy

### Wave 1: Multi-Family Setup (Start Immediately)
- **ROB-01** (Agent A) - Family configs (2-3 hours)
- **ROB-02** (Agent A) - Discovery & API indexes (3-4 hours)

### Wave 2: Sampling & Analysis (After Wave 1)
- **ROB-03** (Agent C) - Sample validation (1-2 hours runtime)
- **ROB-04** (Agent C) - Failure analysis (1 hour)

### Wave 3: Robustness Implementation (After Wave 2)
- **ROB-05** (Agent B) - Namespace validator (2-3 hours)
- **ROB-07** (Agent B) - Pattern detector (2-3 hours) - PARALLEL
- **ROB-09** (Agent E) - Loop detection (1-2 hours) - PARALLEL

### Wave 4: Integration Testing (After Wave 3)
- **ROB-06** (Agent C) - Test snippet 139 with validator (30 min)
- **ROB-08** (Agent C) - Test snippet 140 with pattern detector (30 min)

### Wave 5: Documentation (After Wave 4)
- **ROB-10** (Agent D) - Comprehensive docs (2-3 hours)

**Total Estimated Time**: ~18-24 hours (spread over 2-3 weeks)

---

## Success Metrics

### Primary Metrics (Must Achieve)
- [ ] 16 families indexed in database (kb.aspose.net content)
- [ ] 90 sample snippets validated with comprehensive stats
- [ ] Namespace validator operational (snippet 139 improved)
- [ ] Pattern detector operational (snippet 140 no wrapper errors)
- [ ] Enhanced loop detection catching oscillations

### Secondary Metrics (Target)
- [ ] Verification rate: 25% → 50-65% (across sampled snippets)
- [ ] Average iterations: 5.0 → 3.0
- [ ] Infinite loop rate: 50% → 20-30%

### Quality Gate
**Threshold**: 4.0/5 minimum on ALL 12 dimensions for each task
**Current Pass Rate Target**: 100% (no routing-backs)

---

## Risk Assessment

### High Risks
- **ROB-02**: Content repository may be unavailable or paths incorrect
  - Mitigation: Validate paths first, have fallback manual discovery
- **ROB-03**: Long runtime for 90 snippets (~30-60 min)
  - Mitigation: Run in background, monitor progress, stop early if catastrophic failure

### Medium Risks
- **ROB-05, ROB-07**: Integration complexity may introduce regressions
  - Mitigation: Comprehensive unit tests, integration tests on known snippets

### Low Risks
- **ROB-01, ROB-10**: Configuration and documentation tasks
  - Mitigation: Standard validation, no code execution

---

**Status**: ROB-01 READY TO START
**Next Action**: Spawn Agent A for ROB-01 (family configurations)

---
---

# Task Backlog: Automatic NuGet Dependency Resolution

**Created**: 2026-01-13 20:00 PKT
**Plan Source**: C:\Users\prora\.claude\plans\agile-wiggling-pie.md (PART 3: AUTOMATIC NUGET DEPENDENCY RESOLUTION SYSTEM)
**Orchestrator**: Dependency resolution system to solve PDF family 0% success rate
**Context**: User feedback from ROB-08 - "system should be able to get all deps to test a given code"

---

## Executive Summary

**Critical Problem**: PDF family has 0% success rate (0/15 snippets) due to missing NuGet packages (System.Net.Http, Newtonsoft.Json, System.Data, Azure.Storage.Blobs). Current system only installs packages from static family configs. Code uses these namespaces (allowed by namespace policy) but packages aren't in `.csproj`.

**Root Cause**: Namespace policy allows namespaces but doesn't ensure corresponding packages are installed. No dynamic package detection or installation.

**Solution**: Three-tier automatic dependency resolution system:
- **Tier 1** (Immediate): Add missing packages to PDF config → 20-40% improvement (1 hour, zero risk)
- **Tier 2** (Core): Automatic detection and dynamic installation → 60-80% success (2-3 weeks)
- **Tier 3** (Future): Intelligent mapping with NuGet API → 90%+ success

---

## Workstream Allocation (Max 5 parallel)

| Workstream | Owner Agent | Tasks | Priority | Can Start |
|------------|-------------|-------|----------|-----------|
| **WS1: Quick Fix** | B (Implementation) | DEP-01 | P0 | YES (IMMEDIATE) |
| **WS2: Core System** | B (Implementation) | DEP-02 | P0 | After DEP-01 results |

---

## Tier 1: Static Configuration (Immediate Fix)

### Task DEP-01: Update PDF Configuration with Missing Packages

**ID**: DEP-01
**Scope**: Add 4 missing NuGet packages to `config/families/pdf.json`
**Owner-Agent**: Agent B (Implementation)
**Priority**: P0 (CRITICAL - Immediate execution)
**Status**: READY TO START
**Risk**: ZERO (additive change only, no code modifications)
**Estimated Time**: 5-10 minutes
**Expected Impact**: PDF success rate 0% → 20-40% (3-6 snippets verified)

**Affected Paths**:
- `config/families/pdf.json` (UPDATE - line 18: `additional_packages` array)

**Current State** (line 18 of pdf.json):
```json
"additional_packages": [],
```

**Required Change**:
```json
"additional_packages": [
  {"name": "System.Net.Http", "version": "4.3.4"},
  {"name": "Newtonsoft.Json", "version": "13.0.3"},
  {"name": "System.Data.SqlClient", "version": "4.8.6"},
  {"name": "Azure.Storage.Blobs", "version": "12.19.1"}
],
```

**Acceptance Criteria**:
- [x] File `config/families/pdf.json` exists and has been read
- [ ] Line 18 updated with 4 additional packages (System.Net.Http, Newtonsoft.Json, System.Data.SqlClient, Azure.Storage.Blobs)
- [ ] JSON validated (no syntax errors)
- [ ] Git diff shows only `additional_packages` array changed
- [ ] Validation run executed: `python src/cli.py validate --family pdf --max-snippets 15 --content-root "D:\onedrive\Documents\GitHub\aspose.net\content"`
- [ ] Database query confirms success rate improvement: 0% → 20-40%
- [ ] Evidence document created with before/after stats

**Verification Commands**:
```bash
# Validation run
python src/cli.py validate --family pdf --content-root "D:\onedrive\Documents\GitHub\aspose.net\content" --max-snippets 15

# Check success rate
sqlite3 data/examples.db "SELECT status, COUNT(*) as count FROM snippets s JOIN pages p ON s.page_id = p.page_id WHERE p.family='pdf' AND s.run_id=(SELECT MAX(run_id) FROM runs) GROUP BY status;"

# Expected output:
# verified | 3-6   (was 0)
# needs-fix | 9-12  (was 15)
```

**Success Criteria**:
- At least 3 PDF snippets now verify successfully (20% improvement)
- CS0246 errors for System.Net.Http, Newtonsoft.Json resolved
- No regressions in other families

**Required Tests**: JSON validation, validation run execution, database query verification
**Required Docs/Specs**: Evidence document with run stats, CHANGELOG.md entry

**Plan Reference**: agile-wiggling-pie.md lines 2174-2226

---

## Tier 2: Dynamic Detection & Installation (2-3 weeks)

### Task DEP-02: Implement Automatic Dependency Resolution System

**ID**: DEP-02
**Scope**: Build DependencyResolver service with namespace-to-package mapping, dynamic .csproj updates, database tracking
**Owner-Agent**: Agent B (Implementation)
**Priority**: P0 (CRITICAL - Core system improvement)
**Status**: PENDING (awaits DEP-01 results for baseline comparison)
**Risk**: MEDIUM (database changes, integration complexity, performance impact)
**Estimated Time**: 2-3 weeks (16-20 hours)
**Expected Impact**: PDF success rate 20-40% → 60-80% (9-12 snippets verified)

**Affected Paths**:
- `migrations/006_dependency_resolution.sql` (NEW - ~60 lines) - Database schema for namespace mappings
- `src/dependency_resolver.py` (NEW - ~400 lines) - Core resolution service
- `src/seed_namespace_mappings.py` (NEW - ~50 lines) - Initial data seeding
- `tests/test_dependency_resolver.py` (NEW - ~150 lines) - Unit tests
- `src/validation_orchestrator.py` (MODIFY - add Stage 2.5 after line 115) - Integration point
- `src/workspace_manager.py` (REFERENCE - lines 67-111) - .csproj generation logic
- `src/namespace_validator.py` (REFERENCE) - Reuse `_extract_usings()` method
- `config/families/pdf.json` (MODIFY - add `dependency_resolution` section)
- `src/database.py` (MODIFY - add query methods for new tables)

**Architecture**:
```
ValidationOrchestrator
    ↓
[Namespace Validation] (existing)
    ↓
[Stage 2.5: Dependency Resolution] ← NEW
    ├─ Extract using statements (reuse namespace_validator.py)
    ├─ Map namespaces to packages (NamespaceToPackageMapper)
    ├─ Update .csproj dynamically (DependencyResolver._update_csproj)
    └─ Run dotnet restore
    ↓
[Pattern-based pre-fix] (existing)
```

**Database Schema** (migrations/006_dependency_resolution.sql):
```sql
-- Namespace to Package mapping table
CREATE TABLE IF NOT EXISTS namespace_to_package (
    mapping_id INTEGER PRIMARY KEY AUTOINCREMENT,
    namespace TEXT NOT NULL,
    package_name TEXT NOT NULL,
    package_version TEXT,
    source TEXT NOT NULL CHECK(source IN ('bcl', 'manual', 'inference')),
    confidence REAL DEFAULT 1.0,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(namespace, package_name)
);

CREATE INDEX IF NOT EXISTS idx_namespace_lookup ON namespace_to_package(namespace);

-- Dependency resolution tracking per snippet
CREATE TABLE IF NOT EXISTS dependency_resolutions (
    resolution_id INTEGER PRIMARY KEY AUTOINCREMENT,
    snippet_id INTEGER NOT NULL,
    namespace TEXT NOT NULL,
    package_name TEXT,
    package_version TEXT,
    resolution_status TEXT NOT NULL CHECK(resolution_status IN ('detected', 'resolved', 'failed', 'bcl')),
    detected_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (snippet_id) REFERENCES snippets(snippet_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_dep_resolution_snippet ON dependency_resolutions(snippet_id);
```

**Core Classes**:

1. **NamespaceToPackageMapper** (src/dependency_resolver.py):
   - `BCL_NAMESPACES` set (System, System.IO, etc. - no package needed)
   - `HEURISTIC_MAPPINGS` dict (System.Net.Http → package mapping with confidence)
   - `map_namespace(namespace: str) -> DependencyResolution`
   - Returns: namespace, package_name, package_version, status (bcl/resolved/unknown), source, confidence

2. **DependencyResolver** (src/dependency_resolver.py):
   - `analyze_and_resolve(snippet_id: int, code: str) -> Tuple[bool, List[DependencyResolution]]`
   - `_extract_namespaces(code: str) -> List[str]` (reuse from namespace_validator.py)
   - `_update_csproj(packages: List[Tuple[str, str]]) -> bool` (modify .csproj, invalidate build stamp, run dotnet restore)
   - `_record_resolution(snippet_id: int, res: DependencyResolution)` (insert into dependency_resolutions table)

**Initial Mappings** (src/seed_namespace_mappings.py):
```python
MAPPINGS = [
    ('System.Net.Http', 'System.Net.Http', '4.3.4', 'manual', 1.0),
    ('System.Net.Http.Headers', 'System.Net.Http', '4.3.4', 'manual', 1.0),
    ('System.Data.SqlClient', 'System.Data.SqlClient', '4.8.6', 'manual', 1.0),
    ('Newtonsoft.Json', 'Newtonsoft.Json', '13.0.3', 'manual', 1.0),
    ('Newtonsoft.Json.Linq', 'Newtonsoft.Json', '13.0.3', 'manual', 1.0),
    ('Azure.Storage.Blobs', 'Azure.Storage.Blobs', '12.19.1', 'manual', 1.0),
]
```

**Integration Point** (src/validation_orchestrator.py, after line 115):
```python
# Stage 2.5: Dependency Resolution
dep_config = self.family_config.get('dependency_resolution', {})
if dep_config.get('enabled', False):
    result['stages_completed'].append('dependency_resolution')

    resolved, resolutions = self.dependency_resolver.analyze_and_resolve(
        snippet_id, original_code
    )

    if not resolved:
        result['status'] = 'needs-fix'
        result['message'] = 'Dependency resolution failed'
        self.db.update_snippet(snippet_id, status='needs-fix')
        return result

    resolved_count = len([r for r in resolutions if r.status == 'resolved'])
    if resolved_count > 0:
        self.db.log_event(
            run_id, 'dependencies_resolved', 'info',
            f'Resolved {resolved_count} dependencies for snippet {snippet_id}'
        )
```

**Configuration Update** (config/families/pdf.json, add after persistent_fix section):
```json
"dependency_resolution": {
  "enabled": true,
  "confidence_threshold": 0.7
}
```

**Acceptance Criteria**:
- [ ] Database migration created and applied successfully
- [ ] namespace_to_package table seeded with 6 initial mappings
- [ ] NamespaceToPackageMapper class implemented with BCL detection and heuristic mapping
- [ ] DependencyResolver class implemented with analyze_and_resolve() method
- [ ] .csproj dynamic update working (adds PackageReference, invalidates build stamp, runs dotnet restore)
- [ ] Integration in ValidationOrchestrator Stage 2.5 complete
- [ ] PDF config updated with dependency_resolution.enabled = true
- [ ] Unit tests pass: `pytest tests/test_dependency_resolver.py -v` (10+ tests)
- [ ] End-to-end validation shows 60-80% PDF success rate
- [ ] Database queries confirm dependency resolutions tracked

**Verification Commands**:
```bash
# Apply migration
sqlite3 data/examples.db < migrations/006_dependency_resolution.sql

# Seed mappings
python src/seed_namespace_mappings.py

# Verify seeding
sqlite3 data/examples.db "SELECT namespace, package_name FROM namespace_to_package;"

# Run full PDF validation
python src/cli.py validate --family pdf --content-root "D:\onedrive\Documents\GitHub\aspose.net\content"

# Check success rate
sqlite3 data/examples.db "
SELECT
  s.status,
  COUNT(*) as count,
  ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM snippets s2 JOIN pages p2 ON s2.page_id=p2.page_id WHERE p2.family='pdf' AND s2.run_id=(SELECT MAX(run_id) FROM runs)), 1) as pct
FROM snippets s
JOIN pages p ON s.page_id = p.page_id
WHERE p.family='pdf' AND s.run_id=(SELECT MAX(run_id) FROM runs)
GROUP BY s.status;
"

# Check dependency resolutions
sqlite3 data/examples.db "
SELECT
  resolution_status,
  COUNT(*) as count
FROM dependency_resolutions
WHERE snippet_id IN (SELECT snippet_id FROM snippets s JOIN pages p ON s.page_id=p.page_id WHERE p.family='pdf')
GROUP BY resolution_status;
"

# Expected results:
# Success rate: 60-80% (9-12 verified)
# Resolutions: resolved (60%), bcl (30%), unknown (10%)
```

**Success Criteria**:
- At least 9 PDF snippets verify successfully (60% improvement from baseline)
- Automatic package detection works for 80%+ of required packages
- No performance regression (< 100ms overhead per snippet for analysis)
- No false positives (BCL namespaces not triggering package installs)

**Dependencies**: DEP-01 (need baseline metrics for comparison)

**Required Tests**:
```bash
pytest tests/test_dependency_resolver.py -v
# Expected: 10+ tests covering:
#   - BCL namespace detection (System.IO should not require package)
#   - Heuristic mapping (System.Net.Http → package)
#   - Unknown namespace handling
#   - .csproj update mechanics
#   - Database recording
```

**Required Docs/Specs**:
- Evidence document with architecture diagram
- Verification results comparing Tier 1 baseline to Tier 2 results
- Performance metrics (analysis time per snippet)
- CHANGELOG.md entry with before/after success rates

**Plan Reference**: agile-wiggling-pie.md lines 2230-2741

---

## Tier 3: Intelligent Mapping (Future Enhancement - Not Planned Yet)

**Note**: Tier 3 (NuGet API integration, ML-based inference, community mapping) is planned but not scheduled. Will be considered after Tier 2 success evaluation.

---

## Critical Path

DEP-01 (5 min) → Validation (15 min) → Analysis (10 min) → DEP-02 Decision

**DEP-02 Execution Path** (if approved):
Week 1: Database migration + seed + NamespaceToPackageMapper (8 hours)
Week 2: DependencyResolver + integration (8 hours)
Week 3: Testing + verification + docs (4 hours)

**Total Estimated Time**:
- Tier 1: 30 minutes
- Tier 2: 20 hours (spread over 2-3 weeks)

---

## Success Metrics

| Metric | Baseline | Tier 1 Target | Tier 2 Target |
|--------|----------|---------------|---------------|
| PDF Success Rate | 0% (0/15) | 20-40% (3-6/15) | 60-80% (9-12/15) |
| Packages Auto-Detected | 0 | 4 (manual) | 10-15 (automatic) |
| Manual Intervention | Always | Reduced | Minimal |
| Avg Resolution Time | N/A | N/A | 50-100ms |

---

## Risk Assessment

### Tier 1 Risks (DEP-01)
- **Risk**: ZERO - Only modifying config file, no code changes
- **Rollback**: Revert git commit if issues occur
- **Validation Time**: 15 minutes for re-validation

### Tier 2 Risks (DEP-02)
- **HIGH RISK**: .csproj modification during validation - file corruption possible
  - **Mitigation**: Backup .csproj before modification, validate XML structure, test in isolated workspace
- **MEDIUM RISK**: Database schema changes - migration failure could corrupt database
  - **Mitigation**: Backup database before migration, test migration on copy first, document rollback SQL
- **MEDIUM RISK**: Performance impact - analysis adds 50-100ms per snippet
  - **Mitigation**: Cache mappings, only analyze when needed, add timeout safeguards
- **LOW RISK**: Incorrect package mappings - wrong packages installed
  - **Mitigation**: Use confidence threshold (0.7), manual review for low confidence, comprehensive unit tests

---

## Rollback Plan

### Tier 1 Rollback:
```bash
# Revert config change
git checkout HEAD -- config/families/pdf.json

# Re-run validation to confirm baseline
python src/cli.py validate --family pdf --max-snippets 15
```

### Tier 2 Rollback:
```bash
# Disable dependency resolution in config
# Edit config/families/pdf.json: "enabled": false

# Database rollback (if needed)
sqlite3 data/examples.db "DROP TABLE IF EXISTS dependency_resolutions;"
sqlite3 data/examples.db "DROP TABLE IF EXISTS namespace_to_package;"

# Remove schema version entry
sqlite3 data/examples.db "DELETE FROM schema_version WHERE version = 6;"
```

---

**Status**: DEP-01 READY FOR IMMEDIATE EXECUTION (P0 - CRITICAL)
**Next Action**: Execute DEP-01 (5 minutes) → Run validation (15 minutes) → Analyze results (10 minutes) → Decision point for DEP-02

---
---

# Task Backlog: src/ Folder Reorganization

**Created**: 2026-01-14 14:35
**Plan Source**: C:\Users\prora\.claude\plans\streamed-hatching-blum.md
**Orchestrator**: ORCHESTRATOR workflow - src/ folder restructuring
**Goal**: Reorganize 25 flat Python files into hybrid package structure

---

## Executive Summary

**Context**: src/ folder contains 25 Python files in flat structure causing:
- Too many files in one place (cognitive overload)
- Unclear module boundaries
- Mixing of concerns (CLI + infrastructure + business logic)

**Solution**: Hybrid package structure with 7 top-level packages:
- Shallow organization for simple areas (core/, discovery/, api_reference/, llm/, patching/)
- Deep 3-level nesting for complex validation pipeline (validation/analysis/, validation/fixing/, validation/workspace/)

**Expected Outcome**: Reduced cognitive load, clear module boundaries, scalable architecture

---

## Workstream Allocation (Max 5 parallel)

| Workstream | Owner Agent | Tasks | Priority | Can Start |
|------------|-------------|-------|----------|-----------|
| **WS1: Infrastructure Setup** | B (Implementation) | REORG-01 | P0 | YES |
| **WS2: Core & LLM Migration** | B (Implementation) | REORG-02 | P0 | After WS1 |
| **WS3: Validation Migration** | B (Implementation) | REORG-03 | P0 | After WS2 |
| **WS4: Peripheral Migration** | B (Implementation) | REORG-04 | P0 | After WS2 (parallel with WS3) |
| **WS5: Testing & Verification** | C (Tests) | REORG-05 | P0 | After WS3, WS4 |

---

## Phase 1: Infrastructure Setup

### Task REORG-01: Create Directory Structure & __init__.py Files

**ID**: REORG-01
**Scope**: Create all directories and populate __init__.py exports for clean imports
**Owner-Agent**: Agent B (Implementation)
**Priority**: P0 (Critical - foundation for all other tasks)
**Status**: READY TO START
**Risk**: LOW (directory creation only)
**Estimated Time**: 30 minutes

**Affected Paths**:
- `src/core/__init__.py` (NEW)
- `src/discovery/__init__.py` (NEW)
- `src/validation/__init__.py` (NEW)
- `src/validation/analysis/__init__.py` (NEW)
- `src/validation/fixing/__init__.py` (NEW)
- `src/validation/workspace/__init__.py` (NEW)
- `src/api_reference/__init__.py` (NEW)
- `src/llm/__init__.py` (NEW)
- `src/patching/__init__.py` (NEW)
- `src/legacy/__init__.py` (NEW)
- `src/setup/__init__.py` (NEW)

**Acceptance Criteria**:
- [ ] All 11 directories created
- [ ] All 11 `__init__.py` files created with proper exports
- [ ] Exports match plan specification (core exports Database/Telemetry, validation exports orchestrator, etc.)
- [ ] No syntax errors in any `__init__.py` file
- [ ] Evidence document with directory tree

**Required Tests**: Python import test from each `__init__.py`
**Required Docs/Specs**: None (infrastructure)

**Directory Structure**:
```
src/
├── core/__init__.py
├── discovery/__init__.py
├── validation/
│   ├── __init__.py
│   ├── analysis/__init__.py
│   ├── fixing/__init__.py
│   └── workspace/__init__.py
├── api_reference/__init__.py
├── llm/__init__.py
├── patching/__init__.py
├── legacy/__init__.py
└── setup/__init__.py
```

**Evidence Commands**:
```bash
# Verify directory structure
tree src/ -L 3

# Test imports
python -c "import src.core"
python -c "import src.validation.analysis"
```

---

## Phase 2: File Migration

### Task REORG-02: Migrate Core Infrastructure & LLM Files

**ID**: REORG-02
**Scope**: Move leaf files (no dependencies on other src/ modules)
**Owner-Agent**: Agent B (Implementation)
**Priority**: P0 (Critical - foundation dependencies)
**Status**: BLOCKED (needs REORG-01)
**Risk**: LOW (leaf files have minimal import changes)
**Estimated Time**: 45 minutes

**Files to Move** (4 files):
1. `src/database.py` → `src/core/database.py`
2. `src/telemetry.py` → `src/core/telemetry.py`
3. `src/config_utils.py` → `src/core/config_utils.py`
4. `src/ollama_integration.py` → `src/llm/ollama_integration.py`

**Acceptance Criteria**:
- [ ] 4 files moved to new locations via git mv
- [ ] Import statements updated (no `from database import`, now `from src.core import Database`)
- [ ] Files still importable from original locations (Python can find them)
- [ ] No syntax errors or missing imports
- [ ] Evidence document with git diff showing moves

**Import Changes**:
- database.py: No internal src/ imports (leaf file)
- telemetry.py: Update `from database import` → `from src.core.database import`
- config_utils.py: No src/ imports
- ollama_integration.py: No src/ imports

**Required Tests**: Import validation for each moved file
**Required Docs/Specs**: None

**Evidence Commands**:
```bash
# Verify moves
git status

# Test imports
python -c "from src.core import Database, TelemetryClient"
python -c "from src.llm import OllamaClient"
```

---

### Task REORG-03: Migrate Validation Pipeline Files

**ID**: REORG-03
**Scope**: Move validation-related files (9 files) with complex dependencies
**Owner-Agent**: Agent B (Implementation)
**Priority**: P0 (Critical - largest subsystem)
**Status**: BLOCKED (needs REORG-02)
**Risk**: MEDIUM (many cross-file dependencies)
**Estimated Time**: 2 hours

**Files to Move** (9 files):
1. `src/validation_orchestrator.py` → `src/validation/orchestrator.py` (RENAME!)
2. `src/code_pattern_detector.py` → `src/validation/analysis/code_pattern_detector.py`
3. `src/pattern_registry.py` → `src/validation/analysis/pattern_registry.py`
4. `src/namespace_validator.py` → `src/validation/analysis/namespace_validator.py`
5. `src/persistent_fix_service.py` → `src/validation/fixing/persistent_fix_service.py`
6. `src/dependency_resolver.py` → `src/validation/fixing/dependency_resolver.py`
7. `src/workspace_manager.py` → `src/validation/workspace/workspace_manager.py`

**Acceptance Criteria**:
- [ ] 9 files moved (7 moved + 1 renamed)
- [ ] Import statements updated to use new structure:
  - Absolute imports for cross-package: `from src.core import Database`
  - Relative imports within validation: `from ..workspace import WorkspaceManager`
- [ ] validation_orchestrator.py renamed to orchestrator.py
- [ ] All imports functional (no ImportError)
- [ ] Evidence document with detailed import changes

**Complex Import Updates**:

**orchestrator.py** (was validation_orchestrator.py):
- OLD: `from database import`, `from telemetry import`, `from workspace_manager import`
- NEW:
  ```python
  from src.core import Database, TelemetryClient
  from src.llm import OllamaClient
  from src.api_reference import ApiReferenceService
  from .analysis import PatternRegistry, NamespaceValidator
  from .fixing import PersistentFixService, DependencyResolver
  from .workspace import WorkspaceManager
  ```

**persistent_fix_service.py**:
- OLD: `from workspace_manager import`, `from ollama_integration import`
- NEW:
  ```python
  from src.core import Database, TelemetryClient
  from src.llm import OllamaClient
  from src.api_reference import ApiReferenceService
  from ..workspace import WorkspaceManager
  from ..analysis import CodePatternDetector
  ```

**Required Tests**: Import tests for each file, validation pipeline smoke test
**Required Docs/Specs**: None

**Evidence Commands**:
```bash
# Verify moves
git status | grep validation

# Test imports
python -c "from src.validation import ValidationOrchestrator"
python -c "from src.validation.analysis import PatternRegistry"
python -c "from src.validation.fixing import PersistentFixService"
```

---

### Task REORG-04: Migrate Peripheral Files (Discovery, API, Patching, Legacy)

**ID**: REORG-04
**Scope**: Move remaining files (15 files) - discovery, api_reference, patching, legacy, setup
**Owner-Agent**: Agent B (Implementation)
**Priority**: P0 (Critical)
**Status**: BLOCKED (needs REORG-02 - can run parallel with REORG-03)
**Risk**: LOW-MEDIUM (simpler dependencies than validation)
**Estimated Time**: 1.5 hours

**Files to Move** (15 files):

**Discovery** (4 files):
1. `src/discovery_service.py` → `src/discovery/discovery_service.py`
2. `src/snippet_locator.py` → `src/discovery/snippet_locator.py`
3. `src/page_scanner.py` → `src/discovery/page_scanner.py`
4. `src/gist_service.py` → `src/discovery/gist_service.py`

**API Reference** (2 files):
5. `src/api_reference_service.py` → `src/api_reference/api_reference_service.py`
6. `src/api_index_builder.py` → `src/api_reference/api_index_builder.py`

**Patching** (3 files):
7. `src/patching_service.py` → `src/patching/patching_service.py`
8. `src/placeholder_patcher.py` → `src/patching/placeholder_patcher.py`
9. `src/gist_publisher.py` → `src/patching/gist_publisher.py`

**Legacy** (3 files):
10. `src/example_fixer.py` → `src/legacy/example_fixer.py`
11. `src/review_orchestrator.py` → `src/legacy/review_orchestrator.py`
12. `src/review_inmemory_blog.py` → `src/legacy/review_inmemory_blog.py`

**Setup** (1 file):
13. `src/seed_namespace_mappings.py` → `src/setup/seed_namespace_mappings.py`

**Acceptance Criteria**:
- [ ] 15 files moved to new locations
- [ ] Import statements updated to new structure
- [ ] All files importable from new locations
- [ ] No syntax errors or broken imports
- [ ] Evidence document with git status

**Key Import Updates**:

**discovery_service.py**:
- OLD: `from database import`, `from telemetry import`, `from snippet_locator import`
- NEW:
  ```python
  from src.core import Database, TelemetryClient
  from .snippet_locator import SnippetLocator
  from .gist_service import GistService
  ```

**patching_service.py**:
- OLD: `from database import`, `from placeholder_patcher import`
- NEW:
  ```python
  from src.core import Database, TelemetryClient
  from .placeholder_patcher import PlaceholderPatcher
  ```

**Required Tests**: Import tests for all 15 files
**Required Docs/Specs**: None

**Evidence Commands**:
```bash
# Test imports
python -c "from src.discovery import DiscoveryService"
python -c "from src.api_reference import ApiReferenceService"
python -c "from src.patching import PatchingService"
```

---

### Task REORG-06: Update CLI (Final Integration)

**ID**: REORG-06
**Scope**: Update cli.py with all new imports (most complex import updates)
**Owner-Agent**: Agent B (Implementation)
**Priority**: P0 (Critical - CLI is the main entry point)
**Status**: BLOCKED (needs REORG-03, REORG-04)
**Risk**: MEDIUM (cli.py has most imports, critical file)
**Estimated Time**: 30 minutes

**Affected Paths**:
- `src/cli.py` (MODIFY - ~10 import statement updates)

**Current Imports** (to update):
```python
from database import Database
from telemetry import TelemetryClient
from discovery_service import DiscoveryService
from pattern_registry import PatternRegistry
from ollama_integration import OllamaClient
from workspace_manager import WorkspaceManager
from validation_orchestrator import ValidationOrchestrator
from patching_service import PatchingService
from gist_service import GistService
from api_index_builder import ApiIndexBuilder
```

**New Imports**:
```python
from src.core import Database, TelemetryClient
from src.discovery import DiscoveryService, GistService
from src.validation import (
    ValidationOrchestrator,
    PatternRegistry,
    WorkspaceManager,
)
from src.llm import OllamaClient
from src.patching import PatchingService
from src.api_reference import ApiIndexBuilder
```

**Acceptance Criteria**:
- [ ] All import statements updated to new structure
- [ ] cli.py stays at src/cli.py (root level)
- [ ] CLI commands still functional (discover, validate, patch)
- [ ] No import errors when running CLI
- [ ] Evidence document with before/after imports

**Required Tests**: CLI smoke test for each command
**Required Docs/Specs**: None

**Evidence Commands**:
```bash
# Test CLI
python -m src.cli --help
python -m src.cli discover --help
python -m src.cli validate --help
python -m src.cli patch --help
```

---

## Phase 3: Testing & Verification

### Task REORG-05: Comprehensive Testing & Verification

**ID**: REORG-05
**Scope**: Run all tests, CLI commands, import verification, broken import search
**Owner-Agent**: Agent C (Tests & Verification)
**Priority**: P0 (Critical - must pass before commit)
**Status**: BLOCKED (needs REORG-06)
**Risk**: HIGH (comprehensive validation required)
**Estimated Time**: 1 hour

**Acceptance Criteria**:
- [ ] pytest tests/ passes (all existing tests still work)
- [ ] CLI discover command works: `python -m src.cli discover --family zip`
- [ ] CLI validate command works: `python -m src.cli validate --family zip --max-snippets 2`
- [ ] CLI patch dry-run works: `python -m src.cli patch --family zip --run-id <id> --dry-run`
- [ ] Import verification succeeds (can import from new locations)
- [ ] No broken old import patterns found in src/
- [ ] Git status shows expected file moves (git mv preserves history)
- [ ] Evidence document with all test results

**Verification Commands** (from plan):
```bash
# 1. Run existing tests
pytest tests/ -v

# 2. CLI validation
python -m src.cli discover --family zip --content-root "D:\onedrive\Documents\GitHub\aspose.net\content"
python -m src.cli validate --family zip --max-snippets 2
python -m src.cli patch --family zip --run-id <latest_id> --dry-run

# 3. Import verification (Python REPL)
python -c "from src.core import Database, TelemetryClient"
python -c "from src.validation import ValidationOrchestrator"
python -c "from src.discovery import DiscoveryService"
python -c "from src.llm import OllamaClient"
python -c "from src.patching import PatchingService"

# 4. Check for broken imports
grep -r "^from database import" src/
grep -r "^from validation_orchestrator import" src/
grep -r "^from workspace_manager import" src/
# Expected: No results (all updated)

# 5. Git status validation
git status
# Expected: Shows renames (src/database.py → src/core/database.py)
```

**Red Flags** (must investigate if found):
- Any test failures
- CLI commands crash or error
- ImportError when testing new imports
- Old import patterns still present in src/
- Git shows deletions instead of renames (history lost)

**Required Tests**: All existing tests + new smoke tests
**Required Docs/Specs**: Evidence document with complete verification results

---

## Critical Path

REORG-01 (30 min) → REORG-02 (45 min) → [REORG-03 (2 hrs) + REORG-04 (1.5 hrs) parallel] → REORG-06 (30 min) → REORG-05 (1 hr)

**Total Estimated Time**: 4-5 hours (with parallelization)

---

## Success Metrics

### Primary Metrics (Must Achieve)
- [ ] All 25 files successfully moved to new structure
- [ ] All imports updated to new package structure
- [ ] All existing tests pass
- [ ] All CLI commands functional
- [ ] Zero broken import patterns in src/
- [ ] Git history preserved (using git mv)

### Quality Metrics (Target)
- [ ] Code organization score: 5.0/5
- [ ] Maintainability: 5.0/5
- [ ] Documentation: 4.5/5 (update architecture.md)
- [ ] Zero regressions

### Quality Gate
**Threshold**: 4.0/5 minimum on ALL 12 dimensions for REORG-05 (testing task)
**Regression Policy**: Zero tolerance - any test failure blocks merge

---

## Parallel Execution Strategy

### Wave 1: Foundation (Sequential)
- **REORG-01** (Agent B) - Directory setup (30 min) - MUST COMPLETE FIRST

### Wave 2: Leaf Files (Sequential)
- **REORG-02** (Agent B) - Core & LLM files (45 min)

### Wave 3: Parallel Migration (After Wave 2)
- **REORG-03** (Agent B) - Validation files (2 hrs) - PARALLEL
- **REORG-04** (Agent B) - Peripheral files (1.5 hrs) - PARALLEL

### Wave 4: Integration (After Wave 3)
- **REORG-06** (Agent B) - CLI updates (30 min)

### Wave 5: Verification (After Wave 4)
- **REORG-05** (Agent C) - Testing (1 hr)

---

## Risk Assessment

### High Risks
- **REORG-03**: Complex dependency graph in validation pipeline
  - Mitigation: Update imports methodically, test each file after move
- **REORG-05**: Any test failure blocks entire reorganization
  - Mitigation: Incremental commits per wave, easy rollback

### Medium Risks
- **REORG-06**: CLI is critical entry point, many imports
  - Mitigation: Test CLI commands immediately after update
- **Import circular dependencies**: Could emerge after reorganization
  - Mitigation: Review import chains, use lazy imports if needed

### Low Risks
- **REORG-01**: Directory creation only
- **REORG-02**: Leaf files with minimal dependencies

---

## Rollback Plan

### Per-Wave Rollback (Git-based)
```bash
# Rollback to start of Wave 3
git reset --hard <commit_after_wave_2>

# Rollback entire reorganization
git reset --hard <commit_before_reorg>
```

### Safety Measures
- Each wave is a separate git commit
- Commit messages: "refactor(src): Wave N - <description>"
- Test after each wave before proceeding
- Keep original file structure intact until REORG-05 passes

---

**Status**: READY TO START (Wave 1 - REORG-01)
**Next Action**: Spawn Agent B for REORG-01 (directory structure creation)

---
---

# Task Backlog: Commit & Telemetry Policy Fixes

**Created**: 2026-01-15
**Plan Source**: C:\Users\prora\.claude\plans\valiant-noodling-pizza.md
**Orchestrator**: Fix commit and telemetry policies per user requirements
**Goal**:
1. Commit: Conventional format, description template, hardcoded co-author
2. Telemetry: POST to HTTP API + SQLite with full ~40 field schema

---

## Executive Summary

**Context**: Current implementation has gaps:
- Commit: Description template exists but unused, no co-author, non-conventional format
- Telemetry: Schema has ~10 fields vs required ~40 fields, no HTTP API integration

**Solution**:
- Update GitConfig with conventional commit format
- Add co-author trailer to commit message in orchestrator
- Create TelemetryRun model with full ~40 field schema
- Create TelemetryService for HTTP API + SQLite dual-write
- Integrate into orchestrator at start/end of pipeline

---

## Workstream Allocation

| Workstream | Owner | Tasks | Priority | Can Start |
|------------|-------|-------|----------|-----------|
| **WS1: Config Updates** | Implementation | CT-01, CT-04, CT-08 | P0 | YES |
| **WS2: Model Updates** | Implementation | CT-03 | P0 | YES (parallel with WS1) |
| **WS3: Database Schema** | Implementation | CT-05 | P0 | After WS2 |
| **WS4: Commit Message** | Implementation | CT-02 | P0 | After WS1 |
| **WS5: TelemetryService** | Implementation | CT-06, CT-07 | P0 | After WS3 |
| **WS6: Testing** | Testing | CT-09 | P1 | After WS4, WS5 |

---

## Task CT-01: Update GitConfig Defaults

**ID**: CT-01
**Scope**: Update GitConfig model with conventional commit template and description template
**Priority**: P0 (Critical)
**Status**: READY
**Risk**: LOW (config-only)
**Estimated Time**: 10 minutes

**Affected Paths**:
- `src/core/config.py` (UPDATE - lines 41-47)

**Current State**:
```python
class GitConfig(BaseModel):
    enabled: bool = True
    commit_message_template: str = "Verify examples: {family} ({count} files)"
    commit_description_template: str = "Updated verified examples. RunId={run_id}"
    only_commit_touched_files: bool = True
```

**Required Change**:
```python
class GitConfig(BaseModel):
    enabled: bool = True
    commit_message_template: str = "chore({family}): verify {count} examples"
    commit_description_template: str = "Automated verification of {count} examples.\n\nRunId: {run_id}\nFamily: {family}"
    only_commit_touched_files: bool = True
```

**Acceptance Criteria**:
- [ ] commit_message_template uses conventional commits format
- [ ] commit_description_template includes structured run info
- [ ] No syntax errors

---

## Task CT-02: Update Commit Message with Co-Author

**ID**: CT-02
**Scope**: Update finalization phase to include description and co-author trailer
**Priority**: P0 (Critical)
**Status**: BLOCKED (needs CT-01)
**Risk**: LOW (git command modification)
**Estimated Time**: 15 minutes

**Affected Paths**:
- `src/pipeline/orchestrator.py` (UPDATE - lines 993-1003)

**Current State** (approx):
```python
message = global_config.git.commit_message_template.format(
    family=family, count=len(touched_files),
)
result = subprocess.run(
    ["git", "commit", "-m", message],
    capture_output=True, text=True,
)
```

**Required Change**:
```python
message_title = global_config.git.commit_message_template.format(
    family=family, count=len(touched_files)
)
description = global_config.git.commit_description_template.format(
    family=family, count=len(touched_files), run_id=run_id
)
co_author = "Example Reviewer <example-reviewer@aspose.net>"
full_message = f"{message_title}\n\n{description}\n\nCo-Authored-By: {co_author}"

result = subprocess.run(
    ["git", "commit", "-m", full_message],
    capture_output=True, text=True,
)
```

**Acceptance Criteria**:
- [ ] Full commit message includes title + description + co-author
- [ ] Co-author is hardcoded as `Example Reviewer <example-reviewer@aspose.net>`
- [ ] No syntax errors

---

## Task CT-03: Add TelemetryRun Model

**ID**: CT-03
**Scope**: Add TelemetryRun Pydantic model with ~40 fields matching HTTP API schema
**Priority**: P0 (Critical)
**Status**: READY
**Risk**: LOW (additive model)
**Estimated Time**: 30 minutes

**Affected Paths**:
- `src/core/models.py` (UPDATE - add new model)

**Key Fields** (from local-telemetry.md spec):
- Required: event_id, run_id, agent_name, job_type, start_time, created_at
- Status: end_time, status, duration_ms
- Product: product, product_family, platform, subdomain, website, website_section
- Counts: items_discovered, items_succeeded, items_failed, items_skipped
- Git: git_repo, git_branch, git_commit_hash, git_commit_source, git_commit_author
- Environment: host, environment, trigger_type
- JSON: metrics_json, context_json
- API: api_posted, api_posted_at, api_retry_count

**Acceptance Criteria**:
- [ ] TelemetryRun model with ~40 fields
- [ ] All fields have appropriate types and defaults
- [ ] Default factories for uuid, datetime, hostname
- [ ] No syntax errors

---

## Task CT-04: Update TelemetryConfig with HTTP API Fields

**ID**: CT-04
**Scope**: Add HTTP API configuration fields to TelemetryConfig
**Priority**: P0 (Critical)
**Status**: READY (parallel with CT-01)
**Risk**: LOW (config-only)
**Estimated Time**: 10 minutes

**Affected Paths**:
- `src/core/config.py` (UPDATE - lines 67-71)

**Current State**:
```python
class TelemetryConfig(BaseModel):
    internal_enabled: bool = True
    local_telemetry_enabled: bool = True
    local_telemetry_path: str = "./local-telemetry"
```

**Required Change**:
```python
class TelemetryConfig(BaseModel):
    internal_enabled: bool = True
    local_telemetry_enabled: bool = True
    local_telemetry_path: str = "./local-telemetry"
    http_api_enabled: bool = True
    http_api_url: str = "http://localhost:8765"
    http_api_timeout_seconds: int = 10
    http_api_retry_count: int = 3
```

**Acceptance Criteria**:
- [ ] HTTP API fields added with sensible defaults
- [ ] No syntax errors

---

## Task CT-05: Add telemetry_runs Table Schema

**ID**: CT-05
**Scope**: Add telemetry_runs table with all ~40 columns + CRUD methods
**Priority**: P0 (Critical)
**Status**: BLOCKED (needs CT-03)
**Risk**: MEDIUM (database schema change)
**Estimated Time**: 45 minutes

**Affected Paths**:
- `src/core/database.py` (UPDATE - add table schema + methods)

**New Table Schema**:
```sql
CREATE TABLE IF NOT EXISTS telemetry_runs (
    event_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    start_time TEXT NOT NULL,
    -- ... ~35 more columns matching TelemetryRun model
)
```

**New Methods**:
- `save_telemetry_run(run: TelemetryRun) -> str`
- `get_telemetry_run(event_id: str) -> Optional[TelemetryRun]`
- `update_telemetry_run(event_id: str, updates: Dict) -> bool`

**Acceptance Criteria**:
- [ ] Table schema matches TelemetryRun model
- [ ] CRUD methods implemented
- [ ] Backward compatible with existing schema
- [ ] No syntax errors

---

## Task CT-06: Create TelemetryService

**ID**: CT-06
**Scope**: Create new TelemetryService for HTTP API + SQLite dual-write
**Priority**: P0 (Critical)
**Status**: BLOCKED (needs CT-05)
**Risk**: MEDIUM (new service, HTTP integration)
**Estimated Time**: 1 hour

**Affected Paths**:
- `src/services/telemetry_service.py` (NEW FILE)

**Key Methods**:
- `create_run_event(run_id, job_type, family_config, status="running") -> TelemetryRun`
- `start_run(event: TelemetryRun) -> bool` (POST + save locally)
- `update_run(event_id, updates) -> bool` (PATCH + update locally)
- `complete_run(event_id, status, counts...) -> bool` (final update)
- `associate_commit(event_id, commit_hash, timestamp) -> bool` (POST /associate-commit)
- `_post_to_api(event) -> bool` (HTTP POST with retry)
- `_patch_api(event_id, updates) -> bool` (HTTP PATCH with retry)

**Acceptance Criteria**:
- [ ] HTTP API calls are non-blocking (log warning, don't crash)
- [ ] Retry logic implemented
- [ ] Both HTTP and SQLite writes on each operation
- [ ] Proper field population from config/context
- [ ] No syntax errors

---

## Task CT-07: Integrate TelemetryService into Orchestrator

**ID**: CT-07
**Scope**: Wire TelemetryService into pipeline start/end
**Priority**: P0 (Critical)
**Status**: BLOCKED (needs CT-06)
**Risk**: MEDIUM (orchestrator modification)
**Estimated Time**: 30 minutes

**Affected Paths**:
- `src/pipeline/orchestrator.py` (UPDATE - add service property + calls)

**Integration Points**:
1. Add `TelemetryService` as lazy-initialized property
2. At pipeline start: `create_run_event()` + `start_run()`
3. Track `telemetry_event_id` through pipeline
4. At finalization (after git commit): `associate_commit()` + `complete_run()`

**Acceptance Criteria**:
- [ ] TelemetryService initialized lazily
- [ ] Run event created at pipeline start
- [ ] Commit associated with event after git commit
- [ ] Run completed with final counts
- [ ] No blocking failures (telemetry errors don't crash pipeline)

---

## Task CT-08: Update config/global.json Defaults

**ID**: CT-08
**Scope**: Update global.json with new config defaults
**Priority**: P0 (Critical)
**Status**: READY (parallel with CT-01)
**Risk**: LOW (config file update)
**Estimated Time**: 5 minutes

**Affected Paths**:
- `config/global.json` (UPDATE)

**Required Changes**:
```json
"git": {
    "enabled": false,
    "commit_message_template": "chore({family}): verify {count} examples",
    "commit_description_template": "Automated verification of {count} examples.\n\nRunId: {run_id}\nFamily: {family}",
    "only_commit_touched_files": true
},
"telemetry": {
    "internal_enabled": true,
    "local_telemetry_enabled": true,
    "local_telemetry_path": "./local-telemetry",
    "http_api_enabled": true,
    "http_api_url": "http://localhost:8765",
    "http_api_timeout_seconds": 10,
    "http_api_retry_count": 3
}
```

**Acceptance Criteria**:
- [ ] Git config updated with conventional commit format
- [ ] Telemetry config includes HTTP API fields
- [ ] Valid JSON syntax

---

## Task CT-09: Testing & Verification

**ID**: CT-09
**Scope**: Write tests and verify implementation
**Priority**: P1 (High)
**Status**: BLOCKED (needs CT-07)
**Risk**: LOW (testing)
**Estimated Time**: 1 hour

**Verification Commands**:
```bash
# Commit verification
git log -1 --format="%B"
# Expected format:
# chore(zip): verify 5 examples
#
# Automated verification of 5 examples.
#
# RunId: 2026-01-15T...
# Family: zip
#
# Co-Authored-By: Example Reviewer <example-reviewer@aspose.net>

# Telemetry SQLite check
sqlite3 data/example_reviewer.db \
  "SELECT event_id, status, items_succeeded, api_posted FROM telemetry_runs"

# HTTP API check (if server running)
curl "http://localhost:8765/api/v1/runs?agent_name=example-reviewer"
```

**Acceptance Criteria**:
- [ ] Commit message format verified
- [ ] Telemetry records in SQLite
- [ ] HTTP API posts successful (when server available)
- [ ] No regressions in existing tests

---

## Critical Path

CT-01 + CT-03 + CT-04 + CT-08 (parallel, 30 min) → CT-02 + CT-05 (30 min) → CT-06 (1 hr) → CT-07 (30 min) → CT-09 (1 hr)

**Total Estimated Time**: ~3.5 hours

---

**Status**: CT-01, CT-03, CT-04, CT-08 READY TO START (parallel)

---
---

# Task Backlog: Healing Plans (Infrastructure, Discovery, Drift, CLI Testing)

**Created**: 2026-01-16 (Orchestrator Run)
**Plan Sources**:
- `plans/healing/cli-testing-system.md`
- `plans/healing/infrastructure-hardening.md`
- `plans/healing/configurable-discovery.md`
- `plans/healing/intent-drift-prevention.md`
- `plans/healing/HEALING_PLANS_AUDIT_SUMMARY.md`
**Orchestrator**: Comprehensive healing across CLI testing, infrastructure, discovery patterns, and intent drift prevention
**Priority Source**: HEALING_PLANS_AUDIT_SUMMARY recommended execution order

---

## Executive Summary

**Context**: All healing plans have undergone Reality Check and rescoping. Auto-Commit and Telemetry plans (already in this backlog) were rescoped to enhance existing Phase F and TelemetryService implementations. Four additional healing plans provide systematic improvements across CLI testing, infrastructure, discovery configuration, and intent drift prevention.

**Recommended Execution Order** (from HEALING_PLANS_AUDIT_SUMMARY):
1. **Phase 1: Foundation & CLI Safety (Week 1)** - CT-01, CT-02, IH-02, IH-04 (17h)
2. **Phase 2: Testing & CI Automation (Week 2)** - CT-04, CT-03 (8h)
3. **Phase 3: Discovery & Drift Prevention (Week 3)** - CD-01, CD-02, ID-04 (30h)
4. **Phase 4: Enhanced Configuration (Week 4)** - ID-02 (10h)
5. **Phase 5: Advanced Features (Week 5+)** - IH-03, remaining tasks

**Total Critical Path Effort**: ~109 hours (~13.5 days)

**Key Dependencies**:
- CLI Testing (CT) tasks are independent - can start immediately
- Infrastructure (IH) tasks are independent - can start immediately
- Discovery (CD) tasks can run in parallel with CLI testing
- Intent Drift (ID) tasks should start after CD-01 (reuse pattern detection)

---

## Workstream Allocation (Max 5 parallel)

| Workstream | Owner Agent | Tasks | Priority | Can Start | Notes |
|------------|-------------|-------|----------|-----------|-------|
| **WS1: CLI Testing Foundation** | A (Discovery) | CT-01, CT-02 | P0 | YES | Highest user impact - prevents import errors |
| **WS2: Infrastructure Hygiene** | D (Docs) | IH-02, IH-04 | P0 | YES | Low risk, user-facing improvements |
| **WS3: CLI CI Integration** | E (Ops) | CT-04, CT-03 | P1 | After WS1 | Automates CLI validation |
| **WS4: Discovery Config** | B (Implementation) | CD-01, CD-02 | P1 | YES | Parallel with CLI work |
| **WS5: Drift Prevention** | B (Implementation) | ID-04, ID-02 | P1 | After WS4 | Reuses pattern detection |

---

## PLAN_FIX Tasks (Documentation Updates)

### Task PLAN_FIX-01: Update Configurable Discovery Plan Reality Check

**ID**: PLAN_FIX-01
**Scope**: Add Reality Check section and Pydantic model recommendations to configurable-discovery.md
**Owner-Agent**: Agent D (Docs & Specs)
**Priority**: P2 (Low - optional enhancement)
**Status**: PENDING (documentation-only, not blocking implementation)
**Risk**: ZERO (doc updates only)
**Estimated Time**: 30 minutes

**Affected Paths**:
- `plans/healing/configurable-discovery.md` (UPDATE - add sections)

**Changes Needed** (from HEALING_PLANS_AUDIT_SUMMARY):
- [ ] Add Repo Reality Check section with validation commands
- [ ] Update CD-01 to use Pydantic `BaseModel` instead of `@dataclass`
- [ ] Update fence pattern to handle `c#` language: `(\w+|c#)` instead of `(\w*)`
- [ ] Add regex performance acceptance check
- [ ] Make telemetry metric names explicit in CD-02

**Acceptance Criteria**:
- [ ] Reality Check section added with bash validation commands
- [ ] Pydantic example provided in CD-01 taskcard
- [ ] Fence pattern regex updated in plan
- [ ] Plan remains structurally consistent

---

### Task PLAN_FIX-02: Update Intent Drift Prevention Plan Reality Check

**ID**: PLAN_FIX-02
**Scope**: Add Reality Check section and drift computation clarifications to intent-drift-prevention.md
**Owner-Agent**: Agent D (Docs & Specs)
**Priority**: P2 (Low - optional enhancement)
**Status**: PENDING (documentation-only, not blocking implementation)
**Risk**: ZERO (doc updates only)
**Estimated Time**: 30 minutes

**Affected Paths**:
- `plans/healing/intent-drift-prevention.md` (UPDATE - add sections)

**Changes Needed** (from HEALING_PLANS_AUDIT_SUMMARY):
- [ ] Add Repo Reality Check section
- [ ] Clarify in ID-01 that drift is computed against `original_code`
- [ ] Update ID-01 to reuse `VectorDBService` embedding model instance
- [ ] Add acceptance check to ID-05: "exclude_high_drift=true filters correctly"
- [ ] Add note about cost of SentenceTransformer instantiation

**Acceptance Criteria**:
- [ ] Reality Check section added
- [ ] Drift computation against `original_code` clarified
- [ ] VectorDBService reuse documented
- [ ] Plan remains structurally consistent

---

## Phase 1: Foundation & CLI Safety (Week 1) - HIGHEST PRIORITY

### Task CT-01: Static Import Analyzer

**ID**: CT-01
**Scope**: Create AST-based static analyzer to detect undefined names in Python CLI code
**Owner-Agent**: Agent A (Discovery & Architecture)
**Priority**: P0 (CRITICAL - Highest impact, prevents production import errors)
**Status**: READY TO START
**Risk**: LOW (analysis tool only, no production code changes)
**Estimated Time**: 8 hours
**Expected Impact**: ⭐ Catches CLI import errors before runtime - prevents user-facing failures

**Gap Linkage**: Fixes CT-GAP-01 (No static analysis for import errors in CLI code)

**Problem**: CLI uses lazy imports (to speed up `--help`) causing hidden `NameError`/`ImportError` at runtime. Static type checkers don't catch these because imports exist - just not in the right scope.

**Affected Paths**:
- `scripts/analyze_cli_imports.py` (NEW - ~500 lines) - AST-based analyzer
- `tests/test_import_analyzer.py` (NEW - ~150 lines) - Analyzer tests
- `scripts/README.md` (UPDATE - add analyzer documentation)

**Acceptance Criteria**:
- [ ] `ImportAnalyzer` class implemented with AST-based scope resolution
- [ ] Tracks all scope types: module, function, closure, comprehension, TYPE_CHECKING
- [ ] Detects undefined names with function name, line number, variable name
- [ ] Exit codes: 0 = success, 1 = undefined names found
- [ ] Handles Python builtins correctly (no false positives)
- [ ] Handles `TYPE_CHECKING` imports (excluded from runtime scope)
- [ ] CLI usage: `python scripts/analyze_cli_imports.py src/cli/main.py`
- [ ] Unit tests pass: `pytest tests/test_import_analyzer.py -v` (10+ tests)
- [ ] Fast execution (< 1 second for typical CLI file)
- [ ] Documentation in scripts/README.md with examples

**Core Classes** (from plan lines 175-207):
```python
@dataclass
class FunctionScope:
    name: str
    lineno: int
    qualified_name: str  # e.g., "outer.inner"
    parameters: Set[str]
    local_assignments: Set[str]
    local_imports: Set[str]
    names_used: Dict[str, int]  # name -> first line used
    comprehension_vars: Set[str]
    nested_function_names: Set[str]
    parent_scope: Optional['FunctionScope']  # For closures

class ImportAnalyzer(ast.NodeVisitor):
    def __init__(self):
        self.module_level_names: Set[str] = set()
        self.type_checking_names: Set[str] = set()
        self.function_scopes: List[FunctionScope] = []
        self.current_scope: Optional[FunctionScope] = None
        self.in_type_checking: bool = False

    def visit_Import(self, node): ...
    def visit_ImportFrom(self, node): ...
    def visit_FunctionDef(self, node): ...
    def visit_Name(self, node): ...
    def visit_ListComp(self, node): ...
```

**Scope Resolution Algorithm** (from plan lines 209-220):
Names are available if they come from:
1. Module-level imports/definitions
2. Function parameters
3. Local assignments (for loops, with aliases, except names)
4. Local imports (inside function)
5. Comprehension variables
6. Nested function names
7. Closure scope (parent function scopes)
8. Python builtins (`open`, `print`, `len`, etc.)
9. Common typing names (`Dict`, `List`, `Optional`, etc.)

**Example Output** (from plan lines 131-142):
```
Analyzing src/cli/main.py for undefined names...
======================================================================
❌ Found 2 undefined names:

Function: run_command (line 145)
  - 'Database' used at line 150 (not imported in function scope)
  - 'logger' used at line 155 (not defined anywhere)

Exit code: 1
```

**Required Tests** (from plan lines 221-238):
- Test undefined module import usage
- Test closure scope tracking
- Test comprehension variables
- Test TYPE_CHECKING handling
- Test nested functions
- Test no false positives for builtins

**Plan Reference**: cli-testing-system.md lines 93-350

---

### Task CT-02: Execution Smoke Tests

**ID**: CT-02
**Scope**: Create smoke tests for all CLI commands to validate basic execution
**Owner-Agent**: Agent C (Tests & Verification)
**Priority**: P0 (CRITICAL - Validates basic CLI functionality)
**Status**: READY TO START
**Risk**: LOW (test-only, uses mocks and temp directories)
**Estimated Time**: 4 hours
**Expected Impact**: ⭐ Prevents CLI execution failures before they reach users

**Gap Linkage**: Fixes CT-GAP-02 (No smoke tests for CLI command execution)

**Affected Paths**:
- `tests/test_cli_smoke.py` (NEW - ~200 lines) - Smoke tests for all CLI commands
- `tests/conftest.py` (UPDATE - add CLI fixtures)

**Acceptance Criteria**:
- [ ] Tests for `--help` on all subcommands (run, discover, compile, validate)
- [ ] Test basic execution: `python -m src.cli.main run --family zip --dry-run`
- [ ] Verify no import errors raised during execution
- [ ] All tests use subprocess for real CLI invocation
- [ ] Tests use temporary directories (no pollution)
- [ ] Mock expensive operations (LLM calls, network requests)
- [ ] All tests complete in < 30 seconds total
- [ ] Unit tests pass: `pytest tests/test_cli_smoke.py -v` (8+ tests)

**Test Examples** (from plan lines 406-441):
```python
def test_main_help():
    """Test main --help works without import errors."""
    result = subprocess.run(
        ['python', '-m', 'src.cli.main', '--help'],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    assert '--help' in result.stdout

def test_run_dry_run():
    """Test run command executes without errors in dry-run mode."""
    result = subprocess.run(
        ['python', '-m', 'src.cli.main', 'run',
         '--family', 'zip', '--dry-run', '--max-examples', '1'],
        capture_output=True, text=True, timeout=30
    )
    # Should complete without import errors
    assert 'NameError' not in result.stderr
    assert 'ImportError' not in result.stderr
```

**Fixtures** (from plan lines 443-458):
```python
@pytest.fixture
def temp_workspace():
    """Create temporary workspace for CLI tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        # Create minimal config structure
        (workspace / 'config').mkdir()
        (workspace / 'config' / 'global.json').write_text('{}')
        yield workspace
```

**Plan Reference**: cli-testing-system.md lines 354-495

---

### Task IH-02: Fix CLI Entry Point

**ID**: IH-02
**Scope**: Create top-level `cli` package for cleaner CLI invocation
**Owner-Agent**: Agent D (Docs & Specs)
**Priority**: P0 (CRITICAL - User-facing improvement)
**Status**: READY TO START
**Risk**: LOW (additive change, backward compatible)
**Estimated Time**: 3 hours
**Expected Impact**: Cleaner user experience - `python -m cli` instead of `python -m src.cli.main`

**Gap Linkage**: Fixes IH-GAP-02 (CLI invocation awkward - requires `python -m src.cli.main`)

**Affected Paths**:
- `cli/__init__.py` (NEW)
- `cli/__main__.py` (NEW)
- `README.md` (UPDATE - update CLI examples)
- `docs/*.md` (UPDATE - update CLI examples in docs)

**Current State**:
```bash
# Current (awkward)
python -m src.cli.main run --family zip

# Desired (clean)
python -m cli run --family zip
```

**Acceptance Criteria**:
- [ ] `cli/__init__.py` created (imports from `src.cli.main`)
- [ ] `cli/__main__.py` created (delegates to `src.cli.main`)
- [ ] Both invocations work: `python -m cli` and `python -m src.cli.main`
- [ ] All docs updated with new invocation pattern
- [ ] README.md updated with examples
- [ ] Backward compatibility maintained (old invocation still works)

**Implementation** (from infrastructure-hardening.md):
```python
# cli/__init__.py
"""CLI package - provides cleaner entry point."""
from src.cli.main import main

__all__ = ['main']

# cli/__main__.py
"""CLI entry point."""
from src.cli.main import main

if __name__ == '__main__':
    main()
```

**Verification Commands**:
```bash
# Test new invocation
python -m cli --help
python -m cli run --family zip --dry-run

# Test backward compatibility
python -m src.cli.main --help
```

**Plan Reference**: infrastructure-hardening.md (IH-02 taskcard)

---

### Task IH-04: Repository Hygiene

**ID**: IH-04
**Scope**: Clean up root directory - archive old plans, organize test files
**Owner-Agent**: Agent D (Docs & Specs)
**Priority**: P0 (CRITICAL - Quick win, improves dev experience)
**Status**: READY TO START
**Risk**: ZERO (file organization only)
**Estimated Time**: 2 hours
**Expected Impact**: Cleaner repository, easier navigation

**Gap Linkage**: Fixes IH-GAP-04 (Root directory cluttered with old plans, test files)

**Affected Paths**:
- `archive/` (NEW - directory for old plans)
- `tests/` (UPDATE - organize test files)
- Root directory (CLEAN - move files)

**Files to Archive/Organize** (from git status in context):
```
Root directory clutter:
- RUNTIME_ATTEMPT_FIX_SUMMARY.md
- analyze_failure.py, analyze_failures.py, analyze_remaining_failures.py, analyze_runtime_failures.py
- check_example_status.py, create_encrypted_samples.py
- run_e2e_verification.py, run_single_example_debug.py
- validate_hardening.py, verify_runtime_recording.py
- Multiple old test files (test_*.py) in root that should be in tests/

Old plans deleted (D status in git):
- IMPLEMENTATION-PLAN.md, VALIDATION_FAILURE_ANALYSIS.md, PHASE5_IMPLEMENTATION.md
- docs/bugfix-workspace-wrapper-20260109.md, docs/session-summary-20260109.md
```

**Acceptance Criteria**:
- [ ] `archive/old-plans/` created
- [ ] Old .md files from git status moved to archive
- [ ] Analysis scripts moved to `scripts/analysis/` or archived
- [ ] Root test files moved to `tests/` directory
- [ ] Root directory clean - only essential files remain
- [ ] Git commit created documenting cleanup
- [ ] No functional regressions (all tests still pass)

**Cleanup Actions**:
1. Create `archive/old-plans/` and `archive/analysis-scripts/`
2. Move old markdown files to `archive/old-plans/`
3. Move analysis scripts to `archive/analysis-scripts/`
4. Move root test files to `tests/` (maintaining test discovery)
5. Update .gitignore if needed
6. Document cleanup in CHANGELOG.md

**Verification Commands**:
```bash
# Verify tests still work
pytest tests/ -v

# Verify no broken imports
python -m src.cli.main --help

# Check root directory cleanliness
ls -la | grep -E "\\.py$|\\.md$"
```

**Plan Reference**: infrastructure-hardening.md (IH-04 taskcard)

---

## Phase 2: Testing & CI Automation (Week 2)

### Task CT-04: CI Integration

**ID**: CT-04
**Scope**: Create GitHub Actions workflow for automated CLI testing
**Owner-Agent**: Agent E (Observability & Ops)
**Priority**: P1 (HIGH - Automates validation)
**Status**: BLOCKED (needs CT-01, CT-02)
**Risk**: LOW (CI configuration only)
**Estimated Time**: 2 hours
**Expected Impact**: Automated CLI validation on every commit

**Gap Linkage**: Fixes CT-GAP-04 (No CI/CD integration for CLI validation)

**Dependencies**: CT-01 (static analyzer), CT-02 (smoke tests)

**Affected Paths**:
- `.github/workflows/cli_tests.yml` (NEW - ~60 lines)

**Acceptance Criteria**:
- [ ] GitHub Actions workflow created
- [ ] Runs on: push to main/develop, pull requests to main
- [ ] Job 1: Static analysis (runs analyze_cli_imports.py)
- [ ] Job 2: Smoke tests (runs pytest tests/test_cli_smoke.py)
- [ ] Job 3: Matrix tests (runs on PR only)
- [ ] Python 3.10 used
- [ ] Dependencies cached for fast execution
- [ ] Status checks appear on PRs

**Workflow Structure** (from plan lines 618-660):
```yaml
name: CLI Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  static-analysis:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - name: Run static import analyzer
        run: python scripts/analyze_cli_imports.py src/cli/main.py

  smoke-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run smoke tests
        run: pytest tests/test_cli_smoke.py -v

  matrix-tests:
    if: github.event_name == 'pull_request'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run matrix tests
        run: pytest tests/test_cli_matrix.py -v
```

**Verification**:
- [ ] Push to branch triggers workflow
- [ ] Workflow appears in Actions tab
- [ ] All jobs pass
- [ ] PR shows status checks

**Plan Reference**: cli-testing-system.md lines 587-662

---

### Task CT-03: Runtime Matrix Tests

**ID**: CT-03
**Scope**: Systematic testing of CLI option combinations
**Owner-Agent**: Agent C (Tests & Verification)
**Priority**: P1 (MEDIUM - Comprehensive coverage)
**Status**: BLOCKED (needs CT-02)
**Risk**: LOW (test-only)
**Estimated Time**: 6 hours
**Expected Impact**: Comprehensive CLI option coverage

**Gap Linkage**: Fixes CT-GAP-03 (No systematic testing of CLI option combinations)

**Dependencies**: CT-02 (smoke tests foundation)

**Affected Paths**:
- `tests/test_cli_matrix.py` (NEW - ~250 lines)

**Acceptance Criteria**:
- [ ] Parameterized tests for `run` command option combinations
- [ ] Test flag combinations (boolean flags)
- [ ] Test value parameter combinations
- [ ] Test incompatible options are rejected
- [ ] All tests complete in < 2 minutes
- [ ] Unit tests pass: `pytest tests/test_cli_matrix.py -v` (15+ tests)

**Test Matrix** (from plan lines 529-565):
```python
@pytest.mark.parametrize("family,max_examples", [
    ("zip", 1),
    ("zip", 5),
    ("pdf", 1),
])
def test_run_family_combinations(family, max_examples):
    """Test run command with various family/max_examples combinations."""
    result = subprocess.run(
        ['python', '-m', 'src.cli.main', 'run',
         '--family', family, '--max-examples', str(max_examples), '--dry-run'],
        capture_output=True, text=True, timeout=60
    )
    assert 'NameError' not in result.stderr
    assert 'ImportError' not in result.stderr
```

**Option Combinations to Test**:
- `--family zip --dry-run`
- `--family zip --max-examples 5`
- `--family zip --dry-run --max-examples 1`
- `--family zip --enable-git-commit --dry-run` (should not commit in dry-run)
- Incompatible: `--enable-git-commit --disable-git-commit` (mutually exclusive)

**Plan Reference**: cli-testing-system.md lines 497-583

---

## Phase 3: Discovery & Drift Prevention (Week 3)

### Task CD-01: Make Code Fence Detection Configurable

**ID**: CD-01
**Scope**: Make markdown code fence patterns and language detection configurable
**Owner-Agent**: Agent B (Implementation)
**Priority**: P1 (HIGH - Foundation for discovery improvements)
**Status**: READY TO START
**Risk**: MEDIUM (changes discovery logic)
**Estimated Time**: 12 hours
**Expected Impact**: Flexible code fence detection across different markdown formats

**Gap Linkage**: Fixes CD-GAP-01 (Hardcoded fence patterns can't handle all markdown formats)

**Problem**: Current discovery hardcodes fence pattern `^```(\\w*)\\s*\\n(.*?)^````. Can't handle:
- Language aliases (c#, C#, csharp, cs all mean C#)
- Multi-character language tags (c# has non-word character)
- Alternative fence formats

**Affected Paths**:
- `src/core/config.py` (UPDATE - add `DiscoveryPatternsConfig` model)
- `src/services/discovery_service.py` (UPDATE - use configurable patterns)
- `config/families/*.json` (UPDATE - add discovery_patterns section)
- `config/global.json` (UPDATE - add default patterns)
- `tests/test_discovery_patterns.py` (NEW - ~100 lines)

**Configuration Model** (from plan + HEALING_PLANS_AUDIT_SUMMARY):
**NOTE**: Use Pydantic BaseModel (not dataclass) as config system is Pydantic-based.

```python
from pydantic import BaseModel, Field
from typing import List, Dict

class DiscoveryPatternsConfig(BaseModel):
    """Discovery pattern configuration for code extraction."""
    fence_patterns: List[str] = Field(
        default=["^```(\\w+|c#)\\s*\\n(.*?)^```"],  # Updated to handle c#
        description="Regex patterns for code fence detection"
    )
    validatable_languages: List[str] = Field(
        default=["cs", "csharp"],
        description="Languages that should be validated"
    )
    language_aliases: Dict[str, List[str]] = Field(
        default={
            "csharp": ["cs", "c#", "C#", "csharp", "CSharp"],
            "python": ["py", "python", "python3"]
        },
        description="Language normalization mapping"
    )
    normalize_to_canonical: bool = Field(
        default=True,
        description="Normalize language tags to canonical form"
    )
```

**Language Normalization** (from plan lines 133-180):
```python
def normalize_language(language_tag: str, config: DiscoveryPatternsConfig) -> str:
    """Normalize language tag to canonical form."""
    if not config.normalize_to_canonical:
        return language_tag

    tag_lower = language_tag.lower()
    for canonical, aliases in config.language_aliases.items():
        if tag_lower in [a.lower() for a in aliases]:
            return canonical

    return language_tag  # Return original if no match
```

**Acceptance Criteria**:
- [ ] `DiscoveryPatternsConfig` Pydantic model added to config.py
- [ ] Discovery service uses configurable patterns from config
- [ ] Language normalization working (c#, C#, cs → csharp)
- [ ] Global config has sensible defaults
- [ ] Family configs can override patterns
- [ ] Unit tests pass: `pytest tests/test_discovery_patterns.py -v` (8+ tests)
- [ ] No regressions in existing discovery (ZIP family still works)
- [ ] Performance: regex execution < 10ms per page on large files

**Fence Pattern Safety** (from HEALING_PLANS_AUDIT_SUMMARY):
- Add regex catastrophic backtracking prevention
- Test with large markdown files (10,000+ lines)
- Add timeout safeguards (fail gracefully after 5 seconds)

**Plan Reference**: configurable-discovery.md lines 88-298

---

### Task CD-02: Add Line Count and Content-Based Filtering

**ID**: CD-02
**Scope**: Add filtering for snippet line count and content patterns
**Owner-Agent**: Agent B (Implementation)
**Priority**: P1 (HIGH - Prevents "not code" false positives)
**Status**: READY TO START (parallel with CD-01)
**Risk**: MEDIUM (changes discovery logic)
**Estimated Time**: 10 hours
**Expected Impact**: Filters out non-code snippets (JSON, XML, output)

**Gap Linkage**: Fixes CD-GAP-02 (No content-based filtering - treats JSON/XML as code snippets)

**Problem**: Current discovery accepts all code fences as snippets, including:
- JSON/XML configuration (not compilable code)
- Command-line output
- File listings
- Extremely short snippets (1-2 lines, likely not complete code)

**Affected Paths**:
- `src/core/config.py` (UPDATE - add filtering config to DiscoveryPatternsConfig)
- `src/services/discovery_service.py` (UPDATE - apply content filters)
- `config/families/*.json` (UPDATE - add filtering rules)
- `tests/test_discovery_filters.py` (NEW - ~80 lines)

**Enhanced Configuration** (from plan lines 300-382):
```python
class DiscoveryPatternsConfig(BaseModel):
    # ... existing fields ...

    min_line_count: int = Field(
        default=5,
        description="Minimum lines to consider as code snippet"
    )
    max_line_count: int = Field(
        default=500,
        description="Maximum lines to consider as code snippet"
    )
    content_exclude_patterns: List[str] = Field(
        default=[
            r"^\\s*{\\s*$",  # Starts with { (likely JSON)
            r"^\\s*<\\?xml",  # Starts with <?xml
            r"^\\s*Output:",  # Command output
            r"^\\s*\\$",      # Shell prompt
        ],
        description="Regex patterns for excluding non-code content"
    )
    require_code_indicators: List[str] = Field(
        default=[
            r"\\bclass\\b",
            r"\\bpublic\\b",
            r"\\bvoid\\b",
            r"\\busing\\b",
            r"\\bnamespace\\b"
        ],
        description="Patterns indicating actual C# code (at least one must match)"
    )
```

**Filtering Logic** (from plan lines 384-435):
```python
def filter_snippet(code: str, config: DiscoveryPatternsConfig) -> Tuple[bool, str]:
    """
    Filter snippet based on content rules.
    Returns: (should_include: bool, reason: str)
    """
    lines = code.strip().split('\\n')
    line_count = len(lines)

    # Line count check
    if line_count < config.min_line_count:
        return False, f"Too short ({line_count} lines < {config.min_line_count})"
    if line_count > config.max_line_count:
        return False, f"Too long ({line_count} lines > {config.max_line_count})"

    # Content exclusion patterns
    for pattern in config.content_exclude_patterns:
        if re.search(pattern, code, re.MULTILINE):
            return False, f"Matched exclusion pattern: {pattern}"

    # Require code indicators
    if config.require_code_indicators:
        has_indicator = any(
            re.search(pattern, code, re.MULTILINE | re.IGNORECASE)
            for pattern in config.require_code_indicators
        )
        if not has_indicator:
            return False, "No C# code indicators found"

    return True, "Passed all filters"
```

**Telemetry Integration** (from plan lines 437-482):
- Metric: `discovery.snippets_filtered_out` (counter)
- Metric: `discovery.filter_reasons` (dict with counts per reason)
- Log filter decisions at DEBUG level
- Include filter stats in discovery summary

**Acceptance Criteria**:
- [ ] Line count filtering working (min=5, max=500 defaults)
- [ ] Content exclusion patterns working (JSON, XML, output excluded)
- [ ] Code indicator check working (requires C# keywords)
- [ ] Telemetry metrics tracked: `discovery.snippets_filtered_out`
- [ ] Filter reasons logged and counted
- [ ] Unit tests pass: `pytest tests/test_discovery_filters.py -v` (6+ tests)
- [ ] End-to-end test: ZIP family discovery excludes non-code fences
- [ ] No false negatives (real code snippets still included)

**Verification Commands**:
```bash
# Run discovery with filtering enabled
python -m src.cli.main discover --family zip

# Check telemetry for filter stats
sqlite3 data/example_reviewer.db "
SELECT metrics_json
FROM telemetry_runs
WHERE agent_name='example-reviewer'
ORDER BY started_at DESC LIMIT 1
" | jq '.discovery'

# Expected output shows filtered_out count and reasons
```

**Plan Reference**: configurable-discovery.md lines 300-595

---

### Task ID-04: Two-Code Final Review (Quick Win)

**ID**: ID-04
**Scope**: Add two-code (original + fixed) final review to prevent intent drift
**Owner-Agent**: Agent B (Implementation)
**Priority**: P1 (HIGH - Quick win, prevents intent drift)
**Status**: READY TO START (can run parallel with CD tasks)
**Risk**: LOW (enhancement to existing LLM flow)
**Estimated Time**: 8 hours
**Expected Impact**: ⭐ Catches intent drift before marking verified

**Gap Linkage**: Fixes ID-GAP-04 (No final review - LLM can drift from original intent during fixes)

**Problem**: Current validation flow:
1. LLM fixes code
2. Code compiles
3. Marked as verified - DONE

**Missing**: No check that fixed code still matches original intent!

**Solution**: Add Stage 5.5 (Final Review) after compilation succeeds:
1. LLM receives: original_code + final_fixed_code
2. LLM analyzes: "Does fixed code preserve original intent?"
3. If intent preserved: verify ✅
4. If intent drifted: needs-fix ❌ with drift explanation

**Affected Paths**:
- `src/services/llm_service.py` (UPDATE - add `final_review()` method)
- `src/pipeline/orchestrator.py` (UPDATE - add Stage 5.5 after compilation)
- `config/global.json` (UPDATE - add final_review config)
- `tests/test_final_review.py` (NEW - ~60 lines)

**LLM Prompt** (from plan lines 170-209):
```python
FINAL_REVIEW_PROMPT = """
You are reviewing code that was automatically fixed by an LLM to resolve compilation errors.

ORIGINAL CODE (intent source):
```csharp
{original_code}
```

FIXED CODE (after LLM fixes):
```csharp
{fixed_code}
```

TASK: Analyze whether the FIXED CODE preserves the intent and functionality of the ORIGINAL CODE.

RESPOND WITH JSON:
{{
  "intent_preserved": true/false,
  "confidence": 0.0-1.0,
  "explanation": "Brief explanation of your analysis",
  "drift_details": ["specific drift point 1", "specific drift point 2"]  // Only if intent_preserved=false
}}

GUIDELINES:
- intent_preserved=true: Fixed code does the same thing as original (minor syntax changes OK)
- intent_preserved=false: Fixed code has different functionality, missing features, or wrong logic
- Be strict: If you're unsure, mark intent_preserved=false
- Focus on semantic equivalence, not syntactic similarity
"""
```

**Integration Point** (from plan lines 211-272):
```python
# In orchestrator.py, after compilation succeeds (Stage 5)

# Stage 5.5: Final Review (if enabled)
if self.global_config.final_review.enabled:
    result['stages_completed'].append('final_review')

    review = self.llm_service.final_review(
        original_code=original_code,
        fixed_code=final_code
    )

    if not review['intent_preserved']:
        result['status'] = 'needs-fix'
        result['message'] = f"Intent drift detected: {review['explanation']}"
        result['drift_details'] = review.get('drift_details', [])

        self.db.update_snippet(snippet_id, status='needs-fix')
        self.db.log_event(
            run_id, 'final_review_failed', 'warning',
            f"Intent drift: {review['explanation']}"
        )
        return result

    # Intent preserved - continue to verification
    self.db.log_event(
        run_id, 'final_review_passed', 'info',
        f"Intent preserved (confidence: {review['confidence']})"
    )
```

**Configuration** (from plan lines 274-287):
```json
// config/global.json
"final_review": {
  "enabled": true,
  "confidence_threshold": 0.7,
  "model": "sonnet-4.5",  // Use high-quality model
  "timeout_seconds": 30
}
```

**Acceptance Criteria**:
- [ ] `final_review()` method added to LLMService
- [ ] Stage 5.5 integrated in orchestrator after compilation
- [ ] Prompt includes both original and fixed code
- [ ] LLM response parsed and validated (JSON schema)
- [ ] Intent drift detected → snippet marked needs-fix
- [ ] Intent preserved → snippet continues to verification
- [ ] Drift details logged to database
- [ ] Config option to enable/disable final review
- [ ] Unit tests pass: `pytest tests/test_final_review.py -v` (5+ tests)

**Test Cases** (from plan lines 289-348):
```python
def test_final_review_detects_intent_drift():
    """Test that final review catches intent drift."""
    original = """
    var archive = new Archive();
    archive.CreateEntry("file.txt", new FileInfo("source.txt"));
    archive.Save("output.zip");
    """

    # Fixed code changed functionality (wrong!)
    fixed = """
    using (var archive = new Archive())
    {
        archive.ExtractToDirectory("output.zip");  // WRONG - extracts instead of creates!
    }
    """

    review = llm_service.final_review(original, fixed)
    assert review['intent_preserved'] == False
    assert 'extract' in review['explanation'].lower()

def test_final_review_approves_valid_fix():
    """Test that final review approves semantically equivalent fix."""
    original = """
    Archive archive = new Archive();
    archive.CreateEntry("file.txt", new FileInfo("source.txt"));
    """

    # Fixed code same functionality (OK - just added using)
    fixed = """
    using (var archive = new Archive())
    {
        archive.CreateEntry("file.txt", new FileInfo("source.txt"));
    }
    """

    review = llm_service.final_review(original, fixed)
    assert review['intent_preserved'] == True
```

**Expected Impact**:
- Prevents verified snippets with wrong functionality
- Catches cases where LLM "fixes" by changing behavior
- Low cost (only runs after compilation succeeds - rare)
- High value (prevents false positives in verification)

**Plan Reference**: intent-drift-prevention.md lines 88-399

---

## Phase 4: Enhanced Configuration (Week 4)

### Task ID-02: Drift Threshold Gate

**ID**: ID-02
**Scope**: Implement drift score computation and threshold gating for fix attempts
**Owner-Agent**: Agent B (Implementation)
**Priority**: P1 (MEDIUM - Prevents runaway drift)
**Status**: BLOCKED (needs ID-04 foundation)
**Risk**: MEDIUM (adds complexity to fix loop)
**Estimated Time**: 10 hours
**Expected Impact**: Prevents LLM from drifting too far from original during fix iterations

**Gap Linkage**: Fixes ID-GAP-02 (No drift threshold - LLM can drift arbitrarily far during fixes)

**Dependencies**: ID-04 (establishes final review concept)

**Problem**: Current fix loop has no drift budget:
- LLM can change code drastically across multiple iterations
- By iteration 5, code may be completely different from original
- No mechanism to abort when drift exceeds threshold

**Solution**: Compute drift score after each LLM fix attempt:
1. Embed original_code and current_code using sentence-transformers
2. Compute cosine similarity (1.0 = identical, 0.0 = completely different)
3. Drift score = 1.0 - similarity
4. If drift > threshold (e.g., 0.3): abort fix loop, mark needs-manual-review

**Affected Paths**:
- `src/services/drift_detector.py` (NEW - ~200 lines) - Drift computation service
- `src/pipeline/orchestrator.py` (UPDATE - add drift check in fix loop)
- `config/global.json` (UPDATE - add drift threshold config)
- `tests/test_drift_detector.py` (NEW - ~80 lines)

**IMPORTANT** (from HEALING_PLANS_AUDIT_SUMMARY):
- Drift computed against `original_code`, NOT previous iteration
- Reuse VectorDBService embedding model (don't instantiate new SentenceTransformer)
- Model instantiation is expensive (~2 seconds) - only create once

**Drift Detection Service** (from plan lines 434-511):
```python
from sentence_transformers import SentenceTransformer
import numpy as np
from typing import Tuple

class DriftDetector:
    """Detects semantic drift between original and fixed code."""

    def __init__(self, model: SentenceTransformer):
        """
        Initialize with existing embedding model.

        Args:
            model: SentenceTransformer from VectorDBService (reuse to avoid instantiation cost)
        """
        self.model = model

    def compute_drift(
        self,
        original_code: str,
        fixed_code: str
    ) -> Tuple[float, float]:
        """
        Compute drift score between original and fixed code.

        Returns:
            (drift_score, similarity)
            drift_score: 0.0 (identical) to 1.0 (completely different)
            similarity: 1.0 (identical) to 0.0 (completely different)
        """
        # Embed both code snippets
        original_embedding = self.model.encode(original_code)
        fixed_embedding = self.model.encode(fixed_code)

        # Compute cosine similarity
        similarity = np.dot(original_embedding, fixed_embedding) / (
            np.linalg.norm(original_embedding) * np.linalg.norm(fixed_embedding)
        )

        # Drift = 1 - similarity
        drift_score = 1.0 - similarity

        return drift_score, similarity
```

**Integration Point** (from plan lines 513-583):
```python
# In orchestrator.py, fix loop (after each LLM fix attempt)

# Initialize drift detector (reuse VectorDBService model)
if not hasattr(self, '_drift_detector'):
    from src.services.vector_db_service import VectorDBService
    vector_db = VectorDBService(self.db)
    self._drift_detector = DriftDetector(vector_db.model)

# After LLM generates fixed code
drift_score, similarity = self._drift_detector.compute_drift(
    original_code=original_code,  # IMPORTANT: Compare against original, not previous iteration
    fixed_code=current_code
)

# Log drift score
self.db.update_snippet(
    snippet_id,
    drift_score=drift_score,
    drift_similarity=similarity
)

# Check threshold
drift_threshold = self.global_config.drift.threshold
if drift_score > drift_threshold:
    result['status'] = 'needs-manual-review'
    result['message'] = f"Drift threshold exceeded ({drift_score:.3f} > {drift_threshold})"
    result['drift_score'] = drift_score

    self.db.log_event(
        run_id, 'drift_threshold_exceeded', 'error',
        f"Drift {drift_score:.3f} exceeds threshold {drift_threshold}"
    )
    return result  # Abort fix loop

# Continue with compilation...
```

**Configuration** (from plan lines 585-599):
```json
// config/global.json
"drift": {
  "enabled": true,
  "threshold": 0.3,
  "fail_on_exceed": true,
  "log_all_drift_scores": true
}
```

**Database Schema Update** (from plan lines 601-618):
```sql
-- Add drift columns to snippets table
ALTER TABLE snippets ADD COLUMN drift_score REAL;
ALTER TABLE snippets ADD COLUMN drift_similarity REAL;

-- Add drift threshold status
-- status enum now includes: verified, needs-fix, needs-manual-review, unfixable
```

**Acceptance Criteria**:
- [ ] `DriftDetector` class implemented
- [ ] Reuses VectorDBService model (no duplicate instantiation)
- [ ] Drift computed against original_code (not previous iteration)
- [ ] Drift score and similarity logged to database
- [ ] Threshold check aborts fix loop when exceeded
- [ ] Snippet marked 'needs-manual-review' when drift exceeds threshold
- [ ] Config option to enable/disable drift detection
- [ ] Unit tests pass: `pytest tests/test_drift_detector.py -v` (6+ tests)
- [ ] Performance: drift computation < 100ms per check

**Test Cases** (from plan lines 620-688):
```python
def test_drift_detector_identical_code():
    """Test drift score is 0.0 for identical code."""
    code = "using Aspose.Zip; var archive = new Archive();"
    drift_score, similarity = detector.compute_drift(code, code)

    assert drift_score < 0.01  # Nearly identical
    assert similarity > 0.99

def test_drift_detector_completely_different():
    """Test drift score is high for unrelated code."""
    original = "using Aspose.Zip; var archive = new Archive();"
    different = "using System.Net.Http; var client = new HttpClient();"
    drift_score, similarity = detector.compute_drift(original, different)

    assert drift_score > 0.5  # Significant drift
    assert similarity < 0.5

def test_drift_detector_minor_changes():
    """Test drift score is low for minor syntax changes."""
    original = "Archive archive = new Archive();"
    fixed = "using (var archive = new Archive()) { }"  # Added using, var
    drift_score, similarity = detector.compute_drift(original, fixed)

    assert drift_score < 0.2  # Low drift
    assert similarity > 0.8
```

**Threshold Recommendations** (from plan lines 690-719):
- 0.0-0.1: Trivial changes (syntax, formatting, minor refactoring)
- 0.1-0.2: Minor changes (added using statements, changed var to explicit type)
- 0.2-0.3: Moderate changes (restructured code, added try-catch)
- 0.3-0.5: Significant changes (different API usage, changed logic flow)
- 0.5+: Major drift (completely different approach, likely wrong intent)

**Recommended threshold**: 0.3 (conservative - allows moderate changes but blocks major drift)

**Plan Reference**: intent-drift-prevention.md lines 401-876

---

## Phase 5: Advanced Features (Week 5+)

### Task IH-03: Align Architecture Documentation

**ID**: IH-03
**Scope**: Update architecture.md to reflect current system state
**Owner-Agent**: Agent D (Docs & Specs)
**Priority**: P2 (MEDIUM - Documentation alignment)
**Status**: PENDING (documentation-only)
**Risk**: ZERO (doc updates only)
**Estimated Time**: 8 hours
**Expected Impact**: Accurate documentation for onboarding and reference

**Gap Linkage**: Fixes IH-GAP-03 (architecture.md outdated - doesn't reflect current implementation)

**Affected Paths**:
- `docs/architecture.md` (UPDATE - comprehensive rewrite)

**Current Issues** (from infrastructure-hardening.md):
- Missing: Multi-phase pipeline architecture
- Missing: Telemetry system integration
- Missing: Git commit automation (Phase F)
- Missing: Namespace validation layer
- Missing: Pattern detection layer
- Missing: Dependency resolution system
- Outdated: Database schema (missing new tables)
- Outdated: Service layer description

**Required Sections**:
1. **System Overview** - High-level architecture diagram
2. **Pipeline Phases** - Discovery, Compilation, Runtime, Markdown Update, Finalization, Git Commit
3. **Service Layer** - All services documented (LLM, Discovery, Compilation, Runtime, Markdown, Telemetry, VectorDB, Dependency)
4. **Database Schema** - All tables documented with relationships
5. **Configuration System** - Global, family, CLI override hierarchy
6. **Validation Flow** - Stage-by-stage breakdown
7. **Quality Gates** - Namespace validation, pattern detection, drift detection, infinite loop detection
8. **Extensibility Points** - How to add new families, new validators, new patterns

**Acceptance Criteria**:
- [ ] Architecture diagram updated (Mermaid or ASCII art)
- [ ] All pipeline phases documented with flow
- [ ] All services documented with responsibilities
- [ ] Database schema documented with ER diagram
- [ ] Configuration hierarchy explained
- [ ] Quality gates section added
- [ ] Code examples for key extension points
- [ ] Links to relevant source files
- [ ] Document reviewed for accuracy (no outdated information)

**Verification**:
- [ ] Peer review confirms accuracy
- [ ] All links resolve correctly
- [ ] Diagrams render correctly in markdown viewer

**Plan Reference**: infrastructure-hardening.md (IH-03 taskcard)

---

## Queued Tasks (Lower Priority)

### CD-03: Make Gist Pattern Detection Configurable
**ID**: CD-03
**Priority**: P2 (MEDIUM)
**Status**: QUEUED (after CD-01, CD-02)
**Estimated Time**: 8 hours
**Plan Reference**: configurable-discovery.md lines 597-840

### CD-04: Make Context Extraction Configurable
**ID**: CD-04
**Priority**: P2 (MEDIUM)
**Status**: QUEUED (after CD-01, CD-02)
**Estimated Time**: 10 hours
**Plan Reference**: configurable-discovery.md lines 842-1097

### ID-01: Add Drift Score Computation and Tracking
**ID**: ID-01
**Priority**: P2 (MEDIUM)
**Status**: QUEUED (covered by ID-02)
**Note**: ID-02 includes drift computation, so ID-01 may be redundant
**Plan Reference**: intent-drift-prevention.md lines 878-1119

### ID-03: Original-Anchored Fix Prompts
**ID**: ID-03
**Priority**: P2 (MEDIUM)
**Status**: QUEUED (after ID-02)
**Estimated Time**: 6 hours
**Plan Reference**: intent-drift-prevention.md lines 1121-1330

### ID-05: Selective Vector DB Storage (High-Drift Exclusion)
**ID**: ID-05
**Priority**: P2 (MEDIUM)
**Status**: QUEUED (after ID-02)
**Estimated Time**: 8 hours
**Plan Reference**: intent-drift-prevention.md lines 1332-1546

### ID-06: Drift Metrics Dashboard
**ID**: ID-06
**Priority**: P3 (LOW)
**Status**: QUEUED (after ID-05)
**Estimated Time**: 12 hours
**Plan Reference**: intent-drift-prevention.md lines 1548-1757

---

## Parallel Execution Strategy

### Wave 1: Foundation (Start Immediately) - Parallel
**Agents A + C + D**
- **CT-01** (Agent A) - 8 hours - Static Import Analyzer
- **CT-02** (Agent C) - 4 hours - CLI Smoke Tests
- **IH-02** (Agent D) - 3 hours - Fix CLI Entry Point
- **IH-04** (Agent D) - 2 hours - Repository Hygiene

**Total Wall Time**: ~8 hours (parallel)

### Wave 2: Testing & CI (After Wave 1) - Parallel
**Agents C + E**
- **CT-04** (Agent E) - 2 hours - CI Integration (needs CT-01, CT-02)
- **CT-03** (Agent C) - 6 hours - Matrix Tests (needs CT-02)

**Total Wall Time**: ~6 hours (parallel)

### Wave 3: Discovery & Drift (After Wave 2) - Parallel
**Agents B (x2 parallel tasks)**
- **CD-01** (Agent B) - 12 hours - Configurable Fence Detection
- **CD-02** (Agent B) - 10 hours - Content Filtering (can run parallel with CD-01)
- **ID-04** (Agent B) - 8 hours - Final Review (can run parallel with CD tasks)

**Total Wall Time**: ~12 hours (parallel CD-01 + CD-02 = 12h max)

### Wave 4: Advanced Configuration (After Wave 3)
**Agent B**
- **ID-02** (Agent B) - 10 hours - Drift Threshold Gate (needs ID-04)

**Total Wall Time**: ~10 hours

### Wave 5: Documentation (After Wave 4)
**Agent D**
- **IH-03** (Agent D) - 8 hours - Architecture Docs

**Total Wall Time**: ~8 hours

---

## Critical Path Summary

**Total Sequential Time**: ~44 hours (if run sequentially)
**Total Parallel Time**: ~44 hours (optimized with max 3 agents in parallel)
**Total Calendar Time**: ~1-2 weeks (with agent spawn overhead)

**Priority Sequence** (for user impact):
1. CLI Testing (CT-01, CT-02) - Prevents production failures ⭐
2. Infrastructure (IH-02, IH-04) - User experience improvements
3. CI Integration (CT-04, CT-03) - Automates validation
4. Discovery Config (CD-01, CD-02) - Flexible pattern detection
5. Intent Drift (ID-04, ID-02) - Prevents false positives
6. Documentation (IH-03) - Knowledge preservation

---

## Success Metrics

### Primary Metrics (Must Achieve)
- [ ] CLI static analyzer catches at least 1 import error in existing code
- [ ] CLI smoke tests pass on all commands (run, discover, compile, validate)
- [ ] Repository root directory clean (< 10 files in root)
- [ ] Discovery filters out non-code snippets (JSON, XML, output)
- [ ] Final review catches at least 1 intent drift case in testing

### Secondary Metrics (Target)
- [ ] CI workflow passes on first run
- [ ] Discovery pattern customization works for at least 2 families
- [ ] Drift detection reduces verification false positives by 10%+

### Quality Gate
**Threshold**: 4.0/5 minimum on ALL 12 dimensions for each task
**Pass Rate Target**: 100% (no routing-backs required)

---

## Risk Assessment

### High Risks
- **CD-01, CD-02**: Discovery logic changes may break existing families
  - **Mitigation**: Comprehensive tests on ZIP family first, regression testing
- **ID-02**: Drift detection may have false positives (abort valid fixes)
  - **Mitigation**: Conservative threshold (0.3), extensive testing, logging all decisions

### Medium Risks
- **CT-01**: AST analyzer may have false positives/negatives
  - **Mitigation**: Test on real CLI code, handle all scope types, builtin detection

### Low Risks
- **IH-02, IH-04, CT-02, CT-04, ID-04, IH-03**: All low-risk enhancements
  - **Mitigation**: Standard testing, backward compatibility checks

---

**Status**: READY TO START
**Next Action**: Identify PLAN_FIX tasks, then spawn Agent A for CT-01 (Static Import Analyzer)

**Next Action**: Begin implementation with WS1 (Config Updates)
