"""
Tests for CLI entry point contract.

Validates that both 'python -m cli' and 'python -m src.cli.main' work identically,
ensuring backward compatibility while providing the cleaner user-facing invocation.
"""

import subprocess
import sys


def test_cli_module_works():
    """Test that 'python -m cli --help' works."""
    result = subprocess.run(
        [sys.executable, "-m", "cli", "--help"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    assert "Example Reviewer" in result.stdout or "usage:" in result.stdout


def test_src_cli_main_works_backward_compat():
    """Test that 'python -m src.cli.main --help' still works (backward compat)."""
    result = subprocess.run(
        [sys.executable, "-m", "src.cli.main", "--help"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    assert "Example Reviewer" in result.stdout or "usage:" in result.stdout


def test_both_entry_points_identical():
    """Test that both entry points produce identical output."""
    result1 = subprocess.run(
        [sys.executable, "-m", "cli", "--help"],
        capture_output=True,
        text=True
    )

    result2 = subprocess.run(
        [sys.executable, "-m", "src.cli.main", "--help"],
        capture_output=True,
        text=True
    )

    assert result1.stdout == result2.stdout
    assert result1.returncode == result2.returncode


def test_cli_list_families():
    """Test that 'python -m cli list-families' works."""
    result = subprocess.run(
        [sys.executable, "-m", "cli", "list-families"],
        capture_output=True,
        text=True
    )
    # Should succeed (even if no families configured)
    assert result.returncode == 0


def test_cli_status_without_family():
    """Test that 'python -m cli status' works."""
    result = subprocess.run(
        [sys.executable, "-m", "cli", "status"],
        capture_output=True,
        text=True
    )
    # Should succeed (even if no status to report)
    assert result.returncode == 0


def test_cli_version_accessible():
    """Test that version information is accessible from cli package."""
    # This tests the __version__ attribute
    try:
        import cli
        assert hasattr(cli, '__version__')
        assert isinstance(cli.__version__, str)
        assert cli.__version__ == "0.1.0"
    except ImportError:
        # If import fails, the package structure is wrong
        assert False, "cli package should be importable"
