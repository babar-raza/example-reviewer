# Operations Guide

This guide covers day-to-day operations, monitoring, and maintenance for the Example Reviewer system.

---

## Table of Contents

1. [Cache Management](#cache-management)
2. [Database Management](#database-management)
3. [Environment Variables](#environment-variables)
4. [Monitoring & Health Checks](#monitoring--health-checks)
5. [Troubleshooting](#troubleshooting)
6. [Backup & Recovery](#backup--recovery)
7. [Performance Optimization](#performance-optimization)

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

**Check total cache size**:
```bash
du -sh cache/gists/
# Example output: 22K cache/gists/
```

**List largest cached gists**:
```bash
du -h cache/gists/ | sort -h | tail -20
# Shows 20 largest cache entries
```

**Count cached gists**:
```bash
find cache/gists/ -name "*.json" | wc -l
# Example: 2 (number of gists cached)
```

**Check cache by gist ID**:
```bash
ls -lh cache/gists/78c04f45434d446c01e3543fdd084192/
# Shows files cached for specific gist
```

### Cache Cleanup

**Safe total cleanup** (cache will be rebuilt):
```bash
rm -rf cache/gists/
# All gists will be re-fetched from GitHub API on next access
```

**Remove specific gist cache**:
```bash
# Remove by gist ID
rm -rf cache/gists/<gist_id>.json cache/gists/<gist_id>/
```

**Remove stale cache** (older than 7 days):
```bash
find cache/gists/ -name "*.json" -mtime +7 -delete
find cache/gists/ -type d -empty -delete  # Clean up empty directories
```

**Automated cleanup script**:
```bash
#!/bin/bash
# cleanup_cache.sh - Remove cache older than 30 days

echo "Cleaning gist cache older than 30 days..."
find cache/gists/ -name "*.json" -mtime +30 -print -delete
find cache/gists/ -type d -empty -delete
echo "Cache cleanup complete"
du -sh cache/gists/
```

### Cache Validation

**Automated Cache Validation** (Built-in):

The system automatically validates cache integrity during the `discover` command. This ensures corrupted cache files never cause crashes.

**What is validated**:
- Valid JSON structure
- Required fields: `gist_id`, `etag`, `cached_at`, `data`
- Valid `cached_at` timestamp (ISO8601 format)
- `data` is an object containing `files` key

**Automatic Actions**:
1. Corrupted files are logged at WARNING level with full file paths
2. Corrupted files are automatically removed
3. Fresh data will be fetched from GitHub API on next access
4. Discovery continues without interruption

**Example output**:
```bash
$ python src/cli.py discover --family zip
[*] Starting discovery for family: zip
[*] Verifying gist cache integrity...
WARNING: Corrupted cache file detected: c:\...\data\gist_cache\abc123.json - Invalid JSON, removing
[!] Found and removed 2 corrupted cache files
[i] Run ID: 42
...
```

**Manual cache validation** (Python API):
```python
from pathlib import Path
from src.gist_service import GistService
from src.database import Database

# Initialize
db = Database(Path("data/examples.db"))
cache_dir = Path("data/gist_cache")
service = GistService(cache_dir=cache_dir, db=db)

# Verify cache
result = service.verify_cache()

print(f"Total files: {result['total_files']}")
print(f"Valid files: {result['valid_files']}")
print(f"Corrupted files: {result['corrupted_files']}")

if result['corrupted_files'] > 0:
    print("Removed files:")
    for file_path in result['removed_files']:
        print(f"  - {file_path}")

if result['errors']:
    print("Errors encountered:")
    for error in result['errors']:
        print(f"  - {error['file']}: {error.get('removal_error', 'N/A')}")
```

**Cache Corruption Scenarios**:

All corruption scenarios are handled gracefully:

1. **Invalid JSON** - Caused by incomplete writes or power loss
   - Detection: JSONDecodeError during parsing
   - Action: File removed, logged with path
   - Recovery: Fresh fetch on next access

2. **Missing Required Fields** - Partial or damaged cache
   - Detection: `gist_id`, `etag`, `cached_at`, or `data` missing
   - Action: File removed, specific error logged
   - Recovery: Fresh fetch on next access

3. **Invalid Timestamp** - Corrupted metadata
   - Detection: `cached_at` not valid ISO8601 format
   - Action: File removed, logged
   - Recovery: Fresh fetch on next access

4. **Invalid Data Structure** - Malformed response
   - Detection: `data` not a dict, or `files` key missing
   - Action: File removed, logged
   - Recovery: Fresh fetch on next access

**Performance**:
- Validation runs in <1 second for 100 cache files
- Minimal overhead (only scans .json files)
- Runs automatically before each discovery

**Troubleshooting**:

If you see repeated corruption warnings:
1. Check disk space: `df -h`
2. Check disk health: `smartctl -a /dev/sda` (Linux)
3. Verify no concurrent processes writing to cache
4. Clear all cache and start fresh: `rm -rf data/gist_cache/*`

---

## Database Management

### Database Overview

**Architecture** (as of 2026-02-12): Dual-database support for production/dev separation

**Databases**:
- **Development DB** (default): `data/example_reviewer.db`
  - Contains all runs (experimental, test, and production)
  - Default location, always active

- **Production DB** (optional): `data/example_reviewer_prod.db`
  - Contains only runs that created git commits
  - Enabled via configuration (see below)

**Type**: SQLite3 with WAL (Write-Ahead Logging) mode

**Check database sizes**:
```bash
ls -lh data/example_reviewer.db
ls -lh data/example_reviewer_prod.db  # If production DB is enabled
```

**Current Tables** (schema):
- `run_records` - Pipeline run metadata
- `example_records` - Canonical example information
- `example_run_state` - Per-run example state
- `compile_attempts` - Compilation results
- `runtime_attempts` - Runtime execution results
- `markdown_edits` - Code modifications made
- `telemetry_runs` - Full telemetry data with git commit info
- `telemetry_events` - Event stream during runs
- `failure_details` - Detailed failure analysis
- `review_results` - Final LLM review results
- `gist_publications` - Published gist tracking

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

**Benefits**:
- **Clean analytics**: Query production DB for only committed examples
- **Safe testing**: Experimental runs don't pollute production metrics
- **Audit trail**: Production DB shows exactly what shipped to git

### Database Size Queries

**Check database sizes**:
```bash
# Development database
ls -lh data/example_reviewer.db

# Production database (if enabled)
ls -lh data/example_reviewer_prod.db
```

**Using SQLite**:
```python
import sqlite3

def get_db_size(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
    size_bytes = cursor.fetchone()[0]
    size_mb = size_bytes / (1024 * 1024)
    conn.close()
    return size_mb

print(f"Dev DB: {get_db_size('data/example_reviewer.db'):.2f} MB")
print(f"Prod DB: {get_db_size('data/example_reviewer_prod.db'):.2f} MB")
```

**Table row counts**:
```python
import sqlite3

def get_table_stats(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cursor.fetchall()]

    print(f"\nTable Statistics for {db_path}:")
    for table in tables:
        if table.startswith('sqlite_'):
            continue  # Skip internal tables
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"  {table}: {count:,} rows")

    conn.close()

get_table_stats('data/example_reviewer.db')
get_table_stats('data/example_reviewer_prod.db')  # If production DB enabled
```

### Production Database Analytics

**Query production runs only**:
```python
import sqlite3

conn = sqlite3.connect('data/example_reviewer_prod.db')
cursor = conn.cursor()

# Get production run summary
cursor.execute("""
    SELECT
        product_family,
        COUNT(*) as total_runs,
        SUM(items_succeeded) as total_verified
    FROM telemetry_runs
    WHERE git_commit_hash IS NOT NULL AND git_commit_hash != ''
    GROUP BY product_family
""")

print("Production Runs by Family:")
for row in cursor.fetchall():
    print(f"  {row[0]}: {row[1]} runs, {row[2]} verified examples")

conn.close()
```

**Compare dev vs production databases**:
```python
import sqlite3

def count_runs(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM telemetry_runs")
    count = cursor.fetchone()[0]
    conn.close()
    return count

dev_runs = count_runs('data/example_reviewer.db')
prod_runs = count_runs('data/example_reviewer_prod.db')

print(f"Development runs: {dev_runs}")
print(f"Production runs: {prod_runs}")
print(f"Test/experimental runs: {dev_runs - prod_runs}")
print(f"Production ratio: {prod_runs/dev_runs*100:.1f}%")
```

### Database Cleanup

**IMPORTANT**: Always backup before cleanup operations.

**Delete old runs** (older than 30 days):
```python
import sqlite3
from datetime import datetime, timedelta

conn = sqlite3.connect('data/examples.db')
cursor = conn.cursor()

cutoff = (datetime.now() - timedelta(days=30)).isoformat()
cursor.execute("DELETE FROM runs WHERE started_at < ?", (cutoff,))
deleted_runs = cursor.rowcount

cursor.execute("DELETE FROM run_events WHERE timestamp < ?", (cutoff,))
deleted_events = cursor.rowcount

conn.commit()
print(f"Deleted {deleted_runs} old runs and {deleted_events} events")
conn.close()
```

**Delete old gist cache** (older than 90 days):
```python
import sqlite3
from datetime import datetime, timedelta

conn = sqlite3.connect('data/examples.db')
cursor = conn.cursor()

cutoff = (datetime.now() - timedelta(days=90)).isoformat()
cursor.execute("DELETE FROM gists WHERE last_fetched_at < ?", (cutoff,))
deleted_gists = cursor.rowcount

cursor.execute("DELETE FROM gist_files WHERE gist_id NOT IN (SELECT gist_id FROM gists)")
deleted_files = cursor.rowcount

conn.commit()
print(f"Deleted {deleted_gists} old gists and {deleted_files} orphaned files")
conn.close()
```

**Delete orphaned snippets** (page no longer exists):
```python
import sqlite3

conn = sqlite3.connect('data/examples.db')
cursor = conn.cursor()

cursor.execute("""
    DELETE FROM snippets
    WHERE page_id NOT IN (SELECT page_id FROM pages)
""")
deleted = cursor.rowcount
conn.commit()
print(f"Deleted {deleted} orphaned snippets")
conn.close()
```

**Cleanup script** (combine all):
```python
#!/usr/bin/env python3
"""cleanup_database.py - Database maintenance script"""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

def cleanup_database(db_path="data/examples.db", days_old=30):
    """Clean up old data from database."""

    # Backup first
    backup_path = f"{db_path}.backup-{datetime.now().strftime('%Y%m%d')}"
    Path(backup_path).write_bytes(Path(db_path).read_bytes())
    print(f"Backup created: {backup_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Delete old runs
    cutoff = (datetime.now() - timedelta(days=days_old)).isoformat()
    cursor.execute("DELETE FROM runs WHERE started_at < ?", (cutoff,))
    print(f"Deleted {cursor.rowcount} old runs")

    # Delete old gist cache (90 days)
    gist_cutoff = (datetime.now() - timedelta(days=90)).isoformat()
    cursor.execute("DELETE FROM gists WHERE last_fetched_at < ?", (gist_cutoff,))
    print(f"Deleted {cursor.rowcount} old gists")

    # Delete orphaned records
    cursor.execute("DELETE FROM snippets WHERE page_id NOT IN (SELECT page_id FROM pages)")
    print(f"Deleted {cursor.rowcount} orphaned snippets")

    cursor.execute("DELETE FROM gist_files WHERE gist_id NOT IN (SELECT gist_id FROM gists)")
    print(f"Deleted {cursor.rowcount} orphaned gist files")

    conn.commit()

    # Vacuum to reclaim space
    print("Running VACUUM to reclaim space...")
    cursor.execute("VACUUM")

    conn.close()
    print("Cleanup complete")

if __name__ == "__main__":
    cleanup_database()
```

### Database Integrity Checks

**Basic integrity check**:
```python
import sqlite3
conn = sqlite3.connect('data/examples.db')
cursor = conn.cursor()
cursor.execute("PRAGMA integrity_check")
result = cursor.fetchone()[0]
print(f"Database integrity: {result}")  # Should print "ok"
conn.close()
```

**Foreign key check**:
```python
import sqlite3
conn = sqlite3.connect('data/examples.db')
cursor = conn.cursor()
cursor.execute("PRAGMA foreign_key_check")
violations = cursor.fetchall()
if violations:
    print(f"Found {len(violations)} foreign key violations:")
    for v in violations:
        print(f"  Table: {v[0]}, Row: {v[1]}, Parent: {v[2]}, FK: {v[3]}")
else:
    print("No foreign key violations found")
conn.close()
```

**Schema version check**:
```python
import sqlite3
conn = sqlite3.connect('data/examples.db')
cursor = conn.cursor()
cursor.execute("SELECT version FROM schema_version")
version = cursor.fetchone()[0]
print(f"Database schema version: {version}")
conn.close()
```

### Backup & Restore

**Manual backup**:
```bash
# Simple copy
cp data/examples.db data/examples.db.backup-$(date +%Y%m%d)

# With compression
gzip -c data/examples.db > data/examples.db.backup-$(date +%Y%m%d).gz
```

**SQL dump** (portable format):
```bash
# Export to SQL
sqlite3 data/examples.db .dump > backup-$(date +%Y%m%d).sql

# Compress
gzip backup-$(date +%Y%m%d).sql
```

**Restore from backup**:
```bash
# From binary backup
cp data/examples.db.backup-20260111 data/examples.db

# From SQL dump
sqlite3 data/examples.db < backup-20260111.sql
```

**Automated backup script**:
```bash
#!/bin/bash
# backup_database.sh - Daily database backup

BACKUP_DIR="backups"
DB_FILE="data/examples.db"
DATE=$(date +%Y%m%d)

mkdir -p "$BACKUP_DIR"

# Create backup
cp "$DB_FILE" "$BACKUP_DIR/examples.db.$DATE"
gzip "$BACKUP_DIR/examples.db.$DATE"

# Keep only last 30 days
find "$BACKUP_DIR" -name "examples.db.*.gz" -mtime +30 -delete

echo "Backup complete: $BACKUP_DIR/examples.db.$DATE.gz"
```

**Cron job** (daily at 2 AM):
```cron
0 2 * * * /path/to/backup_database.sh >> /path/to/logs/backup.log 2>&1
```

### Vacuum Database

**Reclaim space** after deletions:
```python
import sqlite3
conn = sqlite3.connect('data/examples.db')
conn.execute("VACUUM")
conn.close()
print("Database vacuumed successfully")
```

**Check fragmentation**:
```python
import sqlite3
conn = sqlite3.connect('data/examples.db')
cursor = conn.cursor()

cursor.execute("PRAGMA page_count")
page_count = cursor.fetchone()[0]

cursor.execute("PRAGMA freelist_count")
free_pages = cursor.fetchone()[0]

fragmentation = (free_pages / page_count) * 100 if page_count > 0 else 0
print(f"Database fragmentation: {fragmentation:.2f}%")

if fragmentation > 10:
    print("Consider running VACUUM")

conn.close()
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
- Scope: `gist` (Create gists)
- Example: `export GIST_PUBLISH_TOKEN="ghp_your_publish_token_here"`
- **Security**: Token is never logged (only last 4 chars shown)

**GIST_PUBLISH_PUBLIC** (Optional):
- Purpose: Control whether published gists are public or private
- Default: `true` (public gists)
- Example: `export GIST_PUBLISH_PUBLIC="false"` for private gists

### Setting Variables

**Linux/Mac**:
```bash
# Temporary (current session)
export GITHUB_TOKEN="ghp_your_token_here"
export GIST_PUBLISH_OWNER="mycompany"
export GIST_PUBLISH_TOKEN="ghp_your_publish_token_here"
export GIST_PUBLISH_PUBLIC="true"

# Persistent (add to ~/.bashrc or ~/.zshrc)
echo 'export GIST_PUBLISH_OWNER="mycompany"' >> ~/.bashrc
echo 'export GIST_PUBLISH_TOKEN="ghp_your_token_here"' >> ~/.bashrc
source ~/.bashrc
```

**Windows Command Prompt**:
```cmd
set GITHUB_TOKEN=ghp_your_token_here
set GIST_PUBLISH_OWNER=mycompany
set GIST_PUBLISH_TOKEN=ghp_your_publish_token_here
set GIST_PUBLISH_PUBLIC=true
```

**Windows PowerShell**:
```powershell
$env:GITHUB_TOKEN="ghp_your_token_here"
$env:GIST_PUBLISH_OWNER="mycompany"
$env:GIST_PUBLISH_TOKEN="ghp_your_publish_token_here"
$env:GIST_PUBLISH_PUBLIC="true"
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

### Verifying Variables

**Check if variables are set**:
```bash
# Linux/Mac/PowerShell
echo $GITHUB_TOKEN
echo $GIST_PUBLISH_OWNER
echo $GIST_PUBLISH_TOKEN

# Windows Command Prompt
echo %GITHUB_TOKEN%
echo %GIST_PUBLISH_OWNER%
echo %GIST_PUBLISH_TOKEN%
```

**Test publishing capability** (dry-run):
```bash
python src/cli.py patch --family zip --gist-mode upload-on-change --dry-run
# Should show: [i] Gist publishing enabled: owner=mycompany, token=...x7a9
```

### CI/CD Integration

**GitHub Actions**:
```yaml
name: Example Reviewer with Gist Publishing
on: [push]
jobs:
  patch:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Patch and publish gists
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          GIST_PUBLISH_OWNER: ${{ secrets.GIST_PUBLISH_OWNER }}
          GIST_PUBLISH_TOKEN: ${{ secrets.GIST_PUBLISH_TOKEN }}
          GIST_PUBLISH_PUBLIC: "true"
        run: |
          python src/cli.py patch --family zip --gist-mode upload-on-change
```

**GitLab CI**:
```yaml
variables:
  GITHUB_TOKEN: $CI_GITHUB_TOKEN
  GIST_PUBLISH_OWNER: $CI_GIST_OWNER
  GIST_PUBLISH_TOKEN: $CI_GIST_TOKEN
  GIST_PUBLISH_PUBLIC: "true"
```

---

## Monitoring & Health Checks

### System Health Check

**Complete health check script**:
```bash
#!/bin/bash
# health_check.sh - System health verification

echo "=== Example Reviewer Health Check ==="
echo ""

# Python version
echo "Python: $(python --version 2>&1)"

# .NET version
echo ".NET: $(dotnet --version 2>&1)"

# Database status
if [ -f "data/examples.db" ]; then
    DB_SIZE=$(ls -lh data/examples.db | awk '{print $5}')
    echo "Database: $DB_SIZE"

    # Count records
    SNIPPET_COUNT=$(python -c "import sqlite3; conn = sqlite3.connect('data/examples.db'); c = conn.cursor(); c.execute('SELECT COUNT(*) FROM snippets'); print(c.fetchone()[0]); conn.close()")
    echo "  Snippets: $SNIPPET_COUNT"

    GIST_COUNT=$(python -c "import sqlite3; conn = sqlite3.connect('data/examples.db'); c = conn.cursor(); c.execute('SELECT COUNT(*) FROM gists'); print(c.fetchone()[0]); conn.close()")
    echo "  Gists: $GIST_COUNT"
else
    echo "Database: Not found"
fi

# Cache status
if [ -d "cache/gists" ]; then
    CACHE_SIZE=$(du -sh cache/gists | awk '{print $1}')
    echo "Cache: $CACHE_SIZE"
    CACHE_FILES=$(find cache/gists -name "*.json" | wc -l)
    echo "  Cached gists: $CACHE_FILES"
else
    echo "Cache: Not initialized"
fi

# Disk space
echo "Disk usage: $(df -h . | tail -1 | awk '{print $5 " used"}')"

# GitHub API rate limit
if [ -n "$GITHUB_TOKEN" ]; then
    RATE_LIMIT=$(curl -s -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/rate_limit | python -c "import json, sys; d=json.load(sys.stdin); print(f\"{d['resources']['core']['remaining']}/{d['resources']['core']['limit']}\")" 2>/dev/null)
    echo "GitHub API: $RATE_LIMIT requests remaining"
else
    echo "GitHub API: No token set (60/hour limit)"
fi

echo ""
echo "Health check complete"
```

### Database Health Queries

**Recent activity summary**:
```python
import sqlite3
conn = sqlite3.connect('data/examples.db')
cursor = conn.cursor()

# Pages by family
cursor.execute("SELECT family, COUNT(*) as count FROM pages GROUP BY family")
print("Pages by family:")
for row in cursor.fetchall():
    print(f"  {row[0]}: {row[1]}")

# Snippets by status
cursor.execute("SELECT status, COUNT(*) as count FROM snippets GROUP BY status")
print("\nSnippets by status:")
for row in cursor.fetchall():
    print(f"  {row[0]}: {row[1]}")

# Gists by fetch status
cursor.execute("SELECT last_status, COUNT(*) as count FROM gists GROUP BY last_status")
print("\nGists by fetch status:")
for row in cursor.fetchall():
    print(f"  {row[0]}: {row[1]}")

conn.close()
```

**Latest run information**:
```python
import sqlite3
conn = sqlite3.connect('data/examples.db')
cursor = conn.cursor()

cursor.execute("""
    SELECT run_id, family, started_at, completed_at, total_pages, total_snippets
    FROM runs
    ORDER BY started_at DESC
    LIMIT 5
""")

print("Recent runs:")
for row in cursor.fetchall():
    run_id, family, started, completed, pages, snippets = row
    print(f"  Run {run_id}: {family} - {snippets} snippets from {pages} pages")
    print(f"    Started: {started}")
    print(f"    Completed: {completed if completed else 'In Progress'}")

conn.close()
```

### Performance Metrics

**Average build time**:
```python
import sqlite3
conn = sqlite3.connect('data/examples.db')
cursor = conn.cursor()

cursor.execute("""
    SELECT
        AVG(CAST(duration_seconds AS REAL)) as avg_duration,
        MIN(duration_seconds) as min_duration,
        MAX(duration_seconds) as max_duration,
        COUNT(*) as total_attempts
    FROM build_attempts
    WHERE duration_seconds IS NOT NULL
""")

result = cursor.fetchone()
if result and result[0]:
    avg, min_d, max_d, count = result
    print(f"Build performance:")
    print(f"  Average: {avg:.2f}s")
    print(f"  Min: {min_d}s")
    print(f"  Max: {max_d}s")
    print(f"  Total attempts: {count}")
else:
    print("No build attempts recorded yet")

conn.close()
```

**Cache hit rate** (requires logging):
```python
# This requires tracking cache hits/misses in code
# Example calculation if data available:
cache_hits = 45
cache_misses = 5
hit_rate = (cache_hits / (cache_hits + cache_misses)) * 100
print(f"Cache hit rate: {hit_rate:.1f}%")
```

---

## Troubleshooting

This section covers the most common operational issues. For comprehensive troubleshooting, see [Troubleshooting Guide](troubleshooting.md).

### Common Issues (Quick Reference)

#### 1. "No module named 'gist_service'"

**Cause**: Python path issue, running from wrong directory

**Solution**:
```bash
# Always run from repository root
cd /path/to/example-reviewer
python src/cli.py <command>

# Or add to PYTHONPATH
export PYTHONPATH="/path/to/example-reviewer:$PYTHONPATH"
```

#### 2. "GITHUB_TOKEN not found" / Rate limit warnings

**Cause**: Token not set or expired

**Solution**:
```bash
# Set token
export GITHUB_TOKEN="ghp_your_token_here"

# Verify token works
curl -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/rate_limit

# Check expiration in GitHub settings
# https://github.com/settings/tokens
```

#### 3. "Rate limit exceeded"

**Cause**: Hit GitHub API rate limit (60/hr without token, 5000/hr with token)

**Solution**:
```bash
# Check when rate limit resets
curl -s https://api.github.com/rate_limit | python -c "
import json, sys
from datetime import datetime
data = json.load(sys.stdin)
reset = datetime.fromtimestamp(data['resources']['core']['reset'])
print(f'Rate limit resets at: {reset}')
"

# Wait until reset time, or set/rotate GITHUB_TOKEN
```

#### 4. "Cache corrupted" / JSON parse errors

**Cause**: Incomplete downloads, disk full during write, corrupted files

**Solution**:
```bash
# Option 1: Delete entire cache (safe - will rebuild)
rm -rf cache/gists/

# Option 2: Validate and remove only corrupted files
python -c "
import json
from pathlib import Path

cache_dir = Path('cache/gists')
for json_file in cache_dir.glob('*.json'):
    try:
        with open(json_file) as f:
            json.load(f)
    except json.JSONDecodeError:
        print(f'Removing corrupted: {json_file}')
        json_file.unlink()
"
```

#### 5. "Database locked"

**Cause**: Multiple processes accessing database, or stale lock

**Solution**:
```bash
# Check for running processes
ps aux | grep "python.*cli.py"

# Kill stale processes
pkill -f "python.*cli.py"

# Enable WAL mode (if not already enabled)
python -c "
import sqlite3
conn = sqlite3.connect('data/examples.db')
conn.execute('PRAGMA journal_mode=WAL')
conn.close()
print('WAL mode enabled')
"

# Increase timeout (in code or config)
export DATABASE_TIMEOUT="60"
```

#### 6. "Permission denied" on cache/data directories

**Cause**: Wrong file permissions or ownership

**Solution**:
```bash
# Fix directory permissions
chmod 755 cache/
chmod 755 cache/gists/
chmod 700 data/

# Fix file permissions
chmod 644 cache/gists/*
chmod 600 data/examples.db

# Check ownership
ls -la data/ cache/

# Fix ownership if needed (replace 'username' with your user)
chown -R username:username data/ cache/
```

#### 7. "Network timeout" / Connection errors

**Cause**: GitHub API unreachable, proxy issues, firewall blocking

**Solution**:
```bash
# Test basic connectivity
curl -v https://api.github.com/rate_limit

# Test with timeout
curl --max-time 10 https://api.github.com/rate_limit

# Check proxy settings
echo $HTTP_PROXY
echo $HTTPS_PROXY

# Bypass proxy (if needed)
unset HTTP_PROXY HTTPS_PROXY

# Test DNS resolution
nslookup api.github.com

# Check firewall (allow HTTPS outbound)
# Contact network admin if blocked
```

### Diagnostic Commands

**Full system diagnostics**:
```bash
# Run health check
./health_check.sh

# Check database integrity
python -c "
import sqlite3
conn = sqlite3.connect('data/examples.db')
c = conn.cursor()
c.execute('PRAGMA integrity_check')
print(c.fetchone()[0])
c.execute('PRAGMA foreign_key_check')
violations = c.fetchall()
if violations:
    print(f'Foreign key violations: {len(violations)}')
conn.close()
"

# Check cache integrity
find cache/gists -name "*.json" -exec python -c "
import json, sys
try:
    json.load(open('{}'))
except Exception as e:
    print('Corrupted: {} - {}'.format('{}', e))
" \;

# Check disk space
df -h .

# Check for stale processes
ps aux | grep example-reviewer
```

---

## Backup & Recovery

### Backup Strategy

**Recommended backup schedule**:
- **Daily**: Automated database backup (keep 30 days)
- **Weekly**: Full system backup including cache (keep 4 weeks)
- **Before major operations**: Manual backup

**What to backup**:
1. Database: `data/examples.db` (critical)
2. Cache: `cache/gists/` (optional, can rebuild)
3. Configuration: `config/` (if customized)
4. Logs: `logs/` (optional, for troubleshooting)

**What NOT to backup**:
- `workspaces/` (temporary build artifacts)
- `reports/` (generated reports)
- `.venv/` or `venv/` (virtual environment)

### Disaster Recovery

**Scenario 1: Database corruption**

```bash
# Try SQLite recovery
sqlite3 data/examples.db ".recover" | sqlite3 data/examples_recovered.db

# Verify recovered database
python -c "
import sqlite3
conn = sqlite3.connect('data/examples_recovered.db')
c = conn.cursor()
c.execute('PRAGMA integrity_check')
print(c.fetchone()[0])
conn.close()
"

# If successful, replace
mv data/examples.db data/examples.db.corrupt
mv data/examples_recovered.db data/examples.db
```

**Scenario 2: Complete data loss**

```bash
# Rebuild from scratch
rm -rf data/examples.db cache/gists/

# Re-initialize database
python src/cli.py init-db

# Re-discover content
python src/cli.py discover --family zip

# Re-validate
python src/cli.py validate --family zip
```

**Scenario 3: Accidental deletion**

```bash
# Restore from latest backup
cp data/examples.db.backup-$(date +%Y%m%d) data/examples.db

# Verify restore
python -c "
import sqlite3
conn = sqlite3.connect('data/examples.db')
c = conn.cursor()
c.execute('SELECT COUNT(*) FROM snippets')
print(f'Restored {c.fetchone()[0]} snippets')
conn.close()
"
```

---

## Performance Optimization

### Database Optimization

**Enable WAL mode** (if not already enabled):
```python
import sqlite3
conn = sqlite3.connect('data/examples.db')
conn.execute('PRAGMA journal_mode=WAL')
result = conn.execute('PRAGMA journal_mode').fetchone()[0]
print(f"Journal mode: {result}")
conn.close()
```

**Analyze and optimize**:
```python
import sqlite3
conn = sqlite3.connect('data/examples.db')
conn.execute('ANALYZE')
conn.close()
print("Database analyzed and optimized")
```

**Check index usage**:
```python
import sqlite3
conn = sqlite3.connect('data/examples.db')
cursor = conn.cursor()

# List all indexes
cursor.execute("""
    SELECT name, tbl_name, sql
    FROM sqlite_master
    WHERE type='index' AND sql IS NOT NULL
    ORDER BY tbl_name, name
""")

print("Indexes:")
for row in cursor.fetchall():
    print(f"  {row[0]} on {row[1]}")

conn.close()
```

### Cache Optimization

**Pre-warm cache** before large operations:
```bash
# Fetch all gists used in a family
python src/cli.py discover --family zip --dry-run
# This will cache all gists without modifying files
```

**Monitor cache hit rate**:
```python
# Track in code with logging:
# [INFO] Gist cache hit: <gist_id>
# [INFO] Gist cache miss: <gist_id>

# Analyze logs
grep "Gist cache" logs/example-reviewer.log | \
  awk '{print $4}' | sort | uniq -c
```

### Disk I/O Optimization

**Use faster storage for workspaces**:
```bash
# Move workspaces to tmpfs (Linux)
export WORKSPACE_BASE_PATH="/tmp/example-reviewer-workspaces"

# Or use SSD
export WORKSPACE_BASE_PATH="/mnt/ssd/workspaces"
```

**Monitor disk I/O**:
```bash
# Linux
iostat -x 1

# Check if disk is bottleneck
iotop -o
```

---

## Additional Resources

- [Security Guide](security.md) - Token management and security best practices
- [Configuration Guide](configuration.md) - Environment variables and setup
- [Troubleshooting Guide](troubleshooting.md) - Comprehensive issue resolution
- [Architecture Documentation](architecture.md) - System design and components

---

**Last Updated**: 2026-01-11
**Next Review**: 2026-04-11 (quarterly)
