"""
Tests for runtime reprocessing functionality.

Validates that RUNTIME_FAILED examples are included in re-processing
when new patterns are available, allowing learned patterns to fix
runtime-specific issues.
"""

import pytest
from pathlib import Path
from src.core.database import Database
from src.core.models import ExampleStatus, ExampleRecord, Location


class TestRuntimeReprocessing:
    """Test runtime failure re-processing logic."""

    def _create_example(self, family: str, key: str, status: ExampleStatus) -> ExampleRecord:
        """Helper to create test example."""
        return ExampleRecord(
            family=family,
            example_key=key,
            file_path=f"/test/{key}.md",
            original_code="// test",
            status=status,
            location=Location(start_line=1, end_line=10)
        )

    def test_runtime_failed_included_in_query(self, temp_db):
        """get_examples_with_applicable_patterns should include RUNTIME_FAILED examples."""
        db = Database(temp_db)
        db.initialize_schema()

        # Create a run
        run_id = db.create_run(family="test_family", current_phase="test")

        # Create examples with different statuses
        examples_data = [
            ("ex1", ExampleStatus.DISCOVERED),
            ("ex2", ExampleStatus.COMPILE_FAILED),
            ("ex3", ExampleStatus.RUNTIME_FAILED),
            ("ex4", ExampleStatus.FINAL_REVIEW_PASSED),
        ]

        for key, status in examples_data:
            example = self._create_example("test_family", key, status)
            db.save_example(example, run_id=run_id)

        # Query with all 3 statuses (as orchestrator now does)
        examples = db.get_examples_with_applicable_patterns(
            family="test_family",
            status=[ExampleStatus.DISCOVERED, ExampleStatus.COMPILE_FAILED, ExampleStatus.RUNTIME_FAILED],
            run_id=run_id
        )

        # Should return 3 examples (ex1, ex2, ex3)
        assert len(examples) == 3

        # Verify statuses
        statuses = {ex.status for ex in examples}
        assert ExampleStatus.DISCOVERED in statuses
        assert ExampleStatus.COMPILE_FAILED in statuses
        assert ExampleStatus.RUNTIME_FAILED in statuses
        assert ExampleStatus.FINAL_REVIEW_PASSED not in statuses

    def test_runtime_failed_excluded_without_status_filter(self, temp_db):
        """Query should respect status filter - don't include RUNTIME_FAILED if not in list."""
        db = Database(temp_db)
        db.initialize_schema()

        run_id = db.create_run(family="test_family", current_phase="test")

        # Create RUNTIME_FAILED example
        example = self._create_example("test_family", "ex_runtime_fail", ExampleStatus.RUNTIME_FAILED)
        db.save_example(example, run_id=run_id)

        # Query with only DISCOVERED and COMPILE_FAILED (old behavior)
        examples = db.get_examples_with_applicable_patterns(
            family="test_family",
            status=[ExampleStatus.DISCOVERED, ExampleStatus.COMPILE_FAILED],
            run_id=run_id
        )

        # Should NOT include the RUNTIME_FAILED example
        assert len(examples) == 0

    def test_status_breakdown_calculation(self, temp_db):
        """Verify status breakdown logic works correctly."""
        db = Database(temp_db)
        db.initialize_schema()

        run_id = db.create_run(family="test_family", current_phase="test")

        # Create multiple examples with different statuses
        status_counts = {
            ExampleStatus.DISCOVERED: 5,
            ExampleStatus.COMPILE_FAILED: 3,
            ExampleStatus.RUNTIME_FAILED: 2,
        }

        for status, count in status_counts.items():
            for i in range(count):
                example = self._create_example("test_family", f"{status.value}_{i}", status)
                db.save_example(example, run_id=run_id)

        # Query all statuses
        examples = db.get_examples_with_applicable_patterns(
            family="test_family",
            status=[ExampleStatus.DISCOVERED, ExampleStatus.COMPILE_FAILED, ExampleStatus.RUNTIME_FAILED],
            run_id=run_id
        )

        # Calculate breakdown (mimics orchestrator logic)
        status_breakdown = {}
        for ex in examples:
            status = ex.status
            status_breakdown[status.value] = status_breakdown.get(status.value, 0) + 1

        # Verify counts
        assert len(examples) == 10  # 5 + 3 + 2
        assert status_breakdown["DISCOVERED"] == 5
        assert status_breakdown["COMPILE_FAILED"] == 3
        assert status_breakdown["RUNTIME_FAILED"] == 2

    def test_max_examples_limit_respected(self, temp_db):
        """Verify max_examples limit is respected when including RUNTIME_FAILED."""
        db = Database(temp_db)
        db.initialize_schema()

        run_id = db.create_run(family="test_family", current_phase="test")

        # Create 20 examples across different statuses
        for i in range(20):
            status = [
                ExampleStatus.DISCOVERED,
                ExampleStatus.COMPILE_FAILED,
                ExampleStatus.RUNTIME_FAILED
            ][i % 3]

            example = self._create_example("test_family", f"ex_{i}", status)
            db.save_example(example, run_id=run_id)

        # Query with max_examples=5
        examples = db.get_examples_with_applicable_patterns(
            family="test_family",
            status=[ExampleStatus.DISCOVERED, ExampleStatus.COMPILE_FAILED, ExampleStatus.RUNTIME_FAILED],
            max_examples=5,
            run_id=run_id
        )

        # Should return exactly 5 examples
        assert len(examples) == 5

    def test_no_examples_when_run_id_missing(self, temp_db):
        """Query should return empty list when run_id not provided."""
        db = Database(temp_db)
        db.initialize_schema()

        # Query without run_id
        examples = db.get_examples_with_applicable_patterns(
            family="test_family",
            status=[ExampleStatus.DISCOVERED, ExampleStatus.COMPILE_FAILED, ExampleStatus.RUNTIME_FAILED],
            run_id=None
        )

        # Should return empty list (per database.py line 1024)
        assert len(examples) == 0
