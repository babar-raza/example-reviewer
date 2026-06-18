<!-- merged-from: ops-runbook.md, operations.md, troubleshooting.md -->

# Example Reviewer Pipeline: Operations Runbook

**Version**: 2.0
**Last Updated**: 2026-06-17
**Target Audience**: DevOps, Platform Engineers, Production Operators

---

## Table of Contents

### Pipeline Operations
1. [Running Deterministic Validation](#running-deterministic-validation)
2. [Safe Validation Mode (No Writes)](#safe-validation-mode-no-writes)
3. [Review Queue Management](#review-queue-management)
4. [Telemetry and Failure Analysis](#telemetry-and-failure-analysis)

### System Operations
5. [Cache Management](#cache-management)
6. [Database Management](#database-management)
7. [Environment Variables](#environment-variables)
8. [Monitoring & Health Checks](#monitoring--health-checks)
9. [Backup & Recovery](#backup--recovery)

### Troubleshooting
10. [Production Troubleshooting](#production-troubleshooting)
11. [Discovery Issues](#discovery-issues)
12. [Validation Issues](#validation-issues)
13. [Patching Issues](#patching-issues)
14. [Workspace Issues](#workspace-issues)
15. [Logging Issues](#logging-issues)
16. [Getting Help](#getting-help)

### Appendices
- [Command Reference](#appendix-a-command-reference)
- [Database Queries](#appendix-b-database-queries)
- [Quick Reference Table](#quick-reference-table)
- [FAQ](#faq)

---

## Running Deterministic Validation

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

## Safe Validation Mode (No Writes)

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

## Review Queue Management

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

### Step 1: List All NEEDS_REVIEW Examples
```bash
python -m src.cli.main review-queue --limit 50
```

### Step 2: List NEEDS_REVIEW for Specific Family
```bash
python -m src.cli.main review-queue --family zip --limit 50
```

### Step 3: View Code Snippets for Review
```bash
python -m src.cli.main review-queue --family pdf --show-code --limit 10
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

**Resolution**:
```bash
# Increase timeout and retry (modify config/families/<family>.json)
# Or skip runtime-verify phase
python -m src.cli.main run --family zip --skip-runtime
```

#### VALIDATION_FAILED

**What it means**: LLM final review rejected output (safety concern).

**Resolution**: Manual code review required. Check the failure_reason for specific issues (unsafe imports, unsafe patterns, etc.).

#### SEED_NOT_SUPPORTED

**What it means**: Example configuration requires a seed value not supported by the family.

**Resolution**: Update family config to support required seed, or mark example as non-deterministic.

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
WHERE example_id = '<example_id>'
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
WHERE example_id = '<example_id>';
EOF
```

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

---

## Telemetry and Failure Analysis

The pipeline captures detailed telemetry for every run. Operators can analyze failures, track resolution patterns, and identify systemic issues.

### Telemetry Data Structure

**Run Records**: Each pipeline run captures ~40 fields including `run_id`, `job_type`, `family`, `status`, `examples_processed`, `examples_passed`, `examples_failed`, `timestamp`.

**Failure Details**: Structured tracking for each failure including `failure_id`, `run_id`, `example_id`, `phase`, `failure_category`, `error_category`, `resolution`.

### Step 1: Query Failure Summary

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

### Step 2: Analyze by Phase

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

### Step 3: Top Error Types

```bash
sqlite3 data/example_reviewer.db << 'EOF'
SELECT
    error_category,
    failure_category,
    COUNT(*) as occurrence_count,
    COUNT(DISTINCT example_id) as affected_examples,
    ROUND(100.0 * COUNT(CASE WHEN resolution = 'fixed' THEN 1 END) / COUNT(*), 2) as fix_rate_pct
FROM failure_details
WHERE error_category IS NOT NULL
GROUP BY error_category, failure_category
ORDER BY occurrence_count DESC
LIMIT 10;
EOF
```

### Step 4: Track Resolution Success

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

### Step 5: Drift Score Analysis

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

### Step 6: Visualize Drift Metrics

```bash
python -m src.cli.main visualize-drift --family zip --format ascii
```

### Step 7: Drift Trends Over Time

```bash
python -m src.cli.main drift-trends --family zip --last-n-runs 10
```

### Step 8: Export Failure Data for Analysis

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

## Cache Management

### Cache Overview

**Location**: `cache/gists/` (or `$CACHE_DIR` environment variable)

**Purpose**:
- Store GitHub Gist API responses locally
- Reduce API calls and rate limit usage
- Enable offline operation with cached gists

**Structure**:
```
cache/gists/
├── <gist_id>.json              # Gist metadata with ETag
└── <gist_id>/
    ├── file1.cs.raw            # Cached file content
    └── file2.cs.raw
```

**Cache Behavior**:
- ETags used for conditional requests (304 Not Modified)
- Cache considered stale after 1 hour
- Automatic revalidation on stale cache access

### Cache Size Monitoring

```bash
# Check total cache size
du -sh cache/gists/

# List largest cached gists
du -h cache/gists/ | sort -h | tail -20

# Count cached gists
find cache/gists/ -name "*.json" | wc -l
```

### Cache Cleanup

**Safe total cleanup** (cache will be rebuilt):
```bash
rm -rf cache/gists/
# All gists will be re-fetched from GitHub API on next access
```

**Remove stale cache** (older than 7 days):
```bash
find cache/gists/ -name "*.json" -mtime +7 -delete
find cache/gists/ -type d -empty -delete
```

### Cache Validation

The system automatically validates cache integrity during the `discover` command. Corrupted files are logged at WARNING level, automatically removed, and fresh data fetched on next access.

**What is validated**: Valid JSON structure, required fields (`gist_id`, `etag`, `cached_at`, `data`), valid ISO8601 timestamp, `data` containing `files` key.

**Cache Corruption Scenarios** (all handled gracefully):
1. **Invalid JSON** — incomplete writes or power loss → file removed, fresh fetch
2. **Missing Required Fields** — partial or damaged cache → file removed
3. **Invalid Timestamp** — corrupted metadata → file removed
4. **Invalid Data Structure** — malformed response → file removed

**Troubleshooting repeated corruption warnings**:
1. Check disk space: `df -h`
2. Verify no concurrent processes writing to cache
3. Clear all cache and start fresh: `rm -rf cache/gists/*`

---

## Database Management

### Database Overview

**Architecture** (as of 2026-02-12): Dual-database support for production/dev separation.

**Databases**:
- **Development DB** (default): `data/example_reviewer.db`
  - Contains all runs (experimental, test, and production)
  - Default location, always active

- **Production DB** (optional): `data/example_reviewer_prod.db`
  - Contains only runs that created git commits
  - Enabled via configuration (see below)

**Type**: SQLite3 with WAL (Write-Ahead Logging) mode

**Current Tables** (schema):
- `run_records` — Pipeline run metadata
- `example_records` — Canonical example information
- `example_run_state` — Per-run example state
- `compile_attempts` — Compilation results
- `runtime_attempts` — Runtime execution results
- `markdown_edits` — Code modifications made
- `telemetry_runs` — Full telemetry data with git commit info
- `telemetry_events` — Event stream during runs
- `failure_details` — Detailed failure analysis
- `review_results` — Final LLM review results
- `gist_publications` — Published gist tracking

### Production Database Setup

**Enable production database** in `config/global.json`:
```json
{
  "database": {
    "path": "./data/example_reviewer.db",
    "production_path": "./data/example_reviewer_prod.db"
  }
}
```

**Or via CLI**:
```bash
python -m src.cli.main run --family zip --prod-db-path ./data/production.db --commit
```

**Or via environment variable**:
```bash
export EXAMPLE_REVIEWER_PROD_DB_PATH="./data/production.db"
```

**How it works**:
- All runs write to development database during execution
- After successful git commit, the entire run is copied to production database
- Copy is atomic (transaction-based) and includes all related records
- If commit fails, nothing is written to production database

### Database Size Queries

```bash
ls -lh data/example_reviewer.db
ls -lh data/example_reviewer_prod.db  # If production DB is enabled
```

**Table row counts**:
```python
import sqlite3

def get_table_stats(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cursor.fetchall()]
    print(f"\nTable Statistics for {db_path}:")
    for table in tables:
        if table.startswith('sqlite_'):
            continue
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"  {table}: {count:,} rows")
    conn.close()

get_table_stats('data/example_reviewer.db')
```

### Database Cleanup

**IMPORTANT**: Always backup before cleanup operations.

**Delete old runs** (older than 30 days):
```python
import sqlite3
from datetime import datetime, timedelta

conn = sqlite3.connect('data/example_reviewer.db')
cursor = conn.cursor()

cutoff = (datetime.now() - timedelta(days=30)).isoformat()
cursor.execute("DELETE FROM run_records WHERE started_at < ?", (cutoff,))
deleted_runs = cursor.rowcount

conn.commit()
print(f"Deleted {deleted_runs} old runs")
conn.close()
```

### Database Integrity Checks

```bash
# Basic integrity check
sqlite3 data/example_reviewer.db "PRAGMA integrity_check;"

# Foreign key check
sqlite3 data/example_reviewer.db "PRAGMA foreign_key_check;"
```

### Vacuum Database

```bash
# Reclaim space after deletions
sqlite3 data/example_reviewer.db "VACUUM;"

# Check fragmentation
sqlite3 data/example_reviewer.db "
SELECT
    page_count,
    freelist_count,
    ROUND(100.0 * freelist_count / page_count, 2) as fragmentation_pct
FROM pragma_page_count(), pragma_freelist_count();
"
```

---

## Environment Variables

### Core Variables

**GITHUB_TOKEN** (Optional for discovery):
- Purpose: Increase GitHub API rate limit from 60 to 5,000 requests/hour
- Scope: No scopes required for reading public gists
- Usage: `export GITHUB_TOKEN="ghp_your_token_here"`

### Gist Publishing Variables (Phase 5)

**GIST_PUBLISH_OWNER** (Required for upload modes):
- Purpose: GitHub username for publishing new gists
- Example: `export GIST_PUBLISH_OWNER="mycompany"`

**GIST_PUBLISH_TOKEN** (Required for upload modes):
- Purpose: GitHub PAT with `gist` scope for creating gists
- **Security**: Token is never logged (only last 4 chars shown)

**GIST_PUBLISH_PUBLIC** (Optional):
- Purpose: Control whether published gists are public or private
- Default: `true`

### Setting Variables

**Linux/Mac**:
```bash
export GITHUB_TOKEN="ghp_your_token_here"
export GIST_PUBLISH_OWNER="mycompany"
export GIST_PUBLISH_TOKEN="ghp_your_publish_token_here"
export GIST_PUBLISH_PUBLIC="true"
```

**Windows Command Prompt**:
```cmd
set GITHUB_TOKEN=ghp_your_token_here
set GIST_PUBLISH_OWNER=mycompany
set GIST_PUBLISH_TOKEN=ghp_your_publish_token_here
```

**Windows PowerShell**:
```powershell
$env:GITHUB_TOKEN="ghp_your_token_here"
$env:GIST_PUBLISH_OWNER="mycompany"
$env:GIST_PUBLISH_TOKEN="ghp_your_publish_token_here"
```

### Using .env File (Recommended for Development)

Create `.env` file in repository root:
```bash
# .env (already in .gitignore)
GITHUB_TOKEN=ghp_your_read_token_here
GIST_PUBLISH_OWNER=mycompany
GIST_PUBLISH_TOKEN=ghp_your_publish_token_here
GIST_PUBLISH_PUBLIC=true
```

Load with python-dotenv:
```python
from dotenv import load_dotenv
load_dotenv()
```

### CI/CD Integration

**GitHub Actions**:
```yaml
env:
  GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
  GIST_PUBLISH_OWNER: ${{ secrets.GIST_PUBLISH_OWNER }}
  GIST_PUBLISH_TOKEN: ${{ secrets.GIST_PUBLISH_TOKEN }}
```

**GitLab CI**:
```yaml
variables:
  GITHUB_TOKEN: $CI_GITHUB_TOKEN
  GIST_PUBLISH_OWNER: $CI_GIST_OWNER
  GIST_PUBLISH_TOKEN: $CI_GIST_TOKEN
```

---

## Monitoring & Health Checks

### System Health Check

```bash
#!/bin/bash
echo "=== Example Reviewer Health Check ==="

# Python version
echo "Python: $(python --version 2>&1)"

# .NET version
echo ".NET: $(dotnet --version 2>&1)"

# Database status
if [ -f "data/example_reviewer.db" ]; then
    DB_SIZE=$(ls -lh data/example_reviewer.db | awk '{print $5}')
    echo "Database: $DB_SIZE"
else
    echo "Database: Not found"
fi

# Cache status
if [ -d "cache/gists" ]; then
    CACHE_SIZE=$(du -sh cache/gists | awk '{print $1}')
    echo "Cache: $CACHE_SIZE"
else
    echo "Cache: Not initialized"
fi

# Disk space
echo "Disk usage: $(df -h . | tail -1 | awk '{print $5 " used"}')"

# GitHub API rate limit
if [ -n "$GITHUB_TOKEN" ]; then
    echo "GitHub API: Token configured"
else
    echo "GitHub API: No token set (60/hour limit)"
fi

echo "Health check complete"
```

### Database Health Queries

**Recent activity summary**:
```python
import sqlite3
conn = sqlite3.connect('data/example_reviewer.db')
cursor = conn.cursor()

# Examples by status
cursor.execute("SELECT status, COUNT(*) as count FROM example_records GROUP BY status")
print("Examples by status:")
for row in cursor.fetchall():
    print(f"  {row[0]}: {row[1]}")

conn.close()
```

### Performance Metrics

**Average build time**:
```python
import sqlite3
conn = sqlite3.connect('data/example_reviewer.db')
cursor = conn.cursor()

cursor.execute("""
    SELECT
        AVG(CAST(duration_seconds AS REAL)) as avg_duration,
        MIN(duration_seconds) as min_duration,
        MAX(duration_seconds) as max_duration,
        COUNT(*) as total_attempts
    FROM compile_attempts
    WHERE duration_seconds IS NOT NULL
""")

result = cursor.fetchone()
if result and result[0]:
    avg, min_d, max_d, count = result
    print(f"Build performance: Avg {avg:.2f}s, Min {min_d}s, Max {max_d}s ({count} attempts)")
else:
    print("No build attempts recorded yet")

conn.close()
```

---

## Backup & Recovery

### Backup Strategy

**Recommended backup schedule**:
- **Daily**: Automated database backup (keep 30 days)
- **Weekly**: Full system backup including cache (keep 4 weeks)
- **Before major operations**: Manual backup

**What to backup**:
1. Database: `data/example_reviewer.db` (critical)
2. Production DB: `data/example_reviewer_prod.db` (critical, if enabled)
3. Cache: `cache/gists/` (optional, can rebuild)
4. Configuration: `config/` (if customized)

**What NOT to backup**:
- `workspaces/` (temporary build artifacts)
- `.venv/` or `venv/` (virtual environment)

### Manual Backup

```bash
# Simple copy
cp data/example_reviewer.db data/example_reviewer.db.backup-$(date +%Y%m%d)

# SQL dump (portable format)
sqlite3 data/example_reviewer.db .dump > backup-$(date +%Y%m%d).sql
```

### Restore from Backup

```bash
# From binary backup
cp data/example_reviewer.db.backup-20260111 data/example_reviewer.db

# From SQL dump
sqlite3 data/example_reviewer.db < backup-20260111.sql
```

### Disaster Recovery

**Scenario 1: Database corruption**
```bash
# Try SQLite recovery
sqlite3 data/example_reviewer.db ".recover" | sqlite3 data/example_reviewer_recovered.db

# Verify recovered database
sqlite3 data/example_reviewer_recovered.db "PRAGMA integrity_check;"

# If successful, replace
mv data/example_reviewer.db data/example_reviewer.db.corrupt
mv data/example_reviewer_recovered.db data/example_reviewer.db
```

**Scenario 2: Complete data loss**
```bash
# Rebuild from scratch
rm -rf data/example_reviewer.db cache/gists/

# Re-discover content
python -m src.cli.main run --family zip --dry-run
```

---

## Production Troubleshooting

### Symptom 1: VectorDB Unavailable

#### Symptom
```
[ERROR] Vector DB not available (disabled or missing dependencies)
```

#### Diagnosis
```bash
# Check VectorDB config
grep -A 5 '"vector_db"' config/global.json | grep enabled

# Verify ChromaDB installation
python -c "import chromadb; print(chromadb.__version__)"

# Check for port conflicts
netstat -an | grep 6333
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

**Option B: Reinstall ChromaDB**
```bash
pip uninstall chromadb -y
pip install chromadb
```

**Option C: Clear VectorDB cache**
```bash
rm -rf .chroma_data
python -m src.cli.main run --family zip --dry-run
```

---

### Symptom 2: Timeout During Runtime Verification

#### Symptom
```
[ERROR] Example <ID> runtime verification timed out after 300 seconds
Escalation Reason: TIMEOUT
```

#### Resolution

**Option A: Increase timeout** — Edit `config/global.json`:
```json
{
  "runtime": {
    "timeout_seconds": 600
  }
}
```

**Option B: Skip runtime verification**
```bash
python -m src.cli.main run --family zip --skip-runtime
```

**Option C: Kill long-running processes** (Windows)
```bash
taskkill /F /IM dotnet.exe
```

---

### Symptom 3: Seed Not Supported

#### Symptom
```
[ERROR] Family 'zip' does not support seed: 12345
Escalation Reason: SEED_NOT_SUPPORTED
```

#### Resolution

**Option A: Add seed to family config** — Edit `config/families/zip.json`:
```json
{
  "seeds": [12345, 54321, 99999]
}
```

**Option B: Run without seed** (uses default seed 42)
```bash
python -m src.cli.main run --family zip --deterministic
```

---

### Symptom 4: Drift Exceeded Threshold

#### Symptom
```
[ERROR] Example output drift 0.52 exceeds threshold 0.30
Escalation Reason: DRIFT_EXCEEDED
```

#### Resolution

**Option A: Clean high-drift examples from VectorDB**
```bash
python -m src.cli.main clean-vector-db --family zip --max-drift 0.30
python -m src.cli.main run --family zip --max-examples 10 --deterministic
```

**Option B: Adjust drift threshold** — Edit `config/families/zip.json`:
```json
{
  "validation": {
    "drift_threshold": 0.40
  }
}
```

---

### Symptom 5: Database Corruption or Locks

#### Symptom
```
[ERROR] database is locked
[ERROR] sqlite3.OperationalError: database table is locked
```

#### Diagnosis
```bash
# Check WAL files
ls -la data/example_reviewer.db*

# Database integrity check
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

**Option B: Recover from WAL**
```bash
sqlite3 data/example_reviewer.db << 'EOF'
PRAGMA journal_mode=DELETE;
VACUUM;
EOF
```

**Option C: Backup and restore** — see [Backup & Recovery](#backup--recovery).

---

### Symptom 6: Markdown Write Permission Denied

#### Symptom
```
[ERROR] Permission denied: /path/to/docs/example.md
```

#### Resolution

**Linux/macOS**: `chmod 644 docs/examples/*.md && chmod 755 docs/examples/`

**Windows**: Run PowerShell as Administrator, then retry.

**Workaround**: Use dry-run: `python -m src.cli.main run --family zip --dry-run`

---

### Symptom 7: LLM API Errors

#### Symptom
```
[ERROR] LLM service error: connection timeout
[ERROR] API key validation failed
[ERROR] Rate limit exceeded
```

#### Resolution

```bash
# Verify API key
echo $ANTHROPIC_API_KEY  # Should be non-empty

# Check API configuration
grep -A 5 '"llm"' config/global.json

# Reduce load
python -m src.cli.main run --family zip --max-examples 3

# Skip LLM-based fixing
python -m src.cli.main run --family zip --skip-llm
```

---

### Symptom 8: Memory Exhaustion

#### Symptom
```
[ERROR] MemoryError: unable to allocate memory
```

#### Resolution

```bash
# Process fewer examples
python -m src.cli.main run --family zip --max-examples 1

# Run phases separately
python -m src.cli.main extract --family zip
python -m src.cli.main compile-verify --family zip --max-examples 5
python -m src.cli.main runtime-verify --family zip --max-examples 5
```

---

## Discovery Issues

### No Snippets Found

**Symptom**: Discovery reports 0 snippets found.

**Possible Causes**:
1. Wrong content root path
2. Incorrect family pattern
3. No C# code fences in files

**Solutions**:
```bash
# Check content root exists
ls -la ../../content

# Verify family pattern matches files
find ../../content -path "**/zip/**/*.md" | head -5

# Check for C# code fences manually
grep -r "```csharp" ../../content/blog.aspose.net/zip/ | head -5

# Enable debug logging
export LOG_LEVEL="DEBUG"
python -m src.cli.main discover --family zip -v
```

### Permission Denied Errors

**Symptom**: `PermissionError: [Errno 13] Permission denied`

```bash
# Check file permissions
ls -la ../../content

# Fix permissions
chmod -R u+r ../../content
```

---

## Validation Issues

### CS5001: Program does not contain a static 'Main' method

**Cause**: Library mode not enabled in workspace.

**Solution**: Check `workspace_manager.py` has `<OutputType>Library</OutputType>` not `<OutputType>Exe</OutputType>`.

### CS0246: The type or namespace name could not be found

**Possible Causes**: Missing using statement, wrong NuGet package version, package not installed.

```bash
# Check NuGet package in workspace
cat workspaces/snippet_123/Validator.csproj

# Verify package exists
dotnet list workspaces/snippet_123 package

# Clear NuGet cache and restore
dotnet nuget locals all --clear
cd workspaces/snippet_123 && dotnet restore
```

### Compilation Timeout

```bash
# Increase timeout
export COMPILATION_TIMEOUT="120"

# Check dotnet is working
dotnet --version

# Test manual compilation
cd workspaces/snippet_123 && dotnet build -v detailed
```

### Pattern Fixes Not Applied

**Symptom**: Known errors not being fixed automatically.

```python
# Check pattern registry
from src.pattern_registry import PatternRegistry

patterns = PatternRegistry.get_pattern_fixes("zip")
for p in patterns:
    print(f"{p.name}: {p.error_pattern}")
```

---

## Patching Issues

### Could Not Locate Code Fence

**Symptom**: Patching fails with "Could not locate code fence in file".

**Possible Causes**: File modified since discovery, all three strategies (hash, context, fuzzy) failed, code fence deleted.

```bash
# Re-discover snippets
python -m src.cli.main discover --family zip --force

# Try dry-run to see which strategies work
python -m src.cli.main patch --family zip --dry-run -v
```

### Patch Verification Failed

**Symptom**: "Patch verification failed: Expected code not found in any code fence"

**Cause**: Verification regex doesn't match patched content. Debug with:

```python
import re
fence_pattern = r'```(?:csharp|cs|c#|dotnet|net)\s*\n(.*?)\n```'
matches = re.finditer(fence_pattern, modified_content, re.DOTALL | re.IGNORECASE)
for match in matches:
    print(match.group(1)[:100])
```

### Multiple Identical Snippets

**Symptom**: Wrong snippet being patched (fuzzy matching selected wrong code fence).

Use heading context to disambiguate locators:
```json
{
  "heading_context": ["Method 1"],
  "snippet_ordinal": 1
}
```

---

## Workspace Issues

### Disk Space Full

**Symptom**: `OSError: [Errno 28] No space left on device`

```bash
df -h
rm -rf workspaces/*
dotnet nuget locals all --clear
export WORKSPACE_CLEANUP_AUTO="true"
```

### Workspace Creation Fails

```bash
ls -la workspaces/
chmod 755 workspaces/
mkdir -p workspaces
```

### Stale Build Artifacts

```bash
# Clean all workspaces
find workspaces -name "bin" -type d -exec rm -rf {} +
find workspaces -name "obj" -type d -exec rm -rf {} +

# Force rebuild
dotnet build --no-incremental
```

---

## Logging Issues

### No Logs Generated

```bash
mkdir -p logs/
chmod 755 logs/
export LOG_LEVEL="DEBUG"
export LOG_FILE_PATH="logs/debug.log"
```

### Too Many Logs

Enable log rotation in Python:
```python
from logging.handlers import RotatingFileHandler

handler = RotatingFileHandler(
    "logs/example-reviewer.log",
    maxBytes=10*1024*1024,  # 10 MB
    backupCount=5
)
```

---

## Getting Help

### Enable Verbose Output

```bash
export LOG_LEVEL="DEBUG"
python -m src.cli.main <command> -v
```

### Collect Diagnostic Information

```bash
mkdir -p diagnostics/
cp data/example_reviewer.db diagnostics/
cp logs/*.log diagnostics/
sqlite3 data/example_reviewer.db .dump > diagnostics/schema.sql
tar -czf diagnostics-$(date +%Y%m%d).tar.gz diagnostics/
```

### Report Issue

When reporting issues, include:
1. **Error message** (full stack trace)
2. **Command executed**
3. **Environment** (OS, Python version, .NET version)
4. **Logs** (relevant excerpts)
5. **Database state** (snippet counts, validation run status)

---

## Quick Reference Table

| Issue | Diagnosis Command | Resolution Command |
|-------|------|---|
| VectorDB unavailable | `python -c "import chromadb"` | Edit `config/global.json`, set `enabled: false` |
| Timeout | Query `escalation_reason = 'TIMEOUT'` | Increase timeout in config or use `--skip-runtime` |
| Seed not supported | `cat config/families/<family>.json` | Add seed to config or remove requirement |
| Drift exceeded | `python -m src.cli.main visualize-drift --family <f>` | `python -m src.cli.main clean-vector-db --family <f>` |
| Database locked | `sqlite3 data/example_reviewer.db ".tables"` | `taskkill /F /IM python.exe` (Windows) |
| Permission denied | `ls -la docs/` | `chmod 644 docs/examples/*.md` |
| LLM API error | `echo $ANTHROPIC_API_KEY` | Set API key and retry |
| Memory exhausted | `free -h` | `--max-examples 1` or restart |

---

## FAQ

### Q: Why are some snippets marked as "needs_fix" instead of being auto-fixed?

**A**: Pattern fixes only cover known error patterns. If an error doesn't match any pattern and LLM fixing is unavailable or fails, the snippet remains as "needs_fix". Either add a new pattern fix or run the fix command with LLM fixing enabled.

### Q: Can I patch snippets even if they failed validation?

**A**: No. Only snippets with `status='verified'` are patched. Failed snippets must be fixed first.

### Q: How do I reset the database and start over?

```bash
rm data/example_reviewer.db
python -m src.cli.main run --family zip --dry-run
```

### Q: Can I run validation in parallel?

Currently no. Parallel validation is experimental and not yet stable.

### Q: What if I want to use a different .NET framework version?

```bash
export DOTNET_FRAMEWORK="net7.0"
```
And update the .csproj template in `workspace_manager.py`.

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

## Additional Resources

- [Safety Guide](../safety/safety.md) — Operational safeguards and write guards
- [Configuration Guide](../reference/configuration.md) — Environment variables and setup
- [Architecture Documentation](../architecture/architecture.md) — System design and components
- [Performance Benchmarks](performance.md) — Gist system performance baselines
- [Failure Analytics Queries](analytics-queries.md) — Advanced SQL analytics

---

**End of Runbook**
