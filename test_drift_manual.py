"""
Manual test runner for drift reporting (without pytest dependency).
"""

import sys
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

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
from src.core.models import ExampleRecord, ExampleStatus, SourceType, Location


def seed_drift_data(db: Database, family: str, drift_scores: list) -> None:
    """Seed database with example records containing drift scores."""
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


def seed_runs_with_drift(db: Database, family: str, run_data: list) -> None:
    """Seed database with runs and drift data."""
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


def run_tests():
    """Run all tests."""
    passed = 0
    failed = 0

    print("=" * 80)
    print("DRIFT REPORTING TESTS")
    print("=" * 80)
    print()

    # Test 1: Basic drift metrics export
    try:
        tmpdir = tempfile.mkdtemp()
        db_path = Path(tmpdir) / "test.db"
        db = Database(db_path)
        db.initialize_schema()

        drift_scores = [0.1, 0.2, 0.3, 0.15, 0.25]
        seed_drift_data(db, "zip", drift_scores)

        metrics = export_drift_metrics(db, "zip")

        assert metrics['family'] == 'zip'
        assert metrics['count'] == 5
        assert 0.15 <= metrics['avg_drift'] <= 0.25
        assert metrics['median_drift'] == 0.2
        assert metrics['max_drift'] == 0.3

        print("[PASS] test_export_drift_metrics_basic")
        passed += 1

        shutil.rmtree(tmpdir)
    except Exception as e:
        print(f"[FAIL] test_export_drift_metrics_basic: {e}")
        failed += 1

    # Test 2: Empty dataset
    try:
        tmpdir = tempfile.mkdtemp()
        db_path = Path(tmpdir) / "test.db"
        db = Database(db_path)
        db.initialize_schema()

        metrics = export_drift_metrics(db, "nonexistent")

        assert metrics['family'] == 'nonexistent'
        assert metrics['count'] == 0
        assert metrics['avg_drift'] == 0.0

        print("[PASS] test_export_drift_metrics_empty_dataset")
        passed += 1

        shutil.rmtree(tmpdir)
    except Exception as e:
        print(f"[FAIL] test_export_drift_metrics_empty_dataset: {e}")
        failed += 1

    # Test 3: Distribution buckets
    try:
        tmpdir = tempfile.mkdtemp()
        db_path = Path(tmpdir) / "test.db"
        db = Database(db_path)
        db.initialize_schema()

        drift_scores = [0.05, 0.05, 0.05, 0.15, 0.15, 0.25, 0.35]
        seed_drift_data(db, "zip", drift_scores)

        metrics = export_drift_metrics(db, "zip")
        dist = metrics['drift_distribution']

        assert dist['0.0-0.1'] == 3
        assert dist['0.1-0.2'] == 2
        assert dist['0.2-0.3'] == 1
        assert dist['0.3-0.4'] == 1

        print("[PASS] test_export_drift_metrics_distribution_buckets")
        passed += 1

        shutil.rmtree(tmpdir)
    except Exception as e:
        print(f"[FAIL] test_export_drift_metrics_distribution_buckets: {e}")
        failed += 1

    # Test 4: Render visualization
    try:
        tmpdir = tempfile.mkdtemp()
        db_path = Path(tmpdir) / "test.db"
        db = Database(db_path)
        db.initialize_schema()

        drift_scores = [0.1, 0.2, 0.3, 0.15, 0.25]
        seed_drift_data(db, "zip", drift_scores)

        metrics = export_drift_metrics(db, "zip")
        output = _render_drift_visualization(metrics)

        assert "Drift Distribution (family: zip)" in output
        assert "Avg drift:" in output
        assert "Median drift:" in output

        print("[PASS] test_render_drift_visualization")
        print()
        print("Sample output:")
        print(output)
        print()
        passed += 1

        shutil.rmtree(tmpdir)
    except Exception as e:
        print(f"[FAIL] test_render_drift_visualization: {e}")
        failed += 1

    # Test 5: Drift trends
    try:
        tmpdir = tempfile.mkdtemp()
        db_path = Path(tmpdir) / "test.db"
        db = Database(db_path)
        db.initialize_schema()

        run_data = [
            {'date': '2026-01-10T10:00:00', 'drift_scores': [0.3, 0.4, 0.5]},
            {'date': '2026-01-11T10:00:00', 'drift_scores': [0.2, 0.3, 0.4]},
            {'date': '2026-01-12T10:00:00', 'drift_scores': [0.1, 0.2, 0.3]},
        ]
        seed_runs_with_drift(db, "zip", run_data)

        trends = get_drift_trends(db, "zip", n_runs=10)

        assert trends['family'] == 'zip'
        assert len(trends['runs']) == 3
        assert trends['overall_trend']['direction'] == 'down'

        print("[PASS] test_get_drift_trends_multi_run")
        passed += 1

        shutil.rmtree(tmpdir)
    except Exception as e:
        print(f"[FAIL] test_get_drift_trends_multi_run: {e}")
        failed += 1

    # Test 6: Render trends
    try:
        tmpdir = tempfile.mkdtemp()
        db_path = Path(tmpdir) / "test.db"
        db = Database(db_path)
        db.initialize_schema()

        run_data = [
            {'date': '2026-01-10T10:00:00', 'drift_scores': [0.3, 0.4, 0.5]},
            {'date': '2026-01-11T10:00:00', 'drift_scores': [0.2, 0.3, 0.4]},
            {'date': '2026-01-12T10:00:00', 'drift_scores': [0.1, 0.2, 0.3]},
        ]
        seed_runs_with_drift(db, "zip", run_data)

        trends = get_drift_trends(db, "zip", n_runs=10)
        output = _render_drift_trends(trends, 10)

        assert "Drift Trends" in output
        assert "Overall trend:" in output

        print("[PASS] test_render_drift_trends")
        print()
        print("Sample output:")
        print(output)
        print()
        passed += 1

        shutil.rmtree(tmpdir)
    except Exception as e:
        print(f"[FAIL] test_render_drift_trends: {e}")
        failed += 1

    # Test 7: Helper functions
    try:
        # Test _compute_drift_stats
        scores = [0.1, 0.2, 0.3, 0.4, 0.5]
        stats = _compute_drift_stats(scores)
        assert stats['count'] == 5
        assert stats['avg_drift'] == 0.3
        assert stats['median_drift'] == 0.3

        # Test _compute_drift_distribution
        dist = _compute_drift_distribution(scores)
        assert isinstance(dist, dict)
        assert len(dist) == 8

        # Test _calculate_trend
        trend_down = _calculate_trend([0.3, 0.2, 0.1])
        assert trend_down['direction'] == 'down'

        trend_up = _calculate_trend([0.1, 0.2, 0.3])
        assert trend_up['direction'] == 'up'

        # Test _empty_drift_metrics
        empty = _empty_drift_metrics("test")
        assert empty['count'] == 0
        assert empty['family'] == 'test'

        print("[PASS] test_helper_functions")
        passed += 1
    except Exception as e:
        print(f"[FAIL] test_helper_functions: {e}")
        failed += 1

    # Test 8: JSON serialization
    try:
        tmpdir = tempfile.mkdtemp()
        db_path = Path(tmpdir) / "test.db"
        db = Database(db_path)
        db.initialize_schema()

        drift_scores = [0.1, 0.2, 0.3]
        seed_drift_data(db, "zip", drift_scores)

        metrics = export_drift_metrics(db, "zip")
        json_str = json.dumps(metrics)
        parsed = json.loads(json_str)

        assert parsed['family'] == 'zip'
        assert parsed['count'] == 3

        print("[PASS] test_json_serialization")
        passed += 1

        shutil.rmtree(tmpdir)
    except Exception as e:
        print(f"[FAIL] test_json_serialization: {e}")
        failed += 1

    # Summary
    print()
    print("=" * 80)
    print(f"TEST SUMMARY: {passed} passed, {failed} failed")
    print("=" * 80)

    return failed == 0


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
