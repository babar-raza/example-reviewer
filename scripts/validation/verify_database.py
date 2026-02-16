"""Verify database contains correct example counts."""
import sqlite3
import sys
from pathlib import Path

def verify_database(db_path, expected_count=None, run_id=None):
    """Query and verify database example counts."""
    if not Path(db_path).exists():
        print(f"❌ Database does not exist: {db_path}")
        return False

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get total count
    if run_id:
        cursor.execute(
            'SELECT COUNT(*) FROM examples WHERE family="zip" AND run_id=?',
            (run_id,)
        )
        count_label = f"for run_id={run_id}"
    else:
        cursor.execute('SELECT COUNT(*) FROM examples WHERE family="zip"')
        count_label = "total"

    total_count = cursor.fetchone()[0]
    print(f"\n📊 Database Statistics ({count_label}):")
    print(f"   Total examples: {total_count}")

    # Get count by status
    cursor.execute('''
        SELECT status, COUNT(*)
        FROM examples
        WHERE family="zip"
        GROUP BY status
    ''')

    print(f"\n   By Status:")
    for status, count in cursor.fetchall():
        print(f"     {status}: {count}")

    # Get count by source type
    cursor.execute('''
        SELECT source_type, COUNT(*)
        FROM examples
        WHERE family="zip"
        GROUP BY source_type
    ''')

    print(f"\n   By Source Type:")
    for source_type, count in cursor.fetchall():
        print(f"     {source_type}: {count}")

    # Verify expected count
    if expected_count is not None:
        if total_count == expected_count:
            print(f"\n✓ PASS: Database contains exactly {expected_count} examples")
            success = True
        else:
            print(f"\n❌ FAIL: Expected {expected_count} examples, found {total_count}")
            success = False
    else:
        success = True

    conn.close()
    return success

if __name__ == '__main__':
    db_path = sys.argv[1] if len(sys.argv) > 1 else 'data/example_reviewer.db'
    expected_count = int(sys.argv[2]) if len(sys.argv) > 2 else None
    run_id = sys.argv[3] if len(sys.argv) > 3 else None

    success = verify_database(db_path, expected_count, run_id)
    sys.exit(0 if success else 1)
