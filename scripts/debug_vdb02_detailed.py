#!/usr/bin/env python3
"""Detailed debug of VDB-02."""

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
    vdb = VectorDBService(persist_directory=str(Path(tmp_dir) / "chroma"), enabled=True)

    print("=== Adding Examples ===")
    examples = [
        ("ex1", "code1", {"family": "test", "app_context": "console", "type": "A"}),
        ("ex2", "code2", {"family": "test", "app_context": "library", "type": "B"}),
    ]

    for ex_id, code, meta in examples:
        success = vdb.add_example(ex_id, code, metadata=meta, drift_score=0.0)
        print(f"Added {ex_id}: {success}")

    print("\n=== Checking Collections ===")
    for coll_name in ["original_examples", "fixed_examples"]:
        try:
            coll = vdb._get_collection(coll_name)
            all_data = coll.get()
            print(f"\n{coll_name}: {len(all_data['ids'])} items")
            for i, ex_id in enumerate(all_data['ids']):
                meta = all_data['metadatas'][i]
                print(f"  {ex_id}: {meta}")
        except Exception as e:
            print(f"{coll_name}: Error - {e}")

    print("\n=== Search Tests ===")

    # Test 1: No filter
    print("\n1. Search with no filters:")
    results = vdb.search_similar("code", k=10)
    print(f"   Results: {len(results)}")
    for ex_id, code, sim, meta in results:
        print(f"   - {ex_id}: {meta}")

    # Test 2: Family filter only
    print("\n2. Search with family='test':")
    results = vdb.search_similar("code", family="test", k=10)
    print(f"   Results: {len(results)}")
    for ex_id, code, sim, meta in results:
        print(f"   - {ex_id}: {meta}")

    # Test 3: app_context filter only
    print("\n3. Search with app_context='console':")
    results = vdb.search_similar("code", app_context="console", k=10)
    print(f"   Results: {len(results)}")
    for ex_id, code, sim, meta in results:
        print(f"   - {ex_id}: {meta}")

    # Test 4: Both filters
    print("\n4. Search with family='test' AND app_context='console':")
    results = vdb.search_similar("code", family="test", app_context="console", k=10)
    print(f"   Results: {len(results)}")
    for ex_id, code, sim, meta in results:
        print(f"   - {ex_id}: {meta}")
