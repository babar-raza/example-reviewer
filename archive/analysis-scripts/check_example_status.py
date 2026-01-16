#!/usr/bin/env python3
"""Check status of specific example."""

import sqlite3
from pathlib import Path

db_path = Path('data/example_reviewer.db')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get example details
cursor.execute('''
    SELECT example_id, file_path, status, failure_reason, compilable_code, verified_code
    FROM example_records
    WHERE example_id LIKE '35e5a83b%'
''')

row = cursor.fetchone()
if row:
    ex_id, file_path, status, failure_reason, compilable_code, verified_code = row
    print(f"Example ID: {ex_id}")
    print(f"File: {file_path}")
    print(f"Status: {status}")
    print(f"Failure Reason: {failure_reason[:200] if failure_reason else 'None'}")
    print(f"\nCompilable Code Length: {len(compilable_code) if compilable_code else 0}")
    print(f"Verified Code Length: {len(verified_code) if verified_code else 0}")

    if verified_code and verified_code != compilable_code:
        print("\n--- LAST LLM FIX ATTEMPT ---")
        print(verified_code[:500])
else:
    print("Example not found")

conn.close()
