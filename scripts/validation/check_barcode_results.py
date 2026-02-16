import sqlite3

conn = sqlite3.connect('data/example_reviewer.db')
cursor = conn.cursor()

# Get total discovered
cursor.execute("SELECT COUNT(*) FROM example_records WHERE family='barcode'")
total = cursor.fetchone()[0]
print(f"Total Discovered: {total}")

# Get outcomes breakdown
cursor.execute("""
SELECT status, COUNT(*)
FROM example_run_state ers
JOIN example_records er ON ers.example_id = er.example_id
WHERE er.family='barcode'
GROUP BY status
""")
print("\nOutcomes Breakdown:")
for row in cursor.fetchall():
    print(f"  {row[0]}: {row[1]}")

# Get compile attempts
cursor.execute("""
SELECT COUNT(*), SUM(CASE WHEN success=1 THEN 1 ELSE 0 END)
FROM compile_attempts ca
JOIN example_records er ON ca.example_id = er.example_id
WHERE er.family='barcode'
""")
compile_total, compile_success = cursor.fetchone()
print(f"\nCompile Attempts: {compile_total} ({compile_success} successful)")

# Get runtime attempts
cursor.execute("""
SELECT COUNT(*), SUM(CASE WHEN success=1 THEN 1 ELSE 0 END)
FROM runtime_attempts ra
JOIN example_records er ON ra.example_id = er.example_id
WHERE er.family='barcode'
""")
runtime_total, runtime_success = cursor.fetchone()
print(f"Runtime Attempts: {runtime_total} ({runtime_success} successful)")

# Get review results
cursor.execute("""
SELECT COUNT(*), SUM(CASE WHEN approved=1 THEN 1 ELSE 0 END)
FROM review_results
WHERE family='barcode'
""")
review_total, review_pass = cursor.fetchone()
if review_total:
    print(f"\nFinal Reviews: {review_total} ({review_pass} passed)")

conn.close()
