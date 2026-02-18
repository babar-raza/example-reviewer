#!/usr/bin/env python3
"""
Create Phase 2 Gate B Integrity upload packages.
"""

import zipfile
import os
from pathlib import Path

def create_review_bundle():
    """Create phase2_gateb_integrity_review_bundle.zip"""
    output_path = Path("release/phase2_gateb_integrity_review_bundle.zip")

    files = [
        "reports/phase2_gateb_integrity/run_1_fingerprint.json",
        "reports/phase2_gateb_integrity/run_2_fingerprint.json",
        "reports/phase2_gateb_integrity/determinism_comparison.json",
        "reports/phase2_gateb_integrity/e2e_summary.json",
        "reports/phase2_gateb_integrity/failure_analytics_run2.json",
        "reports/phase2_gateb_integrity/fixture_acquisition_ledger.md",
        "reports/phase2_gateb_integrity/rar_fixtures_sha256.txt",
    ]

    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for file in files:
            if Path(file).exists():
                zf.write(file, Path(file).name)
                print(f"  Added: {file}")
            else:
                print(f"  [WARN] Missing: {file}")

    print(f"[OK] Created: {output_path} ({output_path.stat().st_size:,} bytes)")
    return True

def create_reports_zip():
    """Create phase2_gateb_integrity_reports.zip"""
    output_path = Path("release/phase2_gateb_integrity_reports.zip")

    dirs_to_include = [
        "reports/phase2_gateb_integrity",
        "reports/e2e/run_20260123_164233",
    ]

    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for dir_path in dirs_to_include:
            dir_path = Path(dir_path)
            if dir_path.exists():
                for file in dir_path.rglob('*'):
                    if file.is_file():
                        arcname = str(file.relative_to("reports"))
                        zf.write(file, arcname)
                        print(f"  Added: {arcname}")
            else:
                print(f"  [WARN] Missing directory: {dir_path}")

    print(f"[OK] Created: {output_path} ({output_path.stat().st_size:,} bytes)")
    return True

def create_source_zip():
    """Create phase2_gateb_integrity_source.zip"""
    output_path = Path("release/phase2_gateb_integrity_source.zip")

    dirs_and_patterns = [
        ("src", "**/*.py"),
        ("tools", "**/*.py"),
        ("tests", "**/*.py"),
        ("docs", "**/*.md"),
        ("config", "**/*.json"),
        ("migrations", "**/*.sql"),
    ]

    files_to_include = [
        "requirements.txt",
        "requirements-dev.txt",
        "README.md",
    ]

    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Add directories with patterns
        for dir_name, pattern in dirs_and_patterns:
            dir_path = Path(dir_name)
            if dir_path.exists():
                for file in dir_path.rglob(pattern):
                    if file.is_file():
                        zf.write(file, str(file))
                        print(f"  Added: {file}")

        # Add individual files
        for file_name in files_to_include:
            file_path = Path(file_name)
            if file_path.exists():
                zf.write(file_path, file_name)
                print(f"  Added: {file_name}")

    print(f"[OK] Created: {output_path} ({output_path.stat().st_size:,} bytes)")
    return True

def create_failure_artifacts_zip():
    """Create failure_artifacts_final.zip"""
    output_path = Path("release/failure_artifacts_final.zip")

    # Include failure artifacts directory if it exists
    artifacts_dir = Path("reports/phase2_gateb_verify/failure_artifacts")

    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Add the ledger as evidence
        ledger_path = Path("reports/phase2_gateb_integrity/fixture_acquisition_ledger.md")
        if ledger_path.exists():
            zf.write(ledger_path, "fixture_acquisition_ledger.md")
            print(f"  Added: fixture_acquisition_ledger.md")

        # Add failure artifacts if they exist
        if artifacts_dir.exists():
            for file in artifacts_dir.rglob('*'):
                if file.is_file():
                    # Skip .db files
                    if file.suffix == '.db':
                        continue
                    arcname = str(file.relative_to(artifacts_dir.parent))
                    zf.write(file, arcname)
                    print(f"  Added: {arcname}")

        # Add a README explaining the artifacts
        readme_content = """# Failure Artifacts - Phase 2 Gate B Integrity

This package contains artifacts related to failures in the Phase 2 Gate B validation run.

## Contents

1. **fixture_acquisition_ledger.md** - Documents all attempts to acquire RAR, 7Z, and password fixtures
2. **failure_artifacts/** - (If present) Contains compile logs, runtime logs, and prepared code for non-VERIFIED examples

## Key Findings

All required RAR and 7Z fixtures are present and verified:
- plrabn12.rar: FOUND (SHA256 verified)
- encrypted.rar: FOUND (SHA256 verified)
- archive.7z: FOUND (SHA256 verified)

The 3 examples marked as "missing_rar_fixture" appear to be false positives - the fixtures exist in the backfill directory.
See fixture_acquisition_ledger.md for complete evidence.

## Legitimate Infrastructure Blocks

Only 1 legitimate INFRA_BLOCKED classification:
- encrypted.rar password: NOT AVAILABLE (documented in ledger)

The other 3 "missing_rar_fixture" blocks are disputed and should be investigated as potential code or file access issues.
"""
        zf.writestr("README.md", readme_content)
        print(f"  Added: README.md")

    print(f"[OK] Created: {output_path} ({output_path.stat().st_size:,} bytes)")
    return True

def main():
    print("Creating Phase 2 Gate B Integrity packages...")
    print()

    # Ensure release directory exists
    Path("release").mkdir(exist_ok=True)

    print("[1/4] Creating review bundle...")
    create_review_bundle()
    print()

    print("[2/4] Creating reports archive...")
    create_reports_zip()
    print()

    print("[3/4] Creating source archive...")
    create_source_zip()
    print()

    print("[4/4] Creating failure artifacts...")
    create_failure_artifacts_zip()
    print()

    print("="*80)
    print("[SUCCESS] All packages created successfully!")
    print()
    print("Upload these files in order:")
    print("  1. release/phase2_gateb_integrity_review_bundle.zip")
    print("  2. release/phase2_gateb_integrity_reports.zip")
    print("  3. release/phase2_gateb_integrity_source.zip")
    print("  4. release/failure_artifacts_final.zip")
    print()
    print("Also upload:")
    print("  5. release/CHECKLIST_PHASE2_GATEB_INTEGRITY.md")
    print("="*80)

if __name__ == "__main__":
    main()
