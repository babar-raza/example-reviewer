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
