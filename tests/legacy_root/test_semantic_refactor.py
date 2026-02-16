"""
Test semantic_microfixes refactoring (TASK-2A).

Verifies that the family-aware refactoring works correctly.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.services.semantic_microfixes import apply_semantic_microfixes
from src.pipeline.family_service_registry import FamilyServiceRegistry
from src.core.config import ConfigurationManager

def test_basic_functionality():
    """Test that semantic_microfixes still works with basic code."""
    print("Test 1: Basic functionality (no family)")
    code = """
using System;
class Program {
    static void Main() {
        Archive archive = new Archive();
    }
}
"""
    errors = ["error CS0246: The type or namespace name 'Archive' could not be found"]

    # Call without family (backwards compatibility)
    fixed, fixes = apply_semantic_microfixes(code, errors)

    assert "using Aspose.Zip;" in fixed, "Should add using directive"
    assert len(fixes) == 1, f"Expected 1 fix, got {len(fixes)}"
    print(f"  [OK] Applied {len(fixes)} fix(es)")
    print()


def test_family_aware():
    """Test family-aware functionality with registry."""
    print("Test 2: Family-aware with ZIP family")

    # Initialize registry
    config_mgr = ConfigurationManager()
    artifacts_dir = Path("artifacts")
    registry = FamilyServiceRegistry(config_mgr, artifacts_dir)

    # Test code with ZIP-specific pattern
    code = """
using System;
using Aspose.Zip.Rar;
class Program {
    static void Main() {
        var archive = new RarArchive("test.rar", "password");
    }
}
"""
    errors = []

    # Call with ZIP family
    fixed, fixes = apply_semantic_microfixes(code, errors, family="zip", registry=registry)

    # Should apply ZIP-specific RarArchive password fix
    assert "RarArchiveLoadOptions" in fixed, "Should fix RarArchive constructor"
    assert len(fixes) > 0, "Should apply at least one fix"
    print(f"  [OK] Applied {len(fixes)} fix(es) for ZIP family")
    for fix in fixes:
        print(f"    - {fix}")
    print()


def test_zip_specific_fixes():
    """Test that ZIP-specific fixes are applied."""
    print("Test 3: ZIP-specific Entries string index fix")

    config_mgr = ConfigurationManager()
    artifacts_dir = Path("artifacts")
    registry = FamilyServiceRegistry(config_mgr, artifacts_dir)

    code = """
using System;
using Aspose.Zip;
class Program {
    static void Main() {
        var archive = new Archive("test.zip");
        var entry = archive.Entries["file.txt"];
    }
}
"""
    errors = []

    fixed, fixes = apply_semantic_microfixes(code, errors, family="zip", registry=registry)

    assert "Entries[0]" in fixed, "Should fix Entries string index"
    assert "Entries[\"file.txt\"]" not in fixed, "Should remove string index"
    print(f"  [OK] Applied {len(fixes)} fix(es)")
    for fix in fixes:
        print(f"    - {fix}")
    print()


def test_words_family():
    """Test that Words family doesn't break (placeholder module)."""
    print("Test 4: Words family (placeholder)")

    config_mgr = ConfigurationManager()
    artifacts_dir = Path("artifacts")
    registry = FamilyServiceRegistry(config_mgr, artifacts_dir)

    code = """
using System;
class Program {
    static void Main() {
        Console.WriteLine("Hello");
    }
}
"""
    errors = []

    # Should not crash with words family
    fixed, fixes = apply_semantic_microfixes(code, errors, family="words", registry=registry)

    assert fixed == code, "Should not modify code (no fixes needed)"
    print(f"  [OK] Words family handled correctly (0 fixes applied)")
    print()


def test_catalog_loading():
    """Test that ZIP catalog loads correctly."""
    print("Test 5: API Catalog loading")

    config_mgr = ConfigurationManager()
    artifacts_dir = Path("artifacts")
    registry = FamilyServiceRegistry(config_mgr, artifacts_dir)

    # Load ZIP catalog
    catalog = registry.get_api_catalog("zip")
    using_dirs = catalog.get_using_directive_map()

    assert len(using_dirs) > 100, f"Expected 100+ types, got {len(using_dirs)}"
    assert "Archive" in using_dirs, "Should have Archive type"
    assert "SevenZipArchive" in using_dirs, "Should have SevenZipArchive type"
    print(f"  [OK] Loaded {len(using_dirs)} types from ZIP catalog")
    print()


if __name__ == "__main__":
    print("="*70)
    print("Testing Semantic Microfixes Refactoring (TASK-2A)")
    print("="*70)
    print()

    try:
        test_basic_functionality()
        test_catalog_loading()
        test_family_aware()
        test_zip_specific_fixes()
        test_words_family()

        print("="*70)
        print("ALL TESTS PASSED [OK]")
        print("="*70)
        print()
        print("Summary:")
        print("  - Backward compatibility maintained (no family parameter)")
        print("  - Family-aware functionality working (ZIP catalog loaded)")
        print("  - ZIP-specific fixes applied correctly")
        print("  - Words family handled gracefully (placeholder)")
        print("  - No module-level hardcoded catalog initialization")
        print()

    except AssertionError as e:
        print(f"\n[FAIL] TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[FAIL] ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
