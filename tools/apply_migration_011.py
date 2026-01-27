#!/usr/bin/env python3
"""
Apply Migration 011: Add code_block_signature and extraction_warning columns.

This migration enables safe md_update targeting by adding signature verification.
"""

import argparse
import sqlite3
import sys
from pathlib import Path


def apply_migration_011(db_path: str, force: bool = False) -> bool:
    """
    Apply migration 011 to add code_block_signature and extraction_warning.

    Args:
        db_path: Path to SQLite database
        force: If True, ignore if columns already exist

    Returns:
        True if migration applied successfully
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(example_records)")
        columns = {row[1] for row in cursor.fetchall()}

        already_exists = []
        if 'code_block_signature' in columns:
            already_exists.append('code_block_signature')
        if 'extraction_warning' in columns:
            already_exists.append('extraction_warning')

        if already_exists and not force:
            print(f"Migration 011 already applied: columns {already_exists} exist")
            print("Use --force to reapply")
            return False

        # Apply migration
        print("Applying Migration 011...")

        if 'code_block_signature' not in columns:
            print("  Adding code_block_signature column...")
            cursor.execute(
                "ALTER TABLE example_records ADD COLUMN code_block_signature TEXT DEFAULT NULL"
            )

        if 'extraction_warning' not in columns:
            print("  Adding extraction_warning column...")
            cursor.execute(
                "ALTER TABLE example_records ADD COLUMN extraction_warning TEXT DEFAULT NULL"
            )

        # Create index if not exists
        print("  Creating signature index...")
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_example_records_signature "
            "ON example_records(code_block_signature)"
        )

        conn.commit()
        print("Migration 011 applied successfully")
        return True

    except Exception as e:
        conn.rollback()
        print(f"Error applying migration: {e}", file=sys.stderr)
        raise
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(
        description='Apply Migration 011 to add code_block_signature'
    )
    parser.add_argument(
        '--db-path',
        required=True,
        help='Path to SQLite database'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force reapply even if columns exist'
    )

    args = parser.parse_args()

    # Validate inputs
    if not Path(args.db_path).exists():
        print(f"Error: Database not found at {args.db_path}", file=sys.stderr)
        sys.exit(1)

    # Apply migration
    try:
        success = apply_migration_011(args.db_path, args.force)
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Failed to apply migration: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
