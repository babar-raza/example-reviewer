# Evidence

Status: Pending. No commands run yet.

Planned commands:
- `pytest tests/test_telemetry.py -v --cov=src/telemetry --cov-report=term-missing`

## Update — 2026-01-12 20:28 PKT

Commands executed (initial coverage run with incorrect module name):
```
pytest tests/test_telemetry.py -v --cov=src/telemetry --cov-report=term-missing
```

Output:
```
============================= test session starts =============================
platform win32 -- Python 3.12.7, pytest-9.0.2, pluggy-1.6.0 -- C:\Users\prora\anaconda3\python.exe
cachedir: .pytest_cache
rootdir: C:\Users\prora\OneDrive\Documents\GitHub\example-reviewer
configfile: pytest.ini
plugins: anyio-3.7.1, langsmith-0.3.43, asyncio-1.3.0, cov-7.0.0, mock-3.14.0
asyncio: mode=Mode.STRICT, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 16 items

tests/test_telemetry.py::test_start_run_creates_artifacts_and_metadata PASSED [  6%]
tests/test_telemetry.py::test_start_run_posts_to_api_with_schema PASSED  [ 12%]
tests/test_telemetry.py::test_log_event_writes_ndjson PASSED             [ 18%]
tests/test_telemetry.py::test_log_event_http_failure_graceful PASSED     [ 25%]
tests/test_telemetry.py::test_track_page_success_updates_metrics PASSED  [ 31%]
tests/test_telemetry.py::test_track_page_failure_updates_errors PASSED   [ 37%]
tests/test_telemetry.py::test_track_snippet_success PASSED               [ 43%]
tests/test_telemetry.py::test_track_validation_success PASSED            [ 50%]
tests/test_telemetry.py::test_track_fix_success_and_failure PASSED       [ 56%]
tests/test_telemetry.py::test_track_patch_success PASSED                 [ 62%]
tests/test_telemetry.py::test_track_compilation_logs_events PASSED       [ 68%]
tests/test_telemetry.py::test_record_timing_and_save_metrics PASSED      [ 75%]
tests/test_telemetry.py::test_save_metrics_patches_http_when_configured PASSED [ 81%]
tests/test_telemetry.py::test_finish_run_patches_status_and_metrics PASSED [ 87%]
tests/test_telemetry.py::test_finish_run_without_start_does_not_raise PASSED [ 93%]
tests/test_telemetry.py::test_build_headers_with_auth PASSED             [100%]
CoverageWarning: Module src/telemetry was never imported.
CoverageWarning: No data was collected.
WARNING: Failed to generate report: No data to report.

============================= 16 passed in 1.19s ==============================
```

Commands executed (corrected coverage run):
```
pytest tests/test_telemetry.py -v --cov=telemetry --cov-report=term-missing
```

Output:
```
============================= test session starts =============================
platform win32 -- Python 3.12.7, pytest-9.0.2, pluggy-1.6.0 -- C:\Users\prora\anaconda3\python.exe
cachedir: .pytest_cache
rootdir: C:\Users\prora\OneDrive\Documents\GitHub\example-reviewer
configfile: pytest.ini
plugins: anyio-3.7.1, langsmith-0.3.43, asyncio-1.3.0, cov-7.0.0, mock-3.14.0
asyncio: mode=Mode.STRICT, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 31 items

tests/test_telemetry.py::test_start_run_creates_artifacts_and_metadata PASSED [  3%]
tests/test_telemetry.py::test_start_run_posts_to_api_with_schema PASSED  [  6%]
tests/test_telemetry.py::test_log_event_writes_ndjson PASSED             [  9%]
tests/test_telemetry.py::test_log_event_http_failure_graceful PASSED     [ 12%]
tests/test_telemetry.py::test_log_event_ndjson_write_failure_is_caught PASSED [ 16%]
tests/test_telemetry.py::test_track_page_success_updates_metrics PASSED  [ 19%]
tests/test_telemetry.py::test_track_page_failure_updates_errors PASSED   [ 22%]
tests/test_telemetry.py::test_track_snippet_success PASSED               [ 25%]
tests/test_telemetry.py::test_track_snippet_failure_updates_errors PASSED [ 29%]
tests/test_telemetry.py::test_track_validation_success PASSED            [ 32%]
tests/test_telemetry.py::test_track_validation_failure_updates_errors PASSED [ 35%]
tests/test_telemetry.py::test_track_fix_success_and_failure PASSED       [ 38%]
tests/test_telemetry.py::test_track_patch_success PASSED                 [ 41%]
tests/test_telemetry.py::test_track_patch_failure_updates_errors PASSED  [ 45%]
tests/test_telemetry.py::test_track_compilation_logs_events PASSED       [ 48%]
tests/test_telemetry.py::test_track_compilation_failure_logs_event PASSED [ 51%]
tests/test_telemetry.py::test_record_timing_and_save_metrics PASSED      [ 54%]
tests/test_telemetry.py::test_record_timing_invalid_inputs PASSED        [ 58%]
tests/test_telemetry.py::test_save_metrics_patches_http_when_configured PASSED [ 61%]
tests/test_telemetry.py::test_increment_metric_new_key PASSED            [ 64%]
tests/test_telemetry.py::test_finish_run_patches_status_and_metrics PASSED [ 67%]
tests/test_telemetry.py::test_finish_run_without_start_does_not_raise PASSED [ 70%]
tests/test_telemetry.py::test_finish_run_records_error_in_metadata PASSED [ 74%]
tests/test_telemetry.py::test_post_run_start_skips_when_missing_config PASSED [ 77%]
tests/test_telemetry.py::test_post_run_start_rate_limited PASSED         [ 80%]
tests/test_telemetry.py::test_post_run_start_non_200 PASSED              [ 83%]
tests/test_telemetry.py::test_patch_run_update_handles_errors PASSED     [ 87%]
tests/test_telemetry.py::test_patch_run_update_skips_without_config PASSED [ 90%]
tests/test_telemetry.py::test_send_metrics_update_skips_without_config PASSED [ 93%]
tests/test_telemetry.py::test_aggregate_timing_metrics_skips_empty_values PASSED [ 96%]
tests/test_telemetry.py::test_build_headers_with_auth PASSED             [100%]

=============================== tests coverage ================================
_______________ coverage: platform win32, python 3.12.7-final-0 _______________

Name               Stmts   Miss  Cover   Missing
------------------------------------------------
src\\telemetry.py     266      0   100%
------------------------------------------------
TOTAL                266      0   100%
============================= 31 passed in 2.55s ==============================
```
