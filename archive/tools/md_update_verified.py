#!/usr/bin/env python3
"""
Standalone MD Update for VERIFIED Examples.

This script updates markdown files with verified code for a specific set of examples.
Designed for evaluation workflows where you want to update only VERIFIED examples.
"""

import argparse
import json
import logging
import re
import sqlite3
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional


logger = logging.getLogger(__name__)


class MarkdownUpdater:
    """Updates markdown files with verified code."""

    def __init__(self, dry_run: bool = False, verbose: bool = False):
        self.dry_run = dry_run
        self.verbose = verbose
        self.stats = {
            'processed': 0,
            'updated': 0,
            'skipped': 0,
            'errors': 0
        }

    def update_code_block(
        self,
        md_content: str,
        verified_code: str,
        snippet_id: str = ""
    ) -> tuple[str, bool]:
        """
        Update a code block in markdown content.

        Args:
            md_content: Original markdown content
            verified_code: Verified code to insert
            snippet_id: Optional anchor/identifier for the code block

        Returns:
            Tuple of (updated_content, was_updated)
        """
        # Find C# code blocks
        pattern = r'```(?:csharp|cs|c#)\s*\n(.*?)```'
        matches = list(re.finditer(pattern, md_content, re.DOTALL | re.IGNORECASE))

        if not matches:
            logger.warning("No C# code blocks found in markdown")
            return md_content, False

        if len(matches) == 1:
            # Single code block - replace it
            match = matches[0]
            original_code = match.group(1)

            # Build replacement
            updated_content = (
                md_content[:match.start()] +
                f"```csharp\n{verified_code}\n```" +
                md_content[match.end():]
            )

            if self.verbose:
                logger.debug(f"Replaced single code block ({len(original_code)} -> {len(verified_code)} chars)")

            return updated_content, True

        else:
            # Multiple code blocks - need snippet_id or heuristic
            logger.warning(f"Multiple code blocks ({len(matches)}) found, using first one")
            # TODO: Could implement more sophisticated matching based on snippet_id or content similarity
            match = matches[0]
            updated_content = (
                md_content[:match.start()] +
                f"```csharp\n{verified_code}\n```" +
                md_content[match.end():]
            )
            return updated_content, True

    def update_markdown_file(
        self,
        file_path: str,
        verified_code: str,
        snippet_id: str = ""
    ) -> bool:
        """
        Update a markdown file with verified code.

        Args:
            file_path: Path to markdown file
            verified_code: Verified code to insert
            snippet_id: Optional snippet identifier

        Returns:
            True if file was updated, False otherwise
        """
        md_file = Path(file_path)

        if not md_file.exists():
            logger.error(f"Markdown file not found: {file_path}")
            return False

        try:
            # Read original content
            with open(md_file, 'r', encoding='utf-8') as f:
                original_content = f.read()

            # Update code block
            updated_content, was_updated = self.update_code_block(
                original_content,
                verified_code,
                snippet_id
            )

            if not was_updated:
                logger.warning(f"No changes made to {file_path}")
                return False

            # Write updated content (unless dry-run)
            if self.dry_run:
                logger.info(f"[DRY-RUN] Would update {file_path}")
                logger.debug(f"[DRY-RUN] Content length: {len(original_content)} -> {len(updated_content)}")
            else:
                with open(md_file, 'w', encoding='utf-8') as f:
                    f.write(updated_content)
                logger.info(f"Updated {file_path}")

            return True

        except Exception as e:
            logger.error(f"Error updating {file_path}: {e}")
            return False

    def process_verified_examples(
        self,
        examples: List[Dict[str, Any]],
        limit: Optional[int] = None
    ) -> Dict[str, int]:
        """
        Process verified examples and update markdown files.

        Args:
            examples: List of verified example dictionaries
            limit: Optional limit on number of examples to process

        Returns:
            Statistics dictionary
        """
        examples_to_process = examples[:limit] if limit else examples

        logger.info(f"Processing {len(examples_to_process)} VERIFIED examples")

        for idx, example in enumerate(examples_to_process, 1):
            example_id = example.get('example_id', 'unknown')
            file_path = example.get('file_path', '')
            verified_code = example.get('verified_code_ref', '')
            snippet_id = example.get('snippet_id', '')

            logger.info(f"\n[{idx}/{len(examples_to_process)}] Processing {example_id}")
            logger.debug(f"  File: {file_path}")

            if not verified_code:
                logger.warning(f"  No verified code for {example_id}, skipping")
                self.stats['skipped'] += 1
                continue

            if not file_path:
                logger.warning(f"  No file path for {example_id}, skipping")
                self.stats['skipped'] += 1
                continue

            # Update markdown file
            try:
                success = self.update_markdown_file(
                    file_path,
                    verified_code,
                    snippet_id
                )

                self.stats['processed'] += 1
                if success:
                    self.stats['updated'] += 1
                else:
                    self.stats['skipped'] += 1

            except Exception as e:
                logger.error(f"  Error processing {example_id}: {e}")
                self.stats['errors'] += 1

        return self.stats


def load_verified_examples(json_path: str) -> List[Dict[str, Any]]:
    """Load verified examples from JSON file."""
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def main():
    parser = argparse.ArgumentParser(
        description="Update markdown files with verified code from VERIFIED examples"
    )
    parser.add_argument(
        '--input',
        required=True,
        help='Path to verified_examples.json'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Limit number of examples to process'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help="Don't write changes, just show what would be updated"
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose output'
    )

    args = parser.parse_args()

    # Setup logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    # Load examples
    try:
        examples = load_verified_examples(args.input)
        logger.info(f"Loaded {len(examples)} VERIFIED examples from {args.input}")
    except Exception as e:
        logger.error(f"Failed to load examples: {e}")
        sys.exit(1)

    # Process examples
    updater = MarkdownUpdater(dry_run=args.dry_run, verbose=args.verbose)
    stats = updater.process_verified_examples(examples, limit=args.limit)

    # Print summary
    print("\n" + "=" * 80)
    print("MD UPDATE SUMMARY")
    print("=" * 80)
    print(f"Processed:  {stats['processed']}")
    print(f"Updated:    {stats['updated']}")
    print(f"Skipped:    {stats['skipped']}")
    print(f"Errors:     {stats['errors']}")
    print("=" * 80)

    if args.dry_run:
        print("\nDRY-RUN MODE: No files were actually modified")

    sys.exit(0 if stats['errors'] == 0 else 1)


if __name__ == "__main__":
    main()
