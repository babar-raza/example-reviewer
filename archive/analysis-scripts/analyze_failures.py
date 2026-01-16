#!/usr/bin/env python3
"""
Analyze compilation failures to understand error patterns.
"""

import sys
import sqlite3
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from core.database import Database

def analyze_failures():
    db_path = Path('data/example_reviewer.db')
    if not db_path.exists():
        print("Database not found")
        return

    db = Database(db_path)

    # Get all failed compilations
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get examples that failed compilation
    cursor.execute("""
        SELECT example_id, family, original_code, compilable_code, failure_reason
        FROM example_records
        WHERE status = 'COMPILE_FAILED'
        LIMIT 10
    """)

    failed_examples = cursor.fetchall()

    print("="*70)
    print(f"  COMPILATION FAILURE ANALYSIS")
    print("="*70)
    print(f"\nFound {len(failed_examples)} failed examples (showing first 10)\n")

    for i, (ex_id, family, orig_code, comp_code, fail_reason) in enumerate(failed_examples, 1):
        print(f"\n--- Example {i}: {ex_id[:8]} ---")
        print(f"Family: {family}")
        print(f"Code length: {len(orig_code) if orig_code else 0} chars")

        if fail_reason:
            print(f"Failure reason: {fail_reason[:200]}")

        # Get compilation attempts for this example
        cursor.execute("""
            SELECT attempt_id, success, error_messages
            FROM compile_attempts
            WHERE example_id = ?
            ORDER BY rowid DESC
            LIMIT 1
        """, (ex_id,))

        attempt = cursor.fetchone()
        if attempt:
            attempt_id, success, errors_json = attempt
            print(f"Last attempt: {attempt_id}")
            print(f"Success: {success}")

            if errors_json:
                try:
                    errors = json.loads(errors_json)
                    print(f"Errors ({len(errors)}):")
                    for err in errors[:3]:
                        if err and len(err) > 10:
                            print(f"  - {err[:150]}")
                except:
                    print(f"  Raw errors: {errors_json[:200]}")

        # Show code snippet
        code_to_show = comp_code or orig_code
        if code_to_show:
            lines = code_to_show.split('\n')[:5]
            print(f"\nCode preview:")
            for line in lines:
                print(f"  {line[:80]}")
            if len(code_to_show.split('\n')) > 5:
                print(f"  ... ({len(code_to_show.split('\n'))} total lines)")

    conn.close()

    print("\n" + "="*70)
    print("  ANALYSIS COMPLETE")
    print("="*70)

if __name__ == "__main__":
    analyze_failures()
