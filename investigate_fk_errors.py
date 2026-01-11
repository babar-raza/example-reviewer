"""
Investigate FOREIGN KEY constraint errors.
"""

import sqlite3
from pathlib import Path

db_path = Path(__file__).parent / "data" / "examples.db"
db = sqlite3.connect(str(db_path))
db.row_factory = sqlite3.Row

print("=" * 70)
print("FOREIGN KEY CONSTRAINT INVESTIGATION")
print("=" * 70)

# 1. Check foreign key constraints on fixes_applied table
print("\n1. Foreign key constraints on fixes_applied table:")
print("-" * 70)
cursor = db.execute('PRAGMA foreign_key_list(fixes_applied)')
rows = cursor.fetchall()
if rows:
    for r in rows:
        print(f"  Table: {r[2]}, From: {r[3]} -> To: {r[4]}")
else:
    print("  No foreign key constraints found")

# 2. Get schema for fixes_applied table
print("\n2. Schema for fixes_applied table:")
print("-" * 70)
cursor = db.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='fixes_applied'")
schema = cursor.fetchone()
if schema:
    print(schema[0])

# 3. Check version counts for snippets with FOREIGN KEY errors
print("\n3. Version counts for snippets with FOREIGN KEY errors:")
print("-" * 70)
failing_snippets = [4, 5, 19, 22, 24, 31, 32, 40, 41, 58, 62, 65, 70, 72, 76]
cursor = db.execute(f'''
SELECT s.snippet_id, s.status, COUNT(sv.version_id) as version_count
FROM snippets s
LEFT JOIN snippet_versions sv ON s.snippet_id = sv.snippet_id
WHERE s.snippet_id IN ({','.join(map(str, failing_snippets))})
GROUP BY s.snippet_id
ORDER BY s.snippet_id
''')
print(f"{'ID':<5} {'Status':<15} {'Versions':<10}")
print("-" * 35)
for row in cursor.fetchall():
    print(f"{row[0]:<5} {row[1]:<15} {row[2]:<10}")

# 4. Check if there are any fix attempts for these snippets
print("\n4. Fix attempts for failing snippets:")
print("-" * 70)
cursor = db.execute(f'''
SELECT snippet_id, COUNT(*) as fix_attempts
FROM fixes_applied
WHERE snippet_id IN ({','.join(map(str, failing_snippets))})
GROUP BY snippet_id
ORDER BY snippet_id
''')
fix_attempts = cursor.fetchall()
if fix_attempts:
    print(f"{'Snippet ID':<12} {'Fix Attempts':<15}")
    print("-" * 30)
    for row in fix_attempts:
        print(f"{row[0]:<12} {row[1]:<15}")
else:
    print("  No fix attempts found in fixes_applied table")

# 5. Check validation attempts for these snippets
print("\n5. Validation attempts for failing snippets:")
print("-" * 70)
cursor = db.execute(f'''
SELECT snippet_id, COUNT(*) as attempts
FROM validation_attempts
WHERE snippet_id IN ({','.join(map(str, failing_snippets))})
GROUP BY snippet_id
ORDER BY snippet_id
''')
validation_attempts = cursor.fetchall()
if validation_attempts:
    print(f"{'Snippet ID':<12} {'Attempts':<15}")
    print("-" * 30)
    for row in validation_attempts:
        print(f"{row[0]:<12} {row[1]:<15}")
else:
    print("  No validation attempts found")

# 6. Get details of one failing snippet to analyze
print("\n6. Detailed analysis of snippet 4 (example):")
print("-" * 70)
cursor = db.execute('''
SELECT
    va.attempt_id,
    va.compilation_success,
    va.error_message,
    va.attempted_at
FROM validation_attempts va
WHERE va.snippet_id = 4
ORDER BY va.attempted_at DESC
LIMIT 5
''')
print(f"{'Attempt ID':<12} {'Success':<10} {'Error':<50}")
print("-" * 75)
for row in cursor.fetchall():
    error = row[2][:47] + "..." if row[2] and len(row[2]) > 50 else (row[2] or "")
    print(f"{row[0]:<12} {str(row[1]):<10} {error:<50}")

db.close()

print("\n" + "=" * 70)
print("Investigation complete")
print("=" * 70)
