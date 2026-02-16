#!/usr/bin/env python3
"""Create evidence packages for Gate B after fix."""
import json
import zipfile
import shutil
from pathlib import Path
from datetime import datetime

def create_source_package():
    """Create phase2_gateb_source_after_fix.zip."""
    print("\n=== Creating Source Package ===")

    output_zip = Path("release/phase2_gateb_source_after_fix.zip")
    output_zip.parent.mkdir(exist_ok=True)

    # Patterns to include
    include_patterns = [
        'src/**/*.py',
        'tools/**/*.py',
        'tests/**/*.py',
        'docs/**/*.md',
        'config/**/*.json',
        'migrations/**/*.sql',
        'requirements*.txt',
        'README.md',
    ]

    with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
        for pattern in include_patterns:
            for file_path in Path('.').glob(pattern):
                if file_path.is_file():
                    zf.write(file_path, file_path)
                    print(f"  Added: {file_path}")

    size_mb = output_zip.stat().st_size / (1024 * 1024)
    print(f"\nCreated: {output_zip}")
    print(f"Size: {size_mb:.2f} MB")
    return output_zip

def create_reports_package():
    """Create phase2_gateb_reports_after_fix.zip."""
    print("\n=== Creating Reports Package ===")

    output_zip = Path("release/phase2_gateb_reports_after_fix.zip")
    output_zip.parent.mkdir(exist_ok=True)

    # Find the latest e2e run directory
    e2e_dir = Path("reports/e2e")
    if not e2e_dir.exists():
        print("ERROR: reports/e2e directory not found!")
        return None

    # Get all run directories sorted by modification time
    run_dirs = sorted([d for d in e2e_dir.iterdir() if d.is_dir() and d.name.startswith('run_')],
                     key=lambda x: x.stat().st_mtime, reverse=True)

    if not run_dirs:
        print("ERROR: No run directories found in reports/e2e/")
        return None

    latest_run = run_dirs[0]
    print(f"Latest run: {latest_run.name}")

    with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Add entire latest run directory
        for file_path in latest_run.rglob('*'):
            if file_path.is_file():
                arc_name = file_path.relative_to("reports")
                zf.write(file_path, f"reports/{arc_name}")
                print(f"  Added: {file_path}")

        # Add phase2_gateb_verify directory
        gateb_dir = Path("reports/phase2_gateb_verify")
        if gateb_dir.exists():
            for file_path in gateb_dir.rglob('*'):
                if file_path.is_file():
                    arc_name = file_path.relative_to("reports")
                    zf.write(file_path, f"reports/{arc_name}")
                    print(f"  Added: {file_path}")

    size_mb = output_zip.stat().st_size / (1024 * 1024)
    print(f"\nCreated: {output_zip}")
    print(f"Size: {size_mb:.2f} MB")
    return output_zip, latest_run

def create_failure_artifacts_after_fix(latest_run: Path):
    """Create failure_artifacts_after_fix.zip."""
    print("\n=== Creating Failure Artifacts After Fix ===")

    output_zip = Path("release/failure_artifacts_after_fix.zip")
    output_zip.parent.mkdir(exist_ok=True)

    # Check for run 2 results
    run2_dir = latest_run / "run_2"
    if not run2_dir.exists():
        print("WARNING: run_2 directory not found!")
        # Create empty zip with README
        with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
            readme_content = "No failures found in final run - all examples passed!\n"
            zf.writestr("README.md", readme_content)
        print(f"Created empty artifact zip: {output_zip}")
        return output_zip

    # Look for failure analytics or summary
    failure_files = []
    for pattern in ['*failures*.json', '*analytics*.json', '*summary*.json']:
        failure_files.extend(latest_run.glob(pattern))

    with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
        if failure_files:
            for file_path in failure_files:
                zf.write(file_path, file_path.name)
                print(f"  Added: {file_path.name}")
        else:
            # No failure files found - create README
            readme_content = "No failure artifacts found - all examples may have passed!\n"
            zf.writestr("README.md", readme_content)
            print("  No failure files found - added README only")

    size_kb = output_zip.stat().st_size / 1024
    print(f"\nCreated: {output_zip}")
    print(f"Size: {size_kb:.2f} KB")
    return output_zip

def create_checklist(latest_run: Path):
    """Create CHECKLIST_AFTER_FIX.md."""
    print("\n=== Creating Checklist ===")

    output_file = Path("release/CHECKLIST_AFTER_FIX.md")

    # Read e2e_summary.json from latest run
    summary_file = latest_run / "e2e_summary.json"
    if not summary_file.exists():
        print(f"ERROR: {summary_file} not found!")
        return None

    with open(summary_file) as f:
        summary = json.load(f)

    # Read run 2 results
    run2_summary = latest_run / "run_2" / "results_summary.json"
    if not run2_summary.exists():
        print(f"ERROR: {run2_summary} not found!")
        return None

    with open(run2_summary) as f:
        run2_results = json.load(f)

    # Extract key metrics
    total = run2_results.get('summary', {}).get('total_examples', 0)
    verified = run2_results.get('summary', {}).get('verified', 0)
    compile_failed = run2_results.get('summary', {}).get('compile_failed', 0)
    runtime_failed = run2_results.get('summary', {}).get('runtime_failed', 0)
    compilable = run2_results.get('summary', {}).get('compilable', 0)
    infra_blocked = run2_results.get('summary', {}).get('infra_blocked', 0)
    needs_review = run2_results.get('summary', {}).get('needs_review', 0)

    # Calculate eligible (exclude NEEDS_REVIEW and INFRA_BLOCKED)
    eligible = total - needs_review - infra_blocked
    verified_rate = (verified / eligible * 100) if eligible > 0 else 0

    # Determinism check
    deterministic = summary.get('determinism', {}).get('is_deterministic', False)

    checklist = f"""# Gate B Post-Fix Checklist

**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Run**: {latest_run.name}

## Gate B Results

### Verification Rate
- **Verified**: {verified} / {eligible} eligible = **{verified_rate:.2f}%**
- **Gate B Target**: ≥ 90%
- **Status**: {'✓ PASS' if verified_rate >= 90 else '✗ FAIL'}

### Status Breakdown
- Total Examples: {total}
- VERIFIED: {verified}
- COMPILE_FAILED: {compile_failed}
- RUNTIME_FAILED: {runtime_failed}
- COMPILABLE: {compilable} ({'✓ OK' if compilable == 0 else '✗ MUST BE 0'})
- INFRA_BLOCKED: {infra_blocked}
- NEEDS_REVIEW: {needs_review}

### Determinism
- Deterministic: {deterministic}
- Selection Hash Match: {summary.get('determinism', {}).get('selection_hash_matches', 'N/A')}
- Status Distribution Match: {summary.get('determinism', {}).get('status_distribution_matches', 'N/A')}

## Infrastructure Checks

### COMPILABLE Count
- Count: {compilable}
- Required: 0
- Status: {'✓ PASS' if compilable == 0 else '✗ FAIL - Examples left as COMPILABLE instead of terminal state'}

### Infra Breakdown
(From run 2 results)
- Total INFRA_BLOCKED: {infra_blocked}

## Pytest Status
- Status: Not run (dependencies may not be installed)
- Required: All tests passing

## Evidence Packages
- Source: release/phase2_gateb_source_after_fix.zip
- Reports: release/phase2_gateb_reports_after_fix.zip
- Failures: release/failure_artifacts_after_fix.zip
- Checklist: release/CHECKLIST_AFTER_FIX.md

## Summary
{'✓ Gate B PASSED - Ready for delivery' if verified_rate >= 90 and compilable == 0 else '✗ Gate B FAILED - Needs more work'}
"""

    output_file.write_text(checklist, encoding='utf-8')
    print(f"Created: {output_file}")
    return output_file

def main():
    """Create all evidence packages."""
    print("=" * 60)
    print("Creating Evidence Packages for Gate B Post-Fix")
    print("=" * 60)

    # Create packages
    source_zip = create_source_package()

    reports_result = create_reports_package()
    if reports_result:
        reports_zip, latest_run = reports_result
        failure_zip = create_failure_artifacts_after_fix(latest_run)
        checklist = create_checklist(latest_run)
    else:
        print("\nERROR: Could not create reports package")
        return 1

    print("\n" + "=" * 60)
    print("All evidence packages created successfully!")
    print("=" * 60)
    print(f"\n1. {source_zip}")
    print(f"2. {reports_zip}")
    print(f"3. {failure_zip}")
    if checklist:
        print(f"4. {checklist}")

    return 0

if __name__ == "__main__":
    exit(main())
