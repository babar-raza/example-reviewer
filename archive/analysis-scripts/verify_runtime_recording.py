"""
Verification script: Run pipeline and verify runtime attempts are recorded.
"""

import subprocess
import sqlite3
from pathlib import Path
import time

def check_database_state():
    """Check database state before and after pipeline run."""
    db_path = Path("data/example_reviewer.db")

    if not db_path.exists():
        print(f"ERROR: Database not found at {db_path}")
        return None

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Get counts
    total_examples = cursor.execute("SELECT COUNT(*) FROM example_records").fetchone()[0]
    compile_attempts = cursor.execute("SELECT COUNT(*) FROM compile_attempts").fetchone()[0]
    runtime_attempts = cursor.execute("SELECT COUNT(*) FROM runtime_attempts").fetchone()[0]

    # Get examples by status
    status_counts = {}
    for status, count in cursor.execute("SELECT status, COUNT(*) FROM example_records GROUP BY status").fetchall():
        status_counts[status] = count

    conn.close()

    return {
        'total_examples': total_examples,
        'compile_attempts': compile_attempts,
        'runtime_attempts': runtime_attempts,
        'status_counts': status_counts,
    }

def main():
    print("\n" + "="*80)
    print("RUNTIME ATTEMPT RECORDING VERIFICATION")
    print("="*80 + "\n")

    # Get initial state
    print("INITIAL DATABASE STATE:")
    initial_state = check_database_state()
    if initial_state:
        print(f"  Total examples: {initial_state['total_examples']}")
        print(f"  Compile attempts: {initial_state['compile_attempts']}")
        print(f"  Runtime attempts: {initial_state['runtime_attempts']}")
        print(f"  Status breakdown: {initial_state['status_counts']}")

    print("\n" + "="*80)
    print("RUNNING PIPELINE (3 examples, force rerun)")
    print("="*80 + "\n")

    # Run pipeline with limited examples
    start_time = time.time()

    # Use current Python interpreter
    import sys
    python_exe = sys.executable

    result = subprocess.run(
        [python_exe, "-m", "src.cli.main", "run",
         "--family", "zip",
         "--max-examples", "3",
         "--skip-llm",  # Skip LLM fixes to run faster
         "--dry-run"],  # Don't commit changes
        capture_output=True,
        text=True,
        timeout=300,
        cwd=Path.cwd()
    )
    duration = time.time() - start_time

    print(f"Pipeline completed in {duration:.1f}s")
    print(f"Exit code: {result.returncode}")

    if result.returncode != 0:
        print("\nSTDERR:")
        print(result.stderr[-2000:] if len(result.stderr) > 2000 else result.stderr)

    # Show last 50 lines of output
    output_lines = result.stdout.split('\n')
    print("\nPipeline output (last 50 lines):")
    for line in output_lines[-50:]:
        print(line)

    print("\n" + "="*80)
    print("FINAL DATABASE STATE:")
    print("="*80 + "\n")

    final_state = check_database_state()
    if final_state:
        print(f"  Total examples: {final_state['total_examples']}")
        print(f"  Compile attempts: {final_state['compile_attempts']}")
        print(f"  Runtime attempts: {final_state['runtime_attempts']}")
        print(f"  Status breakdown: {final_state['status_counts']}")

    print("\n" + "="*80)
    print("VERIFICATION RESULTS:")
    print("="*80 + "\n")

    if initial_state and final_state:
        compile_delta = final_state['compile_attempts'] - initial_state['compile_attempts']
        runtime_delta = final_state['runtime_attempts'] - initial_state['runtime_attempts']

        print(f"Compile attempts added: {compile_delta}")
        print(f"Runtime attempts added: {runtime_delta}")

        if runtime_delta > 0:
            print("\n[SUCCESS] Runtime attempts are now being recorded!")
            print(f"   {runtime_delta} new runtime attempts were saved to the database.")
        else:
            print("\n[FAILURE] No runtime attempts were recorded!")
            print("   The fix may not be working correctly.")

        # Check specific examples
        print("\n" + "="*80)
        print("SAMPLE RUNTIME ATTEMPTS (last 5):")
        print("="*80)

        conn = sqlite3.connect("data/example_reviewer.db")
        cursor = conn.cursor()

        attempts = cursor.execute("""
            SELECT example_id, scenario, success, exit_code, exception_message, timestamp
            FROM runtime_attempts
            ORDER BY timestamp DESC
            LIMIT 5
        """).fetchall()

        if attempts:
            for attempt in attempts:
                print(f"\nExample ID: {attempt[0]}")
                print(f"  Scenario: {attempt[1]}")
                print(f"  Success: {attempt[2]}")
                print(f"  Exit Code: {attempt[3]}")
                print(f"  Error: {attempt[4][:80] if attempt[4] else 'None'}...")
                print(f"  Timestamp: {attempt[5]}")
        else:
            print("  No runtime attempts found")

        conn.close()

    print("\n" + "="*80)

if __name__ == "__main__":
    main()
