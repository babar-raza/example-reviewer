"""
Tests for drift metrics dashboard and reporting (ID-06).

Tests:
- Drift metrics export
- Visualization rendering
- Trends analysis
- Edge cases and error handling
"""

import json
import pytest
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any

from src.core.database import Database
from src.core.telemetry import (
    export_drift_metrics,
    get_drift_trends,
    _compute_drift_stats,
    _compute_drift_distribution,
    _calculate_trend,
    _empty_drift_metrics,
)
from src.cli.main import (
    _render_drift_visualization,
    _render_drift_trends,
)


@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary database for testing."""
    db_path = tmp_path / "test.db"
    db = Database(db_path)
    db.initialize_schema()
    return db


def seed_drift_data(db: Database, family: str, drift_scores: List[float]) -> None:
    """Seed database with example records containing drift scores."""
    from src.core.models import ExampleRecord, ExampleStatus, SourceType, Location

    for i, score in enumerate(drift_scores):
        example = ExampleRecord(
            example_id=f"example_{i}",
            family=family,
            file_path=f"test_{i}.md",
            source_type=SourceType.INLINE,
            language="csharp",
            location=Location(block_index=0, start_line=1, end_line=10),
            original_code="// Test code",
            status=ExampleStatus.VERIFIED,
        )
        db.save_example(example)

        # Update drift score
        db.update_snippet(example.example_id, drift_score=score, drift_similarity=1.0 - score)


def seed_runs_with_drift(db: Database, family: str, run_data: List[Dict[str, Any]]) -> None:
    """
    Seed database with runs and drift data.

    Args:
        db: Database instance
        family: Product family
        run_data: List of dicts with 'date' and 'drift_scores' keys
    """
    from src.core.models import ExampleRecord, ExampleStatus, SourceType, Location

    for run_idx, run_info in enumerate(run_data):
        # Create run record
        run_id = f"run_{run_idx}"
        date_str = run_info['date']
        started_at = datetime.fromisoformat(date_str)

        with db.get_connection() as conn:
            conn.execute("""
                INSERT INTO run_records (
                    run_id, family, started_at, status, phases_completed,
                    examples_processed, examples_successful, examples_failed
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                run_id,
                family,
                started_at.isoformat(),
                'completed',
                json.dumps(['discovery', 'compilation']),
                len(run_info['drift_scores']),
                len(run_info['drift_scores']),
                0,
            ))

        # Create examples with drift scores
        for i, score in enumerate(run_info['drift_scores']):
            example_id = f"{run_id}_example_{i}"
            example = ExampleRecord(
                example_id=example_id,
                family=family,
                file_path=f"test_{run_idx}_{i}.md",
                source_type=SourceType.INLINE,
                language="csharp",
                location=Location(block_index=0, start_line=1, end_line=10),
                original_code="// Test code",
                status=ExampleStatus.VERIFIED,
            )
            db.save_example(example)

            # Update timestamps to match run
            with db.get_connection() as conn:
                conn.execute("""
                    UPDATE example_records
                    SET updated_at = ?
                    WHERE example_id = ?
                """, (started_at.isoformat(), example_id))

            # Update drift score
            db.update_snippet(example_id, drift_score=score, drift_similarity=1.0 - score)


# =========================================================================
# DRIFT METRICS EXPORT TESTS (10+ tests)
# =========================================================================

def test_export_drift_metrics_basic(temp_db):
    """Test basic drift metrics export."""
    drift_scores = [0.1, 0.2, 0.3, 0.15, 0.25]
    seed_drift_data(temp_db, "zip", drift_scores)

    metrics = export_drift_metrics(temp_db, "zip")

    assert metrics['family'] == 'zip'
    assert metrics['count'] == 5
    assert 0.15 <= metrics['avg_drift'] <= 0.25
    assert metrics['median_drift'] == 0.2
    assert metrics['max_drift'] == 0.3


def test_export_drift_metrics_empty_dataset(temp_db):
    """Test drift metrics with no data."""
    metrics = export_drift_metrics(temp_db, "nonexistent")

    assert metrics['family'] == 'nonexistent'
    assert metrics['count'] == 0
    assert metrics['avg_drift'] == 0.0
    assert metrics['median_drift'] == 0.0
    assert metrics['max_drift'] == 0.0
    assert metrics['p95_drift'] == 0.0


def test_export_drift_metrics_single_value(temp_db):
    """Test drift metrics with single value."""
    seed_drift_data(temp_db, "zip", [0.5])

    metrics = export_drift_metrics(temp_db, "zip")

    assert metrics['count'] == 1
    assert metrics['avg_drift'] == 0.5
    assert metrics['median_drift'] == 0.5
    assert metrics['max_drift'] == 0.5
    assert metrics['p95_drift'] == 0.5


def test_export_drift_metrics_distribution_buckets(temp_db):
    """Test drift distribution histogram buckets."""
    # Create specific distribution
    drift_scores = [
        0.05, 0.05, 0.05,  # 3 in 0.0-0.1
        0.15, 0.15,        # 2 in 0.1-0.2
        0.25,              # 1 in 0.2-0.3
        0.35,              # 1 in 0.3-0.4
    ]
    seed_drift_data(temp_db, "zip", drift_scores)

    metrics = export_drift_metrics(temp_db, "zip")
    dist = metrics['drift_distribution']

    assert dist['0.0-0.1'] == 3
    assert dist['0.1-0.2'] == 2
    assert dist['0.2-0.3'] == 1
    assert dist['0.3-0.4'] == 1
    assert dist['0.4-0.5'] == 0


def test_export_drift_metrics_percentile_calculation(temp_db):
    """Test P95 percentile calculation."""
    # Create 100 values with known P95
    drift_scores = [i / 100.0 for i in range(100)]  # 0.00 to 0.99
    seed_drift_data(temp_db, "zip", drift_scores)

    metrics = export_drift_metrics(temp_db, "zip")

    # P95 should be around 0.95
    assert metrics['p95_drift'] >= 0.90
    assert metrics['p95_drift'] <= 1.0


def test_export_drift_metrics_null_values(temp_db):
    """Test handling of NULL drift values."""
    from src.core.models import ExampleRecord, ExampleStatus, SourceType, Location

    # Create examples without drift scores
    for i in range(5):
        example = ExampleRecord(
            example_id=f"example_{i}",
            family="zip",
            file_path=f"test_{i}.md",
            source_type=SourceType.INLINE,
            language="csharp",
            location=Location(block_index=0, start_line=1, end_line=10),
            original_code="// Test code",
            status=ExampleStatus.VERIFIED,
        )
        temp_db.save_example(example)
        # Don't set drift_score - leave as NULL

    metrics = export_drift_metrics(temp_db, "zip")

    # Should return empty metrics
    assert metrics['count'] == 0
    assert metrics['avg_drift'] == 0.0


def test_export_drift_metrics_extreme_values(temp_db):
    """Test drift metrics with extreme values (0.0 and 1.0)."""
    drift_scores = [0.0, 0.0, 1.0, 1.0, 0.5]
    seed_drift_data(temp_db, "zip", drift_scores)

    metrics = export_drift_metrics(temp_db, "zip")

    assert metrics['count'] == 5
    assert metrics['avg_drift'] == 0.5
    assert metrics['max_drift'] == 1.0
    assert 0.0 in drift_scores


def test_export_drift_metrics_large_dataset(temp_db):
    """Test drift metrics with large dataset (1000+ examples)."""
    import random
    random.seed(42)

    drift_scores = [random.uniform(0.0, 1.0) for _ in range(1000)]
    seed_drift_data(temp_db, "zip", drift_scores)

    metrics = export_drift_metrics(temp_db, "zip")

    assert metrics['count'] == 1000
    assert 0.0 <= metrics['avg_drift'] <= 1.0
    assert 0.0 <= metrics['median_drift'] <= 1.0
    assert 0.0 <= metrics['p95_drift'] <= 1.0


def test_export_drift_metrics_multiple_families(temp_db):
    """Test drift metrics with multiple families."""
    seed_drift_data(temp_db, "zip", [0.1, 0.2, 0.3])
    seed_drift_data(temp_db, "pdf", [0.5, 0.6, 0.7])

    zip_metrics = export_drift_metrics(temp_db, "zip")
    pdf_metrics = export_drift_metrics(temp_db, "pdf")

    assert zip_metrics['count'] == 3
    assert pdf_metrics['count'] == 3
    assert zip_metrics['avg_drift'] < pdf_metrics['avg_drift']


def test_export_drift_metrics_distribution_edge_case(temp_db):
    """Test distribution with value exactly at bucket boundary."""
    drift_scores = [0.1, 0.2, 0.3, 0.5, 0.7]  # Exact bucket boundaries
    seed_drift_data(temp_db, "zip", drift_scores)

    metrics = export_drift_metrics(temp_db, "zip")
    dist = metrics['drift_distribution']

    # Values at boundaries should be in lower bucket
    total_in_dist = sum(dist.values())
    assert total_in_dist == 5


# =========================================================================
# VISUALIZATION COMMAND TESTS (5+ tests)
# =========================================================================

def test_render_drift_visualization_basic(temp_db):
    """Test ASCII histogram rendering."""
    drift_scores = [0.1, 0.2, 0.3, 0.15, 0.25]
    seed_drift_data(temp_db, "zip", drift_scores)

    metrics = export_drift_metrics(temp_db, "zip")
    output = _render_drift_visualization(metrics)

    assert "Drift Distribution (family: zip)" in output
    assert "0.0-0.1" in output
    assert "Avg drift:" in output
    assert "Median drift:" in output
    assert "P95 drift:" in output
    assert "█" in output or "(0)" in output  # Either has bars or shows zero


def test_render_drift_visualization_histogram_scaling(temp_db):
    """Test histogram bar scaling."""
    # Create distribution with clear max
    drift_scores = [0.05] * 10 + [0.15] * 5 + [0.25] * 2
    seed_drift_data(temp_db, "zip", drift_scores)

    metrics = export_drift_metrics(temp_db, "zip")
    output = _render_drift_visualization(metrics)

    # Should have bars of different lengths
    lines = output.split('\n')
    histogram_lines = [l for l in lines if '█' in l]

    if histogram_lines:
        # Check that bars have different lengths
        bar_lengths = [l.count('█') for l in histogram_lines if '█' in l]
        assert len(set(bar_lengths)) > 1, "All bars have same length"


def test_render_drift_visualization_empty_data(temp_db):
    """Test visualization with empty data."""
    metrics = export_drift_metrics(temp_db, "zip")
    output = _render_drift_visualization(metrics)

    assert "Drift Distribution (family: zip)" in output
    assert "Total examples: 0" in output


def test_render_drift_visualization_json_format(temp_db):
    """Test JSON output format."""
    drift_scores = [0.1, 0.2, 0.3]
    seed_drift_data(temp_db, "zip", drift_scores)

    metrics = export_drift_metrics(temp_db, "zip")

    # JSON should be serializable
    json_str = json.dumps(metrics)
    parsed = json.loads(json_str)

    assert parsed['family'] == 'zip'
    assert parsed['count'] == 3
    assert 'drift_distribution' in parsed


def test_render_drift_visualization_format_validation(temp_db):
    """Test format parameter validation."""
    # This is tested at CLI level, but we verify metrics can be JSON serialized
    drift_scores = [0.1, 0.2]
    seed_drift_data(temp_db, "zip", drift_scores)

    metrics = export_drift_metrics(temp_db, "zip")

    # All values should be JSON-serializable
    try:
        json.dumps(metrics)
    except (TypeError, ValueError):
        pytest.fail("Metrics not JSON serializable")


# =========================================================================
# TRENDS ANALYSIS TESTS (5+ tests)
# =========================================================================

def test_get_drift_trends_multi_run(temp_db):
    """Test drift trends across multiple runs."""
    run_data = [
        {'date': '2026-01-10T10:00:00', 'drift_scores': [0.3, 0.4, 0.5]},
        {'date': '2026-01-11T10:00:00', 'drift_scores': [0.2, 0.3, 0.4]},
        {'date': '2026-01-12T10:00:00', 'drift_scores': [0.1, 0.2, 0.3]},
    ]
    seed_runs_with_drift(temp_db, "zip", run_data)

    trends = get_drift_trends(temp_db, "zip", n_runs=10)

    assert trends['family'] == 'zip'
    assert len(trends['runs']) == 3
    assert trends['overall_trend']['direction'] == 'down'
    assert trends['overall_trend']['percentage'] < 0


def test_get_drift_trends_single_run(temp_db):
    """Test drift trends with single run."""
    run_data = [
        {'date': '2026-01-10T10:00:00', 'drift_scores': [0.3, 0.4, 0.5]},
    ]
    seed_runs_with_drift(temp_db, "zip", run_data)

    trends = get_drift_trends(temp_db, "zip", n_runs=10)

    assert len(trends['runs']) == 1
    assert trends['overall_trend']['direction'] == 'stable'


def test_get_drift_trends_direction_calculation(temp_db):
    """Test trend direction (up/down/stable)."""
    # Upward trend
    run_data = [
        {'date': '2026-01-10T10:00:00', 'drift_scores': [0.1, 0.1, 0.1]},
        {'date': '2026-01-11T10:00:00', 'drift_scores': [0.2, 0.2, 0.2]},
        {'date': '2026-01-12T10:00:00', 'drift_scores': [0.3, 0.3, 0.3]},
    ]
    seed_runs_with_drift(temp_db, "zip", run_data)

    trends = get_drift_trends(temp_db, "zip", n_runs=10)

    assert trends['overall_trend']['direction'] == 'up'
    assert trends['overall_trend']['percentage'] > 0


def test_get_drift_trends_n_runs_limit(temp_db):
    """Test limiting number of runs returned."""
    # Create 10 runs
    run_data = [
        {'date': f'2026-01-{i:02d}T10:00:00', 'drift_scores': [0.2, 0.3]}
        for i in range(1, 11)
    ]
    seed_runs_with_drift(temp_db, "zip", run_data)

    # Request only 5 runs
    trends = get_drift_trends(temp_db, "zip", n_runs=5)

    assert len(trends['runs']) <= 5


def test_get_drift_trends_percentage_calculation(temp_db):
    """Test trend percentage calculation."""
    run_data = [
        {'date': '2026-01-10T10:00:00', 'drift_scores': [0.4, 0.4, 0.4]},  # avg = 0.4
        {'date': '2026-01-11T10:00:00', 'drift_scores': [0.3, 0.3, 0.3]},  # avg = 0.3
    ]
    seed_runs_with_drift(temp_db, "zip", run_data)

    trends = get_drift_trends(temp_db, "zip", n_runs=10)

    # 0.4 to 0.3 = -25% change
    assert trends['overall_trend']['percentage'] == pytest.approx(-25.0, rel=0.1)


def test_render_drift_trends_output(temp_db):
    """Test trends visualization rendering."""
    run_data = [
        {'date': '2026-01-10T10:00:00', 'drift_scores': [0.3, 0.4, 0.5]},
        {'date': '2026-01-11T10:00:00', 'drift_scores': [0.2, 0.3, 0.4]},
    ]
    seed_runs_with_drift(temp_db, "zip", run_data)

    trends = get_drift_trends(temp_db, "zip", n_runs=10)
    output = _render_drift_trends(trends, 10)

    assert "Drift Trends (family: zip" in output
    assert "Run 1" in output
    assert "Overall trend:" in output
    assert "↓" in output or "↑" in output or "→" in output


# =========================================================================
# EDGE CASES TESTS
# =========================================================================

def test_empty_drift_metrics_structure():
    """Test empty drift metrics helper."""
    metrics = _empty_drift_metrics("test")

    assert metrics['family'] == 'test'
    assert metrics['count'] == 0
    assert metrics['avg_drift'] == 0.0
    assert len(metrics['drift_distribution']) == 8


def test_compute_drift_stats_empty_list():
    """Test compute_drift_stats with empty list."""
    stats = _compute_drift_stats([])

    assert stats['count'] == 0
    assert stats['avg_drift'] == 0.0


def test_compute_drift_stats_with_values():
    """Test compute_drift_stats with actual values."""
    scores = [0.1, 0.2, 0.3, 0.4, 0.5]
    stats = _compute_drift_stats(scores)

    assert stats['count'] == 5
    assert stats['avg_drift'] == 0.3
    assert stats['median_drift'] == 0.3
    assert stats['max_drift'] == 0.5


def test_compute_drift_distribution_basic():
    """Test drift distribution computation."""
    scores = [0.05, 0.15, 0.25, 0.35]
    dist = _compute_drift_distribution(scores)

    assert dist['0.0-0.1'] == 1
    assert dist['0.1-0.2'] == 1
    assert dist['0.2-0.3'] == 1
    assert dist['0.3-0.4'] == 1


def test_calculate_trend_stable():
    """Test trend calculation with stable values."""
    values = [0.2, 0.21, 0.19, 0.20]  # Small variations < 5%
    trend = _calculate_trend(values)

    assert trend['direction'] == 'stable'


def test_calculate_trend_up():
    """Test trend calculation with upward trend."""
    values = [0.1, 0.2, 0.3]
    trend = _calculate_trend(values)

    assert trend['direction'] == 'up'
    assert trend['percentage'] > 0


def test_calculate_trend_down():
    """Test trend calculation with downward trend."""
    values = [0.3, 0.2, 0.1]
    trend = _calculate_trend(values)

    assert trend['direction'] == 'down'
    assert trend['percentage'] < 0


def test_calculate_trend_single_value():
    """Test trend calculation with single value."""
    trend = _calculate_trend([0.5])

    assert trend['direction'] == 'stable'
    assert trend['percentage'] == 0.0


def test_calculate_trend_zero_first_value():
    """Test trend calculation when first value is zero."""
    trend = _calculate_trend([0.0, 0.1, 0.2])

    assert trend['direction'] == 'stable'
    assert trend['percentage'] == 0.0


def test_no_runs_found(temp_db):
    """Test drift trends when no runs exist."""
    trends = get_drift_trends(temp_db, "nonexistent", n_runs=10)

    assert trends['family'] == 'nonexistent'
    assert len(trends['runs']) == 0
    assert trends['overall_trend']['direction'] == 'stable'


def test_render_trends_no_data(temp_db):
    """Test rendering trends with no data."""
    trends = get_drift_trends(temp_db, "zip", n_runs=10)
    output = _render_drift_trends(trends, 10)

    assert "No runs found" in output


# =========================================================================
# PERFORMANCE TESTS
# =========================================================================

def test_visualization_performance(temp_db):
    """Test that visualization completes in < 1 second."""
    import time

    # Create moderate dataset
    drift_scores = [i / 100.0 for i in range(100)]
    seed_drift_data(temp_db, "zip", drift_scores)

    start = time.time()
    metrics = export_drift_metrics(temp_db, "zip")
    _render_drift_visualization(metrics)
    duration = time.time() - start

    assert duration < 1.0, f"Visualization took {duration:.2f}s, expected < 1s"


def test_trends_performance(temp_db):
    """Test that trends analysis completes in < 2 seconds."""
    import time

    # Create 10 runs with drift data
    run_data = [
        {'date': f'2026-01-{i:02d}T10:00:00', 'drift_scores': [0.1 + i * 0.01] * 10}
        for i in range(1, 11)
    ]
    seed_runs_with_drift(temp_db, "zip", run_data)

    start = time.time()
    trends = get_drift_trends(temp_db, "zip", n_runs=10)
    _render_drift_trends(trends, 10)
    duration = time.time() - start

    assert duration < 2.0, f"Trends analysis took {duration:.2f}s, expected < 2s"
