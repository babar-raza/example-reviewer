"""
E2E test script for max_examples functionality.

Tests different max_examples values to verify discovery stops at the correct limit.
"""
import subprocess
import sys
import re
import sqlite3
import os
import tempfile
import shutil
from pathlib import Path

# Fix Windows encoding for Unicode output
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

def run_command(cmd, description):
    """Run command and return output."""
    print(f"\n{'='*80}")
    print(f"TEST: {description}")
    print(f"{'='*80}")
    print(f"Command: {' '.join(cmd)}")

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace'
    )

    return result.returncode, result.stdout, result.stderr

def extract_discovery_stats(output):
    """Extract discovery statistics from output."""
    # Look for "Discovery complete: X examples found"
    match = re.search(r'Discovery complete: (\d+) examples found', output)
    if match:
        examples_found = int(match.group(1))
    else:
        examples_found = None

    # Look for "Reached max_examples limit"
    hit_limit = 'Reached max_examples limit' in output

    # Look for "Processing X files"
    files_match = re.search(r'Processing (\d+) files', output)
    files_to_process = int(files_match.group(1)) if files_match else None

    return {
        'examples_found': examples_found,
        'hit_limit': hit_limit,
        'files_to_process': files_to_process
    }

def query_database(db_path, run_id=None):
    """Query database for example counts."""
    if not os.path.exists(db_path):
        return None

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    if run_id:
        cursor.execute(
            'SELECT COUNT(*) FROM examples WHERE family="zip" AND run_id=?',
            (run_id,)
        )
    else:
        cursor.execute('SELECT COUNT(*) FROM examples WHERE family="zip"')

    count = cursor.fetchone()[0]
    conn.close()
    return count

def test_max_examples(limit, expected_count, python_exe, db_path):
    """Test a specific max_examples limit."""
    cmd = [
        python_exe,
        '-m', 'src.cli.main',
        'run',
        '--family', 'zip',
        '--max-examples', str(limit)
    ]

    returncode, stdout, stderr = run_command(
        cmd,
        f"max-examples {limit} (expect {expected_count} examples)"
    )

    output = stdout + stderr
    stats = extract_discovery_stats(output)

    print(f"\nRESULTS:")
    print(f"  Examples found: {stats['examples_found']}")
    print(f"  Hit limit: {stats['hit_limit']}")
    print(f"  Files to process: {stats['files_to_process']}")

    # Verify expectations
    success = True
    if stats['examples_found'] != expected_count:
        print(f"  ❌ FAIL: Expected {expected_count} examples, got {stats['examples_found']}")
        success = False
    else:
        print(f"  ✓ PASS: Correct number of examples discovered")

    if expected_count < 67 and not stats['hit_limit']:
        print(f"  ❌ FAIL: Should have hit limit but didn't")
        success = False
    elif expected_count < 67 and stats['hit_limit']:
        print(f"  ✓ PASS: Correctly hit limit and stopped early")

    return success, stats

def test_no_limit(python_exe, db_path):
    """Test with no max_examples limit."""
    cmd = [
        python_exe,
        '-m', 'src.cli.main',
        'run',
        '--family', 'zip'
    ]

    returncode, stdout, stderr = run_command(
        cmd,
        "No limit (expect all examples discovered)"
    )

    output = stdout + stderr
    stats = extract_discovery_stats(output)

    print(f"\nRESULTS:")
    print(f"  Examples found: {stats['examples_found']}")
    print(f"  Hit limit: {stats['hit_limit']}")

    success = True
    if stats['hit_limit']:
        print(f"  ❌ FAIL: Should not have hit limit when no limit specified")
        success = False
    else:
        print(f"  ✓ PASS: No limit hit (as expected)")

    # For zip family, we expect around 50-70 examples total
    if stats['examples_found'] and stats['examples_found'] >= 40:
        print(f"  ✓ PASS: Discovered substantial number of examples ({stats['examples_found']})")
    else:
        print(f"  ⚠ WARNING: Expected more examples (got {stats['examples_found']})")

    return success, stats

def main():
    """Run all E2E tests."""
    project_root = Path(__file__).parent
    python_exe = project_root / '.venv' / 'Scripts' / 'python.exe'
    db_path = project_root / 'data' / 'example_reviewer.db'

    print("="*80)
    print("E2E Test Suite for max_examples Discovery Limiting")
    print("="*80)
    print(f"Python: {python_exe}")
    print(f"Database: {db_path}")
    print(f"Working directory: {project_root}")

    # Clean database before tests
    if db_path.exists():
        print(f"\nRemoving existing database: {db_path}")
        db_path.unlink()

    os.chdir(project_root)

    # Test scenarios
    test_cases = [
        (3, 3, "Very small limit"),
        (5, 5, "Small limit"),
        (10, 10, "Medium-small limit"),
        (20, 20, "Medium limit"),
        (50, 50, "Large limit"),
    ]

    results = []

    # Run tests
    for limit, expected, description in test_cases:
        success, stats = test_max_examples(limit, expected, str(python_exe), str(db_path))
        results.append({
            'test': f"max-examples {limit}",
            'expected': expected,
            'actual': stats['examples_found'],
            'success': success
        })

        # Clean DB between tests
        if db_path.exists():
            db_path.unlink()

    # Test no limit
    success, stats = test_no_limit(str(python_exe), str(db_path))
    results.append({
        'test': 'no limit',
        'expected': '>40',
        'actual': stats['examples_found'],
        'success': success
    })

    # Print summary
    print(f"\n{'='*80}")
    print("TEST SUMMARY")
    print(f"{'='*80}")

    print(f"\n{'Test':<20} {'Expected':<12} {'Actual':<12} {'Status'}")
    print("-" * 60)

    for r in results:
        status = '✓ PASS' if r['success'] else '❌ FAIL'
        print(f"{r['test']:<20} {str(r['expected']):<12} {str(r['actual']):<12} {status}")

    total_tests = len(results)
    passed_tests = sum(1 for r in results if r['success'])

    print(f"\n{'='*80}")
    print(f"RESULTS: {passed_tests}/{total_tests} tests passed")
    print(f"{'='*80}")

    if passed_tests == total_tests:
        print("\n🎉 ALL TESTS PASSED!")
        return 0
    else:
        print(f"\n⚠️  {total_tests - passed_tests} test(s) failed")
        return 1

if __name__ == '__main__':
    sys.exit(main())
