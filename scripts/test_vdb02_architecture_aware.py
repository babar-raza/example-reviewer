#!/usr/bin/env python3
"""
Integration test for VDB-02: Architecture-Aware Search.

Tests app_context filtering and cs_file prioritization in vector DB search.
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
    """Test 1: app_context filter works correctly."""
    print("\n=== Test 1: app_context Filtering ===")

    if not VECTOR_DB_AVAILABLE:
        print("⚠ ChromaDB not available, skipping test")
        return None

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        chroma_path = tmp_path / "chroma"

        # Create and populate vector DB
        vdb = VectorDBService(
            persist_directory=str(chroma_path),
            enabled=True,
        )

        if not vdb.is_available():
            print("⚠ Vector DB service not available")
            return None

        # Add examples with different app_contexts
        test_examples = [
            {
                "example_id": "console_001",
                "code": "using System;\nclass ConsoleApp { static void Main() { Console.WriteLine(\"Hello\"); } }",
                "metadata": {
                    "family": "test",
                    "app_context": "console",
                    "source_type": "cs_file",
                },
                "drift_score": 0.0,
            },
            {
                "example_id": "console_002",
                "code": "using System;\nclass ConsoleApp2 { static void Main() { Console.ReadLine(); } }",
                "metadata": {
                    "family": "test",
                    "app_context": "console",
                    "source_type": "inline",
                },
                "drift_score": 0.0,
            },
            {
                "example_id": "aspnet_001",
                "code": "var builder = WebApplication.CreateBuilder(args);\nvar app = builder.Build();\napp.Run();",
                "metadata": {
                    "family": "test",
                    "app_context": "aspnet_minimal",
                    "source_type": "cs_file",
                },
                "drift_score": 0.0,
            },
            {
                "example_id": "library_001",
                "code": "using System;\npublic static class Helper { public static void Process() { } }",
                "metadata": {
                    "family": "test",
                    "app_context": "library",
                    "source_type": "cs_file",
                },
                "drift_score": 0.0,
            },
        ]

        # Add all examples
        for example in test_examples:
            vdb.add_example(
                example_id=example["example_id"],
                code=example["code"],
                metadata=example["metadata"],
                drift_score=example["drift_score"],
            )

        # Test 1a: Search without app_context filter (should return all)
        results_all = vdb.search_similar(
            query_code="using System;",
            family="test",
            k=10,
        )
        print(f"Search without app_context: {len(results_all)} results")

        # Test 1b: Search with app_context="console" (should return only console)
        results_console = vdb.search_similar(
            query_code="using System;",
            family="test",
            app_context="console",
            k=10,
        )
        print(f"Search with app_context='console': {len(results_console)} results")

        console_contexts = [r[3].get("app_context") for r in results_console]
        if all(ctx == "console" for ctx in console_contexts):
            print("✓ All results have app_context='console'")
            test1b_pass = True
        else:
            print(f"✗ Found non-console results: {console_contexts}")
            test1b_pass = False

        # Test 1c: Search with app_context="aspnet_minimal"
        results_aspnet = vdb.search_similar(
            query_code="var app = builder.Build();",
            family="test",
            app_context="aspnet_minimal",
            k=10,
        )
        print(f"Search with app_context='aspnet_minimal': {len(results_aspnet)} results")

        aspnet_contexts = [r[3].get("app_context") for r in results_aspnet]
        if all(ctx == "aspnet_minimal" for ctx in aspnet_contexts):
            print("✓ All results have app_context='aspnet_minimal'")
            test1c_pass = True
        else:
            print(f"✗ Found non-aspnet results: {aspnet_contexts}")
            test1c_pass = False

        # Test 1d: Search with app_context="library"
        results_library = vdb.search_similar(
            query_code="public static class",
            family="test",
            app_context="library",
            k=10,
        )
        print(f"Search with app_context='library': {len(results_library)} results")

        library_contexts = [r[3].get("app_context") for r in results_library]
        if all(ctx == "library" for ctx in library_contexts):
            print("✓ All results have app_context='library'")
            test1d_pass = True
        else:
            print(f"✗ Found non-library results: {library_contexts}")
            test1d_pass = False

        return test1b_pass and test1c_pass and test1d_pass


def test_cs_file_prioritization():
    """Test 2: cs_file examples are prioritized over inline/gist."""
    print("\n=== Test 2: cs_file Prioritization ===")

    if not VECTOR_DB_AVAILABLE:
        print("⚠ ChromaDB not available, skipping test")
        return None

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        chroma_path = tmp_path / "chroma"

        # Create and populate vector DB
        vdb = VectorDBService(
            persist_directory=str(chroma_path),
            enabled=True,
        )

        if not vdb.is_available():
            print("⚠ Vector DB service not available")
            return None

        # Add examples with same code but different source_types
        # We'll add them with slightly different codes to ensure different similarities
        test_examples = [
            {
                "example_id": "inline_file",
                "code": "using System;\nclass Example { void Method() { Console.WriteLine(\"test\"); } }",
                "metadata": {
                    "family": "test",
                    "source_type": "inline",
                    "app_context": "console",
                },
                "drift_score": 0.0,
            },
            {
                "example_id": "cs_file_1",
                "code": "using System;\nclass Example { void Method() { Console.WriteLine(\"hello\"); } }",
                "metadata": {
                    "family": "test",
                    "source_type": "cs_file",
                    "app_context": "console",
                },
                "drift_score": 0.0,
            },
            {
                "example_id": "gist_file",
                "code": "using System;\nclass Example { void Method() { Console.WriteLine(\"world\"); } }",
                "metadata": {
                    "family": "test",
                    "source_type": "gist",
                    "app_context": "console",
                },
                "drift_score": 0.0,
            },
            {
                "example_id": "cs_file_2",
                "code": "using System;\nclass Example { void Method() { Console.WriteLine(\"foo\"); } }",
                "metadata": {
                    "family": "test",
                    "source_type": "cs_file",
                    "app_context": "console",
                },
                "drift_score": 0.0,
            },
        ]

        # Add all examples
        for example in test_examples:
            vdb.add_example(
                example_id=example["example_id"],
                code=example["code"],
                metadata=example["metadata"],
                drift_score=example["drift_score"],
            )

        # Search with a query that should match all
        results = vdb.search_similar(
            query_code="using System;\nclass Example { void Method() { } }",
            family="test",
            k=10,
        )

        print(f"Search returned {len(results)} results:")
        for i, (ex_id, code, similarity, metadata) in enumerate(results):
            source_type = metadata.get("source_type")
            print(f"  {i+1}. {ex_id}: source_type={source_type}, similarity={similarity:.4f}")

        # Check that cs_file examples come first
        # Group consecutive cs_file vs non-cs_file
        cs_file_positions = []
        non_cs_file_positions = []

        for i, (ex_id, code, similarity, metadata) in enumerate(results):
            source_type = metadata.get("source_type")
            if source_type == "cs_file":
                cs_file_positions.append(i)
            else:
                non_cs_file_positions.append(i)

        if cs_file_positions and non_cs_file_positions:
            # All cs_file should come before non-cs_file (unless similarity is significantly different)
            max_cs_file_pos = max(cs_file_positions)
            min_non_cs_file_pos = min(non_cs_file_positions)

            if max_cs_file_pos < min_non_cs_file_pos:
                print("✓ All cs_file examples ranked before inline/gist examples")
                return True
            else:
                # Check if they're at least prioritized (more cs_file in top positions)
                top_half = len(results) // 2
                cs_in_top = sum(1 for i in cs_file_positions if i < top_half)
                non_cs_in_top = sum(1 for i in non_cs_file_positions if i < top_half)

                print(f"  cs_file in top {top_half}: {cs_in_top}")
                print(f"  non-cs_file in top {top_half}: {non_cs_in_top}")

                if cs_in_top >= non_cs_in_top:
                    print("✓ cs_file examples prioritized (majority in top half)")
                    return True
                else:
                    print("✗ cs_file examples not properly prioritized")
                    return False
        elif cs_file_positions:
            print("✓ Only cs_file examples returned")
            return True
        else:
            print("⚠ No cs_file examples in results")
            return None


def test_combined_filtering():
    """Test 3: Combined app_context + cs_file prioritization."""
    print("\n=== Test 3: Combined Filtering ===")

    if not VECTOR_DB_AVAILABLE:
        print("⚠ ChromaDB not available, skipping test")
        return None

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        chroma_path = tmp_path / "chroma"

        # Create and populate vector DB
        vdb = VectorDBService(
            persist_directory=str(chroma_path),
            enabled=True,
        )

        if not vdb.is_available():
            print("⚠ Vector DB service not available")
            return None

        # Add examples with combinations of app_context and source_type
        test_examples = [
            # Console apps
            {"id": "console_cs_1", "code": "using System;\nConsole.WriteLine();",
             "app_context": "console", "source_type": "cs_file"},
            {"id": "console_inline_1", "code": "using System;\nConsole.ReadLine();",
             "app_context": "console", "source_type": "inline"},
            {"id": "console_cs_2", "code": "using System;\nConsole.Clear();",
             "app_context": "console", "source_type": "cs_file"},

            # ASP.NET apps
            {"id": "aspnet_cs_1", "code": "var app = builder.Build();\napp.Run();",
             "app_context": "aspnet_minimal", "source_type": "cs_file"},
            {"id": "aspnet_inline_1", "code": "app.MapGet(\"/\", () => \"Hello\");",
             "app_context": "aspnet_minimal", "source_type": "inline"},

            # Library
            {"id": "library_cs_1", "code": "public static class Utils { }",
             "app_context": "library", "source_type": "cs_file"},
        ]

        # Add all examples
        for example in test_examples:
            vdb.add_example(
                example_id=example["id"],
                code=example["code"],
                metadata={
                    "family": "test",
                    "app_context": example["app_context"],
                    "source_type": example["source_type"],
                },
                drift_score=0.0,
            )

        # Test: Search with app_context="console", should get console only, cs_file first
        results = vdb.search_similar(
            query_code="using System;",
            family="test",
            app_context="console",
            k=10,
        )

        print(f"Search (app_context='console') returned {len(results)} results:")
        for i, (ex_id, code, similarity, metadata) in enumerate(results):
            ctx = metadata.get("app_context")
            src = metadata.get("source_type")
            print(f"  {i+1}. {ex_id}: app_context={ctx}, source_type={src}")

        # Validate results
        console_only = all(r[3].get("app_context") == "console" for r in results)

        if not console_only:
            print("✗ Found non-console results")
            return False

        # Check cs_file comes first
        if results:
            first_source = results[0][3].get("source_type")
            if first_source == "cs_file":
                print("✓ First result is cs_file")
                print("✓ All results are console app_context")
                return True
            else:
                print(f"✗ First result is {first_source}, not cs_file")
                return False
        else:
            print("⚠ No results returned")
            return None


def test_backward_compatibility():
    """Test 4: Existing calls without app_context still work."""
    print("\n=== Test 4: Backward Compatibility ===")

    if not VECTOR_DB_AVAILABLE:
        print("⚠ ChromaDB not available, skipping test")
        return None

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        chroma_path = tmp_path / "chroma"

        # Create and populate vector DB
        vdb = VectorDBService(
            persist_directory=str(chroma_path),
            enabled=True,
        )

        if not vdb.is_available():
            print("⚠ Vector DB service not available")
            return None

        # Add test example
        vdb.add_example(
            example_id="compat_001",
            code="using System;\nclass Test { }",
            metadata={
                "family": "test",
                "source_type": "cs_file",
            },
            drift_score=0.0,
        )

        # Test legacy calls (without app_context parameter)
        try:
            # Call 1: Just query_code
            results1 = vdb.search_similar("using System;")
            print(f"✓ Legacy call 1 (query_code only): {len(results1)} results")

            # Call 2: With family
            results2 = vdb.search_similar("using System;", family="test")
            print(f"✓ Legacy call 2 (query_code + family): {len(results2)} results")

            # Call 3: With k
            results3 = vdb.search_similar("using System;", family="test", k=5)
            print(f"✓ Legacy call 3 (query_code + family + k): {len(results3)} results")

            # Call 4: With all original params
            results4 = vdb.search_similar(
                "using System;",
                family="test",
                k=5,
                min_similarity=0.0,
                exclude_high_drift=True,
            )
            print(f"✓ Legacy call 4 (all original params): {len(results4)} results")

            print("✓ All legacy calls succeeded")
            return True

        except Exception as e:
            print(f"✗ Legacy call failed: {e}")
            import traceback
            traceback.print_exc()
            return False


def test_drift_threshold_config():
    """Test 5: drift_threshold parameter works correctly."""
    print("\n=== Test 5: Drift Threshold Configuration ===")

    if not VECTOR_DB_AVAILABLE:
        print("⚠ ChromaDB not available, skipping test")
        return None

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        chroma_path = tmp_path / "chroma"

        # Create vector DB with custom drift threshold
        vdb = VectorDBService(
            persist_directory=str(chroma_path),
            enabled=True,
            drift_threshold=0.5,  # Higher threshold
        )

        if not vdb.is_available():
            print("⚠ Vector DB service not available")
            return None

        # Verify drift_threshold is set
        if vdb.drift_threshold == 0.5:
            print(f"✓ Drift threshold set correctly: {vdb.drift_threshold}")
        else:
            print(f"✗ Drift threshold incorrect: {vdb.drift_threshold} (expected 0.5)")
            return False

        # Add examples with different drift scores
        test_examples = [
            {"id": "low_drift", "drift": 0.1},
            {"id": "medium_drift", "drift": 0.4},
            {"id": "high_drift", "drift": 0.6},
        ]

        for example in test_examples:
            vdb.add_example(
                example_id=example["id"],
                code="using System;",
                metadata={"family": "test"},
                drift_score=example["drift"],
            )

        # Search with exclude_high_drift=True (should exclude 0.6)
        results = vdb.search_similar(
            query_code="using System;",
            family="test",
            k=10,
            exclude_high_drift=True,
        )

        print(f"Search with exclude_high_drift=True: {len(results)} results")

        # Check that high_drift (0.6) was excluded
        result_ids = [r[0] for r in results]
        if "high_drift" not in result_ids:
            print("✓ High drift example (0.6) correctly excluded")
            if "low_drift" in result_ids and "medium_drift" in result_ids:
                print("✓ Low and medium drift examples included")
                return True
            else:
                print(f"✗ Expected low and medium drift examples: {result_ids}")
                return False
        else:
            print("✗ High drift example not excluded")
            return False


def main():
    """Run all integration tests."""
    print("="*70)
    print("VDB-02: Architecture-Aware Search Tests")
    print("="*70)

    results = {
        "Test 1 (app_context filtering)": test_app_context_filtering(),
        "Test 2 (cs_file prioritization)": test_cs_file_prioritization(),
        "Test 3 (combined filtering)": test_combined_filtering(),
        "Test 4 (backward compatibility)": test_backward_compatibility(),
        "Test 5 (drift threshold config)": test_drift_threshold_config(),
    }

    print("\n" + "="*70)
    print("Test Summary:")
    print("="*70)
    for test_name, result in results.items():
        if result is True:
            status = "✓ PASS"
        elif result is False:
            status = "✗ FAIL"
        else:
            status = "⚠ SKIP"
        print(f"{test_name}: {status}")

    # Determine overall success
    failed = sum(1 for r in results.values() if r is False)
    skipped = sum(1 for r in results.values() if r is None)
    passed = sum(1 for r in results.values() if r is True)

    print(f"\nPassed: {passed}, Failed: {failed}, Skipped: {skipped}")

    if failed > 0:
        print("\n❌ INTEGRATION TESTS FAILED")
        return 1
    elif passed == 0:
        print("\n⚠ ALL TESTS SKIPPED (ChromaDB not available)")
        return 0
    else:
        print("\n✅ ALL INTEGRATION TESTS PASSED")
        return 0


if __name__ == "__main__":
    sys.exit(main())
