#!/usr/bin/env python3
"""Check example statuses in database."""

import sqlite3
import sys

db_path = sys.argv[1] if len(sys.argv) > 1 else "data/example_reviewer.db"
run_id = sys.argv[2] if len(sys.argv) > 2 else None

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

if run_id:
    query = """
        SELECT status, COUNT(*) as count
        FROM example_run_state
        WHERE run_id = ?
        GROUP BY status
        ORDER BY count DESC
    """
    cursor.execute(query, (run_id,))
else:
    query = """
        SELECT status, COUNT(*) as count
        FROM example_run_state
        GROUP BY status
        ORDER BY count DESC
    """
    cursor.execute(query)

print("Example Status Distribution:")
print("-" * 40)
for row in cursor.fetchall():
    print(f"{row['status']:20s} {row['count']:5d}")

conn.close()
