"""
Simple integration test for proactive using directive injection using the real ZIP catalog.
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'src')

import json
from pathlib import Path
from services.semantic_microfixes import proactive_add_using_directives


def test_with_real_zip_catalog():
    """
    Test proactive using directive injection with the real ZIP API catalog.
    """
    print("\n" + "="*70)
    print("INTEGRATION TEST: Proactive Using Directives with Real ZIP Catalog")
    print("="*70)

    # Load the real ZIP API catalog
    catalog_path = Path("config/families/zip_api_catalog.json")
    print(f"\nLoading ZIP API catalog from: {catalog_path}")

    if not catalog_path.exists():
        print(f"[FAIL] Catalog file not found: {catalog_path}")
        return False

    with open(catalog_path, 'r', encoding='utf-8') as f:
        catalog_data = json.load(f)

    # Get namespace_map from catalog (types is a dict: class_name -> namespace)
    namespace_map = catalog_data.get('types', {})

    print(f"Loaded {len(namespace_map)} type mappings from catalog")

    # Show some sample mappings
    print("\nSample type mappings:")
    sample_types = ['SevenZipArchive', 'RarArchive', 'Archive', 'GzipArchive', 'TarArchive']
    for type_name in sample_types:
        if type_name in namespace_map:
            print(f"  {type_name} -> {namespace_map[type_name]}")

    # Test code: missing using directives
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

    # Verify
    print("\n" + "-"*70)
    print("Verification:")
    print("-"*70)

    success = True

    if "using Aspose.Zip.SevenZip;" in fixed_code:
        print("[PASS] Using directive 'Aspose.Zip.SevenZip' was added")
    else:
        print("[FAIL] Using directive 'Aspose.Zip.SevenZip' was NOT added")
        success = False

    if len(fixes) == 1:
        print(f"[PASS] Exactly 1 fix reported")
    else:
        print(f"[FAIL] Expected 1 fix, got {len(fixes)}")
        success = False

    # Check placement
    lines = fixed_code.split('\n')
    using_line_idx = None
    class_line_idx = None

    for i, line in enumerate(lines):
        if 'using Aspose.Zip.SevenZip;' in line:
            using_line_idx = i
        if 'class Program' in line:
            class_line_idx = i

    if using_line_idx is not None and class_line_idx is not None:
        if using_line_idx < class_line_idx:
            print(f"[PASS] Using directive at line {using_line_idx}, class at line {class_line_idx}")
        else:
            print(f"[FAIL] Using directive placement incorrect")
            success = False
    else:
        print(f"[FAIL] Could not find using or class line")
        success = False

    return success


def test_multiple_apis():
    """
    Test with code using multiple Aspose APIs.
    """
    print("\n" + "="*70)
    print("INTEGRATION TEST: Multiple API Types")
    print("="*70)

    # Load catalog
    catalog_path = Path("config/families/zip_api_catalog.json")
    with open(catalog_path, 'r', encoding='utf-8') as f:
        catalog_data = json.load(f)

    # Get namespace_map from catalog
    namespace_map = catalog_data.get('types', {})

    # Test code using multiple APIs
    test_code = """class Program
{
    static void Main()
    {
        var rar = new RarArchive("input.rar");
        var zip = new Archive("input.zip");
        var sevenZ = new SevenZipArchive("input.7z");
    }
}"""

    print("\nTest Code (using 3 different Aspose.Zip types):")
    print("-"*70)
    print(test_code)

    fixed_code, fixes = proactive_add_using_directives(test_code, namespace_map)

    print("\n" + "-"*70)
    print("Fixed Code:")
    print("-"*70)
    print(fixed_code)

    print(f"\nFixes applied: {len(fixes)}")
    for fix in fixes:
        print(f"  - {fix}")

    # Verify all 3 using directives were added
    print("\n" + "-"*70)
    print("Verification:")
    print("-"*70)

    success = True

    expected_usings = [
        "using Aspose.Zip;",
        "using Aspose.Zip.Rar;",
        "using Aspose.Zip.SevenZip;"
    ]

    for using in expected_usings:
        if using in fixed_code:
            print(f"[PASS] {using}")
        else:
            print(f"[FAIL] Missing: {using}")
            success = False

    if len(fixes) == 3:
        print(f"[PASS] All 3 fixes reported")
    else:
        print(f"[FAIL] Expected 3 fixes, got {len(fixes)}")
        success = False

    return success


def main():
    """Run integration tests."""
    print("\n" + "#"*70)
    print("# Integration Tests: Real ZIP Catalog")
    print("#"*70)

    try:
        result1 = test_with_real_zip_catalog()
        result2 = test_multiple_apis()

        if result1 and result2:
            print("\n" + "="*70)
            print("[PASS] ALL INTEGRATION TESTS PASSED!")
            print("="*70)
            print("\nSummary:")
            print("- Proactive using directive injection works with real ZIP catalog")
            print("- Code missing using directives gets them added before compilation")
            print("- Multiple API types are detected and handled correctly")
            print("- This prevents cosmetic-only commits by ensuring first-try success")
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
