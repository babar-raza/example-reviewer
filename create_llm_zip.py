"""Create a clean zip file for LLM exploration, excluding cache files."""
import zipfile
import os
from pathlib import Path

def should_include(path):
    """Check if a file should be included in the zip."""
    # Exclude patterns
    exclude_patterns = [
        '__pycache__',
        '.pyc',
        '.pyo',
        '.pyd',
        '.so',
        '.dll',
        '.dylib',
        '.egg-info',
        '.pytest_cache',
    ]

    path_str = str(path)
    for pattern in exclude_patterns:
        if pattern in path_str:
            return False
    return True

def create_llm_zip():
    """Create a comprehensive zip for LLM exploration."""
    zip_path = 'llm-exploration-clean.zip'

    # Directories to include
    dirs_to_include = ['src', 'docs', 'specs', 'tests', 'config', 'plans', 'migrations']

    # Individual files to include
    files_to_include = [
        'schema.sql',
        'README.md',
        'QUICKSTART.md',
        'EXECUTIVE_SUMMARY.md',
        'IMPLEMENTATION-PLAN.md',
        'PHASE5_IMPLEMENTATION.md',
        'API_REFERENCE_ENHANCEMENT_RESULTS.md',
        'MULTI_FAMILY_VERIFICATION_RESULTS.md',
        'VALIDATION_FAILURE_ANALYSIS.md',
        'requirements.txt',
        'requirements-dev.txt',
        'pytest.ini',
        '.env.example',
        '.gitignore',
        'run.py',
        'run_cli.py',
        'run_tests.py',
        'run_validation.py',
    ]

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Add directories
        for dir_name in dirs_to_include:
            dir_path = Path(dir_name)
            if dir_path.exists():
                for file_path in dir_path.rglob('*'):
                    if file_path.is_file() and should_include(file_path):
                        arcname = str(file_path)
                        zipf.write(file_path, arcname)
                        print(f"Added: {arcname}")

        # Add individual files
        for file_name in files_to_include:
            file_path = Path(file_name)
            if file_path.exists():
                zipf.write(file_path, file_name)
                print(f"Added: {file_name}")

    # Get zip file size
    zip_size = os.path.getsize(zip_path)
    print(f"\nZip created: {zip_path}")
    print(f"Size: {zip_size / 1024:.1f} KB ({zip_size / (1024*1024):.2f} MB)")

    # Count files in zip
    with zipfile.ZipFile(zip_path, 'r') as zipf:
        file_count = len(zipf.namelist())
        print(f"Files included: {file_count}")

if __name__ == '__main__':
    create_llm_zip()
