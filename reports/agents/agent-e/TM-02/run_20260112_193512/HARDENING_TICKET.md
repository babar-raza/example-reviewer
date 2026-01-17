# HARDENING TICKET: TM-02

## Failing Dimensions
- Coverage, Correctness, Evidence, Test Quality, Maintainability, Safety, Security, Reliability, Observability, Performance, Compatibility, Docs/Specs Fidelity

## Missing Evidence/Tests/Docs
- CLI env var and flag wiring in `src/cli.py`
- Telemetry HTTP API integration in `src/telemetry.py`
- `.env.example` telemetry configuration documentation
- `test_telemetry_config.py` results (env hierarchy, auth, timeout, idempotency, rate limiting)

## Next Actions
1. Implement telemetry HTTP API configuration and idempotent run lifecycle in `src/telemetry.py`.
2. Wire `--telemetry-url` and env var hierarchy in `src/cli.py`.
3. Update `.env.example` with telemetry variables and documentation note.
4. Add `test_telemetry_config.py` covering auth, timeout, idempotency, and 429 handling.
5. Run tests and capture outputs in `evidence.md`.
6. Update `self_review.md` with evidence-backed scores >= 4 and clear Known Gaps.

## Update — 2026-01-12 20:21 PKT

Status: RESOLVED. All next actions completed with passing tests and updated self-review.
