#!/usr/bin/env python3
"""Create failure artifacts zip."""
import zipfile
from pathlib import Path

def create_zip():
    """Create failure_artifacts_before_fix.zip."""

    output_zip = Path("release/failure_artifacts_before_fix.zip")
    output_zip.parent.mkdir(exist_ok=True)

    with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Add failures JSON
        json_file = Path("reports/phase2_gateb_verify/run2_failures.json")
        if json_file.exists():
            zf.write(json_file, "run2_failures.json")
            print(f"Added: {json_file}")

        # Add README
        readme = Path("reports/phase2_gateb_verify/failure_artifacts/README.md")
        if readme.exists():
            zf.write(readme, "failure_artifacts/README.md")
            print(f"Added: {readme}")

    print(f"\nCreated: {output_zip}")
    print(f"Size: {output_zip.stat().st_size:,} bytes")

if __name__ == "__main__":
    create_zip()
