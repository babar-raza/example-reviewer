#!/usr/bin/env python3
"""
Batch generate API catalogs for multiple families using assembly reflection.
"""
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple

CATALOG_SPECS = [
    ("imaging", "Aspose.Imaging", "*", "Aspose.Imaging"),
    ("slides", "Aspose.Slides.NET", "*", "Aspose.Slides"),
    ("email", "Aspose.Email", "*", "Aspose.Email"),
    ("tex", "Aspose.TeX", "*", "Aspose.TeX"),
    ("cad", "Aspose.CAD", "*", "Aspose.CAD"),
    ("html", "Aspose.HTML", "*", "Aspose.Html"),
    ("page", "Aspose.Page", "*", "Aspose.Page"),
    ("tasks", "Aspose.Tasks", "*", "Aspose.Tasks"),
]


def generate_catalog(family: str, package: str, version: str, namespace: str) -> Tuple[bool, str]:
    """Generate API catalog for a family."""

    script_path = Path(__file__).parent / "extract_assembly_catalog.py"
    output_path = Path(__file__).parent.parent / "config" / "families" / f"{family}_api_catalog.json"

    print(f"[*] Generating catalog for {family}...")
    print(f"    Package: {package} ({version})")
    print(f"    Namespace: {namespace}")

    try:
        result = subprocess.run(
            [
                sys.executable,
                str(script_path),
                package,
                version,
                namespace,
                "--full",
                "--output",
                str(output_path)
            ],
            capture_output=True,
            text=True,
            timeout=300
        )

        if result.returncode == 0:
            print(f"    [OK] Success: {output_path}")
            # Parse output for stats
            if "types found" in result.stdout.lower():
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'types found' in line.lower() or 'namespaces' in line.lower():
                        print(f"    [STAT] {line.strip()}")
            return True, ""
        else:
            error_msg = result.stderr or result.stdout
            print(f"    [FAIL] Failed: {error_msg[:200]}")
            return False, error_msg

    except subprocess.TimeoutExpired:
        error_msg = "Timeout after 300 seconds"
        print(f"    [FAIL] {error_msg}")
        return False, error_msg
    except Exception as e:
        error_msg = str(e)
        print(f"    [FAIL] Error: {error_msg}")
        return False, error_msg


def main():
    """Generate all catalogs."""

    print("=" * 80)
    print("BATCH API CATALOG GENERATION")
    print("=" * 80)
    print(f"Families to process: {len(CATALOG_SPECS)}")
    print()

    successes = []
    failures = []

    for family, package, version, namespace in CATALOG_SPECS:
        success, error = generate_catalog(family, package, version, namespace)
        if success:
            successes.append(family)
        else:
            failures.append((family, error))
        print()

    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"[OK] Successful: {len(successes)}")
    print(f"[FAIL] Failed: {len(failures)}")
    print()

    if successes:
        print("Successful families:")
        for family in successes:
            print(f"  [OK] {family}")
        print()

    if failures:
        print("Failed families:")
        for family, error in failures:
            print(f"  [FAIL] {family}")
            print(f"         Error: {error[:100]}")
        print()

    print("=" * 80)

    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
