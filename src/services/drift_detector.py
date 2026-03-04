"""
Drift Detection Service for Example Reviewer Pipeline.

Detects semantic drift between original and fixed code to prevent
runaway LLM changes that alter code intent.
"""

import logging
import numpy as np
from typing import Tuple

logger = logging.getLogger(__name__)


class DriftDetector:
    """
    Detects semantic drift between original and fixed code using embeddings.

    Uses sentence-transformers to embed code and compute cosine similarity.
    Drift score = 1.0 - similarity, where:
    - 0.0 = identical code
    - 1.0 = completely different code

    The detector reuses an existing SentenceTransformer model instance
    to avoid expensive model initialization overhead (~2 seconds).
    """

    def __init__(self, model):
        """
        Initialize drift detector with an existing embedding model.

        Args:
            model: Pre-instantiated SentenceTransformer from VectorDBService
                  (reused to avoid instantiation cost)
        """
        if model is None:
            raise ValueError("Drift detector requires a valid SentenceTransformer model")

        self.model = model
        logger.debug("DriftDetector initialized with reused embedding model")

    def compute_drift(
        self,
        original_code: str,
        fixed_code: str
    ) -> Tuple[float, float]:
        """
        Compute drift score between original and fixed code.

        Embeds both code snippets using the sentence-transformer model,
        computes cosine similarity, and derives drift score.

        Args:
            original_code: Original code before LLM fixes
            fixed_code: Code after LLM fix attempt

        Returns:
            Tuple of (drift_score, similarity):
            - drift_score: 0.0 (identical) to 1.0 (completely different)
            - similarity: 1.0 (identical) to 0.0 (completely different)

        Example:
            >>> detector = DriftDetector(model)
            >>> drift, sim = detector.compute_drift(orig, fixed)
            >>> if drift > 0.3:
            ...     print("Excessive drift detected")
        """
        if not original_code or not fixed_code:
            logger.warning("Empty code provided to compute_drift, returning 1.0 drift")
            return 1.0, 0.0

        try:
            # Embed both code snippets
            original_embedding = self.model.encode(original_code)
            fixed_embedding = self.model.encode(fixed_code)

            # Compute cosine similarity
            # similarity = (A · B) / (||A|| * ||B||)
            dot_product = np.dot(original_embedding, fixed_embedding)
            norm_original = np.linalg.norm(original_embedding)
            norm_fixed = np.linalg.norm(fixed_embedding)

            # Avoid division by zero
            if norm_original == 0 or norm_fixed == 0:
                logger.warning("Zero-norm embedding detected, returning 1.0 drift")
                return 1.0, 0.0

            similarity = dot_product / (norm_original * norm_fixed)

            # Clamp similarity to [0.0, 1.0] (cosine can be negative for opposite vectors)
            similarity = float(np.clip(similarity, 0.0, 1.0))

            # Drift = 1 - similarity
            drift_score = 1.0 - similarity

            logger.debug(
                f"Drift computed: drift={drift_score:.3f}, similarity={similarity:.3f}"
            )

            return drift_score, similarity

        except Exception as e:
            logger.error(f"Error computing drift: {e}", exc_info=True)
            # Return high drift on error (fail-safe: prefer human review)
            return 1.0, 0.0

