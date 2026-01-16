"""Pytest configuration and fixtures for Example Reviewer tests."""

import pytest
from pathlib import Path


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--integration",
        action="store_true",
        default=False,
        help="Run integration tests (requires GitHub API access)"
    )


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers",
        "integration: Integration tests requiring real GitHub API access"
    )


def pytest_ignore_collect(collection_path, path, config):
    """
    Prevent collection of integration test file unless --integration flag is passed.

    This prevents module-level import errors from breaking default pytest runs.
    Integration tests may have dependencies (like fixtures.gist_fixtures) that
    are only needed when actually running integration tests.
    """
    # Use collection_path (preferred in newer pytest) with fallback to path
    file_path = collection_path if collection_path is not None else path

    if file_path.name == "test_gist_integration.py":
        if not config.getoption("--integration", default=False):
            return True  # Ignore this file during collection

    return False  # Collect normally


def pytest_collection_modifyitems(config, items):
    """Skip integration tests by default unless --integration flag passed."""
    if config.getoption("--integration"):
        # --integration flag passed: run all tests including integration
        return

    # Default behavior: skip integration tests
    skip_integration = pytest.mark.skip(reason="Integration tests require --integration flag")
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip_integration)


# ============================================================================
# CLI Test Fixtures
# ============================================================================


import json
import tempfile


@pytest.fixture
def temp_workspace():
    """
    Create temporary workspace for CLI tests.

    Provides isolated temporary directory with minimal config structure
    for testing CLI commands without polluting the main workspace.

    Yields:
        Path: Temporary workspace directory path
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)

        # Create minimal directory structure
        (workspace / 'config').mkdir()
        (workspace / 'config' / 'families').mkdir()
        (workspace / 'data').mkdir()
        (workspace / 'workspace').mkdir()

        # Create minimal global config
        global_config = {
            'llm_provider': 'openai',
            'default_model': 'gpt-4',
            'retry_attempts': 3,
            'timeout': 300
        }
        (workspace / 'config' / 'global.json').write_text(
            json.dumps(global_config, indent=2)
        )

        # Create minimal family config for testing
        family_config = {
            'family_id': 'test_family',
            'product_name': 'Test Product',
            'language': 'csharp',
            'runtime': 'dotnet',
            'content_paths': []
        }
        (workspace / 'config' / 'families' / 'test_family.json').write_text(
            json.dumps(family_config, indent=2)
        )

        yield workspace
        # Cleanup handled by TemporaryDirectory context manager


@pytest.fixture
def cli_env(temp_workspace):
    """
    Environment variables for CLI testing.

    Args:
        temp_workspace: Temporary workspace fixture

    Returns:
        dict: Environment variables for subprocess calls
    """
    import os
    env = os.environ.copy()
    env['EXAMPLE_REVIEWER_CONFIG'] = str(temp_workspace / 'config')
    env['EXAMPLE_REVIEWER_DB'] = str(temp_workspace / 'data' / 'test.db')
    env['EXAMPLE_REVIEWER_WORKSPACE'] = str(temp_workspace / 'workspace')
    return env
