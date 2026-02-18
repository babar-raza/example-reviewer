#!/usr/bin/env python3
"""
Build Test Data Inventory Tool

Generates an inventory JSON file with tags for all test data files.
Tags help the LLM select appropriate test files during runtime validation.

Usage:
    python tools/build_test_data_inventory.py --family zip
"""

import argparse
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.config import ConfigurationManager
from src.pipeline.orchestrator import resolve_test_data_path


def infer_tags(file_path: Path, size: int) -> List[str]:
    """
    Infer tags for a file based on its properties.

    Args:
        file_path: Path to the file
        size: File size in bytes

    Returns:
        List of tags
    """
    tags = []
    name = file_path.name.lower()
    suffix = file_path.suffix.lower()

    # Archive format tags
    archive_formats = {
        '.zip': 'zip',
        '.rar': 'rar',
        '.7z': '7z',
        '.gz': 'gz',
        '.tar': 'tar',
        '.bz2': 'bzip2',
        '.xz': 'xz',
        '.z': 'compress',
        '.arj': 'arj',
        '.cab': 'cab',
        '.iso': 'iso',
        '.lha': 'lha',
        '.lz': 'lzip',
        '.lz4': 'lz4',
        '.lzma': 'lzma',
        '.lzx': 'lzx',
        '.wim': 'wim',
        '.xar': 'xar',
        '.zst': 'zstd',
    }

    if suffix in archive_formats:
        tags.append(archive_formats[suffix])
        tags.append('archive')

    # Encryption/password tags
    if 'encrypt' in name or 'password' in name or 'protected' in name:
        tags.append('encrypted')
        tags.append('password')

    # Nested archive tag
    if 'nested' in name or 'outer' in name or 'inner' in name:
        tags.append('nested')

    # Multi-volume tag
    if 'multi' in name or 'volume' in name or 'split' in name:
        tags.append('multi_volume')

    # Text corpus tag (large text files)
    text_extensions = {'.txt', '.html', '.c', '.lsp', '.xls', '.1'}
    if suffix in text_extensions:
        tags.append('text')
        if size > 50000:  # >50KB text files
            tags.append('text_corpus')

    # Directory tag
    if file_path.is_dir():
        tags.append('directory')
        tags.append('dir_sample')

    # Binary tag
    if suffix == '.bin' or (suffix not in text_extensions and size > 0):
        if 'archive' not in tags and not file_path.is_dir():
            tags.append('binary')

    # Empty file tag
    if size == 0:
        tags.append('empty')

    # Specific test scenarios
    if 'flatten' in name:
        tags.append('flatten')
    if 'different' in name:
        tags.append('different_password')

    return tags


def build_inventory(test_data_path: Path, family: str) -> Dict[str, Any]:
    """
    Build inventory of test data files.

    Args:
        test_data_path: Path to test data directory
        family: Family identifier

    Returns:
        Inventory dictionary
    """
    entries = []

    # Iterate through all files and directories
    for item in sorted(test_data_path.rglob('*'), key=lambda p: str(p).lower()):
        try:
            # Get file info
            if item.is_file():
                size = item.stat().st_size
                kind = 'file'

                # Calculate SHA256 for files
                if size > 0 and size < 10 * 1024 * 1024:  # Only hash files <10MB
                    sha256 = hashlib.sha256(item.read_bytes()).hexdigest()
                else:
                    sha256 = None
            elif item.is_dir():
                size = 0
                sha256 = None
                kind = 'directory'
            else:
                continue  # Skip symlinks, etc.

            # Calculate relative path
            relative_path = item.relative_to(test_data_path)

            # Infer tags
            tags = infer_tags(item, size)

            # Add entry
            entry = {
                'path': str(relative_path).replace('\\', '/'),
                'size_bytes': size,
                'sha256': sha256,
                'ext': item.suffix.lower() if item.suffix else None,
                'kind': kind,
                'tags': tags,
            }
            entries.append(entry)

        except Exception as e:
            print(f"Warning: Failed to process {item}: {e}", file=sys.stderr)

    # Build inventory
    inventory = {
        'family': family,
        'source_path': str(test_data_path),
        'generated_at': datetime.now().isoformat(),
        'total_items': len(entries),
        'entries': entries,
    }

    # Add tag summary
    tag_counts = {}
    for entry in entries:
        for tag in entry['tags']:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1

    inventory['tag_summary'] = dict(sorted(tag_counts.items(), key=lambda x: x[1], reverse=True))

    return inventory


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Build test data inventory with tags')
    parser.add_argument('--family', '-f', required=True, help='Family identifier')
    parser.add_argument('--output', '-o', help='Output path (default: artifacts/backfill/<family>/test-data-inventory.json)')
    args = parser.parse_args()

    # Load config
    config_manager = ConfigurationManager(Path('config/families'))
    family_config = config_manager.load_family_config(args.family)

    # Resolve test data path
    test_data_path = resolve_test_data_path(args.family, family_config)

    if not test_data_path:
        print(f"Error: No test data found for family '{args.family}'", file=sys.stderr)
        print("Run backfill first: python -m src.cli.main backfill --family <family> --targets test_data", file=sys.stderr)
        return 1

    if not test_data_path.exists():
        print(f"Error: Test data path does not exist: {test_data_path}", file=sys.stderr)
        return 1

    print(f"Building inventory for family '{args.family}'")
    print(f"Test data path: {test_data_path}")

    # Build inventory
    inventory = build_inventory(test_data_path, args.family)

    # Determine output path
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = Path(f"artifacts/backfill/{args.family}/test-data-inventory.json")

    # Create output directory
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write inventory
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(inventory, f, indent=2)

    print(f"\nInventory written to: {output_path}")
    print(f"Total items: {inventory['total_items']}")
    print(f"\nTop tags:")
    for tag, count in list(inventory['tag_summary'].items())[:10]:
        print(f"  {tag}: {count}")

    return 0


if __name__ == '__main__':
    sys.exit(main())
