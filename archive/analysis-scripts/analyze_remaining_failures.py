#!/usr/bin/env python3
"""Analyze remaining runtime failures after fix."""

import sqlite3
import os
from pathlib import Path
import re

conn = sqlite3.connect(Path('data/example_reviewer.db'))
cursor = conn.cursor()

print('='*80)
print('  REMAINING RUNTIME FAILURES AFTER FIX')
print('='*80)

cursor.execute('''
    SELECT example_id, file_path, failure_reason
    FROM example_records
    WHERE status = 'RUNTIME_FAILED'
    ORDER BY rowid
''')

failures = cursor.fetchall()
print(f'\nTotal remaining failures: {len(failures)}\n')

# Categorize failures
missing_file_errors = []
other_errors = []

for ex_id, file_path, reason in failures:
    if reason and ('Could not find file' in reason or 'does not exist' in reason):
        # Extract filename from error
        match = re.search(r"'([^']+)'", reason)
        if match:
            full_path = match.group(1)
            filename = os.path.basename(full_path)
        else:
            filename = '(unknown)'
        missing_file_errors.append((ex_id[:8], Path(file_path).name, filename))
    else:
        other_errors.append((ex_id[:8], Path(file_path).name, reason))

print(f'Missing file errors: {len(missing_file_errors)}')
print(f'Other errors: {len(other_errors)}')

if missing_file_errors:
    print(f'\n--- MISSING FILE ERRORS ---')
    seen_files = set()
    for ex_id, file, missing in missing_file_errors:
        print(f'{ex_id} - {file}: missing \"{missing}\"')
        seen_files.add(missing)

    print(f'\nUnique missing files: {", ".join(sorted(seen_files))}')

if other_errors:
    print(f'\n--- OTHER ERRORS ---')
    for ex_id, file, reason in other_errors:
        print(f'{ex_id} - {file}')
        if reason:
            print(f'  {reason[:250]}')
        print()

conn.close()
