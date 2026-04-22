# .benchmarks — Baseline Performance Data

This directory stores committed baseline files that ground the accuracy claims
in [README.md Section 9](../README.md#9-supported-families) and
[evals/family_accuracy_report.json](../evals/family_accuracy_report.json).

## Contents

```
.benchmarks/
  README.md                          — this file
  baselines/
    <family>_baseline.json           — one file per configured family
```

## Baseline Schema

Each `<family>_baseline.json` file contains:

| Field | Type | Description |
|-------|------|-------------|
| `schema_version` | string | Schema version (currently "1.0") |
| `family` | string | Family slug (e.g. "zip", "pdf") |
| `generated_at` | ISO-8601 | When this baseline was generated |
| `source` | string | `"production_db"` or `"readme_documented_production_run"` |
| `pipeline_version` | string | Short git SHA of generating commit |
| `totals.discovered` | int | Examples found in Phase A |
| `totals.verified` | int | Examples reaching VERIFIED status |
| `totals.failed` | int | Examples that did not verify |
| `totals.verification_rate_pct` | float | verified / discovered × 100 |
| `run_id` | string or null | Production DB run ID (null for documented-source baselines) |
| `notes` | string | Human notes |

## Updating Baselines

After any pipeline change that could affect accuracy, refresh the affected families:

```bash
# Single family from production DB
python scripts/evals/generate_baseline.py --family zip --db-path data/example_reviewer_prod.db

# All families (uses documented figures when DB unavailable)
python scripts/evals/generate_baseline.py --all
```

Then commit the updated files. CI will warn if baselines are older than 90 days.

## What "source" Means

- `"production_db"` — figures queried directly from the production SQLite database
  (`data/example_reviewer_prod.db`). Highest confidence.
- `"readme_documented_production_run"` — figures sourced from README Section 9,
  which documents actual production run results. These are grounded production data,
  not estimates. Refresh with `--db-path` when the production DB is accessible.

## Methodology

See [evals/methodology.md](../evals/methodology.md) for full definitions of
"discovered", "verified", and the 3-gate verification process.
