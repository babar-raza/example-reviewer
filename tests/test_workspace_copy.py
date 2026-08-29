"""
Tests for workspace copy mode integration.
Ensures read-only paths are properly redirected to workspace copies.
"""

import pytest
from pathlib import Path
from src.core.path_guard import (
    is_read_only_path,
    get_workspace_path,
    assert_write_allowed,
)
from src.services.markdown_service import MarkdownUpdateService
from tests.conftest import make_pdp
from src.core.database import Database
from src.core.models import ExampleRecord, ExampleStatus, SourceType, Location


class TestWorkspaceCopyMode:
    """Test workspace copy mode functionality."""

    def test_read_only_path_detection(self):
        """Test that read-only paths are correctly identified."""
        # Test all protected prefixes
        assert is_read_only_path("test-data/zip/sample.zip")
        assert is_read_only_path("tests/fixtures/content/docs/example.md")
        assert is_read_only_path("test-examples/Program.cs")
        assert is_read_only_path("tests/fixtures/reference/api.json")

        # Test absolute paths
        assert is_read_only_path("/home/user/repo/tests/fixtures/content/docs/example.md")
        assert is_read_only_path("c:\\Users\\user\\test-data\\file.txt")

        # Test non-protected paths
        assert not is_read_only_path("workspace/content/example.md")
        assert not is_read_only_path("artifacts/output.txt")

    def test_workspace_path_mapping_relative(self):
        """Test workspace path mapping for relative paths."""
        workspace_root = Path("artifacts/workspace")
        run_id = "test123"

        # Test relative path
        original = "tests/fixtures/content/docs/example.md"
        workspace = get_workspace_path(original, workspace_root, run_id)

        # Normalize to forward slashes for cross-platform comparison
        assert workspace.as_posix() == "artifacts/workspace/test123/content/docs/example.md"

    def test_workspace_path_mapping_absolute(self):
        """Test workspace path mapping for absolute paths."""
        workspace_root = Path("artifacts/workspace")
        run_id = "test123"

        # Test absolute path (Unix-style)
        original = "/home/user/repo/tests/fixtures/content/docs/example.md"
        workspace = get_workspace_path(original, workspace_root, run_id)

        # Normalize to forward slashes for cross-platform comparison
        assert workspace.as_posix() == "artifacts/workspace/test123/content/docs/example.md"

    def test_workspace_path_mapping_non_readonly(self):
        """Test that non-read-only paths are not redirected."""
        workspace_root = Path("artifacts/workspace")
        run_id = "test123"

        # Test non-protected path
        original = "workspace/file.txt"
        result = get_workspace_path(original, workspace_root, run_id)

        # Should return original path unchanged
        # Normalize to forward slashes for cross-platform comparison
        assert result.as_posix() == original

    def test_write_guard_blocks_readonly_paths(self):
        """Test that write guard blocks writes to read-only paths."""
        with pytest.raises(PermissionError, match="WRITE BLOCKED"):
            assert_write_allowed("tests/fixtures/content/docs/example.md", "test write")

    def test_markdown_service_workspace_copy_integration(self, temp_db, tmp_path):
        """Test markdown service integration with workspace copy mode."""
        # Create markdown service with workspace copy enabled
        service = MarkdownUpdateService(
            db=Database(temp_db),
            pdp=make_pdp(allow_writes=True),
            use_workspace_copy=True,
            workspace_root=tmp_path / "workspace",
            run_id="test_run_123"
        )

        # Verify workspace copy mode is enabled
        assert service.use_workspace_copy is True

        # Test path mapping
        original_path = "tests/fixtures/content/docs/example.md"
        target_path = service._get_write_target_path(original_path)

        # Should be redirected to workspace
        # Normalize for cross-platform comparison
        normalized = target_path.replace("\\", "/")
        assert "workspace" in normalized
        assert "test_run_123" in normalized
        assert "content/docs/example.md" in normalized

    def test_markdown_service_without_workspace_copy(self, temp_db):
        """Test markdown service without workspace copy mode."""
        service = MarkdownUpdateService(
            db=Database(temp_db),
            pdp=make_pdp(allow_writes=False),
            use_workspace_copy=False,
        )

        # Verify workspace copy mode is disabled
        assert service.use_workspace_copy is False

        # Test path mapping (should return original)
        original_path = "workspace/docs/example.md"
        target_path = service._get_write_target_path(original_path)

        assert target_path == original_path


class TestWorkspacePathStructure:
    """Test workspace directory structure."""

    def test_workspace_preserves_structure(self):
        """Test that workspace mapping preserves directory structure."""
        workspace_root = Path("artifacts/workspace")
        run_id = "abc123"

        test_cases = [
            ("tests/fixtures/content/docs/guide.md", "artifacts/workspace/abc123/content/docs/guide.md"),
            ("tests/fixtures/content/api/reference.md", "artifacts/workspace/abc123/content/api/reference.md"),
            ("test-data/zip/sample.zip", "artifacts/workspace/abc123/content/zip/sample.zip"),
        ]

        for original, expected in test_cases:
            result = get_workspace_path(original, workspace_root, run_id)
            # Normalize to forward slashes for cross-platform comparison
            assert result.as_posix() == expected

    def test_workspace_run_isolation(self):
        """Test that different runs get isolated workspaces."""
        workspace_root = Path("artifacts/workspace")
        original = "tests/fixtures/content/docs/example.md"

        # Run 1
        workspace1 = get_workspace_path(original, workspace_root, "run_001")
        assert "run_001" in str(workspace1)

        # Run 2
        workspace2 = get_workspace_path(original, workspace_root, "run_002")
        assert "run_002" in str(workspace2)

        # Paths should be different
        assert workspace1 != workspace2
