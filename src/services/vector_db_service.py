"""
Vector Database Service for Example Reviewer Pipeline.
Stores and retrieves verified examples using embeddings for similarity search.
"""

import logging
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

logger = logging.getLogger(__name__)

# Try to import ChromaDB and sentence-transformers
# Graceful degradation if not installed
try:
    import chromadb
    from chromadb.config import Settings
    from sentence_transformers import SentenceTransformer
    VECTOR_DB_AVAILABLE = True
except ImportError:
    VECTOR_DB_AVAILABLE = False
    logger.warning(
        "ChromaDB or sentence-transformers not installed. "
        "Vector DB features disabled. "
        "Install with: pip install chromadb>=0.4.20 sentence-transformers>=2.2.0"
    )


class VectorDBService:
    """
    Service for storing and retrieving code examples using vector embeddings.

    Uses ChromaDB for storage and sentence-transformers for embeddings.
    Gracefully degrades if dependencies are not available.

    Features:
    - Store verified examples with metadata
    - Search for similar examples using semantic similarity
    - Support for multiple product families
    - Persistent storage
    """

    DEFAULT_EMBEDDING_MODEL = "all-MiniLM-L6-v2"
    DEFAULT_COLLECTION_NAME = "verified_examples"

    def __init__(
        self,
        persist_directory: Optional[str] = None,
        embedding_model: Optional[str] = None,
        enabled: bool = True,
    ):
        """
        Initialize Vector DB service.

        Args:
            persist_directory: Directory to persist ChromaDB data
            embedding_model: Sentence-transformers model name
            enabled: Enable/disable vector DB features (config flag)
        """
        self.persist_directory = persist_directory or "./data/chroma"
        self.embedding_model_name = embedding_model or self.DEFAULT_EMBEDDING_MODEL
        self.enabled = enabled and VECTOR_DB_AVAILABLE

        self._client = None
        self._collection = None
        self._embedding_model = None

        if not VECTOR_DB_AVAILABLE:
            logger.info("Vector DB service initialized but unavailable (missing dependencies)")
            return

        if not self.enabled:
            logger.info("Vector DB service initialized but disabled by configuration")
            return

        # Initialize ChromaDB client
        try:
            self._initialize_client()
            logger.info(f"Vector DB service initialized with model: {self.embedding_model_name}")
        except Exception as e:
            logger.error(f"Failed to initialize Vector DB: {e}")
            self.enabled = False

    def _initialize_client(self):
        """Initialize ChromaDB client and collection."""
        if not VECTOR_DB_AVAILABLE:
            return

        # Create persist directory
        Path(self.persist_directory).mkdir(parents=True, exist_ok=True)

        # Initialize ChromaDB persistent client (for data persistence)
        self._client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
            )
        )

        # Get or create collection
        self._collection = self._client.get_or_create_collection(
            name=self.DEFAULT_COLLECTION_NAME,
            metadata={"description": "Verified code examples for similarity search"}
        )

        # Initialize embedding model
        self._embedding_model = SentenceTransformer(self.embedding_model_name)

        logger.info(
            f"ChromaDB initialized: {self._collection.count()} examples in collection"
        )

    def is_available(self) -> bool:
        """
        Check if vector DB is available and ready.

        Returns:
            True if vector DB can be used, False otherwise
        """
        return self.enabled and self._client is not None

    def add_example(
        self,
        example_id: str,
        code: str,
        metadata: Optional[Dict[str, Any]] = None,
        drift_score: Optional[float] = None,
    ) -> bool:
        """
        Add a code example to the vector database with drift filtering.

        NEW (ID-05): Only stores examples with drift_score < threshold.
        High-drift examples are rejected to prevent drift contagion.

        Args:
            example_id: Unique identifier for the example
            code: Code content to embed and store
            metadata: Optional metadata (family, source, verified, etc.)
            drift_score: Optional drift score (0.0=identical, 1.0=completely different)

        Returns:
            True if added successfully, False otherwise
        """
        if not self.is_available():
            logger.debug("Vector DB not available, skipping add_example")
            return False

        try:
            # Check drift threshold (ID-05: Selective storage)
            if metadata is None:
                metadata = {}

            drift_threshold = metadata.get('drift_threshold', 0.3)

            if drift_score is not None and drift_score >= drift_threshold:
                logger.info(
                    f"Skipping vector DB storage for {example_id}: "
                    f"drift_score={drift_score:.3f} >= threshold {drift_threshold}"
                )
                return False

            # Add drift metadata (ID-05: Observability)
            if drift_score is not None:
                metadata['drift_score'] = drift_score

            # Determine collection (ID-05: Separate collections)
            source = metadata.get('source', '')
            if 'llm_fixed' in source:
                collection_name = "fixed_examples"
            else:
                collection_name = "original_examples"

            # Get or create collection
            collection = self._get_collection(collection_name)

            # Generate embedding
            embedding = self._embedding_model.encode(code).tolist()

            # Add to collection
            collection.add(
                ids=[example_id],
                embeddings=[embedding],
                documents=[code],
                metadatas=[metadata]
            )

            logger.debug(f"Added example {example_id} to {collection_name} (drift_score={drift_score})")
            return True

        except Exception as e:
            logger.error(f"Failed to add example {example_id}: {e}")
            return False

    def search_similar(
        self,
        query_code: str,
        family: Optional[str] = None,
        k: int = 3,
        min_similarity: float = 0.0,
        exclude_high_drift: bool = True,
    ) -> List[Tuple[str, str, float, Dict[str, Any]]]:
        """
        Search for similar code examples with drift filtering.

        NEW (ID-05): Can exclude high-drift examples from results
        to prevent drift contagion in fixes.

        Args:
            query_code: Code to search for
            family: Optional family filter
            k: Number of results to return
            min_similarity: Minimum similarity threshold (0.0 to 1.0)
            exclude_high_drift: Exclude examples with drift_score >= 0.3 (default True)

        Returns:
            List of tuples: (example_id, code, similarity_score, metadata)
            Returns empty list if vector DB unavailable
        """
        if not self.is_available():
            logger.debug("Vector DB not available, returning empty results")
            return []

        try:
            # Generate query embedding
            query_embedding = self._embedding_model.encode(query_code).tolist()

            # Build where filter
            where_filter = None
            if family:
                where_filter = {"family": family}

            # Search both collections (ID-05: Multiple collections)
            all_results = []

            for collection_name in ["original_examples", "fixed_examples"]:
                try:
                    collection = self._get_collection(collection_name)

                    # Query collection (get extra results for filtering)
                    results = collection.query(
                        query_embeddings=[query_embedding],
                        n_results=k * 3,  # Get extra to allow for drift filtering
                        where=where_filter,
                    )

                    # Extract and format results
                    if results['ids'] and len(results['ids'][0]) > 0:
                        for i in range(len(results['ids'][0])):
                            example_id = results['ids'][0][i]
                            code = results['documents'][0][i]
                            # ChromaDB returns distance, convert to similarity (1 - distance)
                            similarity = 1.0 - results['distances'][0][i]
                            metadata = results['metadatas'][0][i]

                            # Filter by minimum similarity
                            if similarity < min_similarity:
                                continue

                            # Filter by drift (ID-05: Drift filtering)
                            if exclude_high_drift and 'drift_score' in metadata:
                                drift_score = metadata['drift_score']
                                if drift_score >= 0.3:
                                    logger.debug(f"Excluding {example_id} from search: drift_score={drift_score:.3f}")
                                    continue

                            all_results.append((example_id, code, similarity, metadata))

                except Exception as e:
                    # Collection might not exist yet, continue with other collection
                    logger.debug(f"Could not search {collection_name}: {e}")
                    continue

            # Sort by similarity (descending) and take top k
            all_results.sort(key=lambda x: x[2], reverse=True)
            final_results = all_results[:k]

            logger.debug(
                f"Found {len(final_results)} similar examples "
                f"(k={k}, min_similarity={min_similarity}, family={family}, exclude_high_drift={exclude_high_drift})"
            )
            return final_results

        except Exception as e:
            logger.error(f"Failed to search similar examples: {e}")
            return []

    def get_example(self, example_id: str) -> Optional[Tuple[str, Dict[str, Any]]]:
        """
        Retrieve a specific example by ID.

        UPDATED (ID-05): Search both original and fixed collections.

        Args:
            example_id: Example identifier

        Returns:
            Tuple of (code, metadata) if found, None otherwise
        """
        if not self.is_available():
            return None

        try:
            # Search both collections (ID-05: Multiple collections)
            for collection_name in ["original_examples", "fixed_examples"]:
                try:
                    collection = self._get_collection(collection_name)
                    result = collection.get(ids=[example_id])

                    if result['ids']:
                        code = result['documents'][0]
                        metadata = result['metadatas'][0]
                        return (code, metadata)
                except Exception as e:
                    # Collection might not exist yet, continue with other collection
                    logger.debug(f"Could not get from {collection_name}: {e}")
                    continue

            return None

        except Exception as e:
            logger.error(f"Failed to get example {example_id}: {e}")
            return None

    def delete_example(self, example_id: str) -> bool:
        """
        Delete an example from the vector database.

        Args:
            example_id: Example identifier

        Returns:
            True if deleted successfully, False otherwise
        """
        if not self.is_available():
            return False

        try:
            self._collection.delete(ids=[example_id])
            logger.debug(f"Deleted example {example_id} from vector DB")
            return True

        except Exception as e:
            logger.error(f"Failed to delete example {example_id}: {e}")
            return False

    def count(self, family: Optional[str] = None) -> int:
        """
        Get count of examples in the database.

        Args:
            family: Optional family filter

        Returns:
            Number of examples (0 if unavailable)
        """
        if not self.is_available():
            return 0

        try:
            if family:
                # Count with filter
                results = self._collection.get(where={"family": family})
                return len(results['ids'])
            else:
                # Total count
                return self._collection.count()

        except Exception as e:
            logger.error(f"Failed to count examples: {e}")
            return 0

    def clear_family(self, family: str) -> bool:
        """
        Clear all examples for a specific family.

        Args:
            family: Product family identifier

        Returns:
            True if cleared successfully, False otherwise
        """
        if not self.is_available():
            return False

        try:
            # Get all IDs for family
            results = self._collection.get(where={"family": family})

            if results['ids']:
                # Delete all matching IDs
                self._collection.delete(ids=results['ids'])
                logger.info(f"Cleared {len(results['ids'])} examples for family {family}")
                return True

            return True  # No examples to clear

        except Exception as e:
            logger.error(f"Failed to clear family {family}: {e}")
            return False

    def _get_collection(self, collection_name: str):
        """
        Get or create a collection by name.

        NEW (ID-05): Helper for managing multiple collections.

        Args:
            collection_name: Name of the collection

        Returns:
            ChromaDB collection object
        """
        if not self.is_available():
            return None

        try:
            return self._client.get_or_create_collection(
                name=collection_name,
                metadata={"description": f"Code examples - {collection_name}"}
            )
        except Exception as e:
            logger.error(f"Failed to get/create collection {collection_name}: {e}")
            raise

    def clean_high_drift(
        self,
        family: str,
        max_drift: float = 0.3,
    ) -> int:
        """
        Remove high-drift examples from vector DB.

        NEW (ID-05): Cleanup command to remove drifted examples
        that may cause contagion.

        Args:
            family: Family to clean
            max_drift: Maximum drift score to keep (default 0.3)

        Returns:
            Number of examples removed
        """
        if not self.is_available():
            logger.debug("Vector DB not available, skipping clean_high_drift")
            return 0

        removed_count = 0

        try:
            for collection_name in ["original_examples", "fixed_examples"]:
                try:
                    collection = self._get_collection(collection_name)

                    # Query all examples for family
                    all_results = collection.get(where={"family": family})

                    if not all_results['ids']:
                        logger.debug(f"No examples found in {collection_name} for family {family}")
                        continue

                    # Find high-drift examples
                    ids_to_remove = []
                    for i, metadata in enumerate(all_results['metadatas']):
                        if 'drift_score' in metadata:
                            drift_score = metadata['drift_score']
                            if drift_score >= max_drift:
                                ids_to_remove.append(all_results['ids'][i])

                    # Remove high-drift examples
                    if ids_to_remove:
                        collection.delete(ids=ids_to_remove)
                        removed_count += len(ids_to_remove)
                        logger.info(
                            f"Removed {len(ids_to_remove)} high-drift examples "
                            f"from {collection_name} (family: {family}, max_drift: {max_drift})"
                        )

                except Exception as e:
                    # Collection might not exist yet, continue with other collection
                    logger.debug(f"Could not clean {collection_name}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Failed to clean high-drift examples: {e}")
            return removed_count

        logger.info(f"Total removed: {removed_count} high-drift examples for family {family}")
        return removed_count

    def close(self):
        """Close the vector DB connection and persist data."""
        if self._client and VECTOR_DB_AVAILABLE:
            try:
                # ChromaDB auto-persists, but we can explicitly trigger it
                logger.info("Vector DB closed")
            except Exception as e:
                logger.error(f"Error closing Vector DB: {e}")
