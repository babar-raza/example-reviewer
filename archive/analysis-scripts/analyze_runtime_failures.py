#!/usr/bin/env python3
"""Analyze runtime failures to identify patterns and root causes."""

import sqlite3
from pathlib import Path
import json

db_path = Path('data/example_reviewer.db')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("="*80)
print("  RUNTIME FAILURE ANALYSIS")
print("="*80)

# Get runtime failure statistics
cursor.execute('''
    SELECT
        COUNT(*) as total,
        SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as passed,
        SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed
    FROM runtime_attempts
''')

total, passed, failed = cursor.fetchone()
print(f"\nRuntime Attempts Summary:")
print(f"  Total: {total}")
print(f"  Passed: {passed} ({100*passed/total:.1f}%)" if total > 0 else "  Passed: 0")
print(f"  Failed: {failed} ({100*failed/total:.1f}%)" if total > 0 else "  Failed: 0")

# Get exception types
cursor.execute('''
    SELECT exception_type, COUNT(*) as count
    FROM runtime_attempts
    WHERE success = 0 AND exception_type IS NOT NULL
    GROUP BY exception_type
    ORDER BY count DESC
''')

print(f"\nException Types:")
for exc_type, count in cursor.fetchall():
    print(f"  {count:3d}x {exc_type}")

# Get specific error patterns from stderr
cursor.execute('''
    SELECT e.example_id, e.file_path, r.exit_code, r.stderr, r.stdout, r.exception_type, r.exception_message
    FROM example_records e
    JOIN runtime_attempts r ON e.example_id = r.example_id
    WHERE r.success = 0
    ORDER BY r.rowid DESC
    LIMIT 15
''')

print(f"\n{'='*80}")
print(f"TOP 15 RUNTIME FAILURES - DETAILED")
print(f"{'='*80}\n")

error_patterns = {}

for i, (ex_id, file_path, exit_code, stderr, stdout, exc_type, exc_msg) in enumerate(cursor.fetchall(), 1):
    print(f"{i}. Example {ex_id[:8]} - {Path(file_path).name}")
    print(f"   Exit code: {exit_code}")

    if exc_type:
        print(f"   Exception: {exc_type}")
    if exc_msg:
        print(f"   Message: {exc_msg[:200]}")

    if stderr:
        # Extract key error lines
        lines = stderr.strip().split('\n')
        error_lines = [l for l in lines if 'error' in l.lower() or 'exception' in l.lower()]

        if error_lines:
            key_error = error_lines[-1][:150]
            print(f"   Error: {key_error}")

            # Categorize errors
            if 'FileNotFoundException' in key_error or 'could not find file' in key_error.lower():
                error_patterns['missing_file'] = error_patterns.get('missing_file', 0) + 1
            elif 'DirectoryNotFoundException' in key_error or 'could not find path' in key_error.lower():
                error_patterns['missing_directory'] = error_patterns.get('missing_directory', 0) + 1
            elif 'InvalidDataException' in key_error:
                error_patterns['invalid_archive'] = error_patterns.get('invalid_archive', 0) + 1
            elif 'IOException' in key_error:
                error_patterns['io_error'] = error_patterns.get('io_error', 0) + 1
            else:
                error_patterns['other'] = error_patterns.get('other', 0) + 1
        else:
            # Show last line of stderr
            print(f"   Stderr: {lines[-1][:150] if lines else '(empty)'}")

    if stdout:
        # Check if there's useful info in stdout
        lines = stdout.strip().split('\n')
        if lines and len(lines[-1]) > 0:
            print(f"   Stdout: {lines[-1][:100]}")

    print()

print(f"{'='*80}")
print(f"ERROR PATTERN SUMMARY")
print(f"{'='*80}\n")
for pattern, count in sorted(error_patterns.items(), key=lambda x: x[1], reverse=True):
    print(f"  {count:3d}x {pattern}")

conn.close()

print(f"\n{'='*80}")
print(f"ANALYSIS COMPLETE")
print(f"{'='*80}")
