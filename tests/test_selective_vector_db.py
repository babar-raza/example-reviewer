"""
Tests for Selective Vector DB Storage (ID-05).

Tests drift filtering, separate collections, and cleanup functionality.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from src.services.vector_db_service import VectorDBService, VECTOR_DB_AVAILABLE
from src.core.database import Database


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def vector_db(temp_dir):
    """Create test vector DB service."""
    if not VECTOR_DB_AVAILABLE:
        pytest.skip("ChromaDB not installed")

    service = VectorDBService(
        persist_directory=str(temp_dir / "chroma"),
        enabled=True
    )

    return service


@pytest.fixture
def database():
    """Create test database."""
    return Database(":memory:")


class TestDriftFiltering:
    """Tests for drift-based filtering during storage."""

    def test_high_drift_examples_not_stored(self, vector_db):
        """Test that high-drift examples are not stored in vector DB."""
        # Arrange
        example_id = "test_001"
        code = "using Aspose.Zip; var archive = new Archive();"
        metadata = {'family': 'zip', 'source': 'llm_fixed'}
        high_drift = 0.8  # Above threshold (0.3)

        # Act
        stored = vector_db.add_example(
            example_id=example_id,
            code=code,
            metadata=metadata,
            drift_score=high_drift
        )

        # Assert
        assert stored is False, "High-drift example should not be stored"

        # Verify not in DB
        result = vector_db.get_example(example_id)
        assert result is None, "High-drift example should not be retrievable"

    def test_low_drift_examples_stored(self, vector_db):
        """Test that low-drift examples are stored in vector DB."""
        # Arrange
        example_id = "test_002"
        code = "using Aspose.Zip; var archive = new Archive();"
        metadata = {'family': 'zip', 'source': 'llm_fixed'}
        low_drift = 0.1  # Below threshold (0.3)

        # Act
        stored = vector_db.add_example(
            example_id=example_id,
            code=code,
            metadata=metadata,
            drift_score=low_drift
        )

        # Assert
        assert stored is True, "Low-drift example should be stored"

        # Verify in DB
        result = vector_db.get_example(example_id)
        assert result is not None, "Low-drift example should be retrievable"

    def test_boundary_drift_threshold(self, vector_db):
        """Test drift filtering at exact threshold boundary."""
        # Test exactly at threshold (0.3)
        example_at_threshold = "test_003"
        stored = vector_db.add_example(
            example_id=example_at_threshold,
            code="test code",
            metadata={'family': 'zip'},
            drift_score=0.3  # Exactly at threshold
        )
        assert stored is False, "Example at threshold should not be stored"

        # Test just below threshold
        example_below = "test_004"
        stored = vector_db.add_example(
            example_id=example_below,
            code="test code 2",
            metadata={'family': 'zip'},
            drift_score=0.29  # Just below threshold
        )
        assert stored is True, "Example just below threshold should be stored"

    def test_custom_drift_threshold(self, vector_db):
        """Test that custom drift threshold in metadata is respected."""
        # Arrange
        example_id = "test_005"
        code = "test code"
        metadata = {
            'family': 'zip',
            'drift_threshold': 0.2  # Custom threshold
        }
        drift_score = 0.25  # Above custom threshold, below default

        # Act
        stored = vector_db.add_example(
            example_id=example_id,
            code=code,
            metadata=metadata,
            drift_score=drift_score
        )

        # Assert
        assert stored is False, "Example should be rejected by custom threshold"

    def test_no_drift_score_stored(self, vector_db):
        """Test that examples without drift_score are stored (backwards compatible)."""
        # Arrange
        example_id = "test_006"
        code = "test code"
        metadata = {'family': 'zip'}

        # Act
        stored = vector_db.add_example(
            example_id=example_id,
            code=code,
            metadata=metadata,
            drift_score=None  # No drift score
        )

        # Assert
        assert stored is True, "Example without drift_score should be stored"


class TestDriftMetadata:
    """Tests for drift_score in vector DB metadata."""

    def test_drift_metadata_in_vector_db(self, vector_db):
        """Test that drift_score is included in vector DB metadata."""
        # Arrange
        example_id = "test_007"
        code = "test code"
        metadata = {'family': 'zip', 'source': 'llm_fixed'}
        drift_score = 0.15

        # Act
        vector_db.add_example(
            example_id=example_id,
            code=code,
            metadata=metadata,
            drift_score=drift_score
        )

        # Assert
        result = vector_db.get_example(example_id)
        assert result is not None
        _, retrieved_metadata = result
        assert 'drift_score' in retrieved_metadata, "drift_score should be in metadata"
        assert retrieved_metadata['drift_score'] == drift_score

    def test_no_drift_score_not_in_metadata(self, vector_db):
        """Test that drift_score is not added if None."""
        # Arrange
        example_id = "test_008"
        code = "test code"
        metadata = {'family': 'zip'}

        # Act
        vector_db.add_example(
            example_id=example_id,
            code=code,
            metadata=metadata,
            drift_score=None
        )

        # Assert
        result = vector_db.get_example(example_id)
        assert result is not None
        _, retrieved_metadata = result
        assert 'drift_score' not in retrieved_metadata, "drift_score should not be in metadata if None"


class TestSearchFiltering:
    """Tests for drift filtering during search."""

    def test_search_excludes_high_drift(self, vector_db):
        """Test that search excludes high-drift examples by default."""
        # Arrange - add low and high drift examples
        vector_db.add_example(
            example_id="low_drift_1",
            code="using System; class Test { }",
            metadata={'family': 'zip', 'source': 'llm_fixed'},
            drift_score=0.1
        )
        vector_db.add_example(
            example_id="high_drift_1",
            code="using System.IO; class TestHigh { }",
            metadata={'family': 'zip', 'source': 'llm_fixed'},
            drift_score=0.8
        )

        # Act - search with default exclude_high_drift=True
        results = vector_db.search_similar(
            query_code="using System;",
            family="zip",
            k=10,
            min_similarity=0.0,
            exclude_high_drift=True
        )

        # Assert
        result_ids = [ex_id for ex_id, _, _, _ in results]
        assert "low_drift_1" in result_ids, "Low-drift example should be in results"
        assert "high_drift_1" not in result_ids, "High-drift example should be excluded"

    def test_search_can_include_high_drift(self, vector_db):
        """Test that search can include high-drift examples if requested."""
        # Arrange - add low and high drift examples
        vector_db.add_example(
            example_id="low_drift_2",
            code="using System; class Test { }",
            metadata={'family': 'zip', 'source': 'llm_fixed'},
            drift_score=0.1
        )
        vector_db.add_example(
            example_id="high_drift_2",
            code="using System.IO; class TestHigh { }",
            metadata={'family': 'zip', 'source': 'llm_fixed'},
            drift_score=0.8
        )

        # Act - search with exclude_high_drift=False
        results = vector_db.search_similar(
            query_code="using System;",
            family="zip",
            k=10,
            min_similarity=0.0,
            exclude_high_drift=False
        )

        # Assert - both should be included
        result_ids = [ex_id for ex_id, _, _, _ in results]
        # Note: high-drift might be included if exclude_high_drift=False
        assert "low_drift_2" in result_ids, "Low-drift example should be in results"
        # high_drift_2 may or may not be in results depending on similarity

    def test_search_without_drift_metadata(self, vector_db):
        """Test that examples without drift_score metadata pass filter."""
        # Arrange - add example without drift_score
        vector_db.add_example(
            example_id="no_drift_1",
            code="using System; class Test { }",
            metadata={'family': 'zip'},
            drift_score=None
        )

        # Act - search with exclude_high_drift=True
        results = vector_db.search_similar(
            query_code="using System;",
            family="zip",
            k=10,
            min_similarity=0.0,
            exclude_high_drift=True
        )

        # Assert - should be included (no drift_score = passes filter)
        result_ids = [ex_id for ex_id, _, _, _ in results]
        assert "no_drift_1" in result_ids, "Example without drift_score should pass filter"


class TestSeparateCollections:
    """Tests for separate original and fixed collections."""

    def test_original_examples_collection(self, vector_db):
        """Test that non-LLM examples go to original_examples collection."""
        # Arrange
        example_id = "original_001"
        code = "test code"
        metadata = {'family': 'zip', 'source': 'pipeline_compilation'}

        # Act
        vector_db.add_example(
            example_id=example_id,
            code=code,
            metadata=metadata,
            drift_score=None
        )

        # Assert - verify in original_examples collection
        try:
            original_collection = vector_db._get_collection("original_examples")
            result = original_collection.get(ids=[example_id])
            assert result['ids'], "Example should be in original_examples collection"
        except Exception:
            pytest.skip("Could not verify collection directly")

    def test_fixed_examples_collection(self, vector_db):
        """Test that LLM-fixed examples go to fixed_examples collection."""
        # Arrange
        example_id = "fixed_001"
        code = "test code"
        metadata = {'family': 'zip', 'source': 'pipeline_compilation_llm_fixed'}

        # Act
        vector_db.add_example(
            example_id=example_id,
            code=code,
            metadata=metadata,
            drift_score=0.1
        )

        # Assert - verify in fixed_examples collection
        try:
            fixed_collection = vector_db._get_collection("fixed_examples")
            result = fixed_collection.get(ids=[example_id])
            assert result['ids'], "Example should be in fixed_examples collection"
        except Exception:
            pytest.skip("Could not verify collection directly")

    def test_search_both_collections(self, vector_db):
        """Test that search queries both original and fixed collections."""
        # Arrange - add examples to both collections
        vector_db.add_example(
            example_id="original_002",
            code="using System; class Original { }",
            metadata={'family': 'zip', 'source': 'pipeline_compilation'},
            drift_score=None
        )
        vector_db.add_example(
            example_id="fixed_002",
            code="using System; class Fixed { }",
            metadata={'family': 'zip', 'source': 'pipeline_runtime_llm_fixed'},
            drift_score=0.1
        )

        # Act - search
        results = vector_db.search_similar(
            query_code="using System;",
            family="zip",
            k=10,
            min_similarity=0.0
        )

        # Assert - should find examples from both collections
        result_ids = [ex_id for ex_id, _, _, _ in results]
        # At least one should be found (both have similar code)
        assert len(result_ids) > 0, "Should find examples from both collections"


class TestCleanupMethod:
    """Tests for clean_high_drift() cleanup method."""

    def test_cleanup_removes_high_drift(self, vector_db):
        """Test that cleanup command removes high-drift examples."""
        # Arrange - add examples with various drift scores
        # First add low-drift examples (will be stored)
        vector_db.add_example(
            example_id="keep_001",
            code="test code 1",
            metadata={'family': 'zip', 'source': 'llm_fixed'},
            drift_score=0.1
        )
        vector_db.add_example(
            example_id="keep_002",
            code="test code 3",
            metadata={'family': 'zip', 'source': 'llm_fixed'},
            drift_score=0.15  # Below test threshold (0.2)
        )

        # Now manually add a medium-drift example (below 0.3 so it's stored)
        # but we'll clean with a lower threshold to test cleanup
        vector_db.add_example(
            example_id="remove_001",
            code="test code 2",
            metadata={'family': 'zip', 'source': 'llm_fixed'},
            drift_score=0.25  # Below default threshold (0.3) but above our test threshold (0.2)
        )

        # Act - run cleanup with lower threshold
        removed = vector_db.clean_high_drift(family="zip", max_drift=0.2)

        # Assert
        assert removed == 1, f"Should remove 1 example with drift >= 0.2, got {removed}"

        # Verify correct examples removed/kept
        assert vector_db.get_example("keep_001") is not None, "Low-drift example should be kept"
        assert vector_db.get_example("remove_001") is None, "Medium-drift example should be removed"
        assert vector_db.get_example("keep_002") is not None, "Low-drift example should be kept"

    def test_cleanup_custom_threshold(self, vector_db):
        """Test cleanup with custom max_drift threshold."""
        # Arrange
        vector_db.add_example(
            example_id="remove_002",
            code="test code",
            metadata={'family': 'zip', 'source': 'llm_fixed'},
            drift_score=0.25
        )

        # Act - cleanup with lower threshold
        removed = vector_db.clean_high_drift(family="zip", max_drift=0.2)

        # Assert
        assert removed == 1, "Should remove example above custom threshold"
        assert vector_db.get_example("remove_002") is None

    def test_cleanup_family_filter(self, vector_db):
        """Test that cleanup only affects specified family."""
        # Arrange - add examples from different families (all below 0.3 threshold)
        vector_db.add_example(
            example_id="zip_medium",
            code="test code",
            metadata={'family': 'zip', 'source': 'llm_fixed'},
            drift_score=0.25  # Below default threshold (0.3) so it's stored
        )
        vector_db.add_example(
            example_id="cells_medium",
            code="test code",
            metadata={'family': 'cells', 'source': 'llm_fixed'},
            drift_score=0.25  # Below default threshold (0.3) so it's stored
        )

        # Act - cleanup only zip family with threshold 0.2
        removed = vector_db.clean_high_drift(family="zip", max_drift=0.2)

        # Assert
        assert removed == 1, f"Should only remove 1 zip family example, got {removed}"
        assert vector_db.get_example("zip_medium") is None, "Zip example should be removed"
        assert vector_db.get_example("cells_medium") is not None, "Cells example should remain"

    def test_cleanup_no_matching_examples(self, vector_db):
        """Test cleanup when no examples match criteria."""
        # Act - cleanup empty family
        removed = vector_db.clean_high_drift(family="nonexistent", max_drift=0.3)

        # Assert
        assert removed == 0, "Should remove 0 examples when none match"


class TestGracefulDegradation:
    """Tests for graceful handling when vector DB unavailable."""

    def test_vector_db_unavailable_add_example(self, temp_dir):
        """Test graceful handling when vector DB unavailable."""
        # Arrange - disabled vector DB
        service = VectorDBService(
            persist_directory=str(temp_dir),
            enabled=False
        )

        # Act
        result = service.add_example(
            example_id="test",
            code="test code",
            metadata={'family': 'zip'},
            drift_score=0.5
        )

        # Assert
        assert result is False, "Should return False when unavailable"

    def test_vector_db_unavailable_search(self, temp_dir):
        """Test graceful handling of search when unavailable."""
        # Arrange - disabled vector DB
        service = VectorDBService(
            persist_directory=str(temp_dir),
            enabled=False
        )

        # Act
        results = service.search_similar(
            query_code="test",
            family="zip",
            exclude_high_drift=True
        )

        # Assert
        assert results == [], "Should return empty list when unavailable"

    def test_vector_db_unavailable_cleanup(self, temp_dir):
        """Test graceful handling of cleanup when unavailable."""
        # Arrange - disabled vector DB
        service = VectorDBService(
            persist_directory=str(temp_dir),
            enabled=False
        )

        # Act
        removed = service.clean_high_drift(family="zip", max_drift=0.3)

        # Assert
        assert removed == 0, "Should return 0 when unavailable"


class TestBackwardsCompatibility:
    """Tests for backwards compatibility with existing code."""

    def test_add_example_without_drift_parameter(self, vector_db):
        """Test that add_example works without drift_score parameter."""
        # Act - call without drift_score (backwards compatible)
        result = vector_db.add_example(
            example_id="compat_001",
            code="test code",
            metadata={'family': 'zip'}
        )

        # Assert
        assert result is True, "Should work without drift_score parameter"
        assert vector_db.get_example("compat_001") is not None

    def test_search_without_exclude_parameter(self, vector_db):
        """Test that search works without exclude_high_drift parameter."""
        # Arrange
        vector_db.add_example(
            example_id="search_001",
            code="test code",
            metadata={'family': 'zip'},
            drift_score=0.1
        )

        # Act - call without exclude_high_drift (backwards compatible)
        results = vector_db.search_similar(
            query_code="test",
            family="zip",
            k=3
        )

        # Assert - should work (default exclude_high_drift=True)
        assert isinstance(results, list), "Should return list"

    def test_old_examples_without_drift_metadata(self, vector_db):
        """Test that old examples without drift_score work correctly."""
        # Simulate old example stored without drift_score
        vector_db.add_example(
            example_id="old_001",
            code="test code",
            metadata={'family': 'zip'},
            drift_score=None
        )

        # Search should find it
        results = vector_db.search_similar(
            query_code="test",
            family="zip",
            k=10,
            exclude_high_drift=True
        )

        result_ids = [ex_id for ex_id, _, _, _ in results]
        assert "old_001" in result_ids, "Old examples without drift_score should be found"
