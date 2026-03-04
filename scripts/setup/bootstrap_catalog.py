#!/usr/bin/env python3
"""
Bootstrap API Catalog for a product family via assembly reflection.

Generates a {family}_api_catalog.json by invoking the test-examples catalog-types
command, which uses System.Reflection to extract all exported types from the
NuGet assembly. This replaces the old markdown/HTML extraction approach.

Usage:
    python scripts/bootstrap_catalog.py --family zip
    python scripts/bootstrap_catalog.py --family zip --dry-run
    python scripts/bootstrap_catalog.py --family words --package Aspose.Words --version 26.1.0
    python scripts/bootstrap_catalog.py --family cells --package Aspose.Cells --version "*" --dry-run

HEAL-01 / TASK-DLL-02: Assembly-based catalog generation (replaces markdown extraction)
"""

import argparse
import json
import logging
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict

sys.stdout.reconfigure(encoding="utf-8")
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.parent

# Known namespace prefix mappings (NuGet package name -> .NET namespace prefix)
# Some packages have different capitalization in their namespace vs package name
NAMESPACE_PREFIXES = {
    "Aspose.PDF": "Aspose.Pdf",
    "Aspose.PSD": "Aspose.PSD",
    "Aspose.Words": "Aspose.Words",
    "Aspose.Zip": "Aspose.Zip",
    "Aspose.BarCode": "Aspose.BarCode",
    "Aspose.OCR": "Aspose.OCR",
    "Aspose.Cells": "Aspose.Cells",
    "Aspose.Email": "Aspose.Email",
    "Aspose.Imaging": "Aspose.Imaging",
    "Aspose.Slides": "Aspose.Slides",
    "Aspose.Tasks": "Aspose.Tasks",
    "Aspose.CAD": "Aspose.CAD",
    "Aspose.3D": "Aspose.ThreeD",
    "Aspose.HTML": "Aspose.Html",
    "Aspose.SVG": "Aspose.Svg",
    "Aspose.Font": "Aspose.Font",
    "Aspose.Drawing": "Aspose.Drawing",
    "Aspose.Page": "Aspose.Page",
    "Aspose.GIS": "Aspose.Gis",
    "Aspose.TeX": "Aspose.TeX",
}


def invoke_catalog_types(package: str, version: str, namespace_prefix: str) -> dict:
    """
    Invoke test-examples/Program.cs catalog-types command to extract assembly types.

    Runs `dotnet run --project {PROJECT_ROOT}/test-examples -- catalog-types` with
    the given package, version, and namespace prefix. Parses the JSON output,
    skipping any build warnings that appear before the JSON block.

    Args:
        package: NuGet package name (e.g., "Aspose.Zip")
        version: NuGet package version (e.g., "25.12.0" or "*" for latest)
        namespace_prefix: Namespace prefix to filter types (e.g., "Aspose.Zip")

    Returns:
        dict with Namespaces, Types, TypesFullMap, AmbiguousTypes,
        AssemblyVersion, TotalTypes, TotalNamespaces, etc.

    Raises:
        RuntimeError: If the dotnet command fails or times out
        ValueError: If no JSON output is found
    """
    logger.info(f"Invoking catalog-types for {package} v{version} (prefix: {namespace_prefix})...")

    cmd = [
        "dotnet",
        "run",
        "--project",
        str(PROJECT_ROOT / "test-examples" / "AsposeZipValidator.csproj"),
        "--",
        "catalog-types",
        "--package",
        package,
        "--version",
        version,
        "--namespace-prefix",
        namespace_prefix,
    ]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, cwd=PROJECT_ROOT, timeout=120
        )

        if result.returncode != 0:
            logger.error(f"Catalog extraction failed with code {result.returncode}")
            logger.error(f"STDERR: {result.stderr}")
            raise RuntimeError(f"Catalog extraction failed: {result.stderr}")

        # Filter out build warnings — find the first line starting with '{'
        output_lines = result.stdout.strip().split("\n")
        json_start = -1
        for i, line in enumerate(output_lines):
            if line.strip().startswith("{"):
                json_start = i
                break

        if json_start == -1:
            raise ValueError(
                "No JSON output found from catalog-types command. "
                f"Output was: {result.stdout[:500]}"
            )

        json_output = "\n".join(output_lines[json_start:])
        return json.loads(json_output)

    except subprocess.TimeoutExpired:
        raise RuntimeError("Catalog extraction timed out after 120 seconds")
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON output: {e}")
        logger.error(f"Output was: {result.stdout[:500]}")
        raise


def transform_assembly_catalog(assembly_catalog: dict, family: str) -> Dict:
    """
    Transform raw catalog-types output into the standard catalog JSON format.

    Converts the raw assembly reflection output (PascalCase keys) into the
    normalized catalog structure used by the rest of the pipeline.

    Args:
        assembly_catalog: Raw dict from invoke_catalog_types()
        family: Product family name (e.g., "zip", "words")

    Returns:
        dict with _metadata, namespaces, types, using_directive_map,
        and namespace_ambiguous_types sections.
    """
    namespaces = sorted(assembly_catalog.get("Namespaces", []))
    types = dict(sorted(assembly_catalog.get("Types", {}).items()))
    ambiguous_types = assembly_catalog.get("AmbiguousTypes", {})
    assembly_version = assembly_catalog.get("AssemblyVersion")
    total_types = assembly_catalog.get("TotalTypes", len(types))
    total_namespaces = assembly_catalog.get("TotalNamespaces", len(namespaces))

    # Build using directive map: type -> "using {namespace};"
    using_directive_map = {t: f"using {ns};" for t, ns in types.items()}

    return {
        "_metadata": {
            "family": family,
            "source": f"Aspose.{family.capitalize()} v{assembly_version or 'unknown'} assembly (via reflection)",
            "generated_by": "scripts/bootstrap_catalog.py (assembly reflection)",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "assembly_version": assembly_version,
            "total_types": total_types,
            "total_namespaces": total_namespaces,
            "total_ambiguous_types": len(ambiguous_types),
            "extraction_method": "assembly_reflection",
            "assembly_validation": {
                "enabled": True,
                "assembly_version": assembly_version,
                "direct_extraction": True,
            },
        },
        "namespaces": namespaces,
        "types": types,
        "using_directive_map": dict(sorted(using_directive_map.items())),
        "namespace_ambiguous_types": ambiguous_types,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Bootstrap API catalog for a family via assembly reflection"
    )
    parser.add_argument(
        "--family", required=True, help="Product family (e.g., zip, words, cells)"
    )
    parser.add_argument(
        "--package", help="NuGet package name (default: Aspose.{Family})"
    )
    parser.add_argument(
        "--version", default="*", help='NuGet package version (default: "*" for latest)'
    )
    parser.add_argument(
        "--namespace-prefix",
        help="Namespace prefix to filter (default: same as package name)",
    )
    parser.add_argument(
        "--output",
        help="Output JSON path (default: config/families/{family}_api_catalog.json)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print catalog JSON to stdout without writing to file",
    )
    args = parser.parse_args()

    family = args.family

    # Derive defaults from family name
    package = args.package or f"Aspose.{family.capitalize()}"
    version = args.version
    # Use known mapping for namespace prefix, fall back to package name
    namespace_prefix = args.namespace_prefix or NAMESPACE_PREFIXES.get(package, package)

    output_path = Path(args.output) if args.output else (
        PROJECT_ROOT / "config" / "families" / f"{family}_api_catalog.json"
    )

    logger.info(f"Bootstrapping API catalog for '{family}'")
    logger.info(f"  Package: {package}")
    logger.info(f"  Version: {version}")
    logger.info(f"  Namespace prefix: {namespace_prefix}")

    # Step 1: Invoke assembly reflection
    assembly_catalog = invoke_catalog_types(package, version, namespace_prefix)
    raw_types = assembly_catalog.get("TotalTypes", 0)
    raw_namespaces = assembly_catalog.get("TotalNamespaces", 0)
    logger.info(f"Assembly contains {raw_types} types in {raw_namespaces} namespaces")

    # Step 2: Transform to standard catalog format
    catalog = transform_assembly_catalog(assembly_catalog, family)

    # Step 3: Output
    if args.dry_run:
        print(json.dumps(catalog, indent=2))
        logger.info(f"[DRY RUN] Would write to {output_path}")
    else:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(catalog, indent=2), encoding="utf-8")
        logger.info(f"Wrote catalog to {output_path}")

    # Summary
    final_types = len(catalog.get("types", {}))
    final_namespaces = len(catalog.get("namespaces", []))
    ambiguous = len(catalog.get("namespace_ambiguous_types", {}))

    print(f"\n{'='*60}")
    print(f"Family:           {family}")
    print(f"Package:          {package}")
    print(f"Assembly Version: {catalog['_metadata'].get('assembly_version', 'N/A')}")
    print(f"Types:            {final_types}")
    print(f"Namespaces:       {final_namespaces}")
    print(f"Ambiguous Types:  {ambiguous}")
    print(f"Extraction:       Assembly Reflection (direct)")
    print(f"Output:           {output_path}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
