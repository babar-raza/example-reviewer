# Database Migrations

These SQL files are for **upgrading existing databases** only.

Fresh installs auto-create the full schema via `src/core/database.py` - no manual migration needed.

## Active Migrations

| Migration | Purpose |
|-----------|---------|
| 007 | Failure details tracking + analytical views |
| 008 | Run scoping (`example_run_state` table) |
| 009 | Data migration: move run-scoped fields to `example_run_state` |
| 010 | Add `app_context` column |
| 011 | Add `code_block_signature` for safe multi-block targeting |

Migrations are applied automatically by `database.py` on startup.
