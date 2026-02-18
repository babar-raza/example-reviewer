#!/usr/bin/env python
"""Create evidence bundle ZIPs for strict context validation."""
import zipfile
import os
from pathlib import Path

timestamp = "20260126_164909"
report_dir = Path(f"reports/strict_context_validation/{timestamp}")
release_dir = Path(f"release/strict_context_validation_{timestamp}")
release_dir.mkdir(parents=True, exist_ok=True)

# Helper function to add files to ZIP
def add_file_if_exists(zipf, file_path, arcname=None):
    """Add file to ZIP if it exists."""
    p = Path(file_path)
    if p.exists():
        zipf.write(p, arcname=arcname or p.name)
        print(f"  [OK] Added: {p}")
        return True
    else:
        print(f"  [SKIP] Missing: {p}")
        return False

def add_dir_recursive(zipf, dir_path, arcname_base=""):
    """Add directory recursively to ZIP."""
    p = Path(dir_path)
    if not p.exists():
        print(f"  [SKIP] Missing directory: {p}")
        return False

    for item in p.rglob("*"):
        if item.is_file():
            arcname = str(Path(arcname_base) / item.relative_to(p))
            zipf.write(item, arcname=arcname)
    print(f"  [OK] Added directory: {p}")
    return True

# A) Create strict_context_review_bundle.zip
print("\n[1/3] Creating strict_context_review_bundle.zip...")
review_zip = release_dir / "strict_context_review_bundle.zip"
with zipfile.ZipFile(review_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
    add_file_if_exists(zipf, report_dir / "SUMMARY.md")
    add_file_if_exists(zipf, report_dir / "pytest_q.txt")
    add_file_if_exists(zipf, report_dir / "git_state.txt")
    add_file_if_exists(zipf, report_dir / "run_id.txt")
    add_file_if_exists(zipf, report_dir / "strict_run_stdout.txt")
    add_file_if_exists(zipf, report_dir / "strict_run_stdout_v2.txt")
    add_file_if_exists(zipf, report_dir / "validation_stdout.txt")
    # Try to add run artifacts if they exist
    add_file_if_exists(zipf, "runs/43e160bc474e6cef/fingerprint.json", "run_1/fingerprint.json")
    add_file_if_exists(zipf, "runs/43e160bc474e6cef/results_summary.json", "run_1/results_summary.json")

print(f"[OK] Created: {review_zip} ({review_zip.stat().st_size / 1024:.1f} KB)")

# B) Create strict_context_reports.zip
print("\n[2/3] Creating strict_context_reports.zip...")
reports_zip = release_dir / "strict_context_reports.zip"
with zipfile.ZipFile(reports_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
    # Add all validation reports
    add_dir_recursive(zipf, report_dir, f"strict_context_validation/{timestamp}")
    # Add run artifacts if they exist
    add_dir_recursive(zipf, "runs/43e160bc474e6cef", "runs/43e160bc474e6cef")
    # Add telemetry if exists
    add_dir_recursive(zipf, "local-telemetry/43e160bc474e6cef", "local-telemetry/43e160bc474e6cef")

print(f"[OK] Created: {reports_zip} ({reports_zip.stat().st_size / 1024:.1f} KB)")

# C) Create strict_context_source.zip
print("\n[3/3] Creating strict_context_source.zip...")
source_zip = release_dir / "strict_context_source.zip"
with zipfile.ZipFile(source_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
    # Add source directories
    for src_dir in ["src", "tools", "tests", "docs", "config", "migrations"]:
        if Path(src_dir).exists():
            add_dir_recursive(zipf, src_dir, src_dir)

    # Add root files
    for root_file in ["requirements.txt", "requirements-dev.txt", "README.md", "INTEGRATION_COMPLETION_REPORT.md"]:
        add_file_if_exists(zipf, root_file)

print(f"[OK] Created: {source_zip} ({source_zip.stat().st_size / 1024:.1f} KB)")

# Create CHECKLIST.md
print("\n[4/4] Creating CHECKLIST.md...")
checklist_path = release_dir / "CHECKLIST.md"
with open(checklist_path, 'w', encoding='utf-8') as f:
    f.write(f"""# Strict Context Validation Evidence Package

**Timestamp:** {timestamp}
**Commit:** 4be2918b0c070c5a8fc53b3e0e3320ef7b289f36
**Status:** NO-GO - Technical blockers prevent validation

---

## Evidence Bundles

### A) strict_context_review_bundle.zip
**Size:** {review_zip.stat().st_size / 1024:.1f} KB
**Priority:** HIGH - Review this first
**Contents:**
- SUMMARY.md (validation summary with NO-GO verdict)
- pytest_q.txt (pytest results: 17 failed, 150 passed)
- git_state.txt (commit hash and git status)
- run_id.txt (RUN_ID: 43e160bc474e6cef)
- strict_run_stdout.txt (run output logs)
- run_1/fingerprint.json (if available)
- run_1/results_summary.json (if available)

### B) strict_context_reports.zip
**Size:** {reports_zip.stat().st_size / 1024:.1f} KB
**Priority:** MEDIUM - Full diagnostic data
**Contents:**
- Full reports/strict_context_validation/{timestamp}/ directory
- Run artifacts from runs/43e160bc474e6cef/
- Telemetry from local-telemetry/43e160bc474e6cef/

### C) strict_context_source.zip
**Size:** {source_zip.stat().st_size / 1024:.1f} KB
**Priority:** LOW - Source code reference
**Contents:**
- src/ (all source code)
- tools/ (validation and utility scripts)
- tests/ (test suite)
- docs/ (documentation)
- config/ (configuration files including strict context config)
- migrations/ (database migrations including 010_add_app_context)
- requirements.txt, requirements-dev.txt
- README.md, INTEGRATION_COMPLETION_REPORT.md

---

## Validation Status: NO-GO

### Critical Blockers

1. **Database Schema Migration Failure**
   - Migration `010_add_app_context` marked as applied but column not created
   - Discovery phase cannot save examples (17 errors)
   - Result: 0 examples processed

2. **LLM Service Unavailable**
   - ollama service not running on localhost:11434
   - Cannot perform compilation-fix or runtime-fix phases
   - Requires: ollama with model qwen2.5:14b

3. **No Processed Examples**
   - Validation tool requires `examples` table with data
   - Cannot test strict context enforcement without examples
   - Cannot run determinism tests without successful runs

### Evidence Quality

- [OK] Preflight checks completed (pytest, git state)
- [OK] Strict context config validated (3 flags enabled)
- [OK] One run completed (0 examples due to errors)
- [OK] Detailed error logs collected
- ✗ Validation tests could not run
- ✗ Determinism tests could not run
- ✗ No cross-context conversion data

---

## Required Actions

**Before claiming GO:**

1. Fix migration `010_add_app_context.sql` to add column correctly
2. Start ollama service with model `qwen2.5:14b`
3. Re-run strict context validation
4. Verify examples are discovered and processed
5. Run validation tests successfully
6. Run 2-run determinism test
7. Create new evidence packages with full validation

---

**Package Created:** {Path().absolute()}
**Bundles Location:** {release_dir.absolute()}
""")

print(f"[OK] Created: {checklist_path}")

print(f"\n{'='*80}")
print("SUMMARY")
print(f"{'='*80}")
print(f"Release directory: {release_dir.absolute()}")
print(f"\nZIP files created:")
print(f"  1. {review_zip.name} - {review_zip.stat().st_size / 1024:.1f} KB")
print(f"  2. {reports_zip.name} - {reports_zip.stat().st_size / 1024:.1f} KB")
print(f"  3. {source_zip.name} - {source_zip.stat().st_size / 1024:.1f} KB")
print(f"\nCHECKLIST: {checklist_path.name}")
print(f"\n{'='*80}")
print("STATUS: NO-GO")
print("REASON: Technical blockers prevent validation (see SUMMARY.md)")
print(f"{'='*80}")
