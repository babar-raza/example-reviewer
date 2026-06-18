# src/core/ - Core Infrastructure

Shared infrastructure used by all pipeline components.

## Files

| File | Purpose |
|------|---------|
| `config.py` | Configuration management (global + per-family JSON loading) |
| `config_utils.py` | Configuration helper utilities |
| `database.py` | SQLite database (WAL mode, schema auto-creation, dual-DB support) |
| `models.py` | Data models and enums (ExampleRecord, RunState, etc.) |
| `telemetry.py` | Local telemetry recording (events, runs, LLM calls) |
| `path_guard.py` | Write protection for read-only test directories |
| `provenance_guard.py` | Code provenance tracking (original vs modified) |
| `fingerprint.py` | Run fingerprinting for deduplication |
| `results_summary.py` | Pipeline run summary generation |
| `app_context.py` | Application context detection (console, library, ASP.NET) |
| `failure_tracking.py` | Failure reason categorization |
| `timeout_manager.py` | Process timeout management |
