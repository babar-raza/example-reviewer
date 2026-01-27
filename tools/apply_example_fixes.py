"""
Apply targeted fixes to specific examples in the database.

This tool allows applying specific code fixes to examples that have known issues,
such as missing directories, wrong API usage, etc.

Usage:
    python tools/apply_example_fixes.py --db-path <path> --run-id <run_id> --fix-id <fix_id>
"""

import argparse
import json
import logging
import sqlite3
import sys
from pathlib import Path
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


# Define fixes for specific examples
FIXES = {
    # Fix #1: Missing directory - create it in wrapper
    "1a78833310063754_missing_dir": {
        "example_id": "1a78833310063754",
        "description": "Create missing zip_folder directory",
        "fix_type": "add_directory_creation",
        "code_patch": """
        // Ensure output directory exists
        var outputDir = Path.Combine(Environment.CurrentDirectory, "zip_folder");
        if (!Directory.Exists(outputDir))
        {
            Directory.CreateDirectory(outputDir);
        }
        """,
    },

    # Additional fixes can be added here
}


def get_connection(db_path: str):
    """Get database connection."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def apply_fix(db_path: str, run_id: str, fix_id: str, dry_run: bool = True):
    """
    Apply a specific fix to an example.

    Args:
        db_path: Path to database
        run_id: Run ID
        fix_id: Fix identifier from FIXES dict
        dry_run: If True, only show what would be done
    """
    if fix_id not in FIXES:
        logger.error(f"Unknown fix_id: {fix_id}")
        logger.info(f"Available fixes: {list(FIXES.keys())}")
        return False

    fix = FIXES[fix_id]
    example_id = fix["example_id"]

    logger.info(f"{'[DRY RUN] ' if dry_run else ''}Applying fix: {fix['description']}")
    logger.info(f"Example ID: {example_id}")
    logger.info(f"Fix type: {fix['fix_type']}")

    try:
        conn = get_connection(db_path)

        # Get current example state
        row = conn.execute("""
            SELECT ers.compilable_code, er.original_code
            FROM example_run_state ers
            JOIN example_records er ON er.example_id = ers.example_id
            WHERE ers.run_id = ? AND ers.example_id = ?
        """, (run_id, example_id)).fetchone()

        if not row:
            logger.error(f"Example {example_id} not found in run {run_id}")
            conn.close()
            return False

        current_code = row['compilable_code'] or row['original_code']
        logger.info(f"Current code length: {len(current_code)} chars")

        # Apply fix based on type
        if fix['fix_type'] == "add_directory_creation":
            # Insert directory creation code at the beginning of Main
            fixed_code = apply_directory_creation_fix(current_code, fix['code_patch'])
        else:
            logger.error(f"Unknown fix type: {fix['fix_type']}")
            conn.close()
            return False

        logger.info(f"Fixed code length: {len(fixed_code)} chars")

        if not dry_run:
            # Update the database
            conn.execute("""
                UPDATE example_run_state
                SET compilable_code = ?, updated_at = ?
                WHERE run_id = ? AND example_id = ?
            """, (fixed_code, datetime.utcnow().isoformat(), run_id, example_id))
            conn.commit()
            logger.info("Fix applied successfully")
        else:
            logger.info("[DRY RUN] Would update database (use --apply to actually apply)")

        conn.close()
        return True

    except Exception as e:
        logger.error(f"Error applying fix: {e}", exc_info=True)
        return False


def apply_directory_creation_fix(code: str, patch: str) -> str:
    """
    Insert directory creation code into the Main method.

    Args:
        code: Original code
        patch: Code to insert

    Returns:
        Modified code
    """
    # Find Main method and insert after opening brace
    import re

    # Look for Main method
    main_pattern = r'(static\s+void\s+Main\s*\([^)]*\)\s*\{)'
    match = re.search(main_pattern, code)

    if not match:
        logger.warning("Could not find Main method, inserting at beginning")
        return patch + "\n\n" + code

    # Insert after the opening brace of Main
    insert_pos = match.end()
    return code[:insert_pos] + "\n" + patch + "\n" + code[insert_pos:]


def list_fixes():
    """List all available fixes."""
    print("Available Fixes:")
    print("=" * 80)
    for fix_id, fix in FIXES.items():
        print(f"\nFix ID: {fix_id}")
        print(f"  Example: {fix['example_id']}")
        print(f"  Description: {fix['description']}")
        print(f"  Type: {fix['fix_type']}")


def main():
    """Parse CLI arguments and apply fix."""
    parser = argparse.ArgumentParser(
        description="Apply targeted fixes to specific examples",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--db-path",
        type=str,
        help="Path to SQLite database"
    )

    parser.add_argument(
        "--run-id",
        type=str,
        help="Run ID"
    )

    parser.add_argument(
        "--fix-id",
        type=str,
        help="Fix identifier to apply"
    )

    parser.add_argument(
        "--list",
        action="store_true",
        help="List all available fixes"
    )

    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually apply the fix (default is dry-run)"
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if args.list:
        list_fixes()
        return 0

    if not args.db_path or not args.run_id or not args.fix_id:
        parser.print_help()
        return 1

    try:
        success = apply_fix(
            db_path=args.db_path,
            run_id=args.run_id,
            fix_id=args.fix_id,
            dry_run=not args.apply
        )
        return 0 if success else 1

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
