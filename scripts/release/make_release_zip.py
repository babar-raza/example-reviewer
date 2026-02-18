#!/usr/bin/env python3
"""
Release ZIP Creator for Example Reviewer Pipeline

Creates a clean ZIP package for distribution that:
- Includes source code, tests, docs, migrations, config
- Excludes compiled artifacts, caches, data, large files
- Ensures reproducibility and clean packaging

Usage:
    python tools/make_release_zip.py [output_name]

Example:
    python tools/make_release_zip.py hardening_release.zip
"""

import zipfile
import os
from pathlib import Path
from datetime import datetime
import sys

# Directories and files to include
INCLUDE_PATTERNS = [
    'src/**/*.py',
    'tests/**/*.py',
    'tests/**/*.md',
    'migrations/**/*.sql',
    'docs/**/*.md',
    'config/**/*.json',
    'config/families/**/*.json',
    'tools/**/*.py',
    'requirements.txt',
    'requirements-dev.txt',
    'README.md',
    '.gitignore',
    'pytest.ini',
    'setup.py',
]

# Directories to exclude (even if matched by include patterns)
EXCLUDE_DIRS = {
    '__pycache__',
    '.venv',
    'venv',
    '.git',
    '.pytest_cache',
    'data',
    'artifacts',
    'workspace',
    'workspaces',
    'cache',
    'logs',
    'local-telemetry',
    'runs',
    'reports',
    'report',
    'reviews',
    'plans',
    'specs',
    'validation-results',
    'test_determinism',
    'archive',
    '.benchmarks',
    '.github',
    'KB',
    'content',
    '-p',
}

# File patterns to exclude
EXCLUDE_FILES = {
    '*.pyc',
    '*.pyo',
    '*.pyd',
    '*.db',
    '*.db-shm',
    '*.db-wal',
    '*.zip',
    '*.env',
    '.DS_Store',
    'checksums*.txt',
    'NUL',
}


def should_exclude_path(path: Path) -> bool:
    """Check if a path should be excluded from the ZIP."""
    # Check if any parent directory is in exclude list
    for parent in path.parents:
        if parent.name in EXCLUDE_DIRS:
            return True

    # Check if the path itself is an excluded directory
    if path.is_dir() and path.name in EXCLUDE_DIRS:
        return True

    # Check if filename matches exclude patterns
    for pattern in EXCLUDE_FILES:
        if pattern.startswith('*.'):
            ext = pattern[1:]  # e.g., ".pyc"
            if path.name.endswith(ext):
                return True
        elif path.name == pattern:
            return True

    return False


def get_files_to_include(repo_root: Path) -> list[Path]:
    """Get list of files to include in the ZIP."""
    files = set()

    # Process each include pattern
    for pattern in INCLUDE_PATTERNS:
        if '**' in pattern:
            # Glob pattern
            matches = repo_root.glob(pattern)
            for match in matches:
                if match.is_file() and not should_exclude_path(match):
                    files.add(match)
        else:
            # Direct file reference
            file_path = repo_root / pattern
            if file_path.exists() and file_path.is_file() and not should_exclude_path(file_path):
                files.add(file_path)

    return sorted(files)


def create_release_zip(output_name: str = None) -> Path:
    """Create the release ZIP file."""
    repo_root = Path(__file__).parent.parent

    # Generate default output name if not provided
    if output_name is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_name = f'example_reviewer_release_{timestamp}.zip'

    output_path = repo_root / output_name

    # Get files to include
    files = get_files_to_include(repo_root)

    print(f"Creating release ZIP: {output_path}")
    print(f"Including {len(files)} files...")

    # Create ZIP
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for file_path in files:
            # Calculate relative path from repo root
            arcname = file_path.relative_to(repo_root)
            zf.write(file_path, arcname)
            print(f"  + {arcname}")

    # Get ZIP size
    size_mb = output_path.stat().st_size / (1024 * 1024)

    print(f"\n[OK] Release ZIP created: {output_path}")
    print(f"   Size: {size_mb:.2f} MB")
    print(f"   Files: {len(files)}")

    return output_path


def verify_zip_contents(zip_path: Path) -> bool:
    """Verify the ZIP contains required files and excludes unwanted ones."""
    print(f"\n[VERIFY] Checking ZIP contents: {zip_path}")

    required_dirs = ['src', 'tests', 'migrations', 'docs', 'config', 'tools']
    required_files = [
        'requirements.txt',
        'requirements-dev.txt',
        'README.md',
        'src/cli/__init__.py',
        'src/cli/main.py',
    ]

    errors = []

    with zipfile.ZipFile(zip_path, 'r') as zf:
        names = set(zf.namelist())

        # Check required directories
        for req_dir in required_dirs:
            if not any(name.startswith(req_dir + '/') for name in names):
                errors.append(f"[FAIL] Missing required directory: {req_dir}/")

        # Check required files
        for req_file in required_files:
            if req_file not in names:
                errors.append(f"[FAIL] Missing required file: {req_file}")

        # Check for unwanted files
        for name in names:
            if '__pycache__' in name:
                errors.append(f"[FAIL] Contains __pycache__: {name}")
            if name.endswith('.pyc'):
                errors.append(f"[FAIL] Contains .pyc file: {name}")
            if name.endswith('.db'):
                errors.append(f"[FAIL] Contains database file: {name}")

        # Print summary
        print(f"   Total files: {len(names)}")
        print(f"   Directories found: {', '.join(sorted(set(n.split('/')[0] for n in names if '/' in n)))}")

    if errors:
        print("\n[FAIL] Verification FAILED:")
        for error in errors:
            print(f"   {error}")
        return False
    else:
        print("\n[OK] Verification PASSED")
        print("   - All required directories present")
        print("   - All required files present")
        print("   - No __pycache__ or .pyc files")
        print("   - No database files")
        return True


def main():
    """Main entry point."""
    output_name = sys.argv[1] if len(sys.argv) > 1 else None

    try:
        # Create the ZIP
        zip_path = create_release_zip(output_name)

        # Verify contents
        if verify_zip_contents(zip_path):
            print(f"\n[SUCCESS] Release ZIP ready: {zip_path}")
            return 0
        else:
            print(f"\n[FAIL] Release ZIP verification failed")
            return 1

    except Exception as e:
        print(f"\n[FAIL] Error creating release ZIP: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
