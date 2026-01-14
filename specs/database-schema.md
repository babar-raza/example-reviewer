# Database Schema Specification

## Overview

The Example Reviewer uses SQLite for persistence with WAL mode enabled for crash resilience. The schema is designed for tracking the complete lifecycle of code snippets from discovery through validation to patching and runtime execution.

**Note:** The system uses raw SQLite connections via the `sqlite3` module (not SQLAlchemy ORM). Database operations are performed using parameterized queries and managed through the `src/core/database.py` module.

## Entity-Relationship Diagram

```
┌─────────────────┐
│      pages      │
│─────────────────│
│ page_id (PK)    │──┐
│ relative_path   │  │
│ family          │  │
│ discovered_at   │  │
│ last_scanned    │  │
│ snippet_count   │  │
└─────────────────┘  │
                     │ 1:N
                     │
┌─────────────────┐  │
│    snippets     │◄─┘
│─────────────────│
│ snippet_id (PK) │──┐
│ page_id (FK)    │  │
│ original_code   │  │
│ verified_code   │  │
│ locator_json    │  │
│ status          │  │
│ created_at      │  │
│ updated_at      │  │
└─────────────────┘  │
                     │ N:M
                     │
┌─────────────────┐  │
│ validation_runs │  │
│─────────────────│  │
│ run_id (PK)     │──┤
│ family          │  │
│ started_at      │  │
│ completed_at    │  │
│ total_snippets  │  │
│ verified_count  │  │
│ needs_fix_count │  │
│ error_count     │  │
└─────────────────┘  │
                     │
┌──────────────────┐ │
│validation_results│◄┤
│──────────────────│ │
│ result_id (PK)   │ │
│ run_id (FK)      │─┘
│ snippet_id (FK)  │─┘
│ status           │
│ compiler_output  │
│ error_messages   │
│ validated_at     │
│ compilation_time │
└──────────────────┘
```

## Tables

### pages

Represents markdown files containing code snippets.

| Column         | Type      | Constraints           | Description                          |
|----------------|-----------|-----------------------|--------------------------------------|
| page_id        | INTEGER   | PRIMARY KEY AUTOINCR  | Unique page identifier               |
| relative_path  | TEXT      | UNIQUE NOT NULL       | Path from content root               |
| family         | TEXT      | NOT NULL              | Product family (e.g., "zip")         |
| discovered_at  | TIMESTAMP | NOT NULL              | First discovery time                 |
| last_scanned   | TIMESTAMP | NOT NULL              | Most recent scan time                |
| snippet_count  | INTEGER   | DEFAULT 0             | Number of snippets in page           |

**Indexes**:
- `idx_pages_family` on `family`
- `idx_pages_relative_path` on `relative_path`

**Example Row**:
```sql
INSERT INTO pages (relative_path, family, discovered_at, last_scanned, snippet_count)
VALUES (
  'content/blog.aspose.net/zip/create-tar-archive-csharp/index.md',
  'zip',
  '2026-01-09 15:30:00',
  '2026-01-09 15:30:00',
  2
);
```

### snippets

Represents individual code snippets extracted from pages.

| Column             | Type      | Constraints           | Description                          |
|--------------------|-----------|-----------------------|--------------------------------------|
| snippet_id         | INTEGER   | PRIMARY KEY AUTOINCR  | Unique snippet identifier            |
| page_id            | INTEGER   | FOREIGN KEY NOT NULL  | Reference to pages.page_id           |
| snippet_ordinal    | INTEGER   | NOT NULL              | Position within page (1-indexed)     |
| locator_json       | TEXT      | NOT NULL              | JSON locator metadata                |
| snippet_type       | TEXT      | NOT NULL              | 'fence' or 'gist'                    |
| language           | TEXT      | NULL                  | Code language (e.g., 'csharp')       |
| status             | TEXT      | NOT NULL              | unverified \| verified \| needs-fix \| skipped |
| first_seen_at      | TEXT      | NOT NULL              | First discovery time                 |
| last_validated_at  | TEXT      | NULL                  | Last validation time                 |
| validation_attempts| INTEGER   | DEFAULT 0             | Number of validation attempts        |
| created_at         | TEXT      | NOT NULL              | Snippet creation time                |
| updated_at         | TEXT      | NOT NULL              | Last modification time               |

**Indexes**:
- `idx_snippets_page` on `page_id`
- `idx_snippets_status` on `status`
- `idx_snippets_type` on `snippet_type`

**Foreign Keys**:
- `page_id` REFERENCES `pages(page_id)` ON DELETE CASCADE

**Unique Constraints**:
- UNIQUE(`page_id`, `snippet_ordinal`) - One snippet per position per page

**Status Values**:
- `unverified`: Newly found, not yet validated
- `verified`: Compiles and (optionally) executes successfully
- `needs-fix`: Compilation or runtime validation failed
- `skipped`: Excluded from validation

**Example Row**:
```sql
INSERT INTO snippets (page_id, original_code, verified_code, locator_json, status, created_at, updated_at)
VALUES (
  1,
  'using (TarArchive archive = new TarArchive()) { }',
  'using Aspose.Zip.Tar;\nusing (TarArchive archive = new TarArchive()) { }',
  '{"snippet_content_hash": "abc123...", "heading_context": ["Create TAR"], "snippet_ordinal": 1}',
  'verified',
  '2026-01-09 15:30:00',
  '2026-01-09 16:45:00'
);
```

### validation_runs

Represents a validation execution session.

| Column          | Type      | Constraints           | Description                          |
|-----------------|-----------|-----------------------|--------------------------------------|
| run_id          | INTEGER   | PRIMARY KEY AUTOINCR  | Unique run identifier                |
| family          | TEXT      | NOT NULL              | Product family being validated       |
| started_at      | TIMESTAMP | NOT NULL              | Run start time                       |
| completed_at    | TIMESTAMP | NULL                  | Run completion time (NULL if active) |
| total_snippets  | INTEGER   | DEFAULT 0             | Total snippets processed             |
| verified_count  | INTEGER   | DEFAULT 0             | Successfully verified snippets       |
| needs_fix_count | INTEGER   | DEFAULT 0             | Snippets needing fixes               |
| error_count     | INTEGER   | DEFAULT 0             | Snippets with fatal errors           |

**Indexes**:
- `idx_validation_runs_family` on `family`
- `idx_validation_runs_started_at` on `started_at` DESC

**Example Row**:
```sql
INSERT INTO validation_runs (family, started_at, completed_at, total_snippets, verified_count, needs_fix_count, error_count)
VALUES (
  'zip',
  '2026-01-09 16:00:00',
  '2026-01-09 16:30:00',
  78,
  50,
  28,
  0
);
```

### validation_results

Represents the outcome of validating a single snippet in a run.

| Column            | Type      | Constraints           | Description                          |
|-------------------|-----------|-----------------------|--------------------------------------|
| result_id         | INTEGER   | PRIMARY KEY AUTOINCR  | Unique result identifier             |
| run_id            | INTEGER   | FOREIGN KEY NOT NULL  | Reference to validation_runs.run_id  |
| snippet_id        | INTEGER   | FOREIGN KEY NOT NULL  | Reference to snippets.snippet_id     |
| status            | TEXT      | NOT NULL              | verified \| needs_fix \| error       |
| compiler_output   | TEXT      | NULL                  | Full dotnet build output             |
| error_messages    | TEXT      | NULL                  | Extracted error messages             |
| validated_at      | TIMESTAMP | NOT NULL              | Validation timestamp                 |
| compilation_time  | REAL      | NULL                  | Compilation duration in seconds      |

**Indexes**:
- `idx_validation_results_run_id` on `run_id`
- `idx_validation_results_snippet_id` on `snippet_id`
- `idx_validation_results_status` on `status`

**Foreign Keys**:
- `run_id` REFERENCES `validation_runs(run_id)` ON DELETE CASCADE
- `snippet_id` REFERENCES `snippets(snippet_id)` ON DELETE CASCADE

**Composite Unique**:
- UNIQUE(`run_id`, `snippet_id`) - One result per snippet per run

**Example Row**:
```sql
INSERT INTO validation_results (run_id, snippet_id, status, compiler_output, error_messages, validated_at, compilation_time)
VALUES (
  2,
  4,
  'verified',
  'Build succeeded.\n    0 Warning(s)\n    0 Error(s)',
  NULL,
  '2026-01-09 16:05:00',
  1.234
);
```

### execution_results

**Added in Schema Version 6 (2026-01-14)**

Stores runtime execution results for snippets that undergo runtime validation (Stage 4.5).

| Column            | Type      | Constraints           | Description                          |
|-------------------|-----------|-----------------------|--------------------------------------|
| execution_id      | INTEGER   | PRIMARY KEY AUTOINCR  | Unique execution identifier          |
| snippet_id        | INTEGER   | FOREIGN KEY NOT NULL  | Reference to snippets.snippet_id     |
| run_id            | INTEGER   | FOREIGN KEY NOT NULL  | Reference to runs.run_id             |
| success           | BOOLEAN   | NOT NULL              | True if execution succeeded          |
| exit_code         | INTEGER   | NULL                  | Process exit code                    |
| duration_ms       | INTEGER   | NULL                  | Execution time in milliseconds       |
| stdout            | TEXT      | NULL                  | Standard output from execution       |
| stderr            | TEXT      | NULL                  | Standard error from execution        |
| exception_type    | TEXT      | NULL                  | Exception type if thrown             |
| exception_message | TEXT      | NULL                  | Exception message                    |
| stack_trace       | TEXT      | NULL                  | Full stack trace if available        |
| output_files_json | TEXT      | NULL                  | JSON list of created output files    |
| memory_peak_kb    | INTEGER   | NULL                  | Peak memory usage in KB              |
| created_at        | TEXT      | NOT NULL              | Execution timestamp                  |

**Indexes**:
- `idx_execution_results_snippet` on (`snippet_id`, `run_id`)
- `idx_execution_results_success` on `success`
- `idx_execution_results_created` on `created_at`

**Foreign Keys**:
- `snippet_id` REFERENCES `snippets(snippet_id)` ON DELETE CASCADE
- `run_id` REFERENCES `runs(run_id)` ON DELETE CASCADE

**Example Row** (successful execution):
```sql
INSERT INTO execution_results (
    snippet_id, run_id, success, exit_code, duration_ms,
    stdout, stderr, exception_type, exception_message, created_at
)
VALUES (
    42,
    5,
    1,
    0,
    1234,
    'Archive created successfully. Size: 324 bytes',
    '',
    NULL,
    NULL,
    '2026-01-14 10:30:00'
);
```

**Example Row** (runtime failure):
```sql
INSERT INTO execution_results (
    snippet_id, run_id, success, exit_code, duration_ms,
    stdout, stderr, exception_type, exception_message, stack_trace, created_at
)
VALUES (
    43,
    5,
    0,
    1,
    156,
    'Starting execution...',
    '',
    'System.ObjectDisposedException',
    'Cannot access a disposed object.\nObject name: ''MemoryStream''.',
    'at System.IO.MemoryStream.Read(...)\nat Aspose.Zip.Archive..ctor(...)',
    '2026-01-14 10:31:00'
);
```

## locator_json Schema

The `snippets.locator_json` column stores JSON with the following structure:

```json
{
  "snippet_content_hash": "sha256_hash_of_original_code",
  "heading_context": ["Parent Heading", "Child Heading"],
  "snippet_ordinal": 1,
  "file_relative_path": "content/blog.aspose.net/zip/...",
  "language": "csharp"
}
```

**Field Descriptions**:
- `snippet_content_hash`: SHA256 hash for exact matching
- `heading_context`: Markdown heading hierarchy leading to snippet
- `snippet_ordinal`: 1-indexed position among C# snippets in page
- `file_relative_path`: Redundant but useful for quick reference
- `language`: Code fence language tag (usually "csharp" or "cs")

## Common Queries

### Get all verified snippets for a family

```sql
SELECT s.snippet_id, s.verified_code, p.relative_path
FROM snippets s
JOIN pages p ON s.page_id = p.page_id
WHERE p.family = 'zip'
  AND s.status = 'verified';
```

### Get validation summary for latest run

```sql
SELECT
  family,
  total_snippets,
  verified_count,
  needs_fix_count,
  error_count,
  CAST(verified_count AS REAL) / total_snippets * 100 AS success_rate
FROM validation_runs
WHERE family = 'zip'
ORDER BY started_at DESC
LIMIT 1;
```

### Get snippets needing fixes

```sql
SELECT
  s.snippet_id,
  p.relative_path,
  vr.error_messages
FROM snippets s
JOIN pages p ON s.page_id = p.page_id
JOIN validation_results vr ON s.snippet_id = vr.snippet_id
WHERE s.status = 'needs_fix'
  AND vr.run_id = (SELECT MAX(run_id) FROM validation_runs WHERE family = 'zip');
```

### Get compilation errors by pattern

```sql
SELECT
  error_messages,
  COUNT(*) as occurrence_count
FROM validation_results
WHERE status = 'needs_fix'
  AND error_messages LIKE '%CS0246%'
GROUP BY error_messages
ORDER BY occurrence_count DESC;
```

### Get patching candidates

```sql
SELECT
  s.snippet_id,
  p.relative_path,
  s.original_code,
  s.verified_code,
  s.locator_json
FROM snippets s
JOIN pages p ON s.page_id = p.page_id
WHERE s.status = 'verified'
  AND s.verified_code IS NOT NULL
  AND s.verified_code != s.original_code
  AND p.family = 'zip';
```

## Migrations

### Schema Creation

The schema is created using the `schema.sql` file in the repository root. On first initialization, run:

```bash
python -m src.cli init-db
```

This executes the SQL script via:
```python
from src.core.database import Database

db = Database("data/examples.db")
db.connect()

with open("schema.sql", 'r') as f:
    db._conn.executescript(f.read())
db._conn.commit()
```

### Schema Updates

For schema changes after initial deployment:

1. **Update schema.sql** with new table/column definitions
2. **Add migration SQL** to the bottom of `schema.sql`:
```sql
-- Schema version 7: Add fix_attempts column
ALTER TABLE snippets ADD COLUMN fix_attempts INTEGER DEFAULT 0;
CREATE INDEX IF NOT EXISTS idx_snippets_fix_attempts ON snippets(fix_attempts);

INSERT OR IGNORE INTO schema_version (version, description)
VALUES (7, 'Add fix_attempts tracking');
```

3. **Re-run initialization** on existing databases (ALTER TABLE is safe):
```bash
python -m src.cli init-db
```

### Data Migration Example

Populate missing locator_json for old snippets:

```python
from src.core.database import Database
from src.discovery.snippet_locator import SnippetLocator
import json

db = Database("data/examples.db")
db.connect()

cursor = db._conn.cursor()
cursor.execute("SELECT snippet_id, page_id FROM snippets WHERE locator_json IS NULL")
snippets_to_fix = cursor.fetchall()

for snippet_id, page_id in snippets_to_fix:
    # Get page info
    cursor.execute("SELECT relative_path FROM pages WHERE page_id = ?", (page_id,))
    relative_path = cursor.fetchone()[0]

    # Create locator
    locator = SnippetLocator.create_locator(
        snippet_code="",  # Would need to fetch actual code
        file_path=relative_path,
        heading_context=[],
        snippet_ordinal=1
    )

    # Update snippet
    cursor.execute(
        "UPDATE snippets SET locator_json = ? WHERE snippet_id = ?",
        (json.dumps(locator), snippet_id)
    )

db._conn.commit()
db.close()
```

## Backup and Restore

### Backup

```bash
# Copy SQLite database
cp data/snippets.db data/snippets.db.backup

# Export to SQL dump
sqlite3 data/snippets.db .dump > data/snippets.sql
```

### Restore

```bash
# From backup
cp data/snippets.db.backup data/snippets.db

# From SQL dump
sqlite3 data/snippets.db < data/snippets.sql
```

## Performance Optimization

### Recommended Indexes

All critical indexes are created by default. For additional performance:

```sql
-- For frequently joining snippets to latest validation results
CREATE INDEX idx_vr_snippet_validated
ON validation_results(snippet_id, validated_at DESC);

-- For family-based filtering
CREATE INDEX idx_pages_family_path
ON pages(family, relative_path);
```

### Query Optimization

**Use EXPLAIN QUERY PLAN**:
```sql
EXPLAIN QUERY PLAN
SELECT s.* FROM snippets s
JOIN pages p ON s.page_id = p.page_id
WHERE p.family = 'zip';
```

**Vacuum Database Periodically**:
```bash
sqlite3 data/snippets.db "VACUUM;"
```

## Integrity Constraints

### Enforced by Database

- Foreign key constraints (ON DELETE CASCADE)
- NOT NULL constraints
- UNIQUE constraints

### Enforced by Application

- Status enum validation (only allowed values)
- JSON schema validation for locator_json
- Timestamp ordering (created_at <= updated_at)

### Validation Checks

```sql
-- Ensure status is valid
CREATE TRIGGER validate_snippet_status
BEFORE INSERT ON snippets
BEGIN
  SELECT CASE
    WHEN NEW.status NOT IN ('discovered', 'verified', 'needs_fix', 'error')
    THEN RAISE(ABORT, 'Invalid snippet status')
  END;
END;

-- Ensure timestamps are ordered
CREATE TRIGGER validate_snippet_timestamps
BEFORE UPDATE ON snippets
BEGIN
  SELECT CASE
    WHEN NEW.updated_at < NEW.created_at
    THEN RAISE(ABORT, 'updated_at must be >= created_at')
  END;
END;
```

## Data Retention

### Cleanup Policies

- **Validation Runs**: Keep last 30 days
- **Validation Results**: Keep last 10 runs per family
- **Snippets**: Keep indefinitely (track documentation evolution)
- **Pages**: Keep indefinitely

### Cleanup Script

```python
from datetime import datetime, timedelta
from database import Database, ValidationRun

db = Database("data/snippets.db")
with db.get_session() as session:
    # Delete runs older than 30 days
    cutoff = datetime.now() - timedelta(days=30)
    session.query(ValidationRun).filter(
        ValidationRun.started_at < cutoff
    ).delete()

    session.commit()
```

## Security Considerations

### SQL Injection Prevention

- All queries use parameterized statements via `sqlite3`
- No string concatenation in SQL
- User input is always passed as query parameters:
  ```python
  # SAFE
  cursor.execute("SELECT * FROM snippets WHERE snippet_id = ?", (snippet_id,))

  # UNSAFE - Never do this
  cursor.execute(f"SELECT * FROM snippets WHERE snippet_id = {snippet_id}")
  ```

### Data Sanitization

- Markdown content escaped before storage
- JSON validated before parsing locator_json
- File paths validated against traversal attacks

### Access Control

- Database file permissions: 600 (owner read/write only)
- No network access (SQLite is local)
- Workspace directories isolated per snippet

## Database Configuration

### Connection Setup

```python
from src.core.database import Database

# Initialize database connection
db = Database("data/examples.db")
db.connect()

# Connection is established with:
# - WAL mode enabled (PRAGMA journal_mode=WAL)
# - Foreign keys enabled (PRAGMA foreign_keys=ON)
# - Row factory set to sqlite3.Row for dict-like access
```

### Connection Parameters

The Database class manages connections with the following defaults:

```python
import sqlite3

self._conn = sqlite3.connect(
    str(self.db_path),
    timeout=30.0,           # 30 second lock timeout
    check_same_thread=False # Allow multi-threading
)
self._conn.row_factory = sqlite3.Row  # Dict-like row access
```

## Monitoring

### Database Size

```bash
ls -lh data/snippets.db
```

### Table Statistics

```sql
SELECT
  name,
  (SELECT COUNT(*) FROM main[name]) as row_count
FROM sqlite_master
WHERE type='table'
ORDER BY row_count DESC;
```

### Index Usage

```sql
.schema snippets  -- Shows all indexes
PRAGMA index_list('snippets');  -- List indexes
PRAGMA index_info('idx_snippets_status');  -- Index details
```
