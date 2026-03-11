"""Query results for the 15 concern articles from the latest run."""
import sqlite3
import sys
import os
sys.stdout.reconfigure(encoding='utf-8')

db = sqlite3.connect('data/example_reviewer.db')
db.row_factory = sqlite3.Row

run_id = 'b15a9243bb11d9d0'

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

# Check review_results
rr_count = db.execute("SELECT COUNT(*) FROM review_results WHERE run_id=?", (run_id,)).fetchone()[0]
ri_count = db.execute("SELECT COUNT(*) FROM review_issues ri JOIN review_results rr ON ri.review_id=rr.review_id WHERE rr.run_id=?", (run_id,)).fetchone()[0]
print(f"ReviewResult rows for run: {rr_count}")
print(f"ReviewIssue rows for run: {ri_count}")
print()

# Get intent_mismatch / outdated_api issues
intent_issues = db.execute("""
    SELECT rr.file_path, ri.issue_type, ri.severity, ri.description
    FROM review_issues ri
    JOIN review_results rr ON ri.review_id=rr.review_id
    WHERE rr.run_id=? AND ri.issue_type IN ('intent_mismatch', 'outdated_api')
    ORDER BY rr.file_path
""", (run_id,)).fetchall()

print(f"Intent/outdated issues: {len(intent_issues)}")
for ii in intent_issues:
    fname = os.path.basename(ii['file_path'])
    print(f"  {fname}: [{ii['issue_type']}] {ii['severity']} - {ii['description'][:100]}")
print()

# Group by file_path
from collections import defaultdict
by_file = defaultdict(list)
for r in rows:
    by_file[r['file_path']].append(r)

for slug in slugs:
    matches = [(f, exs) for f, exs in by_file.items() if slug in f]
    if not matches:
        print(f"[MISSING] {slug} - no examples discovered")
        continue
    for f, exs in matches:
        fname = os.path.basename(f)
        statuses = [e['status'] for e in exs]
        reasons = list(set(e['failure_reason'] for e in exs if e['failure_reason']))
        has_intent = any(e['article_intent'] for e in exs)
        all_pass = all(s in ('VERIFIED', 'FINAL_REVIEW_PASSED') for s in statuses)
        any_fail = any(s in ('COMPILE_FAILED', 'RUNTIME_FAILED', 'INFRA_BLOCKED', 'NEEDS_REVIEW') for s in statuses)
        verdict = 'PASS' if all_pass else ('PARTIAL' if not all([s in ('COMPILE_FAILED','RUNTIME_FAILED','INFRA_BLOCKED') for s in statuses]) else 'FAIL')
        print(f"[{slug}] {verdict}")
        print(f"  file: {fname}")
        print(f"  examples: {len(exs)}  statuses: {statuses}")
        if reasons:
            print(f"  failure_reasons: {reasons}")
        print(f"  has_intent: {has_intent}")
        if has_intent:
            intent = next(e['article_intent'] for e in exs if e['article_intent'])
            print(f"  intent: {intent[:150]}")
        print()
