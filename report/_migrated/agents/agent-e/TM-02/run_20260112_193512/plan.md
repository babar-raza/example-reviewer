# Plan: TM-02 HTTP API configuration

## Assumptions (verify)
- Telemetry HTTP API env vars are not yet wired in `src/cli.py`.
- `src/telemetry.py` does not yet support `telemetry_url`, auth, timeout, or idempotent `event_id`.
- `docs/local-telemetry.md` defines the POST/PATCH schema for v2.1.0.

## Steps
1. Read `docs/local-telemetry.md` for required fields and endpoints.
2. Inspect `src/cli.py` to add `--telemetry-url` and env var parsing.
3. Update `TelemetryClient.__init__` to accept URL, timeout, auth, and `event_id`.
4. Implement `start_run()` POST `/api/v1/runs` per schema (idempotent by `event_id`).
5. Implement `finish_run()` PATCH `/api/v1/runs/{event_id}` with metrics_json.
6. Add 429 handling and graceful failures without crashing.
7. Add `test_telemetry_config.py` for env hierarchy, timeout, auth headers, idempotency, rate limiting.
8. Update `.env.example` with telemetry variables and docs reference.

## Rollback Plan
- Revert changes in `src/cli.py`, `src/telemetry.py`, `.env.example`, and `test_telemetry_config.py` using git or backups.

## Tests to Add/Run
- `pytest test_telemetry_config.py -v`

## Done Means (Acceptance Checklist)
- [ ] Env vars + `--telemetry-url` supported with override behavior
- [ ] POST/PATCH schema matches `docs/local-telemetry.md`
- [ ] Auth headers and timeout respected
- [ ] 429 and duplicate event_id handled gracefully
- [ ] Tests pass and evidence captured

## Dependencies
- TM-01 completion to avoid conflicting `src/telemetry.py` changes

## Update — 2026-01-12 20:21 PKT

Status: COMPLETE

Acceptance checklist:
- [x] Env vars + `--telemetry-url` supported with override behavior
- [x] POST/PATCH schema matches `docs/local-telemetry.md` required fields
- [x] Auth headers and timeout respected
- [x] 429 and duplicate event_id handled gracefully
- [x] Tests pass and evidence captured
