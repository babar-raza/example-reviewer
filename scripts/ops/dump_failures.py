"""Dump all pipeline failures grouped by type with example IDs."""
import sqlite3
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect('data/example_reviewer.db')
cursor = conn.cursor()

cursor.execute('SELECT run_id FROM run_records ORDER BY started_at DESC LIMIT 1')
run_id = cursor.fetchone()[0]
print(f'Run: {run_id}')
print()


def shorten_path(fpath):
    p = str(fpath or '').replace('\\', '/')
    idx = p.find('content/')
    if idx >= 0:
        return p[idx + 8:][:70]
    return p[-70:]


# ======================== COMPILE FAILED ========================
print('=' * 70)
print('COMPILE_FAILED')
print('=' * 70)

cursor.execute('''
    SELECT ers.example_id, ers.failure_reason, er.file_path
    FROM example_run_state ers
    JOIN example_records er ON ers.example_id = er.example_id
    WHERE ers.run_id = ? AND ers.status = 'COMPILE_FAILED'
    ORDER BY ers.failure_reason
''', (run_id,))

compile_groups = {}
for eid, reason, fpath in cursor.fetchall():
    codes = re.findall(r'CS\d+', reason or '')
    key = ', '.join(sorted(set(codes))) if codes else str(reason or 'unknown')[:60]
    if key not in compile_groups:
        compile_groups[key] = []
    compile_groups[key].append((eid, shorten_path(fpath)))

for key, examples in sorted(compile_groups.items(), key=lambda x: -len(x[1])):
    print(f'\n[{len(examples)}] {key}')
    for eid, src in examples:
        print(f'  {eid}  {src}')

# ======================== RUNTIME FAILED ========================
print()
print('=' * 70)
print('RUNTIME_FAILED')
print('=' * 70)

cursor.execute('''
    SELECT ers.example_id, ers.failure_reason, er.file_path
    FROM example_run_state ers
    JOIN example_records er ON ers.example_id = er.example_id
    WHERE ers.run_id = ? AND ers.status = 'RUNTIME_FAILED'
    ORDER BY ers.failure_reason
''', (run_id,))

runtime_groups = {}
for eid, reason, fpath in cursor.fetchall():
    r = str(reason or '')
    if 'Wrong password' in r:
        key = 'Wrong password supplied'
    elif 'Cannot create' in r:
        key = 'Cannot create (file already exists)'
    elif 'not found' in r.lower() or 'NotFound' in r:
        key = 'File/Directory not found'
    else:
        key = r[:80]
    if key not in runtime_groups:
        runtime_groups[key] = []
    runtime_groups[key].append((eid, shorten_path(fpath)))

for key, examples in sorted(runtime_groups.items(), key=lambda x: -len(x[1])):
    print(f'\n[{len(examples)}] {key}')
    for eid, src in examples:
        print(f'  {eid}  {src}')

# ======================== INFRA BLOCKED ========================
print()
print('=' * 70)
print('INFRA_BLOCKED')
print('=' * 70)

cursor.execute('''
    SELECT ers.example_id, ers.failure_reason, er.file_path
    FROM example_run_state ers
    JOIN example_records er ON ers.example_id = er.example_id
    WHERE ers.run_id = ? AND ers.status = 'INFRA_BLOCKED'
''', (run_id,))

for eid, reason, fpath in cursor.fetchall():
    print(f'  {eid}  {shorten_path(fpath)}')
    print(f'    Reason: {str(reason or "")[:120]}')

# ======================== SUMMARY ========================
print()
print('=' * 70)
print('SUMMARY')
print('=' * 70)
print(f'\nCompile failure groups ({sum(len(v) for v in compile_groups.values())} total):')
for key, examples in sorted(compile_groups.items(), key=lambda x: -len(x[1])):
    print(f'  [{len(examples):3d}] {key}')

print(f'\nRuntime failure groups ({sum(len(v) for v in runtime_groups.values())} total):')
for key, examples in sorted(runtime_groups.items(), key=lambda x: -len(x[1])):
    print(f'  [{len(examples):3d}] {key}')

conn.close()
