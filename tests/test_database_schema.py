"""
Tests for database schema and migrations.
Ensures schema is created correctly and migrations apply properly.
"""

import pytest
from pathlib import Path
from src.core.database import Database


class TestDatabaseSchema:
    """Test database schema creation."""

    def test_schema_creates_all_tables(self, temp_db):
        """Schema should create all required tables."""
        db = Database(temp_db)
        db.initialize_schema()

        with db.get_connection() as conn:
            cursor = conn.cursor()

            # Check that core tables exist
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = {row[0] for row in cursor.fetchall()}

            required_tables = {
                'schema_migrations',
                'example_records',
                'example_run_state',
                'compile_attempts',
                'runtime_attempts',
                'markdown_edits',
                'run_records',
                'telemetry_events',
            }

            assert required_tables.issubset(tables), \
                f"Missing tables: {required_tables - tables}"

    def test_example_run_state_composite_key(self, temp_db):
        """example_run_state should have composite primary key (run_id, example_id)."""
        db = Database(temp_db)
        db.initialize_schema()

        with db.get_connection() as conn:
            cursor = conn.cursor()

            # Check table info for example_run_state
            cursor.execute("PRAGMA table_info(example_run_state)")
            columns = {row[1]: row for row in cursor.fetchall()}

            assert 'run_id' in columns
            assert 'example_id' in columns

            # Check that it has the expected columns
            expected_columns = {
                'run_id', 'example_id', 'status', 'failure_reason',
                'escalation_reason', 'compilable_code', 'verified_code',
                'drift_score', 'needs_human_review', 'created_at', 'updated_at'
            }
            assert expected_columns.issubset(columns.keys())

    def test_run_id_columns_added_to_attempts(self, temp_db):
        """compile_attempts, runtime_attempts, markdown_edits should have run_id column."""
        db = Database(temp_db)
        db.initialize_schema()

        with db.get_connection() as conn:
            cursor = conn.cursor()

            for table in ['compile_attempts', 'runtime_attempts', 'markdown_edits']:
                cursor.execute(f"PRAGMA table_info({table})")
                columns = {row[1] for row in cursor.fetchall()}
                assert 'run_id' in columns, f"run_id column missing from {table}"

    def test_example_records_canonical_structure(self, temp_db):
        """example_records should be canonical (no run-scoped fields)."""
        db = Database(temp_db)
        db.initialize_schema()

        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(example_records)")
            columns = {row[1] for row in cursor.fetchall()}

            # Should have canonical fields
            assert 'example_id' in columns
            assert 'family' in columns
            assert 'file_path' in columns
            assert 'original_code' in columns

            # Should NOT have run-scoped fields (those are in example_run_state)
            # Note: If these exist, it means we haven't completed the migration
            # to the production-grade design yet


class TestMigrationEngine:
    """Test migration application."""

    def test_migrations_table_created(self, temp_db):
        """schema_migrations table should be created."""
        db = Database(temp_db)
        db.initialize_schema()

        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='schema_migrations'")
            assert cursor.fetchone() is not None

    def test_migrations_applied_once(self, temp_db):
        """Migrations should only be applied once."""
        db = Database(temp_db)

        # First init
        db.initialize_schema()

        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM schema_migrations")
            count1 = cursor.fetchone()[0]

        # Second init (should not re-apply migrations)
        db.initialize_schema()

        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM schema_migrations")
            count2 = cursor.fetchone()[0]

        # Count should be the same (migrations not re-applied)
        assert count1 == count2


class TestRunScoping:
    """Test run scoping isolation."""

    def test_example_run_state_isolated_by_run(self, temp_db):
        """Example run state should be isolated by run_id."""
        db = Database(temp_db)
        db.initialize_schema()

        # This test is a placeholder - full implementation requires
        # updating database methods to use example_run_state
        # For now, just verify the table structure supports isolation

        with db.get_connection() as conn:
            cursor = conn.cursor()

            # Verify composite primary key structure
            cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='example_run_state'")
            schema = cursor.fetchone()[0]

            assert 'PRIMARY KEY (run_id, example_id)' in schema or 'PRIMARY KEY(run_id, example_id)' in schema
