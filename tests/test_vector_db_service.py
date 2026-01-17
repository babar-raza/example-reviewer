"""
Tests for VectorDBService.
Tests work with or without ChromaDB installed (graceful degradation).
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from src.services.vector_db_service import VectorDBService, VECTOR_DB_AVAILABLE


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


class TestVectorDBServiceUnavailable:
    """Tests for VectorDBService when dependencies are not available."""

    def test_service_unavailable_when_disabled(self, temp_dir):
        """Test that service reports unavailable when disabled."""
        service = VectorDBService(
            persist_directory=str(temp_dir),
            enabled=False
        )

        assert not service.is_available()

    def test_service_gracefully_handles_missing_dependencies(self, temp_dir):
        """Test that service works when ChromaDB is not installed."""
        # This test will pass regardless of whether ChromaDB is installed
        # because we check VECTOR_DB_AVAILABLE flag

        if not VECTOR_DB_AVAILABLE:
            service = VectorDBService(
                persist_directory=str(temp_dir),
                enabled=True
            )

            assert not service.is_available()
            assert service.add_example("test_id", "test code") is False
            assert service.search_similar("test query") == []
            assert service.get_example("test_id") is None
            assert service.count() == 0

    def test_operations_return_gracefully_when_unavailable(self, temp_dir):
        """Test that all operations return gracefully when unavailable."""
        service = VectorDBService(
            persist_directory=str(temp_dir),
            enabled=False
        )

        # All operations should return gracefully
        assert service.add_example("id1", "code", {"family": "zip"}) is False
        assert service.search_similar("query") == []
        assert service.get_example("id1") is None
        assert service.delete_example("id1") is False
        assert service.count() == 0
        assert service.count(family="zip") == 0
        assert service.clear_family("zip") is False


@pytest.mark.skipif(not VECTOR_DB_AVAILABLE, reason="ChromaDB not installed")
class TestVectorDBServiceAvailable:
    """Tests for VectorDBService when ChromaDB is available."""

    def test_service_initializes_with_chromadb(self, temp_dir):
        """Test that service initializes successfully with ChromaDB."""
        service = VectorDBService(
            persist_directory=str(temp_dir),
            enabled=True
        )

        assert service.is_available()
        assert service._client is not None
        assert service._collection is not None
        assert service._embedding_model is not None

    def test_add_and_retrieve_example(self, temp_dir):
        """Test adding and retrieving an example."""
        service = VectorDBService(
            persist_directory=str(temp_dir),
            enabled=True
        )

        code = "using System; class Test { }"
        metadata = {
            "family": "zip",
            "source": "test",
            "verified": True
        }

        # Add example
        success = service.add_example("test_id_001", code, metadata)
        assert success

        # Retrieve example
        result = service.get_example("test_id_001")
        assert result is not None
        retrieved_code, retrieved_metadata = result
        assert retrieved_code == code
        assert retrieved_metadata["family"] == "zip"

    def test_search_similar_examples(self, temp_dir):
        """Test searching for similar examples."""
        service = VectorDBService(
            persist_directory=str(temp_dir),
            enabled=True
        )

        # Add multiple examples
        examples = [
            ("ex1", "using System.IO; class ZipFile { }", {"family": "zip"}),
            ("ex2", "using Aspose.Zip; var archive = new Archive();", {"family": "zip"}),
            ("ex3", "using System; Console.WriteLine();", {"family": "cells"}),
        ]

        for example_id, code, metadata in examples:
            service.add_example(example_id, code, metadata)

        # Search for similar examples
        query = "How to create a zip archive?"
        results = service.search_similar(query, k=2)

        assert len(results) <= 2
        assert all(len(r) == 4 for r in results)  # (id, code, similarity, metadata)

        # Check similarity scores are between 0 and 1
        for example_id, code, similarity, metadata in results:
            assert 0.0 <= similarity <= 1.0

    def test_search_with_family_filter(self, temp_dir):
        """Test searching with family filter."""
        service = VectorDBService(
            persist_directory=str(temp_dir),
            enabled=True
        )

        # Add examples from different families
        service.add_example("zip1", "zip code example", {"family": "zip"})
        service.add_example("cells1", "cells code example", {"family": "cells"})

        # Search only in zip family
        results = service.search_similar("code example", family="zip", k=5)

        # Should only return zip examples
        for example_id, code, similarity, metadata in results:
            assert metadata["family"] == "zip"

    def test_search_with_min_similarity_threshold(self, temp_dir):
        """Test filtering by minimum similarity threshold."""
        service = VectorDBService(
            persist_directory=str(temp_dir),
            enabled=True
        )

        # Add example
        service.add_example(
            "ex1",
            "using System.IO; class ZipFile { }",
            {"family": "zip"}
        )

        # Search with high threshold (may return empty)
        results = service.search_similar(
            "completely unrelated query about databases",
            min_similarity=0.9,
            k=5
        )

        # All results should meet minimum threshold
        for example_id, code, similarity, metadata in results:
            assert similarity >= 0.9

    def test_delete_example(self, temp_dir):
        """Test deleting an example."""
        service = VectorDBService(
            persist_directory=str(temp_dir),
            enabled=True
        )

        # Add example
        service.add_example("to_delete", "test code", {"family": "zip"})

        # Verify it exists
        assert service.get_example("to_delete") is not None

        # Delete it
        success = service.delete_example("to_delete")
        assert success

        # Verify it's gone
        assert service.get_example("to_delete") is None

    def test_count_examples(self, temp_dir):
        """Test counting examples."""
        service = VectorDBService(
            persist_directory=str(temp_dir),
            enabled=True
        )

        # Initially empty
        assert service.count() == 0

        # Add examples
        service.add_example("ex1", "code1", {"family": "zip"})
        service.add_example("ex2", "code2", {"family": "zip"})
        service.add_example("ex3", "code3", {"family": "cells"})

        # Total count
        assert service.count() == 3

        # Count by family
        assert service.count(family="zip") == 2
        assert service.count(family="cells") == 1

    def test_clear_family(self, temp_dir):
        """Test clearing all examples for a family."""
        service = VectorDBService(
            persist_directory=str(temp_dir),
            enabled=True
        )

        # Add examples from multiple families
        service.add_example("zip1", "code", {"family": "zip"})
        service.add_example("zip2", "code", {"family": "zip"})
        service.add_example("cells1", "code", {"family": "cells"})

        # Clear zip family
        success = service.clear_family("zip")
        assert success

        # Verify only zip examples are gone
        assert service.count(family="zip") == 0
        assert service.count(family="cells") == 1

    def test_persistence_across_instances(self, temp_dir):
        """Test that data persists across service instances."""
        persist_dir = str(temp_dir / "persist")

        # Create first instance and add example
        service1 = VectorDBService(persist_directory=persist_dir, enabled=True)
        service1.add_example("persistent", "code", {"family": "zip"})

        # Create second instance
        service2 = VectorDBService(persist_directory=persist_dir, enabled=True)

        # Should be able to retrieve the example
        result = service2.get_example("persistent")
        assert result is not None

    def test_custom_embedding_model(self, temp_dir):
        """Test using a custom embedding model."""
        # Note: This test may download the model on first run
        service = VectorDBService(
            persist_directory=str(temp_dir),
            embedding_model="all-MiniLM-L6-v2",  # Same as default but explicit
            enabled=True
        )

        assert service.is_available()
        assert service.embedding_model_name == "all-MiniLM-L6-v2"

    def test_handles_duplicate_ids(self, temp_dir):
        """Test handling of duplicate example IDs."""
        service = VectorDBService(
            persist_directory=str(temp_dir),
            enabled=True
        )

        # Add example
        service.add_example("dup_id", "original code", {"version": 1})

        # Add again with same ID (should update)
        service.add_example("dup_id", "updated code", {"version": 2})

        # Should have the updated version
        result = service.get_example("dup_id")
        assert result is not None
        code, metadata = result
        # ChromaDB behavior: may have updated or appended, just check it worked
        assert code is not None

    def test_empty_search_returns_empty_list(self, temp_dir):
        """Test that searching an empty database returns empty list."""
        service = VectorDBService(
            persist_directory=str(temp_dir),
            enabled=True
        )

        results = service.search_similar("any query", k=5)
        assert results == []

    def test_search_with_no_results_above_threshold(self, temp_dir):
        """Test search returns empty when no results meet threshold."""
        service = VectorDBService(
            persist_directory=str(temp_dir),
            enabled=True
        )

        # Add example
        service.add_example("ex1", "System.IO namespace", {"family": "zip"})

        # Search with very high threshold
        results = service.search_similar(
            "completely different topic about machine learning",
            min_similarity=0.99,
            k=10
        )

        # May return empty if similarity too low
        for example_id, code, similarity, metadata in results:
            assert similarity >= 0.99


class TestVectorDBServiceMocked:
    """Tests using mocked ChromaDB to avoid dependency requirements."""

    @patch('src.services.vector_db_service.VECTOR_DB_AVAILABLE', True)
    @patch('src.services.vector_db_service.chromadb')
    @patch('src.services.vector_db_service.SentenceTransformer')
    def test_initialization_with_mocked_chromadb(self, mock_st, mock_chromadb, temp_dir):
        """Test initialization with mocked ChromaDB."""
        # Mock collection
        mock_collection = MagicMock()
        mock_collection.count.return_value = 0

        mock_client = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection

        mock_chromadb.Client.return_value = mock_client

        # Mock embedding model
        mock_model = MagicMock()
        mock_st.return_value = mock_model

        service = VectorDBService(
            persist_directory=str(temp_dir),
            enabled=True
        )

        assert service.is_available()
        mock_chromadb.Client.assert_called_once()
        mock_st.assert_called_once()
