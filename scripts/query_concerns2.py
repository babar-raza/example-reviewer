"""Query results for the 15 concern articles from run f5e3066f89c3fa17."""
import sqlite3
import sys
import os
sys.stdout.reconfigure(encoding='utf-8')

db = sqlite3.connect('data/example_reviewer.db')
db.row_factory = sqlite3.Row

run_id = 'f5e3066f89c3fa17'

slugs = [
    'track-comments', 'add-watermarks', 'backup-encrypt',
    'document-creation', 'automate-elearning', 'invoice-receipt',
    'legal-workflow', 'remove-blank', 'approval-system',
    'version-system', 'fillable-interactive', 'extract-text',
    'format-pages', 'read-word-document', 'optimize-processing'
]

rows = db.execute('''
    SELECT er.file_path, er.example_id, er.article_intent,
           ers.status, ers.failure_reason
    FROM example_records er
    JOIN example_run_state ers ON er.example_id=ers.example_id
    WHERE ers.run_id=?
    ORDER BY er.file_path, er.example_id
''', (run_id,)).fetchall()

# Review results for this run
rr_count = db.execute("SELECT COUNT(*) FROM review_results WHERE run_id=?", (run_id,)).fetchone()[0]
ri_count = db.execute("""
    SELECT COUNT(*) FROM review_issues ri
    JOIN review_results rr ON ri.review_id=rr.review_id
    WHERE rr.run_id=?
""", (run_id,)).fetchone()[0]
print(f"Run: {run_id}")
print(f"Total examples in run: {len(rows)}")
print(f"ReviewResult rows: {rr_count}")
print(f"ReviewIssue rows: {ri_count}")
print()

# All issues from Phase E
all_issues = db.execute("""
    SELECT rr.file_path, ri.issue_type, ri.severity, ri.description, ri.suggestion
    FROM review_issues ri
    JOIN review_results rr ON ri.review_id=rr.review_id
    WHERE rr.run_id=?
    ORDER BY rr.file_path, ri.severity DESC
""", (run_id,)).fetchall()

print(f"=== All Phase E Issues ({len(all_issues)} total) ===")
from collections import defaultdict
by_file_issues = defaultdict(list)
for ii in all_issues:
    by_file_issues[os.path.basename(ii['file_path'])].append(ii)
for fname, issues in sorted(by_file_issues.items()):
    print(f"\n{fname}:")
    for ii in issues:
        print(f"  [{ii['issue_type']}] {ii['severity']}: {ii['description'][:120]}")
        if ii['suggestion']:
            print(f"    -> {ii['suggestion'][:100]}")
print()

# Status breakdown
status_counts = defaultdict(int)
for r in rows:
    status_counts[r['status']] += 1
print("=== Status Breakdown ===")
for s, c in sorted(status_counts.items()):
    print(f"  {s}: {c}")
print()

# Group by file_path
by_file = defaultdict(list)
for r in rows:
    by_file[r['file_path']].append(r)

print("=== 15 Concern Articles ===")
for slug in slugs:
    matches = [(f, exs) for f, exs in by_file.items() if slug in f]
    if not matches:
        print(f"[MISSING] {slug}")
        continue
    for f, exs in matches:
        fname = os.path.basename(f)
        statuses = [e['status'] for e in exs]
        reasons = list(set(e['failure_reason'] for e in exs if e['failure_reason']))
        has_intent = any(e['article_intent'] for e in exs)
        all_pass = all(s in ('VERIFIED', 'FINAL_REVIEW_PASSED') for s in statuses)
        all_fail = all(s in ('COMPILE_FAILED', 'RUNTIME_FAILED', 'INFRA_BLOCKED') for s in statuses)
        verdict = 'PASS' if all_pass else ('FAIL' if all_fail else 'PARTIAL')
        print(f"[{slug}] {verdict}")
        print(f"  {fname}: {len(exs)} examples -> {statuses}")
        if reasons:
            for r in reasons:
                print(f"  FAIL: {r[:120]}")
        if has_intent:
            intent = next(e['article_intent'] for e in exs if e['article_intent'])
            print(f"  intent: {intent[:130]}")
        print()
