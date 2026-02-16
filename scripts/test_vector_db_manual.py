#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Manual integration test for Vector DB indexing.

This script verifies that the vector DB indexing code works correctly
by checking logs and database state after a real run.
"""

import sys
import io
from pathlib import Path

# Fix Windows encoding issues
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.database import Database
from src.core.models import ExampleStatus, SourceType
from src.services.vector_db_service import VectorDBService, VECTOR_DB_AVAILABLE


def test_vector_db_availability():
    """Test 1: Check if ChromaDB is available."""
    print("\n=== Test 1: ChromaDB Availability ===")

    if VECTOR_DB_AVAILABLE:
        print("✓ ChromaDB and sentence-transformers are installed")
        return True
    else:
        print("✗ ChromaDB or sentence-transformers not available")
        print("  Install with: pip install chromadb>=0.4.20 sentence-transformers>=2.2.0")
        return False


def test_vector_db_initialization():
    """Test 2: Initialize Vector DB service."""
    print("\n=== Test 2: Vector DB Initialization ===")

    if not VECTOR_DB_AVAILABLE:
        print("⚠ Skipping (ChromaDB not available)")
        return None

    try:
        vdb = VectorDBService(
            persist_directory="./data/chroma",
            enabled=True,
        )

        if vdb.is_available():
            print("✓ Vector DB service initialized successfully")
            print(f"  Persist directory: {vdb.persist_directory}")
            print(f"  Embedding model: {vdb.embedding_model_name}")

            # Check collection count
            count = vdb.count()
            print(f"  Total examples in DB: {count}")

            return True
        else:
            print("✗ Vector DB service not available")
            return False

    except Exception as e:
        print(f"✗ Failed to initialize Vector DB: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_vector_db_add_example():
    """Test 3: Add example to vector DB."""
    print("\n=== Test 3: Add Example ===")

    if not VECTOR_DB_AVAILABLE:
        print("⚠ Skipping (ChromaDB not available)")
        return None

    try:
        vdb = VectorDBService(
            persist_directory="./data/chroma",
            enabled=True,
        )

        if not vdb.is_available():
            print("✗ Vector DB not available")
            return False

        # Add test example
        success = vdb.add_example(
            example_id="manual_test_001",
            code="using System;\nusing System.IO;\nclass Test { }",
            metadata={
                "family": "test",
                "source": "manual_test",
                "source_type": "cs_file",
                "app_context": "console",
                "topic": "Manual Test",
                "section_heading": "Test Section",
                "file_path": "/manual/test.cs",
                "read_only": True,
            },
            drift_score=0.0,
        )

        if success:
            print("✓ Example added successfully")

            # Verify it was added
            result = vdb.get_example("manual_test_001")
            if result:
                code, metadata = result
                print(f"✓ Example retrieved successfully")
                print(f"  Code length: {len(code)} chars")
                print(f"  Metadata: source={metadata.get('source')}, "
                      f"read_only={metadata.get('read_only')}, "
                      f"drift_score={metadata.get('drift_score')}")
                return True
            else:
                print("✗ Example not found after adding")
                return False
        else:
            print("✗ Failed to add example")
            return False

    except Exception as e:
        print(f"✗ Error adding example: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_vector_db_search():
    """Test 4: Search for similar examples."""
    print("\n=== Test 4: Search Similarity ===")

    if not VECTOR_DB_AVAILABLE:
        print("⚠ Skipping (ChromaDB not available)")
        return None

    try:
        vdb = VectorDBService(
            persist_directory="./data/chroma",
            enabled=True,
        )

        if not vdb.is_available():
            print("✗ Vector DB not available")
            return False

        # Search for examples similar to System.IO usage
        results = vdb.search_similar(
            query_code="using System.IO;",
            k=3,
            min_similarity=0.0,
        )

        if results:
            print(f"✓ Search returned {len(results)} results")
            for i, (ex_id, code, similarity, metadata) in enumerate(results, 1):
                print(f"\n  Result {i}:")
                print(f"    ID: {ex_id}")
                print(f"    Similarity: {similarity:.3f}")
                print(f"    Source: {metadata.get('source')}")
                print(f"    Family: {metadata.get('family')}")
                print(f"    Read-only: {metadata.get('read_only')}")
                print(f"    Code preview: {code[:100]}...")
            return True
        else:
            print("⚠ No results found (empty database)")
            return None

    except Exception as e:
        print(f"✗ Error searching: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_check_cs_file_in_db():
    """Test 5: Check if CS_FILE examples exist in main database."""
    print("\n=== Test 5: CS_FILE Examples in Database ===")

    try:
        db = Database(db_path=Path("data/example_reviewer.db"))

        with db.get_connection() as conn:
            # Count CS_FILE examples
            result = conn.execute(
                "SELECT COUNT(*) FROM example_records WHERE source_type = ?",
                (SourceType.CS_FILE.value,)
            ).fetchone()

            cs_file_count = result[0]
            print(f"  Total CS_FILE examples in database: {cs_file_count}")

            if cs_file_count > 0:
                # Get sample
                samples = conn.execute(
                    """
                    SELECT example_id, family, file_path
                    FROM example_records
                    WHERE source_type = ?
                    LIMIT 5
                    """,
                    (SourceType.CS_FILE.value,)
                ).fetchall()

                print(f"✓ Found {cs_file_count} CS_FILE examples")
                print("  Sample:")
                for ex_id, family, file_path in samples:
                    print(f"    - {ex_id} ({family}): {file_path}")
                return True
            else:
                print("⚠ No CS_FILE examples found in database")
                return None

    except Exception as e:
        print(f"✗ Error querying database: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all manual tests."""
    print("="*70)
    print("Vector DB Manual Integration Tests (VDB-01)")
    print("="*70)

    results = {
        "Test 1 (Availability)": test_vector_db_availability(),
        "Test 2 (Initialization)": test_vector_db_initialization(),
        "Test 3 (Add Example)": test_vector_db_add_example(),
        "Test 4 (Search)": test_vector_db_search(),
        "Test 5 (CS_FILE in DB)": test_check_cs_file_in_db(),
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

    failed = sum(1 for r in results.values() if r is False)
    skipped = sum(1 for r in results.values() if r is None)
    passed = sum(1 for r in results.values() if r is True)

    print(f"\nPassed: {passed}, Failed: {failed}, Skipped: {skipped}")

    if failed > 0:
        print("\n❌ TESTS FAILED")
        return 1
    elif passed == 0:
        print("\n⚠ ALL TESTS SKIPPED")
        return 0
    else:
        print("\n✅ ALL TESTS PASSED")
        return 0


if __name__ == "__main__":
    sys.exit(main())
