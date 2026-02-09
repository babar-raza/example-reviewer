"""
Unit tests for FamilyServiceRegistry (TASK-1B).

Tests cover:
- Lazy initialization with per-family caching
- Service isolation between families
- Error handling for missing family configs
- Correct parameter passing to services
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

from src.pipeline.family_service_registry import FamilyServiceRegistry
from src.core.config import ConfigurationManager, GlobalConfig, FamilyConfig, SubstitutionConfig
from src.services.api_catalog_service import APICatalogService
from src.services.learned_patterns_service import LearnedPatternsService
from src.services.example_substitution_service import ExampleSubstitutionService


@pytest.fixture
def mock_config_manager():
    """Create a mock ConfigurationManager."""
    manager = Mock(spec=ConfigurationManager)

    # Mock load_family_config to succeed for 'zip' and 'words'
    def mock_load_family(family: str):
        if family in ['zip', 'words']:
            config = Mock(spec=FamilyConfig)
            config.family = family
            return config
        raise FileNotFoundError(f"Family config not found: config/families/{family}.json")

    manager.load_family_config.side_effect = mock_load_family

    # Mock load_global_config
    global_config = Mock(spec=GlobalConfig)
    substitution_config = Mock(spec=SubstitutionConfig)
    substitution_config.same_context_only = False
    global_config.substitution = substitution_config
    manager.load_global_config.return_value = global_config

    return manager


@pytest.fixture
def registry(mock_config_manager, tmp_path):
    """Create a FamilyServiceRegistry with mocked dependencies."""
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir()
    return FamilyServiceRegistry(mock_config_manager, artifacts_dir)


def test_get_api_catalog_caches_per_family(registry):
    """Test that API catalog is cached per family."""
    with patch('src.pipeline.family_service_registry.APICatalogService') as mock_catalog:
        # Configure mock to return different instances
        mock_instance_zip = Mock(spec=APICatalogService)
        mock_instance_words = Mock(spec=APICatalogService)
        mock_catalog.side_effect = [mock_instance_zip, mock_instance_words]

        # First call for 'zip'
        catalog1 = registry.get_api_catalog('zip')
        assert catalog1 is mock_instance_zip

        # Second call for 'zip' (should return cached)
        catalog2 = registry.get_api_catalog('zip')
        assert catalog2 is mock_instance_zip
        assert catalog1 is catalog2  # Same instance

        # Call for 'words' (should create new instance)
        catalog3 = registry.get_api_catalog('words')
        assert catalog3 is mock_instance_words
        assert catalog3 is not catalog1  # Different instance

        # Verify APICatalogService was called twice (once per family)
        assert mock_catalog.call_count == 2


def test_get_substitution_service_uses_correct_backfill_dir(registry, tmp_path):
    """Test that substitution service uses correct backfill directory path."""
    with patch('src.pipeline.family_service_registry.ExampleSubstitutionService') as mock_sub:
        mock_instance = Mock(spec=ExampleSubstitutionService)
        mock_sub.return_value = mock_instance

        # Get substitution service for 'zip'
        service = registry.get_substitution_service('zip')

        # Verify ExampleSubstitutionService was called with correct backfill_dir
        expected_backfill_dir = tmp_path / "artifacts" / "backfill" / "zip"
        mock_sub.assert_called_once()
        call_args = mock_sub.call_args
        assert call_args[1]['backfill_dir'] == expected_backfill_dir
        assert call_args[1]['same_context_only'] is False


def test_missing_family_raises_clear_error(registry):
    """Test that attempting to get service for non-existent family raises ValueError."""
    with pytest.raises(ValueError) as exc_info:
        registry.get_api_catalog('invalid_family')

    assert "Family 'invalid_family' not found" in str(exc_info.value)
    assert "config/families/invalid_family.json" in str(exc_info.value)


def test_multiple_families_isolated(registry):
    """Test that services for different families are isolated."""
    with patch('src.pipeline.family_service_registry.APICatalogService') as mock_catalog:
        mock_zip = Mock(spec=APICatalogService)
        mock_words = Mock(spec=APICatalogService)
        mock_catalog.side_effect = [mock_zip, mock_words]

        # Get services for both families
        zip_catalog = registry.get_api_catalog('zip')
        words_catalog = registry.get_api_catalog('words')

        # Verify isolation
        assert zip_catalog is not words_catalog
        assert 'zip' in registry._cache
        assert 'words' in registry._cache
        assert registry._cache['zip']['api_catalog'] is mock_zip
        assert registry._cache['words']['api_catalog'] is mock_words


def test_cache_hit_returns_same_instance(registry):
    """Test that cache hit returns the exact same object instance."""
    with patch('src.pipeline.family_service_registry.APICatalogService') as mock_catalog:
        mock_instance = Mock(spec=APICatalogService)
        mock_catalog.return_value = mock_instance

        # Call multiple times
        service1 = registry.get_api_catalog('zip')
        service2 = registry.get_api_catalog('zip')
        service3 = registry.get_api_catalog('zip')

        # All should be the same object
        assert service1 is service2
        assert service2 is service3

        # APICatalogService should only be instantiated once
        assert mock_catalog.call_count == 1


def test_namespace_map_returns_catalog_data(registry):
    """Test that get_namespace_map returns data from APICatalogService."""
    with patch('src.pipeline.family_service_registry.APICatalogService') as mock_catalog_class:
        # Create mock catalog instance with get_using_directive_map method
        mock_catalog = Mock(spec=APICatalogService)
        expected_map = {'ZipArchive': 'using Aspose.Zip;', 'Archive': 'using Aspose.Zip;'}
        mock_catalog.get_using_directive_map.return_value = expected_map
        mock_catalog_class.return_value = mock_catalog

        # Get namespace map
        namespace_map = registry.get_namespace_map('zip')

        # Verify it returns the catalog's data
        assert namespace_map == expected_map
        mock_catalog.get_using_directive_map.assert_called_once()


def test_using_directives_returns_catalog_data(registry):
    """Test that get_using_directives returns data from APICatalogService."""
    with patch('src.pipeline.family_service_registry.APICatalogService') as mock_catalog_class:
        mock_catalog = Mock(spec=APICatalogService)
        expected_directives = {'ZipArchive': 'using Aspose.Zip;'}
        mock_catalog.get_using_directive_map.return_value = expected_directives
        mock_catalog_class.return_value = mock_catalog

        # Get using directives
        directives = registry.get_using_directives('zip')

        # Verify it returns the catalog's data
        assert directives == expected_directives


def test_learned_patterns_with_family_config(registry):
    """Test that learned patterns service is created with correct family."""
    with patch('src.pipeline.family_service_registry.LearnedPatternsService') as mock_patterns:
        mock_instance = Mock(spec=LearnedPatternsService)
        mock_patterns.return_value = mock_instance

        # Get learned patterns service
        service = registry.get_learned_patterns('zip')

        # Verify LearnedPatternsService was called with family='zip'
        mock_patterns.assert_called_once_with('zip')
        assert service is mock_instance


def test_api_reference_returns_none(registry):
    """Test that get_api_reference returns None (Phase 3 placeholder)."""
    result = registry.get_api_reference('zip')
    assert result is None


def test_substitution_service_same_context_flag(mock_config_manager, tmp_path):
    """Test that substitution service receives same_context_only flag from global config."""
    # Configure global config with same_context_only=True
    global_config = Mock(spec=GlobalConfig)
    substitution_config = Mock(spec=SubstitutionConfig)
    substitution_config.same_context_only = True
    global_config.substitution = substitution_config
    mock_config_manager.load_global_config.return_value = global_config

    # Create registry
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir()
    reg = FamilyServiceRegistry(mock_config_manager, artifacts_dir)

    with patch('src.pipeline.family_service_registry.ExampleSubstitutionService') as mock_sub:
        mock_instance = Mock(spec=ExampleSubstitutionService)
        mock_sub.return_value = mock_instance

        # Get substitution service
        service = reg.get_substitution_service('zip')

        # Verify same_context_only=True was passed
        call_args = mock_sub.call_args
        assert call_args[1]['same_context_only'] is True


def test_clear_cache_specific_family(registry):
    """Test clearing cache for a specific family."""
    with patch('src.pipeline.family_service_registry.APICatalogService') as mock_catalog:
        mock_zip = Mock(spec=APICatalogService)
        mock_words = Mock(spec=APICatalogService)
        mock_catalog.side_effect = [mock_zip, mock_words]

        # Cache services for both families
        registry.get_api_catalog('zip')
        registry.get_api_catalog('words')

        assert 'zip' in registry._cache
        assert 'words' in registry._cache

        # Clear only 'zip'
        registry.clear_cache('zip')

        assert 'zip' not in registry._cache
        assert 'words' in registry._cache


def test_clear_cache_all_families(registry):
    """Test clearing cache for all families."""
    with patch('src.pipeline.family_service_registry.APICatalogService') as mock_catalog:
        mock_zip = Mock(spec=APICatalogService)
        mock_words = Mock(spec=APICatalogService)
        mock_catalog.side_effect = [mock_zip, mock_words]

        # Cache services for both families
        registry.get_api_catalog('zip')
        registry.get_api_catalog('words')

        assert len(registry._cache) == 2

        # Clear all
        registry.clear_cache()

        assert len(registry._cache) == 0


def test_get_cached_families(registry):
    """Test getting list of cached families."""
    with patch('src.pipeline.family_service_registry.APICatalogService') as mock_catalog:
        mock_catalog.return_value = Mock(spec=APICatalogService)

        # Initially no cached families
        assert registry.get_cached_families() == []

        # Cache 'zip'
        registry.get_api_catalog('zip')
        assert registry.get_cached_families() == ['zip']

        # Cache 'words'
        registry.get_api_catalog('words')
        cached = registry.get_cached_families()
        assert 'zip' in cached
        assert 'words' in cached
        assert len(cached) == 2


def test_multiple_service_types_same_family(registry):
    """Test that different service types for same family are cached separately."""
    with patch('src.pipeline.family_service_registry.APICatalogService') as mock_catalog, \
         patch('src.pipeline.family_service_registry.LearnedPatternsService') as mock_patterns, \
         patch('src.pipeline.family_service_registry.ExampleSubstitutionService') as mock_sub:

        mock_catalog_inst = Mock(spec=APICatalogService)
        mock_patterns_inst = Mock(spec=LearnedPatternsService)
        mock_sub_inst = Mock(spec=ExampleSubstitutionService)

        mock_catalog.return_value = mock_catalog_inst
        mock_patterns.return_value = mock_patterns_inst
        mock_sub.return_value = mock_sub_inst

        # Get different services for 'zip'
        catalog = registry.get_api_catalog('zip')
        patterns = registry.get_learned_patterns('zip')
        substitution = registry.get_substitution_service('zip')

        # All should be different instances
        assert catalog is not patterns
        assert patterns is not substitution
        assert catalog is not substitution

        # All should be cached under 'zip'
        assert 'zip' in registry._cache
        assert 'api_catalog' in registry._cache['zip']
        assert 'learned_patterns' in registry._cache['zip']
        assert 'substitution' in registry._cache['zip']
