# Implementation Plan: ID-06 - Drift Metrics Dashboard and Reporting

## Overview
Implement observability features to monitor drift metrics over time, building on completed ID-02 (Drift Threshold Gate) and ID-05 (Selective Vector DB Storage).

## Objectives
1. Export drift metrics to telemetry JSON (avg, max, distribution)
2. Create `visualize-drift` CLI command with ASCII chart
3. Create `drift-trends` CLI command for temporal analysis
4. Track drift reduction after improvements
5. Alert on drift regression

## Implementation Steps

### Step 1: Extend Telemetry Module (src/core/telemetry.py)
**New Functions:**
- `export_drift_metrics(db: Database, family: str) -> dict`
  - Query drift_score values from example_records table
  - Compute avg_drift, max_drift, median_drift, p95_drift
  - Create drift_distribution histogram (8 buckets: 0.0-0.1, 0.1-0.2, ..., 0.7+)
  - Handle missing drift data gracefully

- `get_drift_trends(db: Database, family: str, n_runs: int = 10) -> dict`
  - Query drift metrics across last N runs
  - Group by run_id (from run_records table)
  - Calculate trend direction (↑/↓)
  - Compute overall trend percentage

**Data Flow:**
```
example_records (drift_score)
  → compute_drift_stats()
  → export_drift_metrics()
  → JSON output
```

### Step 2: Extend CLI Module (src/cli/main.py)
**New Commands:**
- `visualize-drift`
  - Args: --family (required), --format (optional, default: ascii)
  - Calls export_drift_metrics()
  - Renders ASCII histogram using █ character
  - Shows summary stats (avg, median, P95)

- `drift-trends`
  - Args: --family (required), --last-n-runs (default: 10)
  - Calls get_drift_trends()
  - Shows run-by-run drift evolution
  - Displays trend arrows (↑/↓)
  - Shows overall trend percentage

**Visualization Functions:**
- `visualize_drift_distribution(family: str, format: str) -> None`
  - Renders ASCII histogram
  - Prints summary statistics

- `show_drift_trends(family: str, n_runs: int) -> None`
  - Displays temporal drift analysis
  - Shows trend direction indicators

### Step 3: Create Test Suite (tests/test_drift_reporting.py)
**Test Coverage:**
1. **Drift Metrics Export (10+ tests):**
   - Test basic drift computation
   - Test empty dataset handling
   - Test single value
   - Test distribution buckets
   - Test percentile calculations
   - Test missing drift_score column (backward compatibility)
   - Test NULL drift values
   - Test extreme values (0.0, 1.0)

2. **Visualization Command (5+ tests):**
   - Test ASCII histogram rendering
   - Test histogram scaling
   - Test JSON output format
   - Test empty data visualization
   - Test format parameter validation

3. **Trends Analysis (5+ tests):**
   - Test multi-run trends
   - Test single run
   - Test trend direction calculation
   - Test trend percentage
   - Test n_runs limit

4. **Edge Cases:**
   - Missing family data
   - No runs in database
   - Partial drift data (some NULLs)
   - Large datasets (1000+ examples)

**Mock Strategy:**
- Use in-memory SQLite database
- Seed with sample drift data
- Mock run_records for trends

## Database Schema Usage

### Queries Required:
```sql
-- Get drift scores for a family
SELECT drift_score, drift_similarity
FROM example_records
WHERE family = ? AND drift_score IS NOT NULL;

-- Get drift by run (requires joining with timestamps)
SELECT
  r.run_id,
  r.started_at,
  e.drift_score
FROM run_records r
JOIN example_records e ON r.family = e.family
WHERE r.family = ?
ORDER BY r.started_at DESC
LIMIT ?;
```

## Algorithm Details

### Drift Statistics Computation:
```python
def compute_drift_stats(drift_scores: List[float]) -> dict:
    """Compute drift statistics from scores."""
    if not drift_scores:
        return {
            'avg_drift': 0.0,
            'median_drift': 0.0,
            'max_drift': 0.0,
            'p95_drift': 0.0,
            'count': 0
        }

    import numpy as np
    return {
        'avg_drift': float(np.mean(drift_scores)),
        'median_drift': float(np.median(drift_scores)),
        'max_drift': float(np.max(drift_scores)),
        'p95_drift': float(np.percentile(drift_scores, 95)),
        'count': len(drift_scores)
    }
```

### Histogram Rendering:
```python
def render_histogram(drift_scores: List[float], width: int = 50) -> str:
    """Render ASCII histogram."""
    import numpy as np

    bins = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 1.0]
    counts, _ = np.histogram(drift_scores, bins=bins)

    max_count = max(counts) if max(counts) > 0 else 1

    lines = []
    for i, count in enumerate(counts):
        label = f"{bins[i]:.1f}-{bins[i+1]:.1f}:"
        bar_width = int((count / max_count) * width)
        bar = '█' * bar_width
        lines.append(f"{label:10} {bar} ({count})")

    return '\n'.join(lines)
```

### Trend Calculation:
```python
def calculate_trend(values: List[float]) -> dict:
    """Calculate trend direction and percentage."""
    if len(values) < 2:
        return {'direction': 'stable', 'percentage': 0.0}

    first_val = values[0]
    last_val = values[-1]

    if first_val == 0:
        return {'direction': 'stable', 'percentage': 0.0}

    percentage = ((last_val - first_val) / first_val) * 100

    if abs(percentage) < 5:
        direction = 'stable'
    elif percentage > 0:
        direction = 'up'
    else:
        direction = 'down'

    return {'direction': direction, 'percentage': percentage}
```

## Expected Outputs

### visualize-drift Output:
```
Drift Distribution (family: zip)
================================

0.0-0.1: ████████████████████ (20)
0.1-0.2: ████████████ (12)
0.2-0.3: ██████ (6)
0.3-0.4: ███ (3)
0.4-0.5: █ (1)
0.5-0.6: █ (1)
0.6-0.7: (0)
0.7+:    (0)

Avg drift: 0.18
Median drift: 0.15
P95 drift: 0.42
Total examples: 43
```

### drift-trends Output:
```
Drift Trends (family: zip, last 10 runs)
========================================

Run 1 (2026-01-10): Avg 0.24, Max 0.65
Run 2 (2026-01-11): Avg 0.21, Max 0.58  ↓
Run 3 (2026-01-12): Avg 0.19, Max 0.52  ↓
Run 4 (2026-01-13): Avg 0.18, Max 0.48  ↓
Run 5 (2026-01-14): Avg 0.22, Max 0.55  ↑

Overall trend: -25% reduction in avg drift
```

### JSON Export (--format json):
```json
{
  "family": "zip",
  "avg_drift": 0.18,
  "median_drift": 0.15,
  "max_drift": 0.65,
  "p95_drift": 0.42,
  "count": 43,
  "drift_distribution": {
    "0.0-0.1": 20,
    "0.1-0.2": 12,
    "0.2-0.3": 6,
    "0.3-0.4": 3,
    "0.4-0.5": 1,
    "0.5-0.6": 1,
    "0.6-0.7": 0,
    "0.7+": 0
  }
}
```

## Quality Checklist
- [ ] All functions have docstrings
- [ ] Backward compatible with missing drift_score column
- [ ] No network calls in tests (use mocks)
- [ ] Deterministic output (same data → same chart)
- [ ] Performance < 1s for visualization, < 2s for trends
- [ ] Error handling for missing data
- [ ] Logging for metric computation
- [ ] 20+ comprehensive tests
- [ ] All tests pass

## Files to Modify
1. `src/core/telemetry.py` - Add drift metrics functions
2. `src/cli/main.py` - Add CLI commands and visualization
3. `tests/test_drift_reporting.py` - New comprehensive test suite

## Risk Mitigation
- **Backward compatibility:** Check if drift_score column exists before querying
- **Performance:** Use efficient SQL queries with indexes
- **Data quality:** Handle NULL/missing values gracefully
- **Testing:** Mock database to avoid test pollution

## Success Metrics
- ✅ `python -m src.cli.main visualize-drift --family zip` works
- ✅ `python -m src.cli.main drift-trends --family zip` works
- ✅ `pytest tests/test_drift_reporting.py -v` passes (20+ tests)
- ✅ Performance: < 1s for visualization, < 2s for trends
- ✅ Quality score: ≥ 48/60 (all dimensions ≥ 4/5)
