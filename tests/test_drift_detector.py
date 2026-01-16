"""
Test suite for DriftDetector service.

Validates drift score computation and threshold enforcement.
"""

import pytest
import time
from unittest.mock import Mock, MagicMock
import numpy as np

# Import the DriftDetector
from src.services.drift_detector import DriftDetector


# Sample code snippets for testing
SAMPLE_CODE_1 = """
using Aspose.Zip;
using System.IO;

var archive = new Archive();
archive.CreateEntry("file.txt", "path/to/file.txt");
archive.Save("output.zip");
"""

SAMPLE_CODE_2_MINOR_CHANGE = """
using Aspose.Zip;
using System.IO;

using (var archive = new Archive())
{
    archive.CreateEntry("file.txt", "path/to/file.txt");
    archive.Save("output.zip");
}
"""

SAMPLE_CODE_3_MODERATE_CHANGE = """
using Aspose.Zip;
using System;
using System.IO;

try
{
    var archive = new Archive();
    archive.CreateEntry("document.txt", "path/to/document.txt");
    archive.Save("result.zip");
}
catch (Exception ex)
{
    Console.WriteLine(ex.Message);
}
"""

SAMPLE_CODE_4_COMPLETELY_DIFFERENT = """
using System.Net.Http;
using System.Threading.Tasks;

var client = new HttpClient();
var response = await client.GetAsync("https://api.example.com/data");
var content = await response.Content.ReadAsStringAsync();
Console.WriteLine(content);
"""


@pytest.fixture
def mock_embedding_model():
    """Create a mock SentenceTransformer model."""
    model = Mock()

    # Mock encode method to return different embeddings based on input
    def encode_mock(text):
        # Generate deterministic embeddings based on text hash
        hash_val = hash(text) % 10000
        # Return a 384-dimensional embedding (typical for all-MiniLM-L6-v2)
        np.random.seed(hash_val)
        embedding = np.random.randn(384).astype(np.float32)
        # Normalize
        return embedding / np.linalg.norm(embedding)

    model.encode = Mock(side_effect=encode_mock)
    return model


@pytest.fixture
def drift_detector(mock_embedding_model):
    """Create a DriftDetector instance with mock model."""
    return DriftDetector(mock_embedding_model)


def test_drift_detector_initialization(mock_embedding_model):
    """Test drift detector initialization."""
    detector = DriftDetector(mock_embedding_model)
    assert detector.model is not None
    assert detector.model == mock_embedding_model


def test_drift_detector_initialization_no_model():
    """Test drift detector fails with no model."""
    with pytest.raises(ValueError, match="requires a valid SentenceTransformer model"):
        DriftDetector(None)


def test_drift_detector_identical_code(drift_detector):
    """Test drift score is ~0.0 for identical code."""
    code = SAMPLE_CODE_1
    drift_score, similarity = drift_detector.compute_drift(code, code)

    # Identical code should have near-zero drift
    assert drift_score < 0.01, f"Expected drift < 0.01, got {drift_score:.3f}"
    assert similarity > 0.99, f"Expected similarity > 0.99, got {similarity:.3f}"


def test_drift_detector_completely_different(drift_detector):
    """Test drift score is high for unrelated code."""
    original = SAMPLE_CODE_1
    different = SAMPLE_CODE_4_COMPLETELY_DIFFERENT

    drift_score, similarity = drift_detector.compute_drift(original, different)

    # Completely different code should have significant drift
    assert drift_score > 0.3, f"Expected drift > 0.3, got {drift_score:.3f}"
    assert similarity < 0.7, f"Expected similarity < 0.7, got {similarity:.3f}"


def test_drift_detector_minor_changes(drift_detector):
    """Test drift score is computed for minor syntax changes."""
    original = SAMPLE_CODE_1
    minor_change = SAMPLE_CODE_2_MINOR_CHANGE

    drift_score, similarity = drift_detector.compute_drift(original, minor_change)

    # With mock embeddings, we can't guarantee exact thresholds
    # But we can verify drift is computed and in valid range
    assert 0.0 <= drift_score <= 1.0, f"Drift score {drift_score:.3f} out of range"
    assert 0.0 <= similarity <= 1.0, f"Similarity {similarity:.3f} out of range"
    # Drift != 0 (codes are different)
    assert drift_score > 0.0, "Different codes should have non-zero drift"


def test_drift_detector_moderate_changes(drift_detector):
    """Test drift score is computed for restructuring."""
    original = SAMPLE_CODE_1
    moderate = SAMPLE_CODE_3_MODERATE_CHANGE

    drift_score, similarity = drift_detector.compute_drift(original, moderate)

    # With mock embeddings, we can't guarantee exact thresholds
    # But we can verify drift is computed and in valid range
    assert 0.0 <= drift_score <= 1.0, f"Drift score {drift_score:.3f} out of range"
    assert 0.0 <= similarity <= 1.0, f"Similarity {similarity:.3f} out of range"


def test_drift_detector_empty_code(drift_detector):
    """Test drift score handles empty code gracefully."""
    drift_score, similarity = drift_detector.compute_drift("", "some code")
    assert drift_score == 1.0, "Empty code should return max drift"
    assert similarity == 0.0

    drift_score, similarity = drift_detector.compute_drift("some code", "")
    assert drift_score == 1.0, "Empty code should return max drift"
    assert similarity == 0.0


def test_drift_detector_performance(drift_detector):
    """Test drift computation is < 100ms per check."""
    code1 = SAMPLE_CODE_1
    code2 = SAMPLE_CODE_2_MINOR_CHANGE

    # Warmup
    drift_detector.compute_drift(code1, code2)

    # Time 10 iterations
    start = time.time()
    for _ in range(10):
        drift_detector.compute_drift(code1, code2)
    elapsed = time.time() - start

    avg_time_ms = (elapsed / 10) * 1000
    assert avg_time_ms < 100, f"Expected < 100ms, got {avg_time_ms:.2f}ms per check"


def test_is_drift_acceptable(drift_detector):
    """Test drift acceptability checking."""
    threshold = 0.3

    # Low drift (acceptable)
    assert drift_detector.is_drift_acceptable(0.1, threshold)
    assert drift_detector.is_drift_acceptable(0.3, threshold)  # Equal is acceptable

    # High drift (not acceptable)
    assert not drift_detector.is_drift_acceptable(0.5, threshold)
    assert not drift_detector.is_drift_acceptable(1.0, threshold)


def test_drift_score_symmetry(drift_detector):
    """Test that drift(A, B) ~= drift(B, A)."""
    code1 = SAMPLE_CODE_1
    code2 = SAMPLE_CODE_2_MINOR_CHANGE

    drift_ab, sim_ab = drift_detector.compute_drift(code1, code2)
    drift_ba, sim_ba = drift_detector.compute_drift(code2, code1)

    # Cosine similarity is symmetric, so drift should be too
    assert abs(drift_ab - drift_ba) < 0.01, "Drift should be symmetric"
    assert abs(sim_ab - sim_ba) < 0.01, "Similarity should be symmetric"


def test_drift_score_range(drift_detector):
    """Test that drift scores are always in [0, 1]."""
    test_cases = [
        (SAMPLE_CODE_1, SAMPLE_CODE_1),
        (SAMPLE_CODE_1, SAMPLE_CODE_2_MINOR_CHANGE),
        (SAMPLE_CODE_1, SAMPLE_CODE_3_MODERATE_CHANGE),
        (SAMPLE_CODE_1, SAMPLE_CODE_4_COMPLETELY_DIFFERENT),
    ]

    for code1, code2 in test_cases:
        drift_score, similarity = drift_detector.compute_drift(code1, code2)

        assert 0.0 <= drift_score <= 1.0, f"Drift score {drift_score} out of range"
        assert 0.0 <= similarity <= 1.0, f"Similarity {similarity} out of range"
        # Drift = 1 - similarity
        assert abs(drift_score + similarity - 1.0) < 0.01, "Drift + similarity should ~= 1.0"


def test_model_reuse():
    """Test that model is reused and not reinstantiated."""
    # This test verifies the design pattern
    model = Mock()
    model.encode = Mock(return_value=np.ones(384))

    detector1 = DriftDetector(model)
    detector2 = DriftDetector(model)

    # Both detectors should use the same model instance
    assert detector1.model is model
    assert detector2.model is model
    assert detector1.model is detector2.model


def test_drift_cumulative_tracking():
    """Test that drift is computed against original code, not previous iteration."""
    # This is a design validation test
    # In actual usage, orchestrator must pass original_code, not current_code

    model = Mock()
    model.encode = Mock(side_effect=lambda text: np.random.randn(384) / 10)

    detector = DriftDetector(model)

    original = "original code"
    iteration1 = "iteration 1 code"
    iteration2 = "iteration 2 code"

    # Compute drift from original to iteration 1
    drift1, _ = detector.compute_drift(original, iteration1)

    # Compute drift from original to iteration 2 (NOT from iteration1)
    drift2, _ = detector.compute_drift(original, iteration2)

    # Both should be computed against original
    # (actual values will vary, but both calls should use original as base)
    assert model.encode.call_count >= 4  # At least 2 calls per drift computation

    # Verify that 'original' was encoded for both drift computations
    calls = [str(call) for call in model.encode.call_args_list]
    original_calls = sum(1 for call in calls if 'original' in call)
    assert original_calls >= 2, "Original code should be encoded for each drift check"


def test_error_handling_zero_norm(drift_detector):
    """Test handling of zero-norm embeddings."""
    # Mock model to return zero vector
    drift_detector.model.encode = Mock(return_value=np.zeros(384))

    drift_score, similarity = drift_detector.compute_drift("code1", "code2")

    # Should fail-safe to max drift
    assert drift_score == 1.0
    assert similarity == 0.0


def test_error_handling_exception(drift_detector):
    """Test handling of embedding exceptions."""
    # Mock model to raise exception
    drift_detector.model.encode = Mock(side_effect=Exception("Embedding failed"))

    drift_score, similarity = drift_detector.compute_drift("code1", "code2")

    # Should fail-safe to max drift
    assert drift_score == 1.0
    assert similarity == 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
