# ADR 0003: SQLite as State Machine Backend

## Status
Accepted

## Context
The pipeline processes hundreds of examples per run. Each example transitions
through multiple states (DISCOVERED, COMPILING, COMPILED, RUNNING, VERIFIED,
MD_UPDATED, COMMITTED). We needed persistent state tracking that supports:

1. Resume after interruption
2. Concurrent read access for monitoring
3. Full audit trail of all attempts and transitions
4. Dual-database mode (dev vs production)

## Decision
We use **SQLite with WAL mode** as the state machine backend. The schema
includes 17 tables tracking examples, attempts, edits, runs, telemetry,
reviews, and commits.

Key design choices:
- WAL mode for concurrent read access during long pipeline runs
- Per-run isolation via `run_id` columns
- Dual-database support: development DB for testing, production DB for
  committed results (atomic copy after successful git commit)
- Migration system for schema evolution

Implementation is in `src/core/database.py`.

## Consequences
- **Positive:** Zero external dependencies (SQLite is bundled with Python)
- **Positive:** Full audit trail of every attempt and state transition
- **Positive:** Resume capability after interruption
- **Positive:** Dual-database mode prevents test pollution of production data
- **Negative:** SQLite has limited write concurrency (mitigated by WAL mode)
- **Negative:** Not suitable for distributed deployments (single-file database)
- **Negative:** Risky on network filesystems (OneDrive, DrvFS) — CLI warns
