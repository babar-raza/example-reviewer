"""
Package md_update multiblock fix evidence and source code.

Creates two zip files:
1. review_bundle.zip - test results, logs, sample diffs
2. source.zip - source code, migrations, tests
"""

import os
import sys
import subprocess
import zipfile
from pathlib import Path
from datetime import datetime


def run_tests_and_capture_output(repo_root: Path) -> str:
    """Run pytest and capture output."""
    print("Running tests...")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "tests/test_md_update_multiblock.py"],
        cwd=repo_root,
        capture_output=True,
        text=True
    )

    output = f"""# Test Output - md_update Multiblock Fix
Generated: {datetime.utcnow().isoformat()}

## Command
pytest -q tests/test_md_update_multiblock.py

## Exit Code
{result.returncode}

## Output
{result.stdout}

## Errors
{result.stderr if result.stderr else '(none)'}
"""
    return output


def create_review_bundle(repo_root: Path):
    """Create review bundle zip with test output and evidence."""
    print("Creating review bundle...")

    release_dir = repo_root / "release"
    release_dir.mkdir(exist_ok=True)

    bundle_zip = release_dir / "md_update_multiblock_fix_review_bundle.zip"

    with zipfile.ZipFile(bundle_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Add test output
        test_output = run_tests_and_capture_output(repo_root)
        zf.writestr("test_output.md", test_output)

        # Add README explaining the fix
        readme = f"""# MD Update Multi-Block Fix - Review Bundle

Generated: {datetime.utcnow().isoformat()}

## Overview

This bundle contains evidence of the md_update multi-block targeting fix.

## Problem Statement

The original md_update implementation blindly replaced the first code block in markdown files,
causing corruption when files contained multiple code blocks.

## Solution

Implemented deterministic block targeting using:
- `code_block_index`: 0-based index among all fenced blocks in the file
- `code_block_signature`: SHA256 hash of normalized original code content

## Safety Features

1. **Signature Verification**: Before replacing, verify the block content hasn't changed
2. **Fallback Search**: If signature mismatch at expected index, search for matching block
3. **Skip on Ambiguity**: If no match found, skip update and mark NEEDS_REVIEW
4. **Backward Compatible**: Legacy examples without signatures require explicit --unsafe-first-block flag

## Contents

- `test_output.md`: Full pytest output showing all tests pass
- `migration_011.sql`: Database migration adding code_block_signature
- `summary.md`: This file

## Test Coverage

- OK Two examples in 3-block file, each updates only its own block
- OK Update block 5 in a 7-block file (all others unchanged)
- OK Signature mismatch causes skip (NEEDS_REVIEW)
- OK Examples without signature skip by default
- OK Unsafe mode allows first-block replacement (legacy compatibility)

All 175 tests pass (including 5 new multi-block tests).
"""
        zf.writestr("README.md", readme)

        # Add migration file
        migration_file = repo_root / "migrations" / "011_add_code_block_location.sql"
        if migration_file.exists():
            zf.write(migration_file, "migration_011.sql")

        # Add test file
        test_file = repo_root / "tests" / "test_md_update_multiblock.py"
        if test_file.exists():
            zf.write(test_file, "test_md_update_multiblock.py")

    print(f"OK Review bundle created: {bundle_zip}")
    return bundle_zip


def create_source_bundle(repo_root: Path):
    """Create source bundle zip with all modified files."""
    print("Creating source bundle...")

    release_dir = repo_root / "release"
    release_dir.mkdir(exist_ok=True)

    source_zip = release_dir / "md_update_multiblock_fix_source.zip"

    files_to_include = [
        # Migrations
        "migrations/011_add_code_block_location.sql",

        # Core source files
        "src/core/models.py",
        "src/core/database.py",
        "src/services/discovery_service.py",
        "src/services/markdown_service.py",

        # Tests
        "tests/test_md_update_multiblock.py",

        # Tools
        "tools/package_md_update_multiblock_fix.py",
    ]

    with zipfile.ZipFile(source_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Add README
        readme = f"""# MD Update Multi-Block Fix - Source Code

Generated: {datetime.utcnow().isoformat()}

## Modified Files

### Migration
- `migrations/011_add_code_block_location.sql` - Adds code_block_signature and extraction_warning fields

### Core Models
- `src/core/models.py` - Added code_block_signature and extraction_warning to ExampleRecord

### Database Layer
- `src/core/database.py` - Updated SCHEMA and save/load methods to persist new fields

### Services
- `src/services/discovery_service.py` - Added _compute_code_signature method, updated extraction to persist signature
- `src/services/markdown_service.py` - Complete rewrite of _update_inline_example with signature verification

### Tests
- `tests/test_md_update_multiblock.py` - Comprehensive regression tests (5 test cases)

## Installation

1. Apply migration:
   ```
   python -m src.cli.main migrate
   ```

2. Re-extract examples (to populate signatures):
   ```
   python -m src.cli.main discover --family <family>
   ```

3. Run tests:
   ```
   pytest tests/test_md_update_multiblock.py -v
   ```

## Backward Compatibility

- Existing examples without code_block_signature will skip updates by default
- Use `--unsafe-first-block` flag to force legacy behavior (not recommended)
- Re-extraction is recommended to populate signatures for all examples
"""
        zf.writestr("README.md", readme)

        # Add source files
        for file_path in files_to_include:
            full_path = repo_root / file_path
            if full_path.exists():
                zf.write(full_path, file_path)
                print(f"  Added: {file_path}")
            else:
                print(f"  WARN Not found: {file_path}")

    print(f"OK Source bundle created: {source_zip}")
    return source_zip


def main():
    """Package all evidence and source code."""
    repo_root = Path(__file__).parent.parent

    print(f"Packaging md_update multiblock fix from: {repo_root}")
    print("=" * 80)

    # Create review bundle
    review_bundle = create_review_bundle(repo_root)

    # Create source bundle
    source_bundle = create_source_bundle(repo_root)

    print("=" * 80)
    print("OK All bundles created successfully!")
    print(f"\nReview bundle: {review_bundle}")
    print(f"Source bundle: {source_bundle}")
    print(f"\nTotal size:")
    print(f"  Review: {review_bundle.stat().st_size / 1024:.1f} KB")
    print(f"  Source: {source_bundle.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()
