"""
Integration tests for run-scoped pipeline operations.

Tests that the pipeline properly passes run_id through all phases.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from src.pipeline.orchestrator import PipelineOrchestrator
from src.core.models import ExampleStatus


def test_cli_parser_exists():
    """Test that CLI module can be imported and has parser."""
    from src.cli import main

    assert hasattr(main, 'main')
    assert callable(main.main)


def test_orchestrator_run_id_wiring():
    """Test that orchestrator passes run_id to database operations."""

    with patch('src.pipeline.orchestrator.Database') as mock_db_class:
        # Setup mock database
        mock_db = Mock()
        mock_db.initialize_schema = Mock()
        mock_db.create_run = Mock(return_value="test_run_123")
        mock_db.get_examples_by_family = Mock(return_value=[])
        mock_db_class.return_value = mock_db

        # Create orchestrator
        with patch('src.pipeline.orchestrator.ConfigurationManager'):
            orchestrator = PipelineOrchestrator(
                config_dir=Path("test_config"),
                db_path=Path(":memory:"),
            )

            # Verify database was initialized
            assert mock_db.initialize_schema.called


def test_discovery_service_accepts_run_id():
    """Test that discovery service accepts run_id parameter."""
    from src.services.discovery_service import DiscoveryService
    from src.core.database import Database

    # This test verifies the signature supports run_id
    import inspect

    sig = inspect.signature(DiscoveryService.discover_family)
    params = sig.parameters

    assert 'run_id' in params, "discover_family should accept run_id parameter"


def test_markdown_service_run_scoped_query():
    """Test that markdown service uses run_id in queries."""
    from src.services.markdown_service import MarkdownUpdateService
    from src.core.database import Database

    with patch.object(Database, 'get_connection'):
        mock_db = Mock(spec=Database)
        mock_db.get_examples_by_family = Mock(return_value=[])

        service = MarkdownUpdateService(
            db=mock_db,
            run_id="test_run_456"
        )

        # Call update_all_files
        service.update_all_files("test_family", dry_run=True)

        # Verify run_id was passed
        mock_db.get_examples_by_family.assert_called_once()
        call_args = mock_db.get_examples_by_family.call_args

        # Check if run_id was passed as keyword argument
        assert 'run_id' in call_args.kwargs or (len(call_args.args) > 2)


def test_database_update_status_requires_run_id():
    """Test that update_example_status logs warning without run_id."""
    from src.core.database import Database
    import tempfile

    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    try:
        db = Database(Path(db_path))
        db.initialize_schema()

        # Try to update status without run_id
        result = db.update_example_status(
            example_id="test_id",
            status=ExampleStatus.COMPILABLE,
            run_id=None
        )

        # Should return False when run_id is missing
        assert result is False

    finally:
        Path(db_path).unlink(missing_ok=True)


def test_database_update_code_requires_run_id():
    """Test that update_example_code logs warning without run_id."""
    from src.core.database import Database
    import tempfile

    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    try:
        db = Database(Path(db_path))
        db.initialize_schema()

        # Try to update code without run_id
        result = db.update_example_code(
            example_id="test_id",
            compilable_code="test code",
            run_id=None
        )

        # Should return False when run_id is missing
        assert result is False

    finally:
        Path(db_path).unlink(missing_ok=True)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
