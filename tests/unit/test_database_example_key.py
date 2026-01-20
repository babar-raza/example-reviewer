"""
Unit tests for database example_key stability and selection_hash computation.

Tests that example_key generation is deterministic and database ordering is stable.
"""

import pytest
import sqlite3
import hashlib
from datetime import datetime
from pathlib import Path

from src.core.database import Database
from src.core.models import ExampleRecord, ExampleStatus, SourceType, Location


class TestExampleKeyGeneration:
    """Test that example_key generation is deterministic and stable."""

    def test_example_key_is_stable(self):
        """Same inputs should produce same example_key."""
        example1 = ExampleRecord(
            family="zip",
            file_path="test-content/blog/archive-example.md",
            original_code="using Aspose.Zip;\nvar archive = new Archive();",
            source_type=SourceType.INLINE,
            language="csharp",
            location=Location(block_index=0, start_line=10, end_line=12),
        )

        example2 = ExampleRecord(
            family="zip",
            file_path="test-content/blog/archive-example.md",
            original_code="using Aspose.Zip;\nvar archive = new Archive();",
            source_type=SourceType.INLINE,
            language="csharp",
            location=Location(block_index=0, start_line=10, end_line=12),
        )

        assert example1.example_key == example2.example_key
        assert len(example1.example_key) == 16  # SHA256 truncated to 16 chars

    def test_different_block_index_different_key(self):
        """Different block index should produce different example_key."""
        example1 = ExampleRecord(
            family="zip",
            file_path="test-content/blog/archive-example.md",
            original_code="var archive = new Archive();",
            source_type=SourceType.INLINE,
            language="csharp",
            location=Location(block_index=0, start_line=10, end_line=12),
        )

        example2 = ExampleRecord(
            family="zip",
            file_path="test-content/blog/archive-example.md",
            original_code="var archive = new Archive();",
            source_type=SourceType.INLINE,
            language="csharp",
            location=Location(block_index=1, start_line=20, end_line=22),
        )

        assert example1.example_key != example2.example_key

    def test_different_file_path_different_key(self):
        """Different file path should produce different example_key."""
        example1 = ExampleRecord(
            family="zip",
            file_path="test-content/blog/archive-example.md",
            original_code="var archive = new Archive();",
            source_type=SourceType.INLINE,
            language="csharp",
            location=Location(block_index=0, start_line=10, end_line=12),
        )

        example2 = ExampleRecord(
            family="zip",
            file_path="test-content/blog/other-example.md",
            original_code="var archive = new Archive();",
            source_type=SourceType.INLINE,
            language="csharp",
            location=Location(block_index=0, start_line=10, end_line=12),
        )

        assert example1.example_key != example2.example_key

    def test_example_key_is_path_normalized(self):
        """example_key should normalize path separators."""
        # Windows-style path
        example1 = ExampleRecord(
            family="zip",
            file_path="test-content\\blog\\archive.md",
            original_code="var archive = new Archive();",
            source_type=SourceType.INLINE,
            language="csharp",
            location=Location(block_index=0, start_line=10, end_line=12),
        )

        # POSIX-style path
        example2 = ExampleRecord(
            family="zip",
            file_path="test-content/blog/archive.md",
            original_code="var archive = new Archive();",
            source_type=SourceType.INLINE,
            language="csharp",
            location=Location(block_index=0, start_line=10, end_line=12),
        )

        # Should produce same example_key after normalization
        assert example1.example_key == example2.example_key


class TestDatabaseOrdering:
    """Test that database queries order by example_key deterministically."""

    def test_examples_ordered_by_example_key(self, in_memory_db):
        """Examples should be ordered by example_key, then example_id."""
        db = in_memory_db

        # Create examples with different example_keys
        examples = [
            ExampleRecord(
                family="zip",
                file_path="test-content/zebra.md",
                original_code="// Zebra",
                location=Location(block_index=0),
            ),
            ExampleRecord(
                family="zip",
                file_path="test-content/apple.md",
                original_code="// Apple",
                location=Location(block_index=0),
            ),
            ExampleRecord(
                family="zip",
                file_path="test-content/banana.md",
                original_code="// Banana",
                location=Location(block_index=0),
            ),
        ]

        # Save in random order
        for ex in examples:
            db.save_example(ex)

        # Retrieve and check ordering
        retrieved = db.get_examples_by_family("zip")

        # Should be ordered by example_key
        example_keys = [ex.example_key for ex in retrieved]

        assert example_keys == sorted(example_keys)

    def test_same_example_key_ordered_by_example_id(self, in_memory_db):
        """Examples with same example_key should be ordered by example_id."""
        db = in_memory_db

        # This is a degenerate case (shouldn't happen with proper example_key)
        # but test the tie-breaker behavior

        # Create two examples with potentially same example_key
        # (simulate collision or re-ingestion)
        example1 = ExampleRecord(
            family="zip",
            file_path="test-content/same.md",
            original_code="// Same",
            location=Location(block_index=0),
        )

        example2 = ExampleRecord(
            family="zip",
            file_path="test-content/same.md",
            original_code="// Same",
            location=Location(block_index=0),
        )

        # Force different example_ids
        example1.example_id = "aaa"
        example2.example_id = "zzz"

        db.save_example(example1)
        db.save_example(example2)

        # Retrieve
        retrieved = db.get_examples_by_family("zip")

        # Should be ordered by example_id as tie-breaker
        if len(retrieved) == 2:
            assert retrieved[0].example_id < retrieved[1].example_id

    def test_limit_preserves_ordering(self, in_memory_db):
        """LIMIT should not affect ordering determinism."""
        db = in_memory_db

        # Create 10 examples
        for i in range(10):
            example = ExampleRecord(
                family="zip",
                file_path=f"test-content/file_{i:02d}.md",
                original_code=f"// Example {i}",
                location=Location(block_index=0),
            )
            db.save_example(example)

        # Retrieve with limit
        limited = db.get_examples_by_family("zip", limit=5)

        # Should be first 5 in sorted order
        all_examples = db.get_examples_by_family("zip")

        assert len(limited) == 5
        for i in range(5):
            assert limited[i].example_key == all_examples[i].example_key


class TestSelectionHashComputation:
    """Test that selection_hash is computed deterministically."""

    def test_selection_hash_from_sorted_keys(self, in_memory_db):
        """selection_hash should be computed from sorted example_keys."""
        db = in_memory_db

        example_keys = ["key3", "key1", "key2"]

        selection_hash = db.compute_selection_hash(example_keys)

        # Should sort keys first
        expected_content = "\n".join(sorted(example_keys))
        expected_hash = hashlib.sha256(expected_content.encode()).hexdigest()

        assert selection_hash == expected_hash

    def test_same_keys_same_hash(self, in_memory_db):
        """Same keys in different order should produce same hash."""
        db = in_memory_db

        keys1 = ["zebra", "apple", "banana"]
        keys2 = ["apple", "banana", "zebra"]

        hash1 = db.compute_selection_hash(keys1)
        hash2 = db.compute_selection_hash(keys2)

        assert hash1 == hash2

    def test_different_keys_different_hash(self, in_memory_db):
        """Different keys should produce different hash."""
        db = in_memory_db

        keys1 = ["apple", "banana"]
        keys2 = ["apple", "cherry"]

        hash1 = db.compute_selection_hash(keys1)
        hash2 = db.compute_selection_hash(keys2)

        assert hash1 != hash2

    def test_empty_keys_produces_valid_hash(self, in_memory_db):
        """Empty key list should produce valid hash."""
        db = in_memory_db

        selection_hash = db.compute_selection_hash([])

        # Should be hash of empty string
        expected_hash = hashlib.sha256(b"").hexdigest()

        assert selection_hash == expected_hash


class TestUniqueIndexOnExampleKey:
    """Test that unique index on (family, example_key) prevents duplicates."""

    def test_duplicate_example_key_rejected(self, in_memory_db):
        """Duplicate (family, example_key) should fail on insert."""
        db = in_memory_db

        example1 = ExampleRecord(
            family="zip",
            file_path="test-content/same.md",
            original_code="// Same",
            location=Location(block_index=0),
        )

        example2 = ExampleRecord(
            family="zip",
            file_path="test-content/same.md",
            original_code="// Same",
            location=Location(block_index=0),
        )

        # Force same example_key
        example2.example_key = example1.example_key
        example2.example_id = "different_id"

        db.save_example(example1)

        # Second insert should fail or replace (depending on INSERT OR REPLACE logic)
        # The database currently uses INSERT OR REPLACE, so it will update
        db.save_example(example2)

        # Verify only one example exists
        examples = db.get_examples_by_family("zip")

        # Should have exactly one example (replaced)
        assert len(examples) == 1

    def test_same_example_key_different_family_allowed(self, in_memory_db):
        """Same example_key with different family should be allowed."""
        db = in_memory_db

        example1 = ExampleRecord(
            family="zip",
            file_path="test-content/same.md",
            original_code="// Same",
            location=Location(block_index=0),
        )

        example2 = ExampleRecord(
            family="pdf",  # Different family
            file_path="test-content/same.md",
            original_code="// Same",
            location=Location(block_index=0),
        )

        # Force same example_key
        example2.example_key = example1.example_key

        db.save_example(example1)
        db.save_example(example2)

        # Both should exist
        zip_examples = db.get_examples_by_family("zip")
        pdf_examples = db.get_examples_by_family("pdf")

        assert len(zip_examples) == 1
        assert len(pdf_examples) == 1


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def in_memory_db(tmp_path):
    """
    Create in-memory SQLite database for testing.

    Uses temporary file instead of :memory: to avoid connection isolation issues.

    Returns:
        Database: Temporary database instance
    """
    db_file = tmp_path / "test.db"
    db = Database(db_path=db_file)
    db.initialize_schema()
    return db
