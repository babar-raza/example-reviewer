# Plan: TM-04 extend metric support

## Assumptions (verify)
- Existing `TelemetryClient` stores counters and timing metrics.
- `metrics.json` is consumed by downstream tooling and should remain backward compatible.
- HTTP API `metrics_json` should carry structured metrics (counters/timings/histograms/gauges).

## Steps
1. Extend metric storage in `src/telemetry.py` (gauges, histograms, percentiles).
2. Keep backward-compatible flat timing keys in `metrics.json` while adding structured `metrics_json`.
3. Add `test_telemetry_metrics.py` for percentiles, histogram buckets, gauges, and API payload.
4. Run tests and capture evidence.

## Rollback Plan
- Revert edits in `src/telemetry.py` and remove `test_telemetry_metrics.py`.

## Tests to Add/Run
- `pytest test_telemetry_metrics.py -v`

## Done Means (Acceptance Checklist)
- [ ] Gauges, histograms, and percentiles supported in telemetry
- [ ] `metrics.json` includes structured `metrics_json` with new metric types
- [ ] HTTP API metrics_json includes all metric types
- [ ] Backward compatibility preserved for flat timing keys
- [ ] Tests pass and evidence captured

## Update — 2026-01-12 20:47 PKT

Status: COMPLETE

Acceptance checklist:
- [x] Gauges, histograms, and percentiles supported in telemetry
- [x] `metrics.json` includes structured `metrics_json` with new metric types
- [x] HTTP API metrics_json includes all metric types
- [x] Backward compatibility preserved for flat timing keys
- [x] Tests pass and evidence captured
