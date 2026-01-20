# Telemetry and Artifacts

Telemetry is recorded in two places:

1. **SQLite Tables**: `telemetry_events`, `run_records`, attempts tables
2. **Optional External Telemetry Sinks**: Via `TelemetryService` (HTTP API)

Additionally, build/runtime logs, diffs, and LLM prompts can be stored as files under an artifact store directory.

## Phase Timing

**Implementation**: `src/core/telemetry.py` -> `track_phase_timing(...)`

The orchestrator wraps each phase with this context manager so duration is recorded even if the phase throws.

## Exporting Run Telemetry

**Implementation**: `src/core/telemetry.py` -> `export_run_telemetry(db, run_id, output_dir)`

Exports several JSON files into `output_dir/<run_id>/`:

- `run_summary.json`
- `phase_events.json`
- `artifact_index.json`
- `errors.json`

## TelemetryService (HTTP API)

**Implementation**: `src/services/telemetry_service.py`

If `telemetry.internal_enabled` and `telemetry.http_api_enabled` are `true`, the orchestrator attempts to:

- Create a run event at the start of `run_full_pipeline`
- Mark it complete at the end, optionally associating a git commit hash

Telemetry failures are treated as non-fatal.

## Artifact References

Tables store string references such as:

- `compiler_log_ref`
- `runtime_log_ref`
- `llm_request_ref`
- `llm_response_ref`
- `diff_ref`

In this archive, these refs are treated as opaque identifiers. Services typically write artifact files under `artifacts/` (or the configured `artifact_store_path`) and store relative paths or IDs in the DB.

## Drift Metrics Helpers

CLI helpers in `src/cli/main.py` call telemetry and DB helpers to:

- Export drift metrics per family (`visualize-drift`)
- Compute drift trends over recent runs (`drift-trends`)