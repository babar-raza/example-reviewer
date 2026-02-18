# scripts/ops/ - Pipeline Operations

Day-to-day scripts for running the pipeline and analyzing results.

## Scripts

| Script | Purpose |
|--------|---------|
| `run_all_gates.py` | Execute all verification gates (compile, runtime, determinism) |
| `run_e2e_zip.py` | End-to-end ZIP family pipeline run |
| `run_with_hard_timeout.py` | Run pipeline with hard process timeout |
| `batch_preflight.py` | Pre-flight checks before a batch run |
| `dump_failures.py` | Dump failure details from database |
| `export_run_failures.py` | Export failures to CSV/JSON |
| `export_verified_examples.py` | Export verified examples for review |
| `check_db_schema.py` | Verify database schema integrity |
| `check_example_statuses.py` | Show example status distribution |
| `report_failure_analytics.py` | Generate failure analytics report |
| `monitor_llm_telemetry.py` | Monitor LLM usage, costs, and latency |
| `build_test_data_inventory.py` | Inventory test data files across families |
| `md_update_verified_v2.py` | Update markdown files with verified code |
