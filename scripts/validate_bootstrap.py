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

# Known-bad namespaces that should NOT be in validated catalogs
# NOTE: After v26.1.0 reflection verification, Drawing.Charts DOES exist!
KNOWN_BAD_NAMESPACES = {
    "words": [],  # All namespaces validated via assembly reflection
    "zip": [],  # ZIP catalog is clean
}


def load_catalog(family: str, path: str = None) -> dict:
    """Load catalog JSON."""
    catalog_path = Path(path) if path else (
        PROJECT_ROOT / "config" / "families" / f"{family}_api_catalog.json"
    )
    if not catalog_path.exists():
        raise FileNotFoundError(f"Catalog not found: {catalog_path}")
    return json.loads(catalog_path.read_text(encoding="utf-8"))


def validate(catalog: dict, min_types: int = 100, min_namespaces: int = 10, family: str = None) -> list:
    """Run validation checks. Returns list of (level, message) tuples."""
    results = []

    types = catalog.get("types", {})
    namespaces = catalog.get("namespaces", [])
    using_map = catalog.get("using_directive_map", {})
    metadata = catalog.get("_metadata", {})
    assembly_validation = metadata.get("assembly_validation", {})

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

    # Assembly Validation Checks (Layer 2)
    if assembly_validation:
        assembly_enabled = assembly_validation.get("enabled", False)
        if assembly_enabled:
            results.append(("PASS", "Assembly validation: ENABLED"))

            # Check assembly version is recorded
            assembly_version = assembly_validation.get("assembly_version")
            if assembly_version:
                results.append(("PASS", f"Assembly version: {assembly_version}"))
            else:
                results.append(("WARN", "Assembly version not recorded"))

            # Check validation stats (for legacy filtered catalogs)
            types_before = assembly_validation.get("types_before_validation", 0)
            types_after = assembly_validation.get("types_after_validation", 0)
            types_removed = assembly_validation.get("types_removed", 0)

            if types_before > 0:
                # Legacy filtered catalog — show filtering stats
                if types_removed > 0:
                    removal_pct = (types_removed / types_before * 100) if types_before > 0 else 0
                    results.append(("PASS", f"Types filtered: {types_removed} removed ({removal_pct:.1f}%)"))
                else:
                    results.append(("PASS", "Types filtered: 0 removed (100% match)"))

            # Check for known-bad namespaces
            if family and family in KNOWN_BAD_NAMESPACES:
                bad_namespaces = KNOWN_BAD_NAMESPACES[family]
                found_bad = [ns for ns in bad_namespaces if ns in namespaces]
                if not found_bad:
                    results.append(("PASS", f"Known-bad namespaces: None found (checked {len(bad_namespaces)})"))
                else:
                    results.append(("FAIL", f"Known-bad namespaces found: {found_bad}"))

            # Direct extraction check (TASK-DLL-02: assembly reflection catalogs)
            direct_extraction = assembly_validation.get("direct_extraction", False)
            if direct_extraction:
                results.append(("PASS", "Direct assembly extraction: YES (no markdown intermediary)"))
            else:
                results.append(("WARN", "Direct assembly extraction: NO (filtered from markdown)"))

        else:
            results.append(("FAIL", "Assembly validation: DISABLED (expected enabled=True)"))
    else:
        results.append(("WARN", "Assembly validation: NOT CONFIGURED"))

    # Extraction method check (TASK-DLL-02)
    extraction_method = metadata.get("extraction_method")
    if extraction_method:
        if extraction_method == "assembly_reflection":
            results.append(("PASS", f"Extraction method: {extraction_method}"))
        else:
            results.append(("WARN", f"Extraction method: {extraction_method} (expected assembly_reflection)"))

    # Assembly version in top-level metadata
    top_assembly_version = metadata.get("assembly_version")
    if top_assembly_version:
        results.append(("PASS", f"Metadata assembly_version: {top_assembly_version}"))
    else:
        results.append(("WARN", "Metadata assembly_version: not recorded"))

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

    results = validate(catalog, args.min_types, args.min_namespaces, args.family)

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
