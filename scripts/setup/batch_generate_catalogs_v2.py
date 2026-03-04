#!/usr/bin/env python3
"""
Batch generate API catalogs for multiple families using assembly reflection.
Handles package name != DLL name mappings and missing packages.
"""
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# (family, package_name, dll_name, namespace)
CATALOG_SPECS = [
    ("imaging", "Aspose.Imaging", "Aspose.Imaging", "Aspose.Imaging"),
    ("slides", "Aspose.Slides.NET", "Aspose.Slides", "Aspose.Slides"),
    ("email", "Aspose.Email", "Aspose.Email", "Aspose.Email"),
    ("tex", "Aspose.TeX", "Aspose.TeX", "Aspose.TeX"),
    ("cad", "Aspose.CAD", "Aspose.CAD", "Aspose.CAD"),
    ("html", "Aspose.HTML", "Aspose.HTML", "Aspose.Html"),
    ("page", "Aspose.Page", "Aspose.Page", "Aspose.Page"),
    ("tasks", "Aspose.Tasks", "Aspose.Tasks", "Aspose.Tasks"),
]


def find_package_dll(package_name: str, dll_name: str) -> Optional[str]:
    """
    Find the DLL for a package in NuGet cache.
    Returns the full path to the DLL if found, None otherwise.
    """
    nuget_root = Path.home() / ".nuget" / "packages" / package_name.lower()

    if not nuget_root.exists():
        return None

    # Find latest version
    versions = sorted([v for v in nuget_root.iterdir() if v.is_dir()], reverse=True)
    if not versions:
        return None

    version_dir = versions[0]

    # Try multiple framework targets in order of preference
    framework_targets = ["net8.0", "net7.0", "net6.0", "net462", "netstandard2.1", "netstandard2.0"]

    lib_dir = version_dir / "lib"
    if not lib_dir.exists():
        return None

    for framework in framework_targets:
        dll_path = lib_dir / framework / f"{dll_name}.dll"
        if dll_path.exists():
            return str(dll_path)

    return None


def generate_catalog_from_dll(family: str, dll_path: str, namespace: str) -> Tuple[bool, str]:
    """Generate catalog by directly loading a DLL."""

    output_path = Path(__file__).parent.parent.parent / "config" / "families" / f"{family}_api_catalog.json"

    print(f"[*] Generating catalog for {family}...")
    print(f"    DLL: {dll_path}")
    print(f"    Namespace: {namespace}")

    # Create a simple C# program to extract the catalog
    script = f"""
using System;
using System.Linq;
using System.Reflection;
using System.Text.Json;
using System.Collections.Generic;

var assembly = Assembly.LoadFrom(@"{dll_path}");
var types = assembly.GetExportedTypes()
    .Where(t => t.Namespace != null && t.Namespace.StartsWith("{namespace}"))
    .ToList();

var namespaces = types.Select(t => t.Namespace).Distinct().OrderBy(n => n).ToList();

var catalog = new {{
    Namespaces = namespaces,
    Types = types.Select(t => new {{
        Name = t.Name,
        FullName = t.FullName,
        Namespace = t.Namespace
    }}).ToList(),
    TotalTypes = types.Count,
    TotalNamespaces = namespaces.Count
}};

Console.WriteLine(JsonSerializer.Serialize(catalog, new JsonSerializerOptions {{ WriteIndented = true }}));
"""

    try:
        result = subprocess.run(
            ["dotnet", "script", "eval", script],
            capture_output=True,
            text=True,
            timeout=120
        )

        if result.returncode == 0 and result.stdout.strip():
            # Save output
            import json
            catalog = json.loads(result.stdout)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(catalog, f, indent=2, ensure_ascii=False)

            print(f"    [OK] Success: {output_path}")
            print(f"    [STAT] {catalog.get('TotalTypes', 0)} types, {catalog.get('TotalNamespaces', 0)} namespaces")
            return True, ""
        else:
            error_msg = result.stderr or result.stdout or "Unknown error"
            print(f"    [FAIL] {error_msg[:200]}")
            return False, error_msg

    except Exception as e:
        error_msg = str(e)
        print(f"    [FAIL] Error: {error_msg}")
        return False, error_msg


def generate_catalog_via_extractor(family: str, package: str, namespace: str) -> Tuple[bool, str]:
    """Generate catalog using the existing extractor script."""

    script_path = Path(__file__).parent / "extract_assembly_catalog.py"
    output_path = Path(__file__).parent.parent.parent / "config" / "families" / f"{family}_api_catalog.json"

    print(f"[*] Generating catalog for {family}...")
    print(f"    Package: {package}")
    print(f"    Namespace: {namespace}")

    try:
        result = subprocess.run(
            [
                sys.executable,
                str(script_path),
                package,
                "*",
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
            return True, ""
        else:
            error_msg = result.stderr or result.stdout
            print(f"    [FAIL] {error_msg[:200]}")
            return False, error_msg

    except subprocess.TimeoutExpired:
        return False, "Timeout after 300 seconds"
    except Exception as e:
        return False, str(e)


def main():
    """Generate all catalogs."""

    print("=" * 80)
    print("BATCH API CATALOG GENERATION V2")
    print("=" * 80)
    print(f"Families to process: {len(CATALOG_SPECS)}")
    print()

    successes = []
    failures = []

    for family, package, dll_name, namespace in CATALOG_SPECS:
        # First try the standard extractor
        success, error = generate_catalog_via_extractor(family, package, namespace)

        if not success:
            # If it failed, try finding the DLL directly
            print(f"    [INFO] Standard extractor failed, trying direct DLL approach...")
            dll_path = find_package_dll(package, dll_name)
            if dll_path:
                print(f"    [INFO] Found DLL: {dll_path}")
                # Note: This would require dotnet-script installed
                # For now, we'll just report the DLL location
                print(f"    [WARN] Please install package manually or use DLL at: {dll_path}")
                failures.append((family, f"DLL found but needs manual catalog: {dll_path}"))
            else:
                print(f"    [FAIL] Package not found in NuGet cache")
                failures.append((family, "Package not in NuGet cache"))
        else:
            successes.append(family)

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
        print("Failed families (need manual catalog or package install):")
        for family, error in failures:
            print(f"  [FAIL] {family}")
            print(f"         {error[:150]}")
        print()

    if failures:
        print("TO FIX FAILURES:")
        print("1. Install missing packages:")
        for family, package, _, _ in CATALOG_SPECS:
            if family in [f for f, _ in failures]:
                print(f"   dotnet add package {package}")
        print("2. Re-run this script")
        print()

    print("=" * 80)

    return 0 if len(successes) >= 2 else 1  # Success if at least 2 catalogs generated


if __name__ == "__main__":
    sys.exit(main())
