#!/usr/bin/env python3
"""
Deduplicate Learned Patterns — One-time cleanup migration.

Groups patterns by (family, error_signature, fix_type) and retires duplicates,
keeping the one with the highest times_applied (ties: highest confidence).

Usage:
    python scripts/deduplicate_patterns.py              # Dry run (default)
    python scripts/deduplicate_patterns.py --commit     # Actually retire duplicates
"""

import json
import logging
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent
CATALOG_DB = PROJECT_ROOT / "data" / "api_catalog.db"


def deduplicate(commit: bool = False) -> dict:
    """Find and retire duplicate patterns.

    Returns:
        Summary dict with before/after counts per family.
    """
    if not CATALOG_DB.exists():
        logger.error(f"Database not found: {CATALOG_DB}")
        return {}

    conn = sqlite3.connect(str(CATALOG_DB))
    conn.row_factory = sqlite3.Row

    # Fetch all active patterns with performance data
    rows = conn.execute(
        """SELECT lp.id, lp.family, lp.error_signature, lp.fix_type,
                  lp.fix_code, lp.confidence, lp.source,
                  COALESCE(pp.times_applied, 0) as times_applied,
                  COALESCE(pp.times_succeeded, 0) as times_succeeded
           FROM learned_patterns lp
           LEFT JOIN pattern_performance pp ON lp.id = pp.pattern_id
           WHERE lp.source IS NULL OR lp.source NOT LIKE 'retired_%'
           ORDER BY lp.family, lp.error_signature, lp.fix_type"""
    ).fetchall()

    # Group by (family, error_signature, fix_type)
    groups = defaultdict(list)
    for row in rows:
        key = (row["family"], row["error_signature"], row["fix_type"])
        groups[key].append(dict(row))

    total_before = len(rows)
    retired_count = 0
    retired_ids = []
    family_stats = defaultdict(lambda: {"before": 0, "after": 0, "retired": 0})

    for key, members in groups.items():
        family = key[0]
        family_stats[family]["before"] += len(members)

        if len(members) <= 1:
            family_stats[family]["after"] += len(members)
            continue

        # Sort: highest times_applied first, then highest confidence
        members.sort(key=lambda m: (m["times_applied"], m["confidence"]), reverse=True)

        # Keep the best one, retire the rest
        keeper = members[0]
        family_stats[family]["after"] += 1

        for dup in members[1:]:
            retired_ids.append(dup["id"])
            retired_count += 1
            family_stats[family]["retired"] += 1
            logger.debug(
                f"  Retire pattern {dup['id']} ({key[1]}/{key[2]}) "
                f"in {family} -- kept {keeper['id']} "
                f"(applied={keeper['times_applied']} vs {dup['times_applied']})"
            )

    # Apply retirements
    if commit and retired_ids:
        for pid in retired_ids:
            conn.execute(
                """UPDATE learned_patterns
                   SET auto_approved = FALSE,
                       source = 'retired_duplicate',
                       updated_at = datetime('now')
                   WHERE id = ?""",
                (pid,),
            )
        conn.commit()
        logger.info(f"Committed: retired {retired_count} duplicate patterns")
    elif retired_ids:
        logger.info(f"DRY RUN: would retire {retired_count} duplicate patterns")

    conn.close()

    # Report
    total_after = total_before - retired_count
    logger.info(f"\n{'='*60}")
    logger.info(f"DEDUPLICATION SUMMARY")
    logger.info(f"{'='*60}")
    logger.info(f"Total patterns before: {total_before}")
    logger.info(f"Total patterns after:  {total_after}")
    logger.info(f"Duplicates retired:    {retired_count}")
    logger.info(f"")
    logger.info(f"{'Family':<15} {'Before':>8} {'After':>8} {'Retired':>8}")
    logger.info(f"{'-'*15} {'-'*8} {'-'*8} {'-'*8}")
    for family in sorted(family_stats):
        s = family_stats[family]
        logger.info(f"{family:<15} {s['before']:>8} {s['after']:>8} {s['retired']:>8}")

    return {
        "total_before": total_before,
        "total_after": total_after,
        "retired_count": retired_count,
        "family_stats": dict(family_stats),
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Deduplicate learned patterns")
    parser.add_argument("--commit", action="store_true", help="Actually retire duplicates (default: dry run)")
    args = parser.parse_args()

    result = deduplicate(commit=args.commit)
    if not args.commit and result.get("retired_count", 0) > 0:
        logger.info("\nRun with --commit to apply changes")
