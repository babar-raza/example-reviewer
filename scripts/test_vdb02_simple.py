#!/usr/bin/env python3
"""
Simple focused tests for VDB-02: Architecture-Aware Search.
"""

import sys
import tempfile
from pathlib import Path

# Fix Windows encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.vector_db_service import VectorDBService, VECTOR_DB_AVAILABLE


def test_app_context_filtering():
    """Test app_context filtering."""
    print("\n=== Test: app_context Filtering ===")

    if not VECTOR_DB_AVAILABLE:
        print("⚠ ChromaDB not available")
        return None

    with tempfile.TemporaryDirectory() as tmp_dir:
        vdb = VectorDBService(persist_directory=str(Path(tmp_dir) / "chroma"), enabled=True)

        # Add examples
        examples = [
            ("console_1", "Console.WriteLine();", "console"),
            ("console_2", "Console.ReadLine();", "console"),
            ("library_1", "public static class", "library"),
            ("aspnet_1", "app.Run();", "aspnet_minimal"),
        ]

        for ex_id, code, ctx in examples:
            vdb.add_example(
                ex_id, code,
                metadata={"family": "test", "app_context": ctx},
                drift_score=0.0
            )

        # Test 1: No filter - should return all
        results = vdb.search_similar("code", family="test", k=10)
        print(f"No app_context filter: {len(results)} results (expected 4)")
        if len(results) != 4:
            print(f"✗ Expected 4, got {len(results)}")
            return False

        # Test 2: Filter by console
        results = vdb.search_similar("code", family="test", app_context="console", k=10)
        print(f"app_context='console': {len(results)} results (expected 2)")
        contexts = [r[3]["app_context"] for r in results]
        if len(results) != 2 or not all(c == "console" for c in contexts):
            print(f"✗ Expected 2 console results, got: {contexts}")
            return False

        # Test 3: Filter by library
        results = vdb.search_similar("code", family="test", app_context="library", k=10)
        print(f"app_context='library': {len(results)} results (expected 1)")
        if len(results) != 1 or results[0][3]["app_context"] != "library":
            print(f"✗ Expected 1 library result")
            return False

        print("✓ app_context filtering works correctly")
        return True


def test_cs_file_priority():
    """Test cs_file prioritization."""
    print("\n=== Test: cs_file Prioritization ===")

    if not VECTOR_DB_AVAILABLE:
        print("⚠ ChromaDB not available")
        return None

    with tempfile.TemporaryDirectory() as tmp_dir:
        vdb = VectorDBService(persist_directory=str(Path(tmp_dir) / "chroma"), enabled=True)

        # Add examples with similar code but different source_types
        # All have similar similarity scores
        base_code = "using System;\nclass Example { }"
        examples = [
            ("inline_1", base_code + " // inline", "inline"),
            ("cs_file_1", base_code + " // cs", "cs_file"),
            ("gist_1", base_code + " // gist", "gist"),
            ("cs_file_2", base_code + " // cs2", "cs_file"),
        ]

        for ex_id, code, src_type in examples:
            vdb.add_example(
                ex_id, code,
                metadata={"family": "test", "source_type": src_type},
                drift_score=0.0
            )

        # Search - cs_file should come first
        results = vdb.search_similar(base_code, family="test", k=10)
        print(f"Search returned {len(results)} results:")

        # Extract source types in order
        source_types = [r[3]["source_type"] for r in results]
        for i, (ex_id, _, _, meta) in enumerate(results):
            print(f"  {i+1}. {ex_id}: source_type={meta['source_type']}")

        # Count cs_file positions
        cs_file_positions = [i for i, st in enumerate(source_types) if st == "cs_file"]
        non_cs_positions = [i for i, st in enumerate(source_types) if st != "cs_file"]

        # Check if all cs_file come before non-cs_file
        if cs_file_positions and non_cs_positions:
            max_cs_pos = max(cs_file_positions)
            min_non_cs_pos = min(non_cs_positions)
            if max_cs_pos < min_non_cs_pos:
                print("✓ All cs_file examples ranked before non-cs_file")
                return True
            else:
                print(f"✗ cs_file not prioritized: cs_file max pos={max_cs_pos}, non-cs min pos={min_non_cs_pos}")
                return False
        else:
            print("⚠ Not enough examples to test priority")
            return None


def test_combined_filter_and_priority():
    """Test combined app_context filtering + cs_file prioritization."""
    print("\n=== Test: Combined Filtering + Prioritization ===")

    if not VECTOR_DB_AVAILABLE:
        print("⚠ ChromaDB not available")
        return None

    with tempfile.TemporaryDirectory() as tmp_dir:
        vdb = VectorDBService(persist_directory=str(Path(tmp_dir) / "chroma"), enabled=True)

        # Add mixed examples
        code = "using System;"
        examples = [
            ("console_inline", code, "console", "inline"),
            ("console_cs_1", code, "console", "cs_file"),
            ("console_cs_2", code, "console", "cs_file"),
            ("library_cs", code, "library", "cs_file"),
            ("aspnet_inline", code, "aspnet_minimal", "inline"),
        ]

        for ex_id, c, ctx, src in examples:
            vdb.add_example(
                ex_id, c,
                metadata={"family": "test", "app_context": ctx, "source_type": src},
                drift_score=0.0
            )

        # Search with app_context filter
        results = vdb.search_similar(code, family="test", app_context="console", k=10)
        print(f"Search (app_context='console') returned {len(results)} results")

        # Validate: all should be console, cs_file should come first
        if len(results) == 0:
            print("✗ No results returned")
            return False

        contexts = [r[3]["app_context"] for r in results]
        source_types = [r[3]["source_type"] for r in results]

        # Check all are console
        if not all(c == "console" for c in contexts):
            print(f"✗ Found non-console results: {contexts}")
            return False

        # Check cs_file comes first
        if source_types[0] != "cs_file":
            print(f"✗ First result is not cs_file: {source_types}")
            return False

        print("✓ Combined filtering and prioritization work correctly")
        return True


def test_backward_compatibility():
    """Test backward compatibility."""
    print("\n=== Test: Backward Compatibility ===")

    if not VECTOR_DB_AVAILABLE:
        print("⚠ ChromaDB not available")
        return None

    with tempfile.TemporaryDirectory() as tmp_dir:
        vdb = VectorDBService(persist_directory=str(Path(tmp_dir) / "chroma"), enabled=True)
        vdb.add_example("ex1", "code", metadata={"family": "test"}, drift_score=0.0)

        try:
            # All these should work without errors
            vdb.search_similar("code")
            vdb.search_similar("code", family="test")
            vdb.search_similar("code", family="test", k=5)
            vdb.search_similar("code", family="test", k=5, min_similarity=0.0)
            vdb.search_similar("code", family="test", k=5, min_similarity=0.0, exclude_high_drift=True)
            print("✓ All legacy API calls succeeded")
            return True
        except Exception as e:
            print(f"✗ Backward compatibility broken: {e}")
            return False


def main():
    """Run tests."""
    print("="*70)
    print("VDB-02: Architecture-Aware Search - Simple Tests")
    print("="*70)

    tests = [
        ("app_context filtering", test_app_context_filtering),
        ("cs_file prioritization", test_cs_file_priority),
        ("combined filter+priority", test_combined_filter_and_priority),
        ("backward compatibility", test_backward_compatibility),
    ]

    results = {}
    for name, test_func in tests:
        results[name] = test_func()

    print("\n" + "="*70)
    print("Summary:")
    print("="*70)

    for name, result in results.items():
        status = "✓ PASS" if result is True else ("✗ FAIL" if result is False else "⚠ SKIP")
        print(f"{name}: {status}")

    passed = sum(1 for r in results.values() if r is True)
    failed = sum(1 for r in results.values() if r is False)
    skipped = sum(1 for r in results.values() if r is None)

    print(f"\nPassed: {passed}, Failed: {failed}, Skipped: {skipped}")

    if failed > 0:
        return 1
    elif passed == 0:
        print("\n⚠ ALL TESTS SKIPPED")
        return 0
    else:
        print("\n✅ ALL TESTS PASSED")
        return 0


if __name__ == "__main__":
    sys.exit(main())
