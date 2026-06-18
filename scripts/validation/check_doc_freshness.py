#!/usr/bin/env python3
"""
Documentation Freshness Checker — DC-08
Reports documentation files that have not been updated within a
configurable threshold. Advisory — helps identify docs that may
be drifting from the codebase.

Usage:
    python scripts/validation/check_doc_freshness.py
    python scripts/validation/check_doc_freshness.py --max-age-days 90
"""

import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# Directories to check for freshness
DOC_ROOTS = [
    REPO_ROOT / "docs",
]

# Skip directories where staleness is expected/acceptable
SKIP_DIRS = {"adr", "internal"}

DEFAULT_MAX_AGE_DAYS = 180


def get_last_modified(file_path: Path) -> datetime | None:
    """Get the last commit date for a file via git log."""
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%aI", "--", str(file_path)],
            capture_output=True, text=True, cwd=REPO_ROOT
        )
        date_str = result.stdout.strip()
        if not date_str:
            return None
        return datetime.fromisoformat(date_str)
    except (subprocess.SubprocessError, ValueError):
        return None


def collect_doc_files() -> list:
    """Collect documentation files to check."""
    files = []
    for root in DOC_ROOTS:
        if not root.exists():
            continue
        for f in root.rglob("*.md"):
            # Skip directories in SKIP_DIRS
            rel = f.relative_to(root)
            if rel.parts and rel.parts[0] in SKIP_DIRS:
                continue
            files.append(f)
    return sorted(files)


def main():
    max_age_days = DEFAULT_MAX_AGE_DAYS

    # Parse --max-age-days argument
    args = sys.argv[1:]
    for i, arg in enumerate(args):
        if arg == "--max-age-days" and i + 1 < len(args):
            try:
                max_age_days = int(args[i + 1])
            except ValueError:
                print(f"Invalid --max-age-days value: {args[i + 1]}")
                return 2

    doc_files = collect_doc_files()
    if not doc_files:
        print("No documentation files found to check.")
        return 0

    now = datetime.now(timezone.utc)
    stale_files = []

    for doc_file in doc_files:
        last_modified = get_last_modified(doc_file)
        if last_modified is None:
            continue  # Untracked file, skip

        # Ensure timezone-aware comparison
        if last_modified.tzinfo is None:
            last_modified = last_modified.replace(tzinfo=timezone.utc)

        age_days = (now - last_modified).days
        if age_days > max_age_days:
            rel_path = doc_file.relative_to(REPO_ROOT)
            stale_files.append((rel_path, age_days, last_modified))

    print(f"Checked {len(doc_files)} docs (threshold: {max_age_days} days)")

    if stale_files:
        print(f"\nFOUND {len(stale_files)} STALE DOCUMENT(S):\n")
        for rel_path, age, last_mod in sorted(stale_files, key=lambda x: -x[1]):
            print(f"  {rel_path}: {age} days old (last modified: {last_mod.date()})")
        return 1
    else:
        print("All documents are within freshness threshold.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
