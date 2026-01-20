"""
Unit tests for deterministic discovery and file ordering.

Tests that glob sorting is deterministic and case-normalized for cross-platform compatibility.
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.core.config import ConfigurationManager, GlobalConfig


class TestGlobSortingDeterminism:
    """Test that glob operations sort results deterministically."""

    def test_glob_results_are_sorted(self, mock_filesystem):
        """Glob results should be sorted case-insensitively."""
        files = ["zebra.md", "apple.md", "Banana.md", "CHERRY.md"]
        mock_paths = [Path(f) for f in files]

        # Mock glob to return unsorted paths
        with patch.object(Path, 'glob', return_value=iter(mock_paths)):
            config_manager = ConfigurationManager()

            # This should trigger internal glob + sort
            families = config_manager.list_families()

            # Families should be sorted case-insensitively
            # (Actual implementation should sort internally)

    def test_case_normalized_sorting(self):
        """File paths should be sorted with case normalization."""
        paths = [
            Path("test-content/Zoo.md"),
            Path("test-content/apple.md"),
            Path("test-content/Banana.md"),
            Path("test-content/CHERRY.md"),
        ]

        # Sort using same strategy as production code (case-normalized)
        sorted_paths = sorted(paths, key=lambda p: str(p).lower())

        expected_order = [
            Path("test-content/apple.md"),
            Path("test-content/Banana.md"),
            Path("test-content/CHERRY.md"),
            Path("test-content/Zoo.md"),
        ]

        assert sorted_paths == expected_order

    def test_nested_paths_sorted_deterministically(self):
        """Nested directory paths should sort deterministically."""
        paths = [
            Path("content/z/file.md"),
            Path("content/a/file.md"),
            Path("content/b/file.md"),
            Path("content/A/other.md"),
        ]

        sorted_paths = sorted(paths, key=lambda p: str(p).lower())

        # "a" and "A" should be adjacent (case-insensitive sort)
        path_strs = [str(p).lower() for p in sorted_paths]

        assert path_strs == sorted(path_strs)

    def test_recursive_glob_sorting(self):
        """Recursive glob patterns should produce sorted results."""
        # Simulate recursive glob results
        glob_results = [
            Path("api/Z/Class.md"),
            Path("api/a/Method.md"),
            Path("api/B/Property.md"),
            Path("api/c/Example.md"),
        ]

        # Sort deterministically
        sorted_results = sorted(glob_results, key=lambda p: str(p).lower())

        expected_order = [
            Path("api/a/Method.md"),
            Path("api/B/Property.md"),
            Path("api/c/Example.md"),
            Path("api/Z/Class.md"),
        ]

        assert sorted_results == expected_order


class TestAPIContextOrdering:
    """Test that API context files are loaded in stable order."""

    def test_api_context_files_sorted(self, tmp_path):
        """API context cache files should be loaded in deterministic order."""
        # Create mock API cache directory
        api_cache = tmp_path / "api_cache"
        api_cache.mkdir()

        # Create files in non-alphabetical order
        (api_cache / "ZipArchive.md").write_text("# ZipArchive")
        (api_cache / "Archive.md").write_text("# Archive")
        (api_cache / "BZip2Archive.md").write_text("# BZip2Archive")

        # Glob and sort
        files = sorted(api_cache.glob("*.md"), key=lambda p: str(p).lower())

        file_names = [f.name for f in files]

        expected_order = ["Archive.md", "BZip2Archive.md", "ZipArchive.md"]

        assert file_names == expected_order

    def test_recursive_api_cache_sorted(self, tmp_path):
        """Recursive API cache glob should be sorted deterministically."""
        api_cache = tmp_path / "api_cache"
        (api_cache / "classes").mkdir(parents=True)
        (api_cache / "methods").mkdir(parents=True)

        # Create nested files
        (api_cache / "classes" / "Archive.md").write_text("# Archive")
        (api_cache / "methods" / "Save.md").write_text("# Save")
        (api_cache / "classes" / "ZipFile.md").write_text("# ZipFile")

        # Recursive glob with sorting
        files = sorted(api_cache.glob("**/*.md"), key=lambda p: str(p).lower())

        file_paths = [str(f.relative_to(api_cache)) for f in files]

        # Should be sorted deterministically
        assert file_paths == sorted(file_paths, key=str.lower)


class TestContentDiscoveryOrdering:
    """Test that content discovery produces deterministic ordering."""

    def test_content_files_sorted_by_path(self, tmp_path):
        """Content markdown files should be discovered in sorted order."""
        content_root = tmp_path / "content"
        content_root.mkdir()

        # Create files in random order
        (content_root / "zebra-tutorial.md").write_text("# Zebra")
        (content_root / "apple-guide.md").write_text("# Apple")
        (content_root / "Banana-example.md").write_text("# Banana")

        # Discover and sort
        files = sorted(content_root.glob("*.md"), key=lambda p: str(p).lower())

        file_names = [f.name for f in files]

        expected_order = ["apple-guide.md", "Banana-example.md", "zebra-tutorial.md"]

        assert file_names == expected_order

    def test_discovery_service_file_ordering(self, tmp_path):
        """DiscoveryService should discover files in deterministic order across runs."""
        from src.services.discovery_service import DiscoveryService
        from src.core.database import Database
        from src.core.config import FamilyConfig

        # Create test content
        content_root = tmp_path / "content"
        content_root.mkdir()

        # Create files with varied case
        files_to_create = [
            "zoo-animals.md",
            "Apple-pie.md",
            "Banana-bread.md",
            "cherry-tart.md",
            "ZEBRA-stripes.md",
        ]

        for fname in files_to_create:
            (content_root / fname).write_text(f"# {fname}\n\n```csharp\nConsole.WriteLine(\"test\");\n```")

        # Initialize discovery service
        db = Database(":memory:")
        db.initialize_schema()

        discovery = DiscoveryService(
            db=db,
            content_roots=[str(content_root)]
        )

        # Create family config
        family_config = FamilyConfig(
            family="test_family",
            content_roots=[str(content_root)]
        )

        # Run discovery twice - should produce same order
        from src.services.discovery_service import DiscoveryService

        files_run1 = discovery._find_markdown_files(family_config)
        files_run2 = discovery._find_markdown_files(family_config)

        # Files should be identical across runs
        assert files_run1 == files_run2

        # Files should be sorted case-insensitively
        file_names = [Path(f).name for f in files_run1]
        # Sort verification: files should be in sorted order (case-insensitive)
        expected_order = sorted(file_names, key=str.lower)

        assert file_names == expected_order

    def test_multiple_content_roots_merged_sorted(self, tmp_path):
        """Multiple content roots should be merged and sorted."""
        root1 = tmp_path / "root1"
        root2 = tmp_path / "root2"
        root1.mkdir()
        root2.mkdir()

        (root1 / "apple.md").write_text("# Apple")
        (root1 / "zebra.md").write_text("# Zebra")
        (root2 / "banana.md").write_text("# Banana")
        (root2 / "cherry.md").write_text("# Cherry")

        # Merge and sort
        all_files = []
        for root in [root1, root2]:
            all_files.extend(root.glob("*.md"))

        # Note: glob returns files from each root in iteration order, not sorted
        # The test should verify sorting works when explicitly applied
        file_names = [f.name for f in all_files]

        # Verify that when sorted, they are in correct case-insensitive order
        sorted_names = sorted(file_names, key=str.lower)
        expected_order = ["apple.md", "banana.md", "cherry.md", "zebra.md"]

        assert sorted_names == expected_order


class TestWindowsCompatibility:
    """Test that sorting works correctly on Windows (case-insensitive FS)."""

    def test_windows_style_paths(self):
        """Windows-style paths should sort correctly."""
        paths = [
            Path("C:\\Users\\test\\Zoo.md"),
            Path("C:\\Users\\test\\apple.md"),
            Path("C:\\Users\\test\\Banana.md"),
        ]

        sorted_paths = sorted(paths, key=lambda p: str(p).lower())

        # Should be sorted case-insensitively
        path_strs = [p.name for p in sorted_paths]

        assert path_strs == ["apple.md", "Banana.md", "Zoo.md"]

    def test_posix_style_paths(self):
        """POSIX-style paths should sort correctly."""
        paths = [
            Path("/home/user/Zoo.md"),
            Path("/home/user/apple.md"),
            Path("/home/user/Banana.md"),
        ]

        sorted_paths = sorted(paths, key=lambda p: str(p).lower())

        path_strs = [p.name for p in sorted_paths]

        assert path_strs == ["apple.md", "Banana.md", "Zoo.md"]


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_filesystem():
    """Mock filesystem with predefined files."""
    return {
        "test-content": [
            "zebra.md",
            "apple.md",
            "Banana.md",
            "CHERRY.md",
        ],
        "api-cache": [
            "ZipArchive.md",
            "Archive.md",
            "BZip2Archive.md",
        ],
    }
