#!/usr/bin/env python3
"""Debug script to test VDB-02 functionality."""

import sys
import tempfile
from pathlib import Path

# Fix Windows encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.vector_db_service import VectorDBService, VECTOR_DB_AVAILABLE

if not VECTOR_DB_AVAILABLE:
    print("ChromaDB not available")
    sys.exit(1)

with tempfile.TemporaryDirectory() as tmp_dir:
    tmp_path = Path(tmp_dir)
    chroma_path = tmp_path / "chroma"

    # Create vector DB
    vdb = VectorDBService(
        persist_directory=str(chroma_path),
        enabled=True,
    )

    print(f"Vector DB available: {vdb.is_available()}")

    # Add a simple example
    success = vdb.add_example(
        example_id="test_001",
        code="using System;\nclass Test { }",
        metadata={
            "family": "test",
            "app_context": "console",
            "source_type": "cs_file",
        },
        drift_score=0.0,
    )
    print(f"Add example success: {success}")

    # Check which collection it went to
    for collection_name in ["original_examples", "fixed_examples"]:
        try:
            collection = vdb._get_collection(collection_name)
            results = collection.get()
            print(f"\n{collection_name}: {len(results['ids'])} items")
            if results['ids']:
                for i, ex_id in enumerate(results['ids']):
                    print(f"  - {ex_id}: {results['metadatas'][i]}")
        except Exception as e:
            print(f"{collection_name}: error - {e}")

    # Try searching without filter
    print("\n--- Search without filter ---")
    results = vdb.search_similar(
        query_code="using System;",
        k=10,
    )
    print(f"Results: {len(results)}")
    for ex_id, code, sim, meta in results:
        print(f"  - {ex_id}: {meta}")

    # Try searching with family filter
    print("\n--- Search with family='test' ---")
    results = vdb.search_similar(
        query_code="using System;",
        family="test",
        k=10,
    )
    print(f"Results: {len(results)}")
    for ex_id, code, sim, meta in results:
        print(f"  - {ex_id}: {meta}")

    # Try searching with app_context filter
    print("\n--- Search with app_context='console' ---")
    results = vdb.search_similar(
        query_code="using System;",
        app_context="console",
        k=10,
    )
    print(f"Results: {len(results)}")
    for ex_id, code, sim, meta in results:
        print(f"  - {ex_id}: {meta}")

    # Try searching with both filters
    print("\n--- Search with family='test' AND app_context='console' ---")
    results = vdb.search_similar(
        query_code="using System;",
        family="test",
        app_context="console",
        k=10,
    )
    print(f"Results: {len(results)}")
    for ex_id, code, sim, meta in results:
        print(f"  - {ex_id}: {meta}")
