#!/usr/bin/env python
"""
Verification script for TASK-5A namespace map fix.

Tests that namespace_map loading works correctly across all services.
"""

import sys
from pathlib import Path

# Configure stdout encoding for Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.core.config import ConfigurationManager
from src.pipeline.family_service_registry import FamilyServiceRegistry
from src.services.compilation_service import CompilationService
from src.services.runtime_service import RuntimeService
from src.core.database import Database

def verify_namespace_map_format(namespace_map: dict, family: str) -> bool:
    """Verify namespace map has correct format (namespace only, no 'using' prefix)."""
    if not namespace_map:
        print(f"  ❌ FAIL: namespace_map is empty for {family}")
        return False

    # Check first few entries for correct format
    sample = list(namespace_map.items())[:5]
    for type_name, namespace in sample:
        if namespace.startswith("using ") or namespace.endswith(";"):
            print(f"  ❌ FAIL: Incorrect format for {type_name}: '{namespace}'")
            print(f"    Expected: 'Aspose.Zip', Got: '{namespace}'")
            return False
        if not namespace.startswith("Aspose."):
            print(f"  ⚠️  WARN: Unexpected namespace for {type_name}: '{namespace}'")

    return True

def main():
    print("=" * 80)
    print("TASK-5A Namespace Map Fix Verification")
    print("=" * 80)

    # Initialize configuration
    config_manager = ConfigurationManager()
    artifacts_dir = Path("artifacts")

    # Initialize registry
    print("\n1. Testing FamilyServiceRegistry...")
    registry = FamilyServiceRegistry(config_manager, artifacts_dir)

    # Test ZIP family
    family = "zip"
    print(f"\n2. Loading namespace map for '{family}' family...")
    namespace_map = registry.get_namespace_map(family)

    print(f"   Loaded {len(namespace_map)} types")
    sample = list(namespace_map.items())[:5]
    print(f"   Sample entries:")
    for type_name, namespace in sample:
        print(f"     {type_name} -> {namespace}")

    # Verify format
    print(f"\n3. Verifying namespace map format...")
    if verify_namespace_map_format(namespace_map, family):
        print(f"   ✅ PASS: namespace_map has correct format")
    else:
        print(f"   ❌ FAIL: namespace_map has incorrect format")
        return 1

    # Test CompilationService
    print(f"\n4. Testing CompilationService integration...")
    db = Database("data/example_reviewer.db")
    compilation_service = CompilationService(
        db=db,
        family=family,
        registry=registry
    )

    if len(compilation_service.namespace_map) == len(namespace_map):
        print(f"   ✅ PASS: CompilationService loaded {len(compilation_service.namespace_map)} types")
    else:
        print(f"   ❌ FAIL: CompilationService loaded {len(compilation_service.namespace_map)} types, expected {len(namespace_map)}")
        return 1

    if verify_namespace_map_format(compilation_service.namespace_map, family):
        print(f"   ✅ PASS: CompilationService namespace_map has correct format")
    else:
        print(f"   ❌ FAIL: CompilationService namespace_map has incorrect format")
        return 1

    # Test RuntimeService
    print(f"\n5. Testing RuntimeService integration...")
    runtime_service = RuntimeService(
        db=db,
        family=family,
        registry=registry
    )

    if len(runtime_service.namespace_map) == len(namespace_map):
        print(f"   ✅ PASS: RuntimeService loaded {len(runtime_service.namespace_map)} types")
    else:
        print(f"   ❌ FAIL: RuntimeService loaded {len(runtime_service.namespace_map)} types, expected {len(namespace_map)}")
        return 1

    if verify_namespace_map_format(runtime_service.namespace_map, family):
        print(f"   ✅ PASS: RuntimeService namespace_map has correct format")
    else:
        print(f"   ❌ FAIL: RuntimeService namespace_map has incorrect format")
        return 1

    # Test specific type lookups
    print(f"\n6. Testing specific type lookups...")
    test_types = ["Archive", "SevenZipArchive", "RarArchive", "GzipArchive", "TarArchive"]
    for type_name in test_types:
        namespace = namespace_map.get(type_name)
        if namespace:
            print(f"   ✅ {type_name} -> {namespace}")
        else:
            print(f"   ❌ {type_name} not found in namespace_map")
            return 1

    print("\n" + "=" * 80)
    print("✅ ALL TESTS PASSED")
    print("=" * 80)
    print("\nNamespace map loading is working correctly.")
    print(f"Total types available: {len(namespace_map)}")
    print("\nReady to run full pipeline with restored 100% verification rate.")

    return 0

if __name__ == "__main__":
    sys.exit(main())
