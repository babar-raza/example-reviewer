#!/usr/bin/env python3
"""
Unit test for strict context validator when no examples are processed.

This test ensures the validator exits gracefully with exit code 2
when there are no examples to validate.
"""

import sys
import tempfile
import sqlite3
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools.validate_strict_context_mode import StrictContextValidator


def test_validator_no_examples():
    """Test that validator handles no examples case properly."""
    # Create a temporary database with schema but no examples
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.db') as f:
        db_path = f.name

    try:
        # Initialize database with minimal schema
        conn = sqlite3.connect(db_path)
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                migration_id TEXT PRIMARY KEY,
                description TEXT NOT NULL,
                applied_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS example_records (
                example_id TEXT PRIMARY KEY,
                family TEXT NOT NULL,
                file_path TEXT NOT NULL,
                source_type TEXT NOT NULL DEFAULT 'inline',
                language TEXT NOT NULL DEFAULT 'csharp',
                location_block_index INTEGER DEFAULT 0,
                location_start_line INTEGER DEFAULT 0,
                location_end_line INTEGER DEFAULT 0,
                location_anchor TEXT DEFAULT '',
                gist_owner TEXT,
                gist_id TEXT,
                gist_filename TEXT,
                original_code TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                section_heading TEXT,
                description_context TEXT,
                topic TEXT,
                example_key TEXT,
                app_context TEXT DEFAULT NULL
            );

            CREATE TABLE IF NOT EXISTS example_run_state (
                run_id TEXT NOT NULL,
                example_id TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'discovered',
                failure_reason TEXT,
                escalation_reason TEXT,
                compilable_code TEXT,
                verified_code TEXT,
                drift_score REAL DEFAULT 0.0,
                drift_similarity REAL DEFAULT 0.0,
                needs_human_review INTEGER DEFAULT 0,
                app_context TEXT DEFAULT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (run_id, example_id)
            );

            CREATE TABLE IF NOT EXISTS run_records (
                run_id TEXT PRIMARY KEY,
                family TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
        """)
        conn.close()

        # Create validator and run with a fake run_id
        validator = StrictContextValidator(db_path=db_path)
        results = validator.validate_run("fake_run_id_with_no_examples")

        # Verify results
        assert results["summary"]["overall_status"] == "NO_EXAMPLES_PROCESSED", \
            f"Expected NO_EXAMPLES_PROCESSED status, got {results['summary']['overall_status']}"
        assert results["summary"]["total_tests"] == 0, \
            f"Expected 0 tests, got {results['summary']['total_tests']}"
        assert results["summary"]["example_count"] == 0, \
            f"Expected 0 examples, got {results['summary']['example_count']}"

        print("[PASS] Test passed: Validator correctly handles no examples case")
        return True

    finally:
        # Cleanup
        Path(db_path).unlink(missing_ok=True)


if __name__ == "__main__":
    try:
        success = test_validator_no_examples()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"[FAIL] Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
