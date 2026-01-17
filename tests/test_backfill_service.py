"""
Tests for BackfillService.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from src.services.backfill_service import BackfillService, BackfillResult, GIT_AVAILABLE


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    # Cleanup
    if temp_path.exists():
        shutil.rmtree(temp_path)


@pytest.fixture
def mock_config_manager():
    """Create a mock configuration manager."""
    config_mgr = Mock()

    # Mock family config
    family_config = Mock()
    family_config.test_data.local_path = "test-data/zip"
    family_config.test_data.download_if_missing = True
    family_config.example_repo.url = "https://github.com/example/repo.git"
    family_config.example_repo.ref = "main"
    family_config.example_repo.test_data_path = "Data"
    family_config.example_repo.examples_path = "Examples"
    family_config.api_reference.sources = ["test-reference/zip"]
    family_config.api_reference.cache_path = "./cache/api-reference/zip"

    config_mgr.load_family_config.return_value = family_config

    return config_mgr


@pytest.fixture
def backfill_service(mock_config_manager, temp_dir):
    """Create BackfillService instance."""
    return BackfillService(
        config_manager=mock_config_manager,
        cache_dir=temp_dir / "cache",
        timeout_seconds=30,
    )


class TestBackfillTestData:
    """Tests for test data backfill."""

    def test_skip_if_data_exists(self, backfill_service, temp_dir):
        """Test that backfill skips if test data already exists."""
        # Create test data directory
        test_data_path = Path("test-data/zip")
        test_data_path.mkdir(parents=True, exist_ok=True)

        try:
            result = backfill_service.backfill_test_data(family="zip")

            assert result.success
            assert result.skipped
            assert result.skip_reason == "test_data_already_exists"
            assert result.target == "test_data"
        finally:
            # Cleanup
            if test_data_path.exists():
                shutil.rmtree(test_data_path.parent)

    def test_skip_if_download_disabled(self, backfill_service, mock_config_manager):
        """Test that backfill skips if download_if_missing is false."""
        # Modify config to disable download
        family_config = mock_config_manager.load_family_config.return_value
        family_config.test_data.download_if_missing = False
        family_config.test_data.local_path = "nonexistent/path"

        result = backfill_service.backfill_test_data(family="zip")

        assert result.success
        assert result.skipped
        assert result.skip_reason == "download_if_missing_disabled"

    def test_error_if_repo_url_not_configured(self, backfill_service, mock_config_manager):
        """Test error when example_repo.url is not configured."""
        family_config = mock_config_manager.load_family_config.return_value
        family_config.example_repo.url = ""
        family_config.test_data.local_path = "nonexistent/path"

        result = backfill_service.backfill_test_data(family="zip")

        assert not result.success
        assert "example_repo.url not configured" in result.error

    def test_error_if_test_data_path_not_configured(self, backfill_service, mock_config_manager):
        """Test error when test_data_path is not configured."""
        family_config = mock_config_manager.load_family_config.return_value
        family_config.example_repo.test_data_path = ""
        family_config.test_data.local_path = "nonexistent/path"

        result = backfill_service.backfill_test_data(family="zip")

        assert not result.success
        assert "test_data_path not configured" in result.error

    @pytest.mark.skipif(not GIT_AVAILABLE, reason="GitPython not installed")
    @patch('src.services.backfill_service.Repo')
    def test_clone_and_copy_success(self, mock_repo_class, backfill_service, temp_dir):
        """Test successful clone and copy of test data."""
        # Setup mock repo
        mock_repo = MagicMock()
        mock_repo_class.clone_from.return_value = mock_repo

        # Create fake repo with test data
        fake_repo_path = temp_dir / "cache" / "zip" / "repo"
        fake_repo_path.mkdir(parents=True, exist_ok=True)
        (fake_repo_path / ".git").mkdir()
        (fake_repo_path / "Data").mkdir()
        (fake_repo_path / "Data" / "sample.zip").write_text("fake data")

        # Mock _get_or_clone_repo to return our fake repo
        with patch.object(backfill_service, '_get_or_clone_repo', return_value=fake_repo_path):
            # Create temporary local path
            local_path = temp_dir / "test-data" / "zip"
            backfill_service.config_manager.load_family_config.return_value.test_data.local_path = str(local_path)

            result = backfill_service.backfill_test_data(family="zip")

            assert result.success
            assert not result.skipped
            assert result.files_copied > 0
            assert local_path.exists()
            assert (local_path / "sample.zip").exists()

    def test_force_download_overrides_existing(self, backfill_service, temp_dir):
        """Test that force=True downloads even if data exists."""
        # Create existing test data
        test_data_path = temp_dir / "test-data" / "zip"
        test_data_path.mkdir(parents=True, exist_ok=True)
        (test_data_path / "existing.txt").write_text("existing")

        # Mock successful clone
        fake_repo_path = temp_dir / "cache" / "zip" / "repo"
        fake_repo_path.mkdir(parents=True, exist_ok=True)
        (fake_repo_path / ".git").mkdir()
        (fake_repo_path / "Data").mkdir()
        (fake_repo_path / "Data" / "new.zip").write_text("new data")

        backfill_service.config_manager.load_family_config.return_value.test_data.local_path = str(test_data_path)

        with patch.object(backfill_service, '_get_or_clone_repo', return_value=fake_repo_path):
            result = backfill_service.backfill_test_data(family="zip", force=True)

            assert result.success
            assert not result.skipped
            assert (test_data_path / "new.zip").exists()


class TestBackfillAPIReference:
    """Tests for API reference backfill."""

    def test_skip_if_cache_exists(self, backfill_service, temp_dir):
        """Test that backfill skips if cache already exists."""
        cache_path = temp_dir / "cache" / "api-reference" / "zip"
        cache_path.mkdir(parents=True, exist_ok=True)

        backfill_service.config_manager.load_family_config.return_value.api_reference.cache_path = str(cache_path)

        result = backfill_service.backfill_api_reference(family="zip")

        assert result.success
        assert result.skipped
        assert result.skip_reason == "cache_already_exists"

    def test_skip_if_cache_path_not_configured(self, backfill_service):
        """Test skip when cache_path is not configured."""
        backfill_service.config_manager.load_family_config.return_value.api_reference.cache_path = ""

        result = backfill_service.backfill_api_reference(family="zip")

        assert result.success
        assert result.skipped
        assert result.skip_reason == "cache_path_not_configured"

    def test_skip_if_no_sources_configured(self, backfill_service, temp_dir):
        """Test skip when no sources are configured."""
        cache_path = temp_dir / "cache" / "api-reference" / "zip"
        backfill_service.config_manager.load_family_config.return_value.api_reference.cache_path = str(cache_path)
        backfill_service.config_manager.load_family_config.return_value.api_reference.sources = []

        result = backfill_service.backfill_api_reference(family="zip")

        assert result.success
        assert result.skipped
        assert result.skip_reason == "no_sources_configured"

    def test_copy_from_local_sources(self, backfill_service, temp_dir):
        """Test copying API references from local sources."""
        # Create source directory with files
        source_path = temp_dir / "test-reference" / "zip"
        source_path.mkdir(parents=True, exist_ok=True)
        (source_path / "api1.md").write_text("API 1")
        (source_path / "api2.md").write_text("API 2")

        # Configure cache path
        cache_path = temp_dir / "cache" / "api-reference" / "zip"
        backfill_service.config_manager.load_family_config.return_value.api_reference.cache_path = str(cache_path)
        backfill_service.config_manager.load_family_config.return_value.api_reference.sources = [str(source_path)]

        result = backfill_service.backfill_api_reference(family="zip")

        assert result.success
        assert not result.skipped
        assert result.files_copied == 2
        assert cache_path.exists()
        assert (cache_path / "api1.md").exists()
        assert (cache_path / "api2.md").exists()

    def test_force_recache(self, backfill_service, temp_dir):
        """Test that force=True recaches even if cache exists."""
        # Create existing cache
        cache_path = temp_dir / "cache" / "api-reference" / "zip"
        cache_path.mkdir(parents=True, exist_ok=True)
        (cache_path / "old.md").write_text("old")

        # Create new source
        source_path = temp_dir / "test-reference" / "zip"
        source_path.mkdir(parents=True, exist_ok=True)
        (source_path / "new.md").write_text("new")

        backfill_service.config_manager.load_family_config.return_value.api_reference.cache_path = str(cache_path)
        backfill_service.config_manager.load_family_config.return_value.api_reference.sources = [str(source_path)]

        result = backfill_service.backfill_api_reference(family="zip", force=True)

        assert result.success
        assert not result.skipped
        assert (cache_path / "new.md").exists()


class TestBackfillExamples:
    """Tests for example backfill to vector DB."""

    def test_skip_if_vector_db_unavailable(self, backfill_service):
        """Test skip when vector DB is not available."""
        mock_vector_service = Mock()
        mock_vector_service.is_available.return_value = False

        result = backfill_service.backfill_examples_to_vector_db(
            family="zip",
            vector_service=mock_vector_service
        )

        assert result.success
        assert result.skipped
        assert result.skip_reason == "vector_db_not_available"

    def test_error_if_repo_url_not_configured(self, backfill_service):
        """Test error when example_repo.url not configured."""
        mock_vector_service = Mock()
        mock_vector_service.is_available.return_value = True

        backfill_service.config_manager.load_family_config.return_value.example_repo.url = ""

        result = backfill_service.backfill_examples_to_vector_db(
            family="zip",
            vector_service=mock_vector_service
        )

        assert not result.success
        assert "example_repo.url not configured" in result.error

    @pytest.mark.skipif(not GIT_AVAILABLE, reason="GitPython not installed")
    def test_index_examples_to_vector_db(self, backfill_service, temp_dir):
        """Test indexing examples from repo to vector DB."""
        # Create fake repo with examples
        fake_repo_path = temp_dir / "cache" / "zip" / "repo"
        fake_repo_path.mkdir(parents=True, exist_ok=True)
        (fake_repo_path / ".git").mkdir()
        examples_path = fake_repo_path / "Examples"
        examples_path.mkdir()
        (examples_path / "Example1.cs").write_text("using System; class Example1 {}")
        (examples_path / "Example2.cs").write_text("using System; class Example2 {}")

        # Mock vector service
        mock_vector_service = Mock()
        mock_vector_service.is_available.return_value = True

        with patch.object(backfill_service, '_get_or_clone_repo', return_value=fake_repo_path):
            result = backfill_service.backfill_examples_to_vector_db(
                family="zip",
                vector_service=mock_vector_service
            )

            assert result.success
            assert not result.skipped
            assert result.files_copied == 2
            assert mock_vector_service.add_example.call_count == 2


class TestGetOrCloneRepo:
    """Tests for repository caching."""

    @pytest.mark.skipif(not GIT_AVAILABLE, reason="GitPython not installed")
    @patch('src.services.backfill_service.Repo')
    def test_clone_new_repo(self, mock_repo_class, backfill_service, temp_dir):
        """Test cloning a new repository."""
        mock_repo = MagicMock()
        mock_repo_class.clone_from.return_value = mock_repo

        result = backfill_service._get_or_clone_repo(
            url="https://github.com/example/repo.git",
            ref="main",
            family="zip"
        )

        assert result is not None
        assert result.exists()
        assert (result / ".backfill_timestamp").exists()
        mock_repo_class.clone_from.assert_called_once()

    @pytest.mark.skipif(not GIT_AVAILABLE, reason="GitPython not installed")
    def test_use_cached_repo_if_recent(self, backfill_service, temp_dir):
        """Test that cached repo is used if recently fetched."""
        # Create cached repo
        repo_cache_path = temp_dir / "cache" / "zip" / "repo"
        repo_cache_path.mkdir(parents=True, exist_ok=True)
        (repo_cache_path / ".git").mkdir()

        # Create recent timestamp
        timestamp_file = repo_cache_path / ".backfill_timestamp"
        timestamp_file.write_text(datetime.now().isoformat())

        result = backfill_service._get_or_clone_repo(
            url="https://github.com/example/repo.git",
            ref="main",
            family="zip"
        )

        assert result == repo_cache_path

    @pytest.mark.skipif(not GIT_AVAILABLE, reason="GitPython not installed")
    @patch('src.services.backfill_service.Repo')
    def test_refresh_cached_repo_if_old(self, mock_repo_class, backfill_service, temp_dir):
        """Test that old cached repo is refreshed."""
        # Create cached repo
        repo_cache_path = temp_dir / "cache" / "zip" / "repo"
        repo_cache_path.mkdir(parents=True, exist_ok=True)
        (repo_cache_path / ".git").mkdir()

        # Create old timestamp (> 24 hours)
        old_time = datetime.now() - timedelta(hours=25)
        timestamp_file = repo_cache_path / ".backfill_timestamp"
        timestamp_file.write_text(old_time.isoformat())

        # Mock repo for refresh
        mock_repo = MagicMock()
        mock_repo_class.return_value = mock_repo

        result = backfill_service._get_or_clone_repo(
            url="https://github.com/example/repo.git",
            ref="main",
            family="zip"
        )

        assert result == repo_cache_path
        # Verify refresh was attempted
        mock_repo.remotes.origin.fetch.assert_called_once()
        mock_repo.git.checkout.assert_called_once()
        mock_repo.git.pull.assert_called_once()


class TestCopyDirectory:
    """Tests for directory copying utility."""

    def test_copy_directory_recursive(self, backfill_service, temp_dir):
        """Test recursive directory copying."""
        # Create source directory structure
        source = temp_dir / "source"
        source.mkdir()
        (source / "file1.txt").write_text("file1")
        (source / "file2.txt").write_text("file2")
        (source / "subdir").mkdir()
        (source / "subdir" / "file3.txt").write_text("file3")

        # Copy to destination
        dest = temp_dir / "dest"
        dest.mkdir()

        files_copied = backfill_service._copy_directory(source, dest)

        assert files_copied == 3
        assert (dest / "file1.txt").exists()
        assert (dest / "file2.txt").exists()
        assert (dest / "subdir" / "file3.txt").exists()

    def test_copy_empty_directory(self, backfill_service, temp_dir):
        """Test copying an empty directory."""
        source = temp_dir / "empty_source"
        source.mkdir()

        dest = temp_dir / "empty_dest"
        dest.mkdir()

        files_copied = backfill_service._copy_directory(source, dest)

        assert files_copied == 0
