#!/usr/bin/env python
"""
Test Data Provisioning Tool for ZIP Family

Provisions test data files for ZIP family runtime validation using:
1. Local generation (deterministic, using test_data_generator.py)
2. Optional backfill from example repository (not implemented yet)

IMPORTANT: Phase-2 fixture policy - generated files go to artifacts/backfill/zip/test-data/
The test-data/ directory is READ-ONLY and must not be modified.

Usage:
    python tools/provision_test_data_zip.py [--force] [--no-backfill] [--verbose] [--verify]

Flags:
    --force        Delete existing artifacts/backfill/zip/test-data/ and regenerate all files
    --no-backfill  Skip backfill attempt, use local generation only
    --verbose      Print detailed generation progress
    --verify       Generate twice and verify determinism (SHA256 checksums match)
"""

import argparse
import hashlib
import shutil
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from services.test_data_generator import generate_all_zip_family


def calculate_sha256(file_path: Path) -> str:
    """Calculate SHA256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()


def provision_test_data(
    output_dir: Path,
    force: bool = False,
    no_backfill: bool = True,
    verbose: bool = False,
) -> dict:
    """
    Provision test data files for ZIP family.

    Args:
        output_dir: Directory to create files in (test-data/zip/)
        force: If True, delete existing directory before provisioning
        no_backfill: If True, skip backfill and use local generation only
        verbose: Print detailed progress

    Returns:
        Dict mapping filename -> success (True/False)
    """
    if force and output_dir.exists():
        if verbose:
            print(f"[FORCE] Deleting existing {output_dir}...")
        shutil.rmtree(output_dir)

    if verbose:
        print(f"[INFO] Provisioning test data to {output_dir}...")
        print(f"[INFO] Backfill: {'disabled' if no_backfill else 'enabled'}")

    # For now, only local generation is implemented
    # Backfill from example repo will be added by provisioner service
    results = generate_all_zip_family(output_dir, verbose=verbose)

    if verbose:
        success_count = sum(1 for v in results.values() if v)
        print(f"\n[SUMMARY] Provisioned {success_count}/{len(results)} files")

    return results


def verify_determinism(output_dir: Path, verbose: bool = False) -> bool:
    """
    Verify determinism by generating twice and comparing SHA256 checksums.

    Args:
        output_dir: Directory to test
        verbose: Print detailed progress

    Returns:
        True if determinism verified (all checksums match), False otherwise
    """
    if verbose:
        print("\n[VERIFY] Testing determinism...")
        print("[VERIFY] Generating first set of files...")

    # Generate first time
    results1 = generate_all_zip_family(output_dir, verbose=False)
    checksums1 = {}

    for filename, success in results1.items():
        if success:
            file_path = output_dir / filename
            if file_path.is_file():
                checksums1[filename] = calculate_sha256(file_path)

    if verbose:
        print(f"[VERIFY] Generated {len(checksums1)} files")
        print("[VERIFY] Deleting and regenerating...")

    # Delete and generate second time
    shutil.rmtree(output_dir)
    results2 = generate_all_zip_family(output_dir, verbose=False)
    checksums2 = {}

    for filename, success in results2.items():
        if success:
            file_path = output_dir / filename
            if file_path.is_file():
                checksums2[filename] = calculate_sha256(file_path)

    if verbose:
        print(f"[VERIFY] Regenerated {len(checksums2)} files")
        print("[VERIFY] Comparing checksums...")

    # Compare checksums
    mismatches = []
    for filename in checksums1.keys():
        if filename not in checksums2:
            mismatches.append(f"{filename}: missing in second generation")
        elif checksums1[filename] != checksums2[filename]:
            mismatches.append(f"{filename}: checksum mismatch")

    if mismatches:
        print(f"\n[FAIL] Determinism verification FAILED:")
        for mismatch in mismatches:
            print(f"  - {mismatch}")
        return False
    else:
        if verbose:
            print(f"\n[OK] Determinism VERIFIED: All {len(checksums1)} files have matching checksums")
        return True


def main():
    parser = argparse.ArgumentParser(
        description="Provision test data files for ZIP family runtime validation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Delete existing test-data/zip/ and regenerate all files",
    )

    parser.add_argument(
        "--no-backfill",
        action="store_true",
        default=True,  # Backfill not implemented yet
        help="Skip backfill attempt, use local generation only (default: True)",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print detailed generation progress",
    )

    parser.add_argument(
        "--verify",
        action="store_true",
        help="Generate twice and verify determinism (SHA256 checksums must match)",
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts/backfill/zip/test-data"),
        help="Output directory (default: artifacts/backfill/zip/test-data)",
    )

    args = parser.parse_args()

    # Provision test data
    results = provision_test_data(
        output_dir=args.output_dir,
        force=args.force,
        no_backfill=args.no_backfill,
        verbose=args.verbose,
    )

    # Print summary
    total = len(results)
    success_count = sum(1 for v in results.values() if v)
    failed_count = total - success_count

    print(f"\nProvisioning Summary:")
    print(f"  Total: {total}")
    print(f"  Success: {success_count}")
    print(f"  Failed: {failed_count}")

    if failed_count > 0:
        print(f"\nFailed files (acceptable if RAR or 7z):")
        for filename, success in results.items():
            if not success:
                print(f"  - {filename}")

    # Verify determinism if requested
    if args.verify:
        if not verify_determinism(args.output_dir, verbose=args.verbose):
            print("\n[ERROR] Determinism verification failed!")
            return 1

    print(f"\n[OK] Test data provisioned successfully to {args.output_dir}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
