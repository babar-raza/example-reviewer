#!/usr/bin/env python3
"""Debug ChromaDB where filter behavior."""

import sys
import tempfile
from pathlib import Path

# Fix Windows encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.vector_db_service import VECTOR_DB_AVAILABLE

if not VECTOR_DB_AVAILABLE:
    print("ChromaDB not available")
    sys.exit(1)

import chromadb
from sentence_transformers import SentenceTransformer

with tempfile.TemporaryDirectory() as tmp_dir:
    tmp_path = Path(tmp_dir)
    chroma_path = tmp_path / "chroma"

    # Create ChromaDB client
    client = chromadb.PersistentClient(path=str(chroma_path))
    collection = client.get_or_create_collection(name="test")

    # Create embedding model
    model = SentenceTransformer("all-MiniLM-L6-v2")

    # Add test examples
    examples = [
        {"id": "ex1", "family": "test", "app_context": "console"},
        {"id": "ex2", "family": "test", "app_context": "library"},
        {"id": "ex3", "family": "other", "app_context": "console"},
    ]

    for ex in examples:
        embedding = model.encode(f"code for {ex['id']}").tolist()
        collection.add(
            ids=[ex["id"]],
            embeddings=[embedding],
            documents=[f"code for {ex['id']}"],
            metadatas=[{"family": ex["family"], "app_context": ex["app_context"]}],
        )

    print("Added 3 examples")

    # Test 1: No filter
    print("\n--- Test 1: No filter ---")
    results = collection.get()
    print(f"Results: {len(results['ids'])}")
    for i, ex_id in enumerate(results['ids']):
        print(f"  - {ex_id}: {results['metadatas'][i]}")

    # Test 2: Filter by family only
    print("\n--- Test 2: Filter by family='test' ---")
    results = collection.get(where={"family": "test"})
    print(f"Results: {len(results['ids'])}")
    for i, ex_id in enumerate(results['ids']):
        print(f"  - {ex_id}: {results['metadatas'][i]}")

    # Test 3: Filter by app_context only
    print("\n--- Test 3: Filter by app_context='console' ---")
    results = collection.get(where={"app_context": "console"})
    print(f"Results: {len(results['ids'])}")
    for i, ex_id in enumerate(results['ids']):
        print(f"  - {ex_id}: {results['metadatas'][i]}")

    # Test 4: Filter by both (implicit AND)
    print("\n--- Test 4: Filter by family='test' AND app_context='console' (implicit) ---")
    results = collection.get(where={"family": "test", "app_context": "console"})
    print(f"Results: {len(results['ids'])}")
    for i, ex_id in enumerate(results['ids']):
        print(f"  - {ex_id}: {results['metadatas'][i]}")

    # Test 5: Filter with explicit $and
    print("\n--- Test 5: Filter with explicit $and ---")
    try:
        results = collection.get(where={"$and": [{"family": "test"}, {"app_context": "console"}]})
        print(f"Results: {len(results['ids'])}")
        for i, ex_id in enumerate(results['ids']):
            print(f"  - {ex_id}: {results['metadatas'][i]}")
    except Exception as e:
        print(f"Error: {e}")

    # Test 6: Query (vector search) with filters
    print("\n--- Test 6: Query (vector search) with family='test' AND app_context='console' ---")
    query_embedding = model.encode("code for ex1").tolist()
    try:
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=3,
            where={"family": "test", "app_context": "console"},
        )
        print(f"Results: {len(results['ids'][0]) if results['ids'] else 0}")
        if results['ids']:
            for i, ex_id in enumerate(results['ids'][0]):
                print(f"  - {ex_id}: {results['metadatas'][0][i]}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
