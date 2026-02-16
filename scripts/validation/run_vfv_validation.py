#!/usr/bin/env python
"""
VFV Validation Script - Tests auto-learn system across 3 families.

Runs each family twice to demonstrate Run 1 → Run 2 learning improvement:
- ZIP: High baseline (many manual fixes)
- Words: Medium baseline (some manual fixes)
- OCR: Zero baseline (new family)
"""

import subprocess
import sys
import sqlite3
from pathlib import Path
from datetime import datetime

# Configure UTF-8 output for Windows
sys.stdout.reconfigure(encoding='utf-8')

def run_pipeline(family: str, max_examples: int, run_num: int):
    """Run the VFV pipeline for a family."""
    print(f"\n{'='*80}")
    print(f">> {family.upper()} - Run {run_num} ({datetime.now().strftime('%H:%M:%S')})")
    print(f"{'='*80}\n")

    cmd = [
        sys.executable, "-m", "src.cli.main", "run",
        "--family", family,
        "--max-examples", str(max_examples),
        "--enable-all-deterministic",
        "--skip-llm-runtime-fixes",
        "--allow-md-write"
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    # Extract key metrics from output
    for line in result.stdout.split('\n'):
        if any(x in line for x in ['Phase', 'FINAL_REVIEW_PASSED', 'verified', 'compiled_first_try', 'auto-learn']):
            print(line)

    if result.returncode != 0:
        print(f"\n[WARN] Run failed with code {result.returncode}")
        if result.stderr:
            print("Error:", result.stderr[-500:])
    else:
        print(f"\n[OK] Run completed successfully")

    return result.returncode == 0

def get_run_stats(family: str):
    """Get statistics for the most recent run."""
    db_path = Path("data/example_reviewer.db")
    if not db_path.exists():
        return None

    conn = sqlite3.connect(str(db_path))
    cursor = conn.execute("""
        SELECT r.run_id, r.started_at,
               COUNT(CASE WHEN ers.status='FINAL_REVIEW_PASSED' THEN 1 END) as verified,
               COUNT(CASE WHEN ers.status='COMPILE_FAILED' THEN 1 END) as compile_failed,
               COUNT(CASE WHEN ers.status='RUNTIME_FAILED' THEN 1 END) as runtime_failed,
               COUNT(*) as total
        FROM run_records r
        JOIN example_run_state ers ON r.run_id = ers.run_id
        WHERE r.family = ?
        GROUP BY r.run_id
        ORDER BY r.started_at DESC
        LIMIT 1
    """, (family,))

    row = cursor.fetchone()
    conn.close()

    if row:
        return {
            'run_id': row[0][:8],
            'timestamp': row[1][:19],
            'verified': row[2],
            'compile_failed': row[3],
            'runtime_failed': row[4],
            'total': row[5],
            'success_rate': f"{(row[2]/row[5]*100):.1f}%" if row[5] > 0 else "0%"
        }
    return None

def compare_runs(family: str):
    """Compare Run 1 vs Run 2 for a family."""
    print(f"\n{'='*80}")
    print(f"[ANALYSIS] {family.upper()} - Learning Analysis")
    print(f"{'='*80}\n")

    conn = sqlite3.connect("data/example_reviewer.db")
    cursor = conn.execute("""
        SELECT r.run_id, r.started_at,
               COUNT(CASE WHEN ers.status='FINAL_REVIEW_PASSED' THEN 1 END) as verified,
               COUNT(*) as total
        FROM run_records r
        JOIN example_run_state ers ON r.run_id = ers.run_id
        WHERE r.family = ?
        GROUP BY r.run_id
        ORDER BY r.started_at DESC
        LIMIT 2
    """, (family,))

    rows = cursor.fetchall()
    conn.close()

    if len(rows) >= 2:
        run2 = rows[0]
        run1 = rows[1]

        run1_verified = run1[2]
        run1_total = run1[3]
        run1_rate = (run1_verified / run1_total * 100) if run1_total > 0 else 0

        run2_verified = run2[2]
        run2_total = run2[3]
        run2_rate = (run2_verified / run2_total * 100) if run2_total > 0 else 0

        improvement = run2_verified - run1_verified
        rate_delta = run2_rate - run1_rate

        print(f"Run 1: {run1_verified}/{run1_total} verified ({run1_rate:.1f}%)")
        print(f"Run 2: {run2_verified}/{run2_total} verified ({run2_rate:.1f}%)")
        print(f"\n{'[OK] IMPROVEMENT' if improvement > 0 else '[WARN]  NO CHANGE' if improvement == 0 else '[FAIL] REGRESSION'}: {improvement:+d} examples ({rate_delta:+.1f}%)")

        return improvement
    else:
        print(f"[WARN] Need 2 runs for comparison (found {len(rows)})")
        return 0

def main():
    """Run VFV validation across all three families."""
    families = [
        ("zip", 20),    # High baseline
        ("words", 20),  # Medium baseline
        ("ocr", 20)     # Zero baseline
    ]

    results = {}

    for family, max_ex in families:
        # Run 1: Baseline
        run_pipeline(family, max_ex, 1)
        stats1 = get_run_stats(family)
        if stats1:
            print(f"\n[STATS] Run 1 Results: {stats1['verified']}/{stats1['total']} verified ({stats1['success_rate']})")

        # Run 2: With learned patterns
        run_pipeline(family, max_ex, 2)
        stats2 = get_run_stats(family)
        if stats2:
            print(f"\n[STATS] Run 2 Results: {stats2['verified']}/{stats2['total']} verified ({stats2['success_rate']})")

        # Analysis
        improvement = compare_runs(family)
        results[family] = improvement

    # Final Summary
    print(f"\n{'='*80}")
    print(f"[FINAL] FINAL VALIDATION RESULTS")
    print(f"{'='*80}\n")

    for family, improvement in results.items():
        status = "[OK] PASS" if improvement > 0 else "[WARN]  NEUTRAL" if improvement == 0 else "[FAIL] FAIL"
        print(f"{family.upper():8s}: {status} ({improvement:+d} examples improved)")

    total_improvement = sum(results.values())
    print(f"\n{'='*80}")
    print(f"Total Examples Improved: {total_improvement:+d}")
    print(f"Auto-Learn System: {'[OK] WORKING' if total_improvement > 0 else '[FAIL] NOT WORKING'}")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    main()
