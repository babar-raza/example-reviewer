#!/usr/bin/env python3
"""
MD Update for VERIFIED Examples with Signature Verification.

This script updates markdown files with verified code, using the multi-block
safe signature-based targeting introduced in Migration 011.
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import List, Dict, Any

# Add parent directory to path to import from src
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.database import Database
from src.services.markdown_service import MarkdownUpdateService
from src.core.config import ConfigurationManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Update markdown files with VERIFIED examples using signature verification"
    )
    parser.add_argument(
        "--db-path",
        required=True,
        help="Path to SQLite database"
    )
    parser.add_argument(
        "--run-id",
        required=True,
        help="Run identifier to process VERIFIED examples from"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of examples to process"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't write changes, just show what would be updated"
    )
    parser.add_argument(
        "--allow-md-write",
        action="store_true",
        help="REQUIRED to write .md files (safety guard)"
    )
    parser.add_argument(
        "--use-workspace-copy",
        action="store_true",
        help="Write to workspace copy instead of original files"
    )
    parser.add_argument(
        "--workspace-dir",
        default=None,
        help="Workspace directory for copies (required if --use-workspace-copy)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )

    args = parser.parse_args()

    # Validate arguments
    if not Path(args.db_path).exists():
        logger.error(f"Database not found: {args.db_path}")
        sys.exit(1)

    if not args.dry_run and not args.allow_md_write:
        logger.error("--allow-md-write is required to write .md files (use --dry-run to preview)")
        sys.exit(1)

    if args.use_workspace_copy and not args.workspace_dir:
        logger.error("--workspace-dir is required when using --use-workspace-copy")
        sys.exit(1)

    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Initialize database
    db = Database(Path(args.db_path))

    # Load configuration
    config_manager = ConfigurationManager(Path("config/families"))
    global_config = config_manager.load_global_config()

    # Override markdown_write setting if --allow-md-write
    if args.allow_md_write:
        global_config.markdown_write.allow_markdown_write = True

    # Initialize MarkdownUpdateService
    md_service = MarkdownUpdateService(
        db=db,
        run_id=args.run_id,
        allow_markdown_write=args.allow_md_write,
        use_workspace_copy=args.use_workspace_copy,
        workspace_root=Path(args.workspace_dir) if args.workspace_dir else None,
        unsafe_first_block=False  # NEVER enable this - we have signatures now
    )

    # Get all VERIFIED examples for this run
    logger.info(f"Querying VERIFIED examples for run_id: {args.run_id}")

    # Query database
    with db.get_connection() as conn:
        cursor = conn.cursor()

        query = """
            SELECT DISTINCT er.file_path, er.source_type
            FROM example_run_state ers
            JOIN example_records er ON ers.example_id = er.example_id
            WHERE ers.run_id = ? AND ers.status IN ('VERIFIED', 'MD_UPDATED') AND er.source_type = 'inline'
            ORDER BY er.file_path
        """

        if args.limit:
            query += f" LIMIT {args.limit}"

        cursor.execute(query, (args.run_id,))
        rows = cursor.fetchall()

    logger.info(f"Found {len(rows)} files with VERIFIED inline examples")

    if not rows:
        logger.warning("No VERIFIED inline examples found for this run")
        print(json.dumps({
            "success": True,
            "files_processed": 0,
            "files_updated": 0,
            "examples_updated": 0,
            "errors": 0
        }, indent=2))
        return

    # Process each file
    stats = {
        "files_processed": 0,
        "files_updated": 0,
        "examples_updated": 0,
        "errors": 0,
        "files": []
    }

    for row in rows:
        file_path = row[0]
        stats["files_processed"] += 1

        logger.info(f"Processing: {file_path}")

        try:
            success, changes = md_service.update_markdown_file(
                file_path,
                dry_run=args.dry_run
            )

            if success and changes:
                stats["files_updated"] += 1
                stats["examples_updated"] += len(changes)
                stats["files"].append({
                    "path": file_path,
                    "changes": len(changes),
                    "details": changes
                })
                logger.info(f"  ✓ Updated {len(changes)} example(s)")
            elif not changes:
                logger.info(f"  - No changes needed")
            else:
                stats["errors"] += 1
                logger.error(f"  ✗ Failed to update")

        except Exception as e:
            stats["errors"] += 1
            logger.error(f"  ✗ Error: {e}")

    # Print summary
    print("\n" + "="*80)
    print("MD Update Summary")
    print("="*80)
    print(f"Run ID: {args.run_id}")
    print(f"Files processed: {stats['files_processed']}")
    print(f"Files updated: {stats['files_updated']}")
    print(f"Examples updated: {stats['examples_updated']}")
    print(f"Errors: {stats['errors']}")
    print("="*80)

    if args.dry_run:
        print("\n[DRY RUN] No files were actually modified")

    # Print detailed results
    print("\n" + json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
