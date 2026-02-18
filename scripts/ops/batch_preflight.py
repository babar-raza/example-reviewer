#!/usr/bin/env python3
"""
Run preflight discovery checks for all families.
Tests content discovery without running compilation/verification.
"""
import subprocess
import sys
import json
from pathlib import Path
from typing import Dict, List, Tuple

FAMILIES = [
    "imaging",
    "slides",
    "email",
    "tex",
    "cad",
    "html",
    "page",
    "tasks",
    "medical"  # Tolerating missing repo
]


def run_preflight(family: str) -> Tuple[bool, Dict]:
    """Run preflight check for a family."""

    print(f"[*] Running preflight for {family}...")

    try:
        # Use the MCP tool via CLI
        result = subprocess.run(
            [
                sys.executable,
                "-m", "src.cli.main",
                "verify",
                "--family", family,
                "--max-examples", "5",  # Small preflight test
                "--skip-compile",  # Discovery only
                "--dry-run"
            ],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=Path(__file__).parent.parent
        )

        output = result.stdout + result.stderr

        # Parse for discovery count
        discovered = 0
        for line in output.split('\n'):
            if 'discovered' in line.lower() or 'found' in line.lower():
                # Try to extract number
                parts = line.split()
                for i, part in enumerate(parts):
                    if part.isdigit():
                        discovered = int(part)
                        break

        stats = {
            "discovered": discovered,
            "success": result.returncode == 0 or discovered > 0,
            "output_sample": output[:500]
        }

        if stats["success"]:
            print(f"    [OK] Discovered {discovered} examples")
        else:
            print(f"    [WARN] Return code: {result.returncode}")
            if discovered > 0:
                print(f"    [STAT] Discovered {discovered} examples (partial success)")

        return stats["success"] or discovered > 0, stats

    except subprocess.TimeoutExpired:
        print(f"    [FAIL] Timeout after 120 seconds")
        return False, {"error": "timeout"}
    except Exception as e:
        print(f"    [FAIL] Error: {str(e)}")
        return False, {"error": str(e)}


def main():
    """Run preflight for all families."""

    print("=" * 80)
    print("BATCH PREFLIGHT DISCOVERY CHECK")
    print("=" * 80)
    print(f"Families to test: {len(FAMILIES)}")
    print()

    results = {}

    for family in FAMILIES:
        success, stats = run_preflight(family)
        results[family] = {
            "success": success,
            **stats
        }
        print()

    # Write results
    results_file = Path(__file__).parent.parent / "preflight_results.json"
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)

    successful = [f for f, r in results.items() if r["success"]]
    failed = [f for f, r in results.items() if not r["success"]]

    total_discovered = sum(r.get("discovered", 0) for r in results.values())

    print(f"[OK] Successful: {len(successful)}/{len(FAMILIES)}")
    print(f"[FAIL] Failed: {len(failed)}/{len(FAMILIES)}")
    print(f"[STAT] Total examples discovered: {total_discovered}")
    print()

    if successful:
        print("Families ready for pipeline:")
        for family in successful:
            discovered = results[family].get("discovered", 0)
            print(f"  [OK] {family:15s} - {discovered:4d} examples")
        print()

    if failed:
        print("Families needing attention:")
        for family in failed:
            error = results[family].get("error", "unknown")
            print(f"  [FAIL] {family:15s} - {error}")
        print()

    print(f"Full results: {results_file}")
    print("=" * 80)

    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
