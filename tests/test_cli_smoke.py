"""
CLI Smoke Tests for Example Reviewer Pipeline.

Tests basic CLI functionality to catch import errors and execution failures.
All tests use subprocess for real CLI invocation.
"""

import subprocess
import sys
import tempfile
from pathlib import Path

import pytest


def run_cli(*args, timeout=30):
    """
    Run CLI command and return result.

    Args:
        *args: CLI arguments
        timeout: Timeout in seconds

    Returns:
        subprocess.CompletedProcess with stdout, stderr, returncode
    """
    cmd = [sys.executable, '-m', 'src.cli.main'] + list(args)
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=Path(__file__).parent.parent  # Run from repo root
    )
    return result


def assert_no_import_errors(result):
    """Assert no import errors in stderr."""
    assert 'ImportError' not in result.stderr, f"Import error detected: {result.stderr}"
    assert 'ModuleNotFoundError' not in result.stderr, f"Module not found: {result.stderr}"
    assert 'NameError' not in result.stderr, f"Name error detected: {result.stderr}"


def assert_help_works(result):
    """Assert help command worked correctly."""
    assert result.returncode == 0, f"Help command failed: {result.stderr}"
    assert_no_import_errors(result)
    assert len(result.stdout) > 0, "Help output is empty"


# ============================================================================
# Help Tests - Fast smoke tests for all commands
# ============================================================================


def test_main_help():
    """Test main --help works without import errors."""
    result = run_cli('--help')
    assert_help_works(result)
    assert 'Example Reviewer Pipeline CLI' in result.stdout
    assert 'Available commands' in result.stdout


def test_scan_help():
    """Test scan --help works."""
    result = run_cli('scan', '--help')
    assert_help_works(result)
    assert '--family' in result.stdout
    assert 'scan' in result.stdout


def test_extract_help():
    """Test extract --help works."""
    result = run_cli('extract', '--help')
    assert_help_works(result)
    assert '--family' in result.stdout
    assert 'extract' in result.stdout


def test_compile_verify_help():
    """Test compile-verify --help works."""
    result = run_cli('compile-verify', '--help')
    assert_help_works(result)
    assert '--family' in result.stdout
    assert 'compile-verify' in result.stdout


def test_compile_fix_help():
    """Test compile-fix --help works."""
    result = run_cli('compile-fix', '--help')
    assert_help_works(result)
    assert '--family' in result.stdout
    assert 'compile-fix' in result.stdout


def test_runtime_verify_help():
    """Test runtime-verify --help works."""
    result = run_cli('runtime-verify', '--help')
    assert_help_works(result)
    assert '--family' in result.stdout
    assert 'runtime-verify' in result.stdout


def test_runtime_fix_help():
    """Test runtime-fix --help works."""
    result = run_cli('runtime-fix', '--help')
    assert_help_works(result)
    assert '--family' in result.stdout
    assert 'runtime-fix' in result.stdout


def test_md_update_help():
    """Test md-update --help works."""
    result = run_cli('md-update', '--help')
    assert_help_works(result)
    assert '--family' in result.stdout
    assert '--dry-run' in result.stdout


def test_final_review_help():
    """Test final-review --help works."""
    result = run_cli('final-review', '--help')
    assert_help_works(result)
    assert '--family' in result.stdout
    assert 'final-review' in result.stdout


def test_commit_help():
    """Test commit --help works."""
    result = run_cli('commit', '--help')
    assert_help_works(result)
    assert '--family' in result.stdout
    assert 'commit' in result.stdout


def test_status_help():
    """Test status --help works."""
    result = run_cli('status', '--help')
    assert_help_works(result)
    assert 'status' in result.stdout


def test_run_help():
    """Test run --help works."""
    result = run_cli('run', '--help')
    assert_help_works(result)
    assert '--family' in result.stdout
    assert '--dry-run' in result.stdout
    assert '--max-examples' in result.stdout


def test_list_families_help():
    """Test list-families --help works."""
    result = run_cli('list-families', '--help')
    assert_help_works(result)
    assert 'list-families' in result.stdout


def test_backfill_help():
    """Test backfill --help works."""
    result = run_cli('backfill', '--help')
    assert_help_works(result)
    assert '--family' in result.stdout
    assert 'backfill' in result.stdout


# ============================================================================
# Basic Execution Tests - Verify commands execute without import errors
# ============================================================================


def test_no_command_shows_help():
    """Test that running CLI with no command shows help."""
    result = run_cli()
    # Should return 1 but still show help
    assert result.returncode == 1
    assert_no_import_errors(result)
    assert 'Example Reviewer Pipeline CLI' in result.stdout


def test_list_families_executes():
    """Test list-families command executes without errors."""
    result = run_cli('list-families')
    assert_no_import_errors(result)
    # May succeed or fail depending on config, but should not have import errors
    # Don't assert returncode as it depends on environment


def test_status_executes_without_family():
    """Test status command executes without family argument."""
    result = run_cli('status')
    assert_no_import_errors(result)
    # May succeed or fail, but should not have import errors


def test_run_dry_run_minimal(temp_workspace):
    """Test run command with dry-run and minimal args."""
    result = run_cli(
        'run',
        '--family', 'zip',
        '--dry-run',
        '--max-examples', '1',
        '--workspace-dir', str(temp_workspace),
        '--db-path', str(temp_workspace / 'test.db')
    )
    assert_no_import_errors(result)
    # Command may fail due to missing config/data, but should not have import errors


def test_scan_with_invalid_family(temp_workspace):
    """Test scan with invalid family doesn't cause import errors."""
    result = run_cli(
        'scan',
        '--family', 'nonexistent_family_xyz',
        '--max-files', '1',
        '--workspace-dir', str(temp_workspace),
        '--db-path', str(temp_workspace / 'test.db')
    )
    assert_no_import_errors(result)
    # Should fail gracefully, not with import errors


def test_json_output_flag():
    """Test --json flag doesn't cause import errors."""
    result = run_cli('--json', 'list-families')
    assert_no_import_errors(result)
    # Should execute without import errors


def test_verbose_flag():
    """Test --verbose flag doesn't cause import errors."""
    result = run_cli('--verbose', 'list-families')
    assert_no_import_errors(result)
    # Should execute without import errors


# ============================================================================
# Global Options Tests
# ============================================================================


def test_custom_config_dir():
    """Test --config-dir option doesn't cause import errors."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = run_cli('--config-dir', tmpdir, 'list-families')
        assert_no_import_errors(result)


def test_custom_db_path():
    """Test --db-path option doesn't cause import errors."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / 'test.db'
        result = run_cli('--db-path', str(db_path), 'list-families')
        assert_no_import_errors(result)


def test_custom_workspace_dir():
    """Test --workspace-dir option doesn't cause import errors."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = run_cli('--workspace-dir', tmpdir, 'list-families')
        assert_no_import_errors(result)
