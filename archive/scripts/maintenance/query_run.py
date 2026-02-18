import sqlite3
import sys

db_path = sys.argv[1]
run_id = sys.argv[2]

conn = sqlite3.connect(db_path)

# Total examples
cursor = conn.execute('SELECT COUNT(*) FROM example_records WHERE run_id=?', (run_id,))
print(f'Total examples: {cursor.fetchone()[0]}')

# Get run info
cursor = conn.execute('SELECT family, phase, max_examples FROM run_records WHERE run_id=?', (run_id,))
run_info = cursor.fetchone()
if run_info:
    print(f'Family: {run_info[0]}, Phase: {run_info[1]}, Max examples: {run_info[2]}')

# Status counts from example_run_state
cursor = conn.execute('SELECT terminal_status, COUNT(*) FROM example_run_state WHERE run_id=? GROUP BY terminal_status', (run_id,))
print('\nTerminal status counts:')
for row in cursor:
    print(f'  {row[0]}: {row[1]}')

# Phase counts from example_run_state
cursor = conn.execute('SELECT current_phase, COUNT(*) FROM example_run_state WHERE run_id=? GROUP BY current_phase', (run_id,))
print('\nCurrent phase distribution:')
for row in cursor:
    print(f'  {row[0]}: {row[1]}')

conn.close()
