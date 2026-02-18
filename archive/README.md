# archive/ - Historical Files

Files preserved for git history but no longer actively used.

## Contents

| Directory | What's archived |
|-----------|----------------|
| `docs/` | Superseded documentation (quickstart, hardening notes, implementation plans) |
| `specs/` | Outdated specification files (v1 architecture, database schema, API reference) |
| `tools/` | One-time migration scripts, packaging tools, diagnostic utilities |
| `scripts/` | Deprecated script subdirs (packaging, maintenance, debug) |
| `tests/` | Legacy integration test stubs and demos |
| `migrations/` | Legacy database migrations (004-006) |
| `src_legacy/` | Compatibility wrappers for refactored modules |

These files are not loaded by any active code. They exist only for reference.

## Recovery

All files were moved using `git mv` to preserve history. To view a file's history:

```bash
git log --follow archive/<path>/<filename>
```
