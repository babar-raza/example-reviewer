"""
Tests for run-scoped KPI queries.
Ensures KPIs are calculated correctly from example_run_state table.
"""

import pytest
from pathlib import Path
from datetime import datetime
from src.core.database import Database
from src.core.models import ExampleStatus, FailureCategory, FailureResolution


class TestRunScopedKPIs:
    """Test run-scoped KPI calculations."""

    def test_kpis_use_run_state_table(self, temp_db):
        """Test that KPIs query from example_run_state not example_records."""
        db = Database(temp_db)
        db.initialize_schema()

        # Create test run
        run_id = db.create_run("zip", "test_run")

        # Create example record (canonical)
        example_id = "test_example_001"
        with db.get_connection() as conn:
            conn.execute("""
                INSERT INTO example_records (
                    example_id, family, file_path, source_type, language,
                    original_code, created_at, updated_at, example_key
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                example_id, "zip", "test.md", "inline", "csharp",
                "test code", datetime.utcnow().isoformat(),
                datetime.utcnow().isoformat(), "test_key"
            ))

        # Create run state (per-run)
        db.save_example_run_state(
            run_id=run_id,
            example_id=example_id,
            status=ExampleStatus.VERIFIED,
        )

        # Get KPIs for this run
        kpis = db.get_runtime_kpis(run_id=run_id, family="zip")

        # Should find verified example from run state
        assert kpis['verified_count'] == 1

    def test_kpis_isolated_by_run(self, temp_db):
        """Test that KPIs are isolated by run_id."""
        db = Database(temp_db)
        db.initialize_schema()

        # Create two runs
        run_id_1 = db.create_run("zip", "test_run_1")
        run_id_2 = db.create_run("zip", "test_run_2")

        # Create example record
        example_id = "test_example_002"
        with db.get_connection() as conn:
            conn.execute("""
                INSERT INTO example_records (
                    example_id, family, file_path, source_type, language,
                    original_code, created_at, updated_at, example_key
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                example_id, "zip", "test.md", "inline", "csharp",
                "test code", datetime.utcnow().isoformat(),
                datetime.utcnow().isoformat(), "test_key"
            ))

        # Run 1: Example verified
        db.save_example_run_state(
            run_id=run_id_1,
            example_id=example_id,
            status=ExampleStatus.VERIFIED,
        )

        # Run 2: Example failed
        db.save_example_run_state(
            run_id=run_id_2,
            example_id=example_id,
            status=ExampleStatus.RUNTIME_FAILED,
            failure_reason="Test failure",
        )

        # Get KPIs for run 1
        kpis_1 = db.get_runtime_kpis(run_id=run_id_1, family="zip")
        assert kpis_1['verified_count'] == 1

        # Get KPIs for run 2
        kpis_2 = db.get_runtime_kpis(run_id=run_id_2, family="zip")
        assert kpis_2['verified_count'] == 0

    def test_run_state_status_counts(self, temp_db):
        """Test counting run states by status."""
        db = Database(temp_db)
        db.initialize_schema()

        # Create run
        run_id = db.create_run("zip", "test_run")

        # Create example records and run states
        statuses = [
            ExampleStatus.VERIFIED,
            ExampleStatus.VERIFIED,
            ExampleStatus.COMPILE_FAILED,
            ExampleStatus.RUNTIME_FAILED,
        ]

        for i, status in enumerate(statuses):
            example_id = f"test_example_{i:03d}"

            # Create example record
            with db.get_connection() as conn:
                conn.execute("""
                    INSERT INTO example_records (
                        example_id, family, file_path, source_type, language,
                        original_code, created_at, updated_at, example_key
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    example_id, "zip", f"test_{i}.md", "inline", "csharp",
                    "test code", datetime.utcnow().isoformat(),
                    datetime.utcnow().isoformat(), f"test_key_{i}"
                ))

            # Create run state
            db.save_example_run_state(
                run_id=run_id,
                example_id=example_id,
                status=status,
            )

        # Count by status
        counts = db.count_run_states_by_status(run_id=run_id, family="zip")

        assert counts['VERIFIED'] == 2
        assert counts['COMPILE_FAILED'] == 1
        assert counts['RUNTIME_FAILED'] == 1

    def test_get_run_states_by_status(self, temp_db):
        """Test getting run states filtered by status."""
        db = Database(temp_db)
        db.initialize_schema()

        # Create run
        run_id = db.create_run("zip", "test_run")

        # Create examples with different statuses
        for i in range(3):
            example_id = f"verified_example_{i}"

            with db.get_connection() as conn:
                conn.execute("""
                    INSERT INTO example_records (
                        example_id, family, file_path, source_type, language,
                        original_code, created_at, updated_at, example_key
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    example_id, "zip", f"verified_{i}.md", "inline", "csharp",
                    "test code", datetime.utcnow().isoformat(),
                    datetime.utcnow().isoformat(), f"verified_key_{i}"
                ))

            db.save_example_run_state(
                run_id=run_id,
                example_id=example_id,
                status=ExampleStatus.VERIFIED,
            )

        # Get verified states
        verified_states = db.get_run_states_by_status(
            run_id=run_id,
            status=ExampleStatus.VERIFIED,
            family="zip"
        )

        assert len(verified_states) == 3
        for state in verified_states:
            assert state['status'] == 'VERIFIED'
            assert state['family'] == 'zip'


class TestRunStateUpdates:
    """Test run state update methods."""

    def test_update_run_state_status(self, temp_db):
        """Test updating run state status.

        TC-EPIC2-02: was update_example_run_state_status() -- a second,
        structurally identical, zero-caller raw status writer, deleted as
        dead code (FINDINGS_REGISTER.md). update_example_status() is the one
        sanctioned low-level writer this test now exercises directly."""
        db = Database(temp_db)
        db.initialize_schema()

        run_id = db.create_run("zip", "test")
        example_id = "test_001"

        # Create example and initial state
        with db.get_connection() as conn:
            conn.execute("""
                INSERT INTO example_records (
                    example_id, family, file_path, source_type, language,
                    original_code, created_at, updated_at, example_key
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                example_id, "zip", "test.md", "inline", "csharp",
                "code", datetime.utcnow().isoformat(),
                datetime.utcnow().isoformat(), "key"
            ))

        db.save_example_run_state(
            run_id=run_id,
            example_id=example_id,
            status=ExampleStatus.DISCOVERED,
        )

        # Update status
        success = db.update_example_status(
            example_id=example_id,
            status=ExampleStatus.VERIFIED,
            run_id=run_id,
        )

        assert success is True

        # Verify update
        state = db.get_example_run_state(run_id, example_id)
        assert state['status'] == 'VERIFIED'

    def test_update_run_state_code(self, temp_db):
        """Test updating run state code fields."""
        db = Database(temp_db)
        db.initialize_schema()

        run_id = db.create_run("zip", "test")
        example_id = "test_002"

        # Create example and initial state
        with db.get_connection() as conn:
            conn.execute("""
                INSERT INTO example_records (
                    example_id, family, file_path, source_type, language,
                    original_code, created_at, updated_at, example_key
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                example_id, "zip", "test.md", "inline", "csharp",
                "original", datetime.utcnow().isoformat(),
                datetime.utcnow().isoformat(), "key"
            ))

        db.save_example_run_state(
            run_id=run_id,
            example_id=example_id,
            status=ExampleStatus.DISCOVERED,
        )

        # Update code
        success = db.update_example_run_state_code(
            run_id=run_id,
            example_id=example_id,
            compilable_code="fixed code",
            verified_code="verified code",
        )

        assert success is True

        # Verify update
        state = db.get_example_run_state(run_id, example_id)
        assert state['compilable_code'] == "fixed code"
        assert state['verified_code'] == "verified code"
