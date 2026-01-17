# Plan: TM-03 telemetry validation tests

## Assumptions (verify)
- `src/telemetry.py` exposes public methods for lifecycle, metrics, and context managers.
- Test dependencies include `pytest` and `responses` (confirm in `requirements.txt`).
- Telemetry HTTP API schema is defined in `docs/local-telemetry.md`.

## Steps
1. Read `src/telemetry.py` to catalog public methods and context managers.
2. Inspect `docs/local-telemetry.md` for required API schema fields.
3. Create `tests/test_telemetry.py` with fixtures and test classes per taskcard.
4. Add fixtures in `tests/conftest.py` or `tests/fixtures/telemetry/` if needed.
5. Mock HTTP API calls with `responses` to avoid real network calls.
6. Add coverage checks for 95%+ coverage target.
7. Run tests with coverage and capture output in evidence.

## Rollback Plan
- Remove or revert `tests/test_telemetry.py` and any new fixtures if tests are unstable.

## Tests to Add/Run
- `pytest tests/test_telemetry.py -v --cov=src/telemetry --cov-report=term-missing`

## Done Means (Acceptance Checklist)
- [ ] 95%+ coverage for `src/telemetry.py`
- [ ] Context managers + lifecycle methods tested
- [ ] API schema compliance + idempotency + auth + rate limiting tests included
- [ ] Tests pass and evidence captured

## Dependencies
- TM-01 and TM-02 completion for stable telemetry API behavior

## Update — 2026-01-12 20:28 PKT

Status: COMPLETE

Acceptance checklist:
- [x] 95%+ coverage for `src/telemetry.py` (100%)
- [x] Context managers + lifecycle methods tested
- [x] API schema compliance + idempotency + auth + rate limiting tests included
- [x] Tests pass and evidence captured
