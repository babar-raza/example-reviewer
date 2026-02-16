#!/usr/bin/env python3
"""Create evidence packages for strict context unblock task."""

import zipfile
import os
from pathlib import Path

TIMESTAMP = "20260127_111454"
REPORTS_DIR = f"reports/strict_context_unblock/{TIMESTAMP}"
RELEASE_DIR = f"release/strict_context_unblock_{TIMESTAMP}"
RUN_DIR = "runs/beb0933e1914c74c"

# Ensure release directory exists
Path(RELEASE_DIR).mkdir(parents=True, exist_ok=True)

# Package 1: Review Bundle
print("Creating strict_context_unblock_review_bundle.zip...")
with zipfile.ZipFile(f"{RELEASE_DIR}/strict_context_unblock_review_bundle.zip", 'w', zipfile.ZIP_DEFLATED) as zf:
    files = [
        f"{REPORTS_DIR}/migration010_verify.txt",
        f"{REPORTS_DIR}/validation_report.json",
        f"{REPORTS_DIR}/strict_run_stdout.txt",
        f"{REPORTS_DIR}/run_id.txt",
        f"{REPORTS_DIR}/pytest_q_before.txt",
        f"{REPORTS_DIR}/pytest_q_after.txt",
        f"{REPORTS_DIR}/git_state_before.txt",
    ]

    # Add run artifacts if they exist
    if Path(RUN_DIR).exists():
        for file in ["fingerprint.json", "results_summary.json"]:
            file_path = f"{RUN_DIR}/{file}"
            if Path(file_path).exists():
                files.append(file_path)

    for file in files:
        if Path(file).exists():
            zf.write(file, arcname=Path(file).name)
            print(f"  Added: {file}")
        else:
            print(f"  WARNING: File not found: {file}")

print("\nPackage 1 created successfully!")

# Package 2: Full Reports
print("\nCreating strict_context_unblock_reports.zip...")
with zipfile.ZipFile(f"{RELEASE_DIR}/strict_context_unblock_reports.zip", 'w', zipfile.ZIP_DEFLATED) as zf:
    # Add all reports
    if Path(REPORTS_DIR).exists():
        for root, dirs, files in os.walk(REPORTS_DIR):
            for file in files:
                file_path = Path(root) / file
                arcname = file_path.relative_to(Path(REPORTS_DIR).parent)
                zf.write(file_path, arcname=str(arcname))
                print(f"  Added: {file_path}")

    # Add run artifacts
    if Path(RUN_DIR).exists():
        for root, dirs, files in os.walk(RUN_DIR):
            for file in files:
                file_path = Path(root) / file
                arcname = file_path.relative_to(Path(RUN_DIR).parent)
                zf.write(file_path, arcname=str(arcname))
                print(f"  Added: {file_path}")

print("\nPackage 2 created successfully!")

# Package 3: Source Code
print("\nCreating strict_context_unblock_source.zip...")
with zipfile.ZipFile(f"{RELEASE_DIR}/strict_context_unblock_source.zip", 'w', zipfile.ZIP_DEFLATED) as zf:
    # Source directories
    source_dirs = ['src', 'tools', 'tests', 'docs', 'config', 'migrations']
    for dir_name in source_dirs:
        if Path(dir_name).exists():
            for root, dirs, files in os.walk(dir_name):
                # Skip __pycache__ directories
                if '__pycache__' in root:
                    continue
                for file in files:
                    # Skip .pyc files
                    if file.endswith('.pyc'):
                        continue
                    file_path = Path(root) / file
                    zf.write(file_path, arcname=str(file_path))
                    print(f"  Added: {file_path}")

    # Individual files
    individual_files = [
        'requirements.txt',
        'requirements-dev.txt',
        'README.md',
        'INTEGRATION_COMPLETION_REPORT.md'
    ]
    for file in individual_files:
        if Path(file).exists():
            zf.write(file)
            print(f"  Added: {file}")

print("\nPackage 3 created successfully!")

print("\n" + "="*80)
print("All packages created successfully in:", RELEASE_DIR)
print("="*80)
