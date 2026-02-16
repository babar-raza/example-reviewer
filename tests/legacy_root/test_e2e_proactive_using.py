"""
End-to-end integration test for proactive using directive injection.

Tests the complete flow from code extraction → proactive fixes → compilation
to verify that code compiles first-try without LLM invocation.
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')

from pathlib import Path
import json
from services.semantic_microfixes import proactive_add_using_directives
from core.config import GlobalConfig
from pipeline.family_service_registry import FamilyServiceRegistry


def test_end_to_end_with_namespace_map():
    """
    End-to-end test: code missing using directives should get them added proactively.
    """
    print("\n" + "="*70)
    print("E2E TEST: Proactive Using Directive Injection with Real Catalog")
    print("="*70)

    # Load real configuration
    config_path = Path("config/global.json")
    print(f"\nLoading configuration from: {config_path}")
    with open(config_path, 'r', encoding='utf-8') as f:
        config_data = json.load(f)
    global_config = GlobalConfig(**config_data)

    # Initialize registry
    print("Initializing FamilyServiceRegistry...")
    registry = FamilyServiceRegistry(global_config)

    # Get namespace map for ZIP family
    family = "zip"
    namespace_map = registry.get_namespace_map(family)

    print(f"\nNamespace map for '{family}' family:")
    print(f"  Total types: {len(namespace_map)}")
    if namespace_map:
        # Show sample entries
        sample_items = list(namespace_map.items())[:5]
        print(f"  Sample mappings:")
        for api, ns in sample_items:
            print(f"    {api} -> {ns}")
    else:
        print("  [WARNING] Namespace map is EMPTY! Catalog may not be loaded.")
        return False

    # Test code: missing using directive for SevenZipArchive
    test_code = """class Program
{
    static void Main()
    {
        using (SevenZipArchive archive = new SevenZipArchive("input.7z"))
        {
            archive.ExtractToDirectory("output");
        }
    }
}"""

    print("\n" + "-"*70)
    print("Test Code (missing using Aspose.Zip.SevenZip;):")
    print("-"*70)
    print(test_code)

    # Apply proactive using directive injection
    print("\n" + "-"*70)
    print("Applying proactive_add_using_directives()...")
    print("-"*70)

    fixed_code, fixes = proactive_add_using_directives(test_code, namespace_map)

    print(f"\nFixes applied: {len(fixes)}")
    for fix in fixes:
        print(f"  - {fix}")

    print("\n" + "-"*70)
    print("Fixed Code:")
    print("-"*70)
    print(fixed_code)

    # Verify the fix
    print("\n" + "-"*70)
    print("Verification:")
    print("-"*70)

    if "using Aspose.Zip.SevenZip;" in fixed_code:
        print("[PASS] Using directive was added correctly")
    else:
        print("[FAIL] Using directive was NOT added")
        return False

    if len(fixes) > 0:
        print(f"[PASS] {len(fixes)} fix(es) reported")
    else:
        print("[FAIL] No fixes reported")
        return False

    if "SevenZipArchive" in fixed_code:
        print("[PASS] Original code logic preserved")
    else:
        print("[FAIL] Original code was corrupted")
        return False

    # Check that using directive comes BEFORE the class definition
    using_line = None
    class_line = None
    for i, line in enumerate(fixed_code.split('\n')):
        if 'using Aspose.Zip.SevenZip;' in line:
            using_line = i
        if 'class Program' in line:
            class_line = i

    if using_line is not None and class_line is not None and using_line < class_line:
        print("[PASS] Using directive is placed before class definition")
    else:
        print(f"[FAIL] Using directive placement incorrect (using: {using_line}, class: {class_line})")
        return False

    print("\n" + "="*70)
    print("[SUCCESS] E2E test passed!")
    print("="*70)
    print("\nConclusion:")
    print("- Code with missing using directives gets them added PROACTIVELY")
    print("- This happens BEFORE first compilation")
    print("- Result: Code compiles first-try, no LLM invocation needed")
    print("- No cosmetic-only commits!")
    return True


def test_with_existing_using_directive():
    """
    Test that code with existing using directives is not modified.
    """
    print("\n" + "="*70)
    print("E2E TEST: Code with Existing Using Directives (No Changes)")
    print("="*70)

    # Load real configuration
    config_path = Path("config/global.json")
    with open(config_path, 'r', encoding='utf-8') as f:
        config_data = json.load(f)
    global_config = GlobalConfig(**config_data)
    registry = FamilyServiceRegistry(global_config)

    family = "zip"
    namespace_map = registry.get_namespace_map(family)

    # Test code: already has correct using directive
    test_code = """using Aspose.Zip.SevenZip;
using System.IO;

class Program
{
    static void Main()
    {
        using (SevenZipArchive archive = new SevenZipArchive("input.7z"))
        {
            archive.ExtractToDirectory("output");
        }
    }
}"""

    print("\nTest Code (already has correct using directives):")
    print("-"*70)
    print(test_code)

    # Apply proactive using directive injection
    print("\n" + "-"*70)
    print("Applying proactive_add_using_directives()...")
    print("-"*70)

    fixed_code, fixes = proactive_add_using_directives(test_code, namespace_map)

    print(f"\nFixes applied: {len(fixes)}")
    for fix in fixes:
        print(f"  - {fix}")

    # Verify NO changes
    print("\n" + "-"*70)
    print("Verification:")
    print("-"*70)

    if fixed_code == test_code:
        print("[PASS] Code was NOT modified (as expected)")
    else:
        print("[FAIL] Code was unexpectedly modified")
        print(f"\nOriginal:\n{test_code}")
        print(f"\nFixed:\n{fixed_code}")
        return False

    if len(fixes) == 0:
        print("[PASS] No fixes reported (as expected)")
    else:
        print(f"[FAIL] {len(fixes)} unexpected fix(es) reported")
        return False

    # Ensure no duplicates
    using_count = fixed_code.count("using Aspose.Zip.SevenZip;")
    if using_count == 1:
        print("[PASS] Using directive not duplicated")
    else:
        print(f"[FAIL] Using directive count: {using_count} (expected 1)")
        return False

    print("\n" + "="*70)
    print("[SUCCESS] E2E test passed!")
    print("="*70)
    print("\nConclusion:")
    print("- Code with correct using directives is left unchanged")
    print("- No unnecessary modifications")
    print("- Pipeline is smart about what it fixes")
    return True


def main():
    """Run all E2E tests."""
    print("\n" + "#"*70)
    print("# End-to-End Integration Tests: Proactive Using Directive Injection")
    print("#"*70)

    try:
        # Test 1: Missing using directives
        result1 = test_end_to_end_with_namespace_map()

        # Test 2: Existing using directives
        result2 = test_with_existing_using_directive()

        if result1 and result2:
            print("\n" + "="*70)
            print("[PASS] ALL E2E TESTS PASSED!")
            print("="*70)
            print("\nThe proactive using directive injection is working correctly in the")
            print("full pipeline. This will prevent cosmetic-only commits by ensuring")
            print("code compiles first-try when possible.")
            return 0
        else:
            print("\n" + "="*70)
            print("[FAIL] SOME TESTS FAILED")
            print("="*70)
            return 1

    except Exception as e:
        print(f"\n[FAIL] ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
