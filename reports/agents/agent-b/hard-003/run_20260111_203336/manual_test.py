"""Manual test script to verify verify_cache() implementation without pytest.

This script manually creates test scenarios and verifies the verify_cache() method works correctly.
"""

import sys
import json
import tempfile
import logging
from pathlib import Path
from datetime import datetime

# Add src to path
# This file is at: reports/agents/agent-b/hard-003/run_*/manual_test.py
# Need to go up 5 levels to reach repo root
repo_root = Path(__file__).resolve().parent.parent.parent.parent.parent.parent
sys.path.insert(0, str(repo_root / "src"))

try:
    from gist_service import GistService
    from database import Database
except ModuleNotFoundError:
    print(f"Error: Cannot import modules. Repo root: {repo_root}")
    print(f"Sys path: {sys.path[:3]}")
    sys.exit(1)

# Setup logging to see warnings
logging.basicConfig(level=logging.WARNING, format='%(levelname)s: %(message)s')


def test_scenario_1_all_valid():
    """Test with all valid cache files."""
    print("\n=== Test 1: All Valid Cache Files ===")

    temp_dir = Path(tempfile.mkdtemp())
    cache_dir = temp_dir / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Create database
    db_path = temp_dir / "test.db"
    schema_path = Path(__file__).parent.parent.parent.parent.parent / "schema.sql"
    db = Database(db_path)
    db.initialize_schema(schema_path)

    # Create service
    service = GistService(cache_dir=cache_dir, db=db)

    # Create 3 valid cache files
    for i in range(1, 4):
        cache_file = cache_dir / f"valid{i:03d}.json"
        cache_data = {
            'gist_id': f'valid{i:03d}',
            'etag': f'"etag_{i}"',
            'cached_at': datetime.utcnow().isoformat(),
            'data': {
                'id': f'valid{i:03d}',
                'files': {'test.cs': {}}
            }
        }
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f)

    # Verify cache
    result = service.verify_cache()

    # Check results
    assert result['total_files'] == 3, f"Expected 3 files, got {result['total_files']}"
    assert result['valid_files'] == 3, f"Expected 3 valid, got {result['valid_files']}"
    assert result['corrupted_files'] == 0, f"Expected 0 corrupted, got {result['corrupted_files']}"

    print(f"PASS: {result['total_files']} files scanned, all valid")
    return True


def test_scenario_2_corrupted_json():
    """Test with corrupted JSON files."""
    print("\n=== Test 2: Corrupted JSON Files ===")

    temp_dir = Path(tempfile.mkdtemp())
    cache_dir = temp_dir / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Create database
    db_path = temp_dir / "test.db"
    schema_path = Path(__file__).parent.parent.parent.parent.parent / "schema.sql"
    db = Database(db_path)
    db.initialize_schema(schema_path)

    # Create service
    service = GistService(cache_dir=cache_dir, db=db)

    # Create 1 valid file
    valid = cache_dir / "valid.json"
    with open(valid, 'w', encoding='utf-8') as f:
        json.dump({
            'gist_id': 'valid',
            'etag': '"test"',
            'cached_at': datetime.utcnow().isoformat(),
            'data': {'files': {}}
        }, f)

    # Create 2 corrupted files
    corrupt1 = cache_dir / "corrupt1.json"
    with open(corrupt1, 'w') as f:
        f.write("{ invalid json }")

    corrupt2 = cache_dir / "corrupt2.json"
    with open(corrupt2, 'w') as f:
        f.write("not json at all")

    # Verify cache
    result = service.verify_cache()

    # Check results
    assert result['total_files'] == 3, f"Expected 3 files, got {result['total_files']}"
    assert result['valid_files'] == 1, f"Expected 1 valid, got {result['valid_files']}"
    assert result['corrupted_files'] == 2, f"Expected 2 corrupted, got {result['corrupted_files']}"
    assert len(result['removed_files']) == 2, f"Expected 2 removed, got {len(result['removed_files'])}"

    # Verify files removed
    assert not corrupt1.exists(), "corrupt1 should be removed"
    assert not corrupt2.exists(), "corrupt2 should be removed"
    assert valid.exists(), "valid file should remain"

    print(f"PASS: {result['corrupted_files']} corrupted files detected and removed")
    return True


def test_scenario_3_missing_fields():
    """Test with missing required fields."""
    print("\n=== Test 3: Missing Required Fields ===")

    temp_dir = Path(tempfile.mkdtemp())
    cache_dir = temp_dir / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Create database
    db_path = temp_dir / "test.db"
    schema_path = Path(__file__).parent.parent.parent.parent.parent / "schema.sql"
    db = Database(db_path)
    db.initialize_schema(schema_path)

    # Create service
    service = GistService(cache_dir=cache_dir, db=db)

    # Missing gist_id
    missing_gist = cache_dir / "missing_gist.json"
    with open(missing_gist, 'w') as f:
        json.dump({
            'etag': '"test"',
            'cached_at': datetime.utcnow().isoformat(),
            'data': {'files': {}}
        }, f)

    # Missing data
    missing_data = cache_dir / "missing_data.json"
    with open(missing_data, 'w') as f:
        json.dump({
            'gist_id': 'test',
            'etag': '"test"',
            'cached_at': datetime.utcnow().isoformat()
        }, f)

    # Verify cache
    result = service.verify_cache()

    # Check results
    assert result['total_files'] == 2, f"Expected 2 files, got {result['total_files']}"
    assert result['valid_files'] == 0, f"Expected 0 valid, got {result['valid_files']}"
    assert result['corrupted_files'] == 2, f"Expected 2 corrupted, got {result['corrupted_files']}"

    # Verify files removed
    assert not missing_gist.exists(), "missing_gist should be removed"
    assert not missing_data.exists(), "missing_data should be removed"

    print(f"PASS: Files with missing fields detected and removed")
    return True


def test_scenario_4_invalid_timestamp():
    """Test with invalid timestamp format."""
    print("\n=== Test 4: Invalid Timestamp Format ===")

    temp_dir = Path(tempfile.mkdtemp())
    cache_dir = temp_dir / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Create database
    db_path = temp_dir / "test.db"
    schema_path = Path(__file__).parent.parent.parent.parent.parent / "schema.sql"
    db = Database(db_path)
    db.initialize_schema(schema_path)

    # Create service
    service = GistService(cache_dir=cache_dir, db=db)

    # Invalid timestamp
    invalid_ts = cache_dir / "invalid_ts.json"
    with open(invalid_ts, 'w') as f:
        json.dump({
            'gist_id': 'test',
            'etag': '"test"',
            'cached_at': 'not-a-valid-timestamp',
            'data': {'files': {}}
        }, f)

    # Verify cache
    result = service.verify_cache()

    # Check results
    assert result['total_files'] == 1, f"Expected 1 file, got {result['total_files']}"
    assert result['valid_files'] == 0, f"Expected 0 valid, got {result['valid_files']}"
    assert result['corrupted_files'] == 1, f"Expected 1 corrupted, got {result['corrupted_files']}"

    # Verify file removed
    assert not invalid_ts.exists(), "invalid_ts should be removed"

    print(f"PASS: Invalid timestamp detected and file removed")
    return True


def test_scenario_5_empty_directory():
    """Test with empty cache directory."""
    print("\n=== Test 5: Empty Cache Directory ===")

    temp_dir = Path(tempfile.mkdtemp())
    cache_dir = temp_dir / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Create database
    db_path = temp_dir / "test.db"
    schema_path = Path(__file__).parent.parent.parent.parent.parent / "schema.sql"
    db = Database(db_path)
    db.initialize_schema(schema_path)

    # Create service
    service = GistService(cache_dir=cache_dir, db=db)

    # Verify cache (empty)
    result = service.verify_cache()

    # Check results
    assert result['total_files'] == 0, f"Expected 0 files, got {result['total_files']}"
    assert result['valid_files'] == 0, f"Expected 0 valid, got {result['valid_files']}"
    assert result['corrupted_files'] == 0, f"Expected 0 corrupted, got {result['corrupted_files']}"

    print(f"PASS: Empty directory handled correctly")
    return True


def main():
    """Run all manual tests."""
    print("=" * 60)
    print("Manual Test Suite for verify_cache()")
    print("=" * 60)

    tests = [
        test_scenario_1_all_valid,
        test_scenario_2_corrupted_json,
        test_scenario_3_missing_fields,
        test_scenario_4_invalid_timestamp,
        test_scenario_5_empty_directory,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
        except AssertionError as e:
            print(f"FAIL: {e}")
            failed += 1
        except Exception as e:
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
