# Plan v2: Production-Ready Example Reviewer System

**Version:** 2.1  
**Date:** 2026-01-20  
**Status:** Draft for Approval

---

## A. Problem Statement: Production-Ready Definition

**Current State:** The Example Reviewer system achieves ~82% compilation success and ~54% runtime success, but exhibits non-deterministic behavior (results vary 82% vs 88% between runs) and lacks production safeguards.

**Production-Ready Requirements:**

1. **Determinism**: Same inputs + same environment fingerprint -> same outputs (reproducible and explainable)
2. **Reliability**: >=90% compilation success, >=80% runtime success, no indefinite hangs
3. **Safety**: No accidental markdown writes, explicit dry-run support, structured failure tracking
4. **Observability**: Every skip/failure/fallback generates telemetry, exportable summaries
5. **Testability**: Unit tests for critical components, smoke E2E test, CI-compatible
6. **Maintainability**: Config fields enforced in code, no silent degradation, clear error routing

**Success Criteria:** System passes 12-dimension self-review with >=4/5 in every dimension:
- Determinism, Reliability, Safety, Observability, Performance
- Security, Testability, Documentation, Maintainability, User Experience
- Error Handling, Configuration Management

---

## B. Determinism Scope and Definition

### Determinism Definition

**Formal Definition:**
Given identical:
- Input markdown files (content snapshot hash)
- Configuration (config snapshot hash)
- Environment fingerprint (runtime versions, model identity, dependency availability)

The system MUST produce:
- Identical example statuses (VERIFIED, COMPILE_FAILED, etc.)
- Identical ordering of examples in reports and exports
- Identical LLM-generated fixes **when deterministic mode is enabled and the provider honors seed**
- Drift scores that are either:
  - identical (preferred), or
  - within an explicit tolerance window (only if embeddings are enabled and known to vary slightly)

### Determinism Boundaries (Important)

Determinism is only guaranteed when the following are also stable:
- Same model identity (provider, model name, and where possible a model digest/hash)
- Same dependency versions (python, dotnet SDK, chromadb, sentence-transformers)
- Same filesystem inputs and the same selected example set

If any boundary changes, the run fingerprint must show it clearly and the determinism gate becomes “reproducibility within the same fingerprint”.

### Run Fingerprint Fields

Every run MUST record a fingerprint with these fields:

```json
{
  "run_id": "uuid",
  "timestamp_utc": "2026-01-20T10:00:00Z",
  "config_hash": "sha256(config/global.json + resolved family config + effective CLI overrides)",
  "llm": {
    "provider": "ollama",
    "base_url": "http://localhost:11434/v1",
    "model": "qwen2.5:14b",
    "model_hash": null,
    "temperature": 0.0,
    "seed": 12345,
    "timeout_seconds": 120,
    "deterministic_mode": true,
    "provider_capabilities": {
      "seed_supported": true,
      "timeout_supported": true
    }
  },
  "final_review": {
    "enabled": true,
    "provider": "anthropic",
    "model": "claude-3-5-sonnet-latest",
    "timeout_seconds": 30
  },
  "vector_db": {
    "enabled": true,
    "provider": "chromadb",
    "embedding_model": "all-MiniLM-L6-v2",
    "embedding_model_version": "2.2.0",
    "device": "cpu",
    "drift_tolerance": 0.02
  },
  "environment": {
    "os": "Windows",
    "os_version": "10.0.19045",
    "python_version": "3.11.5",
    "dotnet_version": "8.0.100",
    "git_commit": "7d11f41"
  },
  "content_snapshot": {
    "family": "zip",
    "total_examples_selected": 66,
    "content_hash": "sha256(all markdown files included in run)",
    "selection_hash": "sha256(sorted(example_keys))"
  }
}
````

Notes:

* `model_hash` is optional because not all providers expose it. If not available, record `ollama_version` and the output of `ollama show <model>` (or equivalent) in the fingerprint as text.
* `selection_hash` is critical. It proves the exact selected set and order.

**Storage:** New table `run_fingerprints` in database, exported to JSON in `runs/{run_id}/fingerprint.json`.

### Sources of Non-Determinism (To Eliminate)

1. **LLM temperature > 0.0** -> Set to 0.0 and add seed parameter
2. **LLM request options not enforced** -> Always pass timeout and seed when configured; detect if ignored
3. **Lazy VectorDB init** -> Make a single startup decision (fail-fast or deterministically disable)
4. **Filesystem ordering** -> Sort all globs and directory scans deterministically (including recursive globs)
5. **Database ordering** -> Order by a stable **example_key** (not timestamps; UUIDs are not stable across fresh ingestions)
6. **Vector search tie-breaking** -> Deterministic sort (score/distance + stable id tie-break)
7. **Embedding jitter** -> CPU embeddings + seeding + tolerance window, or disable drift checks in strict determinism runs
8. **Timeout behavior differences** -> Cross-platform, enforced timeouts for subprocess, async, and blocking functions
9. **Final review configuration drift** -> Enforce provider/model/timeout from config; record actual model used

---

## C. Track 1: Determinism Hardening

### C.1 Configuration Changes (config/global.json)

**Important:** The snippets below are valid JSON (no inline comments). Put explanations in docs, not inside JSON.

**Required Changes (effective config shape):**

```json
{
  "llm": {
    "temperature": 0.0,
    "seed": 12345,
    "timeout_seconds": 120,
    "enforce_timeout": true,
    "deterministic_mode": true
  },
  "vector_db": {
    "enabled": true,
    "require_on_startup": true,
    "deterministic_search": true,
    "embedding_device": "cpu",
    "drift_tolerance": 0.02
  },
  "final_review": {
    "enabled": true,
    "provider": "anthropic",
    "model": "claude-3-5-sonnet-latest",
    "timeout_seconds": 30,
    "enforce_model": true
  },
  "timeouts": {
    "llm_call_seconds": 120,
    "code_execution_seconds": 30,
    "per_example_seconds": 300,
    "per_phase_seconds": 1800,
    "hard_run_timeout_seconds": 2400,
    "allow_timeout_override": false
  }
}
```

**Files:** `config/global.json`

**Validation Rules:**

* Use strict config parsing: unknown keys MUST fail fast (Pydantic `extra="forbid"`).
* CLI overrides must be reflected in the effective config that gets hashed and stored.

Example (pydantic v2 style):

```python
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional

class LLMConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    seed: Optional[int] = Field(default=None)
    timeout_seconds: int = Field(default=120, ge=1)
    enforce_timeout: bool = Field(default=True)
    deterministic_mode: bool = Field(default=False)
```

### C.2 VectorDB and DriftDetector Startup Decision (No Lazy Init)

**Problem:** Lazy initialization creates non-deterministic code paths.

**Fix:** Make a single decision at orchestrator startup:

* If `vector_db.enabled` and `require_on_startup` then VectorDB must be available, else fail fast.
* If enabled but not required, deterministically disable drift and similarity search for the entire run and emit a telemetry event once.

Implementation requirements:

* Never switch drift detector on/off mid-run.
* Record the decision and reason in run fingerprint and telemetry.

### C.3 API Context File Ordering (Recursive)

**Problem:** glob ordering is filesystem-dependent and recursive globs are currently unsorted.

**Fix:** Always sort file paths deterministically, including recursive globs.

Example:

```python
api_files = sorted(cache_path.glob("**/*.md"), key=lambda p: str(p).lower())
```

Also apply sorting to any other content discovery, test-data inventories, and example inventories.

### C.4 Database Query Determinism (Use Stable example_key)

**Problem:**

* `ORDER BY created_at` is not stable.
* `example_id` as UUID is stable within one DB but not stable across fresh ingestion (new UUIDs).

**Fix:**

1. Introduce a deterministic `example_key` computed from:

   * file_path (normalized)
   * code block index / location_block_index
   * language
   * example kind (compile, runtime, snippet, etc. if applicable)

Recommended:

* `example_key = sha256(f"{norm_path}:{block_index}:{lang}:{kind}").hexdigest()[:16]`

2. Add a unique index on `(family, example_key)` so re-ingestion matches prior examples.

3. Order selections and reports by `example_key` (primary) and then by `example_id` (secondary).

Example query rule:

```sql
ORDER BY example_key ASC, example_id ASC
```

### C.5 LLM Timeout and Seed Enforcement (Provider-Aware)

**Problem:** `timeout_seconds` exists but is not enforced. Seed may be ignored by some providers.

**Fix requirements:**

* Always enforce an application-level wall timeout even if the provider ignores a request-level timeout.
* Pass `seed` only when configured and supported.
* Detect support:

  * On startup, issue a tiny probe request (or a dry capability check) and record results.
  * If provider rejects seed, disable seed usage for that run and log a warning + telemetry event.

Implementation guidance:

* If using OpenAI-compatible SDK: set client-level timeout and also wrap calls in `asyncio.wait_for` or `concurrent.futures` timeout.
* Always record the actual request payload fields used (temperature, seed, max_tokens, stop, timeout).

### C.6 Final Review Provider/Model Enforcement

**Problem:** `final_review.model` exists but code always uses the primary model.

**Fix:**

* `final_review` must support an independent provider and model.
* If `final_review.enabled=false`, no final review calls.
* If `enforce_model=true`, log and fail if the provider returns a different model than requested (where detectable).

### C.7 Vector Search Deterministic Ordering

**Problem:** Vector DB can return same-score results in non-deterministic order, especially when distances tie.

**Fix:**

* Sort results deterministically after retrieval:

  * sort by `distance` (rounded to N decimals) then `example_key` (or stable id)
* If `example_key` missing, fall back to stable `(file_path, block_index)` metadata.

### C.8 Run Fingerprint Capture (and selection_hash)

**New Feature:** Capture and store run fingerprint plus selected example set hash.

Add:

* `selection_hash = sha256("\\n".join(sorted(example_keys))).hexdigest()`

Store both:

* In DB table `run_fingerprints`
* In `runs/{run_id}/fingerprint.json`

---

## D. Track 2: Reliability + Success-Rate Improvements

### D.1 Progressive Retry Enrichment

**Problem:** Retries repeat identical context.

**Rule:** Each retry attempt must change something deterministically.

Recommended tiers:

* Attempt 1: minimal error + targeted API snippet for missing symbols
* Attempt 2: add top-K similar examples (deterministic ordering, stable K)
* Attempt 3: expand API context + add explicit strategy hint based on error category
* Attempt 4+: include full compiler output and a strict response format contract

Also:

* Detect “no change” retries: if the LLM returns identical code twice, escalate faster (do not waste all retries).

### D.2 Multi-Level Timeouts (Cross-Platform)

**Problem:** Examples can hang for a long time, especially during runtime execution and external tool calls.

**Fix:** Enforce timeouts at 4 levels:

* LLM call timeout
* Code execution timeout (subprocess timeout)
* Per-example wall timeout
* Per-phase wall timeout
* Optional hard run timeout (entire pipeline process)

**Cross-platform requirement (Windows included):**

* Do not rely on `signal.SIGALRM` for correctness.
* Use one of these based on operation type:

  1. `subprocess.run(..., timeout=seconds)` for external tools
  2. `asyncio.wait_for(coro, timeout=seconds)` for async steps
  3. `concurrent.futures.ThreadPoolExecutor` with `future.result(timeout=seconds)` for blocking Python functions

Minimal reference implementation:

```python
import asyncio
import subprocess
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout

class TimeoutManager:
    def __init__(self):
        self._pool = ThreadPoolExecutor(max_workers=8)

    async def run_async(self, coro, seconds: int, label: str):
        return await asyncio.wait_for(coro, timeout=seconds)

    def run_blocking(self, fn, seconds: int, label: str):
        fut = self._pool.submit(fn)
        try:
            return fut.result(timeout=seconds)
        except FutureTimeout:
            raise TimeoutError(f"Timeout after {seconds}s: {label}")

    def run_subprocess(self, args, seconds: int, label: str, **kwargs):
        try:
            return subprocess.run(args, timeout=seconds, **kwargs)
        except subprocess.TimeoutExpired:
            raise TimeoutError(f"Timeout after {seconds}s: {label}")
```

Telemetry requirements:

* Every timeout MUST emit:

  * `event_type = "timeout_exceeded"`
  * phase, example_key, timeout value, operation label
* Every timeout MUST also insert a `failure_details` row.

### D.3 Smarter Response Validation by Error Category (No Silent Rejection)

**Problem:** Minimal valid fixes get rejected silently.

**Fix:**

* Validation returns `(is_valid, rejection_reason)`
* Rejections must be logged to telemetry and inserted into failure_details
* Response formats should be strict and parseable:

  * Require code fences for code output
  * Require “NO CHANGE” explicit token if no change is needed
  * Reject partial diffs unless explicitly supported

### D.4 Explicit NEEDS_REVIEW Path for High-Risk Categories

**Problem:** Some errors are not safe to auto-fix.

**Fix:**

* Add risk-based routing:

  * LOW: auto-fix, limited retries
  * MEDIUM: auto-fix with drift + validation gates
  * HIGH: one attempt then NEEDS_REVIEW
  * CRITICAL: immediate NEEDS_REVIEW

Rule:

* Any case where the system cannot confirm correctness should go to NEEDS_REVIEW, not “fail silently”.

### D.5 Structured Failure Tracking (Queryable)

**Fix:**

* Create `failure_details` table as specified, plus indexes on:

  * (run_id, phase)
  * (failure_category)
  * (error_category)
  * (resolution)

Also:

* Ensure each example has a terminal state and a failure reason if not verified.

---

## E. Track 3: Production Readiness Polish

### E.1 Safety Rails: Markdown Write Protection (Three Locks)

Safety must require three independent conditions:

1. Config: `markdown_write.allow_markdown_write=true`
2. CLI flag: `--allow-md-write`
3. Not dry-run: `--dry-run` must override and block all writes

Implementation requirements:

* Before any write, validate all three.
* Always create backups.
* Writes must be atomic:

  * write to temp file, then `os.replace(temp, target)` (atomic on Windows and POSIX)

Optional (recommended):

* Add file locking via a cross-platform library (example: `portalocker`).

### E.2 Observability: Structured Telemetry (No Free Text)

Requirement:

* Every decision point must generate structured telemetry:

  * routing decision
  * drift checks and thresholds used
  * LLM requests (metadata only, not secrets)
  * LLM response validation result
  * timeouts
  * escalations
  * skips and fallbacks

Standardize event types:

* `phase_skipped`
* `example_skipped`
* `compilation_failed`
* `runtime_failed`
* `final_review_failed`
* `timeout_exceeded`
* `vector_db_unavailable`
* `api_context_missing`
* `llm_response_rejected`
* `drift_exceeded`
* `escalated_to_review`
* `error_routing_decision`

Also export:

* `runs/{run_id}/telemetry_summary.json`
* `runs/{run_id}/results_summary.json` (used by determinism gate)

### E.3 Testing: Determinism-Critical Tests (Mock External Services)

Key change: unit tests must not rely on a live LLM or live chromadb unless explicitly marked as integration tests.

Test categories:

1. Unit tests (default)

   * config parsing (extra keys forbidden)
   * deterministic sorting utilities
   * example_key generation stability
   * vector search tie-break sorting logic (mocked)
   * timeout wrappers (blocking and subprocess)
2. Integration tests (optional, gated by env var)

   * LLM determinism probe (temp 0 + seed) only when provider configured
   * chromadb persistence smoke

### E.4 CLI UX: Deterministic Mode

CLI must support:

* `--deterministic` sets:

  * temperature=0.0
  * seed default (if not provided)
  * drift enabled but with CPU embeddings or drift disabled (configurable)
* `--seed` overrides default seed
* `--dry-run` and `--allow-md-write`
* `--phases` and `--max-examples`
* timeout overrides only if `allow_timeout_override=true`

---

## F. Acceptance Gates

### Gate 1: Determinism

**Requirement:** Reproducible summaries across 3 identical runs.

**What is compared:**

* `runs/{run_id}/results_summary.json` (preferred), not raw logs

Comparison rules:

* Ignore `run_id` and timestamps
* Status counts and per-example terminal statuses must match for the same `selection_hash`
* Drift scores:

  * must match exactly when drift is disabled or when embedding determinism is guaranteed
  * may be within `drift_tolerance` when drift is enabled and device/library are known to vary

**Test Protocol (cross-platform):**

1. Run 3 times with identical command
2. Compare summaries with `tools/verify_determinism.py`

Example:

```bash
python -m src.cli.main run --family zip --deterministic --seed 12345 --max-examples 20 --dry-run
python -m src.cli.main run --family zip --deterministic --seed 12345 --max-examples 20 --dry-run
python -m src.cli.main run --family zip --deterministic --seed 12345 --max-examples 20 --dry-run

python tools/verify_determinism.py runs/<run1>/results_summary.json runs/<run2>/results_summary.json runs/<run3>/results_summary.json
```

Exit criteria:

* Same `selection_hash`
* Same per-example statuses
* Drift comparisons meet policy (exact or within tolerance)

### Gate 2: Timeout (No Hangs)

**Requirement:** No indefinite hangs. Entire run bounded by hard timeout.

**Test Protocol (cross-platform):**

* Use a Python wrapper that enforces a hard process timeout using `subprocess.run(..., timeout=...)`.

Example:

```bash
python tools/run_with_hard_timeout.py --seconds 1200 -- \
  python -m src.cli.main run --family zip --dry-run
```

Exit criteria:

* Pipeline completes within hard limit or exits with a clear timeout error
* All timeout events are recorded in telemetry
* No examples left in non-terminal status

### Gate 3: Config Enforcement

This gate has two parts.

**Gate 3A: Schema enforcement (must)**

* Parsing `config/global.json` must fail if unknown keys exist.
* Effective config used at runtime must be stored and hashed.

Test:

```python
def test_config_schema_forbids_unknown_keys():
    ConfigurationManager().load_global_config()  # should raise on unknown keys
```

**Gate 3B: Runtime enforcement (should)**

* Record which config fields were actually consulted at runtime (config access tracker) and export `runs/{run_id}/config_access.json`.
* Each top-level section (llm, vector_db, final_review, timeouts, markdown_write, drift, validation) must have at least one recorded access in a full run.

Exit criteria:

* No unknown keys
* Effective config hash recorded in fingerprint
* Config access export present for full runs

### Gate 4: Safety (No Writes Without Explicit Enablement)

**Requirement:** Markdown writes are impossible unless explicitly allowed and not dry-run.

**Cross-platform verification:**

* Provide a Python check `tools/verify_no_md_changes.py` which runs `git status --porcelain` and fails if any `.md` changed.

Protocol:

1. Default run: no writes allowed -> must produce zero md changes
2. Allow + dry-run: still no writes
3. Allow without dry-run: may write and must create backups and use atomic write

### Gate 5: Tests

**Requirement:** All tests pass.

Protocol:

```bash
pip install -r requirements-dev.txt
pytest -q
```

Exit criteria:

* Unit tests pass reliably (run them 3 times)
* Integration tests are optional but must pass when enabled

---

## G. Rollout Plan

### Phase A: Determinism Foundation (Week 1)

Goal: eliminate non-determinism sources and produce deterministic summaries.

Tasks:

1. Config schema strictness + effective config hashing
2. Deterministic file ordering everywhere (recursive globs)
3. Replace lazy drift detector init with startup decision
4. Introduce example_key and stable ordering
5. Run fingerprint + selection_hash + results_summary export
6. LLM seed/timeout enforcement and capability detection

Evidence:

* Gate 1 passes on at least 20 examples for ZIP family
* Fingerprints and results_summary exported

### Phase B: Reliability Improvements (Weeks 2-3)

Goal: eliminate hangs and improve success rates.

Tasks:

1. Progressive retry enrichment with “no change” detection
2. Multi-level timeouts (cross-platform)
3. Smarter response validation (no silent rejection)
4. Risk routing and NEEDS_REVIEW workflow
5. failure_details table populated consistently

Evidence:

* Gate 2 passes
* > =90% compilation, >=80% runtime (ZIP pilot)
* Telemetry shows structured failure reasons for all non-verified examples

### Phase C: Production Polish (Week 4)

Goal: safety rails, observability, test suite and operator UX.

Tasks:

1. Three-lock markdown write protection and atomic writes
2. Telemetry standardization and exports
3. Unit tests + smoke E2E test
4. CLI flags and help output hardened
5. Runbook doc (how to run deterministically, how to handle review queue)

Evidence:

* All gates pass
* 12-dimension self-review >=4/5 across the board

---

## H. Risks and Mitigations

### Risk 1: Embedding Jitter

Cause: embeddings may vary slightly across devices/versions.

Mitigation:

* Use CPU embeddings for determinism-critical runs
* Seed torch/numpy
* Allow `drift_tolerance` only when drift is enabled and documented

Acceptance:

* Drift comparisons within tolerance; otherwise disable drift in strict determinism mode

### Risk 2: LLM Seed Support Variability

Cause: not all providers honor seed.

Mitigation:

* Probe seed support at startup and record in fingerprint
* If unsupported, determinism gate is limited to statuses and summaries (LLM output may differ)

Acceptance:

* Gate 1 still must pass on statuses and summaries; “identical code fixes” is required only when seed is supported and deterministic mode is enabled

### Risk 3: Filesystem Race Conditions and Cross-Platform Atomicity

Mitigation:

* Atomic writes via temp + `os.replace`
* Optional file locking via cross-platform library (example: portalocker)
* Phase D remains sequential in v2.1

### Risk 4: SQLite Concurrency Limits

Mitigation:

* Keep writes sequential
* Add SQLITE_BUSY retry with backoff
* Use WAL mode if appropriate, but still treat DB as single-writer

### Risk 5: Config Migration

Mitigation:

* Optional fields default to safe values
* Provide migration script and warnings, not hard breaks

---

## I. Implementation Taskcards

### Taskcard 1: Strict Config Schema + Effective Config Hashing

Files:

* `config/global.json`
* `src/core/config.py`

Changes:

1. Add new fields (`seed`, `deterministic_mode`, `embedding_device`, `drift_tolerance`, `hard_run_timeout_seconds`, `final_review.provider`)
2. Make pydantic models strict (`extra="forbid"`)
3. Implement “effective config” generation: config + family config + CLI overrides
4. Hash and store effective config, not just raw global.json

Verification:

* Loading config with an unknown key must fail immediately

### Taskcard 2: VectorDB Startup Decision (No Lazy Drift Detector)

Files:

* `src/pipeline/orchestrator.py`
* `src/services/vector_db_service.py`
* `src/services/drift_detector.py`

Changes:

* Startup decision once per run
* Telemetry event emitted once (`vector_db_unavailable` or `drift_disabled`)
* Record in fingerprint

### Taskcard 3: Deterministic File Ordering Everywhere

Files:

* `src/pipeline/orchestrator.py` (API context loaders, content discovery)
* Any inventory builders under `src/`

Changes:

* Sort recursive glob results deterministically using normalized path sort

### Taskcard 4: Introduce example_key and Stable Ordering

Files:

* `src/core/database.py`
* `src/core/models.py` (if needed)
* ingestion code path that creates ExampleRecord

Changes:

* Add `example_key` column + unique index `(family, example_key)`
* Order selections by `example_key`
* Update vector metadata to include `example_key`

### Taskcard 5: LLM Timeout + Seed Enforcement and Capability Detection

Files:

* `src/services/llm_service.py`

Changes:

* Apply client timeout + application-level wall timeout
* Pass seed only if supported and configured
* Record capability results in fingerprint and telemetry

### Taskcard 6: Final Review Provider/Model Fix

Files:

* `src/services/llm_service.py`
* `src/pipeline/orchestrator.py`

Changes:

* Use `final_review.provider` and `final_review.model`
* Enforce timeout and record model used

### Taskcard 7: Run Fingerprint + results_summary Exports

Files:

* `src/core/database.py`
* `src/core/fingerprint.py` (new)
* `src/core/results_summary.py` (new)
* `src/pipeline/orchestrator.py`

Changes:

* Store fingerprint in DB and JSON
* Export `results_summary.json` for determinism gate comparisons

### Taskcard 8: Progressive Retry Enrichment

Files:

* `src/pipeline/orchestrator.py`

Changes:

* Deterministic tiered context
* Early stop on “no change” loops
* Telemetry for each retry tier used

### Taskcard 9: Cross-Platform Timeout Manager

Files:

* `src/core/timeouts.py` (new)
* `src/pipeline/orchestrator.py`

Changes:

* ThreadPool + asyncio + subprocess timeout support
* Enforced per-example and per-phase wall timers
* Telemetry + failure_details insertions on timeout

### Taskcard 10: Response Validation (No Silent Rejection)

Files:

* `src/services/llm_service.py`

Changes:

* Return rejection reasons
* Emit telemetry + failure_details
* Enforce strict output format

### Taskcard 11: Error Routing + NEEDS_REVIEW Workflow

Files:

* `src/core/config.py`
* `src/core/models.py`
* `src/pipeline/orchestrator.py`
* `src/cli/review_queue.py` (new)

Changes:

* Risk mapping and routing
* Review queue CLI and data model

### Taskcard 12: failure_details Table + Analytics Queries

Files:

* `src/core/database.py`

Changes:

* Add table and indexes
* Insert on every terminal failure or escalation

### Taskcard 13: Safety Rails + Atomic Writes

Files:

* `src/pipeline/orchestrator.py`
* `src/cli/main.py`
* `src/core/file_io.py` (new)

Changes:

* Three-lock gating
* Atomic writes + backups

### Taskcard 14: Telemetry Standardization + Exports

Files:

* `src/core/telemetry.py`
* `src/pipeline/orchestrator.py`

Changes:

* Standard event types
* Export telemetry_summary.json and config_access.json

### Taskcard 15: Tests (Unit + Smoke, Integration Optional)

Files:

* `tests/` (new)

Changes:

* Unit tests for determinism-critical utilities
* Smoke E2E test (max 5 examples, dry-run)
* Integration tests behind env var

### Taskcard 16: CLI UX

Files:

* `src/cli/main.py`

Changes:

* Deterministic flags, seed flags
* Phase selection
* Safe defaults

### Taskcard 17: Gate Scripts (Cross-Platform)

Files:

* `tools/run_with_hard_timeout.py` (new)
* `tools/verify_determinism.py` (new)
* `tools/verify_no_md_changes.py` (new)
* `tools/run_all_gates.py` (new)

Changes:

* Single Python entrypoint to run all gates on Windows and Linux

---

## J. Summary of Top 10 Plan Changes vs Old Plan

| #  | Change                    | v1/v2 draft behavior          | v2.1 behavior                            | Impact                         |
| -- | ------------------------- | ----------------------------- | ---------------------------------------- | ------------------------------ |
| 1  | JSON validity             | Config snippets used comments | All config snippets valid JSON           | Prevents config parse failures |
| 2  | example_id vs example_key | Ordered by created_at or UUID | Deterministic example_key + ordering     | Stable across re-ingestion     |
| 3  | Timeout strategy          | SIGALRM approach (Unix only)  | Cross-platform timeouts                  | Works on Windows               |
| 4  | Determinism comparisons   | Parsed logs                   | Compare results_summary.json             | Less brittle                   |
| 5  | Config enforcement        | Naive string search           | Strict schema + optional access tracking | Fewer false positives          |
| 6  | Final review              | Model fixed or ignored        | Provider+model configurable and enforced | Predictable review             |
| 7  | Drift determinism         | Assumed exact                 | Adds tolerance or strict disable option  | Realistic determinism          |
| 8  | Safety verification       | bash/grep                     | Python tools cross-platform              | Works on Windows               |
| 9  | Tests                     | Live LLM in unit tests        | Mock by default, integration optional    | CI stable                      |
| 10 | Fingerprint completeness  | Missing selection hash        | Adds selection_hash and capability flags | Better reproducibility         |

---

**End of Plan v2.1**

