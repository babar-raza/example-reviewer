"""
Tests for Phase Timing functionality in telemetry module.
"""

import json
import pytest
import time
import tempfile
from pathlib import Path
from datetime import datetime

from src.core.telemetry import track_phase_timing, export_run_telemetry
from src.core.database import Database
from src.core.models import TelemetryEvent


@pytest.fixture
def temp_db():
    """Create a temporary database for tests."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    db = Database(db_path)
    db.initialize_schema()

    yield db

    # Cleanup
    db.close()
    if db_path.exists():
        db_path.unlink()


class TestPhaseTimingContextManager:
    """Tests for track_phase_timing context manager."""

    def test_records_phase_timing_on_success(self, temp_db):
        """Test that phase timing is recorded on successful execution."""
        run_id = "test_run_001"
        family = "zip"
        phase = "compilation"

        # Execute with timing
        with track_phase_timing(temp_db, run_id, family, phase):
            time.sleep(0.01)  # Simulate work

        # Verify event was recorded
        with temp_db.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM telemetry_events WHERE run_id = ? AND phase = ?",
                (run_id, phase)
            ).fetchall()

            assert len(rows) == 1
            event = rows[0]

            assert event['run_id'] == run_id
            assert event['family'] == family
            assert event['event_type'] == 'phase_timing'
            assert event['phase'] == phase
            assert event['success'] == 1
            assert event['duration_ms'] >= 10  # At least 10ms
            assert event['timestamp'] is not None

    def test_records_phase_timing_on_failure(self, temp_db):
        """Test that phase timing is recorded even when exception occurs."""
        run_id = "test_run_002"
        family = "zip"
        phase = "runtime"

        # Execute with exception
        with pytest.raises(ValueError):
            with track_phase_timing(temp_db, run_id, family, phase):
                time.sleep(0.01)
                raise ValueError("Test error")

        # Verify event was recorded with success=False
        with temp_db.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM telemetry_events WHERE run_id = ? AND phase = ?",
                (run_id, phase)
            ).fetchall()

            assert len(rows) == 1
            event = rows[0]

            assert event['run_id'] == run_id
            assert event['success'] == 0  # Failed
            assert event['duration_ms'] >= 10
            # Metadata should contain error info
            import json
            metadata = json.loads(event['metadata'])
            assert 'error' in metadata
            assert 'Test error' in metadata['error']

    def test_includes_custom_metadata(self, temp_db):
        """Test that custom metadata is included in telemetry event."""
        run_id = "test_run_003"
        family = "zip"
        phase = "discovery"
        custom_metadata = {
            'files_found': 42,
            'examples_extracted': 128,
        }

        with track_phase_timing(temp_db, run_id, family, phase, metadata=custom_metadata):
            pass

        # Verify metadata was saved
        with temp_db.get_connection() as conn:
            row = conn.execute(
                "SELECT metadata FROM telemetry_events WHERE run_id = ? AND phase = ?",
                (run_id, phase)
            ).fetchone()

            import json
            metadata = json.loads(row['metadata'])
            assert metadata['files_found'] == 42
            assert metadata['examples_extracted'] == 128

    def test_gracefully_handles_db_errors(self, temp_db):
        """Test that telemetry errors don't break the pipeline."""
        # Close the database to simulate failure
        temp_db.close()

        run_id = "test_run_004"
        family = "zip"
        phase = "compilation"

        # Should not raise exception even though DB is closed
        try:
            with track_phase_timing(temp_db, run_id, family, phase):
                pass
        except Exception as e:
            pytest.fail(f"track_phase_timing raised exception: {e}")

    def test_multiple_phases_tracked_independently(self, temp_db):
        """Test that multiple phases are tracked with separate events."""
        run_id = "test_run_005"
        family = "zip"

        phases = ["discovery", "compilation", "runtime", "final_review"]

        for phase in phases:
            with track_phase_timing(temp_db, run_id, family, phase):
                time.sleep(0.005)

        # Verify all phases recorded
        with temp_db.get_connection() as conn:
            rows = conn.execute(
                "SELECT phase, duration_ms FROM telemetry_events WHERE run_id = ? ORDER BY timestamp",
                (run_id,)
            ).fetchall()

            assert len(rows) == 4
            recorded_phases = [row['phase'] for row in rows]
            assert recorded_phases == phases

            # All should have positive duration
            for row in rows:
                assert row['duration_ms'] > 0

    def test_timing_accuracy(self, temp_db):
        """Test that timing measurements are reasonably accurate."""
        run_id = "test_run_006"
        family = "zip"
        phase = "test_phase"

        sleep_duration = 0.1  # 100ms

        with track_phase_timing(temp_db, run_id, family, phase):
            time.sleep(sleep_duration)

        # Verify duration is approximately correct (within 50ms tolerance)
        with temp_db.get_connection() as conn:
            row = conn.execute(
                "SELECT duration_ms FROM telemetry_events WHERE run_id = ? AND phase = ?",
                (run_id, phase)
            ).fetchone()

            duration_ms = row['duration_ms']
            expected_ms = sleep_duration * 1000

            # Allow 50ms tolerance for timing variations
            assert abs(duration_ms - expected_ms) < 50

    def test_event_id_generation(self, temp_db):
        """Test that event_id is generated automatically."""
        run_id = "test_run_007"
        family = "zip"
        phase = "compilation"

        with track_phase_timing(temp_db, run_id, family, phase):
            pass

        # Verify event_id was generated
        with temp_db.get_connection() as conn:
            row = conn.execute(
                "SELECT event_id FROM telemetry_events WHERE run_id = ? AND phase = ?",
                (run_id, phase)
            ).fetchone()

            assert row['event_id'] is not None
            assert len(row['event_id']) > 0

    def test_supports_multi_family_tracking(self, temp_db):
        """Test tracking across multiple families."""
        run_id = "test_run_008"
        families = ["zip", "cells", "pdf"]
        phase = "compilation"

        for family in families:
            with track_phase_timing(temp_db, run_id, family, phase):
                time.sleep(0.005)

        # Verify events for all families
        with temp_db.get_connection() as conn:
            rows = conn.execute(
                "SELECT family FROM telemetry_events WHERE run_id = ? ORDER BY timestamp",
                (run_id,)
            ).fetchall()

            recorded_families = [row['family'] for row in rows]
            assert recorded_families == families


class TestTelemetryAggregation:
    """Tests for telemetry aggregation queries."""

    def test_get_phase_timings(self, temp_db):
        """Test retrieving phase timings for a run."""
        run_id = "test_run_agg_001"
        family = "zip"

        # Create some phase events
        phases = ["discovery", "compilation", "runtime"]
        for phase in phases:
            with track_phase_timing(temp_db, run_id, family, phase):
                time.sleep(0.01)

        # Get phase timings
        timings = temp_db.get_phase_timings(run_id)

        assert len(timings) == 3
        for i, timing in enumerate(timings):
            assert timing['phase'] == phases[i]
            assert timing['duration_ms'] > 0
            assert timing['success'] is True
            assert 'timestamp' in timing
            assert isinstance(timing['metadata'], dict)

    def test_get_phase_timings_empty_run(self, temp_db):
        """Test getting phase timings for non-existent run."""
        timings = temp_db.get_phase_timings("nonexistent_run")
        assert len(timings) == 0

    def test_get_attempt_counts_empty_run(self, temp_db):
        """Test getting attempt counts for a run with no attempts."""
        # Create run record
        run_id = temp_db.create_run("zip", "test")

        counts = temp_db.get_attempt_counts(run_id)

        assert counts['compilation']['total_attempts'] == 0
        assert counts['compilation']['successful'] == 0
        assert counts['runtime']['total_attempts'] == 0

    def test_get_failure_breakdown(self, temp_db):
        """Test getting failure breakdown for a family."""
        from src.core.models import ExampleRecord, ExampleStatus, SourceType, Location

        # Create some failed examples
        for i in range(3):
            example = ExampleRecord(
                example_id=f"fail_test_{i}",
                family="zip",
                file_path="test.md",
                source_type=SourceType.INLINE,
                language="csharp",
                location=Location(block_index=0, start_line=1, end_line=2),
                original_code="code",
                status=ExampleStatus.COMPILE_FAILED,
                failure_reason=f"Error {i}",
            )
            temp_db.save_example(example)

        breakdown = temp_db.get_failure_breakdown("zip")

        assert breakdown['total_failures'] >= 3
        assert 'COMPILE_FAILED' in breakdown['failure_counts']
        assert len(breakdown['failure_samples']['COMPILE_FAILED']) <= 5


class TestTelemetryExport:
    """Tests for telemetry export functionality."""

    def test_export_run_telemetry_creates_files(self, temp_db):
        """Test that export creates expected JSON files."""
        run_id = temp_db.create_run("zip", "test")
        family = "zip"

        # Create some phase events
        with track_phase_timing(temp_db, run_id, family, "compilation"):
            time.sleep(0.01)

        with track_phase_timing(temp_db, run_id, family, "runtime"):
            time.sleep(0.01)

        # Complete run
        temp_db.complete_run(
            run_id,
            status='completed',
            examples_processed=10,
            examples_verified=8,
        )

        # Export telemetry
        with tempfile.TemporaryDirectory() as tmpdir:
            exported = export_run_telemetry(temp_db, run_id, tmpdir)

            assert 'run_summary' in exported
            assert 'phase_events' in exported

            # Verify files exist
            summary_path = Path(exported['run_summary'])
            assert summary_path.exists()

            phase_events_path = Path(exported['phase_events'])
            assert phase_events_path.exists()

            # Verify summary content
            summary = json.loads(summary_path.read_text())
            assert summary['run_id'] == run_id
            assert summary['family'] == family
            assert summary['status'] == 'completed'
            assert summary['examples_processed'] == 10
            assert 'phase_summary' in summary
            assert 'compilation' in summary['phase_summary']
            assert 'runtime' in summary['phase_summary']

            # Verify phase events content
            events = json.loads(phase_events_path.read_text())
            assert len(events) == 2
            assert events[0]['phase'] == 'compilation'
            assert events[1]['phase'] == 'runtime'

    def test_export_includes_errors_on_failure(self, temp_db):
        """Test that errors.json is created when phases fail."""
        run_id = temp_db.create_run("zip", "test")
        family = "zip"

        # Create successful phase
        with track_phase_timing(temp_db, run_id, family, "discovery"):
            pass

        # Create failed phase
        try:
            with track_phase_timing(temp_db, run_id, family, "compilation"):
                raise ValueError("Compilation error")
        except ValueError:
            pass

        temp_db.complete_run(run_id, status='failed', error="Compilation error")

        # Export telemetry
        with tempfile.TemporaryDirectory() as tmpdir:
            exported = export_run_telemetry(temp_db, run_id, tmpdir)

            # Should have errors file
            assert 'errors' in exported

            errors_path = Path(exported['errors'])
            assert errors_path.exists()

            errors = json.loads(errors_path.read_text())
            assert len(errors) >= 1
            assert errors[0]['phase'] == 'compilation'
            assert 'Compilation error' in errors[0]['error']

    def test_export_handles_missing_run(self, temp_db):
        """Test export gracefully handles non-existent run."""
        with tempfile.TemporaryDirectory() as tmpdir:
            exported = export_run_telemetry(temp_db, "nonexistent_run", tmpdir)
            assert exported == {}

    def test_export_creates_run_directory(self, temp_db):
        """Test that export creates run-specific directory."""
        run_id = temp_db.create_run("zip", "test")

        with track_phase_timing(temp_db, run_id, "zip", "discovery"):
            pass

        temp_db.complete_run(run_id, status='completed')

        with tempfile.TemporaryDirectory() as tmpdir:
            export_run_telemetry(temp_db, run_id, tmpdir)

            run_dir = Path(tmpdir) / run_id
            assert run_dir.exists()
            assert run_dir.is_dir()

    def test_export_doesnt_fail_pipeline_on_error(self, temp_db):
        """Test that export errors are caught gracefully."""
        run_id = temp_db.create_run("zip", "test")
        temp_db.complete_run(run_id, status='completed')

        # Invalid output directory (permission issue)
        try:
            exported = export_run_telemetry(temp_db, run_id, "/invalid/path/that/doesnt/exist")
            assert exported == {}  # Should return empty dict on failure
        except Exception as e:
            pytest.fail(f"Export should not raise exception: {e}")
