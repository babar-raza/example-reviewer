"""Pytest configuration and fixtures for Example Reviewer tests."""

import importlib
import sys
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    import src.core as _core
    import src.services as _services

    sys.modules.setdefault("core", _core)
    sys.modules.setdefault("services", _services)

    for name in (
        "backfill_service",
        "compilation_service",
        "discovery_service",
        "llm_service",
        "markdown_service",
        "runtime_service",
        "telemetry_service",
        "vector_db_service",
    ):
        sys.modules.setdefault(
            f"services.{name}",
            importlib.import_module(f"src.services.{name}"),
        )

    for name in ("config", "database", "models"):
        sys.modules.setdefault(
            f"core.{name}",
            importlib.import_module(f"src.core.{name}"),
        )
except Exception:
    # Optional compatibility aliases; tests will surface errors if needed.
    pass


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


# ============================================================================
# Track 1 Determinism Test Fixtures
# ============================================================================

@pytest.fixture
def mock_llm_service():
    """
    Mock LLMService for unit tests.

    Prevents actual LLM API calls during tests.

    Returns:
        Mock: Mocked LLMService instance
    """
    from unittest.mock import MagicMock
    from src.services.llm_service import LLMService, ProviderCapabilities

    service = MagicMock(spec=LLMService)
    service.is_available.return_value = True
    service.timeout_seconds = 120
    service.seed = 12345
    service.deterministic_mode = True
    service.enforce_timeout = True

    # Mock provider capabilities
    capabilities = ProviderCapabilities(
        seed_supported=True,
        timeout_supported=True,
        detected_at="2026-01-20T10:00:00Z",
    )
    service.get_provider_capabilities.return_value = capabilities

    # Mock LLM response
    from src.services.llm_service import LLMResponse
    mock_response = LLMResponse(
        content="// Fixed code",
        model="gpt-4",
        usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
        finish_reason="stop",
        latency_ms=1000,
    )
    service.fix_compilation_error.return_value = mock_response

    return service


@pytest.fixture
def mock_vector_db():
    """
    Mock VectorDBService for unit tests.

    Prevents actual ChromaDB operations during tests.

    Returns:
        Mock: Mocked VectorDBService instance
    """
    from unittest.mock import MagicMock
    from src.services.vector_db_service import VectorDBService

    service = MagicMock(spec=VectorDBService)
    service.is_available.return_value = True
    service.enabled = True

    # Mock search results (deterministically sorted)
    service.search_similar_examples.return_value = [
        {
            "id": "example1",
            "code": "// Example 1",
            "distance": 0.10,
            "metadata": {"example_key": "key1", "file_path": "a.md"},
        },
        {
            "id": "example2",
            "code": "// Example 2",
            "distance": 0.15,
            "metadata": {"example_key": "key2", "file_path": "b.md"},
        },
    ]

    return service


@pytest.fixture
def mock_database(tmp_path):
    """
    In-memory SQLite database for unit tests.

    Provides isolated database for testing without polluting main DB.

    Returns:
        Database: In-memory database instance
    """
    from src.core.database import Database

    db = Database(db_path=Path(":memory:"))
    db.initialize_schema()

    return db


@pytest.fixture
def temp_config():
    """
    Temporary config directory with valid Track 1 configs.

    Returns:
        Path: Temporary config directory
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = Path(tmpdir) / "config"
        config_dir.mkdir()

        families_dir = config_dir / "families"
        families_dir.mkdir()

        # Create valid global.json with Track 1 fields
        global_config = {
            "llm": {
                "provider": "openai",
                "model": "gpt-4",
                "temperature": 0.0,
                "max_retries": 3,
                "retry_backoff_seconds": 5,
                "timeout_seconds": 120,
                "seed": 12345,
                "deterministic_mode": True,
                "enforce_timeout": True,
            },
            "vector_db": {
                "enabled": True,
                "provider": "chromadb",
                "embedding_model": "all-MiniLM-L6-v2",
                "require_on_startup": False,
                "deterministic_search": True,
                "embedding_device": "cpu",
                "drift_tolerance": 0.02,
            },
            "final_review": {
                "enabled": True,
                "provider": "anthropic",
                "model": "claude-3-5-sonnet-latest",
                "timeout_seconds": 30,
                "enforce_model": True,
            },
            "timeouts": {
                "llm_call_seconds": 120,
                "code_execution_seconds": 30,
                "per_example_seconds": 300,
                "per_phase_seconds": 1800,
                "hard_run_timeout_seconds": 2400,
                "allow_timeout_override": False,
            },
            "database_path": "./data/test.db",
            "artifact_store_path": "./artifacts",
        }

        (config_dir / "global.json").write_text(json.dumps(global_config, indent=2))

        # Create minimal family config
        family_config = {
            "family": "test_family",
            "display_name": "Test Family",
            "content_roots": ["./test-content"],
        }

        (families_dir / "test_family.json").write_text(json.dumps(family_config, indent=2))

        yield config_dir
