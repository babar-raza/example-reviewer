#!/usr/bin/env python3
"""Create Phase-2 measurement results ZIP with proper structure."""

import zipfile
from pathlib import Path

# Base paths
base = Path("c:/Users/prora/OneDrive/Documents/GitHub/example-reviewer")
reports_dir = base / "reports/e2e/run_20260122_154747"

# Output ZIP (create in temp location to avoid OneDrive locking)
import tempfile
output_zip = Path(tempfile.gettempdir()) / "phase2_measurement_results.zip"
final_output = base / "phase2_measurement_results.zip"

# Files to include with their paths in the ZIP
files_to_zip = [
    (reports_dir / "run_1/fingerprint.json", "run_1/fingerprint.json"),
    (reports_dir / "run_2/fingerprint.json", "run_2/fingerprint.json"),
    (reports_dir / "determinism_comparison.json", "determinism_comparison.json"),
    (reports_dir / "e2e_summary.json", "e2e_summary.json"),
    (reports_dir / "failure_analytics.json", "failure_analytics.json"),
    (base / "phase2_run_output.txt", "phase2_run_output.txt"),
]

# Create ZIP
with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
    for source_path, archive_name in files_to_zip:
        if source_path.exists():
            zf.write(source_path, archive_name)
            print(f"Added: {archive_name}")
        else:
            print(f"WARNING: File not found: {source_path}")

print(f"\nZIP created: {output_zip}")
print(f"Size: {output_zip.stat().st_size:,} bytes")

# Move to final location
import shutil
shutil.move(str(output_zip), str(final_output))
print(f"Moved to: {final_output}")
