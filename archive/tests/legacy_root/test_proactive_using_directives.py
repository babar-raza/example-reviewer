"""
Test script for proactive using directive injection.

Tests the catalog-driven proactive using directive functionality that prevents
cosmetic-only commits by ensuring code compiles first-try.
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')  # Fix Windows encoding issues
sys.path.insert(0, 'src')

from services.semantic_microfixes import proactive_add_using_directives


def test_add_missing_using_directive():
    """Test adding missing using directive for detected API usage."""
    print("\n" + "="*70)
    print("TEST 1: Add missing using directive for detected API usage")
    print("="*70)

    code = """class Program
{
    static void Main()
    {
        using (SevenZipArchive archive = new SevenZipArchive("input.7z"))
        {
            archive.ExtractToDirectory("output");
        }
    }
}"""

    namespace_map = {
        "SevenZipArchive": "Aspose.Zip.SevenZip",
        "RarArchive": "Aspose.Zip.Rar",
        "Archive": "Aspose.Zip"
    }

    print("\nOriginal code:")
    print(code)
    print("\nNamespace map:")
    for api, ns in namespace_map.items():
        print(f"  {api} -> {ns}")

    fixed_code, fixes = proactive_add_using_directives(code, namespace_map)

    print("\nFixed code:")
    print(fixed_code)
    print("\nFixes applied:")
    for fix in fixes:
        print(f"  - {fix}")

    # Verify using directive was added
    assert "using Aspose.Zip.SevenZip;" in fixed_code, "Using directive should be added"
    assert len(fixes) == 1, "Should have 1 fix applied"
    assert "Aspose.Zip.SevenZip" in fixes[0], "Fix should mention the namespace"

    print("\n[PASS] TEST PASSED: Missing using directive was added correctly")


def test_no_duplicate_using_directive():
    """Test that existing using directives are not duplicated."""
    print("\n" + "="*70)
    print("TEST 2: No duplicate using directives")
    print("="*70)

    code = """using Aspose.Zip.SevenZip;
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

    namespace_map = {
        "SevenZipArchive": "Aspose.Zip.SevenZip",
    }

    print("\nOriginal code:")
    print(code)

    fixed_code, fixes = proactive_add_using_directives(code, namespace_map)

    print("\nFixed code:")
    print(fixed_code)
    print("\nFixes applied:")
    for fix in fixes:
        print(f"  - {fix}")

    # Verify NO changes were made
    assert fixed_code == code, "Code should remain unchanged"
    assert len(fixes) == 0, "Should have 0 fixes applied"
    assert fixed_code.count("using Aspose.Zip.SevenZip;") == 1, "Should not duplicate using directive"

    print("\n[PASS] TEST PASSED: Existing using directive was not duplicated")


def test_multiple_missing_using_directives():
    """Test adding multiple missing using directives."""
    print("\n" + "="*70)
    print("TEST 3: Add multiple missing using directives")
    print("="*70)

    code = """class Program
{
    static void Main()
    {
        var rar = new RarArchive("input.rar");
        var zip = new Archive("input.zip");
        var sevenZ = new SevenZipArchive("input.7z");
    }
}"""

    namespace_map = {
        "SevenZipArchive": "Aspose.Zip.SevenZip",
        "RarArchive": "Aspose.Zip.Rar",
        "Archive": "Aspose.Zip"
    }

    print("\nOriginal code:")
    print(code)

    fixed_code, fixes = proactive_add_using_directives(code, namespace_map)

    print("\nFixed code:")
    print(fixed_code)
    print("\nFixes applied:")
    for fix in fixes:
        print(f"  - {fix}")

    # Verify all using directives were added
    assert "using Aspose.Zip;" in fixed_code, "Should add Aspose.Zip"
    assert "using Aspose.Zip.Rar;" in fixed_code, "Should add Aspose.Zip.Rar"
    assert "using Aspose.Zip.SevenZip;" in fixed_code, "Should add Aspose.Zip.SevenZip"
    assert len(fixes) == 3, "Should have 3 fixes applied"

    print("\n[PASS] TEST PASSED: Multiple missing using directives were added correctly")


def test_partial_existing_using_directives():
    """Test adding only missing using directives when some already exist."""
    print("\n" + "="*70)
    print("TEST 4: Add only missing using directives")
    print("="*70)

    code = """using System;
using Aspose.Zip;

class Program
{
    static void Main()
    {
        var rar = new RarArchive("input.rar");
        var zip = new Archive("input.zip");
    }
}"""

    namespace_map = {
        "RarArchive": "Aspose.Zip.Rar",
        "Archive": "Aspose.Zip"
    }

    print("\nOriginal code:")
    print(code)

    fixed_code, fixes = proactive_add_using_directives(code, namespace_map)

    print("\nFixed code:")
    print(fixed_code)
    print("\nFixes applied:")
    for fix in fixes:
        print(f"  - {fix}")

    # Verify only missing using directive was added
    assert "using Aspose.Zip.Rar;" in fixed_code, "Should add Aspose.Zip.Rar"
    assert fixed_code.count("using Aspose.Zip;") == 1, "Should not duplicate existing Aspose.Zip"
    assert len(fixes) == 1, "Should have 1 fix applied (only the missing one)"

    print("\n[PASS] TEST PASSED: Only missing using directive was added, existing ones preserved")


def test_no_api_usage():
    """Test with code that doesn't use any Aspose APIs."""
    print("\n" + "="*70)
    print("TEST 5: No changes when no API usage detected")
    print("="*70)

    code = """using System;

class Program
{
    static void Main()
    {
        Console.WriteLine("Hello World");
    }
}"""

    namespace_map = {
        "SevenZipArchive": "Aspose.Zip.SevenZip",
        "Archive": "Aspose.Zip"
    }

    print("\nOriginal code:")
    print(code)

    fixed_code, fixes = proactive_add_using_directives(code, namespace_map)

    print("\nFixed code:")
    print(fixed_code)
    print("\nFixes applied:")
    for fix in fixes:
        print(f"  - {fix}")

    # Verify NO changes were made
    assert fixed_code == code, "Code should remain unchanged"
    assert len(fixes) == 0, "Should have 0 fixes applied"

    print("\n[PASS] TEST PASSED: No changes when no API usage detected")


def test_empty_namespace_map():
    """Test with empty namespace map (no catalog loaded)."""
    print("\n" + "="*70)
    print("TEST 6: No changes when namespace map is empty")
    print("="*70)

    code = """class Program
{
    static void Main()
    {
        var archive = new SevenZipArchive("input.7z");
    }
}"""

    namespace_map = {}

    print("\nOriginal code:")
    print(code)
    print("\nNamespace map: (empty)")

    fixed_code, fixes = proactive_add_using_directives(code, namespace_map)

    print("\nFixed code:")
    print(fixed_code)
    print("\nFixes applied:")
    for fix in fixes:
        print(f"  - {fix}")

    # Verify NO changes were made
    assert fixed_code == code, "Code should remain unchanged when namespace map is empty"
    assert len(fixes) == 0, "Should have 0 fixes applied"

    print("\n[PASS] TEST PASSED: No changes when namespace map is empty")


def main():
    """Run all tests."""
    print("\n" + "#"*70)
    print("# Testing Proactive Using Directive Injection")
    print("#"*70)

    try:
        test_add_missing_using_directive()
        test_no_duplicate_using_directive()
        test_multiple_missing_using_directives()
        test_partial_existing_using_directives()
        test_no_api_usage()
        test_empty_namespace_map()

        print("\n" + "="*70)
        print("[PASS] ALL TESTS PASSED!")
        print("="*70)
        print("\nThe proactive using directive injection is working correctly.")
        print("This will prevent cosmetic-only commits by ensuring code compiles first-try.")
        return 0

    except AssertionError as e:
        print(f"\n[FAIL] TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n[FAIL] ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
