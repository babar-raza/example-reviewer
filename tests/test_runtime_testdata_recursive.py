"""
Test recursive test-data file lookup in RuntimeService.

Ensures that files in nested directories can be found and copied.
"""

import tempfile
import shutil
from pathlib import Path
import pytest

from src.services.runtime_service import RuntimeService
from src.core.config import RuntimeValidationConfig


def test_find_test_file_exact_match_recursive():
    """Test that find_test_file finds files in subdirectories."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_data = Path(tmpdir) / "test-data"
        test_data.mkdir()

        # Create nested structure: test-data/rar/plrabn12.rar
        rar_dir = test_data / "rar"
        rar_dir.mkdir()
        rar_file = rar_dir / "plrabn12.rar"
        rar_file.write_text("fake rar content")

        # Find it recursively
        found = RuntimeService.find_test_file(
            required_name="plrabn12.rar",
            source_dir=test_data,
            file_aliases={},
            inventory=None
        )

        assert found is not None
        assert found.name == "plrabn12.rar"
        assert found.exists()


def test_find_test_file_alias_recursive():
    """Test that find_test_file finds aliased files in subdirectories."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_data = Path(tmpdir) / "test-data"
        test_data.mkdir()

        # Create nested structure: test-data/archives/sample.rar
        archives_dir = test_data / "archives"
        archives_dir.mkdir()
        sample_rar = archives_dir / "sample.rar"
        sample_rar.write_text("fake rar content")

        # Find it via alias
        found = RuntimeService.find_test_file(
            required_name="plrabn12.rar",
            source_dir=test_data,
            file_aliases={"plrabn12.rar": ["sample.rar"]},
            inventory=None
        )

        assert found is not None
        assert found.name == "sample.rar"
        assert found.exists()


def test_find_test_file_case_insensitive_recursive():
    """Test that find_test_file finds files case-insensitively in subdirectories."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_data = Path(tmpdir) / "test-data"
        test_data.mkdir()

        # Create nested structure: test-data/RAR/PLRABN12.RAR
        rar_dir = test_data / "RAR"
        rar_dir.mkdir()
        rar_file = rar_dir / "PLRABN12.RAR"
        rar_file.write_text("fake rar content")

        # Find it case-insensitively
        found = RuntimeService.find_test_file(
            required_name="plrabn12.rar",
            source_dir=test_data,
            file_aliases={},
            inventory=None
        )

        assert found is not None
        # On Windows, filesystem is case-insensitive, so just check it exists
        assert found.exists()
        assert found.stem.lower() == "plrabn12"
        assert found.suffix.lower() == ".rar"


def test_find_test_file_not_found():
    """Test that find_test_file returns None when file doesn't exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_data = Path(tmpdir) / "test-data"
        test_data.mkdir()

        found = RuntimeService.find_test_file(
            required_name="nonexistent.rar",
            source_dir=test_data,
            file_aliases={},
            inventory=None
        )

        assert found is None


def test_check_test_data_availability_recursive():
    """Test that availability check finds files recursively."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_data = Path(tmpdir) / "test-data"
        test_data.mkdir()

        # Create nested structure
        rar_dir = test_data / "rar"
        rar_dir.mkdir()
        (rar_dir / "plrabn12.rar").write_text("fake rar")

        zip_dir = test_data / "zip"
        zip_dir.mkdir()
        (zip_dir / "sample.zip").write_text("fake zip")

        # Create runtime service (no DB needed for this test)
        runtime = RuntimeService(db=None, family="zip")

        # Create config requiring files in nested dirs
        config = RuntimeValidationConfig(
            required_files=["plrabn12.rar", "sample.zip"],
            file_aliases={},
            expected_outputs=[],
            timeout_seconds=10,
            env={}
        )

        # Check availability
        all_available, missing = runtime.check_test_data_availability(
            test_data, config
        )

        assert all_available is True
        assert len(missing) == 0


def test_check_test_data_availability_missing_file():
    """Test that missing files are correctly identified."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_data = Path(tmpdir) / "test-data"
        test_data.mkdir()

        # Only create one file
        (test_data / "existing.zip").write_text("fake zip")

        runtime = RuntimeService(db=None, family="zip")

        config = RuntimeValidationConfig(
            required_files=["existing.zip", "missing.rar"],
            file_aliases={},
            expected_outputs=[],
            timeout_seconds=10,
            env={}
        )

        all_available, missing = runtime.check_test_data_availability(
            test_data, config
        )

        assert all_available is False
        assert "missing.rar" in missing
        assert "existing.zip" not in missing


def test_copy_test_data_recursive():
    """Test that _copy_test_data copies files from nested directories to workspace root."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_data = Path(tmpdir) / "test-data"
        test_data.mkdir()

        # Create nested structure
        rar_dir = test_data / "rar"
        rar_dir.mkdir()
        rar_file = rar_dir / "plrabn12.rar"
        rar_file.write_text("fake rar content")

        workspace = Path(tmpdir) / "workspace"
        workspace.mkdir()

        runtime = RuntimeService(db=None, family="zip")

        config = RuntimeValidationConfig(
            required_files=["plrabn12.rar"],
            file_aliases={},
            expected_outputs=[],
            timeout_seconds=10,
            env={}
        )

        # Copy test data
        runtime._copy_test_data(test_data, workspace, config)

        # Verify file was copied to workspace root
        copied_file = workspace / "plrabn12.rar"
        assert copied_file.exists()
        assert copied_file.read_text() == "fake rar content"


def test_copy_test_data_with_alias_recursive():
    """Test that _copy_test_data copies aliased files from nested directories."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_data = Path(tmpdir) / "test-data"
        test_data.mkdir()

        # Create nested structure with alias name
        archives_dir = test_data / "archives"
        archives_dir.mkdir()
        alias_file = archives_dir / "sample.rar"
        alias_file.write_text("fake rar content")

        workspace = Path(tmpdir) / "workspace"
        workspace.mkdir()

        runtime = RuntimeService(db=None, family="zip")

        config = RuntimeValidationConfig(
            required_files=["plrabn12.rar"],
            file_aliases={"plrabn12.rar": ["sample.rar"]},
            expected_outputs=[],
            timeout_seconds=10,
            env={}
        )

        # Copy test data
        runtime._copy_test_data(test_data, workspace, config)

        # Verify file was copied to workspace root under both names
        required_file = workspace / "plrabn12.rar"
        alias_copy = workspace / "sample.rar"

        assert required_file.exists()
        assert alias_copy.exists()
        assert required_file.read_text() == "fake rar content"
        assert alias_copy.read_text() == "fake rar content"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
