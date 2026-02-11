"""
Test runtime service directory handling.

Verifies that required_dirs configuration correctly identifies and copies
directory test data into runtime workspaces.
"""

import pytest
import shutil
from pathlib import Path

from src.services.runtime_service import RuntimeService
from src.core.config import RuntimeValidationConfig
from src.core.database import Database


def test_find_test_dir_exact_match(tmp_path):
    """Test finding directory by exact name match."""
    # Create test directory structure
    test_data = tmp_path / "test-data"
    test_data.mkdir()
    sample_dir = test_data / "sample_dir"
    sample_dir.mkdir()
    (sample_dir / "file1.txt").write_text("content1")

    # Test finding the directory
    found = RuntimeService.find_test_dir(
        "sample_dir",
        test_data,
        dir_aliases={},
        inventory=None
    )

    assert found is not None
    assert found == sample_dir
    assert found.is_dir()


def test_find_test_dir_alias_match(tmp_path):
    """Test finding directory by alias."""
    # Create test directory structure
    test_data = tmp_path / "test-data"
    test_data.mkdir()
    input_dir = test_data / "input"
    input_dir.mkdir()
    (input_dir / "file1.txt").write_text("content1")

    # Test finding by alias
    found = RuntimeService.find_test_dir(
        "sample_dir",
        test_data,
        dir_aliases={"sample_dir": ["input", "data", "sourceDir"]},
        inventory=None
    )

    assert found is not None
    assert found == input_dir
    assert found.is_dir()


def test_find_test_dir_nested(tmp_path):
    """Test finding directory nested in subdirectories."""
    # Create nested structure
    test_data = tmp_path / "test-data"
    test_data.mkdir()
    nested = test_data / "level1" / "level2" / "sample_dir"
    nested.mkdir(parents=True)
    (nested / "file1.txt").write_text("content1")

    # Test recursive search
    found = RuntimeService.find_test_dir(
        "sample_dir",
        test_data,
        dir_aliases={},
        inventory=None
    )

    assert found is not None
    assert found == nested
    assert found.is_dir()


def test_check_test_data_availability_with_dirs(tmp_path):
    """Test availability check with both files and directories."""
    # Setup
    db = Database(":memory:")
    runtime_service = RuntimeService(db, family="zip", workspace_dir=tmp_path / "workspace")

    # Create test data
    test_data = tmp_path / "test-data"
    test_data.mkdir()
    (test_data / "sample.zip").write_text("zip content")
    sample_dir = test_data / "sample_dir"
    sample_dir.mkdir()
    (sample_dir / "file1.txt").write_text("content1")

    # Config with both files and dirs
    config = RuntimeValidationConfig(
        enabled=True,
        required_files=["sample.zip"],
        required_dirs=["sample_dir"],
        file_aliases={},
    )

    # Check availability
    all_available, missing = runtime_service.check_test_data_availability(
        test_data, config, inventory=None
    )

    assert all_available is True
    assert len(missing) == 0


def test_check_test_data_availability_missing_dir(tmp_path):
    """Test availability check with missing directory."""
    # Setup
    db = Database(":memory:")
    runtime_service = RuntimeService(db, family="zip", workspace_dir=tmp_path / "workspace")

    # Create test data without the required directory
    test_data = tmp_path / "test-data"
    test_data.mkdir()
    (test_data / "sample.zip").write_text("zip content")

    # Config with both files and dirs
    config = RuntimeValidationConfig(
        enabled=True,
        required_files=["sample.zip"],
        required_dirs=["sample_dir"],
        file_aliases={},
    )

    # Check availability
    all_available, missing = runtime_service.check_test_data_availability(
        test_data, config, inventory=None
    )

    assert all_available is False
    assert "sample_dir" in missing
    assert "sample.zip" not in missing


def test_copy_test_data_with_dirs(tmp_path):
    """Test copying test data including directories."""
    # Setup
    db = Database(":memory:")
    runtime_service = RuntimeService(db, family="zip", workspace_dir=tmp_path / "workspace")

    # Create test data
    source_dir = tmp_path / "test-data"
    source_dir.mkdir()
    (source_dir / "sample.zip").write_text("zip content")
    sample_dir = source_dir / "sample_dir"
    sample_dir.mkdir()
    (sample_dir / "file1.txt").write_text("content1")
    (sample_dir / "file2.txt").write_text("content2")
    subfolder = sample_dir / "subfolder"
    subfolder.mkdir()
    (subfolder / "nested.txt").write_text("nested content")

    # Workspace
    work_dir = tmp_path / "workspace"
    work_dir.mkdir(exist_ok=True)

    # Config with both files and dirs
    config = RuntimeValidationConfig(
        enabled=True,
        required_files=["sample.zip"],
        required_dirs=["sample_dir"],
        file_aliases={},
    )

    # Copy test data
    runtime_service._copy_test_data(source_dir, work_dir, config, inventory=None)

    # Verify file copied
    assert (work_dir / "sample.zip").exists()
    assert (work_dir / "sample.zip").is_file()

    # Verify directory copied with contents
    assert (work_dir / "sample_dir").exists()
    assert (work_dir / "sample_dir").is_dir()
    assert (work_dir / "sample_dir" / "file1.txt").exists()
    assert (work_dir / "sample_dir" / "file2.txt").exists()
    assert (work_dir / "sample_dir" / "subfolder" / "nested.txt").exists()

    # Verify content integrity
    assert (work_dir / "sample_dir" / "file1.txt").read_text() == "content1"
    assert (work_dir / "sample_dir" / "subfolder" / "nested.txt").read_text() == "nested content"


def test_copy_test_data_dir_with_aliases(tmp_path):
    """Test copying directories with alias support."""
    # Setup
    db = Database(":memory:")
    runtime_service = RuntimeService(db, family="zip", workspace_dir=tmp_path / "workspace")

    # Create test data
    source_dir = tmp_path / "test-data"
    source_dir.mkdir()
    input_dir = source_dir / "input"
    input_dir.mkdir()
    (input_dir / "file1.txt").write_text("content1")

    # Workspace
    work_dir = tmp_path / "workspace"
    work_dir.mkdir(exist_ok=True)

    # Config with alias mapping
    config = RuntimeValidationConfig(
        enabled=True,
        required_files=[],
        required_dirs=["sample_dir"],
        file_aliases={"sample_dir": ["input", "data", "sourceDir"]},
    )

    # Copy test data
    runtime_service._copy_test_data(source_dir, work_dir, config, inventory=None)

    # Verify canonical name created
    assert (work_dir / "sample_dir").exists()
    assert (work_dir / "sample_dir").is_dir()
    assert (work_dir / "sample_dir" / "file1.txt").exists()

    # Verify aliases created
    assert (work_dir / "input").exists()
    assert (work_dir / "input").is_dir()
    assert (work_dir / "data").exists()
    assert (work_dir / "data").is_dir()
    assert (work_dir / "sourceDir").exists()
    assert (work_dir / "sourceDir").is_dir()
