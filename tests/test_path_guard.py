"""
Unit tests for path_guard module.
Tests read-only path enforcement and workspace path generation.
"""

import pytest
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.path_guard import (
    normalize_path,
    is_read_only_path,
    assert_write_allowed,
    get_workspace_path,
    READ_ONLY_PREFIXES
)


class TestNormalizePath:
    """Test path normalization."""

    def test_normalize_forward_slashes(self):
        """Test normalization of paths with forward slashes."""
        assert normalize_path("test-data/zip/sample.zip") == "test-data/zip/sample.zip"

    def test_normalize_backward_slashes(self):
        """Test normalization of paths with backward slashes."""
        normalized = normalize_path("test-data\\zip\\sample.zip")
        assert "/" in normalized
        assert "\\" not in normalized

    def test_normalize_pathlib_path(self):
        """Test normalization of Path objects."""
        normalized = normalize_path(Path("tests/fixtures/content/docs/page.md"))
        assert normalized == "tests/fixtures/content/docs/page.md"

    def test_normalize_absolute_path(self):
        """Test normalization of absolute paths."""
        normalized = normalize_path("/home/user/test-data/file.txt")
        assert normalized == "/home/user/test-data/file.txt"


class TestIsReadOnlyPath:
    """Test read-only path detection."""

    def test_test_data_relative(self):
        """Test detection of test-data/ paths."""
        assert is_read_only_path("test-data/zip/sample.zip")
        assert is_read_only_path("test-data/file.txt")
        assert is_read_only_path("test-data/nested/deep/file.md")

    def test_test_content_relative(self):
        """Test detection of tests/fixtures/content/ paths (newly protected)."""
        assert is_read_only_path("tests/fixtures/content/docs/page.md")
        assert is_read_only_path("tests/fixtures/content/index.md")

    def test_test_examples_relative(self):
        """Test detection of test-examples/ paths."""
        assert is_read_only_path("test-examples/Example.cs")
        assert is_read_only_path("test-examples/nested/file.cs")

    def test_test_reference_relative(self):
        """Test detection of tests/fixtures/reference/ paths."""
        assert is_read_only_path("tests/fixtures/reference/api.xml")

    def test_absolute_paths(self):
        """Test detection of read-only paths in absolute form."""
        assert is_read_only_path("/home/user/project/test-data/file.txt")
        assert is_read_only_path("/home/user/project/tests/fixtures/content/docs/page.md")
        assert is_read_only_path("C:/Users/Dev/project/test-examples/Example.cs")

    def test_windows_paths(self):
        """Test detection with Windows-style paths."""
        assert is_read_only_path("test-data\\zip\\sample.zip")
        assert is_read_only_path("tests\\fixtures\\content\\docs\\page.md")

    def test_pathlib_paths(self):
        """Test detection with Path objects."""
        assert is_read_only_path(Path("test-data/file.txt"))
        assert is_read_only_path(Path("tests/fixtures/content/docs/page.md"))

    def test_allowed_paths(self):
        """Test that non-protected paths are allowed."""
        assert not is_read_only_path("workspace/content/file.md")
        assert not is_read_only_path("artifacts/diffs/change.diff")
        assert not is_read_only_path("src/core/database.py")
        assert not is_read_only_path("output/results.txt")

    def test_similar_names_not_blocked(self):
        """Test that paths with similar names but not exact matches are allowed."""
        assert not is_read_only_path("test-output/file.txt")
        assert not is_read_only_path("testing-data/file.txt")
        assert not is_read_only_path("my-test-data-backup/file.txt")

    def test_all_protected_prefixes_covered(self):
        """Ensure all required prefixes are protected."""
        expected_prefixes = {'test-data/', 'test-examples/', 'tests/fixtures/reference/', 'tests/fixtures/content/'}
        assert set(READ_ONLY_PREFIXES) == expected_prefixes


class TestAssertWriteAllowed:
    """Test write permission assertions."""

    def test_blocks_test_data(self):
        """Test that writes to test-data/ are blocked."""
        with pytest.raises(PermissionError, match="WRITE BLOCKED"):
            assert_write_allowed("test-data/zip/sample.zip", "test write")

    def test_blocks_test_content(self):
        """Test that writes to tests/fixtures/content/ are blocked (newly protected)."""
        with pytest.raises(PermissionError, match="WRITE BLOCKED"):
            assert_write_allowed("tests/fixtures/content/docs/page.md", "markdown update")

    def test_blocks_test_examples(self):
        """Test that writes to test-examples/ are blocked."""
        with pytest.raises(PermissionError, match="WRITE BLOCKED"):
            assert_write_allowed("test-examples/Example.cs", "test write")

    def test_blocks_test_reference(self):
        """Test that writes to tests/fixtures/reference/ are blocked."""
        with pytest.raises(PermissionError, match="WRITE BLOCKED"):
            assert_write_allowed("tests/fixtures/reference/api.xml", "test write")

    def test_allows_workspace_writes(self):
        """Test that writes to workspace are allowed."""
        # Should not raise
        assert_write_allowed("workspace/content/file.md", "workspace operation")
        assert_write_allowed("workspace/runtime/Program.cs", "compilation")

    def test_allows_artifacts_writes(self):
        """Test that writes to artifacts are allowed."""
        # Should not raise
        assert_write_allowed("artifacts/diffs/change.diff", "diff generation")
        assert_write_allowed("artifacts/compile/output.log", "compilation log")

    def test_allows_src_writes(self):
        """Test that writes to src are allowed."""
        # Should not raise
        assert_write_allowed("src/core/new_file.py", "code generation")

    def test_error_message_contains_path(self):
        """Test that error message contains the blocked path."""
        with pytest.raises(PermissionError) as exc_info:
            assert_write_allowed("test-data/file.txt", "test write")

        assert "test-data/file.txt" in str(exc_info.value)
        assert "WRITE BLOCKED" in str(exc_info.value)

    def test_error_message_contains_reason(self):
        """Test that error message contains the reason for write."""
        with pytest.raises(PermissionError) as exc_info:
            assert_write_allowed("tests/fixtures/content/docs/page.md", "markdown update")

        assert "markdown update" in str(exc_info.value)

    def test_error_message_suggests_workspace(self):
        """Test that error message suggests workspace copy mode."""
        with pytest.raises(PermissionError) as exc_info:
            assert_write_allowed("tests/fixtures/content/docs/page.md", "test write")

        assert "--use-workspace-copy" in str(exc_info.value) or "workspace" in str(exc_info.value)


class TestGetWorkspacePath:
    """Test workspace path generation."""

    def test_test_content_to_workspace(self):
        """Test mapping tests/fixtures/content/ to workspace."""
        workspace_root = Path("artifacts/workspace")
        run_id = "abc123def456"

        original = "tests/fixtures/content/docs/example.md"
        workspace_path = get_workspace_path(original, workspace_root, run_id)

        expected = Path("artifacts/workspace/abc123def456/content/docs/example.md")
        assert workspace_path == expected

    def test_test_data_to_workspace(self):
        """Test mapping test-data/ to workspace."""
        workspace_root = Path("workspace")
        run_id = "run123"

        original = "test-data/zip/sample.zip"
        workspace_path = get_workspace_path(original, workspace_root, run_id)

        expected = Path("workspace/run123/content/zip/sample.zip")
        assert workspace_path == expected

    def test_test_examples_to_workspace(self):
        """Test mapping test-examples/ to workspace."""
        workspace_root = Path("workspace")
        run_id = "run123"

        original = "test-examples/Example.cs"
        workspace_path = get_workspace_path(original, workspace_root, run_id)

        expected = Path("workspace/run123/content/Example.cs")
        assert workspace_path == expected

    def test_nested_path_preservation(self):
        """Test that nested path structure is preserved."""
        workspace_root = Path("workspace")
        run_id = "run123"

        original = "tests/fixtures/content/docs/nested/deep/file.md"
        workspace_path = get_workspace_path(original, workspace_root, run_id)

        expected = Path("workspace/run123/content/docs/nested/deep/file.md")
        assert workspace_path == expected

    def test_non_protected_path_returns_original(self):
        """Test that non-protected paths return original path."""
        workspace_root = Path("workspace")
        run_id = "run123"

        original = Path("src/core/database.py")
        workspace_path = get_workspace_path(original, workspace_root, run_id)

        assert workspace_path == original

    def test_workspace_path_returns_original(self):
        """Test that paths already in workspace return original."""
        workspace_root = Path("workspace")
        run_id = "run123"

        original = Path("workspace/content/file.md")
        workspace_path = get_workspace_path(original, workspace_root, run_id)

        assert workspace_path == original

    def test_pathlib_input(self):
        """Test with Path object input."""
        workspace_root = Path("workspace")
        run_id = "run123"

        original = Path("tests/fixtures/content/docs/page.md")
        workspace_path = get_workspace_path(original, workspace_root, run_id)

        expected = Path("workspace/run123/content/docs/page.md")
        assert workspace_path == expected

    def test_string_input(self):
        """Test with string input."""
        workspace_root = Path("workspace")
        run_id = "run123"

        original = "tests/fixtures/content/docs/page.md"
        workspace_path = get_workspace_path(original, workspace_root, run_id)

        expected = Path("workspace/run123/content/docs/page.md")
        assert workspace_path == expected

    def test_different_run_ids(self):
        """Test that different run IDs create different workspace paths."""
        workspace_root = Path("workspace")
        original = "tests/fixtures/content/docs/page.md"

        workspace_path_1 = get_workspace_path(original, workspace_root, "run1")
        workspace_path_2 = get_workspace_path(original, workspace_root, "run2")

        assert workspace_path_1 != workspace_path_2
        assert "run1" in str(workspace_path_1)
        assert "run2" in str(workspace_path_2)

    def test_workspace_path_not_read_only(self):
        """Test that generated workspace paths are not read-only."""
        workspace_root = Path("workspace")
        run_id = "run123"

        original = "tests/fixtures/content/docs/page.md"
        workspace_path = get_workspace_path(original, workspace_root, run_id)

        # Workspace path should not be read-only
        assert not is_read_only_path(workspace_path)


class TestIntegration:
    """Integration tests for typical workflows."""

    def test_workflow_detect_and_remap(self):
        """Test typical workflow: detect read-only, then remap to workspace."""
        original_path = "tests/fixtures/content/docs/example.md"

        # Step 1: Detect it's read-only
        assert is_read_only_path(original_path)

        # Step 2: Assert write would be blocked
        with pytest.raises(PermissionError):
            assert_write_allowed(original_path, "direct write attempt")

        # Step 3: Get workspace path
        workspace_path = get_workspace_path(
            original_path,
            Path("workspace"),
            "run123"
        )

        # Step 4: Workspace path is not read-only
        assert not is_read_only_path(workspace_path)

        # Step 5: Write would be allowed to workspace
        assert_write_allowed(workspace_path, "workspace write")  # Should not raise

    def test_all_protected_directories(self):
        """Test that all protected directories are covered."""
        protected_paths = [
            "test-data/file.txt",
            "test-examples/file.cs",
            "tests/fixtures/reference/file.xml",
            "tests/fixtures/content/file.md",
        ]

        for path in protected_paths:
            # Should be detected as read-only
            assert is_read_only_path(path), f"{path} should be read-only"

            # Should block writes
            with pytest.raises(PermissionError):
                assert_write_allowed(path, "test")

            # Should map to workspace
            workspace_path = get_workspace_path(path, Path("workspace"), "run123")
            assert not is_read_only_path(workspace_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
