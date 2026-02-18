#!/usr/bin/env python3
"""Create Phase 3 release package."""

import zipfile
from pathlib import Path

def create_phase3_package():
    """Create release package for Phase 3 implementation."""

    # Define base directory
    base_dir = Path(__file__).parent
    release_dir = base_dir / "release"
    release_dir.mkdir(exist_ok=True)

    # Define output file
    output_file = release_dir / "app_context_phase3_source.zip"

    # Define files to include
    files_to_include = [
        "src/pipeline/context_drift_validator.py",
        "src/core/config.py",
        "src/pipeline/orchestrator.py",
        "tests/test_context_drift_validator.py",
        "PROMPT3_IMPLEMENTATION_SUMMARY.md"
    ]

    print(f"Creating release package: {output_file}")

    with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for file_path in files_to_include:
            full_path = base_dir / file_path
            if full_path.exists():
                zf.write(full_path, file_path)
                print(f"  [+] Added: {file_path}")
            else:
                print(f"  [-] Missing: {file_path}")

    print(f"\n[SUCCESS] Package created: {output_file}")
    print(f"   Size: {output_file.stat().st_size:,} bytes")

    return output_file

if __name__ == "__main__":
    create_phase3_package()
