"""
FamilyServiceRegistry — Central registry for family-aware service instances.

Provides lazy initialization and caching for family-specific services:
- API Catalog Service (type->namespace mappings)
- Learned Patterns Service (auto-learned fix patterns)
- Example Substitution Service (example repository integration)

This registry eliminates hardcoded family references (e.g., APICatalogService("zip"))
across the codebase, enabling true multi-family extensibility.

Part of WS-2 Service Refactoring (TASK-1B).
"""

import logging
from pathlib import Path
from typing import Dict, Optional, Any

from src.core.config import ConfigurationManager
from src.services.api_catalog_service import APICatalogService
from src.services.fixture_resolver_service import FixtureResolverService
from src.services.learned_patterns_service import LearnedPatternsService
from src.services.example_substitution_service import ExampleSubstitutionService
from src.services.semantic_signature_service import SemanticSignatureService
from src.services.family_drift_validators.base import FamilyDriftValidator

logger = logging.getLogger(__name__)


class FamilyServiceRegistry:
    """Central registry for family-aware service instances with lazy initialization."""

    def __init__(self, config_manager: ConfigurationManager, artifacts_dir: Path):
        """
        Initialize the service registry.

        Args:
            config_manager: ConfigurationManager instance for loading family configs
            artifacts_dir: Path to artifacts directory (for backfill, test-data, etc.)
        """
        self._config_manager = config_manager
        self._artifacts_dir = Path(artifacts_dir)
        self._cache: Dict[str, Dict[str, Any]] = {}  # {family: {service_name: instance}}

    def get_api_catalog(self, family: str) -> APICatalogService:
        """
        Get API catalog service for family.

        Loads type->namespace mappings from config/families/{family}_api_catalog.json.

        Args:
            family: Product family identifier (e.g., 'zip', 'words')

        Returns:
            APICatalogService instance for the family
        """
        return self._get_cached('api_catalog', family, self._create_api_catalog)

    def get_namespace_map(self, family: str) -> Dict[str, str]:
        """
        Get type->namespace mapping from API catalog.

        Args:
            family: Product family identifier

        Returns:
            Dictionary mapping type names to namespaces (e.g., "Archive" -> "Aspose.Zip")
        """
        catalog = self.get_api_catalog(family)
        namespace_map = catalog.get_namespace_map()  # FIX: Use get_namespace_map() not get_using_directive_map()
        logger.info(f"FamilyServiceRegistry.get_namespace_map({family}): returning {len(namespace_map)} entries")
        if namespace_map:
            sample = list(namespace_map.items())[:3]
            logger.info(f"FamilyServiceRegistry.get_namespace_map({family}): sample entries: {sample}")
        else:
            logger.warning(f"FamilyServiceRegistry.get_namespace_map({family}): EMPTY map returned!")
        return namespace_map

    def get_using_directives(self, family: str) -> Dict[str, str]:
        """
        Get type->using directive mapping from API catalog.

        Args:
            family: Product family identifier

        Returns:
            Dictionary mapping type names to using directive strings
        """
        catalog = self.get_api_catalog(family)
        return catalog.get_using_directive_map()

    def get_api_reference(self, family: str) -> Optional[Any]:
        """
        Get API reference documentation service.

        Deprecated: APIReferenceService and APIContextService have been removed (TASK-DLL-03).
        This method is kept for interface compatibility; it always returns None.

        Args:
            family: Product family identifier

        Returns:
            None (service removed)
        """
        return None

    def get_learned_patterns(self, family: str) -> LearnedPatternsService:
        """
        Get learned patterns service with family-specific transforms.

        Queries learned_patterns table from data/api_catalog.db for auto-learned
        fix patterns (regex, using directives, code transforms, LLM prompts).

        Args:
            family: Product family identifier

        Returns:
            LearnedPatternsService instance for the family
        """
        return self._get_cached('learned_patterns', family, self._create_learned_patterns)

    def get_substitution_service(self, family: str) -> ExampleSubstitutionService:
        """
        Get example substitution service for artifacts/backfill/{family}/ directory.

        Provides automatic substitution of failing examples with verified examples
        from the example repository when specific compile error patterns are detected.

        Args:
            family: Product family identifier

        Returns:
            ExampleSubstitutionService instance for the family
        """
        return self._get_cached('substitution', family, self._create_substitution)

    def get_fixture_resolver(self, family: str) -> Optional[FixtureResolverService]:
        """
        Get fixture resolver service for family.

        Returns None if fixture resolution is disabled for this family
        (fixture_resolver.enabled = false or not configured).

        Args:
            family: Product family identifier

        Returns:
            FixtureResolverService instance, or None if disabled
        """
        try:
            family_config = self._config_manager.load_family_config(family)
        except FileNotFoundError:
            return None

        if not family_config.fixture_resolver or not family_config.fixture_resolver.enabled:
            return None

        return self._get_cached('fixture_resolver', family, self._create_fixture_resolver)

    def _get_cached(self, service_name: str, family: str, factory_fn) -> Any:
        """
        Generic caching pattern: check cache → create if missing → cache → return.

        Args:
            service_name: Name of the service (for cache key)
            family: Product family identifier
            factory_fn: Factory function to create the service (takes family as arg)

        Returns:
            Cached or newly created service instance
        """
        # Ensure family cache exists
        if family not in self._cache:
            self._cache[family] = {}

        # Check if service already cached
        if service_name not in self._cache[family]:
            logger.debug(f"Creating {service_name} for family '{family}'")
            self._cache[family][service_name] = factory_fn(family)

        return self._cache[family][service_name]

    def _create_api_catalog(self, family: str) -> APICatalogService:
        """
        Factory: Create APICatalogService for family.

        Args:
            family: Product family identifier

        Returns:
            APICatalogService instance
        """
        # Validate family config exists (raises FileNotFoundError if missing)
        try:
            self._config_manager.load_family_config(family)
        except FileNotFoundError:
            raise ValueError(
                f"Family '{family}' not found. "
                f"Create config/families/{family}.json first."
            )

        # APICatalogService handles missing catalog file gracefully (logs warning)
        return APICatalogService(family)

    def _create_learned_patterns(self, family: str) -> LearnedPatternsService:
        """
        Factory: Create LearnedPatternsService for family.

        Args:
            family: Product family identifier

        Returns:
            LearnedPatternsService instance
        """
        # Validate family config exists
        try:
            self._config_manager.load_family_config(family)
        except FileNotFoundError:
            raise ValueError(
                f"Family '{family}' not found. "
                f"Create config/families/{family}.json first."
            )

        # LearnedPatternsService uses default db_path (data/api_catalog.db)
        # Will raise FileNotFoundError if db doesn't exist (expected behavior)
        # Pass API catalog for LLM context
        catalog = self.get_api_catalog(family)
        return LearnedPatternsService(family, catalog=catalog)

    def _create_substitution(self, family: str) -> ExampleSubstitutionService:
        """
        Factory: Create ExampleSubstitutionService for family.

        Args:
            family: Product family identifier

        Returns:
            ExampleSubstitutionService instance
        """
        # Load family config to validate it exists
        try:
            self._config_manager.load_family_config(family)
        except FileNotFoundError:
            raise ValueError(
                f"Family '{family}' not found. "
                f"Create config/families/{family}.json first."
            )

        # Load global config to get same_context_only flag
        global_config = self._config_manager.load_global_config()
        same_context_only = global_config.substitution.same_context_only

        # Construct backfill directory path
        backfill_dir = self._artifacts_dir / "backfill" / family

        # ExampleSubstitutionService handles missing backfill directory gracefully
        return ExampleSubstitutionService(
            backfill_dir=backfill_dir,
            same_context_only=same_context_only
        )

    def _create_fixture_resolver(self, family: str) -> FixtureResolverService:
        """
        Factory: Create FixtureResolverService for family.

        Args:
            family: Product family identifier

        Returns:
            FixtureResolverService instance
        """
        family_config = self._config_manager.load_family_config(family)
        fr_config = family_config.fixture_resolver

        # Determine test-data directory
        test_data_dir = self._artifacts_dir / "backfill" / family / "test-data"

        # Registry path from config or default
        registry_path = None
        if fr_config and fr_config.registry_path:
            registry_path = Path(fr_config.registry_path)

        # Resolve example repo test data path from cache (enables Tier 2.5 resolution)
        example_repo_test_data_dir = None
        if family_config.example_repo and family_config.example_repo.test_data_path:
            repo_url = family_config.example_repo.url
            repo_name = repo_url.rstrip('/').split('/')[-1]
            cache_test_data = (
                Path(".cache/backfill") / family / repo_name
                / family_config.example_repo.test_data_path
            )
            if cache_test_data.exists():
                example_repo_test_data_dir = cache_test_data

        return FixtureResolverService(
            family=family,
            test_data_dir=test_data_dir,
            file_aliases=family_config.runtime_validation.file_aliases,
            max_generations_per_run=fr_config.max_generations_per_run if fr_config else 50,
            registry_path=registry_path,
            skip_output_patterns=fr_config.skip_output_patterns if fr_config else None,
            example_repo_test_data_dir=example_repo_test_data_dir,
        )

    def get_semantic_signature_service(self, family: str) -> SemanticSignatureService:
        """
        Get semantic signature service for family.

        Args:
            family: Product family identifier

        Returns:
            SemanticSignatureService instance for the family
        """
        return self._get_cached('semantic_signature', family, self._create_semantic_signature)

    def get_drift_validator(self, family: str) -> Optional[FamilyDriftValidator]:
        """
        Get family-specific drift validator if one exists.

        Args:
            family: Product family identifier

        Returns:
            FamilyDriftValidator instance, or None if no validator for this family
        """
        try:
            return self._get_cached('drift_validator', family, self._create_drift_validator)
        except ValueError:
            return None

    def _create_semantic_signature(self, family: str) -> SemanticSignatureService:
        """Factory: Create SemanticSignatureService for family."""
        catalog = self.get_api_catalog(family)
        return SemanticSignatureService(family=family, api_catalog=catalog)

    def _create_drift_validator(self, family: str) -> FamilyDriftValidator:
        """Factory: Create family-specific drift validator."""
        validator_map = {
            'barcode': 'src.services.family_drift_validators.barcode_validator.BarCodeDriftValidator',
        }
        fqn = validator_map.get(family)
        if not fqn:
            raise ValueError(f"No drift validator for family '{family}'")

        module_path, class_name = fqn.rsplit('.', 1)
        import importlib
        mod = importlib.import_module(module_path)
        cls = getattr(mod, class_name)
        catalog = self.get_api_catalog(family)
        return cls(catalog=catalog)

    def clear_cache(self, family: Optional[str] = None) -> None:
        """
        Clear cached services.

        Useful for testing or when family configs are updated at runtime.

        Args:
            family: Family to clear (None = clear all families)
        """
        if family:
            if family in self._cache:
                logger.debug(f"Clearing cache for family '{family}'")
                del self._cache[family]
        else:
            logger.debug("Clearing entire service registry cache")
            self._cache.clear()

    def get_cached_families(self) -> list[str]:
        """
        Get list of families with cached services.

        Returns:
            List of family identifiers with cached services
        """
        return list(self._cache.keys())
