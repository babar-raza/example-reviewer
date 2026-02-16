#!/usr/bin/env python3
"""
Integration test for Vector DB indexing of CS_FILE examples.

Tests WS2: VDB-01 implementation by creating a temporary database with
CS_FILE examples and verifying they are indexed in ChromaDB.
"""

import sys
import os
import sqlite3
import tempfile
import shutil
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.database import Database
from src.core.models import ExampleStatus, SourceType
from src.services.vector_db_service import VectorDBService, VECTOR_DB_AVAILABLE
from src.core.config import ConfigurationManager
from src.pipeline.orchestrator import PipelineOrchestrator


def create_test_database_with_cs_files(db_path: Path, run_id: str):
    """Create a test database with verified CS_FILE examples."""
    db = Database(db_path=db_path)
    db.initialize_schema()

    # Create a test run (using correct API)
    actual_run_id = db.create_run(family="test_family")

    # Create verified CS_FILE examples
    test_examples = [
        {
            "example_id": "cs_001",
            "family": "test_family",
            "source_type": SourceType.CS_FILE.value,
            "status": ExampleStatus.VERIFIED.value,
            "verified_code": "using System;\nclass Test1 { }",
            "app_context": "console",
            "topic": "Test Topic 1",
            "section_heading": "Section 1",
            "file_path": "/path/to/test1.cs",
        },
        {
            "example_id": "cs_002",
            "family": "test_family",
            "source_type": SourceType.CS_FILE.value,
            "status": ExampleStatus.VERIFIED.value,
            "verified_code": "using System.IO;\nclass Test2 { }",
            "app_context": "library",
            "topic": "Test Topic 2",
            "section_heading": "Section 2",
            "file_path": "/path/to/test2.cs",
        },
        {
            "example_id": "inline_001",
            "family": "test_family",
            "source_type": SourceType.INLINE.value,
            "status": ExampleStatus.VERIFIED.value,
            "verified_code": "using System;\nclass Inline { }",
            "app_context": "console",
            "topic": "Inline Topic",
            "section_heading": "Inline Section",
            "file_path": "/path/to/markdown.md",
        },
    ]

    # Insert examples directly into database
    with db.get_connection() as conn:
        for example in test_examples:
            conn.execute(
                """
                INSERT INTO example_records (
                    example_id, family, source_type, status,
                    verified_code, app_context, topic, section_heading,
                    file_path, discovery_run_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    example["example_id"],
                    example["family"],
                    example["source_type"],
                    example["status"],
                    example["verified_code"],
                    example["app_context"],
                    example["topic"],
                    example["section_heading"],
                    example["file_path"],
                    actual_run_id,
                )
            )
        conn.commit()

    return db


def test_vector_db_disabled():
    """Test 1: Vector DB disabled (default behavior)."""
    print("\n=== Test 1: Vector DB Disabled ===")

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        db_path = tmp_path / "test.db"
        run_id = "test_run_disabled"

        # Create test database
        db = create_test_database_with_cs_files(db_path, run_id)

        # Create orchestrator without vector DB
        orch = PipelineOrchestrator(
            db_path=db_path,
            artifacts_dir=tmp_path / "artifacts",
        )
        orch._vector_db_service = None  # Explicitly disable

        # Run phase D (includes CS_FILE auto-promotion)
        try:
            stats = orch.run_phase_d_markdown_update(
                run_id=run_id,
                family="test_family",
                dry_run=True,
            )
            print("✓ Phase D completed without errors (vector DB disabled)")
            print(f"  Stats: {stats}")
            return True
        except Exception as e:
            print(f"✗ Phase D failed: {e}")
            return False


def test_vector_db_enabled():
    """Test 2: Vector DB enabled with CS_FILE examples."""
    print("\n=== Test 2: Vector DB Enabled ===")

    if not VECTOR_DB_AVAILABLE:
        print("⚠ ChromaDB not available, skipping test")
        return None

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        db_path = tmp_path / "test.db"
        chroma_path = tmp_path / "chroma"
        run_id = "test_run_enabled"

        # Create test database
        db = create_test_database_with_cs_files(db_path, run_id)

        # Create vector DB service
        vdb = VectorDBService(
            persist_directory=str(chroma_path),
            enabled=True,
        )

        if not vdb.is_available():
            print("⚠ Vector DB service not available")
            return None

        # Create orchestrator with vector DB
        orch = PipelineOrchestrator(
            db_path=db_path,
            artifacts_dir=tmp_path / "artifacts",
        )
        orch._vector_db_service = vdb

        # Run phase D (includes CS_FILE auto-promotion and indexing)
        try:
            stats = orch.run_phase_d_markdown_update(
                run_id=run_id,
                family="test_family",
                dry_run=True,
            )
            print("✓ Phase D completed with vector DB enabled")
            print(f"  Stats: {stats}")

            # Verify CS_FILE examples were indexed
            count = vdb.count(family="test_family")
            print(f"✓ Vector DB contains {count} examples")

            if count >= 2:
                print("✓ Expected CS_FILE examples indexed (2+)")

                # Try to retrieve indexed examples
                for collection_name in ["original_examples"]:
                    try:
                        collection = vdb._get_collection(collection_name)
                        results = collection.get(where={"family": "test_family"})
                        if results['ids']:
                            print(f"✓ Found {len(results['ids'])} examples in {collection_name}")
                            for i, ex_id in enumerate(results['ids']):
                                metadata = results['metadatas'][i]
                                print(f"  - {ex_id}: source_type={metadata.get('source_type')}, "
                                      f"read_only={metadata.get('read_only')}, "
                                      f"drift_score={metadata.get('drift_score')}")
                    except Exception as e:
                        print(f"  Could not query {collection_name}: {e}")

                return True
            else:
                print(f"✗ Expected 2+ examples, got {count}")
                return False

        except Exception as e:
            print(f"✗ Phase D failed: {e}")
            import traceback
            traceback.print_exc()
            return False


def test_vector_db_search():
    """Test 3: Vector DB search functionality."""
    print("\n=== Test 3: Vector DB Search ===")

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

        # Add test examples
        vdb.add_example(
            example_id="search_001",
            code="using System;\nusing System.IO;\nclass FileReader { }",
            metadata={
                "family": "test_family",
                "source": "example_repo",
                "source_type": "cs_file",
                "read_only": True,
            },
            drift_score=0.0,
        )

        # Search for similar examples
        results = vdb.search_similar(
            query_code="using System.IO;",
            family="test_family",
            k=1,
        )

        if results:
            print(f"✓ Search returned {len(results)} results")
            for ex_id, code, similarity, metadata in results:
                print(f"  - {ex_id}: similarity={similarity:.3f}")
                print(f"    source={metadata.get('source')}, read_only={metadata.get('read_only')}")
            return True
        else:
            print("✗ Search returned no results")
            return False


def main():
    """Run all integration tests."""
    print("="*70)
    print("Vector DB Knowledge Indexing Integration Tests (VDB-01)")
    print("="*70)

    results = {
        "Test 1 (Disabled)": test_vector_db_disabled(),
        "Test 2 (Enabled)": test_vector_db_enabled(),
        "Test 3 (Search)": test_vector_db_search(),
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
