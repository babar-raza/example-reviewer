"""
Simple analysis script: Investigate why examples have 0 compile attempts but show as compiled.
"""

import sqlite3
from pathlib import Path

def main():
    db_path = Path("data/example_reviewer.db")

    if not db_path.exists():
        print(f"ERROR: Database not found at {db_path}")
        return

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    print("\n" + "="*80)
    print("DATABASE ANALYSIS: Compilation Tracking Discrepancy")
    print("="*80 + "\n")

    # Get all examples
    all_examples = cursor.execute(
        "SELECT example_id, status, file_path, source_type FROM example_records"
    ).fetchall()

    print(f"Total examples in database: {len(all_examples)}\n")

    # Get status breakdown
    print("Status Breakdown:")
    status_counts = cursor.execute(
        "SELECT status, COUNT(*) FROM example_records GROUP BY status"
    ).fetchall()
    for status, count in status_counts:
        print(f"  {status}: {count}")

    # Check examples with compilable_code
    examples_with_compilable = cursor.execute(
        "SELECT COUNT(*) FROM example_records WHERE compilable_code IS NOT NULL"
    ).fetchone()[0]

    print(f"\nExamples with compilable_code: {examples_with_compilable}")

    # Check total compile attempts
    total_compile_attempts = cursor.execute(
        "SELECT COUNT(*) FROM compile_attempts"
    ).fetchone()[0]

    print(f"Total compile attempts in database: {total_compile_attempts}")

    # Check total runtime attempts
    total_runtime_attempts = cursor.execute(
        "SELECT COUNT(*) FROM runtime_attempts"
    ).fetchone()[0]

    print(f"Total runtime attempts in database: {total_runtime_attempts}")

    print("\n" + "="*80)
    print("KEY FINDING: Discrepancy!")
    print("="*80)
    print(f"Examples with compilable_code: {examples_with_compilable}")
    print(f"Compile attempts recorded: {total_compile_attempts}")
    print(f"Runtime attempts recorded: {total_runtime_attempts}")
    print("\nThis suggests that:")
    print("1. Examples are being marked as compiled without recording attempts")
    print("2. OR compile/runtime attempts are not being saved to the database")
    print("3. OR we're looking at data from different pipeline runs")

    # Check run records
    print("\n" + "="*80)
    print("RUN RECORDS")
    print("="*80)

    runs = cursor.execute(
        "SELECT run_id, family, status, started_at, completed_at FROM run_records ORDER BY started_at DESC LIMIT 5"
    ).fetchall()

    print(f"\nLast 5 runs:")
    for run in runs:
        print(f"  Run ID: {run[0]}")
        print(f"    Family: {run[1]}")
        print(f"    Status: {run[2]}")
        print(f"    Started: {run[3]}")
        print(f"    Completed: {run[4]}")
        print()

    # Check specific failed examples
    print("\n" + "="*80)
    print("FAILED EXAMPLES DETAIL")
    print("="*80)

    failed_examples = cursor.execute(
        "SELECT example_id, status, file_path, failure_reason, updated_at FROM example_records "
        "WHERE status IN ('RUNTIME_FAILED', 'COMPILE_FAILED') LIMIT 5"
    ).fetchall()

    print(f"\nSample of failed examples:")
    for ex in failed_examples:
        print(f"\nExample ID: {ex[0]}")
        print(f"  Status: {ex[1]}")
        print(f"  File: {ex[2]}")
        print(f"  Failure: {ex[3][:100] if ex[3] else None}...")
        print(f"  Updated: {ex[4]}")

        # Check if this example has any attempts
        compile_count = cursor.execute(
            "SELECT COUNT(*) FROM compile_attempts WHERE example_id = ?",
            (ex[0],)
        ).fetchone()[0]

        runtime_count = cursor.execute(
            "SELECT COUNT(*) FROM runtime_attempts WHERE example_id = ?",
            (ex[0],)
        ).fetchone()[0]

        print(f"  Compile attempts: {compile_count}")
        print(f"  Runtime attempts: {runtime_count}")

    conn.close()

    print("\n" + "="*80)
    print("CONCLUSION")
    print("="*80)
    print("The database shows examples with status RUNTIME_FAILED and compilable_code,")
    print("but 0 compile_attempts and 0 runtime_attempts. This indicates:")
    print("1. The compilation/runtime phases ran but didn't save attempt records")
    print("2. The attempt saving logic may be broken or not called")
    print("3. Need to trace through compilation_service.py and runtime_service.py")
    print("   to see where save_compile_attempt() and save_runtime_attempt() are called")

if __name__ == "__main__":
    main()
