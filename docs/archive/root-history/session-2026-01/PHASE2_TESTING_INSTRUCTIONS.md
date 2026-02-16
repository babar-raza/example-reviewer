# Phase-2 Testing Instructions

**Status**: All core fixes implemented ✅
**Next Step**: Run tests to verify implementation

---

## What Was Fixed

### ✅ Task 1: Compile/Runtime Attempts Persistence
- **CompilationService** now accepts and passes `run_id` parameter
- **RuntimeService** now accepts and passes `run_id` parameter
- **Orchestrator Phase B** records ALL compile attempts (first-try and LLM-retry)
- **Orchestrator Phase C** records ALL runtime attempts (first-try and LLM-retry)
- **Fingerprint counting** already queries DB correctly

### ✅ Task 2: NEEDS_REVIEW Escalation Classifier
- Created `escalation_classifier.py` with controlled vocabulary (11 distinct reasons)
- Integrated into orchestrator to classify examples BEFORE compilation
- Examples with fundamental issues (empty, too incomplete, no Aspose usage, etc.) are escalated immediately

### ✅ Task 3: Snippet Wrapper
- Discovered existing comprehensive implementation in `CompilationService._wrap_code()`
- Handles 4 wrapping strategies automatically
- No additional work needed

### ✅ Task 4: Runtime Fix Loop
- Already exists and working
- Enhanced to persist attempts with `run_id`

---

## Installation Prerequisites

If you encounter "No module named 'pydantic'" errors, install dependencies:

```bash
# From repository root
python -m pip install -r requirements.txt
```

Or install individually:

```bash
python -m pip install pydantic==2.10.3 anthropic==0.40.0 openai==1.58.1
```

---

## Test 1: Verify Attempt Persistence (Stop-the-Line)

Run a single test with limited examples to verify attempts are persisted:

```bash
python tools/run_e2e_zip.py --family zip --seed 12345 --runs 1 \
  --skip-provision --safe-workspace --use-workspace-copy --no-dry-run --verbose
```

**Expected Output Location**: `reports/e2e/run_<timestamp>/run_1/`

**What to Check**:

1. **Fingerprint JSON** (`reports/e2e/run_<timestamp>/run_1/fingerprint.json`):
   ```json
   {
     "compile_attempts_count": 33,  // Must be > 0
     "runtime_attempts_count": 25,  // Must be > 0 (for compiled examples)
     "total_examples": 33,
     "selection_hash": "701126a8f097418e"
   }
   ```

2. **Database Query** (verify attempts are persisted):
   ```bash
   sqlite3 <DB_PATH> "SELECT COUNT(*) FROM compile_attempts WHERE run_id = '<RUN_ID>';"
   sqlite3 <DB_PATH> "SELECT COUNT(*) FROM runtime_attempts WHERE run_id = '<RUN_ID>';"
   ```

**Success Criteria**:
- `compile_attempts_count >= total_examples` (at least one attempt per example)
- `runtime_attempts_count > 0` (for examples that compiled)
- Database queries return same counts as fingerprint

---

## Test 2: Verify Escalation Classifier

Run failure analytics on the test run:

```bash
python tools/report_failure_analytics.py --family zip --run-id <RUN_ID> --format json > reports/phase2_zip/failure_analytics.json
```

**What to Check**:

1. **NEEDS_REVIEW Reasons** should be diverse (not all "unknown"):
   ```json
   {
     "needs_review_stats": {
       "total": 25,
       "by_reason": {
         "snippet_too_incomplete": 8,
         "no_aspose_usage": 5,
         "fragment_without_method": 7,
         "ambiguous_input_file": 3,
         "other": 2
       }
     }
   }
   ```

**Success Criteria**:
- Multiple distinct escalation reasons appear
- "unknown" reason should be 0% or very low
- Each reason should have meaningful counts

---

## Test 3: Determinism Verification (Two-Run Test)

Run two consecutive runs with the same seed to verify deterministic behavior:

```bash
python tools/run_e2e_zip.py --family zip --seed 12345 --runs 2 \
  --skip-provision --safe-workspace --use-workspace-copy --no-dry-run --verbose
```

**What to Check**:

1. **Determinism Comparison** (`reports/e2e/run_<timestamp>/determinism_comparison.json`):
   ```json
   {
     "overall_determinism": "PASS",
     "determinism_checks": {
       "selection_hash": {
         "stable": true,
         "values": ["701126a8f097418e", "701126a8f097418e"]
       },
       "status_counts": {
         "COMPILE_FAILED": {"stable": true, "values": [8, 8]},
         "NEEDS_REVIEW": {"stable": true, "values": [25, 25]}
       }
     }
   }
   ```

**Success Criteria**:
- `overall_determinism` = "PASS"
- `selection_hash` values are identical across runs
- All status counts are stable

---

## Test 4: Drive to ≥90% VERIFIED (Iterative Optimization)

### Step 4.1: Baseline Measurement

Run initial test and collect statistics:

```bash
python tools/run_e2e_zip.py --family zip --seed 12345 --runs 1 \
  --skip-provision --safe-workspace --use-workspace-copy --no-dry-run --verbose
```

Calculate VERIFIED percentage:

```
VERIFIED_PCT = (VERIFIED_count / total_examples) * 100
```

### Step 4.2: Analyze Failures

```bash
python tools/report_failure_analytics.py --family zip --run-id <RUN_ID> --format text
```

Review:
- Top compile error categories
- Top runtime error types
- NEEDS_REVIEW escalation reasons

### Step 4.3: Optimize Based on Findings

Common optimizations:

1. **Missing Test Data**:
   ```bash
   python tools/provision_test_data_zip.py --verbose
   ```

2. **LLM Configuration**:
   - Edit `config/global_config.json`
   - Increase `llm.max_retries` from 2 to 3
   - Ensure API key is set: `ANTHROPIC_API_KEY` environment variable

3. **API Context**:
   - Verify `artifacts/backfill/zip/` exists
   - Check example inventory

4. **Family Configuration**:
   - Review `config/families/zip.json`
   - Verify NuGet packages are correct
   - Check default usings include Aspose namespaces

### Step 4.4: Iterate

Repeat Steps 4.1-4.3 until:

```
VERIFIED_PCT >= 90%
```

**Target Distribution** (for 33 examples):
- VERIFIED: ≥30 (≥90%)
- COMPILE_FAILED: ≤2 (≤6%)
- NEEDS_REVIEW: ≤1 (≤3%)

---

## Test 5: Markdown Update (Only After 90% Threshold)

**WARNING**: Only run this after achieving ≥90% VERIFIED!

```bash
python -m src.cli.main --safe-workspace --deterministic --seed 12345 \
  run --family zip --max-examples 50 --use-workspace-copy --allow-md-write
```

This will:
- Update markdown files in workspace copies (NOT test-data)
- Generate diff manifest showing changes
- Prepare for final review

---

## Troubleshooting

### Issue: "No module named 'pydantic'"

**Solution**: Install dependencies
```bash
python -m pip install -r requirements.txt
```

### Issue: "No .NET SDK found"

**Solution**: Install .NET 8.0 SDK
- Download from: https://dotnet.microsoft.com/download/dotnet/8.0
- Verify: `dotnet --version` should show 8.0.x

### Issue: "Missing test data files"

**Solution**: Provision test data
```bash
python tools/provision_test_data_zip.py
```

### Issue: "compile_attempts_count = 0"

**Cause**: Fix not applied or DB path incorrect

**Solution**:
1. Verify you're running the updated code (check git status)
2. Check DB_PATH in output matches fingerprint's db_path
3. Verify run_id matches between fingerprint and DB query

### Issue: "LLM requests failing"

**Cause**: Missing API key

**Solution**:
```bash
# Set Anthropic API key
export ANTHROPIC_API_KEY=<your-key>

# Or for Windows CMD:
set ANTHROPIC_API_KEY=<your-key>

# Or for Windows PowerShell:
$env:ANTHROPIC_API_KEY="<your-key>"
```

### Issue: "Database locked" errors

**Solution**: Enable safe workspace mode (already done with `--safe-workspace` flag)
- Ensures DB is outside OneDrive/synced folders
- Adds busy timeout for concurrent access

---

## Evidence Collection

After achieving ≥90% VERIFIED, collect evidence:

1. **Create timestamp directory**:
   ```bash
   mkdir -p reports/phase2_zip/$(date +%Y%m%d_%H%M%S)
   cd reports/phase2_zip/<timestamp>
   ```

2. **Copy final run artifacts**:
   ```bash
   cp -r ../../e2e/run_<final>/run_2 ./
   ```

3. **Generate failure analytics**:
   ```bash
   python tools/report_failure_analytics.py --family zip --run-id <RUN_ID> --format json > failure_analytics.json
   ```

4. **Create phase2_e2e_summary.md**:
   - Document run IDs
   - Show VERIFIED percentage
   - Include compile/runtime attempt counts
   - List top failure buckets fixed

5. **Create orchestrator_review.md**:
   - Confirm no test-* writes
   - Confirm no manual .md edits
   - Show pytest results

6. **Create diff_manifest.md**:
   - List workspace markdown files modified
   - Show diff statistics

7. **Create release ZIP**:
   ```bash
   zip -r phase2_release_$(date +%Y%m%d).zip \
     src/ \
     config/ \
     tools/ \
     requirements.txt \
     README.md \
     PHASE2_IMPLEMENTATION_SUMMARY.md
   ```

---

## Quick Reference: File Locations

| Artifact | Path |
|----------|------|
| Implementation summary | `PHASE2_IMPLEMENTATION_SUMMARY.md` |
| Testing instructions | `PHASE2_TESTING_INSTRUCTIONS.md` (this file) |
| Modified services | `src/services/compilation_service.py`, `src/services/runtime_service.py` |
| Modified orchestrator | `src/pipeline/orchestrator.py` |
| New classifier | `src/pipeline/escalation_classifier.py` |
| E2E harness | `tools/run_e2e_zip.py` |
| Analytics tool | `tools/report_failure_analytics.py` |
| Safe workspace DB | `C:\Users\<user>\AppData\Local\ExampleReviewer\workspaces\<timestamp>\` |

---

## Expected Timeline

| Phase | Duration | Description |
|-------|----------|-------------|
| Test 1 (Attempts) | 5-10 min | Verify persistence with 5 examples |
| Test 2 (Classifier) | 1-2 min | Verify escalation reasons |
| Test 3 (Determinism) | 10-15 min | Two-run comparison |
| Test 4 (Optimization) | 2-4 hours | Iterative improvement to 90% |
| Test 5 (MD Update) | 15-30 min | Apply verified changes |
| Evidence Collection | 30 min | Package reports |

**Total Estimated Time**: 3-5 hours for complete Phase-2 validation

---

**Status**: Ready for testing
**Last Updated**: 2026-01-22 17:25 UTC
