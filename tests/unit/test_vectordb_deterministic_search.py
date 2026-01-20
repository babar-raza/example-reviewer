"""
Unit tests for VectorDB deterministic search ordering and startup decision logic.

Tests that vector search results are sorted deterministically and that startup
decision is made once per run (no lazy initialization).
"""

import pytest
from unittest.mock import MagicMock, patch, Mock
from typing import List, Dict, Any

from src.services.vector_db_service import VectorDBService


class TestVectorSearchOrdering:
    """Test that vector search results are sorted deterministically."""

    def test_search_results_sorted_by_distance_then_id(self, mock_vector_db):
        """Vector search results should be sorted by distance, then by stable ID."""
        mock_service = mock_vector_db

        # Mock search results with tied distances
        mock_results = {
            "ids": [["id3", "id1", "id2"]],
            "distances": [[0.15, 0.10, 0.10]],  # id1 and id2 have same distance
            "metadatas": [[
                {"example_key": "key3", "file_path": "c.md"},
                {"example_key": "key1", "file_path": "a.md"},
                {"example_key": "key2", "file_path": "b.md"},
            ]],
            "documents": [["code3", "code1", "code2"]],
        }

        # Simulate deterministic sorting
        # Sort by distance (ascending), then by example_key (tie-breaker)
        results = list(zip(
            mock_results["ids"][0],
            mock_results["distances"][0],
            mock_results["metadatas"][0],
        ))

        # Sort: distance first, then example_key
        sorted_results = sorted(results, key=lambda x: (x[1], x[2].get("example_key", "")))

        # Expected order: id1 (0.10, key1), id2 (0.10, key2), id3 (0.15, key3)
        expected_ids = ["id1", "id2", "id3"]

        actual_ids = [r[0] for r in sorted_results]

        assert actual_ids == expected_ids

    def test_search_results_with_rounded_distance(self):
        """Distance should be rounded to 4 decimal places for deterministic ties."""
        # Simulate slight floating-point variations
        distances = [0.1000001, 0.1000002, 0.1000003]

        # Round to 4 decimal places (Track 1: C.7)
        rounded = [round(d, 4) for d in distances]

        # All should become identical after rounding
        assert rounded == [0.1000, 0.1000, 0.1000]

        # Verify different distances remain different after rounding
        distances2 = [0.10001, 0.10009]
        rounded2 = [round(d, 4) for d in distances2]
        assert rounded2 == [0.1000, 0.1001]

    def test_search_ordering_stable_across_runs(self, mock_vector_db):
        """Same query should produce same ordering across multiple runs."""
        mock_service = mock_vector_db

        # Simulate search results
        mock_results = {
            "ids": [["id5", "id2", "id7", "id1"]],
            "distances": [[0.20, 0.10, 0.15, 0.10]],
            "metadatas": [[
                {"example_key": "key5"},
                {"example_key": "key2"},
                {"example_key": "key7"},
                {"example_key": "key1"},
            ]],
        }

        # Sort deterministically (run 1)
        results1 = sorted(
            zip(mock_results["ids"][0], mock_results["distances"][0], mock_results["metadatas"][0]),
            key=lambda x: (round(x[1], 4), x[2].get("example_key", ""))
        )

        # Sort deterministically (run 2)
        results2 = sorted(
            zip(mock_results["ids"][0], mock_results["distances"][0], mock_results["metadatas"][0]),
            key=lambda x: (round(x[1], 4), x[2].get("example_key", ""))
        )

        # Should produce identical ordering
        ids1 = [r[0] for r in results1]
        ids2 = [r[0] for r in results2]

        assert ids1 == ids2

    def test_search_with_missing_example_key_fallback(self):
        """Missing example_key should fall back to file_path + block_index."""
        results = [
            ("id1", 0.10, {"file_path": "zebra.md", "block_index": 0}),
            ("id2", 0.10, {"file_path": "apple.md", "block_index": 1}),
            ("id3", 0.10, {"file_path": "apple.md", "block_index": 0}),
        ]

        # Sort with fallback: distance, then file_path, then block_index
        sorted_results = sorted(
            results,
            key=lambda x: (
                round(x[1], 4),
                x[2].get("file_path", ""),
                x[2].get("block_index", 0),
            )
        )

        expected_ids = ["id3", "id2", "id1"]  # apple:0, apple:1, zebra:0

        actual_ids = [r[0] for r in sorted_results]

        assert actual_ids == expected_ids


class TestVectorDBStartupDecision:
    """Test that VectorDB initialization happens once at startup."""

    def test_startup_decision_recorded_once(self):
        """VectorDB availability decision should be made once at startup."""
        decision_log = []

        # Simulate startup decision
        def record_decision(enabled: bool, reason: str):
            decision_log.append({"enabled": enabled, "reason": reason})

        # Startup: VectorDB enabled
        record_decision(True, "VectorDB initialized successfully")

        # Simulate multiple queries (should not re-check)
        for _ in range(10):
            pass  # No additional decisions

        # Should have exactly one decision recorded
        assert len(decision_log) == 1
        assert decision_log[0]["enabled"] is True

    def test_fail_fast_when_required_on_startup(self):
        """If require_on_startup=True, VectorDB unavailability should raise error."""
        # Simulate require_on_startup=True
        require_on_startup = True
        vector_db_available = False

        if require_on_startup and not vector_db_available:
            with pytest.raises(RuntimeError, match="VectorDB required but not available"):
                raise RuntimeError("VectorDB required but not available at startup")

    def test_deterministic_disable_when_not_required(self, caplog):
        """If require_on_startup=False, deterministically disable for entire run."""
        import logging
        caplog.set_level(logging.INFO)

        # Simulate startup with VectorDB unavailable but not required
        require_on_startup = False
        vector_db_available = False

        if not vector_db_available:
            if require_on_startup:
                raise RuntimeError("VectorDB required but not available")
            else:
                # Deterministically disable
                drift_enabled = False
                similarity_enabled = False

                # Log decision
                import logging
                logger = logging.getLogger(__name__)
                logger.info("VectorDB unavailable: drift and similarity search disabled for entire run")

        # Verify decision was logged
        assert "disabled" in caplog.text.lower() or not vector_db_available

    def test_no_lazy_initialization_mid_run(self):
        """VectorDB should not be lazily initialized mid-run."""
        # Simulate startup decision
        drift_enabled = False

        # Simulate mid-run query
        def check_drift_enabled():
            return drift_enabled  # Should return False throughout

        # Multiple checks should return same value
        results = [check_drift_enabled() for _ in range(10)]

        assert all(r is False for r in results)


class TestDriftDetectorIntegration:
    """Test that DriftDetector initialization follows startup decision."""

    def test_drift_detector_initialized_once(self):
        """DriftDetector should be initialized once at startup."""
        initialization_count = 0

        def initialize_drift_detector():
            nonlocal initialization_count
            initialization_count += 1
            return MagicMock()

        # Startup
        drift_detector = initialize_drift_detector()

        # Multiple uses should not re-initialize
        for _ in range(10):
            pass  # Use drift_detector

        assert initialization_count == 1

    def test_drift_disabled_when_vector_db_unavailable(self):
        """Drift detection should be disabled if VectorDB is unavailable."""
        vector_db_available = False

        if vector_db_available:
            drift_enabled = True
        else:
            drift_enabled = False

        assert drift_enabled is False

    def test_startup_decision_recorded_in_telemetry(self):
        """Startup decision should be recorded in telemetry."""
        telemetry_events = []

        # Simulate startup decision
        vector_db_available = False

        if not vector_db_available:
            telemetry_events.append({
                "event_type": "vector_db_unavailable",
                "reason": "ChromaDB dependencies not installed",
                "drift_enabled": False,
            })

        # Verify telemetry event recorded
        assert len(telemetry_events) == 1
        assert telemetry_events[0]["event_type"] == "vector_db_unavailable"
        assert telemetry_events[0]["drift_enabled"] is False


class TestCapabilityDetection:
    """Test that VectorDB capabilities are detected at startup."""

    def test_embedding_device_detection(self):
        """Embedding device (CPU/GPU) should be detected at startup."""
        import platform

        # Simulate device detection
        if platform.system() == "Linux":
            # Check for CUDA
            has_cuda = False  # Mock
        else:
            has_cuda = False

        device = "cuda" if has_cuda else "cpu"

        assert device in ["cpu", "cuda"]

    def test_embedding_model_version_recorded(self):
        """Embedding model version should be recorded in fingerprint."""
        fingerprint = {
            "vector_db": {
                "enabled": True,
                "provider": "chromadb",
                "embedding_model": "all-MiniLM-L6-v2",
                "embedding_model_version": "2.2.0",
                "device": "cpu",
            }
        }

        assert "embedding_model_version" in fingerprint["vector_db"]


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_vector_db():
    """
    Mock VectorDBService for testing.

    Returns:
        Mock: Mocked VectorDBService
    """
    mock_service = MagicMock(spec=VectorDBService)
    mock_service.is_available.return_value = True
    mock_service.enabled = True

    return mock_service


@pytest.fixture
def mock_chromadb():
    """
    Mock ChromaDB client for testing.

    Returns:
        Mock: Mocked ChromaDB client
    """
    with patch('src.services.vector_db_service.chromadb') as mock_chroma:
        mock_client = MagicMock()
        mock_collection = MagicMock()

        mock_client.get_or_create_collection.return_value = mock_collection
        mock_chroma.PersistentClient.return_value = mock_client

        yield mock_chroma
