"""Create Phase 2 Final Push evidence packages."""
import zipfile
import os
from pathlib import Path
from datetime import datetime

# Find the latest release directory
release_base = Path("release")
release_dirs = [d for d in release_base.glob("phase2_final_push_*") if d.is_dir()]
if not release_dirs:
    print("No release directory found!")
    exit(1)

release_dir = sorted(release_dirs)[-1]
print(f"Using release directory: {release_dir}")

# Package 1: Review Bundle
print("\nCreating phase2_final_push_review_bundle.zip...")
bundle_zip = release_dir / "phase2_final_push_review_bundle.zip"

with zipfile.ZipFile(bundle_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
    # Run fingerprints and summaries
    for run_dir in Path("runs").glob("*"):
        for file in ["fingerprint.json", "results_summary.json"]:
            fp = run_dir / file
            if fp.exists():
                zf.write(fp, f"runs/{run_dir.name}/{file}")

    # Failure exports from phase2_final_push
    phase2_reports = Path("reports/phase2_final_push")
    if phase2_reports.exists():
        for file in phase2_reports.glob("*.json"):
            zf.write(file, f"reports/phase2_final_push/{file.name}")
        for file in phase2_reports.glob("*.txt"):
            zf.write(file, f"reports/phase2_final_push/{file.name}")

    # Checklist
    checklist = Path("release/CHECKLIST_PHASE2_FINAL_PUSH.md")
    if checklist.exists():
        zf.write(checklist, "CHECKLIST_PHASE2_FINAL_PUSH.md")

print(f"Created: {bundle_zip} ({bundle_zip.stat().st_size:,} bytes)")

# Package 2: Full Reports
print("\nCreating phase2_final_push_reports.zip...")
reports_zip = release_dir / "phase2_final_push_reports.zip"

with zipfile.ZipFile(reports_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
    # Full phase2_final_push reports
    if phase2_reports.exists():
        for file in phase2_reports.rglob("*"):
            if file.is_file():
                arcname = file.relative_to(Path("reports"))
                zf.write(file, f"reports/{arcname}")

    # Latest e2e run reports (the two Gate B runs)
    e2e_base = Path("reports/e2e")
    if e2e_base.exists():
        e2e_runs = sorted([d for d in e2e_base.glob("run_*") if d.is_dir()])
        if len(e2e_runs) >= 2:
            for run_dir in e2e_runs[-2:]:  # Last 2 runs
                for file in run_dir.rglob("*"):
                    if file.is_file():
                        arcname = file.relative_to(Path("reports"))
                        zf.write(file, f"reports/{arcname}")

print(f"Created: {reports_zip} ({reports_zip.stat().st_size:,} bytes)")

# Package 3: Source Code
print("\nCreating phase2_final_push_source.zip...")
source_zip = release_dir / "phase2_final_push_source.zip"

with zipfile.ZipFile(source_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
    # Source directories
    for dir_name in ["src", "tools", "tests", "config", "migrations"]:
        dir_path = Path(dir_name)
        if dir_path.exists():
            for file in dir_path.rglob("*"):
                if file.is_file() and not file.name.endswith(('.pyc', '__pycache__')):
                    zf.write(file, str(file))

    # Requirements files
    for req_file in ["requirements.txt", "requirements-dev.txt"]:
        if Path(req_file).exists():
            zf.write(req_file, req_file)

    # Fix scripts created during this session
    for script in ["fix_compile_failures.py", "fix_runtime_failures.py", "recompile_fixed_examples.py"]:
        if Path(script).exists():
            zf.write(script, script)

print(f"Created: {source_zip} ({source_zip.stat().st_size:,} bytes)")

print(f"\nAll packages created in: {release_dir}")
print("\nPackage Summary:")
print(f"  1. {bundle_zip.name} - Review bundle with fingerprints and key results")
print(f"  2. {reports_zip.name} - Full reports and logs")
print(f"  3. {source_zip.name} - Source code and configuration")
