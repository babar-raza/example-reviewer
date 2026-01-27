# Failure Analytics Queries

This document provides example analytics queries for the failure_details tracking system.

## Overview

The `failure_details` table tracks all failures across the pipeline, including:
- Timeouts (LLM, compilation, runtime)
- Drift exceeded thresholds
- API context missing
- LLM response rejections
- Escalations to review
- Compile errors
- Runtime errors
- Final review failures

## Table Schema

```sql
CREATE TABLE failure_details (
    failure_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    example_id TEXT,
    phase TEXT NOT NULL,
    failure_category TEXT NOT NULL,
    error_category TEXT,
    error_message TEXT,
    resolution TEXT,
    metadata TEXT,  -- JSON
    timestamp TEXT NOT NULL
);
```

## Available Views

### v_failure_breakdown
Pre-aggregated failure counts by category:
```sql
SELECT * FROM v_failure_breakdown;
```

### v_top_error_types
Top error types with fix rates:
```sql
SELECT * FROM v_top_error_types LIMIT 10;
```

### v_resolution_rates
Resolution rates by phase and category:
```sql
SELECT * FROM v_resolution_rates;
```

## Example Analytics Queries

### 1. Failure Breakdown by Category

Get failure counts grouped by category:

```sql
SELECT
    failure_category,
    COUNT(*) as total_failures,
    COUNT(DISTINCT example_id) as unique_examples,
    COUNT(CASE WHEN resolution = 'fixed' THEN 1 END) as fixed_count,
    COUNT(CASE WHEN resolution = 'abandoned' THEN 1 END) as abandoned_count,
    COUNT(CASE WHEN resolution = 'needs_review' THEN 1 END) as needs_review_count,
    ROUND(100.0 * COUNT(CASE WHEN resolution = 'fixed' THEN 1 END) / COUNT(*), 2) as fix_rate_pct
FROM failure_details
GROUP BY failure_category
ORDER BY total_failures DESC;
```

**Expected Output:**
```
| failure_category    | total_failures | unique_examples | fixed_count | abandoned_count | needs_review_count | fix_rate_pct |
|---------------------|----------------|-----------------|-------------|-----------------|-------------------|--------------|
| compile_error       | 450            | 380             | 290         | 60              | 100               | 64.44        |
| runtime_error       | 280            | 250             | 180         | 50              | 50                | 64.29        |
| drift_exceeded      | 120            | 110             | 0           | 120             | 0                 | 0.00         |
| timeout             | 45             | 42              | 5           | 40              | 0                 | 11.11        |
| review_failed       | 35             | 35              | 0           | 0               | 35                | 0.00         |
```

### 2. Top Error Types

Identify the most common specific errors:

```sql
SELECT
    error_category,
    failure_category,
    COUNT(*) as occurrence_count,
    COUNT(DISTINCT example_id) as affected_examples,
    COUNT(CASE WHEN resolution = 'fixed' THEN 1 END) as fixed_count,
    ROUND(100.0 * COUNT(CASE WHEN resolution = 'fixed' THEN 1 END) / COUNT(*), 2) as fix_rate_pct,
    MIN(timestamp) as first_seen,
    MAX(timestamp) as last_seen
FROM failure_details
WHERE error_category IS NOT NULL
GROUP BY error_category, failure_category
ORDER BY occurrence_count DESC
LIMIT 20;
```

**Expected Output:**
```
| error_category          | failure_category | occurrence_count | affected_examples | fixed_count | fix_rate_pct | first_seen          | last_seen           |
|------------------------|------------------|------------------|-------------------|-------------|--------------|---------------------|---------------------|
| CS0246                 | compile_error    | 185              | 160               | 140         | 75.68        | 2026-01-15 10:23:45 | 2026-01-20 16:42:10 |
| FileNotFoundException  | runtime_error    | 95               | 90                | 70          | 73.68        | 2026-01-15 11:05:22 | 2026-01-20 15:30:18 |
| CS0103                 | compile_error    | 82               | 75                | 58          | 70.73        | 2026-01-15 10:45:33 | 2026-01-20 14:22:05 |
| timeout                | timeout          | 45               | 42                | 5           | 11.11        | 2026-01-16 09:15:40 | 2026-01-20 12:18:30 |
| drift_threshold_exceeded| drift_exceeded   | 120              | 110               | 0           | 0.00         | 2026-01-15 12:30:15 | 2026-01-20 17:05:22 |
```

### 3. Resolution Success Rates by Phase

Analyze which phases have the best recovery rates:

```sql
SELECT
    phase,
    failure_category,
    COUNT(*) as total_failures,
    COUNT(CASE WHEN resolution = 'fixed' THEN 1 END) as fixed,
    COUNT(CASE WHEN resolution = 'needs_review' THEN 1 END) as needs_review,
    COUNT(CASE WHEN resolution = 'abandoned' THEN 1 END) as abandoned,
    COUNT(CASE WHEN resolution = 'pending' THEN 1 END) as pending,
    ROUND(100.0 * COUNT(CASE WHEN resolution = 'fixed' THEN 1 END) / COUNT(*), 2) as fix_rate_pct
FROM failure_details
GROUP BY phase, failure_category
ORDER BY phase, total_failures DESC;
```

**Expected Output:**
```
| phase   | failure_category    | total_failures | fixed | needs_review | abandoned | pending | fix_rate_pct |
|---------|---------------------|----------------|-------|--------------|-----------|---------|--------------|
| Phase B | compile_error       | 450            | 290   | 100          | 50        | 10      | 64.44        |
| Phase B | drift_exceeded      | 80             | 0     | 0            | 80        | 0       | 0.00         |
| Phase B | timeout             | 15             | 2     | 0            | 13        | 0       | 13.33        |
| Phase C | runtime_error       | 280            | 180   | 50           | 40        | 10      | 64.29        |
| Phase C | drift_exceeded      | 40             | 0     | 0            | 40        | 0       | 0.00         |
| Phase C | timeout             | 30             | 3     | 0            | 27        | 0       | 10.00        |
| Phase E | review_failed       | 35             | 0     | 35           | 0         | 0       | 0.00         |
```

### 4. Failure Timeline Analysis

Track failure trends over time:

```sql
SELECT
    DATE(timestamp) as failure_date,
    failure_category,
    COUNT(*) as daily_count,
    COUNT(CASE WHEN resolution = 'fixed' THEN 1 END) as fixed_count
FROM failure_details
WHERE timestamp >= datetime('now', '-7 days')
GROUP BY failure_date, failure_category
ORDER BY failure_date DESC, daily_count DESC;
```

### 5. Examples with Multiple Failures

Identify problematic examples that fail repeatedly:

```sql
SELECT
    example_id,
    COUNT(*) as failure_count,
    GROUP_CONCAT(DISTINCT failure_category) as failure_types,
    GROUP_CONCAT(DISTINCT phase) as phases_affected,
    MAX(CASE WHEN resolution = 'fixed' THEN 1 ELSE 0 END) as was_eventually_fixed
FROM failure_details
WHERE example_id IS NOT NULL
GROUP BY example_id
HAVING failure_count > 1
ORDER BY failure_count DESC
LIMIT 25;
```

**Expected Output:**
```
| example_id       | failure_count | failure_types                      | phases_affected | was_eventually_fixed |
|------------------|---------------|------------------------------------|-----------------|---------------------|
| a3f8e2c9d1b4f7e0 | 5             | compile_error,drift_exceeded       | Phase B         | 0                   |
| b1c4d8e2f9a3c6d7 | 4             | compile_error,runtime_error        | Phase B,Phase C | 1                   |
| c9f2a1e5d8b3c4f6 | 3             | compile_error                      | Phase B         | 1                   |
```

### 6. Run-Specific Failure Summary

Get comprehensive failure stats for a specific run:

```sql
SELECT
    r.family,
    r.status as run_status,
    COUNT(f.failure_id) as total_failures,
    COUNT(DISTINCT f.example_id) as affected_examples,
    COUNT(CASE WHEN f.failure_category = 'compile_error' THEN 1 END) as compile_failures,
    COUNT(CASE WHEN f.failure_category = 'runtime_error' THEN 1 END) as runtime_failures,
    COUNT(CASE WHEN f.failure_category = 'drift_exceeded' THEN 1 END) as drift_failures,
    COUNT(CASE WHEN f.failure_category = 'timeout' THEN 1 END) as timeout_failures,
    COUNT(CASE WHEN f.resolution = 'fixed' THEN 1 END) as fixed_count,
    ROUND(100.0 * COUNT(CASE WHEN f.resolution = 'fixed' THEN 1 END) / COUNT(*), 2) as overall_fix_rate_pct
FROM run_records r
LEFT JOIN failure_details f ON r.run_id = f.run_id
WHERE r.run_id = ?  -- Replace with actual run_id
GROUP BY r.run_id;
```

### 7. Error Message Pattern Analysis

Find common error patterns:

```sql
SELECT
    CASE
        WHEN error_message LIKE '%could not be found%' THEN 'Type not found'
        WHEN error_message LIKE '%namespace%' THEN 'Namespace issue'
        WHEN error_message LIKE '%timeout%' THEN 'Timeout'
        WHEN error_message LIKE '%drift%' THEN 'Drift exceeded'
        WHEN error_message LIKE '%file%not%' THEN 'File not found'
        ELSE 'Other'
    END as error_pattern,
    failure_category,
    COUNT(*) as pattern_count,
    COUNT(CASE WHEN resolution = 'fixed' THEN 1 END) as fixed_count,
    ROUND(100.0 * COUNT(CASE WHEN resolution = 'fixed' THEN 1 END) / COUNT(*), 2) as fix_rate_pct
FROM failure_details
WHERE error_message IS NOT NULL
GROUP BY error_pattern, failure_category
ORDER BY pattern_count DESC;
```

### 8. Phase Effectiveness Analysis

Compare phase success in handling failures:

```sql
SELECT
    phase,
    COUNT(*) as total_phase_failures,
    COUNT(DISTINCT example_id) as unique_examples,
    COUNT(CASE WHEN resolution = 'fixed' THEN 1 END) as recovered_in_phase,
    COUNT(CASE WHEN resolution = 'abandoned' THEN 1 END) as abandoned_in_phase,
    ROUND(100.0 * COUNT(CASE WHEN resolution = 'fixed' THEN 1 END) / COUNT(*), 2) as phase_recovery_rate
FROM failure_details
GROUP BY phase
ORDER BY total_phase_failures DESC;
```

## Python API Usage Examples

### Using Database Methods

```python
from src.core.database import Database

db = Database()

# Get failure breakdown for a run
breakdown = db.get_failure_breakdown(run_id="abc123def456")
print(f"Total failures: {breakdown['total_failures']}")
for category in breakdown['failure_categories']:
    print(f"{category['category']}: {category['count']} failures")

# Get top error types
top_errors = db.get_top_error_types(limit=10, run_id="abc123def456")
for error in top_errors:
    print(f"{error['error_category']}: {error['occurrence_count']} occurrences, {error['fix_rate_pct']}% fixed")

# Get resolution rates
resolution_rates = db.get_resolution_rates(run_id="abc123def456")
for rate in resolution_rates:
    print(f"{rate['phase']} - {rate['failure_category']}: {rate['fix_rate_pct']}% success rate")
```

### Tracking Failures in Pipeline

```python
from src.pipeline.failure_tracker import (
    track_compile_failure,
    track_runtime_failure,
    track_drift_exceeded,
    track_timeout,
)
from src.core.models import FailureResolution

# Track a compile failure
track_compile_failure(
    db=db,
    run_id=run_id,
    example_id=example.example_id,
    errors=compile_result.errors,
    resolution=FailureResolution.PENDING,
    metadata={'attempt': 1}
)

# Track drift exceeded
track_drift_exceeded(
    db=db,
    run_id=run_id,
    example_id=example.example_id,
    phase="Phase B",
    drift_score=0.85,
    threshold=0.50,
    resolution=FailureResolution.ABANDONED
)

# Track timeout
track_timeout(
    db=db,
    run_id=run_id,
    phase="Phase B",
    timeout_seconds=300,
    example_id=example.example_id,
    context="LLM compilation fix",
    resolution=FailureResolution.ABANDONED
)
```

## Monitoring and Alerting

### Critical Failure Threshold Query

Alert when failure rate exceeds threshold:

```sql
SELECT
    run_id,
    COUNT(*) as total_failures,
    COUNT(DISTINCT example_id) as affected_examples,
    ROUND(100.0 * COUNT(CASE WHEN resolution = 'abandoned' THEN 1 END) / COUNT(*), 2) as abandoned_rate
FROM failure_details
WHERE timestamp >= datetime('now', '-1 hour')
GROUP BY run_id
HAVING abandoned_rate > 50.0  -- Alert if >50% abandoned
ORDER BY abandoned_rate DESC;
```

### Timeout Spike Detection

Detect unusual timeout patterns:

```sql
SELECT
    phase,
    DATE(timestamp) as failure_date,
    COUNT(*) as timeout_count,
    AVG(json_extract(metadata, '$.timeout_seconds')) as avg_timeout_seconds
FROM failure_details
WHERE failure_category = 'timeout'
  AND timestamp >= datetime('now', '-24 hours')
GROUP BY phase, failure_date
HAVING timeout_count > 10  -- Alert if >10 timeouts in a day
ORDER BY failure_date DESC, timeout_count DESC;
```

## Performance Indexes

The following indexes are created for optimal query performance:

```sql
CREATE INDEX idx_failure_run_phase ON failure_details(run_id, phase);
CREATE INDEX idx_failure_category ON failure_details(failure_category);
CREATE INDEX idx_failure_error_category ON failure_details(error_category);
CREATE INDEX idx_failure_resolution ON failure_details(resolution);
CREATE INDEX idx_failure_timestamp ON failure_details(timestamp);
CREATE INDEX idx_failure_example ON failure_details(example_id);
```
