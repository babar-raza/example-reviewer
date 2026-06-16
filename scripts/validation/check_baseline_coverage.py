#!/usr/bin/env python3
"""
Validator: Check that all configured families have committed baselines.

Maps to RC-RATE-005: Incomplete family baseline coverage.
Families in config/families/ should have corresponding baseline files
in .benchmarks/baselines/.

Exit codes:
    0 = All families have baselines (or gaps are within tolerance)
    1 = Too many families missing baselines
"""
import sys
from pathlib import Path

FAMILIES_DIR = Path("config/families")
BASELINES_DIR = Path(".benchmarks/baselines")
MAX_MISSING_ALLOWED = 3  # tolerance for families without baselines


def main():
    if not FAMILIES_DIR.exists():
        print(f"SKIP: {FAMILIES_DIR} not found")
        return 0

    # Find all family names from config files (e.g., zip.json -> zip)
    family_configs = sorted(
        p.stem for p in FAMILIES_DIR.glob("*.json")
        if not p.stem.endswith("_behavioral_patterns")
        and not p.stem.endswith("_review_hints")
    )

    if not family_configs:
        print("SKIP: No family config files found")
        return 0

    missing = []
    for family in family_configs:
        baseline = BASELINES_DIR / f"{family}_baseline.json"
        if not baseline.exists():
            missing.append(family)

    print(f"Families configured: {len(family_configs)}")
    print(f"Families with baselines: {len(family_configs) - len(missing)}")

    if missing:
        print(f"Missing baselines ({len(missing)}):")
        for f in missing:
            print(f"  - {f}")

    if len(missing) > MAX_MISSING_ALLOWED:
        print(f"\nFAIL: {len(missing)} families missing baselines (max allowed: {MAX_MISSING_ALLOWED})")
        return 1

    if missing:
        print(f"\nPASS (with {len(missing)} missing baseline(s), within tolerance of {MAX_MISSING_ALLOWED})")
    else:
        print("PASS: All families have baselines")
    return 0


if __name__ == "__main__":
    sys.exit(main())
