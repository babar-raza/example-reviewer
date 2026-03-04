#!/usr/bin/env python
"""
Test Data Provisioning Tool for Words Family

Provisions test data files for Words family runtime validation using local generation
(deterministic, via test_data_generator.py).  No external downloads required.

IMPORTANT: Generated files go to artifacts/backfill/words/test-data/
The test-data/ directory (if it exists) is treated as READ-ONLY.

Usage:
    python scripts/setup/provision_test_data_words.py [--force] [--verbose]

Flags:
    --force    Delete existing artifacts/backfill/words/test-data/ and regenerate
    --verbose  Print detailed generation progress
"""

import argparse
import shutil
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from services.test_data_generator import generate_all_words_family


def provision_test_data(
    output_dir: Path,
    force: bool = False,
    verbose: bool = False,
) -> dict:
    if force and output_dir.exists():
        if verbose:
            print(f"[FORCE] Deleting existing {output_dir}...")
        shutil.rmtree(output_dir)

    if verbose:
        print(f"[INFO] Provisioning Words test data to {output_dir}...")

    return generate_all_words_family(output_dir, verbose=verbose)


def main():
    parser = argparse.ArgumentParser(
        description="Provision test data files for Words family runtime validation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--force", action="store_true",
                        help="Delete existing directory and regenerate")
    parser.add_argument("--verbose", action="store_true",
                        help="Print detailed generation progress")
    parser.add_argument("--output-dir", type=Path,
                        default=Path("artifacts/backfill/words/test-data"),
                        help="Output directory (default: artifacts/backfill/words/test-data)")
    args = parser.parse_args()

    results = provision_test_data(
        output_dir=args.output_dir,
        force=args.force,
        verbose=args.verbose,
    )

    total = len(results)
    success_count = sum(1 for v in results.values() if v)
    failed_count = total - success_count

    print(f"\nProvisioning Summary:")
    print(f"  Total: {total}")
    print(f"  Success: {success_count}")
    print(f"  Failed: {failed_count}")

    if failed_count > 0:
        print(f"\nFailed files:")
        for filename, success in results.items():
            if not success:
                print(f"  - {filename}")

    print(f"\n[OK] Words test data provisioned to {args.output_dir}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
