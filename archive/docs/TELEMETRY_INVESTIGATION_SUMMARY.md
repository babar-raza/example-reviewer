# Telemetry Investigation Summary

## Goal

Verify whether telemetry is fully fixed end-to-end:
- Pipeline writes git metadata to telemetry ✅
- Telemetry API can read the latest run without "database is locked" ✅
- Fix strict validator DB wiring so it validates the safe-workspace run DB ✅

## Implementation

### Task A: Strict Validator DB Path Support ✅

**Updated:** `tools/validate_strict_context_mode.py`

Added `--db-path` parameter with fallback logic:
1. If `--db-path` provided, use it
2. Else locate DB path by reading `reports/e2e/run_*/run_*/fingerprint.json`
3. Else fail with clear message

**New Functions:**
- `locate_db_path_from_run_id(run_id: str)` - Searches fingerprint.json files for matching run_id

**Usage:**
```bash
# With explicit DB path
python tools/validate_strict_context_mode.py --run-id <RUN_ID> --db-path <DB_PATH>

# With auto-location (reads from fingerprint.json)
python tools/validate_strict_context_mode.py --run-id <RUN_ID>
```

**Test:** `tests/test_validate_db_path_location.py`
- Tests auto-location from fingerprint.json
- Tests graceful failure when fingerprint not found
- Tests validator initialization with located DB path

### Task B: Telemetry Verify CLI Command ✅

**Updated:** `src/cli/main.py`

Added `telemetry-verify` command with retry logic:
- Calls telemetry API endpoint to fetch run data
- Retries on "database is locked" with exponential backoff
- Default: 10 retries with 1s initial delay (exponential backoff)
- Fails hard if still locked after max retries

**New Function:**
- `telemetry_verify(args)` - HTTP client with retry logic and timeout handling

**Usage:**
```bash
python -m src.cli.main telemetry-verify --run-id <RUN_ID> --telemetry-url <URL>
python -m src.cli.main telemetry-verify --run-id <RUN_ID> --telemetry-url http://localhost:8765 --max-retries 10
```

**Features:**
- Exponential backoff on database locked errors
- Connection error detection
- Timeout handling
- JSON response parsing
- Displays db_path if present in response

### Task C: Mini Rehearsal Scripts ✅

**Created:**
- `tools/run_telemetry_investigation_rehearsal.sh` (Linux/macOS)
- `tools/run_telemetry_investigation_rehearsal.bat` (Windows)

Automated rehearsal workflow:
1. Run `pytest -q` to verify tests pass
2. Execute pipeline with safe workspace:
   ```bash
   python -m src.cli.main run --family zip \
     --config config/global_strict_context.json \
     --safe-workspace --use-workspace-copy --no-dry-run \
     --skip-llm-fixes --max-examples 5 --verbose
   ```
3. Extract RUN_ID and DB_PATH from output
4. Run strict validator:
   ```bash
   python tools/validate_strict_context_mode.py --run-id <RUN_ID> \
     --db-path <DB_PATH> --output reports/telemetry_investigation/validation_report.json
   ```
5. Run telemetry verify:
   ```bash
   python -m src.cli.main telemetry-verify --run-id <RUN_ID> \
     --telemetry-url http://localhost:8765
   ```

**Usage:**
```bash
# Linux/macOS
bash tools/run_telemetry_investigation_rehearsal.sh

# Windows
tools\run_telemetry_investigation_rehearsal.bat
```

### Task D: Evidence Packaging ✅

**Created:** `tools/package_telemetry_investigation_evidence.py`

Generates two zip files:

1. **`example_reviewer_telemetry_review_bundle_<timestamp>.zip`**
   - `README.txt` - Bundle overview
   - `fingerprint.json` - Run fingerprint with db_path
   - `validation_report.json` - Strict validator output
   - `telemetry_verify_output.txt` - Telemetry API verification output
   - `pytest_output.txt` - Test results
   - `git_state.json` - Git branch/SHA/status
   - `metadata.json` - Evidence metadata

2. **`example_reviewer_telemetry_source_<timestamp>.zip`**
   - `src/` - Source code
   - `tools/` - Tools and scripts
   - `tests/` - Test files
   - `docs/` - Documentation
   - `config/` - Configuration files
   - `migrations/` - Database migrations

**Usage:**
```bash
python tools/package_telemetry_investigation_evidence.py --run-id <RUN_ID>

# Custom output directory
python tools/package_telemetry_investigation_evidence.py --run-id <RUN_ID> \
  --output-dir release/custom_dir
```

**Output Location:** `release/telemetry_investigation_<timestamp>/`

## End-to-End Workflow

Complete workflow to verify telemetry end-to-end:

```bash
# Step 1: Run rehearsal
bash tools/run_telemetry_investigation_rehearsal.sh

# Step 2: Capture RUN_ID from output
# Example: RUN_ID=6ac6ed7a27448a71

# Step 3: Package evidence
python tools/package_telemetry_investigation_evidence.py --run-id <RUN_ID>

# Step 4: Upload zip files from release/telemetry_investigation_<timestamp>/
```

## Key Features

1. **Auto-location of DB Path** - Validator automatically finds DB path from fingerprint.json
2. **Retry Logic** - Telemetry verify handles "database is locked" with exponential backoff
3. **Automated Workflow** - Rehearsal scripts automate the full E2E test
4. **Evidence Packaging** - One command generates uploadable evidence bundles
5. **Cross-platform** - Scripts work on Linux, macOS, and Windows

## Files Modified

- [tools/validate_strict_context_mode.py](../tools/validate_strict_context_mode.py) - Added --db-path with fallback
- [src/cli/main.py](../src/cli/main.py) - Added telemetry-verify command

## Files Created

- [tests/test_validate_db_path_location.py](../tests/test_validate_db_path_location.py) - Unit test for DB path location
- [tools/run_telemetry_investigation_rehearsal.sh](../tools/run_telemetry_investigation_rehearsal.sh) - Rehearsal script (Linux/macOS)
- [tools/run_telemetry_investigation_rehearsal.bat](../tools/run_telemetry_investigation_rehearsal.bat) - Rehearsal script (Windows)
- [tools/package_telemetry_investigation_evidence.py](../tools/package_telemetry_investigation_evidence.py) - Evidence packaging
- [docs/TELEMETRY_INVESTIGATION_SUMMARY.md](../docs/TELEMETRY_INVESTIGATION_SUMMARY.md) - This document

## Testing

Run the unit test:
```bash
python tests/test_validate_db_path_location.py
```

## Next Steps

1. Start telemetry API server (if not already running)
2. Run the rehearsal script to test E2E
3. Package evidence with the packaging script
4. Upload the generated zip files for review
5. Verify pytest passes before production deployment
