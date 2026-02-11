#!/usr/bin/env python3
"""
DEPRECATED: Validate API Catalog Against NuGet Assembly.

===========================================================================
DEPRECATION NOTICE (TASK-DLL-02, 2026-02-10):
    This script was used in the old two-step workflow where catalogs were
    first extracted from markdown/HTML documentation, then filtered against
    the actual NuGet assembly to remove false positives.

    Since bootstrap_catalog.py now generates catalogs DIRECTLY from assembly
    reflection (via `dotnet run -- catalog-types`), there is no longer a need
    for this intermediate validation step. The assembly is the source of truth
    from the start, so no filtering is required.

    This script is kept for historical reference only.

    Replacement: scripts/bootstrap_catalog.py (assembly reflection mode)
===========================================================================

Cross-references a documentation-extracted API catalog with the actual types
in a NuGet package DLL using reflection. Only types that exist in the assembly
are kept in the validated output.

Usage:
    python scripts/validate_nuget_assembly.py \
        --package Aspose.Words \
        --version 26.1.0 \
        --namespace-prefix Aspose.Words \
        --catalog artifacts/validation/words_catalog_raw.json \
        --output artifacts/validation/words_catalog_validated.json

HEAL-01: Layer 2 Validation - Assembly-Based Filtering
"""

import argparse
import json
import logging
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Set

sys.stdout.reconfigure(encoding="utf-8")
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent


def invoke_catalog_types(package: str, version: str, namespace_prefix: str) -> dict:
    """
    Invoke test-examples/Program.cs catalog-types command to extract assembly types.

    Returns:
        dict with Namespaces, Types, TypesFullMap, AssemblyVersion, etc.
    """
    logger.info(f"Invoking catalog-types for {package} v{version}...")

    cmd = [
        "dotnet",
        "run",
        "--project",
        str(PROJECT_ROOT / "test-examples"),
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

        # Filter out build warnings from JSON output
        output_lines = result.stdout.strip().split("\n")
        json_start = -1
        for i, line in enumerate(output_lines):
            if line.strip().startswith("{"):
                json_start = i
                break

        if json_start == -1:
            raise ValueError("No JSON output found from catalog-types command")

        json_output = "\n".join(output_lines[json_start:])
        return json.loads(json_output)

    except subprocess.TimeoutExpired:
        raise RuntimeError("Catalog extraction timed out after 120 seconds")
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON output: {e}")
        logger.error(f"Output was: {result.stdout[:500]}")
        raise


def load_raw_catalog(path: Path) -> dict:
    """Load raw catalog JSON from bootstrap_catalog.py output."""
    if not path.exists():
        raise FileNotFoundError(f"Raw catalog not found: {path}")

    logger.info(f"Loading raw catalog from {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def validate_catalog_against_assembly(
    raw_catalog: dict, assembly_data: dict
) -> tuple[dict, dict]:
    """
    Cross-reference raw catalog with assembly data and filter out invalid types.

    Returns:
        Tuple of (validated_catalog, validation_report)
    """
    logger.info("Cross-referencing catalog with assembly types...")

    raw_types = raw_catalog.get("types", {})
    raw_namespaces = set(raw_catalog.get("namespaces", []))

    assembly_types = assembly_data.get("Types", {})
    assembly_namespaces = set(assembly_data.get("Namespaces", []))

    # Filter types: keep only those that exist in assembly
    validated_types = {}
    removed_types = {}

    for type_name, namespace in raw_types.items():
        if type_name in assembly_types:
            # Type exists in assembly
            assembly_ns = assembly_types[type_name]

            if assembly_ns == namespace:
                # Exact match - keep it
                validated_types[type_name] = namespace
            else:
                # Type exists but in different namespace
                logger.warning(
                    f"Type '{type_name}': docs say '{namespace}', assembly says '{assembly_ns}' - using assembly"
                )
                validated_types[type_name] = assembly_ns
                removed_types[f"{type_name} (wrong ns)"] = {
                    "docs_namespace": namespace,
                    "assembly_namespace": assembly_ns,
                }
        else:
            # Type does NOT exist in assembly - remove it
            removed_types[type_name] = namespace

    # Filter namespaces: keep only those that exist in assembly
    validated_namespaces = []
    removed_namespaces = []

    for ns in raw_namespaces:
        if ns in assembly_namespaces:
            validated_namespaces.append(ns)
        else:
            removed_namespaces.append(ns)
            logger.warning(f"Namespace '{ns}' found in docs but NOT in assembly - removed")

    # Sort for consistency
    validated_namespaces.sort()

    # Build validated catalog
    validated_catalog = {
        "_metadata": {
            **raw_catalog.get("_metadata", {}),
            "assembly_validation": {
                "enabled": True,
                "assembly_version": assembly_data.get("AssemblyVersion"),
                "assembly_full_name": assembly_data.get("AssemblyFullName"),
                "validated_at": datetime.now(timezone.utc).isoformat(),
                "types_before_validation": len(raw_types),
                "types_after_validation": len(validated_types),
                "types_removed": len(removed_types),
                "namespaces_before_validation": len(raw_namespaces),
                "namespaces_after_validation": len(validated_namespaces),
                "namespaces_removed": len(removed_namespaces),
                "removed_namespaces": removed_namespaces,
            },
        },
        "namespaces": validated_namespaces,
        "types": dict(sorted(validated_types.items())),
        "using_directive_map": {
            t: f"using {ns};" for t, ns in validated_types.items()
        },
        "namespace_ambiguous_types": raw_catalog.get("namespace_ambiguous_types", {}),
    }

    # Validation report
    validation_report = {
        "summary": {
            "types_kept": len(validated_types),
            "types_removed": len(removed_types),
            "namespaces_kept": len(validated_namespaces),
            "namespaces_removed": len(removed_namespaces),
        },
        "removed_types": removed_types,
        "removed_namespaces": removed_namespaces,
        "assembly_info": {
            "version": assembly_data.get("AssemblyVersion"),
            "full_name": assembly_data.get("AssemblyFullName"),
            "total_types_in_assembly": len(assembly_types),
            "total_namespaces_in_assembly": len(assembly_namespaces),
        },
    }

    return validated_catalog, validation_report


def generate_validation_report(report: dict, output_path: Path):
    """Generate human-readable validation report."""
    report_lines = [
        "=" * 70,
        "API Catalog Assembly Validation Report",
        "=" * 70,
        "",
        f"Assembly: {report['assembly_info']['full_name']}",
        f"Version: {report['assembly_info']['version']}",
        "",
        "Summary:",
        f"  Types Kept: {report['summary']['types_kept']}",
        f"  Types Removed: {report['summary']['types_removed']}",
        f"  Namespaces Kept: {report['summary']['namespaces_kept']}",
        f"  Namespaces Removed: {report['summary']['namespaces_removed']}",
        "",
    ]

    if report["removed_namespaces"]:
        report_lines.append("Removed Namespaces (not found in assembly):")
        for ns in report["removed_namespaces"]:
            report_lines.append(f"  - {ns}")
        report_lines.append("")

    if report["removed_types"]:
        report_lines.append(
            f"Removed Types ({len(report['removed_types'])} total - showing first 50):"
        )
        for i, (type_name, info) in enumerate(report["removed_types"].items()):
            if i >= 50:
                report_lines.append(f"  ... and {len(report['removed_types']) - 50} more")
                break

            if isinstance(info, dict):
                # Namespace mismatch
                report_lines.append(
                    f"  - {type_name}: {info['docs_namespace']} -> {info['assembly_namespace']}"
                )
            else:
                # Type not found
                report_lines.append(f"  - {type_name} ({info})")
        report_lines.append("")

    report_lines.append("=" * 70)

    report_text = "\n".join(report_lines)
    output_path.write_text(report_text, encoding="utf-8")
    logger.info(f"Validation report written to {output_path}")

    # Also print to console
    print(report_text)


def main():
    parser = argparse.ArgumentParser(
        description="Validate API catalog against NuGet assembly"
    )
    parser.add_argument(
        "--package", required=True, help="NuGet package name (e.g., Aspose.Words)"
    )
    parser.add_argument(
        "--version",
        required=True,
        help='NuGet package version (e.g., 26.1.0 or "*" for latest)',
    )
    parser.add_argument(
        "--namespace-prefix",
        required=True,
        help="Namespace prefix to filter (e.g., Aspose.Words)",
    )
    parser.add_argument(
        "--catalog", required=True, help="Path to raw catalog JSON (from bootstrap)"
    )
    parser.add_argument(
        "--output", required=True, help="Path to write validated catalog JSON"
    )
    args = parser.parse_args()

    catalog_path = Path(args.catalog)
    output_path = Path(args.output)

    # Step 1: Extract assembly types via reflection
    assembly_data = invoke_catalog_types(
        args.package, args.version, args.namespace_prefix
    )
    logger.info(
        f"Assembly contains {assembly_data['TotalTypes']} types in {assembly_data['TotalNamespaces']} namespaces"
    )

    # Step 2: Load raw catalog
    raw_catalog = load_raw_catalog(catalog_path)
    logger.info(
        f"Raw catalog contains {len(raw_catalog.get('types', {}))} types in {len(raw_catalog.get('namespaces', []))} namespaces"
    )

    # Step 3: Validate and filter
    validated_catalog, validation_report = validate_catalog_against_assembly(
        raw_catalog, assembly_data
    )

    # Step 4: Write validated catalog
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(validated_catalog, indent=2), encoding="utf-8"
    )
    logger.info(f"Validated catalog written to {output_path}")

    # Step 5: Generate validation report
    report_path = output_path.with_name(
        output_path.stem + "_validation_report.txt"
    )
    generate_validation_report(validation_report, report_path)

    # Summary
    print(f"\n{'=' * 70}")
    print(f"Validation Complete!")
    print(f"Input: {catalog_path}")
    print(f"Output: {output_path}")
    print(f"Report: {report_path}")
    print(
        f"Result: {validation_report['summary']['types_kept']} types kept, "
        f"{validation_report['summary']['types_removed']} types removed"
    )
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
