"""Investigate failing EMAIL examples from run ad9e00d9ea72c0d7."""
import sqlite3
import sys

sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = 'c:/Users/prora/OneDrive/Documents/GitHub/example-reviewer/data/example_reviewer.db'
RUN_ID = 'ad9e00d9ea72c0d7'

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

# Get all non-verified examples with their run state
examples = conn.execute('''
    SELECT e.example_id, e.example_key, e.file_path, e.original_code, e.app_context,
           e.section_heading, e.description_context, e.extraction_warning,
           s.status, s.failure_reason, s.escalation_reason
    FROM example_records e
    JOIN example_run_state s ON e.example_id = s.example_id AND s.run_id = ?
    WHERE s.status != 'VERIFIED'
    ORDER BY e.example_id
''', (RUN_ID,)).fetchall()

# Also get total count
total = conn.execute('''
    SELECT count(*) FROM example_run_state WHERE run_id = ?
''', (RUN_ID,)).fetchone()[0]

verified = conn.execute('''
    SELECT count(*) FROM example_run_state WHERE run_id = ? AND status = 'VERIFIED'
''', (RUN_ID,)).fetchone()[0]

print(f"Run {RUN_ID}: {total} total, {verified} verified, {len(examples)} non-verified")
print("=" * 120)

for ex in examples:
    eid = ex['example_id']
    print(f"\n{'=' * 120}")
    print(f"EXAMPLE: {eid}")
    print(f"  key: {ex['example_key']}")
    print(f"  file: {ex['file_path']}")
    print(f"  status: {ex['status']}")
    print(f"  failure_reason: {ex['failure_reason']}")
    print(f"  escalation_reason: {ex['escalation_reason']}")
    print(f"  app_context: {ex['app_context']}")
    print(f"  section_heading: {ex['section_heading']}")
    print(f"  description_context: {(ex['description_context'] or '')[:200]}")
    print(f"  extraction_warning: {ex['extraction_warning']}")

    # Show full original code
    code = ex['original_code'] or ''
    lines = code.split('\n')
    print(f"  --- ORIGINAL CODE ({len(code)} chars, {len(lines)} lines) ---")
    for i, line in enumerate(lines, 1):
        print(f"    {i:3d}| {line}")

    # Show compile attempts
    attempts = conn.execute('''
        SELECT attempt_number, success, error_output, fixed_code
        FROM compile_attempts
        WHERE example_id = ?
        ORDER BY attempt_number
    ''', (eid,)).fetchall()

    print(f"  --- COMPILE ATTEMPTS ({len(attempts)}) ---")
    for att in attempts:
        print(f"    Attempt {att['attempt_number']}: success={att['success']}")
        err = att['error_output'] or ''
        if err:
            print(f"    Error ({len(err)} chars):")
            for line in err.split('\n')[:40]:
                print(f"      {line}")
        fixed = att['fixed_code'] or ''
        if fixed and att['attempt_number'] > 0:
            flines = fixed.split('\n')
            print(f"    Fixed code ({len(fixed)} chars, {len(flines)} lines):")
            for i, line in enumerate(flines[:30], 1):
                print(f"      {i:3d}| {line}")
            if len(flines) > 30:
                print(f"      ... ({len(flines) - 30} more lines)")

    # Show runtime attempts
    runtime_attempts = conn.execute('''
        SELECT attempt_number, success, error_output, exit_code
        FROM runtime_attempts
        WHERE example_id = ?
        ORDER BY attempt_number
    ''', (eid,)).fetchall()

    if runtime_attempts:
        print(f"  --- RUNTIME ATTEMPTS ({len(runtime_attempts)}) ---")
        for rt in runtime_attempts:
            print(f"    Attempt {rt['attempt_number']}: success={rt['success']} exit_code={rt['exit_code']}")
            err = rt['error_output'] or ''
            if err:
                print(f"    Error:")
                for line in err.split('\n')[:20]:
                    print(f"      {line}")

conn.close()
