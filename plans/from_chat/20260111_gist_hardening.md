# Gist Support Feature Hardening Plan

**Created**: 2026-01-11
**Source**: Post-merge self-review gap analysis
**Status**: ACTIVE
**Owner**: Orchestrator

---

## Context

Gist support feature merged to main (commit 6e2278d) with 14/14 unit tests passing. Self-review identified gaps in production readiness:
- Thoroughness: 3.5/5 (missing end-to-end validation)
- Production grading: 3/5 (no real API validation)
- Testability: 3/5 (unit tests only, no integration)
- Robustness: 3/5 (error paths not validated)
- Observability: 3/5 (telemetry not demonstrated)

**Risk**: Feature may fail in production with real GitHub API, cache corruption, or scale issues.

---

## Goals

1. **End-to-End Validation**: Prove feature works with real gist shortcodes and GitHub API
2. **Integration Testing**: Add opt-in tests with real external dependencies
3. **Cache Validation**: Verify cache directory structure and add integrity checks
4. **Performance Validation**: Benchmark with realistic workload (100+ gists)
5. **Production Documentation**: Add security and operational guidance

**Success Criteria**: All self-review dimensions ≥4/5 with concrete evidence

---

## Assumptions (MUST VERIFY)

1. **UNVERIFIED**: GitHub API public endpoints work without auth (rate limit 60/hr)
2. **UNVERIFIED**: cache/gists/ directory auto-creates with proper permissions
3. **UNVERIFIED**: Database handles concurrent gist inserts safely
4. **UNVERIFIED**: ETag caching reduces API calls by >80% in practice
5. **UNVERIFIED**: Single gist fetch completes in <2 seconds on average

**Verification Required**: Each assumption needs evidence (logs, tests, measurements)

---

## Steps

### Step 1: End-to-End Smoke Test
**Owner**: Agent C (Tests & Verification)
**Priority**: P0 (blocks production use)

**Actions**:
1. Create minimal family config: `config/families/test.json`
2. Create test content: `test-content/gist-smoke.md` with real public gist
3. Run: `discover --family test --max-pages 1`
4. Verify cache directory created: `cache/gists/<gist-id>.json`
5. Verify database entries: query gists and gist_files tables
6. Run: `patch --family test --dry-run`
7. Capture all output to `reports/agents/agent-c/e2e-smoke/evidence.md`

**Acceptance Criteria**:
- [ ] Gist fetched successfully from real GitHub API
- [ ] Cache directory structure matches design (JSON + raw files)
- [ ] Database entries correct (gist metadata + file content)
- [ ] Patch dry-run shows correct replacement logic
- [ ] All commands complete without errors
- [ ] Evidence file contains full command output

**Tests**: Add `tests/test_e2e_smoke.py` (can be slow, mark @pytest.mark.slow)

**Rollback**: Delete test family config, test content, cache entries

---

### Step 2: Integration Test Suite
**Owner**: Agent C (Tests & Verification)
**Priority**: P0 (robustness validation)

**Actions**:
1. Create `tests/test_gist_integration.py`
2. Add pytest markers: `@pytest.mark.integration`, `@pytest.mark.skipif(not GITHUB_TOKEN)`
3. Test real API scenarios:
   - Valid gist fetch (single .cs file)
   - Multi-file gist with ambiguous selection
   - Non-existent gist (404)
   - Rate limit simulation (if possible)
   - Network timeout handling
4. Test cache behavior:
   - First fetch (cache miss)
   - Second fetch (cache hit with ETag)
   - Cache corruption recovery
5. Document in `tests/README.md`: how to run integration tests

**Acceptance Criteria**:
- [ ] Integration tests cover 5+ real API scenarios
- [ ] Tests pass with real GitHub API (when GITHUB_TOKEN set)
- [ ] Tests skip gracefully when token not available
- [ ] Cache hit/miss behavior validated
- [ ] Error scenarios tested (404, timeout)
- [ ] Documentation explains opt-in testing

**Tests**: Self-contained in test_gist_integration.py

**Rollback**: Integration tests are opt-in, safe to merge without running

---

### Step 3: Cache Validation & Recovery
**Owner**: Agent B (Implementation)
**Priority**: P1 (operational safety)

**Actions**:
1. Add `GistService.verify_cache()` method
2. Check cache/*.json files are valid JSON
3. Check cache structure matches expected format
4. Remove corrupted files, log warnings
5. Call verify_cache() in cli.py discover command startup
6. Add unit tests: `tests/test_cache_validation.py`
7. Document in `docs/operations.md`: cache maintenance procedures

**Acceptance Criteria**:
- [ ] verify_cache() detects corrupted JSON files
- [ ] Corrupted files removed automatically
- [ ] Warnings logged with file paths
- [ ] Unit tests cover: valid cache, corrupted JSON, missing files
- [ ] Operations doc explains cache clearing procedure
- [ ] No crashes from cache corruption

**Tests**: tests/test_cache_validation.py with mocked filesystem

**Rollback**: Method is defensive, safe to add

---

### Step 4: Performance Benchmarking
**Owner**: Agent E (Observability & Ops)
**Priority**: P2 (scalability proof)

**Actions**:
1. Create `tests/benchmark_gist_performance.py`
2. Generate test data: 100 mock gists in database
3. Measure:
   - Time to fetch 100 gists (with/without cache)
   - Cache hit rate
   - Database query performance
   - Memory usage during bulk operations
4. Document baseline performance in `docs/performance.md`
5. Add to CI as optional step (long-running)

**Acceptance Criteria**:
- [ ] Benchmark runs with 100+ gists
- [ ] Cache hit rate measured (expect >80%)
- [ ] Fetch time per gist documented (expect <2s)
- [ ] Database query performance acceptable (expect <100ms)
- [ ] Memory usage reasonable (expect <500MB for 100 gists)
- [ ] Baseline documented for future regression testing

**Tests**: Benchmark script with performance assertions

**Rollback**: Benchmark is analysis only, no production impact

---

### Step 5: Security & Operations Documentation
**Owner**: Agent D (Docs & Specs)
**Priority**: P1 (production readiness)

**Actions**:
1. Create `docs/security.md`:
   - GITHUB_TOKEN permission scopes required
   - Secure storage options (env var, secrets manager)
   - Rate limit security (avoiding token exhaustion)
   - Gist content trust model (public gists only)
2. Create `docs/operations.md`:
   - Cache management (size monitoring, clearing)
   - Database maintenance (gist cleanup queries)
   - Monitoring metrics (fetch success rate, cache hit rate)
   - Troubleshooting guide (common errors, solutions)
3. Update `docs/configuration.md` with security references

**Acceptance Criteria**:
- [ ] GITHUB_TOKEN scopes documented (repo:public_repo or none for public)
- [ ] Cache size monitoring commands provided
- [ ] Database cleanup queries tested and documented
- [ ] Troubleshooting guide covers 5+ common issues
- [ ] Security doc reviewed for completeness
- [ ] Links added to main README

**Tests**: None (documentation only)

**Rollback**: Documentation addition, no risk

---

## Evidence Commands

```bash
# End-to-End Smoke Test
python src/cli.py discover --family test --max-pages 1
ls -la cache/gists/
python -c "import sqlite3; conn = sqlite3.connect('data/examples.db'); print(conn.execute('SELECT * FROM gists').fetchall())"
python src/cli.py patch --family test --dry-run

# Integration Tests
pytest tests/test_gist_integration.py -v -m integration --github-token=$GITHUB_TOKEN

# Cache Validation
python -c "from gist_service import GistService; gs = GistService(); gs.verify_cache()"

# Performance Benchmark
python tests/benchmark_gist_performance.py --gists=100

# Documentation Review
grep -r "GITHUB_TOKEN" docs/
wc -l docs/security.md docs/operations.md
```

---

## Risks & Rollback

### Risk 1: Real API rate limits during testing
**Mitigation**: Use GITHUB_TOKEN for testing, cache aggressively
**Rollback**: Skip integration tests if token unavailable

### Risk 2: Performance benchmark reveals scalability issues
**Mitigation**: Document as known limitation, optimize in future sprint
**Rollback**: None (benchmark is analysis)

### Risk 3: Cache validation breaks existing workflows
**Mitigation**: Make validation opt-in initially, warn only (no removal)
**Rollback**: Remove verify_cache() call from discover command

### Risk 4: Documentation reveals security gaps
**Mitigation**: Address gaps before publishing, escalate if major
**Rollback**: Keep docs internal until reviewed

---

## Acceptance Criteria (GATE)

**Must pass ALL for production ready**:

- [ ] End-to-end smoke test passes with real gist
- [ ] Cache directory structure verified in practice
- [ ] Integration tests added and documented (opt-in)
- [ ] Cache validation implemented and tested
- [ ] Performance baseline documented (100+ gists)
- [ ] Security documentation complete
- [ ] Operations runbook complete
- [ ] All self-review dimensions ≥4/5
- [ ] Evidence files exist for each step
- [ ] No Known Gaps in agent self-reviews

---

## Dependencies

**Required**:
- Main branch with gist support (commit 6e2278d) ✅
- Python dependencies installed ✅
- pytest with markers support ✅

**Optional**:
- GITHUB_TOKEN for integration tests (improves coverage)
- dotnet SDK for full validation workflow (not critical)

---

**Status**: Ready for agent assignment
