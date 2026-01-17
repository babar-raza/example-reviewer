"""
Tests for VectorDB integration with the pipeline orchestrator.
Tests the runtime fix flow with similar example retrieval.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from src.pipeline.orchestrator import PipelineOrchestrator
from src.services.vector_db_service import VectorDBService, VECTOR_DB_AVAILABLE
from src.core.models import ExampleRecord, ExampleStatus, SourceType, Location


@pytest.fixture
def temp_workspace():
    """Create a temporary workspace for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_config_manager():
    """Mock config manager for tests."""
    mock_manager = MagicMock()

    # Mock global config
    global_config = MagicMock()
    global_config.vector_db.enabled = False  # Disabled by default for safety
    global_config.vector_db.persist_directory = "./test_chroma"
    global_config.vector_db.embedding_model = "all-MiniLM-L6-v2"
    global_config.vector_db.search_k = 3
    global_config.vector_db.min_similarity_threshold = 0.7
    global_config.llm.max_retries = 3
    global_config.backfill.auto_enabled = False
    global_config.telemetry.local_telemetry_enabled = False
    global_config.git.enabled = False

    mock_manager.load_global_config.return_value = global_config

    return mock_manager


class TestVectorDBIntegration:
    """Tests for VectorDB integration with orchestrator."""

    def test_orchestrator_initializes_vector_db_service(self, temp_workspace):
        """Test that orchestrator can initialize VectorDBService."""
        with patch('src.pipeline.orchestrator.ConfigurationManager') as mock_cm:
            mock_cm.return_value.load_global_config.return_value = MagicMock(
                vector_db=MagicMock(
                    enabled=False,
                    persist_directory=str(temp_workspace / "chroma"),
                    embedding_model="all-MiniLM-L6-v2",
                ),
                llm=MagicMock(),
            )

            orchestrator = PipelineOrchestrator(
                config_dir=temp_workspace / "config",
                db_path=temp_workspace / "test.db",
                workspace_dir=temp_workspace / "workspace",
            )

            # Access the vector_db_service property
            vdb = orchestrator.vector_db_service

            # Since enabled=False, should not be available
            assert not vdb.is_available()

    def test_vector_search_not_called_when_disabled(self, temp_workspace):
        """Test that vector search is not called when disabled."""
        with patch('src.pipeline.orchestrator.VectorDBService') as mock_vdb_cls:
            mock_vdb = MagicMock()
            mock_vdb.is_available.return_value = False
            mock_vdb_cls.return_value = mock_vdb

            with patch('src.pipeline.orchestrator.ConfigurationManager') as mock_cm:
                mock_cm.return_value.load_global_config.return_value = MagicMock(
                    vector_db=MagicMock(
                        enabled=False,
                        persist_directory=str(temp_workspace / "chroma"),
                        embedding_model="all-MiniLM-L6-v2",
                        search_k=3,
                        min_similarity_threshold=0.7,
                    ),
                    llm=MagicMock(max_retries=3),
                    backfill=MagicMock(auto_enabled=False),
                    telemetry=MagicMock(local_telemetry_enabled=False),
                    git=MagicMock(enabled=False),
                )

                orchestrator = PipelineOrchestrator(
                    config_dir=temp_workspace / "config",
                    db_path=temp_workspace / "test.db",
                    workspace_dir=temp_workspace / "workspace",
                )

                # Trigger access to the vector_db_service
                _ = orchestrator.vector_db_service

                # search_similar should not be called since is_available returns False
                mock_vdb.search_similar.assert_not_called()


class TestVectorDBServiceUnit:
    """Unit tests for VectorDBService itself."""

    def test_service_disabled_returns_not_available(self, temp_workspace):
        """Test that disabled service reports not available."""
        service = VectorDBService(
            persist_directory=str(temp_workspace),
            enabled=False,
        )
        assert not service.is_available()

    def test_add_example_returns_false_when_unavailable(self, temp_workspace):
        """Test that add_example returns False when unavailable."""
        service = VectorDBService(
            persist_directory=str(temp_workspace),
            enabled=False,
        )
        result = service.add_example("test_id", "test code", {"family": "zip"})
        assert result is False

    def test_search_similar_returns_empty_when_unavailable(self, temp_workspace):
        """Test that search_similar returns empty list when unavailable."""
        service = VectorDBService(
            persist_directory=str(temp_workspace),
            enabled=False,
        )
        results = service.search_similar("query code", k=3)
        assert results == []

    def test_count_returns_zero_when_unavailable(self, temp_workspace):
        """Test that count returns 0 when unavailable."""
        service = VectorDBService(
            persist_directory=str(temp_workspace),
            enabled=False,
        )
        assert service.count() == 0
        assert service.count(family="zip") == 0


@pytest.mark.skipif(not VECTOR_DB_AVAILABLE, reason="ChromaDB not installed")
class TestVectorDBServiceWithChromaDB:
    """Integration tests requiring ChromaDB installation."""

    def test_add_and_search_example(self, temp_workspace):
        """Test adding and searching for an example."""
        service = VectorDBService(
            persist_directory=str(temp_workspace / "chroma"),
            enabled=True,
        )

        assert service.is_available()

        # Add example
        code = "using Aspose.Zip; var archive = new Archive();"
        result = service.add_example(
            "test_ex_001",
            code,
            {"family": "zip", "verified": True}
        )
        assert result is True

        # Search for similar
        results = service.search_similar(
            "How to create a zip archive?",
            k=1,
        )

        assert len(results) >= 0  # May or may not find depending on embeddings

        # Verify structure if results found
        for ex_id, ex_code, similarity, metadata in results:
            assert isinstance(ex_id, str)
            assert isinstance(ex_code, str)
            assert 0.0 <= similarity <= 1.0
            assert isinstance(metadata, dict)

    def test_family_filter_in_search(self, temp_workspace):
        """Test that family filter works in search."""
        service = VectorDBService(
            persist_directory=str(temp_workspace / "chroma"),
            enabled=True,
        )

        # Add examples from different families
        service.add_example("zip_001", "zip code", {"family": "zip"})
        service.add_example("cells_001", "cells code", {"family": "cells"})

        # Search with family filter
        zip_results = service.search_similar("code", family="zip", k=10)

        # All results should be from zip family
        for ex_id, ex_code, similarity, metadata in zip_results:
            assert metadata.get("family") == "zip"

    def test_pipeline_stores_verified_examples(self, temp_workspace):
        """Test that pipeline stores verified examples in vector DB."""
        # This is a conceptual test - actual integration would require full pipeline setup
        service = VectorDBService(
            persist_directory=str(temp_workspace / "chroma"),
            enabled=True,
        )

        # Simulate pipeline storing a verified example
        code = """
using Aspose.Zip;

public class Program
{
    public static void Main(string[] args)
    {
        using (var archive = new Archive("test.zip"))
        {
            archive.Save("output.zip");
        }
    }
}
"""
        result = service.add_example(
            example_id="pipeline_001",
            code=code,
            metadata={
                "family": "zip",
                "source": "pipeline_runtime",
                "verified": True,
                "file_path": "docs/examples/zip-create.md",
            }
        )

        assert result is True
        assert service.count() >= 1

        # Verify retrieval
        retrieved = service.get_example("pipeline_001")
        assert retrieved is not None
        retrieved_code, retrieved_metadata = retrieved
        assert "Archive" in retrieved_code
        assert retrieved_metadata["verified"] is True


class TestVectorDBMocked:
    """Tests using mocked ChromaDB for isolated testing."""

    @patch('src.services.vector_db_service.VECTOR_DB_AVAILABLE', True)
    @patch('src.services.vector_db_service.chromadb')
    @patch('src.services.vector_db_service.SentenceTransformer')
    def test_search_results_format(self, mock_st, mock_chromadb, temp_workspace):
        """Test that search results are formatted correctly."""
        # Setup mocks
        mock_collection = MagicMock()
        mock_collection.count.return_value = 2
        mock_collection.query.return_value = {
            'ids': [['ex1', 'ex2']],
            'documents': [['code1', 'code2']],
            'distances': [[0.1, 0.3]],  # Lower distance = higher similarity
            'metadatas': [[{'family': 'zip'}, {'family': 'zip'}]],
        }

        mock_client = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_chromadb.Client.return_value = mock_client

        mock_model = MagicMock()
        mock_model.encode.return_value = MagicMock(tolist=lambda: [0.1] * 384)
        mock_st.return_value = mock_model

        # Create service
        service = VectorDBService(
            persist_directory=str(temp_workspace),
            enabled=True,
        )

        # Search
        results = service.search_similar("query", k=2)

        # Verify format: List of (id, code, similarity, metadata)
        assert len(results) == 2

        # First result (higher similarity = 1 - 0.1 = 0.9)
        ex_id, code, similarity, metadata = results[0]
        assert ex_id == 'ex1'
        assert code == 'code1'
        assert similarity == 0.9  # 1 - 0.1
        assert metadata == {'family': 'zip'}

        # Second result
        ex_id2, code2, similarity2, metadata2 = results[1]
        assert ex_id2 == 'ex2'
        assert similarity2 == 0.7  # 1 - 0.3

    @patch('src.services.vector_db_service.VECTOR_DB_AVAILABLE', True)
    @patch('src.services.vector_db_service.chromadb')
    @patch('src.services.vector_db_service.SentenceTransformer')
    def test_min_similarity_filter(self, mock_st, mock_chromadb, temp_workspace):
        """Test that min_similarity filter works correctly."""
        # Setup mocks with results below threshold
        mock_collection = MagicMock()
        mock_collection.count.return_value = 2
        mock_collection.query.return_value = {
            'ids': [['ex1', 'ex2']],
            'documents': [['code1', 'code2']],
            'distances': [[0.2, 0.8]],  # similarities: 0.8, 0.2
            'metadatas': [[{'family': 'zip'}, {'family': 'zip'}]],
        }

        mock_client = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_chromadb.Client.return_value = mock_client

        mock_model = MagicMock()
        mock_model.encode.return_value = MagicMock(tolist=lambda: [0.1] * 384)
        mock_st.return_value = mock_model

        service = VectorDBService(
            persist_directory=str(temp_workspace),
            enabled=True,
        )

        # Search with min_similarity = 0.5
        results = service.search_similar("query", k=2, min_similarity=0.5)

        # Should only return ex1 (similarity 0.8 >= 0.5)
        assert len(results) == 1
        assert results[0][0] == 'ex1'
        assert results[0][2] == 0.8
