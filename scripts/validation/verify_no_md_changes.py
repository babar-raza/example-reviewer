"""
Verify No Markdown Changes Outside Allowed Paths.

This tool verifies that no markdown files (.md) have been modified outside
the allowed paths (specs/, reports/, docs/, plans/) using git to detect changes.

Usage:
    python tools/verify_no_md_changes.py
    python tools/verify_no_md_changes.py --allow-paths specs/,reports/,docs/,plans/

Exit Codes:
    0 - No violations found (clean)
    1 - Violations found (markdown changes outside allowed paths)
    2 - Error (git not available or other failure)

Hard Rules:
    - NO markdown changes outside: specs/, reports/, docs/, plans/
    - Uses git to detect modifications
    - Works on Windows
"""

import argparse
import logging
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple


def setup_logging(verbose: bool = False) -> None:
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - [%(levelname)s] %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )


def get_git_status() -> Tuple[bool, str]:
    """
    Get git status output.

    Returns:
        Tuple of (success: bool, output: str)
    """
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        return result.returncode == 0, result.stdout

    except FileNotFoundError:
        return False, "ERROR: git command not found"
    except Exception as e:
        return False, f"ERROR: {str(e)}"


def get_modified_md_files(git_output: str) -> List[str]:
    """
    Parse git status output to find modified .md files.

    Args:
        git_output: Output from 'git status --porcelain'

    Returns:
        List of modified .md file paths
    """
    modified_files = []

    for line in git_output.strip().split('\n'):
        if not line:
            continue

        # Git status format: "XY filename"
        # X = status in index, Y = status in working tree
        # M = modified, A = added, D = deleted, R = renamed, etc.
        status = line[:2].strip()
        filepath = line[3:].strip()

        # Check if it's a markdown file
        if filepath.endswith('.md'):
            modified_files.append(filepath)

    return modified_files


def check_violations(
    modified_files: List[str],
    allowed_paths: List[str]
) -> Tuple[List[str], List[str]]:
    """
    Check for violations (markdown files modified outside allowed paths).

    Args:
        modified_files: List of modified .md files
        allowed_paths: List of allowed path prefixes (e.g., ['specs/', 'reports/'])

    Returns:
        Tuple of (violations: List[str], allowed: List[str])
    """
    violations = []
    allowed = []

    for filepath in modified_files:
        # Normalize path separators for Windows
        normalized_path = filepath.replace('\\', '/')

        # Check if file is in any allowed path
        is_allowed = any(
            normalized_path.startswith(path)
            for path in allowed_paths
        )

        if is_allowed:
            allowed.append(filepath)
        else:
            violations.append(filepath)

    return violations, allowed


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Verify no markdown changes outside allowed paths',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument('--allow-paths', type=str,
                        default='specs/,reports/,docs/,plans/',
                        help='Comma-separated list of allowed path prefixes (default: specs/,reports/,docs/,plans/)')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Verbose output')

    args = parser.parse_args()

    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    # Parse allowed paths
    allowed_paths = [p.strip() for p in args.allow_paths.split(',') if p.strip()]

    logger.info("Markdown Change Verification")
    logger.info("=" * 80)
    logger.info(f"Allowed paths: {', '.join(allowed_paths)}")
    logger.info("")

    # Get git status
    success, git_output = get_git_status()

    if not success:
        logger.error(git_output)
        return 2

    # Get modified markdown files
    modified_files = get_modified_md_files(git_output)

    if not modified_files:
        logger.info("No markdown files modified.")
        logger.info("")
        logger.info("[OK] CLEAN - No markdown changes detected")
        return 0

    logger.info(f"Found {len(modified_files)} modified markdown file(s)")
    logger.debug(f"Modified files: {modified_files}")
    logger.info("")

    # Check for violations
    violations, allowed = check_violations(modified_files, allowed_paths)

    # Report allowed changes
    if allowed:
        logger.info("Allowed markdown changes:")
        for filepath in allowed:
            logger.info(f"  [OK] {filepath}")
        logger.info("")

    # Report violations
    if violations:
        logger.error("VIOLATIONS - Markdown files modified outside allowed paths:")
        for filepath in violations:
            logger.error(f"  [VIOLATION] {filepath}")
        logger.info("")
        logger.error("[FAIL] Found markdown changes outside allowed paths")
        logger.error(f"Allowed paths: {', '.join(allowed_paths)}")
        return 1

    logger.info("[OK] CLEAN - All markdown changes are in allowed paths")
    return 0


if __name__ == '__main__':
    sys.exit(main())
