"""
Test SQLite locking behavior and concurrent access.

Task 3: Deterministic concurrency repro test to prevent regression.
"""

import sqlite3
import tempfile
import threading
import time
from datetime import datetime
from pathlib import Path

import pytest

from src.core.database import Database
from src.core.models import ExampleRecord, ExampleStatus, SourceType, Location


class TestSQLiteLocking:
    """Test SQLite locking behavior under concurrent access."""

    def test_wal_mode_applied(self, tmp_path):
        """
        Test 3B: Verify WAL mode is applied.

        Ensures that the database is configured with WAL mode for concurrent access.
        """
        db_path = tmp_path / "test.db"
        db = Database(db_path=db_path, wal_enabled=True)
        db.initialize_schema()

        # Query journal mode
        with db.get_connection() as conn:
            result = conn.execute("PRAGMA journal_mode").fetchone()
            journal_mode = result[0].lower() if result else None

        assert journal_mode == "wal", f"Expected WAL mode, got {journal_mode}"

    def test_wal_mode_can_be_disabled(self, tmp_path):
        """Test that WAL mode can be disabled if needed."""
        db_path = tmp_path / "test.db"
        db = Database(db_path=db_path, wal_enabled=False)
        db.initialize_schema()

        # Query journal mode (should not be WAL)
        with db.get_connection() as conn:
            result = conn.execute("PRAGMA journal_mode").fetchone()
            journal_mode = result[0].lower() if result else None

        # When WAL is disabled, SQLite may use DELETE or other mode
        assert journal_mode != "wal", f"Expected non-WAL mode when disabled, got {journal_mode}"

    def test_busy_timeout_configuration(self, tmp_path):
        """Test that busy timeout is configurable."""
        db_path = tmp_path / "test.db"
        custom_timeout = 60000  # 60 seconds
        db = Database(db_path=db_path, busy_timeout_ms=custom_timeout)
        db.initialize_schema()

        # Verify timeout is set
        with db.get_connection() as conn:
            result = conn.execute("PRAGMA busy_timeout").fetchone()
            timeout_ms = result[0] if result else None

        assert timeout_ms == custom_timeout, f"Expected timeout {custom_timeout}ms, got {timeout_ms}ms"

    def test_concurrent_writers_single_process(self, tmp_path):
        """
        Test 3A: Concurrent writers in one process.

        Spawns multiple threads that write to the database concurrently.
        Verifies no database locking errors occur and all writes succeed.
        """
        db_path = tmp_path / "concurrent_test.db"
        db = Database(db_path=db_path, busy_timeout_ms=120000, wal_enabled=True)
        db.initialize_schema()

        # Create a run record first
        run_id = db.create_run(family="test_family", current_phase="test")

        # Thread worker function
        def write_examples(thread_id: int, count: int, errors: list):
            """Write examples to database from a thread."""
            try:
                for i in range(count):
                    example = ExampleRecord(
                        family="test_family",
                        file_path=f"test_{thread_id}_{i}.md",
                        original_code=f"// Thread {thread_id}, Example {i}",
                        source_type=SourceType.INLINE,
                        language="csharp",
                        location=Location(block_index=0, start_line=1, end_line=2, anchor=""),
                        status=ExampleStatus.DISCOVERED,
                    )
                    # Save with run_id to trigger run state save
                    db.save_example(example, run_id=run_id)
            except Exception as e:
                errors.append((thread_id, str(e)))

        # Spawn multiple threads
        num_threads = 8
        examples_per_thread = 25
        threads = []
        errors = []

        for thread_id in range(num_threads):
            thread = threading.Thread(
                target=write_examples,
                args=(thread_id, examples_per_thread, errors),
            )
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # Verify no errors occurred
        if errors:
            error_msg = "\n".join([f"Thread {tid}: {err}" for tid, err in errors])
            pytest.fail(f"Database locking errors occurred:\n{error_msg}")

        # Verify all examples were saved
        with db.get_connection() as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM example_records WHERE family = ?",
                ("test_family",)
            ).fetchone()[0]

        expected_count = num_threads * examples_per_thread
        assert count == expected_count, f"Expected {expected_count} examples, got {count}"

        # Verify run state records were created
        with db.get_connection() as conn:
            run_state_count = conn.execute(
                "SELECT COUNT(*) FROM example_run_state WHERE run_id = ?",
                (run_id,)
            ).fetchone()[0]

        assert run_state_count == expected_count, (
            f"Expected {expected_count} run state records, got {run_state_count}"
        )

    def test_concurrent_status_updates(self, tmp_path):
        """Test concurrent status updates don't cause locking errors."""
        db_path = tmp_path / "status_test.db"
        db = Database(db_path=db_path, busy_timeout_ms=120000, wal_enabled=True)
        db.initialize_schema()

        # Create a run and examples
        run_id = db.create_run(family="test_family", current_phase="test")

        # Create 50 examples
        example_ids = []
        for i in range(50):
            example = ExampleRecord(
                family="test_family",
                file_path=f"test_{i}.md",
                original_code=f"// Example {i}",
                source_type=SourceType.INLINE,
                language="csharp",
                location=Location(block_index=0, start_line=1, end_line=2, anchor=""),
                status=ExampleStatus.DISCOVERED,
            )
            example_id = db.save_example(example, run_id=run_id)
            example_ids.append(example_id)

        # Thread worker to update statuses
        def update_statuses(thread_id: int, example_ids: list, errors: list):
            """Update example statuses from a thread."""
            try:
                for example_id in example_ids:
                    db.update_example_status(
                        example_id=example_id,
                        status=ExampleStatus.COMPILABLE,
                        run_id=run_id,
                    )
            except Exception as e:
                errors.append((thread_id, str(e)))

        # Spawn threads to update statuses
        num_threads = 4
        threads = []
        errors = []
        examples_per_thread = len(example_ids) // num_threads

        for thread_id in range(num_threads):
            start_idx = thread_id * examples_per_thread
            end_idx = start_idx + examples_per_thread if thread_id < num_threads - 1 else len(example_ids)
            thread_examples = example_ids[start_idx:end_idx]

            thread = threading.Thread(
                target=update_statuses,
                args=(thread_id, thread_examples, errors),
            )
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # Verify no errors
        if errors:
            error_msg = "\n".join([f"Thread {tid}: {err}" for tid, err in errors])
            pytest.fail(f"Database locking errors during status updates:\n{error_msg}")

        # Verify all statuses were updated
        with db.get_connection() as conn:
            updated_count = conn.execute(
                "SELECT COUNT(*) FROM example_run_state WHERE run_id = ? AND status = ?",
                (run_id, ExampleStatus.COMPILABLE.value)
            ).fetchone()[0]

        assert updated_count == len(example_ids), (
            f"Expected {len(example_ids)} updated statuses, got {updated_count}"
        )

    def test_pragmas_applied(self, tmp_path):
        """Test that all required SQLite pragmas are applied."""
        db_path = tmp_path / "pragma_test.db"
        db = Database(db_path=db_path, busy_timeout_ms=30000, wal_enabled=True)
        db.initialize_schema()

        with db.get_connection() as conn:
            # Check WAL mode
            journal_mode = conn.execute("PRAGMA journal_mode").fetchone()[0].lower()
            assert journal_mode == "wal", f"Expected WAL mode, got {journal_mode}"

            # Check synchronous mode
            synchronous = conn.execute("PRAGMA synchronous").fetchone()[0]
            # NORMAL = 1, FULL = 2
            assert synchronous in (1, 2), f"Expected NORMAL(1) or FULL(2), got {synchronous}"

            # Check temp_store
            temp_store = conn.execute("PRAGMA temp_store").fetchone()[0]
            # MEMORY = 2
            assert temp_store == 2, f"Expected MEMORY(2) temp_store, got {temp_store}"

            # Check foreign_keys
            foreign_keys = conn.execute("PRAGMA foreign_keys").fetchone()[0]
            assert foreign_keys == 1, f"Expected foreign_keys ON(1), got {foreign_keys}"

            # Check busy_timeout
            busy_timeout = conn.execute("PRAGMA busy_timeout").fetchone()[0]
            assert busy_timeout == 30000, f"Expected 30000ms timeout, got {busy_timeout}ms"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
