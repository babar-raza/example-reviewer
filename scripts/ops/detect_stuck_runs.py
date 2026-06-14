#!/usr/bin/env python3
"""
Stuck-Run Detector — TC-11
Detects pipeline runs older than a threshold that are still in
non-terminal status. Optionally marks them as failed.
"""

import json
import sqlite3
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_DB = REPO_ROOT / "data" / "example_reviewer.db"
DEFAULT_THRESHOLD_HOURS = 2


def detect_stuck_runs(
    db_path: Path,
    threshold_hours: float = DEFAULT_THRESHOLD_HOURS,
) -> list:
    """Find runs stuck in non-terminal status."""
    if not db_path.exists():
        return []

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    cutoff = (datetime.now(timezone.utc) - timedelta(hours=threshold_hours)).isoformat()

    rows = conn.execute("""
        SELECT run_id, family, started_at, status, current_phase
        FROM run_records
        WHERE status IN ('running', 'pending')
          AND started_at < ?
    """, (cutoff,)).fetchall()
    conn.close()

    return [dict(r) for r in rows]


def fix_stuck_runs(db_path: Path, stuck_runs: list) -> int:
    """Mark stuck runs as failed."""
    if not stuck_runs:
        return 0

    conn = sqlite3.connect(str(db_path))
    now = datetime.now(timezone.utc).isoformat()
    fixed = 0
    for run in stuck_runs:
        conn.execute("""
            UPDATE run_records
            SET status = 'failed',
                completed_at = ?,
                error = 'Marked as failed by stuck-run detector (exceeded timeout)'
            WHERE run_id = ? AND status IN ('running', 'pending')
        """, (now, run["run_id"]))
        fixed += 1

    conn.commit()
    conn.close()
    return fixed


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Detect stuck pipeline runs")
    parser.add_argument("--db-path", type=Path, default=DEFAULT_DB)
    parser.add_argument("--threshold-hours", type=float, default=DEFAULT_THRESHOLD_HOURS)
    parser.add_argument("--fix", action="store_true", help="Mark stuck runs as failed")
    parser.add_argument("--dry-run", action="store_true", help="Report without modifying")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    stuck = detect_stuck_runs(args.db_path, args.threshold_hours)

    if args.json:
        print(json.dumps({"stuck_runs": stuck, "count": len(stuck)}, indent=2))
    else:
        if not stuck:
            print("No stuck runs detected.")
            return 0

        print(f"Found {len(stuck)} stuck run(s):\n")
        for run in stuck:
            print(f"  {run['run_id']} | {run['family']} | started: {run['started_at']} | status: {run['status']}")

    if stuck and args.fix and not args.dry_run:
        fixed = fix_stuck_runs(args.db_path, stuck)
        print(f"\nFixed {fixed} stuck run(s).")
    elif stuck and args.fix and args.dry_run:
        print(f"\n[DRY RUN] Would fix {len(stuck)} stuck run(s).")

    return 1 if stuck else 0


if __name__ == "__main__":
    sys.exit(main())
