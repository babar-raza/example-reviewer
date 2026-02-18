#!/usr/bin/env python3
"""
Promote Global Patterns -- One-time cross-family pattern promotion.

Identifies patterns that should be shared across families (global scope)
and promotes them, retiring family-specific duplicates.

Criteria for global promotion:
- code_transform patterns using generic transformers (fix_stream_disposal, etc.)
- using_directive patterns for System.* namespaces (BCL)
- Duplicate global patterns across families are consolidated

Usage:
    python scripts/promote_global_patterns.py              # Dry run (default)
    python scripts/promote_global_patterns.py --commit     # Actually promote
"""

import json
import logging
import re
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent
CATALOG_DB = PROJECT_ROOT / "data" / "api_catalog.db"

# Generic transformers that work across all families
GENERIC_TRANSFORMERS = {
    "fix_stream_disposal",
    "fix_placeholder_dirs",
    "fix_placeholder_passwords",
}


def promote_global(commit: bool = False) -> dict:
    """Identify and promote patterns to global scope.

    Returns:
        Summary dict with promotion counts.
    """
    if not CATALOG_DB.exists():
        logger.error(f"Database not found: {CATALOG_DB}")
        return {}

    conn = sqlite3.connect(str(CATALOG_DB))
    conn.row_factory = sqlite3.Row

    # Check if scope column exists
    cols = [row[1] for row in conn.execute("PRAGMA table_info(learned_patterns)").fetchall()]
    if "scope" not in cols:
        logger.error("'scope' column not found in learned_patterns. Run schema migration first.")
        conn.close()
        return {}

    # Fetch all active patterns
    rows = conn.execute(
        """SELECT id, family, error_signature, fix_type, fix_code, scope,
                  confidence, source
           FROM learned_patterns
           WHERE (source IS NULL OR source NOT LIKE 'retired_%')"""
    ).fetchall()

    promoted = 0
    consolidated = 0
    actions = []  # (action, pattern_id, reason)

    # --- Pass 1: Promote generic code_transform patterns ---
    for row in rows:
        if row["fix_type"] != "code_transform" or row["scope"] == "global":
            continue
        fix_code = json.loads(row["fix_code"]) if row["fix_code"] else {}
        transformer = fix_code.get("transformer", "")
        if transformer in GENERIC_TRANSFORMERS:
            actions.append(("promote", row["id"], f"generic transformer: {transformer}"))
            promoted += 1

    # --- Pass 2: Promote System.* using_directive patterns ---
    for row in rows:
        if row["fix_type"] != "using_directive" or row["scope"] == "global":
            continue
        fix_code = json.loads(row["fix_code"]) if row["fix_code"] else {}
        directive = fix_code.get("directive", "")
        if directive.startswith("using System"):
            actions.append(("promote", row["id"], f"BCL namespace: {directive}"))
            promoted += 1

    # --- Pass 3: Consolidate duplicate globals ---
    # After promotion, find patterns with identical (error_sig, fix_type, fix_code)
    # across families and keep only one as global, retire the rest
    global_candidates = defaultdict(list)
    for row in rows:
        if row["fix_type"] in ("template",):
            continue
        fix_code_norm = ""
        if row["fix_code"]:
            try:
                fix_code_norm = json.dumps(json.loads(row["fix_code"]), sort_keys=True)
            except json.JSONDecodeError:
                continue
        key = (row["error_signature"], row["fix_type"], fix_code_norm)
        global_candidates[key].append(dict(row))

    for key, members in global_candidates.items():
        if len(members) < 2:
            continue
        # Check if members span multiple families
        families = {m["family"] for m in members}
        if len(families) < 2:
            continue

        # Keep the first one (will be promoted to global), retire others
        keeper = members[0]
        # Check if keeper is already in our promote list
        promoted_ids = {a[1] for a in actions if a[0] == "promote"}
        if keeper["id"] not in promoted_ids:
            actions.append(("promote", keeper["id"], f"cross-family consolidation ({len(families)} families)"))
            promoted += 1

        for dup in members[1:]:
            if dup["id"] not in promoted_ids:
                actions.append(("retire", dup["id"], f"consolidated into global pattern {keeper['id']}"))
                consolidated += 1

    # Apply actions
    if commit and actions:
        for action, pid, reason in actions:
            if action == "promote":
                conn.execute(
                    """UPDATE learned_patterns
                       SET scope = 'global', updated_at = datetime('now')
                       WHERE id = ?""",
                    (pid,),
                )
                logger.info(f"  Promoted pattern {pid} to global: {reason}")
            elif action == "retire":
                conn.execute(
                    """UPDATE learned_patterns
                       SET auto_approved = FALSE,
                           source = 'retired_promoted_to_global',
                           updated_at = datetime('now')
                       WHERE id = ?""",
                    (pid,),
                )
                logger.debug(f"  Retired pattern {pid}: {reason}")
        conn.commit()
        logger.info(f"Committed: {promoted} promoted, {consolidated} consolidated")
    elif actions:
        logger.info(f"DRY RUN: would promote {promoted}, consolidate {consolidated}")
        for action, pid, reason in actions[:20]:
            logger.info(f"  [{action}] pattern {pid}: {reason}")
        if len(actions) > 20:
            logger.info(f"  ... and {len(actions) - 20} more actions")

    conn.close()

    logger.info(f"\n{'='*60}")
    logger.info(f"GLOBAL PROMOTION SUMMARY")
    logger.info(f"{'='*60}")
    logger.info(f"Patterns promoted to global: {promoted}")
    logger.info(f"Duplicates consolidated:     {consolidated}")

    return {
        "promoted": promoted,
        "consolidated": consolidated,
        "total_actions": len(actions),
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Promote patterns to global scope")
    parser.add_argument("--commit", action="store_true", help="Actually apply changes (default: dry run)")
    args = parser.parse_args()

    result = promote_global(commit=args.commit)
    if not args.commit and result.get("total_actions", 0) > 0:
        logger.info("\nRun with --commit to apply changes")
