"""Pytest configuration and fixtures for Example Reviewer tests."""

import pytest


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
