#!/usr/bin/env python3
"""Check database schema for example_records table."""

import sqlite3
import sys

db_path = sys.argv[1] if len(sys.argv) > 1 else "data/example_reviewer.db"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get table schema
cursor.execute("PRAGMA table_info(example_records)")
columns = cursor.fetchall()

print("example_records columns:")
print("-" * 60)
for col in columns:
    cid, name, col_type, notnull, default, pk = col
    print(f"{cid:3d}  {name:30s}  {col_type:15s}  pk={pk}  null={not notnull}")

print("\n" + "=" * 60)

# Get a sample row
cursor.execute("SELECT * FROM example_records LIMIT 1")
row = cursor.fetchone()
if row:
    print("\nSample row values:")
    print("-" * 60)
    for i, col in enumerate(columns):
        print(f"{col[1]:30s} = {repr(row[i])[:60]}")

conn.close()
