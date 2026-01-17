# Plan: TM-01 record_timing() implementation

## Assumptions (verify)
- `TelemetryClient` does not yet implement `record_timing()` (confirm in `src/telemetry.py`).
- `src/persistent_fix_service.py` calls `record_timing()` and expects a `duration_ms` signature.
- Current telemetry artifacts include `events.ndjson` and `metrics.json` (confirm file structure in `src/telemetry.py`).

## Steps
1. Read `docs/local-telemetry.md` for `metrics_json` schema and timing expectations.
2. Inspect `src/telemetry.py` for metric storage and `save_metrics()` behavior.
3. Implement `record_timing(metric_name, duration_ms)` with safe input handling.
4. Aggregate min/max/avg/count for each timing metric inside `save_metrics()`.
5. Ensure timing aggregations flow into `metrics_json` for HTTP API PATCH.
6. Verify `src/persistent_fix_service.py` call signature and adjust if needed.
7. Add `test_telemetry_timing.py` coverage for NDJSON, aggregation, HTTP API, failure handling.

## Rollback Plan
- Revert edits in `src/telemetry.py`, `src/persistent_fix_service.py`, and `test_telemetry_timing.py` using git or backup copies.

## Tests to Add/Run
- `pytest test_telemetry_timing.py -v`
- `python src/cli.py validate --family zip --max-snippets 1`

## Done Means (Acceptance Checklist)
- [ ] `record_timing()` implemented with aggregation (min/max/avg/count)
- [ ] Timing event logged to NDJSON (`timing_recorded`)
- [ ] `metrics.json` includes timing aggregations
- [ ] HTTP API `metrics_json` includes timing metrics when configured
- [ ] Tests pass and evidence captured

## Update — 2026-01-12 20:07 PKT

Status: COMPLETE

Acceptance checklist:
- [x] `record_timing()` implemented with aggregation (min/max/avg/count)
- [x] Timing event logged to NDJSON (`timing_recorded`)
- [x] `metrics.json` includes timing aggregations
- [x] HTTP API `metrics_json` includes timing metrics when configured (PATCH mocked)
- [x] Tests pass and evidence captured
