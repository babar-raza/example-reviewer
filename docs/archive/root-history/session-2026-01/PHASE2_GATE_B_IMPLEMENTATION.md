# Phase-2 Gate B Remediation Implementation

**Date**: 2026-01-23
**Status**: Implementation Complete - Ready for Testing

## Overview

This document describes the implementation of Phase-2 Gate B remediation tasks to improve the `eligible_verified_rate` from 52.17% to ≥90% (target 21/23 verified).

## Implemented Changes

### Task 1: INFRA Breakdown Correctness ✅

**Issue**: `infra_blocked_count=4` but `infra_breakdown` all zeros

**Solution**:
- The existing tracking functions (`track_infra_blocked_rar`, `track_infra_blocked_7z`, `track_infra_missing_test_data`) already record failure_details with proper categories
- These are called in all INFRA_BLOCKED paths in the orchestrator
- The database query in `database.py` lines 2340-2438 correctly aggregates by `failure_category`
- **Action**: Verified that all INFRA_BLOCKED code paths call the appropriate tracking functions with breakdown-compatible categories:
  - `INFRA_BLOCKED_RAR_FIXTURE`
  - `INFRA_BLOCKED_7Z_FIXTURE`
  - `INFRA_BLOCKED_PASSWORD`
  - `INFRA_MISSING_TEST_DATA`

### Task 2: Quick Wins as Deterministic Transforms ✅

**Implementation**: Created `apply_quick_fixes()` function in `src/services/example_substitution_service.py`

**Fixes Applied**:

1. **DirectoryNotFoundException Fix** (example `1a78833310063754`):
   - Detects `DirectoryNotFoundException` in compilation errors
   - Identifies directory paths in code using regex patterns
   - Injects `Directory.CreateDirectory()` calls at the beginning of `Main()` method
   - Deterministic - no LLM involved

2. **Missing using Aspose.Zip.Saving** (example `5707970e00a9f0e2`):
   - Detects errors mentioning `CompressionSettings`, `DeflateCompressionSettings`, etc.
   - Automatically adds `using Aspose.Zip.Saving;` after existing usings
   - Deterministic - pattern-based

3. **Missing using Aspose.Zip.SevenZip** (example `603983d0dadbfec6`):
   - Detects errors mentioning `SevenZipArchive`, `SevenZipArchiveEntry`
   - Automatically adds `using Aspose.Zip.SevenZip;` after existing usings
   - Deterministic - pattern-based

**Integration**: Quick fixes are applied in the compilation phase (lines 899-934 in `orchestrator.py`) BEFORE attempting substitution or LLM fixes.

### Task 3: Example-Repo Substitution ✅

**Implementation**: Created `ExampleSubstitutionService` class in `src/services/example_substitution_service.py`

**Substitution Triggers** (6 patterns):

| Pattern | Reason | Target Examples |
|---------|--------|----------------|
| `ZipArchiveMode does not exist` | wrong_system_io_compression | Use MemoryStream-based Aspose.Zip examples |
| `Microsoft.AspNetCore` missing | wrong_aspnetcore_dependency | Replace with MemoryStream examples |
| `CompressionLevel could not be found` | wrong_compression_namespace | Use DeflateCompressionSettings examples |
| `RarArchiveLoadOptions` missing | missing_rar_loadoptions | Use RarArchive with password examples |
| `SevenZipArchiveSaveOptions` missing | missing_7z_saveoptions | Use SevenZipArchive examples |
| `ArchiveSaveOptions ... CompressionSettings` | missing_compression_settings | Use Archive with compression settings |

**Matching Strategy**:
1. Filter by keywords (tags, class name, path)
2. Avoid examples using problematic classes (e.g., `ZipArchiveMode`, `IFormFile`)
3. Prefer examples with target class if specified
4. Select smallest matching example (simpler is better)

**Integration**: Substitution is attempted in the compilation phase (lines 936-1004 in `orchestrator.py`) AFTER quick fixes fail but BEFORE LLM retry loop.

**Data Source**: Uses `artifacts/backfill/zip/examples-index.json` and corresponding example files in `artifacts/backfill/zip/examples/`

### Task 4: Runtime-to-Compile Reclassification ✅

**Issue**: 2 "runtime_failed" cases are actually compile errors that slipped through

**Solution**: Added guard in runtime phase (lines 1564-1659 in `orchestrator.py`)

**Detection Logic**:
```python
# Check for C# compiler error codes (CSxxxx) in runtime output
compile_error_pattern = r'\bCS\d{4}\b'
has_compile_errors = re.search(compile_error_pattern, runtime_output)
```

**Reclassification Flow**:
1. Detect CSxxxx errors in runtime stderr/stdout
2. Extract compile errors
3. Try substitution first (using same triggers as Task 3)
4. If substitution works and runtime passes → mark VERIFIED
5. If substitution fails → reclassify as COMPILE_FAILED
6. Track as `runtime_reclassified` in stats

### Task 5: RAR Missing Fixture Stays INFRA_BLOCKED ✅

**Status**: Already correctly implemented

Examples like `extract-rar-online` are deterministically marked as INFRA_BLOCKED when RAR fixtures are missing. This is tracked via `track_infra_blocked_rar()` which records:
- `failure_category`: `INFRA_BLOCKED_RAR_FIXTURE`
- `escalation_reason`: `missing_rar_fixture`

## Modified Files

1. **src/services/example_substitution_service.py** (NEW)
   - `ExampleSubstitutionService` class
   - `apply_quick_fixes()` function
   - Substitution trigger patterns and matching logic

2. **src/pipeline/orchestrator.py** (MODIFIED)
   - Added imports for substitution service and tracking
   - Added `substitution_service` property
   - Integrated quick fixes in compilation phase (lines 894-934)
   - Integrated substitution in compilation phase (lines 936-1004)
   - Added runtime-to-compile reclassification (lines 1564-1659)

## Statistics Tracking

New metrics added to pipeline stats:

- `quick_fixes_applied`: Count of quick fix successes
- `substitutions_applied`: Count of substitution successes
- `runtime_reclassified`: Count of runtime failures reclassified as compile failures

## Testing Instructions

### Step 1: Run Single Measurement

```bash
# Activate virtual environment
source .venv/Scripts/activate  # or: source venv/Scripts/activate

# Run single measurement to verify fixes
python tools/run_e2e_zip.py \
  --family zip \
  --seed 12345 \
  --runs 1 \
  --skip-provision \
  --safe-workspace \
  --use-workspace-copy \
  --no-dry-run \
  --verbose
```

**Expected Output**:
- Quick fixes should apply to examples with missing usings and DirectoryNotFoundException
- Substitution should trigger on wrong API usage (System.IO.Compression, AspNetCore, etc.)
- Runtime CSxxxx errors should be reclassified
- `infra_breakdown` should sum to `infra_blocked_count`

### Step 2: Run Gate B Measurement (2 runs, deterministic)

```bash
python tools/run_e2e_zip.py \
  --family zip \
  --seed 12345 \
  --runs 2 \
  --skip-provision \
  --safe-workspace \
  --use-workspace-copy \
  --no-dry-run \
  --verbose
```

**Gate B Pass Criteria**:
- `eligible_verified_rate >= 90.0%` (target 21/23 verified)
- Determinism: PASS
- `infra_breakdown` sums correctly to `infra_blocked_count`

### Step 3: Run md-update (only after Gate B PASS)

```bash
python -m src.cli.main \
  --safe-workspace \
  --deterministic \
  --seed 12345 \
  run \
  --family zip \
  --use-workspace-copy \
  --allow-md-write \
  --max-examples 50
```

## Verification Checklist

- [ ] Quick fixes apply automatically (check logs for "Applied quick fixes")
- [ ] Substitution triggers on error patterns (check logs for "Substitution triggered")
- [ ] Runtime CSxxxx errors are reclassified (check logs for "Reclassifying ... as COMPILE_FAILED")
- [ ] `infra_breakdown` in e2e_summary.json sums to `infra_blocked_count`
- [ ] `eligible_verified_rate >= 90.0%` in Gate B metrics
- [ ] Determinism passes (2 runs produce identical results)

## Expected Improvements

Based on remediation plan analysis:

| Category | Before | Expected After |
|----------|--------|----------------|
| VERIFIED | 12 | 21+ |
| COMPILE_FAILED | 7 | ~2 |
| RUNTIME_FAILED | 4 | 0 |
| INFRA_BLOCKED | 4 | 4 (unchanged) |
| **eligible_verified_rate** | **52.17%** | **≥90%** |

## Troubleshooting

### Issue: Substitution not finding examples

**Check**:
```bash
ls -la artifacts/backfill/zip/
# Should see: examples/, examples-index.json, test-data/

cat artifacts/backfill/zip/examples-index.json | jq '.total_examples'
# Should show 123 examples
```

**Solution**: Run backfill provisioning if missing:
```bash
python tools/provision_test_data_zip.py --family zip
```

### Issue: Quick fixes not applying

**Check logs for**:
- "Applied quick fixes for {example_id}: directory_create_injection"
- "Applied quick fixes for {example_id}: using_aspose_zip_saving"
- "Applied quick fixes for {example_id}: using_aspose_zip_sevenzip"

**Debug**:
```python
# Enable debug logging
import logging
logging.getLogger('example_substitution_service').setLevel(logging.DEBUG)
```

### Issue: Runtime reclassification not working

**Check logs for**:
- "Runtime failure for {example_id} contains compile errors (CSxxxx)"
- "Reclassifying {example_id} as COMPILE_FAILED"

**Verify**: Runtime output contains CSxxxx error codes

## Next Steps

1. Run single measurement to verify implementation
2. Run Gate B measurement (2 runs)
3. Verify Gate B passes (eligible_verified_rate >= 90%)
4. Run md-update
5. Generate evidence reports
6. Create release package

## Evidence Required

After successful Gate B run, collect:

1. `reports/e2e/run_<timestamp>/e2e_summary.json`
2. `reports/e2e/run_<timestamp>/run_1/fingerprint.json`
3. `reports/e2e/run_<timestamp>/run_2/fingerprint.json`
4. Exported failures JSON
5. Updated `reports/phase2_closed/summary.md`
6. Updated `reports/phase2_closed/failure_analytics.json`

## Author

Implementation by Claude Sonnet 4.5 (2026-01-23)
Phase-2 Gate B Remediation - Automate Quick Wins + Substitution
