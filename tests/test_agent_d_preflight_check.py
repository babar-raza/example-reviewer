"""
Unit tests for Agent D: Pre-flight check (check_test_data_availability)

Tests the 3-tier path resolution strategy:
- Tier 1: Exact filename match
- Tier 2: Alias lookup
- Tier 3: Basename match (case-insensitive)
"""

import sys
from pathlib import Path
import tempfile
import shutil
from unittest.mock import Mock

# Add parent to path for src imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.runtime_service import RuntimeService
from src.core.config import RuntimeValidationConfig


class TestAgentDPreFlightCheck:
    """Test suite for check_test_data_availability() method."""

    def setup_method(self):
        """Set up test fixtures before each test."""
        # Create mock database (not used by check_test_data_availability)
        mock_db = Mock()
        self.runtime_service = RuntimeService(db=mock_db)
        self.temp_dir = Path(tempfile.mkdtemp())

    def teardown_method(self):
        """Clean up temporary files after each test."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_check_availability_all_exist_tier1(self):
        """Test: All required files present (Tier 1: Exact match)."""
        # Create test data files
        (self.temp_dir / "sample.zip").write_text("test")
        (self.temp_dir / "archive.zip").write_text("test")

        # Configure required files
        runtime_config = RuntimeValidationConfig(
            required_files=["sample.zip", "archive.zip"],
            file_aliases={}
        )

        # Execute
        all_available, missing = self.runtime_service.check_test_data_availability(
            test_data_path=self.temp_dir,
            runtime_config=runtime_config
        )

        # Verify
        assert all_available is True
        assert missing == []

    def test_check_availability_none_exist(self):
        """Test: Test data path doesn't exist → all files missing."""
        non_existent_path = Path("/nonexistent/path")

        runtime_config = RuntimeValidationConfig(
            required_files=["sample.zip", "archive.zip"],
            file_aliases={}
        )

        # Execute
        all_available, missing = self.runtime_service.check_test_data_availability(
            test_data_path=non_existent_path,
            runtime_config=runtime_config
        )

        # Verify
        assert all_available is False
        assert set(missing) == {"sample.zip", "archive.zip"}

    def test_check_availability_some_missing(self):
        """Test: Some files missing → returns missing list."""
        # Create only one of two required files
        (self.temp_dir / "sample.zip").write_text("test")
        # archive.zip is missing

        runtime_config = RuntimeValidationConfig(
            required_files=["sample.zip", "archive.zip"],
            file_aliases={}
        )

        # Execute
        all_available, missing = self.runtime_service.check_test_data_availability(
            test_data_path=self.temp_dir,
            runtime_config=runtime_config
        )

        # Verify
        assert all_available is False
        assert missing == ["archive.zip"]

    def test_check_availability_tier2_alias(self):
        """Test: Tier 2 - Alias match works."""
        # Create file with alias name
        (self.temp_dir / "input.zip").write_text("test")
        # sample.zip doesn't exist, but input.zip is an alias

        runtime_config = RuntimeValidationConfig(
            required_files=["sample.zip"],
            file_aliases={"sample.zip": ["input.zip", "example.zip"]}
        )

        # Execute
        all_available, missing = self.runtime_service.check_test_data_availability(
            test_data_path=self.temp_dir,
            runtime_config=runtime_config
        )

        # Verify - alias should be found
        assert all_available is True
        assert missing == []

    def test_check_availability_tier3_basename_match(self):
        """Test: Tier 3 - Basename match (case-insensitive) works."""
        # Create file with different case but same basename
        (self.temp_dir / "SAMPLE.zip").write_text("test")
        # sample.zip doesn't exist, but SAMPLE.zip should match (case-insensitive)

        runtime_config = RuntimeValidationConfig(
            required_files=["sample.zip"],
            file_aliases={}
        )

        # Execute
        all_available, missing = self.runtime_service.check_test_data_availability(
            test_data_path=self.temp_dir,
            runtime_config=runtime_config
        )

        # Verify - basename match should work
        assert all_available is True
        assert missing == []

    def test_check_availability_tier3_different_extension_fails(self):
        """Test: Tier 3 - Different extension doesn't match."""
        # Create file with same basename but different extension
        (self.temp_dir / "sample.txt").write_text("test")
        # sample.zip doesn't exist, sample.txt has different extension

        runtime_config = RuntimeValidationConfig(
            required_files=["sample.zip"],
            file_aliases={}
        )

        # Execute
        all_available, missing = self.runtime_service.check_test_data_availability(
            test_data_path=self.temp_dir,
            runtime_config=runtime_config
        )

        # Verify - different extension should not match
        assert all_available is False
        assert missing == ["sample.zip"]

    def test_check_availability_empty_required_files(self):
        """Test: Empty required_files list → all available."""
        runtime_config = RuntimeValidationConfig(
            required_files=[],
            file_aliases={}
        )

        # Execute
        all_available, missing = self.runtime_service.check_test_data_availability(
            test_data_path=self.temp_dir,
            runtime_config=runtime_config
        )

        # Verify
        assert all_available is True
        assert missing == []


if __name__ == "__main__":
    # Run tests manually
    import pytest
    pytest.main([__file__, "-v"])
