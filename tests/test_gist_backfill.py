"""
Tests for gist source code backfill functionality in BackfillService.
"""

import pytest
from unittest.mock import patch, MagicMock
from dataclasses import dataclass
from typing import Optional

from src.services.backfill_service import BackfillService, BackfillResult
from src.core.models import ExampleRecord, SourceType, ExampleStatus, GistInfo, CodeLocation


class TestGistBackfill:
    """Tests for backfill_gist_source_code functionality."""

    def _create_mock_example(
        self,
        example_id: str,
        source_type: SourceType = SourceType.GIST,
        original_code: Optional[str] = None,
        gist_owner: str = "test-owner",
        gist_id: str = "test-gist-id",
        gist_filename: str = "test.cs",
    ) -> ExampleRecord:
        """Create a mock ExampleRecord for testing."""
        gist = None
        if source_type == SourceType.GIST:
            gist = GistInfo(
                owner=gist_owner,
                gist_id=gist_id,
                filename=gist_filename,
            )

        return ExampleRecord(
            example_id=example_id,
            family="test",
            file_path="/test/file.md",
            source_type=source_type,
            status=ExampleStatus.DISCOVERED,
            original_code=original_code,
            location=CodeLocation(start_line=1, end_line=10),
            gist=gist,
        )

    @patch('src.services.backfill_service.GistResolver')
    def test_backfill_gist_source_code_success(self, mock_resolver_class):
        """Test successful gist source code backfill."""
        # Setup mock database
        mock_db = MagicMock()
        mock_example = self._create_mock_example(
            example_id="ex1",
            original_code=None,  # No code yet
        )
        mock_db.get_examples_by_family.return_value = [mock_example]

        # Setup mock config
        mock_config = MagicMock()
        mock_config.gist.pat_env_var = "GIST_PAT"
        mock_config.backfill.targets = ["gist_source_code"]

        # Setup mock resolver
        mock_resolver = MagicMock()
        mock_resolver.resolve_gist.return_value = "// Fetched code from gist"
        mock_resolver_class.return_value = mock_resolver

        # Create service and run backfill
        service = BackfillService(db=mock_db, config=mock_config)

        with patch.dict('os.environ', {'GIST_PAT': 'test-token'}):
            result = service.backfill_gist_source_code(family="test")

        # Verify result
        assert result.success is True
        assert result.items_processed == 1
        assert result.items_downloaded == 1

        # Verify database update was called
        mock_db.update_example_original_code.assert_called_once_with(
            "ex1", "// Fetched code from gist"
        )

    @patch('src.services.backfill_service.GistResolver')
    def test_backfill_skips_examples_with_code(self, mock_resolver_class):
        """Test that examples with existing code are skipped."""
        mock_db = MagicMock()
        mock_example = self._create_mock_example(
            example_id="ex1",
            original_code="// Already has code",  # Has code
        )
        mock_db.get_examples_by_family.return_value = [mock_example]

        mock_config = MagicMock()
        mock_config.gist.pat_env_var = "GIST_PAT"
        mock_config.backfill.targets = ["gist_source_code"]

        service = BackfillService(db=mock_db, config=mock_config)

        with patch.dict('os.environ', {'GIST_PAT': 'test-token'}):
            result = service.backfill_gist_source_code(family="test")

        # No items should be processed (already have code)
        assert result.items_processed == 0
        mock_db.update_example_original_code.assert_not_called()

    @patch('src.services.backfill_service.GistResolver')
    def test_backfill_force_refresh(self, mock_resolver_class):
        """Test force refresh re-fetches all gist code."""
        mock_db = MagicMock()
        mock_example = self._create_mock_example(
            example_id="ex1",
            original_code="// Old code",  # Has code
        )
        mock_db.get_examples_by_family.return_value = [mock_example]

        mock_config = MagicMock()
        mock_config.gist.pat_env_var = "GIST_PAT"
        mock_config.backfill.targets = ["gist_source_code"]

        mock_resolver = MagicMock()
        mock_resolver.resolve_gist.return_value = "// New code from gist"
        mock_resolver_class.return_value = mock_resolver

        service = BackfillService(db=mock_db, config=mock_config)

        with patch.dict('os.environ', {'GIST_PAT': 'test-token'}):
            result = service.backfill_gist_source_code(family="test", force=True)

        # Should process even though code exists
        assert result.items_processed == 1
        assert result.items_downloaded == 1
        mock_db.update_example_original_code.assert_called_once()

    @patch('src.services.backfill_service.GistResolver')
    def test_backfill_skips_inline_examples(self, mock_resolver_class):
        """Test that inline examples are skipped."""
        mock_db = MagicMock()
        mock_example = self._create_mock_example(
            example_id="ex1",
            source_type=SourceType.INLINE,  # Inline, not gist
            original_code=None,
        )
        mock_db.get_examples_by_family.return_value = [mock_example]

        mock_config = MagicMock()
        mock_config.gist.pat_env_var = "GIST_PAT"

        service = BackfillService(db=mock_db, config=mock_config)

        with patch.dict('os.environ', {'GIST_PAT': 'test-token'}):
            result = service.backfill_gist_source_code(family="test")

        # Should skip inline examples
        assert result.items_processed == 0
        mock_resolver_class.assert_not_called()

    @patch('src.services.backfill_service.GistResolver')
    def test_backfill_handles_resolver_failure(self, mock_resolver_class):
        """Test graceful handling of resolver failures."""
        mock_db = MagicMock()
        mock_example = self._create_mock_example(
            example_id="ex1",
            original_code=None,
        )
        mock_db.get_examples_by_family.return_value = [mock_example]

        mock_config = MagicMock()
        mock_config.gist.pat_env_var = "GIST_PAT"

        mock_resolver = MagicMock()
        mock_resolver.resolve_gist.return_value = None  # Resolver returns None on failure
        mock_resolver_class.return_value = mock_resolver

        service = BackfillService(db=mock_db, config=mock_config)

        with patch.dict('os.environ', {'GIST_PAT': 'test-token'}):
            result = service.backfill_gist_source_code(family="test")

        # Should handle gracefully
        assert result.success is True
        assert result.items_processed == 1
        assert result.items_downloaded == 0
        assert result.items_failed == 1
        mock_db.update_example_original_code.assert_not_called()

    @patch('src.services.backfill_service.GistResolver')
    def test_backfill_handles_missing_gist_info(self, mock_resolver_class):
        """Test handling of examples with missing gist info."""
        mock_db = MagicMock()
        # Create example with GIST type but no gist info
        mock_example = ExampleRecord(
            example_id="ex1",
            family="test",
            file_path="/test/file.md",
            source_type=SourceType.GIST,
            status=ExampleStatus.DISCOVERED,
            original_code=None,
            location=CodeLocation(start_line=1, end_line=10),
            gist=None,  # Missing gist info
        )
        mock_db.get_examples_by_family.return_value = [mock_example]

        mock_config = MagicMock()
        mock_config.gist.pat_env_var = "GIST_PAT"

        service = BackfillService(db=mock_db, config=mock_config)

        with patch.dict('os.environ', {'GIST_PAT': 'test-token'}):
            result = service.backfill_gist_source_code(family="test")

        # Should skip examples without gist info
        assert result.items_processed == 0

    @patch('src.services.backfill_service.GistResolver')
    def test_backfill_multiple_examples(self, mock_resolver_class):
        """Test backfilling multiple gist examples."""
        mock_db = MagicMock()
        examples = [
            self._create_mock_example(
                example_id=f"ex{i}",
                original_code=None,
                gist_id=f"gist-{i}",
            )
            for i in range(3)
        ]
        mock_db.get_examples_by_family.return_value = examples

        mock_config = MagicMock()
        mock_config.gist.pat_env_var = "GIST_PAT"

        mock_resolver = MagicMock()
        mock_resolver.resolve_gist.return_value = "// Fetched code"
        mock_resolver_class.return_value = mock_resolver

        service = BackfillService(db=mock_db, config=mock_config)

        with patch.dict('os.environ', {'GIST_PAT': 'test-token'}):
            result = service.backfill_gist_source_code(family="test")

        assert result.items_processed == 3
        assert result.items_downloaded == 3
        assert mock_db.update_example_original_code.call_count == 3


class TestBackfillServiceGistIntegration:
    """Integration tests for gist backfill in BackfillService."""

    def test_backfill_targets_include_gist_source_code(self):
        """Test that gist_source_code is a valid backfill target."""
        mock_db = MagicMock()
        mock_config = MagicMock()
        mock_config.backfill.targets = ["test_data", "gist_source_code", "examples"]

        service = BackfillService(db=mock_db, config=mock_config)

        # Verify targets are accessible
        assert "gist_source_code" in mock_config.backfill.targets

    @patch('src.services.backfill_service.GistResolver')
    def test_dry_run_mode(self, mock_resolver_class):
        """Test dry run doesn't actually update database."""
        mock_db = MagicMock()
        mock_example = ExampleRecord(
            example_id="ex1",
            family="test",
            file_path="/test/file.md",
            source_type=SourceType.GIST,
            status=ExampleStatus.DISCOVERED,
            original_code=None,
            location=CodeLocation(start_line=1, end_line=10),
            gist=GistInfo(owner="owner", gist_id="gid", filename="file.cs"),
        )
        mock_db.get_examples_by_family.return_value = [mock_example]

        mock_config = MagicMock()
        mock_config.gist.pat_env_var = "GIST_PAT"

        mock_resolver = MagicMock()
        mock_resolver.resolve_gist.return_value = "// Code"
        mock_resolver_class.return_value = mock_resolver

        service = BackfillService(db=mock_db, config=mock_config)

        with patch.dict('os.environ', {'GIST_PAT': 'test-token'}):
            result = service.backfill_gist_source_code(family="test", dry_run=True)

        # Should report what would be done but not update
        assert result.success is True
        assert result.items_processed == 1
        mock_db.update_example_original_code.assert_not_called()
