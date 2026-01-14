# Telemetry System Healing Plan

## Context
Local telemetry implementation is 80% complete but has 4 critical blockers preventing production readiness:
- Missing `record_timing()` method causing runtime crashes
- Non-functional HTTP API secondary write path (API is documented at `docs/local-telemetry.md`)
- Zero test coverage for telemetry module
- Limited metric support (integer counters only)

**Reference:** See [docs/local-telemetry.md](../docs/local-telemetry.md) for complete HTTP API specification (v2.1.0)

## Gap → Taskcard Mapping

| Gap/Blocker ID | Description | Taskcard ID(s) |
|----------------|-------------|----------------|
| TM-GAP-01 | Missing `record_timing()` method - `AttributeError` at runtime | TM-01 |
| TM-GAP-02 | No HTTP API configuration - secondary write path non-functional | TM-02 |
| TM-GAP-03 | No telemetry validation tests - zero coverage | TM-03 |
| TM-GAP-04 | Incomplete metric support - integer counters only | TM-04 |

---

## Taskcard TM-01: Implement record_timing() Method

**Status:** Not Started

**Gap Linkage:** Fixes TM-GAP-01 (Missing `record_timing()` method)

**Role:** Senior engineer delivering drop-in, production-ready timing metric support aligned with telemetry API schema.

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

## Taskcard TM-02: Add HTTP API Configuration

**Status:** Not Started

**Gap Linkage:** Fixes TM-GAP-02 (No HTTP API configuration - secondary write path non-functional)

**Role:** Senior engineer delivering production-ready HTTP telemetry configuration for local-telemetry-api v2.1.0.

### Scope

**Fix:**
- Add environment variable support for `TELEMETRY_API_URL` (per `docs/local-telemetry.md` spec, default: `http://localhost:8765`)
- Add support for `TELEMETRY_API_AUTH_ENABLED` and `TELEMETRY_API_AUTH_TOKEN` (optional auth)
- Add timeout configuration via `TELEMETRY_API_TIMEOUT_MS` (default: 2000ms)
- Update CLI initialization to read environment variables
- Add optional CLI flag `--telemetry-url` to override environment variable
- Implement proper telemetry API integration using POST `/api/v1/runs`, PATCH `/api/v1/runs/{event_id}` endpoints
- Use `event_id` (UUID) for idempotency per API spec
- Document configuration in `.env.example` with reference to `docs/local-telemetry.md`

**Allowed paths:**
- `src/cli.py` - read environment variables, add CLI flag
- `src/telemetry.py` - accept timeout and auth parameters, implement API integration
- `.env.example` - document telemetry env vars
- `test_telemetry_config.py` - new test file

**Forbidden:** Any other file/path

### Acceptance Checks

**CLI:**
- Run `export TELEMETRY_API_URL=http://localhost:8765 && python src/cli.py discover --family zip`
- Verify HTTP POST requests sent to `localhost:8765/api/v1/runs` with proper schema (event_id, run_id, agent_name, job_type, start_time)
- Run `python src/cli.py discover --family zip --telemetry-url http://localhost:9999`
- Verify CLI flag overrides environment variable
- Run with `TELEMETRY_API_TIMEOUT_MS=5000` to verify configurable timeout
- Run with `TELEMETRY_API_AUTH_ENABLED=true TELEMETRY_API_AUTH_TOKEN=test123` to verify auth headers

**UI/Web/API:**
- N/A (CLI-only feature)

**Tests:**
- `pytest test_telemetry_config.py` passes
- Test verifies TELEMETRY_API_URL environment variable used
- Test verifies CLI flag overrides environment variable
- Test verifies TELEMETRY_API_TIMEOUT_MS configurable
- Test verifies auth headers sent when enabled
- Test verifies default values when not configured
- Test verifies idempotent POST behavior (same event_id returns 200 OK with "duplicate" status)

**Config respected end-to-end:**
- HTTP API disabled when TELEMETRY_API_URL not set (NDJSON-only mode)
- HTTP API enabled when TELEMETRY_API_URL set
- Timeout respected in HTTP requests
- Auth headers included when TELEMETRY_API_AUTH_ENABLED=true

**No mock data in production paths:**
- Real HTTP requests sent in production
- Mock HTTP server used only in tests

### Deliverables

1. **Updated `src/cli.py`:**
   - Read `TELEMETRY_API_URL`, `TELEMETRY_API_TIMEOUT_MS`, `TELEMETRY_API_AUTH_ENABLED`, `TELEMETRY_API_AUTH_TOKEN` environment variables
   - Add `--telemetry-url` CLI flag to `discover`, `validate`, `patch` commands
   - Pass telemetry_url, timeout, and auth config to `TelemetryClient.__init__()`

2. **Updated `src/telemetry.py`:**
   - Accept `telemetry_url: Optional[str] = None`, `timeout_ms: int = 2000`, `auth_enabled: bool = False`, `auth_token: Optional[str] = None` in `__init__()`
   - Generate `event_id` as UUID at run start (per API spec for idempotency)
   - Implement `start_run()` to POST to `/api/v1/runs` with schema:
     ```python
     {
       "event_id": "<uuid>",
       "run_id": "<timestamp>-<run_type>-<unique_id>",
       "agent_name": "example-reviewer",
       "job_type": "<run_type>",  # discovery, validation, patching
       "status": "running",
       "start_time": "<iso8601_with_tz>",
       "git_repo": "<from_git>",
       "git_branch": "<from_git>"
     }
     ```
   - Implement `finish_run()` to PATCH `/api/v1/runs/{event_id}` with:
     ```python
     {
       "status": "success|failure",
       "end_time": "<iso8601_with_tz>",
       "duration_ms": <int>,
       "error_summary": "<if_failed>",
       "metrics_json": {"pages_scanned": 10, ...}
     }
     ```
   - Include `Authorization: Bearer <token>` header when auth_enabled=True
   - Use timeout in HTTP requests: `requests.post(..., timeout=timeout_ms/1000.0)`
   - Handle idempotent responses (200 OK with "duplicate" status)
   - Handle 429 rate limiting gracefully (log warning, don't crash)

3. **Updated `.env.example`:**
   ```
   # Optional: Local Telemetry API endpoint (see docs/local-telemetry.md)
   # Default: http://localhost:8765 (local-telemetry-api v2.1.0)
   TELEMETRY_API_URL=http://localhost:8765

   # Optional: HTTP request timeout in milliseconds (default: 2000)
   TELEMETRY_API_TIMEOUT_MS=5000

   # Optional: Enable API authentication (default: false)
   TELEMETRY_API_AUTH_ENABLED=false
   TELEMETRY_API_AUTH_TOKEN=your-secret-token-here

   # See full API documentation: docs/local-telemetry.md
   ```

4. **New test file `test_telemetry_config.py`:**
   - Test environment variable TELEMETRY_API_URL used
   - Test CLI flag --telemetry-url overrides environment
   - Test TELEMETRY_API_TIMEOUT_MS configurable
   - Test auth headers sent when enabled
   - Test default behavior (no HTTP API) when not configured
   - Test HTTP requests respect timeout
   - Test idempotent POST behavior (duplicate event_id)
   - Test 429 rate limiting handling

5. **Forward-compatible migration:**
   - Existing code without environment variables continues to work (NDJSON-only mode)
   - CLI runs without --telemetry-url flag use environment variable

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

## Taskcard TM-03: Create Telemetry Validation Tests

**Status:** Not Started

**Gap Linkage:** Fixes TM-GAP-03 (No telemetry validation tests - zero coverage)

**Role:** Senior engineer delivering comprehensive test coverage for telemetry module with API v2.1.0 compliance validation.

### Scope

**Fix:**
- Create comprehensive test suite for `src/telemetry.py` (target: 95%+ coverage)
- Test all 6 context manager decorators (`track_page`, `track_snippet`, `track_validation`, `track_compilation`, `track_fix`, `track_patch`)
- Test run lifecycle (start_run, finish_run) with HTTP API integration
- Test event logging (NDJSON + HTTP API)
- Test metric management (increment, get, save)
- Test error handling and failure modes
- Test artifacts directory creation and file writing
- **NEW:** Test telemetry API v2.1.0 schema compliance (POST /api/v1/runs, PATCH /api/v1/runs/{event_id})
- **NEW:** Test idempotency (duplicate event_id), auth headers, rate limiting (429), error responses

**Allowed paths:**
- `tests/test_telemetry.py` - new comprehensive test file
- `tests/fixtures/` - test fixtures if needed
- `tests/conftest.py` - pytest fixtures if needed

**Forbidden:** Any other file/path (no changes to src/telemetry.py itself)

### Acceptance Checks

**CLI:**
- Run `pytest tests/test_telemetry.py -v --cov=src/telemetry --cov-report=term-missing`
- Coverage ≥ 95% for `src/telemetry.py`
- All tests pass

**UI/Web/API:**
- N/A (test-only taskcard)

**Tests:**
- Test happy path: run lifecycle creates artifacts directory and files
- Test happy path: event logging writes to NDJSON
- Test happy path: HTTP API POST /api/v1/runs receives correct schema
- Test happy path: HTTP API PATCH /api/v1/runs/{event_id} updates run
- Test failure path: HTTP API timeout doesn't crash event logging
- Test failure path: invalid artifact directory doesn't crash initialization
- Test edge case: multiple metrics with same name accumulate correctly
- Test edge case: finish_run without start_run raises error
- Test all 6 context manager decorators
- Test NDJSON parsing: verify events can be read back
- Test metrics.json: verify JSON structure matches schema
- **NEW:** Test API schema compliance: verify all required fields present (event_id, run_id, agent_name, job_type, start_time)
- **NEW:** Test idempotency: duplicate event_id POST returns 200 OK with "duplicate" status
- **NEW:** Test auth: verify Authorization header sent when auth_enabled=True
- **NEW:** Test rate limiting: verify 429 response handled gracefully
- **NEW:** Test timestamps: verify ISO8601 with timezone format

**Config respected end-to-end:**
- Tests verify NDJSON works without HTTP API configured
- Tests verify HTTP API optional and failures graceful

**No mock data in production paths:**
- Tests use temporary directories for artifacts (no pollution)
- Tests use mock HTTP server (no real network calls)

### Deliverables

1. **New test file `tests/test_telemetry.py` (600+ lines):**
   - Pytest fixtures for TelemetryClient with temp directories
   - Test class `TestTelemetryRunLifecycle`:
     - `test_start_run_creates_directories`
     - `test_start_run_writes_metadata`
     - `test_start_run_posts_to_api` (NEW - validates API schema)
     - `test_finish_run_saves_metrics`
     - `test_finish_run_patches_api` (NEW - validates PATCH schema)
     - `test_finish_run_without_start_raises_error`
   - Test class `TestTelemetryEventLogging`:
     - `test_log_event_writes_ndjson`
     - `test_log_event_sends_http_api` (mocked)
     - `test_log_event_http_failure_graceful`
     - `test_log_event_ndjson_parseable`
   - Test class `TestTelemetryContextManagers`:
     - `test_track_page_success`
     - `test_track_page_failure`
     - `test_track_snippet_success`
     - `test_track_validation_success`
     - `test_track_compilation_success`
     - `test_track_fix_success`
     - `test_track_patch_success`
   - Test class `TestTelemetryMetrics`:
     - `test_increment_metric`
     - `test_get_metrics`
     - `test_save_metrics_json_structure`
     - `test_metrics_accumulate_correctly`
     - `test_metrics_json_sent_to_api` (NEW)
   - Test class `TestTelemetryArtifacts`:
     - `test_artifacts_directory_created`
     - `test_ndjson_file_appends`
     - `test_metadata_json_structure`
   - **NEW Test class `TestTelemetryAPIIntegration`:**
     - `test_api_schema_compliance_post_runs`
     - `test_api_schema_compliance_patch_runs`
     - `test_idempotent_post_duplicate_event_id`
     - `test_auth_headers_sent_when_enabled`
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

## Taskcard TM-04: Extend Metric Support

**Status:** Not Started

**Gap Linkage:** Fixes TM-GAP-04 (Incomplete metric support - integer counters only)

**Role:** Senior engineer delivering production-ready metric system with timing, histograms, and percentiles, aligned with telemetry API v2.1.0 `metrics_json` field.

### Scope

**Fix:**
- Extend `TelemetryClient` to support metric types: Counter, Gauge, Timing, Histogram
- Implement histogram bucketing for distribution metrics (e.g., compilation times)
- Calculate percentiles (p50, p90, p95, p99) for timing metrics
- Maintain backward compatibility with existing `increment_metric()` calls (counters)
- Update `save_metrics()` to serialize all metric types
- Add `record_gauge(name, value)` for point-in-time measurements
- Add `record_histogram(name, value)` for distribution tracking
- **NEW:** Ensure all metrics serializable to `metrics_json` field for telemetry API compatibility (JSON serializable dict)

**Allowed paths:**
- `src/telemetry.py` - extend metric support
- `test_telemetry_metrics.py` - new test file for advanced metrics

**Forbidden:** Any other file/path (no changes to call sites yet)

### Acceptance Checks

**CLI:**
- Run `python src/cli.py validate --family zip`
- Verify `metrics.json` includes histogram buckets and percentiles
- Example structure:
  ```json
  {
    "counters": {"pages_scanned": 10, "snippets_found": 25},
    "timings": {
      "compilation_duration": {
        "count": 25,
        "sum": 45000,
        "min": 500,
        "max": 5000,
        "avg": 1800,
        "p50": 1500,
        "p90": 3000,
        "p95": 4000,
        "p99": 4800
      }
    },
    "histograms": {
      "snippet_length": {
        "buckets": {"10": 5, "50": 15, "100": 3, "500": 2},
        "count": 25,
        "sum": 1250
      }
    },
    "gauges": {
      "memory_usage_mb": 256
    }
  }
  ```
- If HTTP API configured, verify `metrics_json` field sent to PATCH `/api/v1/runs/{event_id}` contains all metric types

**UI/Web/API:**
- N/A (internal metric system)

**Tests:**
- `pytest test_telemetry_metrics.py -v` passes
- Test counter: increment multiple times, verify sum
- Test timing: record multiple values, verify min/max/avg/percentiles
- Test histogram: record values, verify bucket distribution
- Test gauge: record value, verify latest value stored
- Test backward compatibility: existing increment_metric() calls still work
- Test metrics_json serialization: all metric types JSON serializable

**Config respected end-to-end:**
- Histogram bucket boundaries configurable (optional, default buckets fine)
- Percentiles always calculated for timing metrics

**No mock data in production paths:**
- Real metric values used in production
- Mock values only in tests

### Deliverables

1. **Updated `src/telemetry.py`:**
   - Add metric type enum or constants: COUNTER, TIMING, HISTOGRAM, GAUGE
   - Separate storage dicts: `_counters`, `_timings`, `_histograms`, `_gauges`
   - Keep `increment_metric()` unchanged (backward compatible, uses `_counters`)
   - Add `record_timing(name, duration_ms)` - stores in `_timings[name] = []`
   - Add `record_histogram(name, value, buckets=None)` - stores in `_histograms[name]`
   - Add `record_gauge(name, value)` - stores in `_gauges[name] = value`
   - Update `save_metrics()` to serialize all metric types with aggregations
   - Calculate percentiles using manual implementation (avoid numpy dependency):
     ```python
     def _percentile(values, p):
         sorted_values = sorted(values)
         index = int(len(values) * p / 100.0)
         return sorted_values[min(index, len(values) - 1)]
     ```
   - Ensure metrics JSON serializable for telemetry API `metrics_json` field

2. **Updated `save_metrics()` method:**
   - Aggregate counters: sum
   - Aggregate timings: count, sum, min, max, avg, p50, p90, p95, p99
   - Aggregate histograms: bucket counts, total count, sum
   - Aggregate gauges: latest value
   - Write structured JSON with sections: counters, timings, histograms, gauges
   - Format compatible with telemetry API `metrics_json` field (flat dict or nested dict, must be JSON serializable)

3. **Updated HTTP API integration in `finish_run()`:**
   - Include all aggregated metrics in `metrics_json` field when calling PATCH `/api/v1/runs/{event_id}`
   - Example:
     ```python
     {
       "status": "success",
       "end_time": "...",
       "duration_ms": 5000,
       "metrics_json": {
         "counters": {"pages_scanned": 10},
         "timings": {"compilation_duration_avg": 1800},
         "histograms": {"snippet_length_count": 25},
         "gauges": {"memory_usage_mb": 256}
       }
     }
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
