#!/usr/bin/env python3
"""
Documentation Link Checker — DC-02
Validates that all relative markdown links in documentation files
resolve to existing files. Detects broken internal links before
they reach main.

Usage:
    python scripts/validation/check_doc_links.py
    python scripts/validation/check_doc_links.py --changed-only
"""

import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# Directories to scan for markdown files
SCAN_ROOTS = [
    REPO_ROOT / "docs",
    REPO_ROOT / "evals",
    REPO_ROOT / "reports",
]

# Root-level markdown files to scan
ROOT_MD_FILES = list(REPO_ROOT.glob("*.md"))

# Pattern to match markdown links: [text](path) or [text](path#anchor)
# Excludes URLs (http://, https://, mailto:)
LINK_PATTERN = re.compile(
    r'\[([^\]]*)\]\(([^)]+)\)'
)


def is_relative_link(target: str) -> bool:
    """Check if a link target is a relative path (not a URL or anchor-only)."""
    if target.startswith(("http://", "https://", "mailto:", "#")):
        return False
    return True


def extract_links(file_path: Path) -> list:
    """Extract all relative markdown links from a file.

    Returns list of (line_number, link_text, link_target) tuples.
    """
    links = []
    try:
        content = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return links

    for i, line in enumerate(content.splitlines(), start=1):
        for match in LINK_PATTERN.finditer(line):
            text = match.group(1)
            target = match.group(2)
            # Strip anchor from target for file existence check
            if is_relative_link(target):
                links.append((i, text, target))
    return links


def resolve_link(source_file: Path, target: str) -> Path:
    """Resolve a relative link target to an absolute path."""
    # Strip anchor
    file_target = target.split("#")[0]
    if not file_target:
        # Anchor-only link within the same file
        return source_file

    # Strip line-range suffixes like :75-80 or :42
    file_target = re.sub(r':\d+(-\d+)?$', '', file_target)

    # Resolve relative to the source file's directory
    resolved = (source_file.parent / file_target).resolve()
    return resolved


def get_changed_files() -> set:
    """Get set of changed .md files from git diff against HEAD."""
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            capture_output=True, text=True, cwd=REPO_ROOT
        )
        staged = subprocess.run(
            ["git", "diff", "--name-only", "--cached"],
            capture_output=True, text=True, cwd=REPO_ROOT
        )
        files = set()
        for line in (result.stdout + staged.stdout).strip().splitlines():
            if line.endswith(".md"):
                files.add((REPO_ROOT / line).resolve())
        return files
    except (subprocess.SubprocessError, OSError):
        return set()


def collect_md_files(changed_only: bool = False) -> list:
    """Collect all markdown files to scan."""
    if changed_only:
        return sorted(get_changed_files())

    files = set()

    # Root-level markdown files
    for f in ROOT_MD_FILES:
        files.add(f.resolve())

    # Files in scan roots
    # _strays_inbox/ is a quarantine area for unreviewed external Markdown files
    # (moved there by git mv). Those files contain links to external APIs that
    # cannot resolve within the repo. Skip them here; they are not governed docs.
    SKIP_DIR_NAMES = {"_strays_inbox"}
    for root in SCAN_ROOTS:
        if root.exists():
            for f in root.rglob("*.md"):
                if not any(part in SKIP_DIR_NAMES for part in f.relative_to(root).parts):
                    files.add(f.resolve())

    # Component READMEs in src/, scripts/, config/, migrations/, archive/
    for subdir in ["src", "scripts", "config", "migrations", "archive"]:
        sub_path = REPO_ROOT / subdir
        if sub_path.exists():
            for f in sub_path.rglob("*.md"):
                files.add(f.resolve())

    # tests/ top-level README only (exclude fixtures — external test data)
    tests_readme = REPO_ROOT / "tests" / "README.md"
    if tests_readme.exists():
        files.add(tests_readme.resolve())

    return sorted(files)


def main():
    changed_only = "--changed-only" in sys.argv

    md_files = collect_md_files(changed_only=changed_only)

    if not md_files:
        if changed_only:
            print("No changed .md files to check.")
            return 0
        print("WARNING: No markdown files found to check")
        return 1

    total_links = 0
    broken_links = []

    for md_file in md_files:
        links = extract_links(md_file)
        for line_num, text, target in links:
            total_links += 1
            resolved = resolve_link(md_file, target)
            if not resolved.exists():
                rel_source = md_file.relative_to(REPO_ROOT)
                broken_links.append(
                    f"  {rel_source}:{line_num}: "
                    f"broken link [{text}]({target})"
                )

    # Print results
    mode = " (changed files only)" if changed_only else ""
    print(f"Checked {total_links} links in {len(md_files)} files{mode}")

    if broken_links:
        print(f"\nFOUND {len(broken_links)} BROKEN LINK(S):\n")
        for link in broken_links:
            print(link)
        return 1
    else:
        print("All links validated successfully.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
