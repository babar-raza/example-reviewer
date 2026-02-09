"""
Unit tests for APIReferenceService.

TASK-3A: Tests for API reference fetching and caching.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from src.services.api_reference_service import APIReferenceService, FileIndexEntry
from src.core.config import ApiReferenceConfig


@pytest.fixture
def temp_cache_dir():
    """Create temporary cache directory."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def basic_config():
    """Basic API reference config."""
    return ApiReferenceConfig(
        git_repo="https://github.com/example/api-reference",
        git_ref="main",
        git_subpath="",
        shallow_clone=True,
        auto_fetch=True,
        max_context_chars=8000
    )


@pytest.fixture
def service_with_config(basic_config, temp_cache_dir):
    """Create service with basic config."""
    return APIReferenceService(
        family="test",
        config=basic_config,
        cache_dir=temp_cache_dir
    )


class TestAPIReferenceServiceInit:
    """Test service initialization."""

    def test_init_creates_service(self, basic_config, temp_cache_dir):
        """Test service initialization."""
        service = APIReferenceService(
            family="words",
            config=basic_config,
            cache_dir=temp_cache_dir
        )

        assert service.family == "words"
        assert service.config == basic_config
        assert service.cache_dir == temp_cache_dir / "words" / "api-reference"
        assert service._index is None
        assert service._indexed is False

    def test_cache_dir_structure(self, service_with_config, temp_cache_dir):
        """Test cache directory structure."""
        expected_path = temp_cache_dir / "test" / "api-reference"
        assert service_with_config.cache_dir == expected_path


class TestEnsureCached:
    """Test ensure_cached() method."""

    def test_no_git_repo_configured(self, temp_cache_dir):
        """Test behavior when git_repo not configured."""
        config = ApiReferenceConfig(git_repo="")
        service = APIReferenceService("test", config, temp_cache_dir)

        result = service.ensure_cached()

        assert result is False

    def test_already_cached(self, service_with_config):
        """Test behavior when cache already exists."""
        # Create cache directory
        service_with_config.cache_dir.mkdir(parents=True, exist_ok=True)

        result = service_with_config.ensure_cached()

        assert result is True

    def test_auto_fetch_disabled(self, temp_cache_dir):
        """Test behavior when auto_fetch disabled."""
        config = ApiReferenceConfig(
            git_repo="https://github.com/example/api-reference",
            auto_fetch=False
        )
        service = APIReferenceService("test", config, temp_cache_dir)

        result = service.ensure_cached()

        assert result is False

    @patch('subprocess.run')
    def test_fetch_from_git_success(self, mock_run, service_with_config):
        """Test successful git clone."""
        mock_run.return_value = MagicMock(stdout="Cloning...", stderr="", returncode=0)

        result = service_with_config.ensure_cached()

        assert result is True
        assert mock_run.called
        call_args = mock_run.call_args[0][0]
        assert "git" in call_args
        assert "clone" in call_args
        assert "--depth" in call_args
        assert "1" in call_args

    @patch('subprocess.run')
    def test_fetch_from_git_timeout(self, mock_run, service_with_config):
        """Test git clone timeout."""
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired("git", 30)

        result = service_with_config.ensure_cached()

        assert result is False

    @patch('subprocess.run')
    def test_fetch_from_git_failure(self, mock_run, service_with_config):
        """Test git clone failure."""
        import subprocess
        mock_run.side_effect = subprocess.CalledProcessError(
            1, "git", stderr="Repository not found"
        )

        result = service_with_config.ensure_cached()

        assert result is False

    @patch('subprocess.run')
    def test_fetch_git_not_installed(self, mock_run, service_with_config):
        """Test behavior when git not installed."""
        mock_run.side_effect = FileNotFoundError()

        result = service_with_config.ensure_cached()

        assert result is False


class TestFileIndexing:
    """Test file indexing functionality."""

    def test_build_index_empty_cache(self, service_with_config):
        """Test building index with empty cache."""
        service_with_config.cache_dir.mkdir(parents=True, exist_ok=True)

        index = service_with_config._build_file_index()

        assert isinstance(index, dict)
        assert len(index) == 0
        assert service_with_config._indexed is True

    def test_build_index_with_markdown_files(self, service_with_config):
        """Test indexing markdown files."""
        # Create cache structure
        cache = service_with_config.cache_dir
        cache.mkdir(parents=True, exist_ok=True)

        # Create test markdown file
        md_file = cache / "charttype.md"
        md_file.write_text("# ChartType Enum\n\nDefines chart types.", encoding='utf-8')

        index = service_with_config._build_file_index()

        assert len(index) > 0
        assert 'charttype' in index or 'ChartType' in index

    def test_build_index_with_csharp_files(self, service_with_config):
        """Test indexing C# files."""
        cache = service_with_config.cache_dir
        cache.mkdir(parents=True, exist_ok=True)

        # Create test C# file
        cs_file = cache / "Document.cs"
        cs_file.write_text(
            "namespace Aspose.Words\n{\n    public class Document { }\n}",
            encoding='utf-8'
        )

        index = service_with_config._build_file_index()

        assert 'Document' in index or 'document' in index
        assert 'Aspose.Words' in index or 'aspose.words' in index

    def test_index_caching(self, service_with_config):
        """Test that index is cached after first build."""
        cache = service_with_config.cache_dir
        cache.mkdir(parents=True, exist_ok=True)

        # First build
        index1 = service_with_config._build_file_index()

        # Second build (should return cached)
        index2 = service_with_config._build_file_index()

        assert index1 is index2

    def test_extract_entity_names_from_markdown(self, service_with_config):
        """Test entity extraction from markdown."""
        cache = service_with_config.cache_dir
        cache.mkdir(parents=True, exist_ok=True)

        md_file = cache / "test.md"
        md_file.write_text(
            "# ChartType Enum\n\nUse `ChartAxis` for axis configuration.",
            encoding='utf-8'
        )

        entities = service_with_config._extract_entity_names(md_file, cache)

        assert 'test' in entities or 'Test' in entities
        assert 'ChartType' in entities or 'charttype' in entities
        assert 'ChartAxis' in entities or 'chartaxis' in entities

    def test_extract_entity_names_from_csharp(self, service_with_config):
        """Test entity extraction from C# file."""
        cache = service_with_config.cache_dir
        cache.mkdir(parents=True, exist_ok=True)

        cs_file = cache / "types.cs"
        cs_file.write_text(
            "namespace Aspose.Words.Drawing\n"
            "{\n"
            "    public enum ChartType { }\n"
            "    public class Chart { }\n"
            "}",
            encoding='utf-8'
        )

        entities = service_with_config._extract_entity_names(cs_file, cache)

        assert 'ChartType' in entities
        assert 'Chart' in entities
        assert 'Aspose.Words.Drawing' in entities


class TestContextExtraction:
    """Test context extraction for errors."""

    def test_get_context_cache_not_available(self, service_with_config):
        """Test context extraction when cache not available."""
        context = service_with_config.get_context_for_error(
            "CS0103",
            "The name 'ChartType' does not exist"
        )

        assert context == ""

    def test_get_context_no_entities_found(self, service_with_config):
        """Test context extraction when no entities found in error."""
        service_with_config.cache_dir.mkdir(parents=True, exist_ok=True)

        context = service_with_config.get_context_for_error(
            "CS0103",
            "Random error message"
        )

        # Should return empty (no matching entities)
        assert isinstance(context, str)

    def test_get_context_with_matching_file(self, service_with_config):
        """Test context extraction with matching documentation."""
        cache = service_with_config.cache_dir
        cache.mkdir(parents=True, exist_ok=True)

        # Create API documentation
        doc_file = cache / "charttype.md"
        doc_file.write_text(
            "# ChartType Enum\n\n"
            "Defines the type of chart.\n\n"
            "## Values\n"
            "- Line\n"
            "- Bar\n"
            "- Pie",
            encoding='utf-8'
        )

        context = service_with_config.get_context_for_error(
            "CS0103",
            "The name 'ChartType' does not exist in the current context"
        )

        assert "ChartType" in context
        assert "API Reference Context" in context

    def test_extract_entities_from_cs0103_error(self, service_with_config):
        """Test entity extraction from CS0103 error."""
        entities = service_with_config._extract_entities_from_error(
            "CS0103",
            "error CS0103: The name 'ChartType' does not exist in the current context"
        )

        assert 'ChartType' in entities

    def test_extract_entities_from_cs0117_error(self, service_with_config):
        """Test entity extraction from CS0117 error."""
        entities = service_with_config._extract_entities_from_error(
            "CS0117",
            "error CS0117: 'ChartType' does not contain a definition for 'Unknown'"
        )

        assert 'ChartType' in entities
        assert 'Unknown' in entities

    def test_extract_entities_with_namespace(self, service_with_config):
        """Test entity extraction with namespace."""
        entities = service_with_config._extract_entities_from_error(
            "CS0246",
            "type or namespace name 'Aspose.Words.Drawing' could not be found"
        )

        assert 'Aspose' in entities or 'Words' in entities or 'Drawing' in entities

    def test_context_respects_max_chars(self, service_with_config):
        """Test context respects max_chars limit."""
        cache = service_with_config.cache_dir
        cache.mkdir(parents=True, exist_ok=True)

        # Create large documentation file
        large_content = "# ChartType\n\n" + ("Lorem ipsum " * 1000)
        doc_file = cache / "charttype.md"
        doc_file.write_text(large_content, encoding='utf-8')

        context = service_with_config.get_context_for_error(
            "CS0103",
            "The name 'ChartType' does not exist",
            max_chars=500
        )

        assert len(context) <= 500


class TestSearchIndex:
    """Test index searching."""

    def test_search_exact_match(self, service_with_config):
        """Test exact match search."""
        entry = FileIndexEntry(
            file_path=Path("/test/chart.md"),
            relative_path="chart.md",
            entity_names=frozenset({'Chart', 'ChartType'}),
            content_preview="Test content",
            file_size=100
        )
        index = {'Chart': [entry], 'ChartType': [entry]}

        matches = service_with_config._search_index(index, {'Chart'})

        assert len(matches) > 0
        assert matches[0][0] == entry
        assert matches[0][1] > 0  # Has relevance score

    def test_search_case_insensitive(self, service_with_config):
        """Test case-insensitive search."""
        entry = FileIndexEntry(
            file_path=Path("/test/chart.md"),
            relative_path="chart.md",
            entity_names=frozenset({'ChartType'}),
            content_preview="Test",
            file_size=50
        )
        index = {'ChartType': [entry]}

        matches = service_with_config._search_index(index, {'charttype'})

        assert len(matches) > 0

    def test_search_partial_match(self, service_with_config):
        """Test partial match search."""
        entry = FileIndexEntry(
            file_path=Path("/test/chart.md"),
            relative_path="chart.md",
            entity_names=frozenset({'ChartType'}),
            content_preview="Test",
            file_size=50
        )
        index = {'ChartType': [entry]}

        matches = service_with_config._search_index(index, {'Chart'})

        assert len(matches) > 0


class TestStats:
    """Test statistics functionality."""

    def test_get_stats_not_cached(self, service_with_config):
        """Test stats when not cached."""
        stats = service_with_config.get_stats()

        assert stats['cached'] is False
        assert stats['indexed'] is False
        assert 'config' in stats

    def test_get_stats_cached(self, service_with_config):
        """Test stats when cached."""
        service_with_config.cache_dir.mkdir(parents=True, exist_ok=True)

        stats = service_with_config.get_stats()

        assert stats['cached'] is True

    def test_get_stats_indexed(self, service_with_config):
        """Test stats after indexing."""
        cache = service_with_config.cache_dir
        cache.mkdir(parents=True, exist_ok=True)

        # Create test file
        (cache / "test.md").write_text("# Test\n", encoding='utf-8')

        # Build index
        service_with_config._build_file_index()

        stats = service_with_config.get_stats()

        assert stats['indexed'] is True
        assert 'entity_count' in stats
        assert 'total_files' in stats


class TestGitSubpath:
    """Test git subpath functionality."""

    def test_subpath_in_config(self, temp_cache_dir):
        """Test subpath configuration."""
        config = ApiReferenceConfig(
            git_repo="https://github.com/example/api-reference",
            git_subpath="english/net"
        )
        service = APIReferenceService("test", config, temp_cache_dir)

        assert service.config.git_subpath == "english/net"

    def test_indexing_with_subpath(self, temp_cache_dir):
        """Test indexing with subpath."""
        config = ApiReferenceConfig(
            git_repo="https://github.com/example/api-reference",
            git_subpath="docs"
        )
        service = APIReferenceService("test", config, temp_cache_dir)

        # Create cache with subpath
        cache = service.cache_dir
        cache.mkdir(parents=True, exist_ok=True)
        subpath_dir = cache / "docs"
        subpath_dir.mkdir(parents=True, exist_ok=True)

        # Create file in subpath
        (subpath_dir / "test.md").write_text("# Test", encoding='utf-8')

        index = service._build_file_index()

        assert len(index) > 0

    def test_indexing_subpath_not_found(self, temp_cache_dir):
        """Test indexing when subpath doesn't exist."""
        config = ApiReferenceConfig(
            git_repo="https://github.com/example/api-reference",
            git_subpath="nonexistent"
        )
        service = APIReferenceService("test", config, temp_cache_dir)

        # Create cache WITHOUT subpath
        cache = service.cache_dir
        cache.mkdir(parents=True, exist_ok=True)
        (cache / "root.md").write_text("# Root", encoding='utf-8')

        # Should fall back to scanning entire cache
        index = service._build_file_index()

        assert len(index) > 0
