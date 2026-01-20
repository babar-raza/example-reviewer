# Changes

Status: In progress.

## Update — 2026-01-12 20:47 PKT

- Extended telemetry metrics with gauges, histograms, and percentiles in `src/telemetry.py`.
- Added structured `metrics_json` while keeping flat timing keys for backward compatibility.
- Added `test_telemetry_metrics.py` with 5 tests for new metric types.
