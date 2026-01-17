# Telemetry System Healing Plan

## Context

⚠️ **CRITICAL CORRECTION**: This plan was originally written for a different telemetry implementation. **The actual implementation is split between two files**:

**Current Reality**:
- **`src/services/telemetry_service.py`** - `TelemetryService` class with HTTP API + SQLite dual-write
  - `start_run()` method exists (line 106) - posts run to API
  - `update_run()` method exists (line 139) - updates run via PATCH
  - `associate_commit()` method exists (line 222) - associates commits with runs
- **`src/core/telemetry.py`** - Utility functions and context managers
  - `track_phase_timing()` context manager exists - records phase durations
  - `export_run_telemetry()` function exists - exports telemetry to files
- **No `TelemetryClient` class** - this was assumed incorrectly
- **No NDJSON dual-write** - uses HTTP API + SQLite, not NDJSON files
- **HTTP API already configured** - `TelemetryConfig` has `http_api_enabled`, `http_api_url`, timeouts, retries (config/global.json lines 40-48)

**Actual Gaps** (refined from original assumptions):
1. **Test coverage incomplete**: TelemetryService methods lack comprehensive tests
2. **Schema compliance unverified**: No tests verifying HTTP API payload matches spec
3. **Failure modes untested**: Need tests for graceful degradation when API unavailable
4. **Commit association untested**: `associate_commit()` exists but lacks test coverage
5. **Phase timing integration**: Verify `track_phase_timing()` covers all pipeline phases

**Reference:** See [src/services/telemetry_service.py](../src/services/telemetry_service.py) and [src/core/telemetry.py](../src/core/telemetry.py)

## Repo Reality Check

**Purpose**: Verify telemetry implementation before making changes.

### Validation Commands

```bash
# 1. Check if src/telemetry.py exists (plan assumes TelemetryClient here)
[ -f src/telemetry.py ] && echo "EXISTS" || echo "MISSING: src/telemetry.py"

# 2. Verify actual telemetry implementation files
[ -f src/services/telemetry_service.py ] && echo "EXISTS: TelemetryService" || echo "MISSING"
[ -f src/core/telemetry.py ] && echo "EXISTS: telemetry utilities" || echo "MISSING"

# 3. Check for TelemetryClient class (plan assumes it exists)
grep -rn "class TelemetryClient" src/ 2>/dev/null || echo "MISSING: TelemetryClient class"

# 4. Check for TelemetryService class
grep -n "class TelemetryService" src/services/telemetry_service.py

# 5. Verify record_timing() method (plan says it's missing)
grep -rn "def record_timing" src/ 2>/dev/null || echo "MISSING: record_timing()"

# 6. Verify track_phase_timing() (actual timing implementation)
grep -n "def track_phase_timing" src/core/telemetry.py

# 7. Check HTTP API configuration
grep -A 10 '"http_api' config/global.json

# 8. Verify TelemetryService methods exist
grep -n "def start_run\|def update_run\|def associate_commit" src/services/telemetry_service.py
```

### Reality Check Results

| Assumption | Status | Evidence |
|------------|--------|----------|
| `TelemetryClient` in `src/telemetry.py` | ❌ **INCORRECT** | No such class - actual is `TelemetryService` |
| NDJSON dual-write pattern | ❌ **INCORRECT** | Uses HTTP API + SQLite, not NDJSON files |
| Missing `record_timing()` | ❌ **MISLEADING** | `track_phase_timing()` context manager exists and works |
| No HTTP API configuration | ❌ **INCORRECT** | `TelemetryConfig` has full HTTP API settings in config |
| Zero test coverage | ⚠️ **PARTIALLY CORRECT** | Some tests exist (tests/test_telemetry_*.py), but coverage incomplete |
| `associate_commit()` missing | ❌ **INCORRECT** | Method exists at telemetry_service.py:222 |
| `persistent_fix_service.py` exists | ❌ **INCORRECT** | No such file in repository |

### Go/No-Go Decision

⚠️ **RESCOPE REQUIRED** - Plan targets non-existent `TelemetryClient` and assumes NDJSON implementation.

**Revised Scope**:
- **TM-01**: ~~Implement record_timing()~~ → **OBSOLETE** - `track_phase_timing()` already works
- **TM-02**: ~~Add HTTP API config~~ → **Add schema compliance tests for existing HTTP API**
- **TM-03**: **Add comprehensive tests for TelemetryService** ← MOST VALUABLE (keep and expand)
- **TM-04**: ~~Extend metric support~~ → **Verify telemetry exports include all needed metrics**

**Estimated Reality Check Time**: 15 minutes

---

## Gap → Taskcard Mapping (REVISED)

| Gap/Blocker ID | Description | Taskcard ID(s) | Status |
|----------------|-------------|----------------|--------|
| TM-GAP-01 | ~~Missing `record_timing()`~~ | ~~TM-01~~ | ✅ **EXISTS** - `track_phase_timing()` works |
| TM-GAP-02 | ~~No HTTP API configuration~~ | ~~TM-02~~ | ✅ **EXISTS** - Full config in global.json |
| TM-GAP-03 | Incomplete test coverage for TelemetryService | TM-03 | ⚠️ **VALID** - Need comprehensive tests |
| TM-GAP-04 | ~~Incomplete metric support~~ | ~~TM-04~~ | ✅ **ADEQUATE** - Metrics work, just verify |
| TM-GAP-05 | Schema compliance unverified | TM-02 (revised) | ⚠️ **VALID** - Need API contract tests |
| TM-GAP-06 | Failure modes untested (API down, timeout, etc) | TM-03 | ⚠️ **VALID** - Need degradation tests |

---

## Taskcard TM-01: ~~Implement record_timing()~~ → OBSOLETE

⚠️ **STATUS: NOT NEEDED** - This taskcard is OBSOLETE. **`track_phase_timing()` context manager already exists** in src/core/telemetry.py.

**Gap Linkage:** ~~Fixes TM-GAP-01 (Missing `record_timing()`)~~ - **Gap does not exist**

**Priority:** ~~⚠️ CRITICAL~~ → ✅ **RESOLVED** - Timing already implemented

**Role:** ~~Senior engineer delivering timing metric support~~ **NOT APPLICABLE**

---

**IMPORTANT:** The plan assumed a `TelemetryClient.record_timing()` method was missing and causing `AttributeError` crashes. **This is incorrect**:

- ✅ `track_phase_timing()` context manager exists in `src/core/telemetry.py` (lines 20-93)
- ✅ Used throughout orchestrator.py to wrap phase execution
- ✅ Records duration_ms, success, metadata to database
- ✅ No crashes - this functionality works correctly

**This taskcard should be SKIPPED. No action required.**

---

### ~~Original Taskcard Details~~ (For Reference Only - DO NOT IMPLEMENT)

### Scope

**Fix:**
- Implement `record_timing(metric_name: str, duration_ms: int)` method in `TelemetryClient` class
- Update call site in `persistent_fix_service.py:256` to use the new method correctly
- Ensure timing metrics are logged to NDJSON and HTTP API (dual-write pattern)
- Store timing metrics in `metrics_json` field for telemetry API compatibility (see `docs/local-telemetry.md` schema)
- Support min/max/avg/count aggregation for timing metrics

**Allowed paths:**
- `src/telemetry.py` - add `record_timing()` method
- `src/persistent_fix_service.py` - verify call site correctness
- `test_telemetry_timing.py` - new test file

**Forbidden:** Any other file/path

### Acceptance Checks

**CLI:**
- Run `python src/cli.py validate --family zip` with persistent fix service enabled
- No `AttributeError` for `record_timing()`
- Timing metrics appear in `artifacts/runs/run_*/metrics.json` with keys like `persistent_fix_duration_avg`, `persistent_fix_duration_min`, `persistent_fix_duration_max`, `persistent_fix_duration_count`
- If HTTP API configured, timing metrics sent to `TELEMETRY_API_URL/api/v1/runs/{event_id}` in `metrics_json` field

**UI/Web/API:**
- N/A (CLI-only feature)

**Tests:**
- `pytest test_telemetry_timing.py` passes
- Test verifies timing metrics written to NDJSON
- Test verifies timing metrics aggregated correctly (min/max/avg/count)
- Test verifies HTTP API receives timing events in `metrics_json` field (with mock server)

**Config respected end-to-end:**
- Timing metrics work with and without HTTP API URL configured
- Dry-run mode doesn't write timing metrics

**No mock data in production paths:**
- Real timing values from `time.time()` used in production
- Only test code uses mock timing values

### Deliverables

1. **Full file replacement for `src/telemetry.py`:**
   - Add `record_timing(metric_name: str, duration_ms: int)` method
   - Store timings in `self._timing_metrics` dict with structure: `{metric_name: [values]}`
   - Aggregate on `save_metrics()`: compute min/max/avg/count for each timing metric
   - Store timing aggregations in `metrics_json` for API compatibility (JSON field per telemetry API spec)
   - Log timing event to NDJSON with event_type `timing_recorded`
   - Send timing metrics to HTTP API via PATCH `/api/v1/runs/{event_id}` with `metrics_json` field if configured

2. **Updated `src/persistent_fix_service.py`:**
   - Verify line 256 call is correct (no changes needed if signature matches)

3. **New test file `test_telemetry_timing.py`:**
   - Test happy path: record single timing, verify NDJSON event
   - Test aggregation: record multiple timings, verify min/max/avg/count in metrics.json
   - Test HTTP API: verify timing metrics sent in `metrics_json` field (mocked)
   - Test failure path: HTTP API timeout doesn't crash timing recording

4. **Forward-compatible migration:**
   - Existing metrics.json files without timing metrics continue to load
   - Old NDJSON events without timing data continue to parse

### Hard Rules

- ✅ Keep public signatures: `TelemetryClient.__init__()` signature unchanged
- ✅ No network in offline tests: Use `responses` or `unittest.mock` for HTTP mocking
- ✅ Keep entrypoints in parity: CLI-only feature, no API/UI parity needed
- ✅ Mock vs Live mode: Tests use mock HTTP server; production uses real HTTP client
- ✅ Deterministic runs: Timing values in tests use fixed mock values
- ✅ No new deps: Use existing `requests`, `pytest` libraries
- ✅ Keep code/docs/tests in sync: Update docstrings in `telemetry.py`, reference API schema from docs/local-telemetry.md

### Review Dimensions (5/5 Criteria)

| Dimension | 5/5 Means |
|-----------|-----------|
| **Correctness** | `record_timing()` works in all code paths; no AttributeError; all tests pass; API schema compliant |
| **Completeness** | Timing metrics in NDJSON + HTTP API `metrics_json` field + aggregated in metrics.json; min/max/avg/count computed |
| **Robustness** | HTTP failures don't crash timing recording; handles zero/negative durations gracefully |
| **Testability** | 100% code coverage for `record_timing()`; tests cover happy + failure paths |
| **Documentation** | Docstring explains usage, parameters, aggregation, and API schema alignment |
| **Integration** | Works seamlessly with existing `persistent_fix_service.py` call; aligns with telemetry API v2.1.0 spec |

### Now (Runbook)

```bash
# 0. Read telemetry API documentation
cat docs/local-telemetry.md | grep -A 20 "metrics_json"
# Note: metrics_json is a JSON field in the API schema for custom metrics

# 1. Read existing telemetry.py to understand structure
cat src/telemetry.py | grep -A 20 "class TelemetryClient"

# 2. Implement record_timing() method in TelemetryClient class
# Add method after increment_metric() around line 250
# Structure:
#   def record_timing(self, metric_name: str, duration_ms: int) -> None:
#       # Store in self._timing_metrics (dict of lists)
#       # Log event to NDJSON
#       # Send to HTTP API in metrics_json field if configured

# 3. Update save_metrics() to aggregate timing metrics
# Add aggregation logic before saving to metrics.json
# Store timing aggregations in metrics_json for API PATCH updates

# 4. Update HTTP API integration
# When calling PATCH /api/v1/runs/{event_id}, include timing aggregations in metrics_json field

# 5. Create test_telemetry_timing.py
# Test cases: single timing, multiple timings, HTTP API metrics_json, failure paths

# 6. Verify call site in persistent_fix_service.py
grep -n "record_timing" src/persistent_fix_service.py

# 7. Run tests
pytest test_telemetry_timing.py -v

# 8. Integration test with real CLI
python src/cli.py validate --family zip --max-snippets 1

# 9. Verify metrics.json has timing aggregations
cat artifacts/runs/run_*/metrics.json | grep "persistent_fix_duration"

# 10. Verify NDJSON has timing events
cat artifacts/runs/run_*/events.ndjson | grep "timing_recorded"

# 11. If HTTP API configured, verify metrics_json sent
# Start telemetry API: docker run -p 8765:8765 local-telemetry-api:2.1.0
# Run CLI with: export TELEMETRY_API_URL=http://localhost:8765
# Verify via: curl http://localhost:8765/api/v1/runs/{event_id} | jq .metrics_json
```

---

## Taskcard TM-02: ~~Add HTTP API Configuration~~ → Test Schema Compliance for Existing API

⚠️ **RESCOPED** - HTTP API configuration already exists (config/global.json lines 40-48). **TelemetryService** already implements HTTP API integration (lines 106-222 in telemetry_service.py). This taskcard now focuses on **testing schema compliance** with the API spec.

**Status:** Not Started (Rescoped)

**Gap Linkage:** Fixes TM-GAP-05 (Schema compliance unverified)

**Role:** Senior engineer delivering comprehensive schema compliance tests for existing TelemetryService HTTP API integration.

---

### ⚠️ CRITICAL: Test Existing API, Don't Rebuild It

**TelemetryService already has**:
- HTTP API configuration via `TelemetryConfig` (config/global.json lines 40-48)
- `start_run()` method (line 106) - POST /api/v1/runs
- `update_run()` method (line 139) - PATCH /api/v1/runs/{event_id}
- `associate_commit()` method (line 222) - POST /api/v1/runs/{event_id}/associate-commit
- Timeout and retry configuration
- Auth token support (optional)

**Work is to ADD**:
1. Schema compliance tests verifying payloads match docs/local-telemetry.md spec
2. Tests for idempotent behavior (duplicate event_id handling)
3. Tests for graceful degradation (API unavailable, timeout, rate limiting)
4. Integration tests with mock telemetry API server

---

### Scope

**Fix:**
- Add comprehensive tests for `TelemetryService.start_run()` schema compliance
- Add tests for `TelemetryService.update_run()` schema compliance
- Add tests for `TelemetryService.associate_commit()` schema compliance
- Test idempotent POST behavior (duplicate event_id returns 200 OK)
- Test failure modes: API unavailable, timeout, 429 rate limiting, 5xx errors
- Test graceful degradation: telemetry failures don't crash pipeline
- Mock HTTP API server in tests using `responses` library

**Allowed paths:**
- `tests/test_telemetry_service.py` - comprehensive tests for TelemetryService (expand existing)
- `tests/test_telemetry_schema_compliance.py` - new test file for schema validation

**Forbidden:** Any other file/path

### Acceptance Checks

**CLI:**
- N/A - This taskcard focuses on testing existing functionality, not CLI behavior

**UI/Web/API:**
- N/A (CLI-only feature in production, but tests verify API contracts)

**Tests:**
- `pytest tests/test_telemetry_schema_compliance.py -v` passes
- Test verifies `TelemetryService.start_run()` sends correct schema per docs/local-telemetry.md
- Test verifies `TelemetryService.update_run()` sends correct PATCH schema
- Test verifies `TelemetryService.associate_commit()` sends correct commit schema
- Test verifies idempotent POST behavior (duplicate event_id returns 200 OK)
- Test verifies 429 rate limiting handled gracefully (logs warning, doesn't crash)
- Test verifies 500 server errors handled gracefully
- Test verifies timeout handling (connection timeout, read timeout)
- Test verifies API unavailable doesn't crash pipeline

**Config respected end-to-end:**
- HTTP API disabled when `telemetry.http_api_enabled = false` in config
- HTTP API enabled when `telemetry.http_api_enabled = true`
- Timeout respected per `telemetry.http_api_timeout_ms` config
- Auth headers included when `telemetry.http_api_auth_token` configured

**No mock data in production paths:**
- Tests use `responses` library to mock HTTP API
- Production code makes real HTTP requests to configured API URL

### Deliverables

1. **New test file `tests/test_telemetry_schema_compliance.py`:**
   - Comprehensive schema validation tests for existing TelemetryService
   - Test class `TestTelemetryAPISchemaCompliance`:
     - `test_start_run_schema_matches_spec`
     - `test_update_run_schema_matches_spec`
     - `test_associate_commit_schema_matches_spec`
     - `test_idempotent_post_duplicate_event_id`
     - `test_rate_limiting_429_handled_gracefully`
     - `test_server_error_500_doesnt_crash`
     - `test_connection_timeout_handled`
     - `test_api_unavailable_graceful_degradation`
   - Use `responses` library to mock HTTP API:
     ```python
     import responses
     from src.services.telemetry_service import TelemetryService

     @responses.activate
     def test_start_run_schema_matches_spec():
         """Verify start_run() sends correct POST schema per docs/local-telemetry.md"""
         responses.add(
             responses.POST,
             'http://localhost:8765/api/v1/runs',
             json={'status': 'success', 'event_id': '...'},
             status=200
         )

         telemetry = TelemetryService(config=telemetry_config, db=db)
         result = telemetry.start_run(event)

         # Verify request payload
         assert len(responses.calls) == 1
         request_body = responses.calls[0].request.body
         assert 'event_id' in request_body
         assert 'run_id' in request_body
         assert 'agent_name' in request_body
         # ... verify all required fields per spec
     ```

2. **Expanded `tests/test_telemetry_service.py` (existing file):**
   - Add tests for graceful degradation when API fails
   - Add tests for timeout handling
   - Add tests for auth token in headers
   - Test cases:
     - `test_telemetry_continues_when_api_down`
     - `test_telemetry_respects_timeout_config`
     - `test_auth_header_included_when_configured`
     - `test_no_auth_header_when_not_configured`

3. **Schema validation helper (tests/helpers/telemetry_schema.py):**
   - JSON schema definitions from docs/local-telemetry.md:
     ```python
     from jsonschema import validate

     START_RUN_SCHEMA = {
         "type": "object",
         "required": ["event_id", "run_id", "agent_name", "status", "start_time"],
         "properties": {
             "event_id": {"type": "string", "format": "uuid"},
             "run_id": {"type": "string"},
             "agent_name": {"type": "string"},
             "status": {"type": "string", "enum": ["running"]},
             "start_time": {"type": "string", "format": "date-time"},
             ...
         }
     }

     def validate_start_run_payload(payload):
         """Validate start_run payload against API spec."""
         validate(instance=payload, schema=START_RUN_SCHEMA)
     ```

4. **Forward-compatible migration:**
   - Tests validate existing TelemetryService implementation
   - No changes to production code required (unless tests reveal bugs)
   - Tests serve as regression protection for future changes

### Hard Rules

- ✅ Keep public signatures: Add optional parameters with defaults (backwards compatible)
- ✅ No network in offline tests: Mock HTTP requests in tests
- ✅ Keep entrypoints in parity: CLI-only feature
- ✅ Mock vs Live mode: Tests use mock server; production uses real HTTP
- ✅ Deterministic runs: Tests don't depend on external HTTP server state
- ✅ No new deps: Use existing `os`, `requests` libraries; consider `uuid` for event_id
- ✅ Keep code/docs/tests in sync: Reference docs/local-telemetry.md in docstrings and .env.example

### Review Dimensions (5/5 Criteria)

| Dimension | 5/5 Means |
|-----------|-----------|
| **Correctness** | Environment variables read correctly; CLI flag overrides work; timeouts respected; auth headers sent; API schema matches docs/local-telemetry.md v2.1.0 |
| **Completeness** | All configuration options documented; works in all modes (env var, CLI flag, none); auth and timeout configurable; idempotency implemented |
| **Robustness** | Invalid URLs don't crash; network failures graceful; default values sensible; 429 rate limiting handled; duplicate event_id handled |
| **Testability** | Tests cover env var, CLI flag, defaults, timeout, auth, idempotency, rate limiting |
| **Documentation** | .env.example references docs/local-telemetry.md; docstrings explain configuration hierarchy and API integration |
| **Integration** | Works seamlessly with existing telemetry code; no breaking changes; follows telemetry API v2.1.0 spec exactly |

### Now (Runbook)

```bash
# 0. Read telemetry API documentation
cat docs/local-telemetry.md | head -100
# Note the endpoints: POST /api/v1/runs, PATCH /api/v1/runs/{event_id}
# Note the schema requirements: event_id (UUID), run_id, agent_name, job_type, start_time (required)

# 1. Read current CLI initialization
grep -A 10 "TelemetryClient" src/cli.py

# 2. Update src/cli.py
# Add at top: import os, uuid
# Add in discover/validate/patch commands:
#   parser.add_argument('--telemetry-url', type=str, help='HTTP telemetry endpoint (overrides TELEMETRY_API_URL)')
# Read environment variables:
#   telemetry_url = args.telemetry_url or os.getenv('TELEMETRY_API_URL')
#   telemetry_timeout = int(os.getenv('TELEMETRY_API_TIMEOUT_MS', '2000'))
#   auth_enabled = os.getenv('TELEMETRY_API_AUTH_ENABLED', 'false').lower() == 'true'
#   auth_token = os.getenv('TELEMETRY_API_AUTH_TOKEN')
# Pass to TelemetryClient(telemetry_url=telemetry_url, timeout_ms=telemetry_timeout, auth_enabled=auth_enabled, auth_token=auth_token)

# 3. Update src/telemetry.py __init__()
# Add parameters: telemetry_url, timeout_ms, auth_enabled, auth_token
# Generate event_id: self.event_id = str(uuid.uuid4())
# Store config: self.telemetry_url, self.timeout_ms, self.auth_enabled, self.auth_token

# 4. Implement start_run() to POST /api/v1/runs
# Build request body per API schema (see docs/local-telemetry.md lines 268-316)
# Include Authorization header if auth_enabled
# Handle response: 201 Created (new), 200 OK (duplicate)

# 5. Implement finish_run() to PATCH /api/v1/runs/{event_id}
# Build request body per API schema (see docs/local-telemetry.md lines 324-350)
# Include status, end_time, duration_ms, error_summary, metrics_json

# 6. Update .env.example
cat >> .env.example << 'EOF'
TELEMETRY_API_URL=http://localhost:8765
TELEMETRY_API_TIMEOUT_MS=5000
TELEMETRY_API_AUTH_ENABLED=false
TELEMETRY_API_AUTH_TOKEN=your-secret-token-here
EOF

# 7. Create test_telemetry_config.py
# Test cases: env var, CLI flag, defaults, timeout, auth, idempotency

# 8. Run tests
pytest test_telemetry_config.py -v

# 9. Start local telemetry API (if available)
# docker run -p 8765:8765 local-telemetry-api:2.1.0
# Or: python -m uvicorn telemetry_api:app --port 8765

# 10. Integration test with environment variable
export TELEMETRY_API_URL=http://localhost:8765
python src/cli.py discover --family zip --max-pages 1

# 11. Verify API received request
curl "http://localhost:8765/api/v1/runs?agent_name=example-reviewer&limit=1"

# 12. Verify event_id idempotency
# Run same command twice, check logs show "duplicate" status on second run

# 13. Test CLI flag override
python src/cli.py discover --family zip --max-pages 1 --telemetry-url http://localhost:9999

# 14. Test with auth enabled
export TELEMETRY_API_AUTH_ENABLED=true
export TELEMETRY_API_AUTH_TOKEN=test123
python src/cli.py discover --family zip --max-pages 1
# Verify Authorization header sent (check API logs or network traffic)
```

---

## Taskcard TM-03: Add Comprehensive Tests for TelemetryService

⚠️ **RESCOPED** - Test target is **TelemetryService** (src/services/telemetry_service.py), not fictional TelemetryClient. Some tests already exist (tests/test_telemetry_*.py), but coverage is incomplete.

**Status:** Not Started (Rescoped)

**Gap Linkage:** Fixes TM-GAP-03 (Incomplete test coverage), TM-GAP-06 (Failure modes untested)

**Role:** Senior engineer delivering comprehensive test coverage for TelemetryService with HTTP API integration validation.

---

### ⚠️ CRITICAL: Test Existing TelemetryService, Not Fictional TelemetryClient

**Target for testing**:
- **src/services/telemetry_service.py** - TelemetryService class (not TelemetryClient)
- **src/core/telemetry.py** - track_phase_timing() context manager

**Some tests already exist**:
- `tests/test_telemetry_config.py` - telemetry configuration tests
- `tests/test_telemetry_metrics.py` - metric tracking tests
- `tests/test_telemetry_timing.py` - timing tests

**Work is to ADD**:
1. Comprehensive tests for TelemetryService.start_run(), update_run(), associate_commit()
2. Tests for graceful degradation (API down, timeout, rate limiting)
3. Tests for commit association workflow
4. Integration tests with mock HTTP API server

---

### Scope

**Fix:**
- Add comprehensive test suite for `src/services/telemetry_service.py` (target: 90%+ coverage)
- Test TelemetryService methods: start_run(), update_run(), associate_commit()
- Test track_phase_timing() context manager from src/core/telemetry.py
- Test error handling and graceful degradation (API unavailable, timeout, 429, 5xx errors)
- Test HTTP API integration with mocked server
- Test database persistence of telemetry events
- Test commit association workflow end-to-end

**Allowed paths:**
- `tests/test_telemetry_service_comprehensive.py` - new comprehensive test file
- `tests/test_telemetry_integration.py` - new integration test file

**Forbidden:** Any other file/path (no changes to src/services/telemetry_service.py itself)

### Acceptance Checks

**CLI:**
- Run `pytest tests/test_telemetry_service_comprehensive.py -v --cov=src/services/telemetry_service --cov-report=term-missing`
- Coverage ≥ 90% for `src/services/telemetry_service.py`
- All tests pass
- Run `pytest tests/test_telemetry_integration.py -v` - integration tests pass

**UI/Web/API:**
- N/A (test-only taskcard)

**Tests:**
- Test happy path: `start_run()` creates run in database and posts to HTTP API
- Test happy path: `update_run()` updates run in database and patches HTTP API
- Test happy path: `associate_commit()` associates commit with run via HTTP API
- Test failure path: HTTP API timeout doesn't crash TelemetryService methods
- Test failure path: API unavailable (connection refused) handled gracefully
- Test failure path: 429 rate limiting logged as warning, doesn't crash
- Test failure path: 5xx server errors logged as warning, doesn't crash
- Test edge case: `update_run()` without `start_run()` handles gracefully
- Test edge case: multiple calls to `start_run()` with same event_id (idempotency)
- Test `track_phase_timing()` context manager records timing to database
- Test `track_phase_timing()` handles exceptions in wrapped code
- Test database persistence: telemetry events saved correctly
- Test commit association: workflow integrates with Phase F correctly

**Config respected end-to-end:**
- Tests verify HTTP API disabled when `http_api_enabled = false`
- Tests verify HTTP API enabled when `http_api_enabled = true`
- Tests verify timeout respected per config
- Tests verify auth token included in headers when configured

**No mock data in production paths:**
- Tests use temporary databases (SQLite :memory:)
- Tests use `responses` library to mock HTTP API

### Deliverables

1. **New test file `tests/test_telemetry_service_comprehensive.py` (400+ lines):**
   - Pytest fixtures for TelemetryService with temp database and mock HTTP API
   - Test class `TestTelemetryServiceRunLifecycle`:
     - `test_start_run_saves_to_database`
     - `test_start_run_posts_to_http_api`
     - `test_update_run_updates_database`
     - `test_update_run_patches_http_api`
     - `test_associate_commit_posts_to_api`
     - `test_associate_commit_updates_database`
   - Test class `TestTelemetryServiceGracefulDegradation`:
     - `test_start_run_api_unavailable_doesnt_crash`
     - `test_update_run_timeout_doesnt_crash`
     - `test_associate_commit_429_rate_limit_logs_warning`
     - `test_api_500_error_handled_gracefully`
     - `test_connection_refused_doesnt_crash`
   - Test class `TestTelemetryServiceHTTPAPIIntegration`:
     - `test_auth_token_included_in_headers`
     - `test_timeout_respected_in_requests`
     - `test_idempotent_post_duplicate_event_id`
     - `test_http_api_disabled_skips_requests`
   - Test class `TestTrackPhaseTimingContextManager`:
     - `test_track_phase_timing_records_duration`
     - `test_track_phase_timing_handles_exceptions`
     - `test_track_phase_timing_saves_to_database`
     - `test_track_phase_timing_calculates_duration_correctly`
     - `test_auth_headers_not_sent_when_disabled`
     - `test_rate_limiting_429_handled_gracefully`
     - `test_timestamps_iso8601_with_timezone`
     - `test_event_id_is_uuid`
     - `test_run_id_format`

2. **Pytest fixtures in `tests/conftest.py` (if needed):**
   - `temp_artifacts_dir` fixture for temporary directories
   - `mock_http_server` fixture for HTTP API mocking (use `responses` library)

3. **Test fixtures in `tests/fixtures/telemetry/` (if needed):**
   - Example NDJSON events for parsing tests
   - Example metrics.json for structure validation
   - Example API responses (201 Created, 200 OK duplicate, 429 rate limit)

### Hard Rules

- ✅ Keep public signatures: Tests don't modify production code
- ✅ No network in offline tests: All HTTP requests mocked (use `responses` library)
- ✅ Mock vs Live mode: Use `responses` library for HTTP API mocking
- ✅ Deterministic runs: Use fixed timestamps in tests (mock `datetime.now()`)
- ✅ No new deps: Use existing pytest, pytest-cov; use `responses` library for HTTP mocking (if not already installed, check requirements.txt)
- ✅ Keep code/docs/tests in sync: Tests serve as documentation for telemetry usage; tests validate API v2.1.0 schema compliance

### Review Dimensions (5/5 Criteria)

| Dimension | 5/5 Means |
|-----------|-----------|
| **Correctness** | All tests pass; no false positives/negatives; tests actually verify behavior; API schema compliance validated |
| **Completeness** | ≥95% coverage; all public methods tested; all context managers tested; all API endpoints tested (POST /api/v1/runs, PATCH /api/v1/runs/{event_id}) |
| **Robustness** | Tests cover happy path + failure paths + edge cases; HTTP failures, auth, rate limiting, idempotency all tested |
| **Testability** | Tests are maintainable; clear test names; good fixtures; API responses mocked correctly |
| **Documentation** | Test names are self-documenting; fixtures well-documented; tests reference docs/local-telemetry.md schema |
| **Integration** | Tests verify end-to-end behavior (artifacts created, files written, API called correctly) |

### Now (Runbook)

```bash
# 0. Read telemetry API documentation for schema validation
cat docs/local-telemetry.md | grep -A 50 "TelemetryRun"
# Note required fields: event_id, run_id, agent_name, job_type, start_time

# 1. Create tests directory if not exists
mkdir -p tests

# 2. Check if responses library available for HTTP mocking
pip list | grep responses
# If not: pip install responses

# 3. Read telemetry.py to understand all public methods
grep "def " src/telemetry.py | grep -v "^    def _"

# 4. Create test file structure
cat > tests/test_telemetry.py << 'EOF'
import pytest
import json
import tempfile
import responses
from pathlib import Path
from datetime import datetime, timezone
from src.telemetry import TelemetryClient

# Fixtures
@pytest.fixture
def temp_artifacts_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)

@pytest.fixture
def mock_telemetry_api():
    """Mock HTTP API responses using responses library."""
    with responses.RequestsMock() as rsps:
        # POST /api/v1/runs - success
        rsps.add(responses.POST, 'http://localhost:8765/api/v1/runs',
                 json={'status': 'created', 'event_id': '...'},
                 status=201)
        # PATCH /api/v1/runs/{event_id} - success
        rsps.add(responses.PATCH, re.compile(r'http://localhost:8765/api/v1/runs/.*'),
                 json={'status': 'updated'},
                 status=200)
        yield rsps

# Test classes...
EOF

# 5. Implement test classes and methods
# Follow TDD pattern: write tests for each public method
# Include API schema validation tests

# 6. Implement TestTelemetryAPIIntegration class
# Test API schema compliance:
#   - Verify POST body has all required fields
#   - Verify PATCH body structure correct
#   - Verify event_id is UUID format
#   - Verify timestamps are ISO8601 with timezone

# 7. Run tests with coverage
pytest tests/test_telemetry.py -v --cov=src/telemetry --cov-report=term-missing

# 8. Verify coverage ≥95%
# If coverage low, add more test cases

# 9. Test all context managers
# Each decorator should have success + failure test

# 10. Test API integration with mocked responses
# Use responses library to mock POST /api/v1/runs (201 Created)
# Use responses library to mock PATCH /api/v1/runs/{event_id} (200 OK)
# Use responses library to mock 429 rate limiting
# Use responses library to mock duplicate event_id (200 OK with "duplicate")

# 11. Verify NDJSON files are parseable
# Read back events.ndjson and parse each line as JSON

# 12. Run full test suite
pytest tests/ -v
```

---

## Taskcard TM-04: ~~Extend Metric Support~~ → Verify Telemetry Exports Include All Metrics

✅ **RESCOPED** - Existing metrics are adequate for current needs. This taskcard now focuses on **verifying** that all metrics are exported correctly to the telemetry API and local files.

**Status:** Not Started (Rescoped)

**Gap Linkage:** Fixes TM-GAP-04 (Verify metrics completeness)

**Role:** Senior engineer verifying comprehensive metric export coverage for existing telemetry implementation.

---

### ⚠️ NOTE: Verify Existing Metrics, Don't Extend Yet

**Current metric implementation**:
- TelemetryService tracks metrics via database (src/core/models.py)
- `track_phase_timing()` context manager records phase durations
- Phase metrics stored in telemetry_events table
- Metrics exported to `metrics_json` field in HTTP API

**Work is to ADD**:
1. Verification tests that all pipeline metrics are captured
2. Tests that metrics are exported to API correctly
3. Documentation of which metrics are tracked by each pipeline phase
4. Audit of metric completeness (are we tracking everything we need?)

---

### Scope

**Fix:**
- Verify all pipeline phases record their metrics correctly
- Test that all metrics are exported to HTTP API `metrics_json` field
- Document which metrics are tracked by each phase (discovery, compilation, runtime, etc.)
- Audit metric completeness: identify any missing metrics that should be tracked
- Test metric aggregation for family-level and global-level rollups
- Verify metrics are queryable via telemetry API

**Allowed paths:**
- `tests/test_telemetry_metrics_export.py` - new test file verifying metric exports
- `docs/TELEMETRY_METRICS.md` - new documentation of tracked metrics (if needed)

**Forbidden:** Any other file/path (no changes to production code unless bugs found)

### Acceptance Checks

**CLI:**
- Run `python -m src.cli.main run --family zip` with telemetry enabled
- Verify telemetry database has events for all pipeline phases (discovery, compilation, runtime, finalization)
- Run `pytest tests/test_telemetry_metrics_export.py -v` - all tests pass
- Verify metrics are exported to HTTP API `metrics_json` field when configured

**UI/Web/API:**
- N/A (verification/testing taskcard)

**Tests:**
- `pytest tests/test_telemetry_metrics_export.py -v` passes
- Test all pipeline phases record metrics to database
- Test metrics exported correctly to HTTP API `metrics_json` field
- Test metric aggregation for family-level rollups
- Test metric queryability via telemetry API
- Test completeness: all expected metrics are tracked

**Config respected end-to-end:**
- Metrics tracked when telemetry enabled
- Metrics skipped when telemetry disabled
- HTTP API export optional (works without API)

**No mock data in production paths:**
- Tests use mock HTTP API server
- Tests verify actual database metric storage

### Deliverables

1. **New test file `tests/test_telemetry_metrics_export.py`:**
   - Test class `TestMetricCompleteness`:
     - `test_all_phases_record_metrics`
     - `test_discovery_phase_metrics_tracked`
     - `test_compilation_phase_metrics_tracked`
     - `test_runtime_phase_metrics_tracked`
     - `test_finalization_phase_metrics_tracked`
   - Test class `TestMetricExport`:
     - `test_metrics_exported_to_api_metrics_json_field`
     - `test_metrics_queryable_via_api`
     - `test_family_level_metric_aggregation`
     - `test_global_level_metric_aggregation`
   - Test class `TestMetricAudit`:
     - `test_phase_timing_durations_tracked`
     - `test_example_counts_tracked`
     - `test_failure_counts_tracked`
     - `test_no_missing_critical_metrics`

2. **Optional: Documentation file `docs/TELEMETRY_METRICS.md` (if gaps found):**
   - List all metrics tracked by each pipeline phase
   - Document metric names and their meanings
   - Example:
     ```markdown
     ## Discovery Phase Metrics
     - `discovery_duration_ms`: Time spent in discovery phase
     - `examples_discovered`: Number of code examples found
     - `markdown_files_scanned`: Number of markdown files processed

     ## Compilation Phase Metrics
     - `compilation_duration_ms`: Time spent compiling examples
     - `compilation_attempts`: Number of compilation attempts
     - `compilation_failures`: Number of compilation errors
     ```

3. **Audit report of metric completeness:**
   - Document which metrics are currently tracked
   - Identify any missing metrics that should be added in future
   - Prioritize missing metrics (critical vs nice-to-have)
     ```

4. **New test file `test_telemetry_metrics.py`:**
   - `test_increment_metric_backward_compatible`
   - `test_record_timing_calculates_percentiles`
   - `test_record_histogram_buckets_values`
   - `test_record_gauge_latest_value`
   - `test_save_metrics_json_structure`
   - `test_percentile_calculation_accuracy`
   - `test_histogram_edge_cases` (empty, single value, boundaries)
   - `test_metrics_json_serializable` (NEW - verify all metrics JSON serializable)
   - `test_metrics_sent_to_api` (NEW - verify metrics_json sent in PATCH request)

5. **Forward-compatible migration:**
   - Existing code using `increment_metric()` continues to work unchanged
   - Old metrics.json files with simple structure can be loaded (graceful degradation)

### Hard Rules

- ✅ Keep public signatures: `increment_metric()` unchanged; new methods added
- ✅ No network in offline tests: Metrics are local-only (NDJSON + JSON files)
- ✅ Deterministic runs: Percentile calculations deterministic for same input
- ✅ No new deps: Avoid numpy; implement percentile calculation manually using built-in `sorted()`
- ✅ Keep code/docs/tests in sync: Update docstrings for metric methods; reference telemetry API v2.1.0 metrics_json field

### Review Dimensions (5/5 Criteria)

| Dimension | 5/5 Means |
|-----------|-----------|
| **Correctness** | Percentile calculations accurate; histogram buckets correct; backward compatibility maintained; metrics JSON serializable |
| **Completeness** | All metric types supported; percentiles (p50/90/95/99) calculated; histogram bucketing works; metrics_json sent to API |
| **Robustness** | Handles edge cases (empty data, single value, outliers); doesn't crash on invalid input; JSON serialization always succeeds |
| **Testability** | Tests verify calculations accurate; tests cover all metric types; tests verify API integration |
| **Documentation** | Docstrings explain metric types, aggregations, and usage; references telemetry API v2.1.0 schema |
| **Integration** | Existing code using increment_metric() unaffected; new metric methods integrate seamlessly; API receives metrics_json correctly |

### Now (Runbook)

```bash
# 0. Read telemetry API documentation for metrics_json field
cat docs/local-telemetry.md | grep -B 5 -A 5 "metrics_json"
# Note: metrics_json is a JSON field (dict) in the API schema

# 1. Read current metric implementation
grep -A 30 "def increment_metric" src/telemetry.py
grep -A 30 "def save_metrics" src/telemetry.py

# 2. Design metric storage structure
# Decide on data structures:
#   self._counters = {}  # {name: int}
#   self._timings = {}   # {name: [values]}
#   self._histograms = {} # {name: [values]}
#   self._gauges = {}    # {name: value}

# 3. Implement new metric methods
# Add after increment_metric():
#   def record_timing(self, name: str, duration_ms: int) -> None
#   def record_histogram(self, name: str, value: float) -> None
#   def record_gauge(self, name: str, value: float) -> None

# 4. Update save_metrics() with aggregations
# Calculate percentiles manually (avoid numpy dependency):
#   def _percentile(values, p):
#       sorted_values = sorted(values)
#       index = int(len(values) * p / 100.0)
#       return sorted_values[min(index, len(values) - 1)]
# Aggregate: min, max, avg, p50, p90, p95, p99

# 5. Update finish_run() to send metrics_json to API
# When calling PATCH /api/v1/runs/{event_id}, include:
#   "metrics_json": {
#     "counters": {...},
#     "timings": {...},
#     "histograms": {...},
#     "gauges": {...}
#   }

# 6. Create test_telemetry_metrics.py
# Test each metric type independently
# Test JSON serialization

# 7. Test percentile calculation accuracy
# Use known datasets with expected percentiles

# 8. Run tests
pytest test_telemetry_metrics.py -v

# 9. Integration test with CLI
python src/cli.py validate --family zip --max-snippets 5

# 10. Verify metrics.json structure
cat artifacts/runs/run_*/metrics.json | jq .

# 11. If HTTP API configured, verify metrics_json sent
export TELEMETRY_API_URL=http://localhost:8765
python src/cli.py validate --family zip --max-snippets 1
curl "http://localhost:8765/api/v1/runs?limit=1" | jq '.[0].metrics_json'

# 12. Verify backward compatibility
# Ensure existing increment_metric() calls still work
grep -r "increment_metric" src/
```

---

## Summary

**4 Taskcards Created:**
- **TM-01:** Implement record_timing() method → Fixes runtime crash bug, aligns with API metrics_json schema
- **TM-02:** Add HTTP API configuration → Enables telemetry API v2.1.0 integration (POST /api/v1/runs, PATCH /api/v1/runs/{event_id})
- **TM-03:** Create telemetry validation tests → Achieves 95%+ coverage, validates API schema compliance
- **TM-04:** Extend metric support → Adds timing/histogram/percentile support, integrates with metrics_json field

**Priority Order:**
1. **TM-01** (Critical - blocks production use)
2. **TM-02** (Critical - enables HTTP API integration with documented spec)
3. **TM-03** (High - validates TM-01 and TM-02, ensures API compliance)
4. **TM-04** (Medium - enhances metrics, completes metrics_json support)

**Key Integration Points:**
- All taskcards reference `docs/local-telemetry.md` for API v2.1.0 specification
- TM-02 implements idempotent POST with `event_id` (UUID)
- TM-01 and TM-04 both populate `metrics_json` field for API PATCH requests
- TM-03 validates API schema compliance and all integration points

**API Endpoints Used:**
- `POST /api/v1/runs` - Create run (idempotent by event_id)
- `PATCH /api/v1/runs/{event_id}` - Update run status, metrics_json, error_summary
- Optional: `POST /api/v1/runs/{event_id}/associate-commit` - Link git commits (see AC-03)

**Total Estimated Effort:** 2-3 days for all taskcards (TM-01: 4h, TM-02: 6h, TM-03: 8h, TM-04: 6h)
