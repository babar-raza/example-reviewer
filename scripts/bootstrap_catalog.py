#!/usr/bin/env python3
"""
Bootstrap API Catalog for a product family.

Generates a {family}_api_catalog.json from test-reference documentation files.
Scans .md/.html API reference docs to extract type names, namespaces, and
using directives.

Usage:
    python scripts/bootstrap_catalog.py --family zip --auto
    python scripts/bootstrap_catalog.py --family zip --reference-dir test-reference/zip
    python scripts/bootstrap_catalog.py --family words --reference-dir test-reference/words --dry-run

HEAL-01: Phase 0 Bootstrap Script (Task 1)
"""

import argparse
import json
import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Set, Tuple

sys.stdout.reconfigure(encoding="utf-8")
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent


def find_reference_dir(family: str) -> Path:
    """Auto-detect reference directory for a family."""
    candidates = [
        PROJECT_ROOT / "test-reference" / family,
        PROJECT_ROOT / "docs" / "api-reference" / family,
    ]
    for c in candidates:
        if c.exists():
            return c
    raise FileNotFoundError(
        f"No reference directory found for family '{family}'. "
        f"Searched: {', '.join(str(c) for c in candidates)}"
    )


def extract_types_from_docs(reference_dir: Path) -> Tuple[Dict[str, str], Set[str]]:
    """
    Extract type->namespace mappings from API reference documentation.

    Returns:
        Tuple of (types_dict, namespaces_set)
    """
    types: Dict[str, str] = {}
    namespaces: Set[str] = set()

    doc_files = list(reference_dir.rglob("*.md")) + list(reference_dir.rglob("*.html"))
    logger.info(f"Scanning {len(doc_files)} documentation files in {reference_dir}")

    # Pattern: "Aspose.Something.TypeName" in headings, titles, or code
    fqn_pattern = re.compile(r"\b(Aspose(?:\.\w+)+)\.([A-Z]\w+)\b")
    # Pattern: namespace declarations
    ns_pattern = re.compile(r"\bnamespace\s+(Aspose(?:\.\w+)+)")

    for doc_file in doc_files:
        try:
            content = doc_file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        # Extract fully qualified type names
        for match in fqn_pattern.finditer(content):
            namespace = match.group(1)
            type_name = match.group(2)
            # Skip common false positives
            if type_name in ("NET", "Api", "Com", "Zip"):
                continue
            namespaces.add(namespace)
            if type_name not in types:
                types[type_name] = namespace

        # Extract explicit namespace declarations
        for match in ns_pattern.finditer(content):
            namespaces.add(match.group(1))

    return types, namespaces


def build_catalog(
    family: str,
    types: Dict[str, str],
    namespaces: Set[str],
    reference_dir: Path,
) -> Dict:
    """Build the catalog JSON structure."""
    sorted_namespaces = sorted(namespaces)
    using_directive_map = {t: f"using {ns};" for t, ns in types.items()}

    # Detect ambiguous types
    ns_by_type: Dict[str, List[str]] = {}
    for t, ns in types.items():
        ns_by_type.setdefault(t, []).append(ns)
    ambiguous = {t: nss for t, nss in ns_by_type.items() if len(nss) > 1}

    return {
        "_metadata": {
            "family": family,
            "source": f"{reference_dir} API documentation ({len(list(reference_dir.rglob('*')))} files)",
            "generated_by": "scripts/bootstrap_catalog.py (HEAL-01)",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_types": len(types),
            "total_namespaces": len(sorted_namespaces),
        },
        "namespaces": sorted_namespaces,
        "types": dict(sorted(types.items())),
        "namespace_ambiguous_types": ambiguous,
        "using_directive_map": dict(sorted(using_directive_map.items())),
    }


def main():
    parser = argparse.ArgumentParser(description="Bootstrap API catalog for a family")
    parser.add_argument("--family", required=True, help="Product family (e.g., zip, words)")
    parser.add_argument("--reference-dir", help="Path to API reference docs")
    parser.add_argument("--output", help="Output JSON path (default: config/families/{family}_api_catalog.json)")
    parser.add_argument("--auto", action="store_true", help="Auto-detect reference directory")
    parser.add_argument("--dry-run", action="store_true", help="Print results without writing")
    args = parser.parse_args()

    family = args.family

    if args.reference_dir:
        reference_dir = Path(args.reference_dir)
    elif args.auto:
        reference_dir = find_reference_dir(family)
    else:
        parser.error("Provide --reference-dir or --auto")

    if not reference_dir.exists():
        logger.error(f"Reference directory not found: {reference_dir}")
        sys.exit(1)

    logger.info(f"Bootstrapping API catalog for '{family}' from {reference_dir}")

    types, namespaces = extract_types_from_docs(reference_dir)
    logger.info(f"Extracted {len(types)} types in {len(namespaces)} namespaces")

    if len(types) < 5:
        logger.warning(f"Only {len(types)} types found. Check reference directory content.")

    catalog = build_catalog(family, types, namespaces, reference_dir)

    output_path = Path(args.output) if args.output else (
        PROJECT_ROOT / "config" / "families" / f"{family}_api_catalog.json"
    )

    if args.dry_run:
        print(json.dumps(catalog, indent=2))
        logger.info(f"[DRY RUN] Would write to {output_path}")
    else:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(catalog, indent=2), encoding="utf-8")
        logger.info(f"Wrote catalog to {output_path}")

    # Summary
    print(f"\n{'='*50}")
    print(f"Family: {family}")
    print(f"Types: {len(types)}")
    print(f"Namespaces: {len(namespaces)}")
    print(f"Output: {output_path}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
