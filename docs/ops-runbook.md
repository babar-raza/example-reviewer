# Example Reviewer Pipeline: Operator Runbook

**Version**: 1.0
**Last Updated**: 2026-01-20
**Target Audience**: DevOps, Platform Engineers, Production Operators

---

## Table of Contents

1. [Section 1: Running Deterministic Validation](#section-1-running-deterministic-validation)
2. [Section 2: Safe Validation Mode (No Writes)](#section-2-safe-validation-mode-no-writes)
3. [Section 3: Review Queue Management](#section-3-review-queue-management)
4. [Section 4: Telemetry and Failure Analysis](#section-4-telemetry-and-failure-analysis)
5. [Section 5: Troubleshooting](#section-5-troubleshooting)

---

## Section 1: Running Deterministic Validation

Deterministic validation ensures reproducible results across multiple runs. This is critical for validating code examples against drift and detecting anomalies.

### Prerequisites

Before running deterministic validation, ensure:

1. **Python Environment**: Python 3.10+ with virtual environment activated
   ```bash
   python --version  # Should be 3.10 or higher
   ```

2. **Virtual Environment**: Activated `.venv` with dependencies installed
   ```bash
   .venv\Scripts\activate  # Windows
   # or
   source .venv/bin/activate  # Linux/macOS
   ```

3. **Dependencies Installed**: All required packages available
   ```bash
   pip show chromadb pydantic httpx  # Verify key packages
   ```

4. **Database Accessible**: SQLite database file readable/writable
   ```bash
   ls -la data/example_reviewer.db  # File should exist
   ```

5. **Configuration Present**: Family config files in place
   ```bash
   ls config/families/  # Should list: cells.json, email.json, imaging.json, pdf.json, slides.json, words.json, zip.json, etc.
   ```

6. **No Active Services Blocking**: Port availability (if using Vector DB with ChromaDB)
   ```bash
   netstat -an | grep 6333  # Should be empty (or available)
   ```

### Step-by-Step: Running Deterministic Validation

#### Step 1: Verify CLI Tool Availability
```bash
python -m src.cli.main --help
```

**Expected Output**:
```
usage: cli [-h] [--config-dir CONFIG_DIR] [--db-path DB_PATH]
           [--workspace-dir WORKSPACE_DIR] [--verbose] [--json] [--deterministic]
           [--seed SEED]
           {scan,extract,compile-verify,compile-fix,runtime-verify,runtime-fix,...}

Example Reviewer Pipeline CLI
```

#### Step 2: List Available Families
```bash
python -m src.cli.main list-families
```

**Expected Output**:
```
[OK] Success
  families:
    - cells
    - email
    - imaging
    - pdf
    - slides
    - words
    - zip
```

#### Step 3: Run Full Deterministic Pipeline (Dry-Run)
For safety, always start with `--dry-run` to validate configuration without modifying markdown.

```bash
python -m src.cli.main run \
  --family zip \
  --deterministic \
  --seed 42 \
  --max-examples 10 \
  --dry-run
```

**Command Breakdown**:
- `--family zip`: Target the "zip" product family
- `--deterministic`: Set temperature=0, enable deterministic mode
- `--seed 42`: Use reproducible random seed
- `--max-examples 10`: Process first 10 examples
- `--dry-run`: Don't modify markdown files

**Expected Output**:
```
[Pipeline Starting]
Scanning for examples...
Extracting code examples...
Compile verification: 10/10 passed
Runtime verification: 10/10 passed
No markdown changes (dry-run mode)
Telemetry recorded to database

[SUMMARY]
Status: SUCCESS
Duration: 45s
Examples processed: 10
Failures: 0
```

#### Step 4: Run Deterministic Pipeline (With Writes - Requires Safety Flag)
Once dry-run validation passes, enable markdown writes:

```bash
python -m src.cli.main run \
  --family zip \
  --deterministic \
  --seed 42 \
  --max-examples 10 \
  --allow-md-write
```

**Safety Guarantee**: Without `--allow-md-write`, markdown files are never modified.

**Expected Output**:
```
[Pipeline Starting]
Scanning for examples...
Extracting code examples...
Compile verification: 10/10 passed
Runtime verification: 10/10 passed
Markdown update: 5 files modified
Final review: 10/10 passed

[SUMMARY]
Status: SUCCESS
Duration: 52s
Examples processed: 10
Markdown files updated: 5
Failures: 0
```

#### Step 5: Verify Determinism Across Runs
Run the pipeline twice with same seed and compare results:

```bash
# First deterministic run
python -m src.cli.main run \
  --family zip \
  --deterministic \
  --seed 42 \
  --max-examples 10 \
  --dry-run

# Save results
mkdir -p workspace/run1
cp workspace/results_summary.json workspace/run1/

# Second deterministic run (same parameters)
python -m src.cli.main run \
  --family zip \
  --deterministic \
  --seed 42 \
  --max-examples 10 \
  --dry-run

# Save results
mkdir -p workspace/run2
cp workspace/results_summary.json workspace/run2/
```

Now verify determinism using the verification tool:

```bash
python tools/verify_determinism.py \
  workspace/run1/results_summary.json \
  workspace/run2/results_summary.json \
  --drift-tolerance 0.02
```

**Expected Output**:
```
[OK] DETERMINISM VERIFIED
Run 1 Summary:
  - Status counts: VERIFIED=10, NEEDS_REVIEW=0
  - Avg drift: 0.05
  - Max drift: 0.15

Run 2 Summary:
  - Status counts: VERIFIED=10, NEEDS_REVIEW=0
  - Avg drift: 0.05
  - Max drift: 0.15

Comparison Results:
  - Status counts match: YES
  - Drift within tolerance: YES (0.02 max allowed)
  - Terminal statuses match: YES

Conclusion: Runs are DETERMINISTIC (exit code 0)
```

**Exit Codes**:
- `0`: Runs are deterministic (match within tolerance)
- `1`: Runs differ (non-deterministic)
- `2`: Error (files not found, invalid JSON)

### Verification Checklist

After completing deterministic validation:

- [ ] CLI tool loads without errors
- [ ] Family list is non-empty
- [ ] Dry-run completes successfully
- [ ] Determinism check passes (exit code 0)
- [ ] Results are reproducible across runs
- [ ] No unintended markdown changes in dry-run

---

## Section 2: Safe Validation Mode (No Writes)

Safe validation mode allows testing the pipeline without modifying any markdown files. This is enforced by a `markdown_write` guard that requires explicit opt-in via `--allow-md-write`.

### Guard Mechanism: markdown_write

The pipeline has a hard safety guard that prevents ANY markdown file modifications unless explicitly enabled:

```python
# src/mcp_tools/tools.py - MarkdownUpdatePhase
if not allow_md_write:
    # Skip all markdown writes
    return ToolResult(success=True, data={'skipped': 'markdown_write guard enabled'})
```

**Key Protection**:
- Default behavior: NO markdown modifications
- Explicit activation required: `--allow-md-write` flag
- Verified by external tool: `tools/verify_no_md_changes.py`

### Using verify_no_md_changes.py

The `verify_no_md_changes.py` tool ensures markdown files are only modified in allowed paths.

#### Prerequisites for Verification Tool

1. **Git Repository**: Working git repo (for detecting changes)
   ```bash
   git status  # Should show git repo status
   ```

2. **No Uncommitted Markdown Changes**: Start clean
   ```bash
   git diff --name-only *.md  # Should be empty
   ```

3. **Tool Installed**: Python with pathlib
   ```bash
   python --version  # 3.10+
   ```

#### Step 1: Verify Tool Availability
```bash
python tools/verify_no_md_changes.py --help
```

**Expected Output**:
```
usage: verify_no_md_changes.py [-h] [--allow-paths ALLOW_PATHS] [--verbose]

Verify no markdown changes outside allowed paths

options:
  --allow-paths ALLOW_PATHS
                        Comma-separated list of allowed path prefixes
                        (default: specs/,reports/,docs/,plans/)
  --verbose, -v         Verbose output
```

#### Step 2: Run Safe Validation (No Writes)
Execute pipeline with safety guard enabled (default):

```bash
# This will NOT modify any markdown files
python -m src.cli.main run \
  --family zip \
  --max-examples 5 \
  --deterministic
```

Note: No `--allow-md-write` flag = no markdown changes.

#### Step 3: Verify No Changes Were Made
```bash
python tools/verify_no_md_changes.py --verbose
```

**Expected Output**:
```
2026-01-20 10:15:30 - [INFO] Markdown Change Verification
2026-01-20 10:15:30 - [INFO] ================================================================================
2026-01-20 10:15:30 - [INFO] Allowed paths: specs/, reports/, docs/, plans/
2026-01-20 10:15:30 - [INFO]
2026-01-20 10:15:30 - [INFO] No markdown files modified.
2026-01-20 10:15:30 - [INFO]
2026-01-20 10:15:30 - [INFO] [OK] CLEAN - No markdown changes detected

Exit Code: 0
```

#### Step 4: Custom Allowed Paths (If Needed)
To verify only specific paths can be modified:

```bash
python tools/verify_no_md_changes.py \
  --allow-paths "docs/,reports/,specs/" \
  --verbose
```

**Custom Rules**:
- Paths are comma-separated: `docs/,reports/,specs/`
- Paths are prefixes (not exact matches): `docs/` matches `docs/ops-runbook.md`
- Works cross-platform (Windows path separators normalized)

#### Step 5: Run with Markdown Writes (Controlled)
If you explicitly need to update markdown, enable writes:

```bash
python -m src.cli.main run \
  --family zip \
  --max-examples 5 \
  --deterministic \
  --allow-md-write
```

Then verify allowed changes:

```bash
python tools/verify_no_md_changes.py --verbose
```

**Expected Output** (if changes made in allowed paths):
```
2026-01-20 10:16:00 - [INFO] Found 2 modified markdown file(s)
2026-01-20 10:16:00 - [INFO]
2026-01-20 10:16:00 - [INFO] Allowed markdown changes:
2026-01-20 10:16:00 - [INFO]   [OK] docs/code_examples.md
2026-01-20 10:16:00 - [INFO]   [OK] reports/agents/agent-b/ID-06/changes.md
2026-01-20 10:16:00 - [INFO]
2026-01-20 10:16:00 - [INFO] [OK] CLEAN - All markdown changes are in allowed paths

Exit Code: 0
```

**Exit Codes**:
- `0`: No violations (clean)
- `1`: Markdown changes detected outside allowed paths (violation)
- `2`: Error (git not available)

### Safe Validation Workflow

**Recommended pattern for operators**:

```bash
# 1. Always start with dry-run + verify guard
python -m src.cli.main run --family zip --dry-run --deterministic

# 2. Verify no changes were made
python tools/verify_no_md_changes.py

# 3. If changes needed, enable writes
python -m src.cli.main run --family zip --deterministic --allow-md-write

# 4. Verify all changes are in allowed paths
python tools/verify_no_md_changes.py

# 5. Review git diff before committing
git diff --stat
```

---

## Section 3: Review Queue Management

Examples that fail safety checks or need human judgment are placed in the NEEDS_REVIEW queue. Operators must manage this queue through the CLI and database.

### Understanding NEEDS_REVIEW Status

The `NEEDS_REVIEW` status indicates an example requires human review before proceeding:

**Status Machine**:
```
DISCOVERED → COMPILE_VERIFIED → RUNTIME_VERIFIED
    ↓              ↓                    ↓
[ERROR]      [NEEDS_REVIEW]       [NEEDS_REVIEW]
             (escalation)          (escalation)

VERIFIED → MD_UPDATED → FINAL_REVIEW_PASSED → COMMITTED
             ↓                    ↓
        [NEEDS_REVIEW]       [NEEDS_REVIEW]
        (escalation)         (escalation)
```

**Escalation Reasons** (track 2 risk routing):
- `DRIFT_EXCEEDED`: Similarity score below threshold (high drift)
- `TIMEOUT`: Processing timeout occurred
- `VALIDATION_FAILED`: LLM validation rejected output
- `SEED_NOT_SUPPORTED`: Configuration requires manual override
- `CONTEXT_MISSING`: Required API reference or test data unavailable
- `MANUAL_REVIEW_REQUIRED`: Operator escalation flag set

### Prerequisites for Review Queue

1. **Database Access**: SQLite database readable
   ```bash
   sqlite3 data/example_reviewer.db ".tables" | grep -q example_records && echo "DB OK"
   ```

2. **CLI Available**: Review queue command available
   ```bash
   python -m src.cli.main review-queue --help
   ```

3. **Examples Exist**: At least one example in pipeline
   ```bash
   sqlite3 data/example_reviewer.db "SELECT COUNT(*) FROM example_records;"
   ```

### Step 1: List All NEEDS_REVIEW Examples
```bash
python -m src.cli.main review-queue --limit 50
```

**Expected Output**:
```
================================================================================
REVIEW QUEUE - 3 Example(s) Requiring Human Review
================================================================================

[1] docs/examples/zip_usage.md
    Example ID: 5a7f2e1c0d4b8a2...
    Status: NEEDS_REVIEW
    Escalation Reason: DRIFT_EXCEEDED
    Failure Reason: Similarity score 0.28 below threshold 0.30
    Location: Block 2, Lines 45-62

[2] docs/code_samples/pdf_extraction.md
    Example ID: 8c4f1a9e2d6b3c1...
    Status: NEEDS_REVIEW
    Escalation Reason: TIMEOUT
    Failure Reason: Runtime verification timed out after 300s
    Location: Block 1, Lines 10-28

[3] docs/examples/cells_formatting.md
    Example ID: 3b1d4a7f8c2e5a9...
    Status: NEEDS_REVIEW
    Escalation Reason: VALIDATION_FAILED
    Failure Reason: LLM review rejected: unsafe imports detected
    Location: Block 3, Lines 95-110

================================================================================
Total: 3 example(s)
```

### Step 2: List NEEDS_REVIEW for Specific Family
Filter by family to focus on one product area:

```bash
python -m src.cli.main review-queue --family zip --limit 50
```

**Expected Output**:
```
================================================================================
REVIEW QUEUE - 2 Example(s) Requiring Human Review
Family: zip
================================================================================

[1] docs/examples/zip_usage.md
    Example ID: 5a7f2e1c0d4b8a2...
    Status: NEEDS_REVIEW
    Escalation Reason: DRIFT_EXCEEDED
    ...

[2] docs/examples/zip_extract.md
    Example ID: 7e2a4f1d9b3c6e8...
    Status: NEEDS_REVIEW
    Escalation Reason: SEED_NOT_SUPPORTED
    ...

================================================================================
Total: 2 example(s)
```

### Step 3: View Code Snippets for Review
Include code preview for quick visual inspection:

```bash
python -m src.cli.main review-queue --family pdf --show-code --limit 10
```

**Expected Output**:
```
[1] docs/examples/pdf_extraction.md
    Example ID: 8c4f1a9e2d6b3c1...
    Status: NEEDS_REVIEW
    Escalation Reason: TIMEOUT
    Failure Reason: Runtime verification timed out after 300s
    Location: Block 1, Lines 10-28
    Code Preview:
      using System;
      using iTextSharp.text.pdf;

      public class PdfExtractor {
          public void ExtractText(string filename) {
              var reader = new PdfReader(filename);
              // ... more code ...
      ...

[2] docs/examples/pdf_merge.md
    ...
```

### Step 4: Interpret Escalation Reasons

#### DRIFT_EXCEEDED

**What it means**: Example output differs significantly from stored version (high semantic drift).

**Diagnosis Query**:
```bash
sqlite3 data/example_reviewer.db << 'EOF'
SELECT
    example_id,
    file_path,
    drift_score,
    drift_similarity,
    failure_reason
FROM example_records
WHERE status = 'NEEDS_REVIEW'
    AND escalation_reason = 'DRIFT_EXCEEDED'
ORDER BY drift_score DESC;
EOF
```

**Resolution**:
```bash
# Clean vector DB to remove drifted examples
python -m src.cli.main clean-vector-db --family zip --max-drift 0.30

# Or visualize drift to understand distribution
python -m src.cli.main visualize-drift --family zip --format json
```

#### TIMEOUT

**What it means**: Example runtime verification exceeded timeout (default 300s).

**Diagnosis Query**:
```bash
sqlite3 data/example_reviewer.db << 'EOF'
SELECT
    example_id,
    file_path,
    failure_reason
FROM example_records
WHERE status = 'NEEDS_REVIEW'
    AND escalation_reason = 'TIMEOUT'
ORDER BY updated_at DESC;
EOF
```

**Resolution**:
```bash
# Increase timeout and retry
# (modify config/families/<family>.json)
# Or skip runtime-verify phase
python -m src.cli.main run --family zip --skip-runtime
```

#### VALIDATION_FAILED

**What it means**: LLM final review rejected output (safety concern).

**Diagnosis Query**:
```bash
sqlite3 data/example_reviewer.db << 'EOF'
SELECT
    example_id,
    file_path,
    failure_reason
FROM example_records
WHERE status = 'NEEDS_REVIEW'
    AND escalation_reason = 'VALIDATION_FAILED'
ORDER BY updated_at DESC;
EOF
```

**Resolution**:
Manual code review required. Check the failure_reason for specific issues (unsafe imports, unsafe patterns, etc.).

#### SEED_NOT_SUPPORTED

**What it means**: Example configuration requires a seed value not supported by the family.

**Diagnosis Query**:
```bash
sqlite3 data/example_reviewer.db << 'EOF'
SELECT
    example_id,
    file_path,
    failure_reason
FROM example_records
WHERE status = 'NEEDS_REVIEW'
    AND escalation_reason = 'SEED_NOT_SUPPORTED';
EOF
```

**Resolution**:
Update family config to support required seed, or mark example as non-deterministic.

### Step 5: Manual Review Workflow

For each NEEDS_REVIEW example:

```bash
# 1. Export example details
sqlite3 data/example_reviewer.db << 'EOF'
SELECT
    example_id,
    file_path,
    original_code,
    verified_code,
    failure_reason,
    escalation_reason
FROM example_records
WHERE example_id = '5a7f2e1c0d4b8a2'
    AND status = 'NEEDS_REVIEW';
EOF
```

**Review Checklist**:
- [ ] Read original code in `original_code`
- [ ] Compare with `verified_code`
- [ ] Understand `failure_reason`
- [ ] Check `escalation_reason` category
- [ ] Decide: Fix, Accept, or Reject

```bash
# 2. After review, update status
sqlite3 data/example_reviewer.db << 'EOF'
UPDATE example_records
SET status = 'VERIFIED'
WHERE example_id = '5a7f2e1c0d4b8a2';
EOF
```

Or keep as NEEDS_REVIEW pending escalation.

### Step 6: Bulk Operations on Review Queue

#### Export All NEEDS_REVIEW to JSON
```bash
python -m src.cli.main review-queue --limit 1000 --json > review_queue_export.json
```

#### Count by Escalation Reason
```bash
sqlite3 data/example_reviewer.db << 'EOF'
SELECT
    escalation_reason,
    COUNT(*) as count
FROM example_records
WHERE status = 'NEEDS_REVIEW'
GROUP BY escalation_reason
ORDER BY count DESC;
EOF
```

**Sample Output**:
```
DRIFT_EXCEEDED|5
TIMEOUT|2
VALIDATION_FAILED|1
SEED_NOT_SUPPORTED|1
```

---

## Section 4: Telemetry and Failure Analysis

The pipeline captures detailed telemetry for every run. Operators can analyze failures, track resolution patterns, and identify systemic issues.

### Telemetry Data Structure

**Run Records**: Each pipeline run captures ~40 fields
- `run_id`: Unique run identifier
- `job_type`: Type (validation, discovery, etc.)
- `family`: Product family
- `status`: Overall run status
- `examples_processed`: Count of examples
- `examples_passed`: Count that succeeded
- `examples_failed`: Count that failed
- `timestamp`: Run start time

**Failure Details**: Structured tracking for each failure
- `failure_id`: Unique failure identifier
- `run_id`: Associated run
- `example_id`: Affected example
- `phase`: Where failure occurred (compile, runtime, etc.)
- `failure_category`: Type (timeout, drift_exceeded, etc.)
- `error_category`: Specific error type
- `resolution`: Status (fixed, needs_review, abandoned, pending)

### Prerequisites for Telemetry Analysis

1. **Database with Telemetry**: Migration 007 applied
   ```bash
   sqlite3 data/example_reviewer.db ".schema failure_details" | head -5
   ```

2. **SQL Knowledge**: Comfortable with SQL queries
3. **Database Tool**: sqlite3 CLI or similar
   ```bash
   sqlite3 --version
   ```

### Step 1: Query Failure Summary

Get overview of all failures in recent runs:

```bash
sqlite3 data/example_reviewer.db << 'EOF'
SELECT
    failure_category,
    COUNT(*) as failure_count,
    COUNT(DISTINCT run_id) as affected_runs,
    COUNT(DISTINCT example_id) as affected_examples
FROM failure_details
WHERE timestamp > datetime('now', '-7 days')
GROUP BY failure_category
ORDER BY failure_count DESC;
EOF
```

**Expected Output**:
```
failure_category|failure_count|affected_runs|affected_examples
compile_error|12|3|12
timeout|8|2|5
drift_exceeded|5|1|5
runtime_error|3|2|3
```

### Step 2: Analyze by Phase

Track which phases fail most frequently:

```bash
sqlite3 data/example_reviewer.db << 'EOF'
SELECT
    phase,
    failure_category,
    COUNT(*) as total_failures,
    COUNT(CASE WHEN resolution = 'fixed' THEN 1 END) as fixed,
    COUNT(CASE WHEN resolution = 'needs_review' THEN 1 END) as needs_review,
    ROUND(100.0 * COUNT(CASE WHEN resolution = 'fixed' THEN 1 END) / COUNT(*), 2) as fix_rate_pct
FROM failure_details
GROUP BY phase, failure_category
ORDER BY phase, total_failures DESC;
EOF
```

**Sample Output**:
```
phase|failure_category|total_failures|fixed|needs_review|fix_rate_pct
compile|compile_error|12|10|2|83.33
runtime|runtime_error|8|6|2|75.00
runtime|timeout|5|1|4|20.00
finalize|drift_exceeded|3|0|3|0.00
```

### Step 3: Top Error Types

Identify most common errors:

```bash
sqlite3 data/example_reviewer.db << 'EOF'
SELECT
    error_category,
    failure_category,
    COUNT(*) as occurrence_count,
    COUNT(DISTINCT example_id) as affected_examples,
    COUNT(CASE WHEN resolution = 'fixed' THEN 1 END) as fixed_count,
    ROUND(100.0 * COUNT(CASE WHEN resolution = 'fixed' THEN 1 END) / COUNT(*), 2) as fix_rate_pct
FROM failure_details
WHERE error_category IS NOT NULL
GROUP BY error_category, failure_category
ORDER BY occurrence_count DESC
LIMIT 10;
EOF
```

**Sample Output**:
```
error_category|failure_category|occurrence_count|affected_examples|fixed_count|fix_rate_pct
CS0103_undefined_name|compile_error|8|8|7|87.50
ArgumentNullException|runtime_error|5|3|4|80.00
TimeoutException|timeout|4|2|1|25.00
DriftScoreLow|drift_exceeded|3|3|0|0.00
```

### Step 4: Track Resolution Success

Monitor how well LLM fixes resolve issues:

```bash
sqlite3 data/example_reviewer.db << 'EOF'
SELECT
    phase,
    failure_category,
    COUNT(*) as total,
    ROUND(100.0 * COUNT(CASE WHEN resolution = 'fixed' THEN 1 END) / COUNT(*), 2) as fix_rate_pct,
    ROUND(100.0 * COUNT(CASE WHEN resolution = 'needs_review' THEN 1 END) / COUNT(*), 2) as escalation_rate_pct,
    ROUND(100.0 * COUNT(CASE WHEN resolution = 'abandoned' THEN 1 END) / COUNT(*), 2) as abandoned_rate_pct
FROM failure_details
GROUP BY phase, failure_category
ORDER BY phase;
EOF
```

**Sample Output**:
```
phase|failure_category|total|fix_rate_pct|escalation_rate_pct|abandoned_rate_pct
compile|compile_error|12|83.33|16.67|0.00
runtime|runtime_error|8|75.00|25.00|0.00
runtime|timeout|5|20.00|80.00|0.00
finalize|drift_exceeded|3|0.00|100.00|0.00
```

### Step 5: Drift Score Analysis

Understand drift distribution and trends:

```bash
sqlite3 data/example_reviewer.db << 'EOF'
SELECT
    example_id,
    drift_score,
    status,
    failure_reason
FROM example_records
WHERE drift_score IS NOT NULL
ORDER BY drift_score DESC
LIMIT 20;
EOF
```

**Sample Output**:
```
example_id|drift_score|status|failure_reason
5a7f2e1c0d4b8a2|0.52|NEEDS_REVIEW|Drift exceeded threshold 0.30
8c4f1a9e2d6b3c1|0.48|NEEDS_REVIEW|High semantic drift detected
...
```

### Step 6: Visualize Drift Metrics

Use CLI command for visual drift analysis:

```bash
python -m src.cli.main visualize-drift --family zip --format ascii
```

**Expected Output**:
```
Drift Distribution (family: zip)
=================================

0.0-0.1    ███████████████████ (85)
0.1-0.2    ██████████ (42)
0.2-0.3    █████ (18)
0.3-0.4    ██ (8)
0.4-0.5    █ (4)
0.5-0.6    █ (3)
0.6-0.7     (1)
0.7+        (0)

Avg drift: 0.12
Median drift: 0.08
P95 drift: 0.28
Max drift: 0.62
Total examples: 161
```

### Step 7: Drift Trends Over Time

Track drift metrics across runs:

```bash
python -m src.cli.main drift-trends --family zip --last-n-runs 10
```

**Expected Output**:
```
Drift Trends (family: zip, last 10 runs)
=========================================

Run 1 (2026-01-10): Avg 0.18, Max 0.65  ↑
Run 2 (2026-01-11): Avg 0.19, Max 0.68  ↑
Run 3 (2026-01-12): Avg 0.17, Max 0.62  ↓
Run 4 (2026-01-13): Avg 0.15, Max 0.58  ↓
Run 5 (2026-01-14): Avg 0.13, Max 0.55  ↓
Run 6 (2026-01-15): Avg 0.12, Max 0.52  ↓
Run 7 (2026-01-16): Avg 0.11, Max 0.48  ↓
Run 8 (2026-01-17): Avg 0.12, Max 0.50  ↑
Run 9 (2026-01-18): Avg 0.11, Max 0.47  ↓
Run 10 (2026-01-19): Avg 0.10, Max 0.44  ↓

Overall trend: 44% reduction in avg drift
```

### Step 8: Export Failure Data for Analysis

Export to JSON for external analysis:

```bash
sqlite3 data/example_reviewer.db -json << 'EOF'
SELECT
    failure_id,
    run_id,
    example_id,
    phase,
    failure_category,
    error_category,
    resolution,
    timestamp
FROM failure_details
WHERE timestamp > datetime('now', '-30 days')
ORDER BY timestamp DESC;
EOF > failure_export_30days.json
```

---

## Section 5: Troubleshooting

Production issues and their systematic resolution.

### Symptom 1: VectorDB Unavailable

#### Symptom
```
[ERROR] Vector DB not available (disabled or missing dependencies)
[FAIL] Failed to clean vector DB: Vector DB not available
```

#### Diagnosis

**Check 1**: Verify VectorDB is enabled in config
```bash
grep -A 5 '"vector_db"' config/global.json | grep enabled
```

**Check 2**: Verify ChromaDB installation
```bash
python -c "import chromadb; print(chromadb.__version__)"
```

**Check 3**: Check for port conflicts
```bash
netstat -an | grep 6333  # Default ChromaDB port
```

**Check 4**: Review database error logs
```bash
sqlite3 data/example_reviewer.db "SELECT * FROM telemetry_events WHERE level = 'ERROR' ORDER BY timestamp DESC LIMIT 5;"
```

#### Resolution

**Option A: Disable VectorDB** (recommended for troubleshooting)
```json
{
  "vector_db": {
    "enabled": false
  }
}
```

Update `config/global.json`, then retry pipeline:
```bash
python -m src.cli.main run --family zip --dry-run
```

**Option B: Reinstall ChromaDB**
```bash
pip uninstall chromadb -y
pip install chromadb
```

**Option C: Clear VectorDB cache and restart**
```bash
rm -rf .chroma_data  # Or path from config
python -m src.cli.main run --family zip --dry-run
```

---

### Symptom 2: Timeout During Runtime Verification

#### Symptom
```
[ERROR] Example <ID> runtime verification timed out after 300 seconds
Status: NEEDS_REVIEW
Escalation Reason: TIMEOUT
```

#### Diagnosis

**Check 1**: Identify which examples timeout
```bash
sqlite3 data/example_reviewer.db << 'EOF'
SELECT
    example_id,
    file_path,
    failure_reason,
    updated_at
FROM example_records
WHERE escalation_reason = 'TIMEOUT'
ORDER BY updated_at DESC;
EOF
```

**Check 2**: Check system resources
```bash
# Windows
wmic os get totalvisiblememoryvsize,freephysicalmemory

# Linux/macOS
free -h
```

**Check 3**: Review timeout configuration
```bash
grep -A 3 '"runtime"' config/global.json
```

#### Resolution

**Option A: Increase timeout**
Edit `config/global.json`:
```json
{
  "runtime": {
    "timeout_seconds": 600  // Increase from 300 to 600
  }
}
```

**Option B: Skip runtime verification**
```bash
python -m src.cli.main run --family zip --skip-runtime
```

**Option C: Process fewer examples**
```bash
python -m src.cli.main runtime-verify --family zip --max-examples 5
```

**Option D: Kill long-running processes** (Windows)
```bash
taskkill /F /IM csc.exe  # Kill C# compiler if stuck
taskkill /F /IM dotnet.exe  # Kill .NET runtime if stuck
```

---

### Symptom 3: Seed Not Supported

#### Symptom
```
[ERROR] Family 'zip' does not support seed: 12345
Status: NEEDS_REVIEW
Escalation Reason: SEED_NOT_SUPPORTED
```

#### Diagnosis

**Check 1**: View family configuration
```bash
cat config/families/zip.json | grep -A 5 '"seeds"'
```

**Check 2**: List all examples with seed requirements
```bash
sqlite3 data/example_reviewer.db << 'EOF'
SELECT DISTINCT
    example_id,
    file_path
FROM example_records
WHERE description_context LIKE '%seed%'
    AND family = 'zip';
EOF
```

#### Resolution

**Option A: Add seed to family config**
Edit `config/families/zip.json`:
```json
{
  "seeds": [12345, 54321, 99999]
}
```

**Option B: Run without seed**
```bash
python -m src.cli.main run --family zip --deterministic
// Uses default seed 42 instead
```

**Option C: Skip specific examples**
Mark as NEEDS_REVIEW if requiring unsupported seed:
```bash
sqlite3 data/example_reviewer.db << 'EOF'
UPDATE example_records
SET status = 'NEEDS_REVIEW'
WHERE description_context LIKE '%seed%'
    AND family = 'zip';
EOF
```

---

### Symptom 4: Drift Exceeded Threshold

#### Symptom
```
[ERROR] Example output drift 0.52 exceeds threshold 0.30
Status: NEEDS_REVIEW
Escalation Reason: DRIFT_EXCEEDED
```

#### Diagnosis

**Check 1**: View drift score distribution
```bash
python -m src.cli.main visualize-drift --family zip --format json
```

**Check 2**: List high-drift examples
```bash
sqlite3 data/example_reviewer.db << 'EOF'
SELECT
    example_id,
    file_path,
    drift_score,
    status
FROM example_records
WHERE drift_score > 0.30
    AND family = 'zip'
ORDER BY drift_score DESC
LIMIT 20;
EOF
```

**Check 3**: Analyze recent drift trends
```bash
python -m src.cli.main drift-trends --family zip --last-n-runs 5
```

#### Resolution

**Option A: Clean high-drift examples from VectorDB**
```bash
python -m src.cli.main clean-vector-db --family zip --max-drift 0.30
```

Then retry:
```bash
python -m src.cli.main run --family zip --max-examples 10 --deterministic
```

**Option B: Adjust drift threshold**
Edit `config/families/zip.json`:
```json
{
  "validation": {
    "drift_threshold": 0.40  // Increase from 0.30 to 0.40
  }
}
```

**Option C: Investigate individual examples**
```bash
sqlite3 data/example_reviewer.db << 'EOF'
SELECT
    example_id,
    file_path,
    original_code,
    verified_code,
    drift_score
FROM example_records
WHERE example_id = '5a7f2e1c0d4b8a2';
EOF
```

Review differences and decide to accept or fix.

---

### Symptom 5: Database Corruption or Locks

#### Symptom
```
[ERROR] database is locked
[ERROR] sqlite3.OperationalError: database table is locked
```

#### Diagnosis

**Check 1**: Identify lock holders
```bash
lsof | grep example_reviewer.db  # Linux/macOS
```

**Check 2**: Check WAL files
```bash
ls -la data/example_reviewer.db*
// Should show: .db, .db-shm, .db-wal
```

**Check 3**: Database integrity check
```bash
sqlite3 data/example_reviewer.db "PRAGMA integrity_check;"
```

#### Resolution

**Option A: Kill blocking processes**
```bash
# Linux/macOS
pkill -f "python.*src.cli.main"

# Windows
taskkill /F /IM python.exe
```

Then retry:
```bash
python -m src.cli.main list-families
```

**Option B: Recover from WAL**
```bash
sqlite3 data/example_reviewer.db << 'EOF'
PRAGMA journal_mode=DELETE;
VACUUM;
EOF
```

**Option C: Backup and restore**
```bash
# Backup current database
cp data/example_reviewer.db data/example_reviewer.db.backup

# Export data
sqlite3 data/example_reviewer.db.backup ".dump" > database_export.sql

# Create fresh database
rm data/example_reviewer.db*

# Import data
sqlite3 data/example_reviewer.db < database_export.sql
```

---

### Symptom 6: Markdown Write Permission Denied

#### Symptom
```
[ERROR] Permission denied: /path/to/docs/example.md
[FAIL] Unable to write markdown: access denied
```

#### Diagnosis

**Check 1**: Verify file permissions
```bash
ls -la docs/examples/  # Linux/macOS
icacls docs\examples  # Windows
```

**Check 2**: Check directory ownership
```bash
# Linux/macOS
ls -ld docs/

# Windows
icacls docs
```

#### Resolution

**Option A: Fix file permissions** (Linux/macOS)
```bash
chmod 644 docs/examples/*.md
chmod 755 docs/examples/
```

**Option B: Fix directory ownership** (Linux)
```bash
sudo chown -R $(whoami) docs/examples
```

**Option C: Run with elevated privileges** (Windows)
```bash
# Run PowerShell as Administrator, then:
python -m src.cli.main run --family zip --allow-md-write
```

**Option D: Use dry-run instead**
```bash
# If writes not critical, use dry-run
python -m src.cli.main run --family zip --dry-run
```

---

### Symptom 7: LLM API Errors

#### Symptom
```
[ERROR] LLM service error: connection timeout
[ERROR] API key validation failed
[ERROR] Rate limit exceeded
```

#### Diagnosis

**Check 1**: Verify API key
```bash
echo $ANTHROPIC_API_KEY  # Should be non-empty
```

**Check 2**: Check API configuration
```bash
cat config/global.json | grep -A 5 '"llm"'
```

**Check 3**: Test API connectivity
```bash
python -c "from anthropic import Anthropic; print('OK')"
```

#### Resolution

**Option A: Verify API key**
```bash
# Set API key
export ANTHROPIC_API_KEY="sk-..."  # Linux/macOS
set ANTHROPIC_API_KEY=sk-...       # Windows PowerShell
$env:ANTHROPIC_API_KEY='sk-...'    # Windows PS

# Verify
python -m src.cli.main list-families
```

**Option B: Check rate limits**
```bash
# Reduce max examples
python -m src.cli.main run --family zip --max-examples 3

# Or add delay between requests
// Update src/services/llm_service.py to add request_delay
```

**Option C: Skip LLM-based fixing**
```bash
python -m src.cli.main run --family zip --skip-llm
```

---

### Symptom 8: Memory Exhaustion

#### Symptom
```
[ERROR] MemoryError: unable to allocate memory
[ERROR] Process terminated (killed by OS)
```

#### Diagnosis

**Check 1**: Monitor memory usage
```bash
# Linux/macOS
while true; do ps aux | grep python; sleep 1; done

# Windows
Get-Process python | Select-Object Name, WorkingSet -AutoSize
```

**Check 2**: Check available memory
```bash
# Linux/macOS
free -h

# Windows
wmic os get totalvisiblememoryvsize,freephysicalmemory
```

#### Resolution

**Option A: Process fewer examples**
```bash
python -m src.cli.main run --family zip --max-examples 1
```

**Option B: Clear cache and restart**
```bash
# Clear Python cache
find . -type d -name __pycache__ -exec rm -r {} +
find . -type f -name "*.pyc" -delete

# Restart Python
python -m src.cli.main list-families
```

**Option C: Increase system memory**
If running in VM or container, allocate more RAM.

**Option D: Run phases separately**
```bash
python -m src.cli.main extract --family zip
python -m src.cli.main compile-verify --family zip --max-examples 5
python -m src.cli.main runtime-verify --family zip --max-examples 5
```

---

## Summary Table: Quick Reference

| Issue | Diagnosis Command | Resolution Command |
|-------|------|---|
| VectorDB unavailable | `python -c "import chromadb"` | Edit `config/global.json`, set `enabled: false` |
| Timeout | `grep TIMEOUT data/example_reviewer.db` | Increase timeout in config or use `--skip-runtime` |
| Seed not supported | `cat config/families/<family>.json` | Add seed to config or remove requirement |
| Drift exceeded | `python -m src.cli.main visualize-drift --family <f>` | `python -m src.cli.main clean-vector-db --family <f>` |
| Database locked | `sqlite3 data/example_reviewer.db ".tables"` | `taskkill /F /IM python.exe` (Windows) |
| Permission denied | `ls -la docs/` | `chmod 644 docs/examples/*.md` |
| LLM API error | `echo $ANTHROPIC_API_KEY` | Set API key and retry |
| Memory exhausted | `free -h` | `--max-examples 1` or restart |

---

## Appendix A: Command Reference

### Pipeline Execution
```bash
python -m src.cli.main run --family <FAMILY> --deterministic --allow-md-write
python -m src.cli.main run --family <FAMILY> --dry-run --deterministic
python -m src.cli.main run --family <FAMILY> --skip-runtime --skip-llm
```

### Verification
```bash
python tools/verify_determinism.py run1/results_summary.json run2/results_summary.json
python tools/verify_no_md_changes.py --verbose
```

### Queue Management
```bash
python -m src.cli.main review-queue --family <FAMILY> --show-code
python -m src.cli.main review-queue --limit 100 --json > export.json
```

### Analysis
```bash
python -m src.cli.main visualize-drift --family <FAMILY> --format ascii
python -m src.cli.main drift-trends --family <FAMILY> --last-n-runs 10
python -m src.cli.main clean-vector-db --family <FAMILY> --max-drift 0.30
```

---

## Appendix B: Database Queries

### Quick Failure Overview
```sql
SELECT failure_category, COUNT(*) FROM failure_details GROUP BY failure_category;
```

### Examples Needing Review
```sql
SELECT example_id, file_path, escalation_reason FROM example_records
WHERE status = 'NEEDS_REVIEW' ORDER BY updated_at DESC;
```

### Drift Statistics
```sql
SELECT family, AVG(drift_score), MAX(drift_score), MIN(drift_score) FROM example_records
WHERE drift_score IS NOT NULL GROUP BY family;
```

### Resolution Rates
```sql
SELECT phase, failure_category,
  ROUND(100.0 * COUNT(CASE WHEN resolution = 'fixed' THEN 1 END) / COUNT(*), 2) as fix_rate
FROM failure_details GROUP BY phase, failure_category;
```

---

**End of Runbook**
