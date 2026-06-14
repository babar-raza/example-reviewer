#!/usr/bin/env python3
"""
Schedule-Based Work Enqueue — TC-07
Queries run_records for families whose last successful run is older
than N days, and enqueues them into the work_queue table.
"""

import json
import sqlite3
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_DB = REPO_ROOT / "data" / "example_reviewer.db"
DEFAULT_STALE_DAYS = 7


def find_stale_families(
    db_path: Path,
    stale_days: int = DEFAULT_STALE_DAYS,
) -> list:
    """Find families whose last successful run is older than stale_days."""
    if not db_path.exists():
        print(f"WARNING: Database not found at {db_path}")
        return []

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    cutoff = (datetime.now(timezone.utc) - timedelta(days=stale_days)).isoformat()

    # Get all known families from run_records
    rows = conn.execute("""
        SELECT family,
               MAX(CASE WHEN status IN ('completed', 'success') THEN started_at END) as last_success,
               MAX(started_at) as last_run
        FROM run_records
        GROUP BY family
    """).fetchall()

    # Also get configured families from family configs
    config_dir = REPO_ROOT / "config" / "families"
    configured_families = set()
    if config_dir.exists():
        for f in config_dir.glob("*.json"):
            name = f.stem
            if not any(suffix in name for suffix in [
                "_api_catalog", "_behavioral_patterns", "_review_hints"
            ]):
                configured_families.add(name)

    stale = []
    seen_families = set()

    for row in rows:
        family = row["family"]
        seen_families.add(family)
        last_success = row["last_success"]

        if last_success is None or last_success < cutoff:
            stale.append({
                "family": family,
                "last_success": last_success,
                "last_run": row["last_run"],
                "reason": "no_successful_run" if last_success is None else "stale",
            })

    # Families that have configs but no runs at all
    for fam in configured_families - seen_families:
        stale.append({
            "family": fam,
            "last_success": None,
            "last_run": None,
            "reason": "never_run",
        })

    conn.close()
    return stale


def enqueue_stale_families(
    db_path: Path,
    stale_families: list,
    priority: int = 5,
    max_examples: int = None,
    skip_llm: bool = False,
    dry_run: bool = False,
) -> int:
    """Enqueue stale families into the work queue."""
    if dry_run:
        for fam in stale_families:
            print(f"  [DRY RUN] Would enqueue: {fam['family']} (reason: {fam['reason']})")
        return 0

    # Import database module for enqueue
    sys.path.insert(0, str(REPO_ROOT))
    from src.core.database import Database

    db = Database(db_path=db_path)
    enqueued = 0

    for fam in stale_families:
        try:
            qid = db.enqueue_work(
                family=fam["family"],
                trigger_source="scheduled",
                priority=priority,
                max_examples=max_examples,
                skip_llm=skip_llm,
            )
            print(f"  Enqueued: {fam['family']} -> {qid} (reason: {fam['reason']})")
            enqueued += 1
        except Exception as e:
            print(f"  ERROR enqueueing {fam['family']}: {e}")

    return enqueued


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Enqueue stale families for processing")
    parser.add_argument("--db-path", type=Path, default=DEFAULT_DB)
    parser.add_argument("--stale-days", type=int, default=DEFAULT_STALE_DAYS)
    parser.add_argument("--priority", type=int, default=5)
    parser.add_argument("--max-examples", type=int, default=None)
    parser.add_argument("--skip-llm", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    stale = find_stale_families(args.db_path, args.stale_days)

    if args.json:
        print(json.dumps({"stale_families": stale, "count": len(stale)}, indent=2))
        return 0

    if not stale:
        print(f"No families are stale (threshold: {args.stale_days} days).")
        return 0

    print(f"Found {len(stale)} stale/never-run families:\n")
    enqueued = enqueue_stale_families(
        args.db_path, stale,
        priority=args.priority,
        max_examples=args.max_examples,
        skip_llm=args.skip_llm,
        dry_run=args.dry_run,
    )

    if args.dry_run:
        print(f"\n[DRY RUN] Would enqueue {len(stale)} families.")
    else:
        print(f"\nEnqueued {enqueued} families.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
