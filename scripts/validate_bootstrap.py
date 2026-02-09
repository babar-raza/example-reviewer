#!/usr/bin/env python3
"""
Validate Bootstrap — Check API catalog completeness and quality.

Validates that a generated catalog meets minimum quality thresholds:
- Type count >= 100 (for major product families)
- Namespace count >= 10
- All types have valid using directives
- No orphaned namespaces (namespace in list but no types in it)

Usage:
    python scripts/validate_bootstrap.py --family zip
    python scripts/validate_bootstrap.py --family zip --min-types 50

HEAL-01: Phase 0 Bootstrap Script (Task 3)
"""

import argparse
import json
import logging
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent


def load_catalog(family: str, path: str = None) -> dict:
    """Load catalog JSON."""
    catalog_path = Path(path) if path else (
        PROJECT_ROOT / "config" / "families" / f"{family}_api_catalog.json"
    )
    if not catalog_path.exists():
        raise FileNotFoundError(f"Catalog not found: {catalog_path}")
    return json.loads(catalog_path.read_text(encoding="utf-8"))


def validate(catalog: dict, min_types: int = 100, min_namespaces: int = 10) -> list:
    """Run validation checks. Returns list of (level, message) tuples."""
    results = []

    types = catalog.get("types", {})
    namespaces = catalog.get("namespaces", [])
    using_map = catalog.get("using_directive_map", {})

    # Check type count
    if len(types) >= min_types:
        results.append(("PASS", f"Type count: {len(types)} >= {min_types}"))
    else:
        results.append(("FAIL", f"Type count: {len(types)} < {min_types}"))

    # Check namespace count
    if len(namespaces) >= min_namespaces:
        results.append(("PASS", f"Namespace count: {len(namespaces)} >= {min_namespaces}"))
    else:
        results.append(("FAIL", f"Namespace count: {len(namespaces)} < {min_namespaces}"))

    # Check all types have using directives
    missing_directives = [t for t in types if t not in using_map]
    if not missing_directives:
        results.append(("PASS", f"All {len(types)} types have using directives"))
    else:
        results.append(("FAIL", f"{len(missing_directives)} types missing using directives: {missing_directives[:5]}"))

    # Check for orphaned namespaces
    used_namespaces = set(types.values())
    orphaned = [ns for ns in namespaces if ns not in used_namespaces]
    if not orphaned:
        results.append(("PASS", "No orphaned namespaces"))
    else:
        results.append(("WARN", f"{len(orphaned)} orphaned namespaces: {orphaned[:5]}"))

    # Check using directive format
    bad_directives = [
        t for t, d in using_map.items()
        if not d.startswith("using ") or not d.endswith(";")
    ]
    if not bad_directives:
        results.append(("PASS", "All using directives properly formatted"))
    else:
        results.append(("FAIL", f"{len(bad_directives)} malformed using directives"))

    # Coverage: what % of namespaces have at least one type
    ns_with_types = len(used_namespaces)
    coverage = ns_with_types / len(namespaces) * 100 if namespaces else 0
    if coverage >= 95:
        results.append(("PASS", f"Namespace coverage: {coverage:.1f}%"))
    elif coverage >= 80:
        results.append(("WARN", f"Namespace coverage: {coverage:.1f}% (below 95%)"))
    else:
        results.append(("FAIL", f"Namespace coverage: {coverage:.1f}% (below 80%)"))

    return results


def main():
    parser = argparse.ArgumentParser(description="Validate API catalog")
    parser.add_argument("--family", required=True, help="Product family")
    parser.add_argument("--path", help="Explicit catalog path")
    parser.add_argument("--min-types", type=int, default=100, help="Minimum types")
    parser.add_argument("--min-namespaces", type=int, default=10, help="Minimum namespaces")
    args = parser.parse_args()

    try:
        catalog = load_catalog(args.family, args.path)
    except FileNotFoundError as e:
        logger.error(str(e))
        sys.exit(1)

    results = validate(catalog, args.min_types, args.min_namespaces)

    # Print results
    print(f"\nValidation Results for '{args.family}' API Catalog")
    print("=" * 50)
    passes = fails = warns = 0
    for level, msg in results:
        icon = {"PASS": "[OK]", "FAIL": "[!!]", "WARN": "[??]"}[level]
        print(f"  {icon} {msg}")
        if level == "PASS":
            passes += 1
        elif level == "FAIL":
            fails += 1
        else:
            warns += 1

    print(f"\nSummary: {passes} passed, {fails} failed, {warns} warnings")

    if fails > 0:
        sys.exit(1)
    print("\nCatalog validation PASSED")


if __name__ == "__main__":
    main()
