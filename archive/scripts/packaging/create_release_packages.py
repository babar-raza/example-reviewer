"""
Create Phase 2 Gate B verification release packages.
"""
import os
import zipfile
from pathlib import Path
import sys

def should_exclude(path_str):
    """Check if path should be excluded from source package."""
    exclude_patterns = [
        '__pycache__',
        '.pyc',
        '.db',
        '.db-wal',
        '.db-shm',
        '/data/',
        '/workspace/',
        '/.git/',
        '/reports/e2e/run_202',  # Exclude old e2e runs (keep only the verification run)
    ]
    for pattern in exclude_patterns:
        if pattern in path_str.replace('\\', '/'):
            return True
    return False

def create_source_package(output_path):
    """Create source code package."""
    print(f"Creating source package: {output_path}")

    include_paths = [
        'src',
        'tools',
        'tests',
        'docs',
        'config',
        'migrations',
        'requirements.txt',
        'requirements-dev.txt',
        'README.md',
        'pytest.ini',
        # New Phase 2 files
        'IMPLEMENTATION_COMPLETE.md',
        'PHASE2_GATE_B_IMPLEMENTATION.md',
        'PHASE2_GATE_B_DELIVERY.md',
        'verify_gate_b_fixes.sh',
    ]

    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for include_path in include_paths:
            path = Path(include_path)
            if not path.exists():
                print(f"  WARNING: {include_path} not found, skipping")
                continue

            if path.is_file():
                print(f"  Adding file: {include_path}")
                zf.write(path, path)
            else:
                # Add directory recursively
                for root, dirs, files in os.walk(path):
                    # Filter out excluded directories
                    dirs[:] = [d for d in dirs if not should_exclude(os.path.join(root, d))]

                    for file in files:
                        file_path = Path(root) / file
                        if not should_exclude(str(file_path)):
                            arcname = file_path
                            zf.write(file_path, arcname)

        print(f"  [OK] Source package created: {os.path.getsize(output_path)} bytes")

def create_reports_package(output_path, run_folder):
    """Create reports package."""
    print(f"Creating reports package: {output_path}")

    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Add phase2_gateb_verify folder
        verify_path = Path('reports/phase2_gateb_verify')
        if verify_path.exists():
            for root, dirs, files in os.walk(verify_path):
                for file in files:
                    file_path = Path(root) / file
                    zf.write(file_path, file_path)

        # Add the e2e run folder
        run_path = Path(f'reports/e2e/{run_folder}')
        if run_path.exists():
            for root, dirs, files in os.walk(run_path):
                for file in files:
                    file_path = Path(root) / file
                    zf.write(file_path, file_path)
        else:
            print(f"  WARNING: Run folder {run_folder} not found")

        print(f"  [OK] Reports package created: {os.path.getsize(output_path)} bytes")

def create_review_bundle(output_path, run_folder):
    """Create minimal review bundle."""
    print(f"Creating review bundle: {output_path}")

    minimal_files = [
        f'reports/e2e/{run_folder}/run_1/fingerprint.json',
        f'reports/e2e/{run_folder}/run_2/fingerprint.json',
        f'reports/e2e/{run_folder}/determinism_comparison.json',
        f'reports/e2e/{run_folder}/e2e_summary.json',
        f'reports/e2e/{run_folder}/failure_analytics_run2.json',
        'reports/phase2_gateb_verify/gateb_result.md',
        'reports/phase2_gateb_verify/task1_infra_check.md',
        'reports/phase2_gateb_verify/gateb_failed_next_actions.md',
    ]

    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for file_path_str in minimal_files:
            file_path = Path(file_path_str)
            if file_path.exists():
                zf.write(file_path, file_path)
            else:
                print(f"  WARNING: {file_path_str} not found, skipping")

        print(f"  [OK] Review bundle created: {os.path.getsize(output_path)} bytes")

if __name__ == '__main__':
    # Configuration
    RUN_FOLDER = 'run_20260123_123943'  # The 2-run verification folder
    RELEASE_FOLDER = 'release'

    # Create release folder if it doesn't exist
    Path(RELEASE_FOLDER).mkdir(exist_ok=True)

    # Create all three packages
    create_source_package(f'{RELEASE_FOLDER}/phase2_gateb_source.zip')
    create_reports_package(f'{RELEASE_FOLDER}/phase2_gateb_reports.zip', RUN_FOLDER)
    create_review_bundle(f'{RELEASE_FOLDER}/phase2_gateb_review_bundle.zip', RUN_FOLDER)

    print("\n" + "="*80)
    print("RELEASE PACKAGES CREATED")
    print("="*80)

    # Show file sizes
    for filename in ['phase2_gateb_source.zip', 'phase2_gateb_reports.zip', 'phase2_gateb_review_bundle.zip']:
        filepath = Path(RELEASE_FOLDER) / filename
        if filepath.exists():
            size_mb = os.path.getsize(filepath) / (1024 * 1024)
            print(f"  {filename}: {size_mb:.2f} MB")

    print("="*80)
