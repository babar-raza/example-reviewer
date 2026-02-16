#!/usr/bin/env python3
"""
Test script to verify using directives are properly loaded from catalog.

This script tests the fix for the critical bug where catalog using directives
were being overridden by the base allowlist.
"""

import sys
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Import the fixed function and registry
from pathlib import Path
from src.services.semantic_microfixes import apply_semantic_microfixes, USING_DIRECTIVE_ALLOWLIST
from src.pipeline.family_service_registry import FamilyServiceRegistry
from src.core.config import ConfigurationManager

def test_using_directives_loading():
    """Test that catalog using directives are properly loaded and merged."""

    print("="*80)
    print("TEST: Using Directives Loading from Catalog")
    print("="*80)
    print()

    # Step 1: Load the registry
    print("Step 1: Loading family registry for ZIP...")
    family = "zip"
    config_manager = ConfigurationManager()
    artifacts_dir = Path("artifacts/backfill")
    registry = FamilyServiceRegistry(config_manager, artifacts_dir)

    # Step 2: Get catalog directives
    print("\nStep 2: Getting catalog using directives...")
    catalog_directives = registry.get_using_directives(family)
    print(f"  Catalog has {len(catalog_directives)} using directives")
    print(f"  Base allowlist has {len(USING_DIRECTIVE_ALLOWLIST)} using directives")

    # Step 3: Show sample catalog entries
    print("\nStep 3: Sample catalog entries:")
    sample_types = ["RarArchive", "BrotliArchive", "CpioArchive", "XarArchive", "WimArchive"]
    for type_name in sample_types:
        if type_name in catalog_directives:
            print(f"  {type_name} -> {catalog_directives[type_name]}")
        else:
            print(f"  {type_name} -> NOT FOUND IN CATALOG")

    # Step 4: Test the merge in apply_semantic_microfixes
    print("\nStep 4: Testing merge in apply_semantic_microfixes...")
    test_code = """using System;
using System.IO;

class Program {
    static void Main() {
        RarArchive archive = new RarArchive("test.rar");
    }
}"""

    # This should trigger the catalog loading logic
    fixed_code, applied_fixes = apply_semantic_microfixes(
        test_code,
        ["error CS0246: The type or namespace name 'RarArchive' could not be found"],
        family=family,
        registry=registry
    )

    # Step 5: Verify the fix was applied
    print("\nStep 5: Verification:")
    if "using Aspose.Zip.Rar;" in fixed_code:
        print("  ✓ PASS: RarArchive using directive was added from catalog")
    else:
        print("  ✗ FAIL: RarArchive using directive was NOT added")
        print(f"\nFixed code:\n{fixed_code}")
        return False

    if applied_fixes:
        print(f"  Applied fixes: {applied_fixes}")

    # Step 6: Test a type that's NOT in base allowlist
    print("\nStep 6: Testing catalog-only type (CpioArchive)...")
    test_code2 = """using System;
using System.IO;

class Program {
    static void Main() {
        CpioArchive archive = new CpioArchive();
    }
}"""

    fixed_code2, applied_fixes2 = apply_semantic_microfixes(
        test_code2,
        ["error CS0246: The type or namespace name 'CpioArchive' could not be found"],
        family=family,
        registry=registry
    )

    if "using Aspose.Zip.Cpio;" in fixed_code2:
        print("  ✓ PASS: CpioArchive using directive was added from catalog")
    else:
        print("  ✗ FAIL: CpioArchive using directive was NOT added")
        print(f"\nFixed code:\n{fixed_code2}")
        return False

    print("\n" + "="*80)
    print("ALL TESTS PASSED!")
    print("="*80)
    return True


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding='utf-8')

    try:
        success = test_using_directives_loading()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Test failed with exception: {e}", exc_info=True)
        sys.exit(1)
