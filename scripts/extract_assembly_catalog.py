#!/usr/bin/env python3
"""Extract clean JSON catalog from catalog-types command output.

Usage:
    python extract_assembly_catalog.py <Package> <Version> <NamespacePrefix> [--full]

The --full flag enables extraction of enums, constructors, and key methods.
Without --full, only types and namespaces are extracted (backward compatible).
"""
import json
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

PROJECT_ROOT = Path(__file__).parent.parent


def main():
    # Parse positional args
    positional = [a for a in sys.argv[1:] if not a.startswith("--")]
    package = positional[0] if len(positional) > 0 else "Aspose.Words"
    version = positional[1] if len(positional) > 1 else "26.1.0"
    namespace_prefix = positional[2] if len(positional) > 2 else package

    # Parse flags
    flags = [a for a in sys.argv[1:] if a.startswith("--")]
    include_full = "--full" in flags
    include_enums = "--include-enums" in flags or include_full
    include_constructors = "--include-constructors" in flags or include_full
    include_methods = "--include-methods" in flags or include_full
    include_properties = "--include-properties" in flags or include_full

    cmd = [
        "dotnet", "run", "--project", str(PROJECT_ROOT / "test-examples" / "AsposeZipValidator.csproj"),
        "--", "catalog-types",
        "--package", package,
        "--version", version,
        "--namespace-prefix", namespace_prefix
    ]

    # Pass enrichment flags through to dotnet command
    if include_full:
        cmd.append("--full")
    else:
        if include_enums:
            cmd.append("--include-enums")
        if include_constructors:
            cmd.append("--include-constructors")
        if include_methods:
            cmd.append("--include-methods")
        if include_properties:
            cmd.append("--include-properties")

    print(f"Running: {' '.join(cmd)}", file=sys.stderr)
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=PROJECT_ROOT)

    if result.stderr:
        # Print stderr (build warnings) for diagnostics, but don't fail
        for line in result.stderr.strip().split("\n"):
            if line.strip():
                print(f"  [dotnet] {line}", file=sys.stderr)

    # Find JSON start (skip any build output lines before the JSON)
    lines = result.stdout.split("\n")
    json_start = -1
    for i, line in enumerate(lines):
        if line.strip().startswith("{"):
            json_start = i
            break

    if json_start == -1:
        print("ERROR: No JSON found in output", file=sys.stderr)
        print(result.stdout, file=sys.stderr)
        sys.exit(1)

    json_text = "\n".join(lines[json_start:])
    catalog = json.loads(json_text)

    # Add metadata for bootstrap compatibility
    ambiguous_raw = catalog.get("AmbiguousTypes", {})

    metadata = {
        "family": package.split(".")[-1].lower(),
        "source": f"{package} v{version} assembly (via reflection)",
        "generated_by": "scripts/extract_assembly_catalog.py",
        "assembly_version": catalog.get("AssemblyVersion"),
        "total_types": catalog.get("TotalTypes"),
        "total_namespaces": catalog.get("TotalNamespaces"),
        "total_ambiguous_types": len(ambiguous_raw),
        "assembly_validation": {
            "enabled": True,
            "assembly_version": catalog.get("AssemblyVersion"),
            "direct_extraction": True
        }
    }

    # Track which enrichment sections are present
    enrichment_sections = []
    if "Enums" in catalog:
        enrichment_sections.append("enums")
    if "Constructors" in catalog:
        enrichment_sections.append("constructors")
    if "KeyMethods" in catalog:
        enrichment_sections.append("key_methods")
    if "Properties" in catalog:
        enrichment_sections.append("properties")
    if enrichment_sections:
        metadata["enrichment"] = enrichment_sections

    # Reformat to match bootstrap catalog structure
    final_catalog = {
        "_metadata": metadata,
        "namespaces": catalog["Namespaces"],
        "types": catalog["Types"],
        "using_directive_map": {t: f"using {ns};" for t, ns in catalog["Types"].items()},
        "namespace_ambiguous_types": ambiguous_raw,
    }

    # Include enrichment sections if present (backward compatible — only added when flags used)
    if "Enums" in catalog:
        final_catalog["enums"] = catalog["Enums"]
    if "Constructors" in catalog:
        final_catalog["constructors"] = catalog["Constructors"]
    if "KeyMethods" in catalog:
        final_catalog["key_methods"] = catalog["KeyMethods"]
    if "Properties" in catalog:
        final_catalog["properties"] = catalog["Properties"]

    output = json.dumps(final_catalog, indent=2)
    print(output)

    # Summary to stderr
    print(f"\nCatalog generated: {catalog.get('TotalTypes')} types, "
          f"{catalog.get('TotalNamespaces')} namespaces", file=sys.stderr)
    if enrichment_sections:
        if "Enums" in catalog:
            print(f"  Enums: {len(catalog['Enums'])} enum types", file=sys.stderr)
        if "Constructors" in catalog:
            print(f"  Constructors: {len(catalog['Constructors'])} types with public ctors", file=sys.stderr)
        if "KeyMethods" in catalog:
            total_methods = sum(len(v) for v in catalog["KeyMethods"].values())
            print(f"  Key methods: {total_methods} methods across {len(catalog['KeyMethods'])} types", file=sys.stderr)
        if "Properties" in catalog:
            total_props = sum(len(v) for v in catalog["Properties"].values())
            print(f"  Properties: {total_props} properties across {len(catalog['Properties'])} types", file=sys.stderr)


if __name__ == "__main__":
    main()
