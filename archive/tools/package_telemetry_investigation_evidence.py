#!/usr/bin/env python3
"""
Task D: Evidence Packaging for Telemetry Investigation

Creates two zip files:
1. example_reviewer_telemetry_review_bundle.zip - Evidence from the rehearsal run
2. example_reviewer_telemetry_source.zip - Source code for review

Usage:
    python tools/package_telemetry_investigation_evidence.py --run-id <RUN_ID>
    python tools/package_telemetry_investigation_evidence.py --run-id <RUN_ID> --db-path <DB_PATH>
"""

import argparse
import glob
import json
import os
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any


def get_git_info() -> Dict[str, str]:
    """Get current git branch and commit SHA."""
    git_info = {
        'branch': 'unknown',
        'commit': 'unknown',
        'status': 'unknown'
    }

    try:
        # Get branch
        result = subprocess.run(
            ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            git_info['branch'] = result.stdout.strip()

        # Get commit SHA
        result = subprocess.run(
            ['git', 'rev-parse', 'HEAD'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            git_info['commit'] = result.stdout.strip()

        # Get status
        result = subprocess.run(
            ['git', 'status', '--porcelain'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            status_lines = result.stdout.strip()
            git_info['status'] = 'clean' if not status_lines else 'modified'

    except Exception as e:
        print(f"[WARN] Failed to get git info: {e}")

    return git_info


def run_pytest() -> str:
    """Run pytest and capture output."""
    try:
        result = subprocess.run(
            ['python', '-m', 'pytest', '-q'],
            capture_output=True,
            text=True,
            timeout=120
        )
        return f"Exit code: {result.returncode}\n\nSTDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}"
    except subprocess.TimeoutExpired:
        return "pytest timed out after 120 seconds"
    except Exception as e:
        return f"Failed to run pytest: {str(e)}"


def locate_fingerprint(run_id: str) -> Optional[Path]:
    """Locate fingerprint.json for the given run_id."""
    # Search in reports/e2e/run_*/run_*/fingerprint.json
    pattern = "reports/e2e/run_*/run_*/fingerprint.json"
    fingerprint_files = glob.glob(pattern)

    for fp_path in fingerprint_files:
        try:
            with open(fp_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if data.get('run_id') == run_id:
                    return Path(fp_path)
        except (json.JSONDecodeError, IOError):
            continue

    return None


def create_review_bundle(
    run_id: str,
    output_dir: Path,
    fingerprint_path: Optional[Path] = None
) -> Path:
    """
    Create telemetry review bundle zip file.

    Args:
        run_id: Run ID
        output_dir: Output directory for the zip
        fingerprint_path: Optional path to fingerprint.json

    Returns:
        Path to created zip file
    """
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    zip_name = f"example_reviewer_telemetry_review_bundle_{timestamp}.zip"
    zip_path = output_dir / zip_name

    print(f"[INFO] Creating review bundle: {zip_path}")

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Add README
        readme_content = f"""Telemetry Investigation Evidence Bundle
========================================

Run ID: {run_id}
Created: {timestamp}

Contents:
---------
1. fingerprint.json - Run fingerprint with db_path
2. validation_report.json - Strict validator output
3. telemetry_verify_output.txt - Telemetry API verification output
4. pytest_output.txt - Test results
5. git_state.json - Git branch and commit info
6. metadata.json - Evidence metadata
"""
        zf.writestr('README.txt', readme_content)

        # Add fingerprint.json
        if fingerprint_path and fingerprint_path.exists():
            print(f"  Adding fingerprint.json from {fingerprint_path}")
            zf.write(fingerprint_path, 'fingerprint.json')
        else:
            print(f"  [WARN] Fingerprint not found for run {run_id}")
            zf.writestr('fingerprint.json', json.dumps({'error': 'Fingerprint not found', 'run_id': run_id}, indent=2))

        # Add validation report
        validation_report_path = Path('reports/telemetry_investigation/validation_report.json')
        if validation_report_path.exists():
            print(f"  Adding validation_report.json")
            zf.write(validation_report_path, 'validation_report.json')
        else:
            print(f"  [WARN] Validation report not found")
            zf.writestr('validation_report.json', json.dumps({'error': 'Validation report not found'}, indent=2))

        # Add telemetry verify output
        telemetry_output_path = Path('reports/telemetry_investigation/telemetry_verify_output.txt')
        if telemetry_output_path.exists():
            print(f"  Adding telemetry_verify_output.txt")
            zf.write(telemetry_output_path, 'telemetry_verify_output.txt')
        else:
            print(f"  [WARN] Telemetry verify output not found")
            zf.writestr('telemetry_verify_output.txt', 'Telemetry verify output not found\n')

        # Run pytest and add output
        print(f"  Running pytest...")
        pytest_output = run_pytest()
        zf.writestr('pytest_output.txt', pytest_output)

        # Add git state
        print(f"  Capturing git state...")
        git_info = get_git_info()
        zf.writestr('git_state.json', json.dumps(git_info, indent=2))

        # Add metadata
        metadata = {
            'run_id': run_id,
            'created_at': timestamp,
            'bundle_version': '1.0',
            'git_branch': git_info['branch'],
            'git_commit': git_info['commit'],
            'git_status': git_info['status']
        }
        zf.writestr('metadata.json', json.dumps(metadata, indent=2))

    print(f"[SUCCESS] Review bundle created: {zip_path}")
    return zip_path


def create_source_bundle(output_dir: Path) -> Path:
    """
    Create source code bundle zip file.

    Includes: src/, tools/, tests/, docs/, config/, migrations/

    Args:
        output_dir: Output directory for the zip

    Returns:
        Path to created zip file
    """
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    zip_name = f"example_reviewer_telemetry_source_{timestamp}.zip"
    zip_path = output_dir / zip_name

    print(f"[INFO] Creating source bundle: {zip_path}")

    directories_to_include = [
        'src',
        'tools',
        'tests',
        'docs',
        'config',
        'migrations'
    ]

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for dir_name in directories_to_include:
            dir_path = Path(dir_name)
            if not dir_path.exists():
                print(f"  [WARN] Directory not found: {dir_name}")
                continue

            print(f"  Adding {dir_name}/...")
            for file_path in dir_path.rglob('*'):
                if file_path.is_file():
                    # Skip __pycache__, .pyc files, and .git
                    if '__pycache__' in file_path.parts or file_path.suffix == '.pyc' or '.git' in file_path.parts:
                        continue

                    arcname = str(file_path)
                    zf.write(file_path, arcname)

    print(f"[SUCCESS] Source bundle created: {zip_path}")
    return zip_path


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Package telemetry investigation evidence"
    )
    parser.add_argument(
        '--run-id',
        type=str,
        required=True,
        help='Run ID from the rehearsal'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default=None,
        help='Output directory for zip files (default: release/telemetry_investigation_<timestamp>)'
    )

    args = parser.parse_args()

    # Determine output directory
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        output_dir = Path(f'release/telemetry_investigation_{timestamp}')

    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n[INFO] Output directory: {output_dir}")
    print("=" * 80)

    # Locate fingerprint
    fingerprint_path = locate_fingerprint(args.run_id)
    if fingerprint_path:
        print(f"[INFO] Found fingerprint at {fingerprint_path}")
    else:
        print(f"[WARN] Could not locate fingerprint for run {args.run_id}")

    # Create review bundle
    review_bundle_path = create_review_bundle(args.run_id, output_dir, fingerprint_path)

    # Create source bundle
    source_bundle_path = create_source_bundle(output_dir)

    # Summary
    print("\n" + "=" * 80)
    print("[SUCCESS] Evidence Packaging Complete")
    print("=" * 80)
    print(f"Review Bundle: {review_bundle_path}")
    print(f"Source Bundle: {source_bundle_path}")
    print(f"\nOutput directory: {output_dir}")
    print("=" * 80)


if __name__ == "__main__":
    main()
