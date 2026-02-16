"""
One-time backfill: repair 3 production telemetry_runs rows and copy missing telemetry_events.

Root cause: copy_run_to_production() was called before complete_run() and
telemetry_events table was omitted from the copy method.

Usage:
    python scripts/backfill_prod_telemetry.py
"""
import sys
import sqlite3
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

DEV_DB = Path("data/example_reviewer.db")
PROD_DB = Path("data/example_reviewer_prod.db")
RUN_IDS = [
    "fbd06a1af34edbc0",
    "2f198808039e53d9",
    "3b1c8cc4998d4f38",
]


def backfill():
    assert DEV_DB.exists(), f"Dev DB not found: {DEV_DB}"
    assert PROD_DB.exists(), f"Prod DB not found: {PROD_DB}"

    dev_conn = sqlite3.connect(str(DEV_DB))
    dev_conn.row_factory = sqlite3.Row
    prod_conn = sqlite3.connect(str(PROD_DB))
    prod_conn.row_factory = sqlite3.Row

    total_events = 0

    for run_id in RUN_IDS:
        print(f"\nProcessing run {run_id}...")

        # 1. Fix telemetry_runs (overwrite stale row)
        row = dev_conn.execute(
            "SELECT * FROM telemetry_runs WHERE run_id = ?", (run_id,)
        ).fetchone()
        if not row:
            print(f"  SKIP: not found in dev telemetry_runs")
            continue

        placeholders = ",".join(["?" for _ in row])
        prod_conn.execute(
            f"INSERT OR REPLACE INTO telemetry_runs VALUES ({placeholders})",
            tuple(row),
        )
        print(
            f"  telemetry_runs: status={row['status']}, "
            f"duration_ms={row['duration_ms']}, "
            f"items_discovered={row['items_discovered']}, "
            f"items_succeeded={row['items_succeeded']}, "
            f"items_failed={row['items_failed']}"
        )

        # 2. Copy telemetry_events
        events = dev_conn.execute(
            "SELECT * FROM telemetry_events WHERE run_id = ?", (run_id,)
        ).fetchall()
        count = 0
        for event in events:
            placeholders = ",".join(["?" for _ in event])
            prod_conn.execute(
                f"INSERT OR IGNORE INTO telemetry_events VALUES ({placeholders})",
                tuple(event),
            )
            count += 1
        total_events += count
        print(f"  telemetry_events: copied {count} events")

    prod_conn.commit()
    prod_conn.close()
    dev_conn.close()
    print(f"\nBackfill complete: {len(RUN_IDS)} runs updated, {total_events} events copied")


if __name__ == "__main__":
    backfill()
