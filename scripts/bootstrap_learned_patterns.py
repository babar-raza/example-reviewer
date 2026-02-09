#!/usr/bin/env python3
"""
Bootstrap Learned Patterns — Seed executable fix patterns into the learned_patterns table.

Seeds data/api_catalog.db with known-good, executable patterns for compile-error
auto-fixing (using directives, regex replacements, etc.).

Idempotent: checks for existing (error_signature, fix_type, fix_code) triples
before inserting.  Supports --clean to remove stale template-only auto_learn rows,
--dry-run to preview without writing, and --family to scope to a product family.

Usage:
    python scripts/bootstrap_learned_patterns.py --family zip
    python scripts/bootstrap_learned_patterns.py --family zip --clean
    python scripts/bootstrap_learned_patterns.py --family zip --dry-run

Task T2-WIRE-002: Bootstrap Script for Executable Learned Patterns
"""

import argparse
import json
import logging
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "api_catalog.db"

# ---------------------------------------------------------------------------
# Pattern definitions
# ---------------------------------------------------------------------------

BOOTSTRAP_PATTERNS = [
    # --- CS0246: missing using directives ---
    {
        "error_signature": "CS0246",
        "pattern_type": "compile_error",
        "fix_type": "using_directive",
        "fix_code": {"directive": "using Aspose.Zip;", "trigger_type": "Archive"},
        "fix_template": "Add 'using Aspose.Zip;' when Archive type is unresolved",
    },
    {
        "error_signature": "CS0246",
        "pattern_type": "compile_error",
        "fix_type": "using_directive",
        "fix_code": {"directive": "using Aspose.Zip.SevenZip;", "trigger_type": "SevenZipArchive"},
        "fix_template": "Add 'using Aspose.Zip.SevenZip;' when SevenZipArchive type is unresolved",
    },
    {
        "error_signature": "CS0246",
        "pattern_type": "compile_error",
        "fix_type": "using_directive",
        "fix_code": {"directive": "using Aspose.Zip.Rar;", "trigger_type": "RarArchive"},
        "fix_template": "Add 'using Aspose.Zip.Rar;' when RarArchive type is unresolved",
    },
    {
        "error_signature": "CS0246",
        "pattern_type": "compile_error",
        "fix_type": "using_directive",
        "fix_code": {"directive": "using Aspose.Zip.Gzip;", "trigger_type": "GzipArchive"},
        "fix_template": "Add 'using Aspose.Zip.Gzip;' when GzipArchive type is unresolved",
    },
    {
        "error_signature": "CS0246",
        "pattern_type": "compile_error",
        "fix_type": "using_directive",
        "fix_code": {"directive": "using Aspose.Zip.Tar;", "trigger_type": "TarArchive"},
        "fix_template": "Add 'using Aspose.Zip.Tar;' when TarArchive type is unresolved",
    },
    {
        "error_signature": "CS0246",
        "pattern_type": "compile_error",
        "fix_type": "using_directive",
        "fix_code": {"directive": "using Aspose.Zip.Saving;", "trigger_type": "ArchiveEntrySettings"},
        "fix_template": "Add 'using Aspose.Zip.Saving;' when ArchiveEntrySettings type is unresolved",
    },
    # --- CS0117: wrong enum member names ---
    {
        "error_signature": "CS0117",
        "pattern_type": "compile_error",
        "fix_type": "regex_replace",
        "fix_code": {"pattern": "CompressionLevel\\.Normal", "replacement": "CompressionLevel.Optimal"},
        "fix_template": "Replace CompressionLevel.Normal with CompressionLevel.Optimal",
    },
    {
        "error_signature": "CS0117",
        "pattern_type": "compile_error",
        "fix_type": "regex_replace",
        "fix_code": {"pattern": "CompressionLevel\\.Low", "replacement": "CompressionLevel.Fastest"},
        "fix_template": "Replace CompressionLevel.Low with CompressionLevel.Fastest",
    },
    {
        "error_signature": "CS0117",
        "pattern_type": "compile_error",
        "fix_type": "regex_replace",
        "fix_code": {"pattern": "CompressionLevel\\.High", "replacement": "CompressionLevel.SmallestSize"},
        "fix_template": "Replace CompressionLevel.High with CompressionLevel.SmallestSize",
    },
    # --- CS1061: async API mismatch ---
    {
        "error_signature": "CS1061",
        "pattern_type": "compile_error",
        "fix_type": "regex_replace",
        "fix_code": {"pattern": "await\\s+(\\w+)\\.SaveAsync\\s*\\(", "replacement": "\\1.Save("},
        "fix_template": "Replace await obj.SaveAsync( with obj.Save( — API is synchronous",
    },
]

# Default confidence and approval status for bootstrap patterns
BOOTSTRAP_CONFIDENCE = 0.9
BOOTSTRAP_AUTO_APPROVED = True
BOOTSTRAP_SOURCE = "bootstrap"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def pattern_exists(conn: sqlite3.Connection, family: str, error_signature: str,
                   fix_type: str, fix_code_json: str) -> bool:
    """Check whether a pattern with the same (error_signature, fix_type, fix_code) already exists."""
    row = conn.execute(
        """
        SELECT COUNT(*) FROM learned_patterns
        WHERE family = ?
          AND error_signature = ?
          AND fix_type = ?
          AND fix_code = ?
        """,
        (family, error_signature, fix_type, fix_code_json),
    ).fetchone()
    return row[0] > 0


def clean_stale_templates(conn: sqlite3.Connection, family: str, dry_run: bool = False) -> int:
    """Remove template-only patterns that came from auto_learn (stale placeholders)."""
    rows = conn.execute(
        """
        SELECT id, error_signature, fix_template FROM learned_patterns
        WHERE family = ?
          AND fix_code IS NULL
          AND source = 'auto_learn'
        """,
        (family,),
    ).fetchall()

    if not rows:
        logger.info("No stale template-only auto_learn patterns found.")
        return 0

    for row in rows:
        pid, sig, tmpl = row
        logger.info(f"  {'[DRY] ' if dry_run else ''}Cleaning stale pattern id={pid}  "
                     f"sig={sig}  template='{tmpl}'")

    if not dry_run:
        # Also clean up associated pattern_performance rows
        ids = [r[0] for r in rows]
        placeholders = ",".join("?" * len(ids))
        conn.execute(f"DELETE FROM pattern_performance WHERE pattern_id IN ({placeholders})", ids)
        conn.execute(
            f"DELETE FROM learned_patterns WHERE id IN ({placeholders})", ids
        )
        conn.commit()

    logger.info(f"{'[DRY] ' if dry_run else ''}Cleaned {len(rows)} stale template-only pattern(s).")
    return len(rows)


def insert_pattern(conn: sqlite3.Connection, family: str, pat: dict,
                   dry_run: bool = False) -> int:
    """Insert a single pattern and its performance row.  Returns the new id, or -1 for dry run."""
    fix_code_json = json.dumps(pat["fix_code"])

    if pattern_exists(conn, family, pat["error_signature"], pat["fix_type"], fix_code_json):
        return 0  # sentinel: already exists

    if dry_run:
        return -1  # sentinel: would insert

    cursor = conn.execute(
        """
        INSERT INTO learned_patterns
        (family, pattern_type, error_signature, fix_template, fix_type, fix_code,
         confidence, auto_approved, priority, requires_llm, source)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            family,
            pat["pattern_type"],
            pat["error_signature"],
            pat["fix_template"],
            pat["fix_type"],
            fix_code_json,
            BOOTSTRAP_CONFIDENCE,
            BOOTSTRAP_AUTO_APPROVED,
            50,   # default priority
            False,
            BOOTSTRAP_SOURCE,
        ),
    )
    pattern_id = cursor.lastrowid

    # Initialize pattern_performance row
    conn.execute(
        """
        INSERT INTO pattern_performance (pattern_id, family)
        VALUES (?, ?)
        """,
        (pattern_id, family),
    )

    return pattern_id


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Bootstrap executable learned patterns into api_catalog.db"
    )
    parser.add_argument("--family", default="zip",
                        help="Product family to bootstrap (default: zip)")
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH),
                        help="Path to api_catalog.db")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview what would happen without writing")
    parser.add_argument("--clean", action="store_true",
                        help="Remove stale template-only auto_learn patterns first")
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        logger.error(f"Database not found: {db_path}")
        sys.exit(1)

    family = args.family
    dry_run = args.dry_run
    label = "[DRY RUN] " if dry_run else ""

    logger.info(f"{label}Bootstrap learned patterns for family='{family}'")
    logger.info(f"Database: {db_path}")

    conn = sqlite3.connect(str(db_path))

    # ── Optional clean step ──────────────────────────────────────────────
    cleaned = 0
    if args.clean:
        logger.info(f"\n{label}Cleaning stale template-only patterns...")
        cleaned = clean_stale_templates(conn, family, dry_run=dry_run)

    # ── Insert executable patterns ───────────────────────────────────────
    inserted = 0
    skipped = 0
    inserted_ids = []

    for pat in BOOTSTRAP_PATTERNS:
        result = insert_pattern(conn, family, pat, dry_run=dry_run)
        sig = pat["error_signature"]
        ft = pat["fix_type"]
        desc = pat["fix_template"]

        if result == 0:
            skipped += 1
            logger.info(f"  SKIP (exists)  {sig} / {ft}: {desc}")
        elif result == -1:
            inserted += 1
            logger.info(f"  {label}INSERT  {sig} / {ft}: {desc}")
        else:
            inserted += 1
            inserted_ids.append(result)
            logger.info(f"  INSERT id={result}  {sig} / {ft}: {desc}")

    if not dry_run and inserted > 0:
        conn.commit()

    conn.close()

    # ── Summary ──────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"{label}Bootstrap Summary for family='{family}'")
    print(f"{'='*60}")
    print(f"  Patterns defined : {len(BOOTSTRAP_PATTERNS)}")
    print(f"  Inserted         : {inserted}")
    print(f"  Skipped (exists) : {skipped}")
    if args.clean:
        print(f"  Cleaned (stale)  : {cleaned}")
    if inserted_ids:
        print(f"  New IDs          : {inserted_ids}")
    print(f"{'='*60}")

    if dry_run:
        print(f"\n{label}No changes were written to the database.")


if __name__ == "__main__":
    main()
