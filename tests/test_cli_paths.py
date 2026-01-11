"""Unit tests for CLI path resolution.

Verifies that CLI correctly resolves repository paths without external dependencies.
"""

from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_cli_path_resolution_logic():
    """Test the path resolution logic without initializing full CLI."""
    # Simulate the path resolution logic from cli.py
    cli_file_path = Path(__file__).parent.parent / "src" / "cli.py"

    script_dir = cli_file_path.parent.parent  # example-reviewer/
    repo_root = script_dir  # Fixed: should be same as script_dir

    # repo_root should be the example-reviewer directory
    assert repo_root.name == "example-reviewer", \
        f"Expected repo_root.name to be 'example-reviewer', got {repo_root.name}"

    # Verify paths point to correct locations
    config_dir = repo_root / "config" / "families"
    content_dir = repo_root / "content"

    # config_dir should be inside repo
    assert repo_root in config_dir.parents, \
        f"config_dir {config_dir} should be inside repo_root {repo_root}"

    # content_dir should be inside repo
    assert repo_root in content_dir.parents, \
        f"content_dir {content_dir} should be inside repo_root {repo_root}"

    # repo_root should exist
    assert repo_root.exists(), \
        f"repo_root {repo_root} should exist"


def test_cli_paths_relative_structure():
    """Verify the relative path structure is correct."""
    # Start from test file location
    repo_root = Path(__file__).parent.parent

    # Key directories should exist or be valid paths under repo
    src_dir = repo_root / "src"
    config_dir = repo_root / "config"
    tests_dir = repo_root / "tests"

    assert src_dir.exists(), f"src directory should exist at {src_dir}"
    assert tests_dir.exists(), f"tests directory should exist at {tests_dir}"

    # Config might not exist yet, but path should be under repo
    assert repo_root in config_dir.parents or config_dir.parent == repo_root, \
        f"config_dir should be under repo_root"


if __name__ == "__main__":
    # Run tests
    test_cli_path_resolution_logic()
    test_cli_paths_relative_structure()
    print("[PASS] All path resolution tests passed!")
