#!/usr/bin/env python3
"""
Gate 4: Safety Verification Tool - No Markdown Changes

Verify no markdown files were modified (safety check).

Requirements (from Plan v2.1):
- Run `git status --porcelain` and parse output
- Check for any .md files with status M (modified)
- Exit code 0 if clean, 1 if .md files modified
- Print list of modified .md files (if any)
- Accept optional --allow-paths argument to whitelist certain paths (e.g., reports/)

Usage:
    python tools/verify_no_md_changes.py
    python tools/verify_no_md_changes.py --allow-paths reports/,docs/
"""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import List, Set


def parse_porcelain_line(line: str) -> tuple[str, str]:
    """
    Parse a git status --porcelain line.

    Format: XY filename
    Where X is index status, Y is working tree status

    Returns: (status, filepath)
    """
    if len(line) < 3:
        return "", ""

    status = line[:2]
    filepath = line[3:].strip()

    # Handle renames (format: "R  old -> new")
    if ' -> ' in filepath:
        filepath = filepath.split(' -> ')[1]

    return status, filepath


def get_modified_files() -> List[tuple[str, str]]:
    """
    Get list of modified files from git status.

    Returns list of (status, filepath) tuples.
    """
    try:
        result = subprocess.run(
            ['git', 'status', '--porcelain'],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode != 0:
            print(f"ERROR: git status failed: {result.stderr}", file=sys.stderr)
            sys.exit(1)

        modified_files = []
        for line in result.stdout.strip().split('\n'):
            if not line:
                continue

            status, filepath = parse_porcelain_line(line)
            if status:
                modified_files.append((status, filepath))

        return modified_files

    except FileNotFoundError:
        print("ERROR: git command not found", file=sys.stderr)
        sys.exit(1)
    except subprocess.TimeoutExpired:
        print("ERROR: git status timed out", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Failed to run git status: {e}", file=sys.stderr)
        sys.exit(1)


def is_path_allowed(filepath: str, allowed_prefixes: Set[str]) -> bool:
    """
    Check if filepath starts with any allowed prefix.

    Args:
        filepath: Path to check
        allowed_prefixes: Set of allowed path prefixes (e.g., {'reports/', 'docs/'})

    Returns:
        True if filepath is in an allowed directory
    """
    if not allowed_prefixes:
        return False

    # Normalize path separators
    normalized = filepath.replace('\\', '/')

    for prefix in allowed_prefixes:
        if normalized.startswith(prefix):
            return True

    return False


def verify_no_md_changes(allowed_paths: List[str] = None) -> int:
    """
    Verify no markdown files were modified outside allowed paths.

    Returns 0 if clean, 1 if .md files modified.
    """
    print("Safety Verification: No Markdown Changes")
    print("="*60)

    # Parse allowed paths
    allowed_prefixes = set()
    if allowed_paths:
        for path in allowed_paths:
            # Normalize to use forward slashes and ensure trailing slash
            normalized = path.replace('\\', '/').rstrip('/') + '/'
            allowed_prefixes.add(normalized)

        print(f"Allowed paths: {', '.join(sorted(allowed_prefixes))}")
    else:
        print("No paths are allowed (strict mode)")

    print()

    # Get modified files
    modified_files = get_modified_files()

    if not modified_files:
        print("PASS: No files modified")
        print("="*60)
        return 0

    # Filter for .md files
    modified_md_files = []
    allowed_md_files = []

    for status, filepath in modified_files:
        if filepath.endswith('.md'):
            # Check if modified (M) or added (A) in index or working tree
            # Status format: XY where X=index, Y=working tree
            # M = modified, A = added, D = deleted, R = renamed, etc.
            is_modified = 'M' in status or 'A' in status

            if is_modified:
                if is_path_allowed(filepath, allowed_prefixes):
                    allowed_md_files.append((status, filepath))
                else:
                    modified_md_files.append((status, filepath))

    # Report results
    if allowed_md_files:
        print(f"Allowed .md changes ({len(allowed_md_files)} files):")
        for status, filepath in sorted(allowed_md_files):
            print(f"  [{status}] {filepath}")
        print()

    if modified_md_files:
        print(f"X FAIL: Forbidden .md files modified ({len(modified_md_files)} files):")
        for status, filepath in sorted(modified_md_files):
            print(f"  [{status}] {filepath}")
        print("\n" + "="*60)
        print("Markdown files were modified outside allowed paths!")
        print("This violates the safety contract.")
        print("="*60)
        return 1

    print("PASS: No forbidden markdown changes")
    print("="*60)
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Verify no markdown files were modified (safety gate)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Strict mode - no changes allowed
  python tools/verify_no_md_changes.py

  # Allow changes in reports/ and docs/
  python tools/verify_no_md_changes.py --allow-paths reports/,docs/

  # Allow changes in specific subdirectories
  python tools/verify_no_md_changes.py --allow-paths "reports/track1/,plans/"

Git status codes:
  M  - Modified
  A  - Added
  D  - Deleted
  R  - Renamed
  ?? - Untracked (ignored by this tool)
        """
    )

    parser.add_argument(
        '--allow-paths',
        type=str,
        default='',
        help='Comma-separated list of allowed path prefixes (e.g., "reports/,docs/")'
    )

    args = parser.parse_args()

    # Parse allowed paths
    allowed_paths = []
    if args.allow_paths:
        allowed_paths = [p.strip() for p in args.allow_paths.split(',') if p.strip()]

    exit_code = verify_no_md_changes(allowed_paths)
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
