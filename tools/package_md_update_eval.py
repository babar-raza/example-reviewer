#!/usr/bin/env python3
"""
Package MD Update Evaluation Evidence.

Creates two zip files:
1. md_update_eval_review_bundle.zip - Key evidence files
2. md_update_eval_reports.zip - Full reports directory
"""

import argparse
import sys
import zipfile
from pathlib import Path


def create_review_bundle(reports_dir: Path, output_dir: Path, timestamp: str):
    """Create review bundle with key evidence files."""

    bundle_name = f"md_update_eval_review_bundle.zip"
    bundle_path = output_dir / bundle_name

    # Files to include in review bundle
    files_to_include = [
        "verified_examples.json",
        "md_update_small_stdout_v2.txt",
        "md_update_full_stdout.txt",
        "diff_small.patch",
        "diff_full.patch",
        "diff_files.txt",
        "diff_small_files.txt",
        "git_state_before.txt",
        "pytest_before.txt",
        "pytest_after.txt",
        "EVALUATION_FINDINGS.md"
    ]

    with zipfile.ZipFile(bundle_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for filename in files_to_include:
            file_path = reports_dir / filename
            if file_path.exists():
                zf.write(file_path, filename)
                print(f"  Added: {filename}")
            else:
                print(f"  Skipped (not found): {filename}")

    print(f"\nCreated: {bundle_path}")
    print(f"Size: {bundle_path.stat().st_size:,} bytes")

    return bundle_path


def create_reports_zip(reports_dir: Path, output_dir: Path, timestamp: str):
    """Create full reports directory zip."""

    zip_name = f"md_update_eval_reports.zip"
    zip_path = output_dir / zip_name

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Add all files from reports directory
        for file_path in reports_dir.rglob('*'):
            if file_path.is_file():
                arcname = file_path.relative_to(reports_dir.parent)
                zf.write(file_path, arcname)
                print(f"  Added: {arcname}")

    print(f"\nCreated: {zip_path}")
    print(f"Size: {zip_path.stat().st_size:,} bytes")

    return zip_path


def main():
    parser = argparse.ArgumentParser(
        description="Package MD Update Evaluation Evidence"
    )
    parser.add_argument(
        '--timestamp',
        required=True,
        help='Timestamp directory name (e.g., 20260127_171424)'
    )
    parser.add_argument(
        '--reports-base',
        default='reports/md_update_eval',
        help='Base reports directory (default: reports/md_update_eval)'
    )
    parser.add_argument(
        '--output-dir',
        default='release',
        help='Output directory for zip files (default: release)'
    )

    args = parser.parse_args()

    # Resolve paths
    reports_dir = Path(args.reports_base) / args.timestamp
    output_dir = Path(args.output_dir) / f"md_update_eval_{args.timestamp}"

    if not reports_dir.exists():
        print(f"Error: Reports directory not found: {reports_dir}")
        sys.exit(1)

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("MD UPDATE EVALUATION - EVIDENCE PACKAGING")
    print("=" * 80)
    print(f"Reports directory: {reports_dir}")
    print(f"Output directory: {output_dir}")
    print()

    # Create review bundle
    print("Creating review bundle...")
    review_bundle = create_review_bundle(reports_dir, output_dir, args.timestamp)
    print()

    # Create full reports zip
    print("Creating full reports zip...")
    reports_zip = create_reports_zip(reports_dir, output_dir, args.timestamp)
    print()

    print("=" * 80)
    print("PACKAGING COMPLETE")
    print("=" * 80)
    print(f"Review Bundle: {review_bundle}")
    print(f"Reports Zip: {reports_zip}")
    print()
    print("Upload these files for review.")
    print("=" * 80)


if __name__ == "__main__":
    main()
