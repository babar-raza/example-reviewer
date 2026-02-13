#!/usr/bin/env python3
"""
Unit test for strict context validator DB path location feature.

This test ensures the validator can auto-locate the database path
from fingerprint.json files when --db-path is not provided.
"""

import json
import sys
import tempfile
import sqlite3
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools.validate_strict_context_mode import locate_db_path_from_run_id, StrictContextValidator


def test_db_path_location_from_fingerprint():
    """Test that validator can locate DB path from fingerprint.json."""
    # Create a temporary directory structure mimicking reports/e2e
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Create reports/e2e/run_test/run_1 directory
        run_dir = tmpdir_path / "reports" / "e2e" / "run_test" / "run_1"
        run_dir.mkdir(parents=True, exist_ok=True)

        # Create a temporary database
        db_path = tmpdir_path / "test_db.db"
        conn = sqlite3.connect(str(db_path))
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS example_run_state (
                run_id TEXT NOT NULL,
                example_id TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'discovered',
                failure_reason TEXT,
                PRIMARY KEY (run_id, example_id)
            );

            CREATE TABLE IF NOT EXISTS example_records (
                example_id TEXT PRIMARY KEY,
                family TEXT NOT NULL,
                file_path TEXT NOT NULL,
                source_type TEXT NOT NULL DEFAULT 'inline',
                language TEXT NOT NULL DEFAULT 'csharp',
                original_code TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                app_context TEXT DEFAULT NULL
            );
        """)
        conn.close()

        # Create fingerprint.json with db_path
        test_run_id = "test_run_12345678"
        fingerprint_data = {
            "run_id": test_run_id,
            "selection_hash": "abc123",
            "total_examples": 5,
            "db_path": str(db_path),
            "artifacts_dir": str(run_dir)
        }

        fingerprint_path = run_dir / "fingerprint.json"
        with open(fingerprint_path, 'w', encoding='utf-8') as f:
            json.dump(fingerprint_data, f, indent=2)

        # Change to tmpdir to make glob patterns work
        import os
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir_path)

            # Test locate_db_path_from_run_id function
            located_db_path = locate_db_path_from_run_id(test_run_id)

            assert located_db_path is not None, "DB path should be found"
            assert located_db_path == str(db_path), \
                f"Expected {db_path}, got {located_db_path}"

            print(f"[PASS] Successfully located DB path: {located_db_path}")

            # Test that validator can be initialized with located path
            validator = StrictContextValidator(db_path=located_db_path)
            assert validator.db is not None, "Validator database should be initialized"

            print("[PASS] Validator initialized successfully with located DB path")

            # Test with non-existent run_id
            missing_db_path = locate_db_path_from_run_id("nonexistent_run_id")
            assert missing_db_path is None, \
                f"Expected None for non-existent run_id, got {missing_db_path}"

            print("[PASS] Correctly returns None for non-existent run_id")

        finally:
            os.chdir(original_cwd)


def test_validator_without_db_path_fails_gracefully():
    """Test that validator fails gracefully when db_path cannot be located."""
    # Test with a run_id that doesn't exist
    located_db_path = locate_db_path_from_run_id("definitely_does_not_exist")

    assert located_db_path is None, \
        "Should return None when fingerprint.json is not found"

    print("[PASS] Validator correctly returns None when fingerprint not found")

if __name__ == "__main__":
    try:
        print("Testing DB path location from fingerprint.json...")
        test_db_path_location_from_fingerprint()

        print("\nTesting graceful failure when fingerprint not found...")
        test_validator_without_db_path_fails_gracefully()

        print("\n[PASS] All tests passed!")
        sys.exit(0)
    except Exception as e:
        print(f"\n[FAIL] Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
