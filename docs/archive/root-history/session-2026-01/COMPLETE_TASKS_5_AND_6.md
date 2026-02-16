# Instructions to Complete Tasks 5 & 6

## Current Status

✅ **Tasks 1-4: COMPLETE**
- Recursive test-data lookup implemented
- INFRA_BLOCKED classification tightened
- Determinism drift fixed (no DISCOVERED leftovers)
- Failure analytics enhanced with status breakdown

⏳ **Task 5: IN PROGRESS**
- 2-run validation is currently running in background

⏳ **Task 6: READY**
- Packaging script created and ready to use

---

## Task 5: Complete 2-Run Validation

### Step 1: Wait for validation to complete

The validation was started with:
```bash
python tools/run_e2e_zip.py --family zip --seed 12345 --runs 2 \
  --skip-provision --safe-workspace --use-workspace-copy --no-dry-run --verbose
```

**How to monitor progress:**
```bash
# Check if process is still running
ps aux | grep run_e2e_zip

# View live output (last 50 lines)
tail -f <output_file_from_task>

# Or check reports directory
ls -ltr reports/e2e/
```

### Step 2: Identify the run ID

Once complete, find the run ID from the output:
```bash
# List recent runs
ls -lt reports/e2e/ | head -10

# Example output:
# run_abc123def456/
```

The run ID will be something like `abc123def456`.

### Step 3: Generate failure analytics

```bash
# Replace <RUN_ID> with actual run ID from Step 2
python tools/report_failure_analytics.py \
  --family zip \
  --run-id <RUN_ID> \
  --format json \
  > reports/phase2_gateb_fix/failure_analytics_run2.json
```

### Step 4: Verify determinism PASS

```bash
# Check determinism comparison
cat reports/e2e/run_<RUN_ID>/determinism_comparison.json | grep status

# Should show: "status": "PASS"
```

### Step 5: Verify RAR false positives resolved

```bash
# Check failure analytics for missing_rar_fixture
cat reports/phase2_gateb_fix/failure_analytics_run2.json | grep missing_rar_fixture

# Should show 0 or very few instances (only truly missing files)
```

---

## Task 6: Create Upload-Ready Packages

Once Task 5 is verified complete, run the packaging script:

```bash
# Replace <RUN_ID> with actual run ID from Task 5 Step 2
python tools/create_phase2_gateb_fix_packages.py --run-id <RUN_ID>
```

### Expected Output

The script will create `release/phase2_gateb_fix_<timestamp>/` with 4 ZIP files:

1. **phase2_gateb_fix_review_bundle.zip** (Core Evidence)
   - Fingerprints from both runs
   - Determinism comparison
   - E2E summary
   - Failure analytics
   - Test data tree (shows where plrabn12.rar lives)

2. **phase2_gateb_fix_reports.zip** (Full Reports)
   - Complete reports/phase2_gateb_fix/ directory
   - Complete reports/e2e/run_<ID>/ directory

3. **phase2_gateb_fix_source.zip** (Source Code)
   - All source: src/, tools/, tests/, docs/, config/, migrations/
   - Requirements files
   - README and summary

4. **phase2_gateb_fix_failure_artifacts.zip** (Failure Details)
   - failures_run2.json (all non-VERIFIED examples)
   - Failure artifacts for up to 20 failing examples
   - Compile/runtime logs where available

### Verify Packages

```bash
cd release/phase2_gateb_fix_<timestamp>/

# Check all 4 ZIPs exist
ls -lh *.zip

# Inspect review bundle
unzip -l phase2_gateb_fix_review_bundle.zip

# Should include:
#   - run_1_fingerprint.json
#   - run_2_fingerprint.json
#   - determinism_comparison.json
#   - e2e_summary.json
#   - failure_analytics_run2.json
#   - test_data_tree.txt
```

---

## Final Checklist

Before marking as complete, verify:

- [ ] 2-run validation completed successfully
- [ ] Determinism comparison shows "PASS"
- [ ] RAR false positives are resolved (check failure_analytics_run2.json)
- [ ] pytest -q still passes (85 tests green)
- [ ] All 4 ZIP packages created successfully
- [ ] Review bundle contains all required files
- [ ] test_data_tree.txt shows recursive structure (plrabn12.rar location visible)

---

## Expected Results

### Determinism

**Before fixes:**
```json
{
  "status": "FAIL",
  "status_counts_match": false,
  "differences": {
    "DISCOVERED": {"run_1": 1, "run_2": 0}
  }
}
```

**After fixes:**
```json
{
  "status": "PASS",
  "status_counts_match": true,
  "fingerprint_identical": true
}
```

### RAR Classification

**Before fixes:**
```
INFRA_BLOCKED: missing_rar_fixture: 3 examples
(even though plrabn12.rar exists in test-data/rar/)
```

**After fixes:**
```
INFRA_BLOCKED: missing_rar_fixture: 0 examples
(or only truly missing files)

RUNTIME_FAILED or NEEDS_REVIEW: file_not_copied: X examples
(if fixture exists but copy failed - system bug, not infra)
```

### Failure Analytics

**Before fixes:**
- Only INFRA-focused analytics
- Missing COMPILE_FAILED, RUNTIME_FAILED breakdowns

**After fixes:**
```json
{
  "status_breakdown": [
    {"status": "VERIFIED", "count": 45, "percentage": 45.0},
    {"status": "COMPILABLE", "count": 25, "percentage": 25.0},
    {"status": "COMPILE_FAILED", "count": 15, "percentage": 15.0},
    {"status": "RUNTIME_FAILED", "count": 10, "percentage": 10.0},
    {"status": "NEEDS_REVIEW", "count": 5, "percentage": 5.0}
  ]
}
```

---

## Troubleshooting

### Validation takes too long

If validation is taking more than 30 minutes:
```bash
# Check progress
tail -f <output_file>

# If stuck, you can:
# 1. Let it continue (might just be slow)
# 2. Ctrl+C and reduce --max-examples for testing
```

### Packaging script fails

```bash
# Ensure run directory exists
ls -la reports/e2e/run_<RUN_ID>/

# Ensure reports directory exists
mkdir -p reports/phase2_gateb_fix

# Check database exists
ls -lh data/example_reviewer.db
```

### Missing test_data_tree.txt

```bash
# Manually create if needed
tree artifacts/backfill/zip/test-data/ > reports/phase2_gateb_fix/test_data_tree.txt

# Or use find
find artifacts/backfill/zip/test-data/ -type f > reports/phase2_gateb_fix/test_data_tree.txt
```

---

## Upload Checklist

Once all packages are created and verified:

1. Review bundle - Share with stakeholders for approval
2. Full reports - Archive for detailed analysis
3. Source code - Commit and tag in git
4. Failure artifacts - Use for debugging any remaining issues

All ZIPs are self-contained and can be uploaded independently.

---

**Last Updated**: 2026-01-24
**Status**: Ready for final validation and packaging
