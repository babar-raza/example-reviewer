#!/usr/bin/env python3
"""
Cross-Run Trend Analysis — TC-13
Compares the last N runs for a family and reports:
- Verification rate trend
- New/resolved failure signatures
- Pattern effectiveness
"""

import json
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_DB = REPO_ROOT / "data" / "example_reviewer.db"


def get_recent_runs(db_path: Path, family: str, limit: int = 5) -> list:
    """Get the most recent completed runs for a family."""
    if not db_path.exists():
        return []

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT run_id, started_at, completed_at, status,
               examples_processed, examples_successful, examples_failed
        FROM run_records
        WHERE family = ? AND status IN ('completed', 'success', 'failed', 'interrupted')
        ORDER BY started_at DESC
        LIMIT ?
    """, (family, limit)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_run_stats(db_path: Path, run_id: str) -> dict:
    """Get detailed stats for a specific run."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    # Status distribution
    statuses = conn.execute("""
        SELECT status, COUNT(*) as cnt
        FROM example_run_state
        WHERE run_id = ?
        GROUP BY status
    """, (run_id,)).fetchall()

    # Failure categories
    failures = conn.execute("""
        SELECT failure_category, error_category, COUNT(*) as cnt
        FROM failure_details
        WHERE run_id = ?
        GROUP BY failure_category, error_category
        ORDER BY cnt DESC
    """, (run_id,)).fetchall()

    conn.close()

    status_dist = {row["status"]: row["cnt"] for row in statuses}
    failure_dist = [
        {"category": row["failure_category"], "error": row["error_category"], "count": row["cnt"]}
        for row in failures
    ]

    total = sum(status_dist.values())
    verified = sum(v for k, v in status_dist.items()
                   if k in ("VERIFIED", "MD_UPDATED", "FINAL_REVIEW_PASSED", "COMMITTED"))

    return {
        "total": total,
        "verified": verified,
        "verification_rate": round((verified / total) * 100, 1) if total > 0 else 0.0,
        "status_distribution": status_dist,
        "failure_distribution": failure_dist,
    }


def analyze_trends(db_path: Path, family: str, last_n: int = 5) -> dict:
    """Perform cross-run trend analysis."""
    runs = get_recent_runs(db_path, family, last_n)
    if not runs:
        return {"family": family, "runs_found": 0, "trends": []}

    run_details = []
    for run in runs:
        stats = get_run_stats(db_path, run["run_id"])
        run_details.append({
            "run_id": run["run_id"],
            "started_at": run["started_at"],
            "status": run["status"],
            **stats,
        })

    # Compute verification rate trend
    rates = [r["verification_rate"] for r in run_details if r["total"] > 0]
    trend_direction = "stable"
    if len(rates) >= 2:
        if rates[0] > rates[-1] + 5:
            trend_direction = "improving"
        elif rates[0] < rates[-1] - 5:
            trend_direction = "declining"

    # Find recurring failure signatures
    all_failures = {}
    for rd in run_details:
        for f in rd["failure_distribution"]:
            key = f"{f['category']}:{f['error']}"
            if key not in all_failures:
                all_failures[key] = 0
            all_failures[key] += 1

    recurring = [
        {"signature": k, "occurrences_in_runs": v}
        for k, v in all_failures.items()
        if v >= 2
    ]
    recurring.sort(key=lambda x: x["occurrences_in_runs"], reverse=True)

    return {
        "family": family,
        "runs_found": len(runs),
        "runs": run_details,
        "verification_rate_trend": {
            "direction": trend_direction,
            "latest": rates[0] if rates else None,
            "oldest": rates[-1] if rates else None,
            "all_rates": rates,
        },
        "recurring_failures": recurring[:10],
    }


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Cross-run trend analysis")
    parser.add_argument("--family", required=True)
    parser.add_argument("--db-path", type=Path, default=DEFAULT_DB)
    parser.add_argument("--last-n", type=int, default=5)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = analyze_trends(args.db_path, args.family, args.last_n)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Family: {result['family']}")
        print(f"Runs found: {result['runs_found']}")
        if result["runs_found"] > 0:
            trend = result["verification_rate_trend"]
            print(f"Verification rate trend: {trend['direction']}")
            print(f"  Latest: {trend['latest']}%  Oldest: {trend['oldest']}%")
            if result["recurring_failures"]:
                print(f"\nRecurring failures:")
                for rf in result["recurring_failures"]:
                    print(f"  {rf['signature']}: {rf['occurrences_in_runs']} runs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
