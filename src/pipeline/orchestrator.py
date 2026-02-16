"""
Pipeline Orchestrator for Example Reviewer.
Coordinates all pipeline phases as defined in the spec.
"""

import json
import logging
import os
import re
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime

from ..core.models import (
    ExampleRecord, ExampleStatus, ScanScope, ScanMode,
    ReviewResult, ReviewIssue, IssueType, IssueSeverity,
    SourceType
)
from ..core.database import Database
from ..core.config import ConfigurationManager, FamilyConfig, GlobalConfig
from ..core.telemetry import track_phase_timing, export_run_telemetry, log_resource_decision
from ..services.discovery_service import DiscoveryService
from ..services.resource_detection_service import ResourceDetectionService
from ..services.compilation_service import CompilationService, CompileResult, check_dotnet_available
from ..services.runtime_service import RuntimeService
from ..services.llm_service import LLMService, LLMServiceFactory
from ..services.markdown_service import MarkdownUpdateService
from ..services.vector_db_service import VectorDBService
from ..services.telemetry_service import TelemetryService
from ..services.example_substitution_service import ExampleSubstitutionService, apply_quick_fixes
from ..services.semantic_microfixes import apply_semantic_microfixes
from .failure_tracker import track_infra_missing_test_data, track_failure, track_compile_failure
from ..core.path_guard import is_read_only_path
from .escalation_classifier import classify_escalation_reason, should_escalate_to_review
from ..core.models import FailureCategory, FailureResolution
from .family_service_registry import FamilyServiceRegistry

try:
    from .context_drift_validator import ContextDriftValidator
except ImportError:
    ContextDriftValidator = None

try:
    from ..services.context_harness_service import ContextHarnessService
except ImportError:
    ContextHarnessService = None

try:
    from ..services.learned_patterns_service import LearnedPatternsService, extract_error_signature, extract_all_error_signatures
except ImportError:
    LearnedPatternsService = None
    extract_error_signature = None
    extract_all_error_signatures = None

logger = logging.getLogger(__name__)


def resolve_test_data_path(family: str, family_config: FamilyConfig) -> Optional[Path]:
    """
    Resolve the actual test data path for a family.

    Priority order (Phase-2 policy: prefer backfill, then local_path):
    1. If artifacts/backfill/<family>/test-data exists → use it (PREFERRED for generated fixtures)
    2. Else if family_config.test_data.local_path exists → use it (read-only reference data)
    3. Else None

    Note: test-data/ paths are read-only (protected from writes) but can still be
    used as a source for reading test data files during runtime verification.

    Args:
        family: Family identifier
        family_config: Family configuration

    Returns:
        Path to test data or None if not available
    """
    # Priority 1: backfill artifacts directory (PREFERRED for Phase-2)
    backfill_path = Path("artifacts/backfill") / family / "test-data"
    if backfill_path.exists():
        logger.debug(f"Using test data from backfill artifacts: {backfill_path}")
        return backfill_path

    # Priority 2: local_path if it exists (read-only is OK for reading)
    if family_config.test_data.local_path:
        local_path = Path(family_config.test_data.local_path)
        if local_path.exists():
            logger.debug(f"Using test data from configured local_path: {local_path}")
            return local_path

    # No test data available
    logger.debug(f"No test data available for family: {family}")
    return None


class PipelineOrchestrator:
    """
    Main orchestrator for the Example Reviewer Pipeline.
    
    Implements the full pipeline from the spec:
    - Phase A: Discovery and Extraction
    - Phase B: Compilation Verification Loop
    - Phase C: Runtime Verification Loop  
    - Phase D: Markdown Update
    - Phase E: Final LLM Review
    - Phase F: Persist, Telemetry, Commit
    """
    
    def __init__(
        self,
        config_dir: Optional[Path] = None,
        db_path: Optional[Path] = None,
        prod_db_path: Optional[Path] = None,
        workspace_dir: Optional[Path] = None,
        artifacts_dir: Optional[Path] = None,
        cli_overrides: Optional[Dict[str, Any]] = None,
        use_workspace_copy: bool = False,
        sqlite_config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize pipeline orchestrator.

        Args:
            config_dir: Directory containing family configs
            db_path: Path to SQLite database
            prod_db_path: Path to production database (optional, enables dual-database mode)
            workspace_dir: Working directory for compilation/runtime
            artifacts_dir: Directory for storing artifacts
            cli_overrides: CLI override dictionary for config hash computation
            use_workspace_copy: Enable workspace copy mode (for test-content/ writes)
            sqlite_config: SQLite configuration (busy_timeout_ms, wal_enabled)
        """
        self.config_dir = config_dir or Path("config/families")
        self.db_path = db_path or Path("data/example_reviewer.db")
        self.workspace_dir = workspace_dir or Path("workspace")
        self.artifacts_dir = artifacts_dir or Path("artifacts")
        self.cli_overrides = cli_overrides or {}
        self.use_workspace_copy = use_workspace_copy
        self.sqlite_config = sqlite_config or {}

        # Create directories
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

        # Initialize components
        self.config_manager = ConfigurationManager(self.config_dir)

        # Load global config to check for production DB path
        global_config = self.config_manager.load_global_config()

        # Determine production DB path: CLI override takes precedence over config
        production_db_path = prod_db_path
        if production_db_path is None and hasattr(global_config, 'database') and global_config.database.production_path:
            production_db_path = Path(global_config.database.production_path)

        # Initialize database with SQLite configuration (Task 2A, 2B)
        self.db = Database(
            db_path=self.db_path,
            production_db_path=production_db_path,
            busy_timeout_ms=self.sqlite_config.get('busy_timeout_ms', 120000),
            wal_enabled=self.sqlite_config.get('wal_enabled', True),
        )
        self.db.initialize_schema()

        # Initialize production DB schema if configured
        if self.db.production_db_path:
            try:
                # Create a temporary Database instance pointing to production DB
                # This allows us to reuse the initialize_schema() method
                prod_db_temp = Database(
                    db_path=self.db.production_db_path,
                    busy_timeout_ms=self.sqlite_config.get('busy_timeout_ms', 120000),
                    wal_enabled=self.sqlite_config.get('wal_enabled', True),
                )
                prod_db_temp.initialize_schema()
                logger.info(f"Production database schema initialized: {self.db.production_db_path}")
            except Exception as e:
                logger.warning(f"Could not initialize production DB schema: {e}")

        # Initialize family service registry (WS-2 TASK-1C)
        self.registry = FamilyServiceRegistry(self.config_manager, self.artifacts_dir)

        # Services (initialized lazily)
        self._llm_service: Optional[LLMService] = None
        self._final_review_llm_service: Optional[LLMService] = None  # Separate LLM for final review
        self._discovery_service: Optional[DiscoveryService] = None
        # Note: _compilation_service and _runtime_service are now family-aware factories
        # Use get_compilation_service(family) and get_runtime_service(family) instead
        self._markdown_service: Optional[MarkdownUpdateService] = None
        self._vector_db_service: Optional[VectorDBService] = None
        self._resource_detection_service: Optional[ResourceDetectionService] = None
        self._telemetry_service: Optional[TelemetryService] = None
        # Note: _substitution_service removed - use self.registry.get_substitution_service(family)
        self._context_drift_validator: Optional['ContextDriftValidator'] = None
        self._context_harness_service: Optional['ContextHarnessService'] = None

        # Track examples that received LLM fixes (for final review filtering)
        self._llm_fixed_example_ids: set = set()

        # Learned patterns service cache (per family)
        self._learned_patterns_service_cache: Dict[str, Optional['LearnedPatternsService']] = {}

        # VectorDB and DriftDetector startup decision (Track 1: C.2)
        # Make a single decision at startup, never change mid-run
        self._drift_detector: Optional['DriftDetector'] = None
        self._drift_enabled: bool = False
        self._vector_db_startup_decision: Dict[str, Any] = {}
        self._initialize_vector_db_and_drift()

        # LLM telemetry accumulator (flushed to metrics_json at run completion)
        self._llm_metrics: Dict[str, Any] = {
            'total_calls': 0,
            'total_prompt_tokens': 0,
            'total_completion_tokens': 0,
            'total_tokens': 0,
            'total_latency_ms': 0,
            'calls_by_context': {},
            'failures': 0,
            'models_used': set(),
        }
    
    @property
    def llm_service(self) -> LLMService:
        """Get or initialize LLM service."""
        if self._llm_service is None:
            global_config = self.config_manager.load_global_config()

            # Apply CLI overrides to LLM config
            llm_config_dict = {
                'provider': global_config.llm.provider,
                'model': global_config.llm.model,
                'temperature': global_config.llm.temperature,
                'max_retries': global_config.llm.max_retries,
                'retry_backoff_seconds': global_config.llm.retry_backoff_seconds,
                'timeout_seconds': global_config.llm.timeout_seconds,
                'seed': global_config.llm.seed,
                'deterministic_mode': global_config.llm.deterministic_mode,
                'enforce_timeout': global_config.llm.enforce_timeout,
                'api_key_env_var': global_config.llm.api_key_env_var,
                'base_url': global_config.llm.base_url,
            }

            # Override with CLI values if present
            if 'llm' in self.cli_overrides:
                for key, value in self.cli_overrides['llm'].items():
                    llm_config_dict[key] = value

            # Resolve API key: config specifies which env var holds the key
            _api_key_env = llm_config_dict.get('api_key_env_var')
            _api_key = os.getenv(_api_key_env) if _api_key_env else None

            self._llm_service = LLMService(
                provider=llm_config_dict['provider'],
                model=llm_config_dict['model'],
                api_key=_api_key,
                base_url=llm_config_dict.get('base_url'),
                temperature=llm_config_dict['temperature'],
                max_retries=llm_config_dict['max_retries'],
                retry_backoff_seconds=llm_config_dict['retry_backoff_seconds'],
                timeout_seconds=llm_config_dict['timeout_seconds'],
                seed=llm_config_dict['seed'],
                deterministic_mode=llm_config_dict['deterministic_mode'],
                enforce_timeout=llm_config_dict['enforce_timeout'],
            )
            # Wire model routing for fallback support
            if global_config.model_routing.enabled:
                self._llm_service.set_routing_config(global_config.model_routing.model_dump())

            # Preflight check: verify endpoint availability
            preflight = self._llm_service.preflight_check()
            primary_status = "OK" if preflight["primary"]["available"] else f"UNAVAILABLE ({preflight['primary']['error']})"
            fallback_status = "OK" if preflight["fallback"]["available"] else f"UNAVAILABLE ({preflight['fallback'].get('error', 'not configured')})"
            logger.info(
                f"LLM preflight: primary={primary_status} ({preflight['primary']['base_url']}), "
                f"fallback={fallback_status} ({preflight['fallback'].get('base_url', 'N/A')})"
            )
            if not preflight["primary"]["available"] and not preflight["fallback"]["available"]:
                logger.error("Neither primary nor fallback LLM endpoint is available!")

            # Detect provider capabilities on startup (Track 1: Agent F)
            if self._llm_service.is_available():
                capabilities = self._llm_service.get_provider_capabilities()
                logger.info(
                    f"LLM capabilities detected: seed_supported={capabilities.seed_supported}, "
                    f"timeout_supported={capabilities.timeout_supported}, "
                    f"model_hash={capabilities.model_hash}"
                )
        return self._llm_service

    @property
    def final_review_llm_service(self) -> LLMService:
        """
        Get or initialize separate LLM service for final review.
        Uses final_review config fields first (self-contained), falls back to main LLM config.
        Wires routing config for Ollama fallback support.
        """
        if self._final_review_llm_service is None:
            global_config = self.config_manager.load_global_config()
            fr = global_config.final_review
            provider = fr.provider

            # --- API key: use final_review's own field, fall back to main LLM ---
            if provider == 'ollama':
                api_key = 'ollama'
            elif fr.api_key_env_var:
                api_key = os.getenv(fr.api_key_env_var)
            elif provider == 'anthropic':
                api_key = os.getenv('ANTHROPIC_API_KEY')
            else:
                _fr_key_env = global_config.llm.api_key_env_var or 'OPENAI_API_KEY'
                api_key = os.getenv(_fr_key_env)

            # --- Base URL: use final_review's own field, fall back to main LLM ---
            if fr.base_url:
                base_url = fr.base_url
            elif provider == 'ollama':
                base_url = "http://localhost:11434/v1"
            elif provider == 'anthropic':
                base_url = None
            else:
                base_url = global_config.llm.base_url

            self._final_review_llm_service = LLMService(
                provider=provider,
                model=fr.model,
                api_key=api_key,
                base_url=base_url,
                temperature=0.0,
                max_retries=1,
                retry_backoff_seconds=5,
                timeout_seconds=fr.timeout_seconds,
                seed=None,
                deterministic_mode=False,
                enforce_timeout=True,
            )

            # Wire routing config for Ollama fallback support
            if global_config.model_routing.enabled:
                self._final_review_llm_service.set_routing_config(
                    global_config.model_routing.model_dump()
                )

            logger.info(
                f"Initialized final review LLM: provider={provider}, "
                f"model={fr.model}, base_url={base_url}, "
                f"timeout={fr.timeout_seconds}s, "
                f"fallback={'enabled' if global_config.model_routing.enabled else 'disabled'}"
            )
        return self._final_review_llm_service

    @property
    def discovery_service(self) -> DiscoveryService:
        """Get or initialize discovery service."""
        if self._discovery_service is None:
            global_config = self.config_manager.load_global_config()
            # Pass global config to DiscoveryService (family config passed per-run)
            self._discovery_service = DiscoveryService(
                self.db,
                global_config=global_config
            )
        return self._discovery_service
    
    def get_compilation_service(self, family: str) -> CompilationService:
        """Get or initialize compilation service for a family."""
        # Return fresh instance for each family (services are family-aware)
        return CompilationService(
            self.db,
            family=family,
            registry=self.registry,
            workspace_dir=self.workspace_dir / "compile",
            artifacts_dir=self.artifacts_dir / "compile",
            context_harness=self.context_harness_service,
        )

    def get_runtime_service(self, family: str) -> RuntimeService:
        """Get or initialize runtime service for a family."""
        # Return fresh instance for each family (services are family-aware)
        return RuntimeService(
            self.db,
            family=family,
            registry=self.registry,
            workspace_dir=self.workspace_dir / "runtime",
            artifacts_dir=self.artifacts_dir / "runtime",
        )

    @property
    def markdown_service(self) -> MarkdownUpdateService:
        """Get or initialize markdown service."""
        if self._markdown_service is None:
            global_config = self.config_manager.load_global_config()
            self._markdown_service = MarkdownUpdateService(
                self.db,
                artifacts_dir=self.artifacts_dir / "diffs",
                allow_markdown_write=global_config.markdown_write.allow_markdown_write,
                use_workspace_copy=self.use_workspace_copy,
                workspace_root=self.artifacts_dir / "workspace",
                run_id="default",  # Will be overridden when run starts
            )
        return self._markdown_service

    @property
    def vector_db_service(self) -> VectorDBService:
        """Get or initialize vector DB service."""
        if self._vector_db_service is None:
            global_config = self.config_manager.load_global_config()
            self._vector_db_service = VectorDBService(
                persist_directory=global_config.vector_db.persist_directory,
                embedding_model=global_config.vector_db.embedding_model,
                enabled=global_config.vector_db.enabled,
            )
        return self._vector_db_service

    @property
    def resource_detection_service(self) -> ResourceDetectionService:
        """Get or initialize resource detection service."""
        if self._resource_detection_service is None:
            global_config = self.config_manager.load_global_config()
            self._resource_detection_service = ResourceDetectionService.from_config(
                global_config.resource_detection
            )
        return self._resource_detection_service

    def _analyze_catalog_gaps(self, family: str, run_id: str, catalog=None) -> Dict:
        """
        C1: Post-run gap analysis. Analyze failures to identify catalog fix gaps.

        For each COMPILE_FAILED/RUNTIME_FAILED example, check if the catalog
        COULD have provided data to fix the error deterministically.

        Returns:
            Dict with gap counts and details for telemetry.
        """
        if not catalog or not catalog.is_loaded:
            return {}

        from .escalation_classifier import EscalationReason
        import re as _re

        gap_results = {
            'catalog_fix_gaps': 0,    # Catalog has data but fixer didn't use it
            'catalog_data_gaps': 0,   # Catalog lacks data to fix
            'details': [],
        }

        # Query failed examples from this run
        try:
            conn = self.db._get_connection()
            rows = conn.execute(
                "SELECT example_id, status, failure_reason FROM example_records "
                "WHERE family = ? AND run_id = ? AND status IN ('compile_failed', 'runtime_failed')",
                (family, run_id)
            ).fetchall()
        except Exception:
            return gap_results

        for row in rows:
            failure = row['failure_reason'] or ''

            # Extract error code from failure reason
            code_match = _re.search(r'CS\d{4}', failure)
            if not code_match:
                continue
            error_code = code_match.group()

            # Extract type/member names from error
            type_match = _re.search(r"'(\w+)'", failure)
            if not type_match:
                continue
            type_name = type_match.group(1)

            # Check if catalog has relevant data
            has_type = catalog.validate_symbol(type_name)
            has_members = bool(catalog.get_all_members(type_name))
            has_enum = bool(catalog.get_enum_members(type_name))

            if has_type or has_members or has_enum:
                gap_results['catalog_fix_gaps'] += 1
                gap_results['details'].append({
                    'example_id': row['example_id'],
                    'error_code': error_code,
                    'type': type_name,
                    'gap': 'fix_gap',
                })
            else:
                gap_results['catalog_data_gaps'] += 1
                gap_results['details'].append({
                    'example_id': row['example_id'],
                    'error_code': error_code,
                    'type': type_name,
                    'gap': 'data_gap',
                })

        if gap_results['details']:
            logger.info(
                f"Gap analysis: {gap_results['catalog_fix_gaps']} fix gaps (catalog had data), "
                f"{gap_results['catalog_data_gaps']} data gaps (catalog missing data)"
            )

        return gap_results

    def _emit_llm_telemetry(
        self,
        run_id: str,
        family: str,
        llm_response: 'LLMResponse',
        context_type: str,
        phase: str,
        example_id: Optional[str] = None,
        attempt: int = 1,
    ) -> None:
        """
        Emit telemetry event for an LLM call and accumulate run-level metrics.

        Non-fatal: all errors are caught and logged.

        Args:
            run_id: Pipeline run ID
            family: Product family
            llm_response: LLMResponse from llm_service
            context_type: 'compile', 'runtime', 'final_review', 'markdown_review'
            phase: Pipeline phase ('compilation', 'runtime', 'final_review')
            example_id: Example being processed
            attempt: Retry attempt number (1-based)
        """
        try:
            # Accumulate in-memory metrics
            self._llm_metrics['total_calls'] += 1
            usage = llm_response.usage or {}
            prompt_tokens = usage.get('prompt_tokens', 0)
            completion_tokens = usage.get('completion_tokens', 0)
            total_tokens = usage.get('total_tokens', 0)

            self._llm_metrics['total_prompt_tokens'] += prompt_tokens
            self._llm_metrics['total_completion_tokens'] += completion_tokens
            self._llm_metrics['total_tokens'] += total_tokens
            self._llm_metrics['total_latency_ms'] += llm_response.latency_ms

            ctx_counts = self._llm_metrics['calls_by_context']
            ctx_counts[context_type] = ctx_counts.get(context_type, 0) + 1

            if not llm_response.success:
                self._llm_metrics['failures'] += 1

            if llm_response.model:
                self._llm_metrics['models_used'].add(llm_response.model)

            # Emit per-call telemetry event
            from ..core.telemetry import emit_telemetry_event
            emit_telemetry_event(
                self.db,
                run_id,
                family,
                event_type='llm_call',
                phase=phase,
                example_id=example_id,
                duration_ms=llm_response.latency_ms,
                success=llm_response.success,
                metadata={
                    'model': llm_response.model,
                    'context_type': context_type,
                    'prompt_tokens': prompt_tokens,
                    'completion_tokens': completion_tokens,
                    'total_tokens': total_tokens,
                    'latency_ms': llm_response.latency_ms,
                    'finish_reason': llm_response.finish_reason,
                    'attempt': attempt,
                    'error': llm_response.error if not llm_response.success else None,
                },
            )
        except Exception as e:
            logger.debug(f"Failed to emit LLM telemetry: {e}")

    def _initialize_vector_db_and_drift(self):
        """
        Make a single startup decision for VectorDB and DriftDetector.

        Track 1 requirement (C.2): No lazy initialization.
        Decision is made once at orchestrator startup and recorded in telemetry.
        """
        global_config = self.config_manager.load_global_config()

        # Guard against mocked/invalid config types (Phase-1 robustness)
        if not isinstance(global_config, GlobalConfig):
            decision = {
                'vector_db_enabled_config': False,
                'require_on_startup': False,
                'drift_enabled_config': False,
                'vector_db_available': False,
                'drift_detector_available': False,
                'decision': 'disabled_by_invalid_config',
                'reason': 'global_config is not a GlobalConfig instance (likely mocked)',
            }
            self._vector_db_startup_decision = decision
            logger.warning(f"VectorDB disabled: {decision['reason']}")
            return

        decision = {
            'vector_db_enabled_config': global_config.vector_db.enabled,
            'require_on_startup': global_config.vector_db.require_on_startup,
            'drift_enabled_config': global_config.drift.enabled,
            'vector_db_available': False,
            'drift_detector_available': False,
            'decision': 'not_attempted',
            'reason': None,
        }

        if not global_config.vector_db.enabled:
            decision['decision'] = 'disabled_by_config'
            decision['reason'] = 'vector_db.enabled=false in config'
            self._vector_db_startup_decision = decision
            logger.info("VectorDB disabled by configuration")
            return

        # Try to initialize VectorDB service
        try:
            self._vector_db_service = VectorDBService(
                persist_directory=global_config.vector_db.persist_directory,
                embedding_model=global_config.vector_db.embedding_model,
                enabled=True,
            )

            if self._vector_db_service.is_available():
                decision['vector_db_available'] = True
                decision['decision'] = 'available'
                decision['reason'] = 'VectorDB initialized successfully'

                # Initialize DriftDetector if drift is enabled
                if global_config.drift.enabled:
                    try:
                        from ..services.drift_detector import DriftDetector
                        if self._vector_db_service._embedding_model:
                            self._drift_detector = DriftDetector(self._vector_db_service._embedding_model)
                            self._drift_enabled = True
                            decision['drift_detector_available'] = True
                            logger.info("DriftDetector initialized successfully at startup")
                        else:
                            decision['reason'] += '; Drift disabled (no embedding model)'
                            logger.warning("Drift disabled: embedding model not available")
                    except Exception as e:
                        decision['reason'] += f'; Drift init failed: {e}'
                        logger.warning(f"Failed to initialize DriftDetector: {e}")
                else:
                    decision['reason'] += '; Drift disabled by config'
                    logger.info("Drift detection disabled by configuration")

                logger.info(f"VectorDB startup decision: {decision['decision']}")
            else:
                # VectorDB dependencies missing
                if global_config.vector_db.require_on_startup:
                    decision['decision'] = 'failed_required'
                    decision['reason'] = 'VectorDB unavailable but required'
                    self._vector_db_startup_decision = decision
                    raise RuntimeError(
                        "VectorDB is unavailable but require_on_startup=true. "
                        "Install dependencies: pip install chromadb>=0.4.20 sentence-transformers>=2.2.0"
                    )
                else:
                    decision['decision'] = 'unavailable_optional'
                    decision['reason'] = 'VectorDB unavailable, proceeding without it'
                    self._vector_db_startup_decision = decision
                    logger.warning("VectorDB unavailable but not required, proceeding without vector DB and drift detection")

        except Exception as e:
            if global_config.vector_db.require_on_startup:
                decision['decision'] = 'failed_required'
                decision['reason'] = f'Init failed: {e}'
                self._vector_db_startup_decision = decision
                raise RuntimeError(f"VectorDB initialization failed and require_on_startup=true: {e}")
            else:
                decision['decision'] = 'failed_optional'
                decision['reason'] = f'Init failed: {e}'
                self._vector_db_startup_decision = decision
                logger.warning(f"VectorDB initialization failed, proceeding without it: {e}")

        self._vector_db_startup_decision = decision

    @property
    def telemetry_service(self) -> TelemetryService:
        """Get or initialize telemetry service for run tracking."""
        if self._telemetry_service is None:
            global_config = self.config_manager.load_global_config()
            self._telemetry_service = TelemetryService(
                config=global_config.telemetry,
                db=self.db,
            )
        return self._telemetry_service

    def get_substitution_service(self, family: str = "zip") -> ExampleSubstitutionService:
        """
        Get or initialize example substitution service for a given family.

        Delegates to FamilyServiceRegistry (WS-2 TASK-1C refactoring).
        Enables true multi-family support without interference.

        Args:
            family: Product family identifier (e.g., 'zip', 'words')

        Returns:
            ExampleSubstitutionService instance for the family
        """
        return self.registry.get_substitution_service(family)

    @property
    def substitution_service(self) -> ExampleSubstitutionService:
        """Backward-compatible property; prefer get_substitution_service(family)."""
        return self.get_substitution_service(self.family)

    @property
    def context_drift_validator(self) -> Optional['ContextDriftValidator']:
        """Get or initialize context drift validator."""
        if self._context_drift_validator is None and ContextDriftValidator is not None:
            global_config = self.config_manager.load_global_config()
            self._context_drift_validator = ContextDriftValidator(
                enabled=global_config.context_enforcement.enabled
            )
        return self._context_drift_validator

    @property
    def context_harness_service(self) -> Optional['ContextHarnessService']:
        """Get or initialize context harness service."""
        if self._context_harness_service is None and ContextHarnessService is not None:
            global_config = self.config_manager.load_global_config()
            self._context_harness_service = ContextHarnessService(
                enabled=global_config.context_harness.enabled
            )
        return self._context_harness_service

    def get_learned_patterns_service(self, family: str) -> Optional['LearnedPatternsService']:
        """Get or create learned patterns service for a family."""
        if family in self._learned_patterns_service_cache:
            return self._learned_patterns_service_cache[family]

        try:
            family_config = self.config_manager.load_family_config(family)
            lp_config = family_config.learned_patterns

            if not lp_config or not lp_config.get('enabled', True):
                self._learned_patterns_service_cache[family] = None
                return None

            service = self.registry.get_learned_patterns(family)
            self._learned_patterns_service_cache[family] = service
            return service
        except Exception as e:
            logger.error(f"Failed to initialize learned_patterns_service: {e}")
            self._learned_patterns_service_cache[family] = None
            return None

    def _get_fix_strategy_config(self) -> Dict[str, Any]:
        """Get fix strategy configuration from learned_patterns config."""
        if not hasattr(self, '_current_family') or not self._current_family:
            return {'enable_learned_patterns': False}

        try:
            family_config = self.config_manager.load_family_config(self._current_family)
            lp_config = family_config.learned_patterns

            return {
                'enable_learned_patterns': lp_config.get('enabled', True),
                'learned_patterns_min_confidence': lp_config.get('min_confidence', 0.6),
                'learned_patterns_require_approval': lp_config.get('require_approval', True),
            }
        except Exception as e:
            logger.warning(f"Failed to load learned_patterns config: {e}")
            return {'enable_learned_patterns': False}

    def _should_run_auto_learn(self, global_config: GlobalConfig, results: Dict[str, Any]) -> bool:
        """Determine if auto-learn should run."""
        run_id = results.get('run_id', 'unknown')
        family = results.get('family', 'unknown')

        # LOG: Entry point
        logger.info(f"[Auto-Learn] Checking if auto-learn should run for run_id={run_id}, family={family}")

        # LOG: Config check
        auto_learn_config = getattr(global_config, 'auto_learn', None)
        config_enabled = getattr(auto_learn_config, 'enabled', None) if auto_learn_config else None
        logger.info(f"[Auto-Learn] Config check: auto_learn_config={'present' if auto_learn_config else 'missing'}, enabled={config_enabled}")

        if not auto_learn_config or not auto_learn_config.enabled:
            logger.warning(f"[Auto-Learn] SKIP: Config disabled or missing (run_id={run_id}, family={family})")
            return False

        # LOG: Success check
        success_value = results.get('success', False)
        logger.info(f"[Auto-Learn] Success check: results['success']={success_value} (run_id={run_id}, family={family})")

        if not success_value:
            logger.warning(f"[Auto-Learn] SKIP: Pipeline success=False (run_id={run_id}, family={family})")
            return False

        # LOG: Failure count calculation
        compile_stats = results.get('phases', {}).get('compilation', {})
        runtime_stats = results.get('phases', {}).get('runtime', {})
        compile_failed = compile_stats.get('failed', 0)
        runtime_failed = runtime_stats.get('failed', 0)
        failed_count = compile_failed + runtime_failed

        logger.info(f"[Auto-Learn] Failure count: compile_failed={compile_failed}, runtime_failed={runtime_failed}, total={failed_count} (run_id={run_id}, family={family})")

        # LOG: Final decision
        will_run = failed_count > 0
        if will_run:
            logger.info(f"[Auto-Learn] WILL RUN: {failed_count} failures detected (run_id={run_id}, family={family})")
        else:
            logger.warning(f"[Auto-Learn] SKIP: No failures detected (failed_count=0) (run_id={run_id}, family={family})")

        return will_run

    def _run_auto_learn_phase(self, run_id: str, family: str, global_config: GlobalConfig) -> Dict:
        """Run auto-learn pattern extraction as subprocess."""
        # LOG: Entry
        logger.info(f"[Auto-Learn] Starting auto-learn phase for run_id={run_id}, family={family}")

        import subprocess
        import sys
        from pathlib import Path

        auto_learn_config = global_config.auto_learn
        use_llm = auto_learn_config.use_llm

        # LOG: Command construction
        script_path = Path(__file__).parent.parent.parent / "scripts" / "auto_learn.py"
        cmd = [sys.executable, str(script_path), "--family", family, "--run-id", run_id]
        if use_llm:
            cmd.append("--use-llm")

        logger.info(f"[Auto-Learn] Subprocess command: {' '.join(cmd)} (run_id={run_id}, family={family})")

        # LOG: Execution
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            logger.info(f"[Auto-Learn] Subprocess completed: return_code={result.returncode} (run_id={run_id}, family={family})")
        except subprocess.TimeoutExpired:
            logger.error(f"[Auto-Learn] Subprocess timeout after 300s (run_id={run_id}, family={family})")
            return {'success': False, 'error': 'Timeout after 300s'}
        except Exception as e:
            logger.error(f"[Auto-Learn] Subprocess exception: {e} (run_id={run_id}, family={family})")
            return {'success': False, 'error': str(e)}

        stats = {'success': result.returncode == 0}
        if result.returncode != 0:
            stats['error'] = result.stderr
            logger.error(f"[Auto-Learn] Failed with stderr: {result.stderr[:500]} (run_id={run_id}, family={family})")
        else:
            # Parse output for metrics
            patterns_stored = 0
            for line in result.stdout.split('\n'):
                if 'Stored' in line and 'patterns' in line:
                    # Extract number from "Stored N new patterns"
                    import re
                    match = re.search(r'Stored\s+(\d+)', line)
                    if match:
                        patterns_stored = int(match.group(1))
            stats['patterns_stored'] = patterns_stored
            stats['stdout'] = result.stdout[:500]  # First 500 chars for logging
            logger.info(f"[Auto-Learn] Success: patterns_stored={patterns_stored} (run_id={run_id}, family={family})")
            logger.debug(f"[Auto-Learn] Stdout preview: {result.stdout[:500]} (run_id={run_id}, family={family})")

        return stats

    def _has_new_patterns_since_last_run(self, family: str, current_run_id: str) -> bool:
        """Check if new learned patterns exist since last run."""
        try:
            prev_runs = self.db.get_recent_runs(family, limit=2)
            if len(prev_runs) < 2:
                return False

            prev_run = prev_runs[1]

            import sqlite3
            conn = sqlite3.connect("data/api_catalog.db")
            cursor = conn.execute(
                "SELECT COUNT(*) FROM learned_patterns WHERE family = ? AND created_at > ?",
                (family, prev_run.started_at)
            )
            count = cursor.fetchone()[0]
            conn.close()

            return count > 0
        except Exception:
            return False

    def _is_build_failure(self, stderr: Optional[str]) -> bool:
        """
        Check if the error is a build failure vs a runtime failure.

        Build failures during runtime phase should use compilation fix prompts,
        not runtime fix prompts.

        Args:
            stderr: The stderr output from runtime execution

        Returns:
            True if this is a build/restore failure, False if runtime failure
        """
        if not stderr:
            return False
        if stderr.startswith("Build failed:"):
            return True
        if "Restore failed:" in stderr:
            return True
        # Also check for common MSBuild error patterns
        if "error CS" in stderr:  # C# compiler errors
            return True
        if "error MSB" in stderr:  # MSBuild errors
            return True
        return False

    def _load_api_context(
        self,
        family: str,
        error_signature: str,
        error_message: str,
        max_chars: int = 8000
    ) -> str:
        """
        Load relevant API documentation context for an error.

        Note: APIReferenceService and APIContextService have been removed (TASK-DLL-03).
        This method is kept as a stub to avoid breaking callers; it always returns "".

        Args:
            family: Product family
            error_signature: Error code (e.g., 'CS0103', 'CS0246')
            error_message: Full error message
            max_chars: Maximum characters of context to return

        Returns:
            Empty string (service removed)
        """
        return ""

    def run_full_pipeline(
        self,
        family: str,
        max_examples: Optional[int] = None,
        skip_runtime: bool = False,
        skip_llm_fixes: bool = False,
        skip_llm_runtime_fixes: bool = False,
        dry_run: bool = False,
        allow_md_write: bool = False,
        allow_commit: bool = False,
        strategy_config: Optional[dict] = None,
    ) -> Dict[str, Any]:
        """
        Run the full pipeline for a family.

        Args:
            family: Family identifier
            max_examples: Maximum examples to process
            skip_runtime: Skip runtime verification phase
            skip_llm_fixes: Skip LLM-based fixing
            skip_llm_runtime_fixes: Skip LLM fixes for runtime errors only
            dry_run: Don't write changes to files
            allow_md_write: Override global config to allow markdown writes
            allow_commit: Override global config to allow git commit
            strategy_config: Dict controlling which fix strategies to enable

        Returns:
            Pipeline results dictionary
        """
        results = {
            'family': family,
            'started_at': datetime.now().isoformat(),
            'phases': {},
            'success': True,
        }

        # Store current family for _get_fix_strategy_config()
        self._current_family = family

        # Load family config
        try:
            family_config = self.config_manager.load_family_config(family)
        except FileNotFoundError:
            results['success'] = False
            results['error'] = f"Family config not found: {family}"
            return results

        # Create run record
        run_id = self.db.create_run(family, "full_pipeline")
        results['run_id'] = run_id

        # Load global config for resource detection
        global_config = self.config_manager.load_global_config()

        # Record VectorDB startup decision to run results (Track 1: C.2)
        results['vector_db_startup_decision'] = self._vector_db_startup_decision
        results['drift_enabled'] = self._drift_enabled

        # Capture run fingerprint at start (Track 1: C.8)
        self._capture_and_store_fingerprint(run_id, family)

        # Start telemetry run tracking (HTTP API + SQLite)
        telemetry_event_id = None
        if global_config.telemetry.internal_enabled:
            try:
                telemetry_event = self.telemetry_service.create_run_event(
                    run_id=run_id,
                    job_type="full_pipeline",
                    family_config=family_config,
                    status="running",
                )
                self.telemetry_service.start_run(telemetry_event)
                telemetry_event_id = telemetry_event.event_id
                results['telemetry_event_id'] = telemetry_event_id
                logger.debug(f"Started telemetry run: {telemetry_event_id}")

                # Emit VectorDB startup decision event once (Track 1: C.2)
                decision = self._vector_db_startup_decision.get('decision', 'unknown')
                if decision in ['unavailable_optional', 'failed_optional', 'disabled_by_config']:
                    # Emit telemetry event for vector DB unavailability
                    try:
                        from ..core.telemetry import emit_telemetry_event
                        emit_telemetry_event(
                            self.db,
                            run_id,
                            family,
                            event_type='vector_db_unavailable' if 'unavailable' in decision else 'drift_disabled',
                            phase='startup',
                            metadata={
                                'decision': decision,
                                'reason': self._vector_db_startup_decision.get('reason'),
                                'drift_enabled': self._drift_enabled,
                            }
                        )
                        logger.debug(f"Emitted telemetry event for VectorDB decision: {decision}")
                    except Exception as e:
                        logger.warning(f"Failed to emit VectorDB telemetry event: {e}")
            except Exception as e:
                # Don't fail pipeline if telemetry fails
                logger.warning(f"Failed to start telemetry run: {e}")

        # Log resource decision to telemetry (if enabled)
        if global_config.resource_detection.telemetry_log_resource_decisions:
            try:
                resource_decision = self.resource_detection_service.make_resource_decision(
                    cpu_max_percent=global_config.limits.cpu_max_percent,
                    ram_max_mb=global_config.limits.ram_max_mb,
                    vram_max_mb=global_config.limits.vram_max_mb,
                )
                log_resource_decision(self.db, run_id, family, resource_decision)
                results['resource_decision'] = resource_decision.to_telemetry_dict()
            except Exception as e:
                # Don't fail pipeline if resource detection fails
                logger.warning(f"Resource detection failed (continuing anyway): {e}")

        cs_file_promoted = 0  # Track CS_FILE auto-promotions for prod DB copy decision
        try:
            # Phase 0: Ensure API catalog is available (mandatory for namespace resolution)
            catalog_path = Path(f"config/families/{family}_api_catalog.json")
            if not catalog_path.exists() or self._is_catalog_invalid(catalog_path):
                logger.info(f"Phase 0: Generating API catalog for {family}")
                try:
                    from ..services.backfill_service import BackfillService
                    bs = BackfillService(config_manager=self.config_manager)
                    catalog_result = bs.backfill_api_catalog(family=family, force=True)
                    if catalog_result.success:
                        logger.info(
                            f"Phase 0: Catalog generated for {family} "
                            f"({catalog_result.files_copied} types)"
                        )
                        # Refresh the registry to pick up the new catalog
                        self.registry = FamilyServiceRegistry(
                            self.config_manager, self.artifacts_dir
                        )
                    else:
                        logger.warning(
                            f"Phase 0: Catalog generation failed for {family}: "
                            f"{catalog_result.error}"
                        )
                except Exception as e:
                    logger.warning(f"Phase 0: Catalog generation error for {family}: {e}")
            else:
                try:
                    data = json.loads(catalog_path.read_text(encoding='utf-8'))
                    type_count = len(data.get("types", {}))
                    logger.info(f"Phase 0: API catalog for {family} OK ({type_count} types)")
                except Exception:
                    logger.info(f"Phase 0: API catalog for {family} exists")

            # Phase 0.5: Validate default_usings against catalog
            self._validate_default_usings(family, family_config)

            # Phase A: Discovery
            logger.info(f"Phase A: Discovery for {family}")
            with track_phase_timing(self.db, run_id, family, "discovery"):
                discovery_stats = self._run_discovery_phase(run_id, family, family_config, max_examples)
            results['phases']['discovery'] = discovery_stats

            if discovery_stats.get('error'):
                results['success'] = False
                return results

            # Phase A.5: Gist backfill (fetch source code for gist-referenced examples)
            try:
                from ..services.backfill_service import BackfillService
                backfill_svc = BackfillService(
                    db=self.db, config_manager=self.config_manager
                )
                backfill_result = backfill_svc.backfill_gist_source_code(family)
                if backfill_result.items_downloaded > 0:
                    logger.info(
                        f"Gist backfill: fetched {backfill_result.items_downloaded} examples"
                    )
                elif backfill_result.skipped:
                    logger.info(f"Gist backfill skipped: {backfill_result.skip_reason}")
            except Exception as e:
                logger.warning(f"Gist backfill failed (continuing): {e}")

            # Phase A.6: Preload learned patterns for performance
            learned_service = self.get_learned_patterns_service(family)
            if learned_service:
                try:
                    learned_service.preload_all_patterns()
                except Exception as e:
                    logger.warning(f"Failed to preload patterns (continuing): {e}")

            # Phase A.7: Auto-promote CS_FILE examples (reference-only, skip compile/runtime)
            # CS_FILE examples are canonical source-of-truth from official repos.
            # They don't need compilation/runtime verification — they serve as
            # reference material for the vector DB and fixture enhancement.
            _all_discovered = self.db.get_examples_by_family(
                family, ExampleStatus.DISCOVERED, run_id=run_id
            )
            _cs_file_examples = [
                ex for ex in (_all_discovered or [])
                if ex.source_type == SourceType.CS_FILE
            ]
            cs_file_promoted = len(_cs_file_examples)
            if _cs_file_examples:
                for ex in _cs_file_examples:
                    self.db.update_example_status(
                        ex.example_id, ExampleStatus.VERIFIED, run_id=run_id
                    )
                    if ex.original_code:
                        self.db.update_example_code(
                            ex.example_id,
                            verified_code=ex.original_code,
                            run_id=run_id,
                        )
                logger.info(
                    f"Phase A.7: Auto-promoted {cs_file_promoted} CS_FILE examples "
                    f"to VERIFIED (reference-only, skip compile/runtime)"
                )
                results['phases']['cs_file_promotion'] = {
                    'promoted': cs_file_promoted,
                }

            # Phase B: Compilation
            logger.info(f"Phase B: Compilation verification for {family}")
            with track_phase_timing(self.db, run_id, family, "compilation"):
                compile_stats = self._run_compilation_phase(
                    run_id, family, family_config, max_examples, skip_llm_fixes, strategy_config
                )
            results['phases']['compilation'] = compile_stats

            # Phase C: Runtime (optional)
            if not skip_runtime:
                logger.info(f"Phase C: Runtime verification for {family}")
                with track_phase_timing(self.db, run_id, family, "runtime"):
                    runtime_stats = self._run_runtime_phase(
                        run_id, family, family_config, max_examples, skip_llm_fixes, skip_llm_runtime_fixes
                    )
                results['phases']['runtime'] = runtime_stats

            # Phase D: Markdown Update
            logger.info(f"Phase D: Markdown update for {family}")
            with track_phase_timing(self.db, run_id, family, "markdown_update"):
                update_stats = self._run_markdown_update_phase(
                    run_id, family, dry_run, allow_md_write=allow_md_write
                )
            results['phases']['markdown_update'] = update_stats

            # Phase E: Final Review (using LLM)
            if not skip_llm_fixes and self.llm_service.is_available():
                logger.info(f"Phase E: Final LLM review for {family}")
                with track_phase_timing(self.db, run_id, family, "final_review"):
                    review_stats = self._run_final_review_phase(run_id, family)
                results['phases']['final_review'] = review_stats
            else:
                # Auto-promote MD_UPDATED -> FINAL_REVIEW_PASSED when Phase E is skipped
                md_updated = self.db.get_examples_by_family(family, ExampleStatus.MD_UPDATED, run_id=run_id)
                auto_promoted = 0
                if md_updated:
                    for ex in md_updated:
                        self.db.update_example_status(ex.example_id, ExampleStatus.FINAL_REVIEW_PASSED, run_id=run_id)
                        auto_promoted += 1
                    logger.info(f"Auto-promoted {auto_promoted} examples to FINAL_REVIEW_PASSED (Phase E skipped)")
                results['phases']['final_review'] = {'skipped': True, 'auto_promoted': auto_promoted}

            # Phase F: Telemetry and Commit
            logger.info(f"Phase F: Finalization for {family}")
            with track_phase_timing(self.db, run_id, family, "finalization"):
                final_stats = self._run_finalization_phase(family, run_id, dry_run, allow_commit=allow_commit)
            results['phases']['finalization'] = final_stats

            # Phase F.5: Auto-Learn (extract patterns from failures)
            logger.info(f"[Auto-Learn] Phase F.5 checkpoint reached for run_id={run_id}, family={family}")
            logger.info(f"[Auto-Learn] Current results['success']={results.get('success')}, phases={list(results.get('phases', {}).keys())}")

            if self._should_run_auto_learn(global_config, results):
                logger.info(f"Phase F.5: Running auto-learn for {family}")
                try:
                    auto_learn_stats = self._run_auto_learn_phase(run_id, family, global_config)
                    results['phases']['auto_learn'] = auto_learn_stats
                    logger.info(f"[Auto-Learn] Phase F.5 completed: {auto_learn_stats}")

                    # Invalidate cache to pick up new patterns
                    if auto_learn_stats.get('patterns_stored', 0) > 0:
                        if family in self._learned_patterns_service_cache:
                            del self._learned_patterns_service_cache[family]
                            self.registry.clear_cache(family)
                            logger.info(f"[Auto-Learn] Invalidated cache for {family}")
                except Exception as e:
                    logger.error(f"[Auto-Learn] Auto-learn failed (non-fatal): {e}", exc_info=True)
            else:
                logger.info(f"[Auto-Learn] Phase F.5 skipped (decision=False)")

            # Export run artifacts (fingerprint.json, results_summary.json)
            logger.info(f"Exporting run artifacts for {run_id}")
            self._export_run_artifacts(run_id, family)
            
            # Complete run (stats computed from DB, not stale counters)
            self.db.complete_run(
                run_id,
                status='completed',
                family=family,  # Let complete_run query DB for accurate stats
            )

            # Complete telemetry run (success)
            if telemetry_event_id and global_config.telemetry.internal_enabled:
                try:
                    # Get accurate stats from DB, not stale counters
                    db_stats = self.db.get_run_stats_from_db(family, run_id)
                    discovery_stats = results['phases'].get('discovery', {})

                    # Associate commit if one was made
                    commit_hash = final_stats.get('commit_hash')
                    if commit_hash:
                        self.telemetry_service.associate_commit(
                            telemetry_event_id,
                            commit_hash,
                            datetime.now(),
                            commit_source="llm",
                        )

                    # C1: Post-run gap analysis — identify catalog fix gaps
                    try:
                        _catalog = self.registry.get_api_catalog(family) if (family and self.registry) else None
                        gap_analysis = self._analyze_catalog_gaps(family, run_id, _catalog)
                        if gap_analysis:
                            logger.info(
                                f"Catalog gap analysis: {gap_analysis.get('catalog_fix_gaps', 0)} fixable gaps, "
                                f"{gap_analysis.get('catalog_data_gaps', 0)} data gaps"
                            )
                    except Exception as ga_err:
                        gap_analysis = {}
                        logger.debug(f"Gap analysis skipped: {ga_err}")

                    # Flush accumulated LLM metrics to metrics_json / context_json
                    llm_metrics_flush = dict(self._llm_metrics)
                    llm_metrics_flush['models_used'] = list(self._llm_metrics['models_used'])
                    context_flush = {
                        'llm_model': global_config.llm.model,
                        'llm_provider': global_config.llm.provider,
                        'llm_temperature': global_config.llm.temperature,
                        'deterministic_mode': getattr(global_config.llm, 'deterministic_mode', False),
                        'drift_enabled': self._drift_enabled,
                        'vector_db_decision': self._vector_db_startup_decision.get('decision'),
                    }
                    self.telemetry_service.update_run(telemetry_event_id, {
                        'metrics_json': llm_metrics_flush,
                        'context_json': context_flush,
                    })

                    self.telemetry_service.complete_run(
                        telemetry_event_id,
                        status='success',
                        items_discovered=discovery_stats.get('examples_found', 0),
                        items_succeeded=db_stats['verified'],
                        items_failed=db_stats['failed'],
                        output_summary=f"Verified {db_stats['verified']} examples for {family}",
                    )
                    logger.debug(f"Completed telemetry run: {telemetry_event_id}")

                    # Copy to production database AFTER telemetry is fully populated
                    # (requires: associate_commit for git_commit_hash, update_run for
                    #  metrics_json/context_json, complete_run for status/end_time/items)
                    # Also copy CS_FILE-only runs (no commit needed since they're reference-only)
                    if self.db.production_db_path and (commit_hash or cs_file_promoted > 0):
                        logger.info(f"Copying run {run_id} to production database...")
                        success = self.db.copy_run_to_production(run_id, commit_hash)
                        if success:
                            logger.info(f"Production database updated for run {run_id}")
                        else:
                            logger.warning(f"Failed to update production database for run {run_id}")

                except Exception as e:
                    logger.warning(f"Failed to complete telemetry run: {e}")

            results['completed_at'] = datetime.now().isoformat()

        except Exception as e:
            logger.exception(f"Pipeline failed: {e}")
            results['success'] = False
            results['error'] = str(e)

            self.db.complete_run(run_id, status='failed', family=family, error=str(e))

            # Complete telemetry run (failure) — include stats from DB
            if telemetry_event_id and global_config.telemetry.internal_enabled:
                try:
                    # Flush partial LLM metrics even on failure
                    llm_metrics_flush = dict(self._llm_metrics)
                    llm_metrics_flush['models_used'] = list(self._llm_metrics['models_used'])
                    context_flush = {
                        'llm_model': global_config.llm.model,
                        'llm_provider': global_config.llm.provider,
                        'llm_temperature': global_config.llm.temperature,
                        'deterministic_mode': getattr(global_config.llm, 'deterministic_mode', False),
                        'drift_enabled': self._drift_enabled,
                        'vector_db_decision': self._vector_db_startup_decision.get('decision'),
                    }
                    self.telemetry_service.update_run(telemetry_event_id, {
                        'metrics_json': llm_metrics_flush,
                        'context_json': context_flush,
                    })

                    # Compute stats from DB even on failure (Fix 3: RC4)
                    try:
                        _fail_disc = results.get('phases', {}).get('discovery', {})
                        _fail_db = self.db.get_run_stats_from_db(family, run_id)
                    except Exception:
                        _fail_disc, _fail_db = {}, {}

                    self.telemetry_service.complete_run(
                        telemetry_event_id,
                        status='failure',
                        items_discovered=_fail_disc.get('examples_found', 0),
                        items_succeeded=_fail_db.get('verified', 0),
                        items_failed=_fail_db.get('failed', 0),
                        error_summary=str(e)[:200],
                        error_details=str(e),
                    )
                except Exception:
                    pass  # Don't fail on telemetry error

            results['completed_at'] = datetime.now().isoformat()

        finally:
            # Guaranteed cleanup: if neither try nor except completed normally,
            # the run is stuck in 'running' state. Mark as 'interrupted'. (Fix 2: RC2)
            if not results.get('completed_at'):
                logger.warning(f"Pipeline run {run_id} did not complete normally - marking as interrupted")
                results['completed_at'] = datetime.now().isoformat()
                results['success'] = False
                results['error'] = results.get('error', 'Pipeline interrupted (timeout or signal)')

                try:
                    self.db.complete_run(run_id, status='interrupted', family=family,
                                         error='Pipeline interrupted before completion')
                except Exception:
                    pass

                if telemetry_event_id:
                    try:
                        _int_disc = results.get('phases', {}).get('discovery', {})
                        _int_db = self.db.get_run_stats_from_db(family, run_id)
                        self.telemetry_service.complete_run(
                            telemetry_event_id,
                            status='interrupted',
                            items_discovered=_int_disc.get('examples_found', 0),
                            items_succeeded=_int_db.get('verified', 0),
                            items_failed=_int_db.get('failed', 0),
                            error_summary='Pipeline interrupted before completion',
                        )
                    except Exception:
                        pass

        return results
    
    def _run_discovery_phase(
        self,
        run_id: str,
        family: str,
        family_config: FamilyConfig,
        max_examples: Optional[int],
    ) -> Dict[str, Any]:
        """
        Run Phase A: Discovery and Extraction.

        Discovers examples from markdown files in content roots, up to max_examples limit.
        Discovery stops when the specified number of examples is reached, processing only
        as many files as needed. This ensures efficient discovery without wasting resources
        on examples that won't be compiled/run.

        Args:
            run_id: UUID for this run
            family: Family name
            family_config: FamilyConfig object
            max_examples: Maximum number of examples to discover (None = no limit)

        Returns:
            Discovery statistics dictionary
        """
        # Pass max_examples directly to discovery (not converted to max_files)
        stats = self.discovery_service.discover_family(
            family, family_config,
            max_files=None,  # No file limit unless explicit
            max_examples=max_examples,  # Limit total examples discovered
            run_id=run_id
        )

        # Emit discovery summary event
        try:
            from ..core.telemetry import emit_telemetry_event
            emit_telemetry_event(
                self.db, run_id, family,
                event_type='discovery_complete',
                phase='discovery',
                success=True,
                metadata={
                    'files_found': stats['files_found'],
                    'files_processed': stats['files_processed'],
                    'examples_found': stats['examples_found'],
                    'inline_examples': stats['inline_examples'],
                    'gist_examples': stats['gist_examples'],
                },
            )
        except Exception:
            pass

        return {
            'files_found': stats['files_found'],
            'files_processed': stats['files_processed'],
            'examples_found': stats['examples_found'],
            'inline_examples': stats['inline_examples'],
            'gist_examples': stats['gist_examples'],
            'errors': stats['errors'],
        }
    
    def _run_compilation_phase(
        self,
        run_id: str,
        family: str,
        family_config: FamilyConfig,
        max_examples: Optional[int],
        skip_llm_fixes: bool,
        strategy_config: Optional[dict] = None,
    ) -> Dict[str, Any]:
        """Run Phase B: Compilation Verification Loop.

        Args:
            strategy_config: Dict with keys:
                - enable_transformers: Enable enhanced transformers (E2)
                - enable_retrieval: Enable vector DB retrieval (E3)
                - enable_semantic_microfixes: Enable semantic micro-fixes (E4)
                - enable_substitution: Enable example substitution
        """
        stats = {
            'total_processed': 0,
            'compiled_first_try': 0,
            'compiled_with_fix': 0,
            'failed': 0,
            'errors': 0,
        }
        
        # Check .NET availability
        dotnet_available, dotnet_version = check_dotnet_available()
        if not dotnet_available:
            stats['error'] = f".NET SDK not available: {dotnet_version}"
            return stats
        
        stats['dotnet_version'] = dotnet_version

        # Get examples to process
        # If new patterns exist since last run, re-process failed examples too
        if self._has_new_patterns_since_last_run(family, run_id):
            logger.info(f"New patterns detected - re-processing failed examples")
            # Include RUNTIME_FAILED to allow learned patterns to fix runtime issues
            # (e.g., missing using directives causing runtime type resolution failures,
            # or fixture path issues that can be resolved with learned substitutions)
            examples = self.db.get_examples_with_applicable_patterns(
                family=family,
                status=[ExampleStatus.DISCOVERED, ExampleStatus.COMPILE_FAILED, ExampleStatus.RUNTIME_FAILED],
                max_examples=max_examples,
                run_id=run_id
            )
            # Log breakdown of statuses being re-processed
            status_breakdown = {}
            for ex in examples:
                status = ex.status
                status_breakdown[status.value] = status_breakdown.get(status.value, 0) + 1
            logger.info(f"Re-processing {len(examples)} examples by status: {status_breakdown}")
        else:
            examples = self.db.get_examples_by_family(family, ExampleStatus.DISCOVERED, max_examples, run_id=run_id)

        global_config = self.config_manager.load_global_config()
        max_retries = global_config.llm.max_retries

        # Initialize strategy configuration
        # If no strategy_config provided, enable all strategies (default behavior)
        if strategy_config is None:
            strategy_config = {
                'enable_transformers': True,
                'enable_retrieval': True,
                'enable_semantic_microfixes': True,
                'enable_substitution': True,
                'enable_learned_patterns': True,
            }

        logger.info(f"Strategy configuration: {strategy_config}")

        # Phase and per-example timeout enforcement (Fix 4: RC3)
        import time as _time
        _phase_start = _time.time()
        _phase_timeout = global_config.timeouts.per_phase_seconds    # Default: 1800s (30 min)
        _per_ex_timeout = global_config.timeouts.per_example_seconds  # Default: 300s (5 min)
        _total_examples = len(examples)
        logger.info(f"[Phase B] Starting compilation: {_total_examples} examples, "
                     f"phase_timeout={_phase_timeout}s, per_example_timeout={_per_ex_timeout}s")

        for _i, example in enumerate(examples):
            # Phase-level timeout check
            _elapsed = _time.time() - _phase_start
            if _elapsed > _phase_timeout:
                logger.error(
                    f"[Phase B] Phase timeout exceeded: {_elapsed:.0f}s > {_phase_timeout}s. "
                    f"Processed {_i}/{_total_examples}. Aborting compilation phase."
                )
                stats['phase_timeout'] = True
                stats['phase_elapsed_seconds'] = int(_elapsed)
                break

            # Progress logging every 10 examples (or every example if <20 total)
            _log_interval = 10 if _total_examples >= 20 else 1
            if _i > 0 and _i % _log_interval == 0:
                _rate = _i / (_elapsed / 60) if _elapsed > 0 else 0
                logger.info(
                    f"[Phase B] {_i}/{_total_examples} ({100*_i/_total_examples:.1f}%) "
                    f"rate={_rate:.1f}/min elapsed={_elapsed:.0f}s "
                    f"ok={stats['compiled_first_try']+stats['compiled_with_fix']} "
                    f"fail={stats['failed']}"
                )

            _example_start = _time.time()
            stats['total_processed'] += 1

            try:
                # Phase-2 Task 2: Check if example should be escalated to NEEDS_REVIEW immediately
                should_escalate, escalation_reason = should_escalate_to_review(
                    code=example.original_code,
                    language=example.language,
                    file_path=example.file_path,
                    error_message=None,
                )

                if should_escalate:
                    logger.info(f"Example {example.example_id} escalated to NEEDS_REVIEW: {escalation_reason}")
                    self.db.update_example_status(
                        example.example_id,
                        ExampleStatus.NEEDS_REVIEW,
                        escalation_reason=escalation_reason,
                        run_id=run_id,
                    )

                    # Phase-2 Task 3: Record compile attempt even for pre-escalated examples
                    # This ensures compile_attempts_count >= total_examples for accurate metrics
                    precheck_result = CompileResult(
                        success=False,
                        exit_code=-1,
                        stdout="",
                        stderr=f"Pre-compilation check failed: {escalation_reason}",
                        duration_ms=0,
                        dll_version="",
                        errors=[f"precheck_escalated:{escalation_reason}"],
                        warnings=[],
                    )
                    self.get_compilation_service(family).record_attempt(
                        example.example_id,
                        precheck_result,
                        example.original_code or "",
                        output_code=None,
                        llm_request=None,
                        llm_response=None,
                        run_id=run_id,
                    )

                    stats['failed'] += 1
                    continue

                # A3: Detect foreign family/external library usage before compilation
                # Uses existing detect_foreign_families() to save LLM cycles on unfixable examples
                try:
                    foreign = self.discovery_service.detect_foreign_families(
                        example.original_code or "", family
                    )
                    if foreign:
                        # Check if any are actual foreign families (not just warnings)
                        foreign_families = [f for f in foreign if not f.startswith('external_') and not f.startswith('invalid_')]
                        external_deps = [f for f in foreign if f.startswith('external_')]

                        if foreign_families:
                            logger.info(
                                f"Example {example.example_id} contains foreign family code: "
                                f"{foreign_families} - escalating to NEEDS_REVIEW"
                            )
                            self.db.update_example_status(
                                example.example_id,
                                ExampleStatus.NEEDS_REVIEW,
                                escalation_reason=f"wrong_family_detected:{','.join(foreign_families)}",
                                run_id=run_id,
                            )
                            stats['failed'] += 1
                            continue

                        if external_deps:
                            logger.info(
                                f"Example {example.example_id} uses external dependencies: "
                                f"{external_deps} - escalating to NEEDS_REVIEW"
                            )
                            self.db.update_example_status(
                                example.example_id,
                                ExampleStatus.NEEDS_REVIEW,
                                escalation_reason=f"external_dependency_missing:{','.join(external_deps)}",
                                run_id=run_id,
                            )
                            stats['failed'] += 1
                            continue
                except Exception as e:
                    logger.debug(f"Foreign family detection failed for {example.example_id}: {e}")

                # CRITICAL: Proactive using directive injection (BEFORE semantic microfixes)
                # This prevents CS0246 errors by adding missing using directives based on
                # detected API usage, ensuring code compiles first-try when possible.
                if strategy_config.get('enable_semantic_microfixes', False) and self.registry:
                    from ..services.semantic_microfixes import proactive_add_using_directives

                    namespace_map = self.registry.get_namespace_map(family)
                    if namespace_map:
                        code_with_usings, using_fixes = proactive_add_using_directives(
                            example.original_code or "",
                            namespace_map
                        )
                        if using_fixes:
                            logger.info(
                                f"Proactive using directives for {example.example_id}: "
                                f"{', '.join(using_fixes)}"
                            )
                            example.original_code = code_with_usings
                            try:
                                from ..core.telemetry import emit_telemetry_event
                                emit_telemetry_event(
                                    self.db, run_id, family,
                                    event_type='proactive_using_directives_added',
                                    phase='compilation',
                                    example_id=example.example_id,
                                    success=True,
                                    metadata={'fixes': using_fixes, 'count': len(using_fixes)},
                                )
                            except Exception:
                                pass
                    else:
                        logger.warning(
                            f"Namespace map is empty for family '{family}' - cannot apply proactive using directives. "
                            f"Check if API catalog is loaded correctly."
                        )

                # Proactive semantic microfixes (before compilation)
                # Apply ALL semantic microfixes proactively since many issues
                # (stream disposal, CompressionLevel, DeflateCompressionSettings, etc.)
                # can be detected and fixed without waiting for compile errors.
                # Pass catalog for catalog-driven proactive fixes (B3-B6 generic fixers)
                _catalog = self.registry.get_api_catalog(family) if (family and self.registry) else None
                if strategy_config.get('enable_semantic_microfixes', False):
                    proactive_code, proactive_fixes = apply_semantic_microfixes(
                        example.original_code or "",
                        [],
                        family=family,
                        registry=self.registry,
                        catalog=_catalog
                    )
                    if proactive_fixes:
                        logger.info(
                            f"Proactive semantic fixes for {example.example_id}: "
                            f"{', '.join(proactive_fixes)}"
                        )
                        example.original_code = proactive_code
                        try:
                            from ..core.telemetry import emit_telemetry_event
                            emit_telemetry_event(
                                self.db, run_id, family,
                                event_type='semantic_microfix_applied',
                                phase='compilation',
                                example_id=example.example_id,
                                success=True,
                                metadata={'fixes': proactive_fixes, 'proactive': True},
                            )
                        except Exception:
                            pass

                # Proactive quick fixes (System.IO.Compression ban, hallucination
                # patterns, async-to-sync, path handling). These transformers check
                # code structure not error messages, so they work before first compile.
                proactive_code, proactive_fixes = apply_quick_fixes(
                    example.original_code or "", []
                )
                if proactive_fixes:
                    logger.info(
                        f"Proactive quick fixes for {example.example_id}: "
                        f"{', '.join(proactive_fixes)}"
                    )
                    example.original_code = proactive_code
                    try:
                        from ..core.telemetry import emit_telemetry_event
                        emit_telemetry_event(
                            self.db, run_id, family,
                            event_type='quick_fix_applied',
                            phase='compilation',
                            example_id=example.example_id,
                            success=True,
                            metadata={'fixes': proactive_fixes, 'proactive': True},
                        )
                    except Exception:
                        pass

                # Proactive CS discovery fixes (data-dir patterns + namespace collision)
                if family_config.cs_discovery.enabled:
                    from ..services.semantic_microfixes import fix_data_dir_patterns, fix_example_namespace_collision
                    if family_config.cs_discovery.data_dir_replacements:
                        fixed_code, dir_desc = fix_data_dir_patterns(
                            example.original_code or "", family_config.cs_discovery.data_dir_replacements
                        )
                        if dir_desc:
                            logger.info(f"CS data-dir fix for {example.example_id}: {dir_desc}")
                            example.original_code = fixed_code

                    pkg_ns = family_config.get_nuget_package_name().replace('.', '.')
                    ns_code, ns_desc = fix_example_namespace_collision(
                        example.original_code or "", pkg_ns
                    )
                    if ns_desc:
                        logger.info(f"CS namespace fix for {example.example_id}: {ns_desc}")
                        example.original_code = ns_code

                # A6: Proactive fixture resolution before compilation
                # Scan code for file references and ensure test data files exist
                try:
                    pre_fixture_resolver = self.registry.get_fixture_resolver(family) if self.registry else None
                    pre_test_data_str = family_config.get('test_data', {}).get('local_path', '') if isinstance(family_config, dict) else getattr(getattr(family_config, 'test_data', None), 'local_path', '')
                    if pre_fixture_resolver and pre_test_data_str:
                        pre_fixture_resolver.precheck_code_references(
                            example.original_code or "", Path(pre_test_data_str)
                        )
                except Exception as e:
                    logger.debug(f"Proactive fixture resolution skipped: {e}")

                # Try initial compilation
                success, result = self.get_compilation_service(family).compile_example(
                    example, family_config
                )

                # Record first-try compilation attempt (Task 1A: Phase-2)
                self.get_compilation_service(family).record_attempt(
                    example.example_id,
                    result,
                    example.original_code,
                    output_code=None,  # No fix on first try
                    llm_request=None,
                    llm_response=None,
                    run_id=run_id,
                )

                if success:
                    # Compiled on first try
                    stats['compiled_first_try'] += 1
                    try:
                        from ..core.telemetry import emit_telemetry_event
                        emit_telemetry_event(
                            self.db, run_id, family,
                            event_type='example_compiled',
                            phase='compilation',
                            example_id=example.example_id,
                            success=True,
                            metadata={'first_try': True},
                        )
                    except Exception:
                        pass
                    self.db.update_example_status(example.example_id, ExampleStatus.COMPILABLE, run_id=run_id)
                    self.db.update_example_code(
                        example.example_id,
                        compilable_code=example.original_code,
                        run_id=run_id,
                    )
                    # Store compilable example in vector DB for future similarity search
                    if self.vector_db_service.is_available():
                        try:
                            self.vector_db_service.add_example(
                                example_id=example.example_id,
                                code=example.original_code,
                                metadata={
                                    'family': family,
                                    'source': 'pipeline_compilation',
                                    'verified': False,  # Not runtime verified yet
                                    'compilable': True,
                                    'file_path': example.file_path,
                                },
                                drift_score=None  # ID-05: No drift (compiled first try)
                            )
                        except Exception as e:
                            logger.debug(f"Failed to add compilable example to vector DB: {e}")
                    continue

                # Phase-2 Task 2 & 3: Try quick fixes and substitution before LLM fixes
                current_code = example.original_code
                substituted = False
                quick_fix_applied = False

                # Task 2: Apply quick fixes (DirectoryNotFoundException, missing usings)
                fixed_code, applied_fixes = apply_quick_fixes(current_code, result.errors)
                if applied_fixes:
                    logger.info(f"Applied quick fixes for {example.example_id}: {', '.join(applied_fixes)}")
                    try:
                        from ..core.telemetry import emit_telemetry_event
                        emit_telemetry_event(
                            self.db, run_id, family,
                            event_type='quick_fix_applied',
                            phase='compilation',
                            example_id=example.example_id,
                            success=True,
                            metadata={'fixes': applied_fixes, 'proactive': False},
                        )
                    except Exception:
                        pass
                    quick_fix_applied = True
                    current_code = fixed_code

                    # Try recompiling with quick fixes
                    example.compilable_code = fixed_code
                    success, result = self.get_compilation_service(family).compile_example(
                        example, family_config
                    )

                    # Record quick fix attempt
                    self.get_compilation_service(family).record_attempt(
                        example.example_id,
                        result,
                        example.original_code,
                        output_code=fixed_code if success else None,
                        llm_request=f"quick_fixes:{','.join(applied_fixes)}",
                        llm_response=fixed_code if success else None,
                        run_id=run_id,
                    )

                    if success:
                        # Quick fix worked!
                        stats['compiled_with_fix'] = stats.get('compiled_with_fix', 0) + 1
                        stats['quick_fixes_applied'] = stats.get('quick_fixes_applied', 0) + 1
                        self.db.update_example_status(example.example_id, ExampleStatus.COMPILABLE, run_id=run_id)
                        self.db.update_example_code(
                            example.example_id,
                            compilable_code=fixed_code,
                            run_id=run_id,
                        )
                        logger.info(f"Quick fix succeeded for {example.example_id}")
                        continue

                # E4: Semantic Micro-Fixes - Try diagnostic-driven fixes
                if not success and strategy_config.get('enable_semantic_microfixes', False):
                    logger.info(f"Attempting semantic micro-fixes for {example.example_id}")
                    fixed_code, applied_fixes = apply_semantic_microfixes(
                        current_code,
                        result.errors,
                        family=family,
                        registry=self.registry,
                        catalog=_catalog
                    )

                    if applied_fixes:
                        logger.info(f"Applied semantic micro-fixes for {example.example_id}: {', '.join(applied_fixes)}")
                        try:
                            from ..core.telemetry import emit_telemetry_event
                            emit_telemetry_event(
                                self.db, run_id, family,
                                event_type='semantic_microfix_applied',
                                phase='compilation',
                                example_id=example.example_id,
                                success=True,
                                metadata={'fixes': applied_fixes, 'proactive': False},
                            )
                        except Exception:
                            pass
                        current_code = fixed_code

                        # Try recompiling with semantic fixes
                        example.compilable_code = fixed_code
                        success, result = self.get_compilation_service(family).compile_example(
                            example, family_config
                        )

                        # Record semantic micro-fixes attempt
                        self.get_compilation_service(family).record_attempt(
                            example.example_id,
                            result,
                            example.original_code,
                            output_code=fixed_code if success else None,
                            llm_request=f"semantic_microfixes:{','.join(applied_fixes)}",
                            llm_response=fixed_code if success else None,
                            run_id=run_id,
                        )

                        if success:
                            # Semantic micro-fixes worked!
                            stats['compiled_with_fix'] = stats.get('compiled_with_fix', 0) + 1
                            stats['semantic_microfixes_applied'] = stats.get('semantic_microfixes_applied', 0) + 1
                            self.db.update_example_status(example.example_id, ExampleStatus.COMPILABLE, run_id=run_id)
                            self.db.update_example_code(
                                example.example_id,
                                compilable_code=fixed_code,
                                run_id=run_id,
                            )
                            logger.info(f"Semantic micro-fixes succeeded for {example.example_id}")
                            continue

                # E4.5: Learned Patterns - Try patterns from auto-learn (2026-02-06)
                if not success and strategy_config.get('enable_learned_patterns', False):
                    if LearnedPatternsService is not None and extract_error_signature is not None:
                        try:
                            learned_service = self.get_learned_patterns_service(family)
                            error_sigs = extract_all_error_signatures(result.errors) if extract_all_error_signatures is not None else [extract_error_signature(result.errors)]
                            min_conf = strategy_config.get('learned_patterns_min_confidence', 0.6)
                            max_patterns = strategy_config.get('learned_patterns_max_per_error', 3)

                            # Read require_approval from family config learned_patterns section
                            lp_config = getattr(family_config, 'learned_patterns', None)
                            require_approval = True
                            if lp_config and isinstance(lp_config, dict):
                                require_approval = lp_config.get('require_approval', True)
                            elif hasattr(lp_config, 'require_approval'):
                                require_approval = lp_config.require_approval

                            all_patterns = []
                            for error_sig in error_sigs:
                                sig_patterns = learned_service.query_patterns(
                                    error_signature=error_sig,
                                    min_confidence=min_conf,
                                    approved_only=require_approval,
                                    limit=max_patterns,
                                )
                                all_patterns.extend(sig_patterns)

                            if all_patterns:
                                logger.info(
                                    f"Found {len(all_patterns)} learned patterns for {example.example_id} "
                                    f"(errors: {error_sigs})"
                                )

                            for pattern in all_patterns:
                                logger.debug(
                                    f"Trying learned pattern {pattern.id} ({pattern.fix_type}) "
                                    f"for {example.example_id}"
                                )

                                fixed_code, applied, desc = learned_service.apply_pattern(
                                    pattern=pattern,
                                    code=current_code,
                                    error_context='\n'.join(result.errors),
                                    llm_service=self.llm_service if pattern.requires_llm else None,
                                )

                                if applied and fixed_code != current_code:
                                    # Try compiling with pattern fix
                                    example.compilable_code = fixed_code
                                    success, result = self.get_compilation_service(family).compile_example(
                                        example, family_config
                                    )

                                    # Record pattern application for feedback loop
                                    if strategy_config.get('learned_patterns_feedback_tracking', True):
                                        learned_service.record_application(
                                            pattern_id=pattern.id,
                                            example_id=example.example_id,
                                            run_id=run_id,
                                            success=success,
                                        )

                                    # Record attempt for telemetry
                                    self.get_compilation_service(family).record_attempt(
                                        example.example_id,
                                        result,
                                        example.original_code,
                                        output_code=fixed_code if success else None,
                                        llm_request=f"learned_pattern:{pattern.id}:{pattern.fix_type}:{desc}",
                                        llm_response=fixed_code if success else None,
                                        run_id=run_id,
                                    )

                                    if success:
                                        # Learned pattern worked!
                                        current_code = fixed_code
                                        stats['compiled_with_fix'] = stats.get('compiled_with_fix', 0) + 1
                                        stats['learned_pattern_fixes'] = stats.get('learned_pattern_fixes', 0) + 1
                                        self.db.update_example_status(
                                            example.example_id, ExampleStatus.COMPILABLE, run_id=run_id
                                        )
                                        self.db.update_example_code(
                                            example.example_id,
                                            compilable_code=fixed_code,
                                            run_id=run_id,
                                        )
                                        logger.info(
                                            f"Learned pattern {pattern.id} succeeded for {example.example_id}: {desc}"
                                        )
                                        break

                                    # Pattern didn't compile, but use improved code for next attempt
                                    current_code = fixed_code

                            learned_service.close()

                            # If learned patterns succeeded, continue to next example
                            if success:
                                continue

                        except Exception as e:
                            logger.warning(f"Error applying learned patterns for {example.example_id}: {e}")

                # E3: Vector DB Retrieval - Try finding similar verified examples
                vector_db_success = False
                if strategy_config.get('enable_retrieval', False) and self.vector_db_service.is_available():
                    logger.info(f"Attempting vector DB retrieval for {example.example_id}")
                    try:
                        # Search for similar verified examples
                        search_results = self.vector_db_service.search_similar(
                            query_code=current_code,
                            family=family,
                            k=3,  # Get top 3 candidates
                            min_similarity=0.6,  # Reasonable similarity threshold
                            exclude_high_drift=True,  # Avoid drift contagion
                        )

                        if search_results:
                            logger.info(f"Found {len(search_results)} similar examples for {example.example_id}")

                            # Try each candidate in order of similarity
                            for idx, (candidate_id, candidate_code, similarity, metadata) in enumerate(search_results, 1):
                                logger.info(
                                    f"Trying vector DB candidate {idx}/3 for {example.example_id}: "
                                    f"{candidate_id} (similarity: {similarity:.3f})"
                                )

                                # Try compiling with candidate code
                                example.compilable_code = candidate_code
                                success, result = self.get_compilation_service(family).compile_example(
                                    example, family_config
                                )

                                # Record retrieval attempt
                                self.get_compilation_service(family).record_attempt(
                                    example.example_id,
                                    result,
                                    example.original_code,
                                    output_code=candidate_code if success else None,
                                    llm_request=f"retrieval:vector_db:candidate_{idx}:similarity_{similarity:.3f}",
                                    llm_response=candidate_code if success else None,
                                    run_id=run_id,
                                )

                                if success:
                                    # Vector DB retrieval worked!
                                    vector_db_success = True
                                    current_code = candidate_code
                                    stats['compiled_with_fix'] = stats.get('compiled_with_fix', 0) + 1
                                    stats['vector_db_retrievals'] = stats.get('vector_db_retrievals', 0) + 1
                                    self.db.update_example_status(example.example_id, ExampleStatus.COMPILABLE, run_id=run_id)
                                    self.db.update_example_code(
                                        example.example_id,
                                        compilable_code=candidate_code,
                                        run_id=run_id,
                                    )
                                    logger.info(
                                        f"Vector DB retrieval succeeded for {example.example_id} "
                                        f"using {candidate_id} (similarity: {similarity:.3f})"
                                    )
                                    break
                                else:
                                    logger.debug(
                                        f"Candidate {idx} failed to compile for {example.example_id}, "
                                        f"trying next candidate"
                                    )

                            # If any candidate succeeded, continue to next example
                            if vector_db_success:
                                continue
                            else:
                                logger.info(
                                    f"All vector DB candidates failed for {example.example_id}, "
                                    f"falling back to substitution"
                                )
                        else:
                            logger.debug(f"No similar examples found in vector DB for {example.example_id}")

                    except Exception as e:
                        logger.warning(f"Vector DB retrieval failed for {example.example_id}: {e}")
                else:
                    logger.debug(f"Vector DB not available for {example.example_id}, skipping retrieval")

                # Task 3: Check for substitution triggers
                if strategy_config.get('enable_substitution', False):
                    should_sub, trigger_info = self.get_substitution_service(family).should_substitute(result.errors)
                else:
                    should_sub = False
                    trigger_info = None

                if should_sub and trigger_info:
                    logger.info(f"Substitution triggered for {example.example_id}: {trigger_info['reason']}")

                    # Try to find a substitute example
                    substitute_result = self.get_substitution_service(family).find_substitute_example(
                        original_code=current_code,
                        trigger_info=trigger_info,
                        family=family,
                        original_app_context=example.app_context,
                    )

                    if substitute_result:
                        substitute_code, substitute_id, metadata = substitute_result
                        metadata['original_example_id'] = example.example_id

                        logger.info(
                            f"Found substitute for {example.example_id}: {substitute_id} "
                            f"(reason: {metadata['trigger_reason']})"
                        )

                        # Try compiling the substitute
                        example.compilable_code = substitute_code
                        success, result = self.get_compilation_service(family).compile_example(
                            example, family_config
                        )

                        # Record substitution attempt
                        self.get_compilation_service(family).record_attempt(
                            example.example_id,
                            result,
                            example.original_code,
                            output_code=substitute_code if success else None,
                            llm_request=f"substitution:{metadata['trigger_reason']}",
                            llm_response=substitute_code if success else None,
                            run_id=run_id,
                        )

                        if success:
                            # Substitution worked!
                            substituted = True
                            current_code = substitute_code
                            stats['compiled_with_fix'] = stats.get('compiled_with_fix', 0) + 1
                            stats['substitutions_applied'] = stats.get('substitutions_applied', 0) + 1
                            self.db.update_example_status(example.example_id, ExampleStatus.COMPILABLE, run_id=run_id)
                            self.db.update_example_code(
                                example.example_id,
                                compilable_code=substitute_code,
                                run_id=run_id,
                            )
                            logger.info(f"Substitution succeeded for {example.example_id}")

                            # Track successful substitution
                            track_compile_failure(
                                db=self.db,
                                run_id=run_id,
                                example_id=example.example_id,
                                errors='\n'.join(result.errors[:3]),
                                category='substitution_success',
                                resolution=FailureResolution.FIXED,
                                metadata=metadata,
                            )
                            continue
                        else:
                            logger.warning(
                                f"Substitution failed to compile for {example.example_id}, "
                                f"falling back to LLM fixes"
                            )

                # After ALL deterministic fixes (quick fixes, semantic micro-fixes, vector DB, substitution)
                if skip_llm_fixes:
                    stats['failed'] += 1
                    self.db.update_example_status(
                        example.example_id,
                        ExampleStatus.COMPILE_FAILED,
                        failure_reason='\n'.join(result.errors[:3]),
                        run_id=run_id,
                    )
                    continue

                # P1-B: Gate — check if CS0246 errors reference types not in the catalog
                # If so, skip LLM escalation (LLM cannot invent missing types)
                try:
                    _gate_catalog = self.registry.get_api_catalog(family) if self.registry else None
                except Exception:
                    _gate_catalog = None
                unfixable_types = self._check_unfixable_types(result.errors, _gate_catalog)
                if unfixable_types:
                    _unfixable_str = ', '.join(unfixable_types)
                    logger.warning(
                        f"UNFIXABLE_API for {example.example_id}: types not in catalog: "
                        f"{_unfixable_str} - skipping LLM escalation"
                    )
                    stats['failed'] += 1
                    self.db.update_example_status(
                        example.example_id,
                        ExampleStatus.COMPILE_FAILED,
                        failure_reason=f"UNFIXABLE_API: {_unfixable_str}",
                        run_id=run_id,
                    )
                    continue

                # Try LLM fixes
                fixed = False

                # Load API reference context for LLM (LCE-01)
                # Extract error signature and message from compile result
                error_signature = ""
                error_message = ""
                if result.errors:
                    if extract_error_signature:
                        error_signature = extract_error_signature(result.errors)
                    error_message = result.errors[0] if result.errors else ""

                api_context = self._load_api_context(
                    family=family,
                    error_signature=error_signature,
                    error_message=error_message,
                    max_chars=8000
                )
                if api_context:
                    logger.debug(f"Loaded {len(api_context)} chars of API context for {example.example_id}")

                # Search for similar examples from vector DB (LCE-02)
                similar_examples = []
                if self.vector_db_service.is_available():
                    try:
                        search_results = self.vector_db_service.search_similar(
                            query_code=current_code,
                            family=family,
                            k=global_config.vector_db.search_k,
                            min_similarity=global_config.vector_db.min_similarity_threshold,
                        )
                        similar_examples = [ex_code for _, ex_code, _, _ in search_results]
                        if similar_examples:
                            logger.debug(f"Found {len(similar_examples)} similar examples for {example.example_id}")
                    except Exception as e:
                        logger.debug(f"Vector search failed for compilation: {e}")

                # Track previous code for no-change detection
                previous_code = None

                for attempt in range(max_retries):
                    # Per-example timeout guard (Fix 4: RC3)
                    if _time.time() - _example_start > _per_ex_timeout:
                        logger.warning(
                            f"Per-example timeout for {example.example_id}: "
                            f"{_time.time() - _example_start:.0f}s > {_per_ex_timeout}s"
                        )
                        break

                    # Track 2: Progressive Enrichment - Determine enrichment tier
                    enrichment_tier = self._get_enrichment_tier(attempt, max_retries)

                    # Track 2: Apply progressive context enrichment
                    tier_api_context, tier_similar_examples, context_sources = self._apply_progressive_enrichment(
                        enrichment_tier=enrichment_tier,
                        base_api_context=api_context,
                        base_similar_examples=similar_examples,
                        error_logs='\n'.join(result.errors),
                        family_config=family_config,
                    )

                    # Track 2: Emit telemetry for retry attempt
                    try:
                        from ..core.telemetry import emit_telemetry_event
                        emit_telemetry_event(
                            self.db,
                            run_id,
                            family,
                            event_type='retry_enrichment',
                            phase='compilation',
                            metadata={
                                'example_id': example.example_id,
                                'retry_attempt': attempt + 1,
                                'enrichment_tier': enrichment_tier,
                                'context_sources': context_sources,
                                'api_context_chars': len(tier_api_context) if tier_api_context else 0,
                                'similar_examples_count': len(tier_similar_examples) if tier_similar_examples else 0,
                            }
                        )
                    except Exception as e:
                        logger.debug(f"Failed to emit retry telemetry: {e}")

                    # Create fix payload with full context (LCE-03)
                    payload = self.get_compilation_service(family).create_fix_payload(
                        example, result,
                        family_config=family_config,
                        api_context=tier_api_context,
                        similar_examples=tier_similar_examples,
                    )

                    # Get LLM fix with all context including content context for relevance
                    # TASK-DLL-07: Pass API catalog for enriched error context
                    _catalog = self.registry.get_api_catalog(family) if family else None
                    llm_response = self.llm_service.fix_code(
                        code=current_code,
                        error_logs='\n'.join(result.errors),
                        context_type="compile",
                        api_context=tier_api_context,
                        similar_examples=tier_similar_examples if tier_similar_examples else None,
                        scaffolding_hints=payload.scaffolding_hints,
                        family_config=family_config,
                        section_heading=example.section_heading,
                        description_context=example.description_context,
                        topic=example.topic,
                        catalog=_catalog,
                    )
                    self._emit_llm_telemetry(
                        run_id=run_id, family=family,
                        llm_response=llm_response,
                        context_type="compile", phase="compilation",
                        example_id=example.example_id, attempt=attempt + 1,
                    )

                    if not llm_response.success:
                        continue

                    fixed_code = llm_response.content.strip()
                    if not fixed_code:
                        continue

                    # DRIFT-06 Gate 1: Semantic signature validation
                    if getattr(global_config.final_review, 'enable_signature_validation', False):
                        try:
                            sig_service = self.registry.get_semantic_signature_service(family)
                            from ..services.semantic_signature_service import CRITICAL_ENUM_FAMILIES
                            orig_sig = sig_service.extract_signature(example.original_code)
                            fixed_sig = sig_service.extract_signature(fixed_code)
                            critical_enums = CRITICAL_ENUM_FAMILIES.get(family, [])
                            sig_drift = sig_service.compare_signatures(orig_sig, fixed_sig, critical_enums)

                            # Store original signature in DB
                            self.db.save_semantic_signature(
                                example_id=example.example_id,
                                run_id=run_id,
                                attempt_type='compile_attempt',
                                signature_data={
                                    'enum_values': orig_sig.enum_values,
                                    'method_calls': orig_sig.method_calls,
                                    'constructor_types': orig_sig.constructor_types,
                                    'property_assignments': orig_sig.property_assignments,
                                },
                                attempt_id=f"compile_{attempt}",
                            )

                            if sig_drift.critical and getattr(global_config.final_review, 'reject_critical_enum_changes', True):
                                logger.warning(
                                    f"GATE-1 Signature drift rejected for {example.example_id}: "
                                    f"{sig_drift.critical_reason}"
                                )
                                self.db.save_drift_rejection(
                                    example_id=example.example_id,
                                    run_id=run_id,
                                    attempt_id=f"compile_{attempt}",
                                    phase='compilation',
                                    rejection_reason=sig_drift.critical_reason or 'Critical enum change',
                                    drift_score=sig_drift.drift_score,
                                    signature_drift=sig_drift.to_dict(),
                                    critical_enum_changes=sig_drift.enum_changes,
                                )
                                continue  # Skip this fix, try next attempt
                        except Exception as e:
                            logger.debug(f"Signature validation error (non-fatal): {e}")

                    # DRIFT-06 Gate 2: Family-specific drift validation
                    if getattr(global_config.final_review, 'enable_family_drift_validation', False):
                        try:
                            family_validator = self.registry.get_drift_validator(family)
                            if family_validator:
                                fv_result = family_validator.validate(
                                    example.original_code, fixed_code, {}
                                )
                                if not fv_result.valid:
                                    reasons = [i.message for i in fv_result.issues]
                                    logger.warning(
                                        f"GATE-2 Family drift rejected for {example.example_id}: "
                                        f"{reasons}"
                                    )
                                    self.db.save_drift_rejection(
                                        example_id=example.example_id,
                                        run_id=run_id,
                                        attempt_id=f"compile_{attempt}",
                                        phase='compilation',
                                        rejection_reason=f"Family validation: {'; '.join(reasons)}",
                                        drift_score=fv_result.drift_score,
                                    )
                                    continue  # Skip this fix, try next attempt
                        except Exception as e:
                            logger.debug(f"Family drift validation error (non-fatal): {e}")

                    # Phase-2 Gate B: Validate context drift if enabled
                    if self.context_drift_validator is not None:
                        drift_result = self.context_drift_validator.validate(
                            original_code=current_code,
                            fixed_code=fixed_code,
                            original_context=example.app_context
                        )

                        if drift_result.should_reject:
                            logger.warning(
                                f"Rejecting LLM fix for {example.example_id} due to context drift: "
                                f"{drift_result.original_context} -> {drift_result.fixed_context}"
                            )
                            # Store drift evidence in failure reason
                            drift_details = {
                                "drift_detected": True,
                                "original_context": drift_result.original_context,
                                "fixed_context": drift_result.fixed_context,
                                "rejection_reason": drift_result.rejection_reason
                            }
                            self.db.update_example_status(
                                run_id=run_id,
                                example_id=example.example_id,
                                status=ExampleStatus.COMPILE_FAILED,
                                failure_reason=f"context_drift_detected: {json.dumps(drift_details)}"
                            )
                            # Skip this fix attempt and continue to next retry
                            continue

                    # Track 2: No-change loop detection
                    if previous_code is not None and self._is_code_identical(previous_code, fixed_code):
                        logger.warning(
                            f"No-change loop detected for {example.example_id} on attempt {attempt + 1}: "
                            f"LLM returned identical code. Escalating early."
                        )
                        # Emit telemetry for no-change detection
                        try:
                            from ..core.telemetry import emit_telemetry_event
                            emit_telemetry_event(
                                self.db,
                                run_id,
                                family,
                                event_type='no_change_loop_detected',
                                phase='compilation',
                                metadata={
                                    'example_id': example.example_id,
                                    'retry_attempt': attempt + 1,
                                    'escalation_reason': 'identical_code_returned',
                                }
                            )
                        except Exception as e:
                            logger.debug(f"Failed to emit no-change telemetry: {e}")
                        # Break early - no point retrying if LLM is stuck
                        break

                    # Update previous code for next iteration
                    previous_code = fixed_code

                    # Drift detection: Compare fixed code against ORIGINAL code
                    # Use startup decision, not runtime check
                    if self._drift_enabled and self._drift_detector:
                        drift_score, similarity = self._drift_detector.compute_drift(
                            original_code=example.original_code,
                            fixed_code=fixed_code
                        )

                        # Log drift score for observability
                        if global_config.drift.log_all_drift_scores:
                            logger.debug(
                                f"Drift for {example.example_id} attempt {attempt+1}: "
                                f"score={drift_score:.3f}, similarity={similarity:.3f}"
                            )

                        # Check threshold
                        if drift_score > global_config.drift.threshold:
                            logger.warning(
                                f"Drift threshold exceeded for {example.example_id}: "
                                f"{drift_score:.3f} > {global_config.drift.threshold}"
                            )

                            if global_config.drift.fail_on_exceed:
                                # Store drift score and abort fix loop
                                self.db.update_snippet(
                                    example.example_id,
                                    drift_score=drift_score,
                                    drift_similarity=similarity
                                )
                                self.db.update_example_status(
                                    example.example_id,
                                    ExampleStatus.COMPILE_FAILED,
                                    failure_reason=f"Drift threshold exceeded ({drift_score:.3f} > {global_config.drift.threshold})",
                                    run_id=run_id,
                                )
                                stats['failed'] += 1
                                logger.info(f"Example {example.example_id} marked as compile-failed due to drift")
                                break  # Exit retry loop

                    # Update example and retry compilation
                    example.compilable_code = fixed_code
                    success, result = self.get_compilation_service(family).compile_example(
                        example, family_config
                    )
                    
                    # Record attempt
                    self.get_compilation_service(family).record_attempt(
                        example.example_id,
                        result,
                        current_code,
                        fixed_code if success else None,
                        payload.to_prompt(),
                        llm_response.content,
                        run_id=run_id,
                    )
                    
                    if success:
                        # Stage 5.5: Final Review (if enabled and code was LLM-fixed)
                        only_review_llm_fixed = getattr(global_config.final_review, 'only_review_llm_fixed', True)
                        if global_config.final_review.enabled and only_review_llm_fixed:
                            logger.debug(f"Running Stage 5.5 final review for {example.example_id}")

                            review = self.llm_service.final_review(
                                original_code=example.original_code,
                                fixed_code=fixed_code,
                            )
                            if self.llm_service._last_response:
                                self._emit_llm_telemetry(
                                    run_id=run_id, family=family,
                                    llm_response=self.llm_service._last_response,
                                    context_type="final_review", phase="compilation",
                                    example_id=example.example_id,
                                )

                            if review['success'] and not review['intent_preserved']:
                                # Intent drift detected - check confidence threshold
                                confidence_threshold = getattr(global_config.final_review, 'confidence_threshold', 0.7)
                                if review['confidence'] >= confidence_threshold:
                                    logger.warning(
                                        f"Intent drift detected for {example.example_id}: {review['explanation']} "
                                        f"(confidence: {review['confidence']})"
                                    )
                                    stats['failed'] += 1
                                    drift_reason = f"Intent drift: {review['explanation']}"
                                    if review.get('drift_details'):
                                        drift_reason += f" | Details: {', '.join(review['drift_details'][:3])}"

                                    self.db.update_example_status(
                                        example.example_id,
                                        ExampleStatus.COMPILE_FAILED,
                                        failure_reason=drift_reason,
                                        run_id=run_id,
                                    )
                                    logger.info(f"Example {example.example_id} marked as needs-fix due to intent drift")
                                    continue  # Skip to next example
                                else:
                                    logger.info(
                                        f"Intent drift detected but confidence {review['confidence']:.2f} "
                                        f"below threshold {confidence_threshold}, accepting fix"
                                    )
                            elif not review['success']:
                                # Review failed - log warning but continue
                                logger.warning(
                                    f"Final review failed for {example.example_id}: {review.get('error', 'Unknown error')}"
                                )
                            else:
                                # Intent preserved - log success
                                logger.debug(
                                    f"Final review passed for {example.example_id}: {review['explanation']} "
                                    f"(confidence: {review['confidence']})"
                                )

                        stats['compiled_with_fix'] += 1
                        self._llm_fixed_example_ids.add(example.example_id)
                        try:
                            from ..core.telemetry import emit_telemetry_event
                            emit_telemetry_event(
                                self.db, run_id, family,
                                event_type='example_compiled',
                                phase='compilation',
                                example_id=example.example_id,
                                success=True,
                                metadata={'first_try': False, 'attempts': attempt + 1},
                            )
                        except Exception:
                            pass
                        self.db.update_example_status(example.example_id, ExampleStatus.COMPILABLE, run_id=run_id)
                        self.db.update_example_code(example.example_id, compilable_code=fixed_code, run_id=run_id)

                        # Store final drift score for successful fix
                        if self._drift_enabled and self._drift_detector:
                            final_drift, final_sim = self._drift_detector.compute_drift(
                                original_code=example.original_code,
                                fixed_code=fixed_code
                            )
                            self.db.update_snippet(
                                example.example_id,
                                drift_score=final_drift,
                                drift_similarity=final_sim
                            )
                        # Store LLM-fixed compilable example in vector DB
                        if self.vector_db_service.is_available():
                            try:
                                # Use final drift score (ID-05: Pass drift to vector DB)
                                drift_to_store = None
                                if self._drift_enabled and self._drift_detector:
                                    drift_to_store = final_drift  # From lines 701-710

                                self.vector_db_service.add_example(
                                    example_id=example.example_id,
                                    code=fixed_code,
                                    metadata={
                                        'family': family,
                                        'source': 'pipeline_compilation_llm_fixed',
                                        'verified': False,  # Not runtime verified yet
                                        'compilable': True,
                                        'file_path': example.file_path,
                                        'fix_attempt': attempt + 1,
                                    },
                                    drift_score=drift_to_store  # ID-05: Pass drift score
                                )
                            except Exception as e:
                                logger.debug(f"Failed to add LLM-fixed compilable example to vector DB: {e}")
                        fixed = True
                        break
                    
                    current_code = fixed_code
                
                if not fixed:
                    # Task 4: Try example-repo fallback for API mismatch errors
                    error_text = '\n'.join(result.errors[:5])
                    if self._is_api_mismatch_error(error_text):
                        fallback = self._search_example_repo_fallback(
                            example.original_code, family_config, error_text
                        )
                        if fallback:
                            substitute_code, fix_strategy = fallback
                            logger.info(
                                f"Using {fix_strategy} for {example.example_id} (API mismatch)"
                            )
                            # Try compiling the substitute
                            example.compilable_code = substitute_code
                            sub_success, sub_result = self.get_compilation_service(family).compile_example(
                                example, family_config
                            )
                            self.get_compilation_service(family).record_attempt(
                                example.example_id,
                                sub_result,
                                example.original_code,
                                substitute_code if sub_success else None,
                                f"fix_strategy={fix_strategy}",
                                substitute_code[:500],
                                run_id=run_id,
                            )
                            if sub_success:
                                stats['compiled_with_fix'] += 1
                                try:
                                    from ..core.telemetry import emit_telemetry_event
                                    emit_telemetry_event(
                                        self.db, run_id, family,
                                        event_type='example_compiled',
                                        phase='compilation',
                                        example_id=example.example_id,
                                        success=True,
                                        metadata={'first_try': False, 'substitution': True},
                                    )
                                except Exception:
                                    pass
                                self.db.update_example_status(
                                    example.example_id, ExampleStatus.COMPILABLE, run_id=run_id
                                )
                                self.db.update_example_code(
                                    example.example_id, compilable_code=substitute_code, run_id=run_id
                                )
                                continue  # Skip the failure path

                    stats['failed'] += 1
                    self.db.update_example_status(
                        example.example_id,
                        ExampleStatus.COMPILE_FAILED,
                        failure_reason='\n'.join(result.errors[:3]),
                        run_id=run_id,
                    )
                    
            except Exception as e:
                logger.error(f"Error compiling {example.example_id}: {e}")
                stats['errors'] += 1

                # Mark as NEEDS_REVIEW so it doesn't remain DISCOVERED
                self.db.update_example_status(
                    example.example_id,
                    ExampleStatus.NEEDS_REVIEW,
                    escalation_reason="unprocessed_in_run",
                    failure_reason=f"Exception during processing: {str(e)[:200]}",
                    run_id=run_id,
                )

        # CRITICAL: Ensure no examples remain in DISCOVERED state
        # Any example that was retrieved but not processed must be marked NEEDS_REVIEW
        remaining_discovered = self.db.get_examples_by_family(
            family, ExampleStatus.DISCOVERED, limit=None, run_id=run_id
        )
        if remaining_discovered:
            logger.warning(
                f"Found {len(remaining_discovered)} examples still in DISCOVERED state - marking as NEEDS_REVIEW"
            )
            for leftover in remaining_discovered:
                self.db.update_example_status(
                    leftover.example_id,
                    ExampleStatus.NEEDS_REVIEW,
                    escalation_reason="unprocessed_in_run",
                    failure_reason="Example was not processed during compilation phase",
                    run_id=run_id,
                )
                stats['failed'] += 1

        stats['verified'] = stats['compiled_first_try'] + stats['compiled_with_fix']
        return stats
    
    def _run_runtime_phase(
        self,
        run_id: str,
        family: str,
        family_config: FamilyConfig,
        max_examples: Optional[int],
        skip_llm_fixes: bool,
        skip_llm_runtime_fixes: bool = False,
    ) -> Dict[str, Any]:
        """Run Phase C: Runtime Verification Loop."""
        # Import failure tracking functions at function scope to avoid UnboundLocalError
        from .failure_tracker import (
            track_infra_missing_test_data,
            track_infra_blocked_rar,
            track_infra_blocked_7z,
        )

        stats = {
            'total_processed': 0,
            'passed_first_try': 0,
            'passed_with_fix': 0,
            'failed': 0,
            'errors': 0,
            'llm_fix_attempts': 0,
        }

        # Pre-runtime backfill check (if enabled)
        global_config = self.config_manager.load_global_config()

        if global_config.backfill.auto_enabled:
            test_data_path = resolve_test_data_path(family, family_config)

            # Determine if backfill is needed:
            # 1. test_data_path is None (directory doesn't exist at all)
            # 2. Directory exists but repo test data was never copied (no marker file)
            _needs_backfill = (test_data_path is None)
            _marker_missing = False
            if not _needs_backfill and test_data_path and family_config.example_repo:
                _backfill_marker = test_data_path / ".backfill_complete"
                if not _backfill_marker.exists():
                    _needs_backfill = True
                    _marker_missing = True  # Directory exists but repo data never copied

            if _needs_backfill and family_config.test_data.local_path:
                logger.info(f"Test data missing or incomplete for {family}, attempting auto-backfill...")

                try:
                    from ..services.backfill_service import BackfillService

                    backfill_service = BackfillService(
                        config_manager=self.config_manager,
                        timeout_seconds=global_config.backfill.github_timeout_seconds
                    )

                    # Force backfill when marker is missing — directory may have only
                    # fixture-generated placeholders, not real repo test data
                    result = backfill_service.backfill_test_data(family=family, force=_marker_missing)

                    if result.success and not result.skipped:
                        logger.info(f"Auto-backfilled {result.files_copied} test data files for {family}")
                        stats['backfill_files_copied'] = result.files_copied
                        # Re-resolve test_data_path after backfill
                        test_data_path = resolve_test_data_path(family, family_config)
                        # Write marker to prevent redundant backfill on next run
                        _marker_dir = test_data_path or (Path("artifacts/backfill") / family / "test-data")
                        _marker_file = _marker_dir / ".backfill_complete"
                        try:
                            _marker_dir.mkdir(parents=True, exist_ok=True)
                            _marker_file.write_text(f"backfilled {result.files_copied} files")
                        except Exception:
                            pass
                    elif result.skipped:
                        logger.info(f"Test data backfill skipped: {result.skip_reason}")
                    elif result.error:
                        logger.warning(f"Test data backfill failed: {result.error}")
                        stats['backfill_error'] = result.error

                except Exception as e:
                    # Don't fail the pipeline if backfill fails
                    logger.warning(f"Backfill error (continuing anyway): {e}")
                    stats['backfill_error'] = str(e)

        # Get examples to process
        # When skip_llm_fixes=False, also process RUNTIME_FAILED examples for retry
        if skip_llm_fixes:
            examples = self.db.get_examples_by_family(family, ExampleStatus.COMPILABLE, max_examples, run_id=run_id)
        else:
            # Get both COMPILABLE and RUNTIME_FAILED for LLM fixing
            compilable = self.db.get_examples_by_family(family, ExampleStatus.COMPILABLE, max_examples, run_id=run_id)
            failed = self.db.get_examples_by_family(family, ExampleStatus.RUNTIME_FAILED, max_examples, run_id=run_id)
            examples = compilable + failed
        
        # Get test data path and info (using resolution helper)
        test_data_path = resolve_test_data_path(family, family_config)
        test_data_info = ""
        if test_data_path:
            # Build comprehensive test data info for LLM context
            test_files = []
            for f in test_data_path.iterdir():
                if f.is_file():
                    test_files.append(f"- {f.name}")
                elif f.is_dir():
                    test_files.append(f"- {f.name}/ (directory)")

            test_data_info = "Available test files:\n" + "\n".join(test_files[:20])

            # Add file aliases mapping if configured (CRITICAL for LLM placeholder replacement)
            if family_config.runtime_validation.file_aliases:
                alias_lines = []
                for real_file, aliases in family_config.runtime_validation.file_aliases.items():
                    alias_lines.append(f"  {real_file} -> replaces: {', '.join(aliases)}")
                test_data_info += "\n\nFile Aliases (use the real file when you see these placeholder names):\n" + "\n".join(alias_lines)
                logger.info(f"Added {len(alias_lines)} file aliases to test_data_info for LLM context")
            else:
                logger.warning("No file aliases configured - LLM will not know about placeholder mappings!")

            # Add tag summary from inventory if available
            if family_config.test_data.inventory_path:
                inventory_path = Path(family_config.test_data.inventory_path)
                if inventory_path.exists():
                    try:
                        import json
                        with open(inventory_path, 'r', encoding='utf-8') as f:
                            inventory = json.load(f)

                        # Add tag summary with example files
                        tag_summary = inventory.get('tag_summary', {})
                        if tag_summary:
                            test_data_info += "\n\nTest Data Tags (with example files):"
                            # Show top 5 tags with sample files
                            for tag, count in list(tag_summary.items())[:5]:
                                test_data_info += f"\n  {tag} ({count} files):"
                                # Find up to 3 example files with this tag
                                examples_shown = 0
                                for entry in inventory.get('entries', []):
                                    if tag in entry.get('tags', []) and examples_shown < 3:
                                        test_data_info += f" {entry['path']}"
                                        examples_shown += 1
                                        if examples_shown < 3:
                                            test_data_info += ","

                            logger.info(f"Added tag summary from inventory ({len(tag_summary)} tags)")
                    except Exception as e:
                        logger.warning(f"Failed to load inventory: {e}")

        max_retries = global_config.llm.max_retries

        # Phase and per-example timeout enforcement (Fix 4: RC3)
        import time as _time
        _rt_phase_start = _time.time()
        _rt_phase_timeout = global_config.timeouts.per_phase_seconds
        _rt_per_ex_timeout = global_config.timeouts.per_example_seconds
        _rt_total = len(examples)
        logger.info(f"[Phase C] Starting runtime: {_rt_total} examples, "
                     f"phase_timeout={_rt_phase_timeout}s, per_example_timeout={_rt_per_ex_timeout}s")

        for _ri, example in enumerate(examples):
            # Phase-level timeout check
            _rt_elapsed = _time.time() - _rt_phase_start
            if _rt_elapsed > _rt_phase_timeout:
                logger.error(
                    f"[Phase C] Phase timeout exceeded: {_rt_elapsed:.0f}s > {_rt_phase_timeout}s. "
                    f"Processed {_ri}/{_rt_total}. Aborting runtime phase."
                )
                stats['phase_timeout'] = True
                break

            # Progress logging every 10 examples
            _rt_log_interval = 10 if _rt_total >= 20 else 1
            if _ri > 0 and _ri % _rt_log_interval == 0:
                _rt_rate = _ri / (_rt_elapsed / 60) if _rt_elapsed > 0 else 0
                logger.info(
                    f"[Phase C] {_ri}/{_rt_total} ({100*_ri/_rt_total:.1f}%) "
                    f"rate={_rt_rate:.1f}/min elapsed={_rt_elapsed:.0f}s "
                    f"ok={stats['passed_first_try']+stats['passed_with_fix']} "
                    f"fail={stats['failed']}"
                )

            stats['total_processed'] += 1
            
            try:
                # Initialize tracking variable
                last_result = None
                
                # Copy compilable code to verified for execution
                example.verified_code = example.compilable_code

                # Proactive required_files resolution: resolve missing required files
                # via fixture resolver BEFORE the availability check
                fixture_resolver_pre = self.registry.get_fixture_resolver(family)
                if fixture_resolver_pre and test_data_path and family_config.runtime_validation.required_files:
                    for req_file in family_config.runtime_validation.required_files:
                        req_path = Path(test_data_path) / req_file
                        if not req_path.exists():
                            # Check file_aliases first (Dict[str, List[str]])
                            aliases = getattr(family_config.runtime_validation, 'file_aliases', {}) or {}
                            alias_targets = aliases.get(req_file, [])
                            resolved_via_alias = False
                            for alias_target in alias_targets:
                                alias_path = Path(test_data_path) / alias_target
                                if alias_path.exists():
                                    # Copy aliased file to expected location
                                    req_path.parent.mkdir(parents=True, exist_ok=True)
                                    import shutil
                                    shutil.copy2(alias_path, req_path)
                                    logger.info(
                                        f"Resolved required file via alias: {req_file} -> {alias_target}"
                                    )
                                    resolved_via_alias = True
                                    break
                            if resolved_via_alias:
                                continue

                            # Fall back to fixture resolver
                            resolved = fixture_resolver_pre.resolve_missing_file(
                                req_file, Path(test_data_path), example_id=None
                            )
                            if resolved:
                                logger.info(
                                    f"Proactive required_file resolution: {req_file} -> {resolved}"
                                )

                # Pre-flight check: Verify test data availability before runtime execution
                # This prevents wasting LLM calls on infrastructure issues
                if test_data_path and family_config.runtime_validation.required_files:
                    all_available, missing_files = self.get_runtime_service(family).check_test_data_availability(
                        test_data_path=test_data_path,
                        runtime_config=family_config.runtime_validation,
                    )

                    if not all_available:
                        # Infrastructure failure: missing test data files
                        # Classify the specific infra blocker type
                        # (imports moved to top of function)

                        # Detect specific infra blockers
                        rar_missing = any(f.endswith('.rar') for f in missing_files)
                        sevenz_missing = any(f.endswith('.7z') for f in missing_files)

                        if rar_missing:
                            # RAR fixture missing - deterministic INFRA_BLOCKED
                            track_infra_blocked_rar(
                                db=self.db,
                                run_id=run_id,
                                example_id=example.example_id,
                                reason=f"Missing RAR fixtures: {', '.join(f for f in missing_files if f.endswith('.rar'))}",
                            )
                            infra_escalation_reason = "missing_rar_fixture"
                        elif sevenz_missing:
                            # 7z fixture missing - deterministic INFRA_BLOCKED
                            track_infra_blocked_7z(
                                db=self.db,
                                run_id=run_id,
                                example_id=example.example_id,
                                reason=f"Missing 7z fixtures: {', '.join(f for f in missing_files if f.endswith('.7z'))}",
                            )
                            infra_escalation_reason = "missing_7z_fixture"
                        else:
                            # Generic missing test data
                            track_infra_missing_test_data(
                                db=self.db,
                                run_id=run_id,
                                example_id=example.example_id,
                                missing_files=missing_files,
                            )
                            infra_escalation_reason = "missing_test_data"

                        # Phase-2: Use INFRA_BLOCKED status instead of NEEDS_REVIEW
                        example.escalation_reason = infra_escalation_reason

                        # Mark example as INFRA_BLOCKED with specific reason
                        self.db.update_example_status(
                            example.example_id,
                            ExampleStatus.INFRA_BLOCKED,
                            escalation_reason=infra_escalation_reason,
                            run_id=run_id,
                        )

                        # Log and skip to next example
                        logger.warning(
                            f"Example {example.example_id}: INFRA_BLOCKED - missing test data files: "
                            f"{', '.join(missing_files[:5])} (reason: {infra_escalation_reason})"
                        )
                        stats['infra_blocked'] = stats.get('infra_blocked', 0) + 1
                        continue

                # Track first failure separately from last result (TASK-1A fix)
                first_failure_result = None

                # Proactive fixture resolution: scan code for file references
                # and resolve missing ones BEFORE first runtime attempt
                fixture_resolver = self.registry.get_fixture_resolver(family)
                if fixture_resolver and test_data_path:
                    code_to_scan = example.compilable_code or example.original_code or ""
                    pre_results = fixture_resolver.precheck_code_references(
                        code_to_scan, workspace_dir=None  # test-data placement only
                    )
                    for pr in pre_results:
                        if pr.resolved:
                            logger.info(
                                f"Proactive fixture for {example.example_id}: "
                                f"{pr.filename} via {pr.method}"
                            )
                            stats['fixture_proactive'] = stats.get('fixture_proactive', 0) + 1

                success, result = self.get_runtime_service(family).execute_example(
                    example, family_config, test_data_path
                )
                last_result = result  # Track result for failure reporting

                # Capture first failure for accurate error reporting
                if not success:
                    first_failure_result = result

                # Record runtime attempt
                sample_ref = str(test_data_path) if test_data_path else "none"
                self.get_runtime_service(family).record_attempt(
                    example_id=example.example_id,
                    family=family,
                    runtime_result=result,
                    sample_ref=sample_ref,
                    scenario="first_try",
                    retrieved_examples=None,
                    llm_request=None,
                    llm_response=None,
                    run_id=run_id,
                )

                if success:
                    stats['passed_first_try'] += 1
                    self.db.update_example_status(example.example_id, ExampleStatus.VERIFIED, run_id=run_id)
                    self.db.update_example_code(
                        example.example_id,
                        verified_code=example.compilable_code,
                        run_id=run_id,
                    )
                    # Store verified example in vector DB for future similarity search
                    if self.vector_db_service.is_available():
                        try:
                            self.vector_db_service.add_example(
                                example_id=example.example_id,
                                code=example.compilable_code,
                                metadata={
                                    'family': family,
                                    'source': 'pipeline_runtime',
                                    'verified': True,
                                    'file_path': example.file_path,
                                },
                                drift_score=None  # ID-05: No drift (verified first try)
                            )
                        except Exception as e:
                            logger.debug(f"Failed to add verified example to vector DB: {e}")
                    continue
                
                # Runtime failed - check for misclassified compile errors first (Phase-2 Task 4)
                # If runtime output contains CS#### compiler errors, it's actually a compile failure
                runtime_stderr = result.stderr if result else ""
                runtime_stdout = result.stdout if result else ""
                runtime_output = f"{runtime_stderr}\n{runtime_stdout}"

                # Check for C# compiler error codes (CSxxxx)
                compile_error_pattern = r'\bCS\d{4}\b'
                has_compile_errors = re.search(compile_error_pattern, runtime_output)

                if has_compile_errors:
                    logger.warning(
                        f"Runtime failure for {example.example_id} contains compile errors (CSxxxx). "
                        f"Reclassifying as COMPILE_FAILED and routing through substitution."
                    )

                    # Extract the compile errors
                    compile_errors = re.findall(r'error CS\d{4}:.*', runtime_output)
                    if not compile_errors:
                        compile_errors = [runtime_stderr[:200]]  # Fallback

                    # Create a fake compile result for substitution
                    fake_compile_result = CompileResult(
                        success=False,
                        exit_code=1,
                        stdout="",
                        stderr=runtime_stderr,
                        duration_ms=0,
                        dll_version="",
                        errors=compile_errors,
                        warnings=[],
                    )

                    # Try substitution first
                    should_sub, trigger_info = self.get_substitution_service(family).should_substitute(compile_errors)

                    if should_sub and trigger_info:
                        logger.info(
                            f"Substitution triggered for misclassified {example.example_id}: "
                            f"{trigger_info['reason']}"
                        )

                        substitute_result = self.get_substitution_service(family).find_substitute_example(
                            original_code=example.compilable_code,
                            trigger_info=trigger_info,
                            family=family,
                            original_app_context=example.app_context,
                        )

                        if substitute_result:
                            substitute_code, substitute_id, metadata = substitute_result
                            metadata['original_example_id'] = example.example_id
                            metadata['misclassified_from_runtime'] = True

                            # Re-compile with substitute
                            example.compilable_code = substitute_code
                            comp_success, comp_result = self.get_compilation_service(family).compile_example(
                                example, family_config
                            )

                            if comp_success:
                                # Substitute compiled - now try runtime
                                runtime_success, runtime_result = self.get_runtime_service(family).execute_example(
                                    example, family_config, test_data_path
                                )

                                if runtime_success:
                                    logger.info(
                                        f"Substitution fixed misclassified compile error for {example.example_id}"
                                    )
                                    self.db.update_example_status(
                                        example.example_id,
                                        ExampleStatus.VERIFIED,
                                        run_id=run_id,
                                    )
                                    self.db.update_example_code(
                                        example.example_id,
                                        verified_code=substitute_code,
                                        run_id=run_id,
                                    )
                                    stats['passed_first_try'] = stats.get('passed_first_try', 0) + 1
                                    stats['runtime_reclassified'] = stats.get('runtime_reclassified', 0) + 1
                                    continue

                    # Substitution didn't work - mark as COMPILE_FAILED
                    logger.info(
                        f"Reclassifying {example.example_id} as COMPILE_FAILED (contains CSxxxx errors)"
                    )
                    self.db.update_example_status(
                        example.example_id,
                        ExampleStatus.COMPILE_FAILED,
                        failure_reason=f"Misclassified runtime failure (compile errors): {compile_errors[0][:100]}",
                        run_id=run_id,
                    )
                    stats['failed'] = stats.get('failed', 0) + 1
                    stats['runtime_reclassified'] = stats.get('runtime_reclassified', 0) + 1
                    continue

                # Runtime failed - try deterministic fixes first (Task 5)
                deterministic_fixed = False
                current_code = example.compilable_code

                # Task 5: Classify runtime error and try deterministic fix
                error_category = self.get_runtime_service(family).classify_runtime_error(result)
                logger.debug(f"Runtime error category for {example.example_id}: {error_category}")

                # Task 5: Escalate missing RAR file as INFRA_BLOCKED
                # BUT ONLY if the fixture is TRULY missing (recursive lookup + inventory check fails)
                if error_category == "missing_rar_file":
                    from .escalation_classifier import EscalationReason

                    # CRITICAL: Verify the RAR file is actually missing
                    # Extract RAR filename from error message
                    rar_filename = None
                    error_text = (result.stderr or "") + (result.exception_message or "")
                    # Look for .rar files in error message
                    rar_match = re.search(r'(["\']?)([^"\']+\.rar)\1', error_text, re.IGNORECASE)
                    if rar_match:
                        rar_filename = rar_match.group(2).replace('\\', '/').split('/')[-1]

                    # Check if this file exists anywhere in test-data (recursive)
                    fixture_truly_missing = True
                    if rar_filename and test_data_path and test_data_path.exists():
                        found_path = self.get_runtime_service(family).find_test_file(
                            required_name=rar_filename,
                            source_dir=test_data_path,
                            file_aliases=family_config.runtime_validation.file_aliases,
                            inventory=None
                        )
                        if found_path is not None:
                            # Fixture EXISTS but runtime still failed - this is a SYSTEM BUG
                            fixture_truly_missing = False
                            logger.warning(
                                f"Example {example.example_id}: RAR file '{rar_filename}' exists at "
                                f"{found_path} but runtime failed - marking as NEEDS_REVIEW (file_not_copied)"
                            )

                    if fixture_truly_missing:
                        # RAR fixture is truly missing - mark INFRA_BLOCKED
                        logger.info(f"Example {example.example_id}: INFRA_BLOCKED (missing_rar_fixture)")

                        track_infra_blocked_rar(
                            db=self.db,
                            run_id=run_id,
                            example_id=example.example_id,
                            reason=f"Missing RAR fixture at runtime: {rar_filename or 'unknown'}",
                        )

                        self.db.update_example_status(
                            example.example_id,
                            ExampleStatus.INFRA_BLOCKED,
                            escalation_reason=EscalationReason.INFRA_BLOCKED_RAR_FIXTURE,
                            run_id=run_id,
                        )
                        stats['infra_blocked'] = stats.get('infra_blocked', 0) + 1
                        continue
                    else:
                        # Fixture exists but wasn't copied - system bug
                        # Continue to runtime failure handling below
                        error_category = "file_not_copied"

                # Task 5: Escalate password errors as INFRA_BLOCKED
                # But first try password normalization if not already applied
                if error_category == "invalid_password":
                    from .escalation_classifier import EscalationReason
                    from ..services.semantic_microfixes import fix_placeholder_passwords as _fix_pw

                    current_pw_code = example.compilable_code or example.original_code or ""
                    fixed_pw_code, pw_fix_desc = _fix_pw(current_pw_code)
                    if pw_fix_desc:
                        # Password was a placeholder — fix and retry runtime once
                        logger.info(f"Pre-escalation password fix for {example.example_id}: {pw_fix_desc}")
                        example.compilable_code = fixed_pw_code
                        retry_result = self.get_runtime_service(family).run_example(
                            example, family_config, test_data_path
                        )
                        if retry_result.success:
                            logger.info(f"Example {example.example_id}: password retry PASSED")
                            stats['passed_first_try'] = stats.get('passed_first_try', 0) + 1
                            stats['verified'] = stats.get('verified', 0) + 1
                            continue
                        # Retry also failed — fall through to escalation

                    logger.info(f"Example {example.example_id}: INFRA_BLOCKED (requires_password_secret)")

                    # Track the infrastructure blocker
                    track_failure(
                        db=self.db,
                        run_id=run_id,
                        phase="Phase D (Runtime)",
                        failure_category=FailureCategory.INFRA_BLOCKED_PASSWORD,
                        example_id=example.example_id,
                        error_category="requires_password",
                        error_message="Password/secret required for archive",
                        resolution=FailureResolution.ABANDONED,
                        metadata={'infra_type': 'password_required'},
                    )

                    self.db.update_example_status(
                        example.example_id,
                        ExampleStatus.INFRA_BLOCKED,
                        escalation_reason=EscalationReason.INFRA_BLOCKED_PASSWORD,
                        run_id=run_id,
                    )
                    stats['infra_blocked'] = stats.get('infra_blocked', 0) + 1
                    continue

                # Task 5: Escalate 7z format issues as INFRA_BLOCKED
                if error_category == "sevenz_format_issue":
                    from .escalation_classifier import EscalationReason
                    logger.info(f"Example {example.example_id}: INFRA_BLOCKED (missing_7z_fixture)")

                    # Track the infrastructure blocker
                    track_infra_blocked_7z(
                        db=self.db,
                        run_id=run_id,
                        example_id=example.example_id,
                        reason="7z format issue at runtime",
                    )

                    self.db.update_example_status(
                        example.example_id,
                        ExampleStatus.INFRA_BLOCKED,
                        escalation_reason=EscalationReason.INFRA_BLOCKED_7Z_FIXTURE,
                        run_id=run_id,
                    )
                    stats['infra_blocked'] = stats.get('infra_blocked', 0) + 1
                    continue

                if error_category in ("missing_file", "missing_directory"):
                    # --- Fixture resolution: fix the ENVIRONMENT first ---
                    # Try to provide the missing file/directory before fixing the code
                    if not fixture_resolver:
                        fixture_resolver = self.registry.get_fixture_resolver(family)
                    if fixture_resolver and test_data_path:
                        from ..services.fixture_resolver_service import extract_missing_filename, extract_missing_dirname
                        error_text = (result.stderr or "") + (result.exception_message or "")

                        if error_category == "missing_file":
                            missing_name = extract_missing_filename(error_text)
                        else:
                            missing_name = extract_missing_dirname(error_text)

                        if missing_name:
                            resolve_result = fixture_resolver.resolve_missing_file(
                                missing_name
                            ) if error_category == "missing_file" else fixture_resolver.resolve_missing_directory(
                                missing_name
                            )

                            if resolve_result.resolved:
                                logger.info(
                                    f"Fixture resolved for {example.example_id}: "
                                    f"{missing_name} via {resolve_result.method}"
                                )
                                # Re-execute: _copy_test_data will now find the new file
                                success, result = self.get_runtime_service(family).execute_example(
                                    example, family_config, test_data_path
                                )
                                self.get_runtime_service(family).record_attempt(
                                    example_id=example.example_id,
                                    family=family,
                                    runtime_result=result,
                                    sample_ref=str(test_data_path) if test_data_path else "none",
                                    scenario=f"fixture_resolved_{error_category}",
                                    retrieved_examples=None,
                                    llm_request=None,
                                    llm_response=None,
                                    run_id=run_id,
                                )
                                if success:
                                    deterministic_fixed = True
                                    stats['fixture_resolved'] = stats.get('fixture_resolved', 0) + 1
                                    self.db.update_example_status(
                                        example.example_id, ExampleStatus.VERIFIED, run_id=run_id
                                    )
                                    self.db.update_example_code(
                                        example.example_id,
                                        verified_code=current_code,
                                        run_id=run_id,
                                    )
                                    logger.info(f"Fixture resolution succeeded for {example.example_id}")
                                    continue
                                # Still failing — fall through to code fixes

                    # --- Deterministic code fixes (existing) ---
                    # Get available test data files for substitution
                    available_files = []
                    if test_data_path and test_data_path.exists():
                        for f in test_data_path.rglob("*"):
                            if f.is_file():
                                available_files.append(f.name)

                    # Try deterministic fix
                    fixed_code = self.get_runtime_service(family).apply_deterministic_fix(
                        current_code, error_category, available_files
                    )

                    if fixed_code and fixed_code != current_code:
                        logger.info(f"Applied deterministic {error_category} fix for {example.example_id}")

                        # Re-run with fixed code
                        example.compilable_code = fixed_code
                        success, result = self.get_runtime_service(family).execute_example(
                            example, family_config, test_data_path
                        )

                        # Record deterministic fix attempt
                        self.get_runtime_service(family).record_attempt(
                            example_id=example.example_id,
                            family=family,
                            runtime_result=result,
                            sample_ref=str(test_data_path) if test_data_path else "none",
                            scenario=f"deterministic_fix_{error_category}",
                            retrieved_examples=None,
                            llm_request=None,
                            llm_response=None,
                            run_id=run_id,
                        )

                        if success:
                            deterministic_fixed = True
                            stats['deterministic_fixes'] = stats.get('deterministic_fixes', 0) + 1
                            self.db.update_example_status(example.example_id, ExampleStatus.VERIFIED, run_id=run_id)
                            self.db.update_example_code(
                                example.example_id,
                                verified_code=fixed_code,
                                run_id=run_id,
                            )
                            logger.info(f"Deterministic fix succeeded for {example.example_id}")
                            continue
                        else:
                            current_code = fixed_code  # Use fixed code for subsequent LLM attempts

                if deterministic_fixed:
                    continue

                # If skip_llm_fixes is True and deterministic fix didn't work, mark as failed
                if skip_llm_fixes:
                    stats['failed'] += 1
                    failure_reason = (
                        result.exception_message
                        or (result.stderr[:200] if result.stderr else None)
                        or "Unknown runtime error"
                    )

                    # Check if this should be INFRA_BLOCKED instead of RUNTIME_FAILED
                    # FileNotFoundException for missing fixtures should be INFRA_BLOCKED
                    if error_category == "missing_file" and result.exception_type == "System.IO.FileNotFoundException":
                        # Mark as INFRA_BLOCKED if it's a missing test fixture
                        self.db.update_example_status(
                            example.example_id,
                            ExampleStatus.INFRA_BLOCKED,
                            escalation_reason="missing_test_data",
                            run_id=run_id,
                        )
                        logger.info(f"Example {example.example_id}: INFRA_BLOCKED (missing file: {failure_reason[:100]})")
                        stats['infra_blocked'] = stats.get('infra_blocked', 0) + 1
                    else:
                        # Try learned patterns for runtime errors before marking as RUNTIME_FAILED
                        runtime_pattern_fixed = False
                        strategy_config = self._get_fix_strategy_config()

                        learned_service = self.get_learned_patterns_service(self._current_family)
                        if strategy_config.get('enable_learned_patterns', False) and learned_service:

                            # Extract error signatures from runtime result
                            error_messages = []
                            if result.exception_message:
                                error_messages.append(result.exception_message)
                            if result.stderr:
                                error_messages.append(result.stderr)

                            if error_messages:
                                from ..services.learned_patterns_service import extract_all_error_signatures

                                error_signatures = extract_all_error_signatures(error_messages)
                                logger.info(f"Runtime error signatures for {example.example_id}: {error_signatures}")

                                # Try patterns for each error signature
                                for error_sig in error_signatures:
                                    patterns = learned_service.query_patterns(
                                        error_sig,
                                        min_confidence=strategy_config.get('learned_patterns_min_confidence', 0.6),
                                        approved_only=strategy_config.get('learned_patterns_require_approval', True),
                                        limit=strategy_config.get('learned_patterns_max_per_error', 3),
                                    )

                                    for pattern in patterns:
                                        logger.info(f"Trying learned pattern {pattern.id} ({pattern.error_signature}) on {example.example_id}")

                                        # Apply pattern
                                        fixed_code, success, description = learned_service.apply_pattern(
                                            pattern,
                                            current_code,
                                            result.stderr or result.exception_message,
                                            self.llm_service if pattern.requires_llm else None,
                                        )

                                        if success and fixed_code != current_code:
                                            # Recompile and rerun with fixed code
                                            logger.info(f"Pattern {pattern.id} applied: {description}")

                                            # Recompile
                                            compile_result = self.compilation_service.compile_code(fixed_code)
                                            if compile_result.success:
                                                # Rerun
                                                runtime_result_retry = self.runtime_service.execute(fixed_code, timeout_seconds=30)
                                                if runtime_result_retry.exit_code == 0:
                                                    # Success!
                                                    logger.info(f"Runtime pattern {pattern.id} fixed {example.example_id}")
                                                    runtime_pattern_fixed = True

                                                    # Record success
                                                    if strategy_config.get('learned_patterns_feedback_tracking', True):
                                                        learned_service.record_application(
                                                            pattern.id, example.example_id, run_id, success=True
                                                        )

                                                    # Update example with verified code
                                                    self.db.update_example(
                                                        example.example_id,
                                                        verified_code=fixed_code,
                                                        run_id=run_id,
                                                    )
                                                    self.db.update_example_status(
                                                        example.example_id,
                                                        ExampleStatus.VERIFIED,
                                                        run_id=run_id,
                                                    )
                                                    stats['passed_with_fix'] = stats.get('passed_with_fix', 0) + 1
                                                    break  # Exit pattern loop
                                                else:
                                                    # Pattern didn't fix runtime
                                                    if strategy_config.get('learned_patterns_feedback_tracking', True):
                                                        learned_service.record_application(
                                                            pattern.id, example.example_id, run_id, success=False
                                                        )

                                    if runtime_pattern_fixed:
                                        break  # Exit error signature loop

                    if runtime_pattern_fixed:
                        continue  # Patterns fixed it, move to next example

                # Task 5: Limit runtime LLM fixes to 1 iteration
                runtime_max_retries = min(max_retries, 1)

                # Runtime still failed - try LLM fixes if enabled
                # BLOCKER-002: Skip LLM runtime fixes if flag is set (prevents hallucinations)
                if not skip_llm_fixes and not skip_llm_runtime_fixes and self.llm_service.is_available():
                    fixed = False
                    current_code = example.compilable_code

                    # Load API reference context for LLM (LCE-04)
                    # Extract error information from runtime result
                    error_signature = "RUNTIME_ERROR"
                    error_message = ""
                    if result.exception_message:
                        error_message = result.exception_message
                    elif result.stderr:
                        error_message = result.stderr

                    api_context = self._load_api_context(
                        family=family,
                        error_signature=error_signature,
                        error_message=error_message,
                        max_chars=8000
                    )
                    if api_context:
                        logger.debug(f"Loaded {len(api_context)} chars of API context for runtime fix")

                    # Search for similar verified examples (if vector DB available)
                    similar_examples = []
                    retrieved_example_ids = []
                    if self.vector_db_service.is_available():
                        try:
                            import time
                            search_start = time.time()

                            search_results = self.vector_db_service.search_similar(
                                query_code=current_code,
                                family=family,
                                k=global_config.vector_db.search_k,
                                min_similarity=global_config.vector_db.min_similarity_threshold,
                            )

                            search_latency_ms = int((time.time() - search_start) * 1000)
                            stats['vector_search_latency_ms'] = search_latency_ms
                            stats['vector_search_hits'] = len(search_results)

                            for ex_id, ex_code, similarity, ex_metadata in search_results:
                                similar_examples.append(ex_code)
                                retrieved_example_ids.append(ex_id)

                            logger.debug(
                                f"Vector search returned {len(similar_examples)} similar examples "
                                f"for {example.example_id} (latency: {search_latency_ms}ms)"
                            )
                        except Exception as e:
                            logger.warning(f"Vector search failed (continuing without): {e}")
                            stats['vector_search_error'] = str(e)

                    # Track previous code for no-change detection (runtime)
                    previous_runtime_code = None

                    _rt_ex_start = _time.time()
                    for attempt in range(runtime_max_retries):
                        # Per-example timeout guard (Fix 4: RC3)
                        if _time.time() - _rt_ex_start > _rt_per_ex_timeout:
                            logger.warning(
                                f"Per-example runtime timeout for {example.example_id}: "
                                f"{_time.time() - _rt_ex_start:.0f}s > {_rt_per_ex_timeout}s"
                            )
                            break

                        stats['llm_fix_attempts'] += 1

                        # Track 2: Progressive Enrichment - Determine enrichment tier
                        enrichment_tier = self._get_enrichment_tier(attempt, runtime_max_retries)

                        # Track 2: Apply progressive context enrichment (runtime specific)
                        tier_api_context, tier_similar_examples, context_sources = self._apply_progressive_enrichment(
                            enrichment_tier=enrichment_tier,
                            base_api_context=api_context,
                            base_similar_examples=similar_examples,
                            error_logs=result.stderr or "Runtime error",
                            family_config=family_config,
                        )

                        # Track 2: Emit telemetry for retry attempt (runtime)
                        try:
                            from ..core.telemetry import emit_telemetry_event
                            emit_telemetry_event(
                                self.db,
                                run_id,
                                family,
                                event_type='retry_enrichment',
                                phase='runtime',
                                metadata={
                                    'example_id': example.example_id,
                                    'retry_attempt': attempt + 1,
                                    'enrichment_tier': enrichment_tier,
                                    'context_sources': context_sources,
                                    'api_context_chars': len(tier_api_context) if tier_api_context else 0,
                                    'similar_examples_count': len(tier_similar_examples) if tier_similar_examples else 0,
                                }
                            )
                        except Exception as e:
                            logger.debug(f"Failed to emit retry telemetry (runtime): {e}")

                        # Detect if this is a build failure vs runtime failure
                        is_build_error = self._is_build_failure(result.stderr)

                        if is_build_error:
                            # Build failures need compilation fix prompts, not runtime prompts
                            logger.info(f"Build failure detected for {example.example_id}, using compile fix")
                            error_logs = result.stderr or "Build failed"

                            # Get scaffolding hints from compilation service
                            error_categories = self.get_compilation_service(family).categorize_errors(error_logs)
                            hints = self.get_compilation_service(family).get_error_fix_hints(error_categories, family_config)

                            # TASK-DLL-07: Pass API catalog for enriched error context
                            _catalog = self.registry.get_api_catalog(family) if family else None
                            llm_response = self.llm_service.fix_code(
                                code=current_code,
                                error_logs=error_logs,
                                context_type="compile",  # Use compilation prompts
                                api_context=tier_api_context,  # Track 2: Use tier-enriched context
                                scaffolding_hints=hints,
                                similar_examples=tier_similar_examples if tier_similar_examples else None,
                                family_config=family_config,
                                section_heading=example.section_heading,
                                description_context=example.description_context,
                                topic=example.topic,
                                original_code=example.original_code,
                                catalog=_catalog,
                            )
                            self._emit_llm_telemetry(
                                run_id=run_id, family=family,
                                llm_response=llm_response,
                                context_type="compile", phase="runtime",
                                example_id=example.example_id, attempt=attempt + 1,
                            )
                        else:
                            # True runtime error - use runtime fix prompts
                            error_context = f"""Exit Code: {result.exit_code}
Exception Type: {result.exception_type or 'Unknown'}
Exception Message: {result.exception_message or 'No message'}
Stderr: {result.stderr[:500] if result.stderr else 'None'}"""

                            # TASK-DLL-07: Pass API catalog for enriched error context
                            _catalog = self.registry.get_api_catalog(family) if family else None
                            llm_response = self.llm_service.fix_code(
                                code=current_code,
                                error_logs=error_context,
                                context_type="runtime",
                                api_context=tier_api_context,  # Track 2: Use tier-enriched context
                                test_data_info=test_data_info,
                                similar_examples=tier_similar_examples if tier_similar_examples else None,
                                family_config=family_config,
                                section_heading=example.section_heading,
                                description_context=example.description_context,
                                topic=example.topic,
                                original_code=example.original_code,
                                catalog=_catalog,
                            )
                            self._emit_llm_telemetry(
                                run_id=run_id, family=family,
                                llm_response=llm_response,
                                context_type="runtime", phase="runtime",
                                example_id=example.example_id, attempt=attempt + 1,
                            )

                        if not llm_response.success or not llm_response.content:
                            logger.warning(f"LLM fix failed for {example.example_id}: {llm_response.error}")
                            break

                        fixed_code = llm_response.content

                        # DRIFT-06 Gate 1: Semantic signature validation (runtime)
                        if getattr(global_config.final_review, 'enable_signature_validation', False):
                            try:
                                sig_service = self.registry.get_semantic_signature_service(family)
                                from ..services.semantic_signature_service import CRITICAL_ENUM_FAMILIES
                                orig_sig = sig_service.extract_signature(example.original_code)
                                fixed_sig = sig_service.extract_signature(fixed_code)
                                critical_enums = CRITICAL_ENUM_FAMILIES.get(family, [])
                                sig_drift = sig_service.compare_signatures(orig_sig, fixed_sig, critical_enums)

                                self.db.save_semantic_signature(
                                    example_id=example.example_id,
                                    run_id=run_id,
                                    attempt_type='runtime_attempt',
                                    signature_data={
                                        'enum_values': orig_sig.enum_values,
                                        'method_calls': orig_sig.method_calls,
                                        'constructor_types': orig_sig.constructor_types,
                                        'property_assignments': orig_sig.property_assignments,
                                    },
                                    attempt_id=f"runtime_{attempt}",
                                )

                                if sig_drift.critical and getattr(global_config.final_review, 'reject_critical_enum_changes', True):
                                    logger.warning(
                                        f"GATE-1 Signature drift rejected (runtime) for {example.example_id}: "
                                        f"{sig_drift.critical_reason}"
                                    )
                                    self.db.save_drift_rejection(
                                        example_id=example.example_id,
                                        run_id=run_id,
                                        attempt_id=f"runtime_{attempt}",
                                        phase='runtime',
                                        rejection_reason=sig_drift.critical_reason or 'Critical enum change',
                                        drift_score=sig_drift.drift_score,
                                        signature_drift=sig_drift.to_dict(),
                                        critical_enum_changes=sig_drift.enum_changes,
                                    )
                                    continue
                            except Exception as e:
                                logger.debug(f"Signature validation error (runtime, non-fatal): {e}")

                        # DRIFT-06 Gate 2: Family-specific drift validation (runtime)
                        if getattr(global_config.final_review, 'enable_family_drift_validation', False):
                            try:
                                family_validator = self.registry.get_drift_validator(family)
                                if family_validator:
                                    fv_result = family_validator.validate(
                                        example.original_code, fixed_code, {}
                                    )
                                    if not fv_result.valid:
                                        reasons = [i.message for i in fv_result.issues]
                                        logger.warning(
                                            f"GATE-2 Family drift rejected (runtime) for {example.example_id}: "
                                            f"{reasons}"
                                        )
                                        self.db.save_drift_rejection(
                                            example_id=example.example_id,
                                            run_id=run_id,
                                            attempt_id=f"runtime_{attempt}",
                                            phase='runtime',
                                            rejection_reason=f"Family validation: {'; '.join(reasons)}",
                                            drift_score=fv_result.drift_score,
                                        )
                                        continue
                            except Exception as e:
                                logger.debug(f"Family drift validation error (runtime, non-fatal): {e}")

                        # Phase-2 Gate B: Validate context drift if enabled
                        if self.context_drift_validator is not None:
                            drift_result = self.context_drift_validator.validate(
                                original_code=current_code,
                                fixed_code=fixed_code,
                                original_context=example.app_context
                            )

                            if drift_result.should_reject:
                                logger.warning(
                                    f"Rejecting LLM fix for {example.example_id} due to context drift: "
                                    f"{drift_result.original_context} -> {drift_result.fixed_context}"
                                )
                                # Store drift evidence in failure reason
                                drift_details = {
                                    "drift_detected": True,
                                    "original_context": drift_result.original_context,
                                    "fixed_context": drift_result.fixed_context,
                                    "rejection_reason": drift_result.rejection_reason
                                }
                                self.db.update_example_status(
                                    run_id=run_id,
                                    example_id=example.example_id,
                                    status=ExampleStatus.RUNTIME_FAILED,
                                    failure_reason=f"context_drift_detected: {json.dumps(drift_details)}"
                                )
                                # Skip this fix attempt and continue to next retry
                                continue

                        # Track 2: No-change loop detection (runtime)
                        if previous_runtime_code is not None and self._is_code_identical(previous_runtime_code, fixed_code):
                            logger.warning(
                                f"No-change loop detected (runtime) for {example.example_id} on attempt {attempt + 1}: "
                                f"LLM returned identical code. Escalating early."
                            )
                            # Emit telemetry for no-change detection
                            try:
                                from ..core.telemetry import emit_telemetry_event
                                emit_telemetry_event(
                                    self.db,
                                    run_id,
                                    family,
                                    event_type='no_change_loop_detected',
                                    phase='runtime',
                                    metadata={
                                        'example_id': example.example_id,
                                        'retry_attempt': attempt + 1,
                                        'escalation_reason': 'identical_code_returned',
                                    }
                                )
                            except Exception as e:
                                logger.debug(f"Failed to emit no-change telemetry (runtime): {e}")
                            # Break early - no point retrying if LLM is stuck
                            break

                        # Update previous code for next iteration
                        previous_runtime_code = fixed_code

                        # Drift detection: Compare fixed code against ORIGINAL code
                        # Use startup decision, not runtime check
                        if self._drift_enabled and self._drift_detector:
                            drift_score, similarity = self._drift_detector.compute_drift(
                                original_code=example.original_code,
                                fixed_code=fixed_code
                            )

                            # Log drift score for observability
                            if global_config.drift.log_all_drift_scores:
                                logger.debug(
                                    f"Drift (runtime) for {example.example_id} attempt {attempt+1}: "
                                    f"score={drift_score:.3f}, similarity={similarity:.3f}"
                                )

                            # Check threshold
                            if drift_score > global_config.drift.threshold:
                                logger.warning(
                                    f"Drift threshold exceeded (runtime) for {example.example_id}: "
                                    f"{drift_score:.3f} > {global_config.drift.threshold}"
                                )

                                if global_config.drift.fail_on_exceed:
                                    # Store drift score and abort fix loop
                                    self.db.update_snippet(
                                        example.example_id,
                                        drift_score=drift_score,
                                        drift_similarity=similarity
                                    )
                                    self.db.update_example_status(
                                        example.example_id,
                                        ExampleStatus.RUNTIME_FAILED,
                                        failure_reason=f"Drift threshold exceeded ({drift_score:.3f} > {global_config.drift.threshold})",
                                        run_id=run_id,
                                    )
                                    stats['failed'] += 1
                                    logger.info(f"Example {example.example_id} marked as runtime-failed due to drift")
                                    break  # Exit retry loop

                        example.verified_code = fixed_code

                        # Track previous result for cascading detection
                        prev_result = result

                        # Re-run with fixed code
                        success, result = self.get_runtime_service(family).execute_example(
                            example, family_config, test_data_path
                        )
                        last_result = result  # Track last result for error reporting

                        # Capture first failure in retry loop (TASK-1A fix)
                        if not result.success and first_failure_result is None:
                            first_failure_result = result

                        # Record runtime attempt with LLM fix context
                        self.get_runtime_service(family).record_attempt(
                            example_id=example.example_id,
                            family=family,
                            runtime_result=result,
                            sample_ref=sample_ref,
                            scenario=f"llm_fix_attempt_{attempt + 1}",
                            retrieved_examples=retrieved_example_ids if retrieved_example_ids else None,
                            llm_request=llm_response.raw_prompt if hasattr(llm_response, 'raw_prompt') else None,
                            llm_response=llm_response.content,
                            run_id=run_id,
                        )

                        if success:
                            # Stage 5.5: Final Review (if enabled and code was LLM-fixed)
                            only_review_llm_fixed = getattr(global_config.final_review, 'only_review_llm_fixed', True)
                            if global_config.final_review.enabled and only_review_llm_fixed:
                                logger.debug(f"Running Stage 5.5 final review (runtime) for {example.example_id}")

                                review = self.llm_service.final_review(
                                    original_code=example.original_code,
                                    fixed_code=fixed_code,
                                )
                                if self.llm_service._last_response:
                                    self._emit_llm_telemetry(
                                        run_id=run_id, family=family,
                                        llm_response=self.llm_service._last_response,
                                        context_type="final_review", phase="runtime",
                                        example_id=example.example_id,
                                    )

                                if review['success'] and not review['intent_preserved']:
                                    # Intent drift detected - check confidence threshold
                                    confidence_threshold = getattr(global_config.final_review, 'confidence_threshold', 0.7)
                                    if review['confidence'] >= confidence_threshold:
                                        logger.warning(
                                            f"Intent drift detected (runtime) for {example.example_id}: {review['explanation']} "
                                            f"(confidence: {review['confidence']})"
                                        )
                                        stats['failed'] += 1
                                        drift_reason = f"Intent drift (runtime): {review['explanation']}"
                                        if review.get('drift_details'):
                                            drift_reason += f" | Details: {', '.join(review['drift_details'][:3])}"

                                        self.db.update_example_status(
                                            example.example_id,
                                            ExampleStatus.RUNTIME_FAILED,
                                            failure_reason=drift_reason,
                                            run_id=run_id,
                                        )
                                        logger.info(f"Example {example.example_id} marked as runtime failed due to intent drift")
                                        break  # Exit retry loop
                                    else:
                                        logger.info(
                                            f"Intent drift detected but confidence {review['confidence']:.2f} "
                                            f"below threshold {confidence_threshold}, accepting fix"
                                        )
                                elif not review['success']:
                                    # Review failed - log warning but continue
                                    logger.warning(
                                        f"Final review failed (runtime) for {example.example_id}: {review.get('error', 'Unknown error')}"
                                    )
                                else:
                                    # Intent preserved - log success
                                    logger.debug(
                                        f"Final review passed (runtime) for {example.example_id}: {review['explanation']} "
                                        f"(confidence: {review['confidence']})"
                                    )

                            stats['passed_with_fix'] += 1
                            self._llm_fixed_example_ids.add(example.example_id)
                            self.db.update_example_status(example.example_id, ExampleStatus.VERIFIED, run_id=run_id)
                            self.db.update_example_code(
                                example.example_id,
                                verified_code=fixed_code,
                                run_id=run_id,
                            )

                            # Store final drift score for successful fix
                            if self._drift_detector and global_config.drift.enabled:
                                final_drift, final_sim = self._drift_detector.compute_drift(
                                    original_code=example.original_code,
                                    fixed_code=fixed_code
                                )
                                self.db.update_snippet(
                                    example.example_id,
                                    drift_score=final_drift,
                                    drift_similarity=final_sim
                                )
                            # Store LLM-fixed verified example in vector DB
                            if self.vector_db_service.is_available():
                                try:
                                    # Use final drift score (ID-05: Pass drift to vector DB)
                                    drift_to_store = None
                                    if self._drift_detector and global_config.drift.enabled:
                                        drift_to_store = final_drift  # From lines 1085-1095

                                    self.vector_db_service.add_example(
                                        example_id=example.example_id,
                                        code=fixed_code,
                                        metadata={
                                            'family': family,
                                            'source': 'pipeline_runtime_llm_fixed',
                                            'verified': True,
                                            'file_path': example.file_path,
                                            'fix_attempt': attempt + 1,
                                            'used_similar_examples': len(similar_examples) > 0,
                                        },
                                        drift_score=drift_to_store  # ID-05: Pass drift score
                                    )
                                except Exception as e:
                                    logger.debug(f"Failed to add LLM-fixed example to vector DB: {e}")
                            fixed = True
                            logger.info(f"Runtime fix succeeded for {example.example_id} on attempt {attempt + 1}")
                            break

                        # Prevent cascading degradation: don't use fixed code if it made things worse
                        # (e.g., introduced build errors when original code at least compiled)
                        prev_was_build_error = self._is_build_failure(prev_result.stderr if prev_result else None)
                        new_is_build_error = self._is_build_failure(result.stderr)

                        if new_is_build_error and not prev_was_build_error:
                            # Fix introduced build errors - don't cascade this degradation
                            logger.warning(
                                f"Fix attempt {attempt + 1} for {example.example_id} introduced build errors, "
                                "keeping previous code for next attempt"
                            )
                            # Don't update current_code, continue with the original
                            continue

                        current_code = fixed_code
                    
                    if fixed:
                        continue
                
                # All retries failed
                stats['failed'] += 1
                # TASK-1A fix: Prioritize first_failure_result for accurate error reporting
                if first_failure_result is not None:
                    failure_reason = (
                        first_failure_result.exception_message
                        or (first_failure_result.stderr[:200] if first_failure_result.stderr else None)
                        or "Unknown runtime error (first failure captured)"
                    )
                elif last_result is not None:
                    failure_reason = (
                        last_result.exception_message
                        or (last_result.stderr[:200] if last_result.stderr else None)
                        or "Unknown runtime error (last result)"
                    )
                else:
                    failure_reason = "Unknown runtime error (no result)"
                self.db.update_example_status(
                    example.example_id,
                    ExampleStatus.RUNTIME_FAILED,
                    failure_reason=failure_reason,
                    run_id=run_id,
                )
                
            except Exception as e:
                logger.error(f"Error running {example.example_id}: {e}")
                stats['errors'] += 1

        # Task 3: Cleanup - ensure no examples remain in COMPILABLE terminal state
        # Any COMPILABLE examples that weren't moved to a terminal state should be resolved
        remaining_compilable = self.db.get_examples_by_family(family, ExampleStatus.COMPILABLE, limit=None, run_id=run_id)
        if remaining_compilable:
            logger.warning(f"Found {len(remaining_compilable)} examples still in COMPILABLE state after runtime phase, marking as terminal states")
            for example in remaining_compilable:
                # Check if example has runtime attempts to determine appropriate status
                try:
                    runtime_attempts = [a for a in self.db.get_runtime_attempts(example.example_id, run_id=run_id)]
                    if runtime_attempts:
                        # Has runtime attempts - classify based on the error
                        last_attempt = runtime_attempts[-1]
                        error_text = (last_attempt.stderr or "") + (last_attempt.exception_message or "")
                        error_lower = error_text.lower()

                        # Check for RAR file missing
                        if ".rar" in error_lower and ("filenotfound" in error_lower or "could not find file" in error_lower):
                            self.db.update_example_status(
                                example.example_id,
                                ExampleStatus.INFRA_BLOCKED,
                                escalation_reason="missing_rar_fixture",
                                run_id=run_id,
                            )
                            logger.info(f"Marked {example.example_id} as INFRA_BLOCKED (missing RAR fixture)")
                            stats['infra_blocked'] = stats.get('infra_blocked', 0) + 1
                        else:
                            # Other runtime error - mark as RUNTIME_FAILED
                            failure_reason = last_attempt.exception_message or last_attempt.stderr[:200] or "Unknown runtime error"
                            self.db.update_example_status(
                                example.example_id,
                                ExampleStatus.RUNTIME_FAILED,
                                failure_reason=failure_reason,
                                run_id=run_id,
                            )
                            logger.info(f"Marked {example.example_id} as RUNTIME_FAILED")
                            stats['failed'] += 1
                    else:
                        # No runtime attempts - check if this is an ASP.NET/library example
                        # that can't be executed in the current runtime harness
                        app_ctx = getattr(example, 'app_context', None) or ''
                        if app_ctx.startswith('aspnet') or app_ctx == 'library':
                            self.db.update_example_status(
                                example.example_id,
                                ExampleStatus.NEEDS_REVIEW,
                                escalation_reason="aspnet_not_runnable",
                                run_id=run_id,
                            )
                            logger.info(f"Marked {example.example_id} as NEEDS_REVIEW (app_context={app_ctx}, not runnable)")
                            stats['needs_review'] = stats.get('needs_review', 0) + 1
                        else:
                            self.db.update_example_status(
                                example.example_id,
                                ExampleStatus.RUNTIME_FAILED,
                                failure_reason="No runtime attempts recorded",
                                run_id=run_id,
                            )
                            logger.warning(f"Marked {example.example_id} as RUNTIME_FAILED (no runtime attempts)")
                            stats['failed'] += 1
                except Exception as cleanup_error:
                    logger.error(f"Error cleaning up COMPILABLE example {example.example_id}: {cleanup_error}")
                    # Default to RUNTIME_FAILED as safe fallback
                    self.db.update_example_status(
                        example.example_id,
                        ExampleStatus.RUNTIME_FAILED,
                        failure_reason="Cleanup error",
                        run_id=run_id,
                    )
                    stats['failed'] += 1

        stats['verified'] = stats['passed_first_try'] + stats['passed_with_fix']
        return stats
    
    def _run_markdown_update_phase(
        self,
        run_id: str,
        family: str,
        dry_run: bool,
        allow_md_write: bool = False,
    ) -> Dict[str, Any]:
        """
        Run Phase D: Markdown Update.

        Args:
            run_id: Run identifier
            family: Family identifier
            dry_run: If True, don't write changes
            allow_md_write: If True, override global config to allow markdown writes

        Returns:
            Statistics dictionary
        """
        # Auto-promote CS_FILE examples past markdown update (no markdown to edit)
        verified = self.db.get_examples_by_family(family, ExampleStatus.VERIFIED, run_id=run_id)
        cs_promoted = 0
        for ex in (verified or []):
            if ex.source_type == SourceType.CS_FILE:
                self.db.update_example_status(ex.example_id, ExampleStatus.MD_UPDATED, run_id=run_id)
                cs_promoted += 1
        if cs_promoted:
            logger.info(f"Auto-promoted {cs_promoted} CS_FILE examples past markdown update")

        # Index verified CS_FILE examples in vector DB for knowledge retrieval
        if self.vector_db_service and cs_promoted > 0:
            indexed_count = 0
            for ex in verified:
                if ex.source_type == SourceType.CS_FILE and ex.verified_code:
                    # Build rich metadata
                    metadata = {
                        "family": family,
                        "source": "example_repo",
                        "source_type": "cs_file",
                        "app_context": ex.app_context or "console",
                        "topic": ex.topic or "",
                        "section_heading": ex.section_heading or "",
                        "file_path": ex.file_path,
                        "read_only": True,  # Mark as reference-only (never modify)
                    }

                    try:
                        self.vector_db_service.add_example(
                            example_id=ex.example_id,
                            code=ex.verified_code,
                            metadata=metadata,
                            drift_score=0.0,  # Canonical source = zero drift
                        )
                        indexed_count += 1
                    except Exception as e:
                        logger.warning(f"Failed to index CS_FILE example {ex.example_id}: {e}")

            if indexed_count > 0:
                logger.info(f"Indexed {indexed_count} verified CS_FILE examples in vector DB")

        # ALWAYS recreate service with correct run_id (fixes run_id mismatch bug)
        global_config = self.config_manager.load_global_config()
        allow_write = allow_md_write or global_config.markdown_write.allow_markdown_write

        self._markdown_service = MarkdownUpdateService(
            self.db,
            artifacts_dir=self.artifacts_dir / "diffs",
            allow_markdown_write=allow_write,
            use_workspace_copy=self.use_workspace_copy,
            workspace_root=self.artifacts_dir / "workspace",
            run_id=run_id,  # Always use current run_id, not "default"
        )

        if allow_md_write:
            logger.info("Markdown writes ENABLED via --allow-md-write flag")

        result = self.markdown_service.update_all_files(family, dry_run)

        # Emit markdown update event
        try:
            from ..core.telemetry import emit_telemetry_event
            emit_telemetry_event(
                self.db, run_id, family,
                event_type='markdown_update_complete',
                phase='markdown_update',
                success=True,
                metadata={
                    'files_updated': result.get('files_updated', 0),
                    'examples_updated': result.get('examples_updated', 0),
                    'dry_run': dry_run,
                },
            )
        except Exception:
            pass

        return result

    def _consensus_review(
        self,
        content: str,
        snippets: List[Dict[str, Any]],
        num_passes: int = 2,
        run_id: Optional[str] = None,
        family: Optional[str] = None,
        catalog=None,
    ) -> Dict[str, Any]:
        """
        Run multiple review passes and require consensus for approval.

        This improves review reliability by:
        1. Running 2 independent reviews
        2. Approving only if both agree (strong consensus)
        3. Running a tiebreaker if reviews disagree

        Uses the separate final_review_llm_service (C.6: independent provider/model/timeout).

        Returns:
            Dict with 'approved', 'issues', 'confidence', and 'raw_response'
        """
        reviews = []

        for pass_num in range(num_passes):
            # Use dedicated final_review LLM service (C.6)
            # TASK-FIX-REVIEW-03: Pass family for catalog-based validation
            result = self.final_review_llm_service.review_markdown_structured(
                content, snippets, catalog=catalog, family=family
            )
            if run_id and family and self.final_review_llm_service._last_response:
                self._emit_llm_telemetry(
                    run_id=run_id, family=family,
                    llm_response=self.final_review_llm_service._last_response,
                    context_type="markdown_review", phase="final_review",
                )
            reviews.append(result)

            # High-confidence optimization: skip second pass if first pass approved with high confidence
            if pass_num == 0 and result.get('approved', False) and result.get('confidence') == 'high':
                logger.info(f"High-confidence approval (confidence={result.get('confidence')}), skipping second pass")
                return {
                    'approved': True,
                    'issues': [],
                    'confidence': 'high',
                    'raw_response': result.get('raw_response', ''),
                }

            # If first pass rejected, we still want second pass to confirm
            # so we don't early-exit here

        # Check for consensus
        approvals = [r.get('approved', False) for r in reviews]

        if all(approvals):
            # Both approved - strong pass
            logger.debug("Consensus review: both passes approved")
            return {
                'approved': True,
                'issues': [],
                'confidence': 'high',
                'raw_response': reviews[-1].get('raw_response', ''),
            }
        elif not any(approvals):
            # Both failed - definite issues
            logger.debug("Consensus review: both passes rejected")
            all_issues = []
            seen_descriptions = set()
            for r in reviews:
                for issue in r.get('issues', []):
                    # Deduplicate issues by description
                    desc = issue.get('description', '')
                    if desc not in seen_descriptions:
                        seen_descriptions.add(desc)
                        all_issues.append(issue)
            return {
                'approved': False,
                'issues': all_issues,
                'confidence': 'high',
                'raw_response': reviews[-1].get('raw_response', ''),
            }
        else:
            # Split decision - run tiebreaker
            logger.info("Consensus review: split decision, running tiebreaker")
            # Use dedicated final_review LLM service (C.6)
            # TASK-FIX-REVIEW-03: Pass family for catalog-based validation
            tiebreaker = self.final_review_llm_service.review_markdown_structured(
                content, snippets, catalog=catalog, family=family
            )
            if run_id and family and self.final_review_llm_service._last_response:
                self._emit_llm_telemetry(
                    run_id=run_id, family=family,
                    llm_response=self.final_review_llm_service._last_response,
                    context_type="markdown_review", phase="final_review",
                )
            if tiebreaker.get('approved', False):
                return {
                    'approved': True,
                    'issues': [],
                    'confidence': 'medium',
                    'raw_response': tiebreaker.get('raw_response', ''),
                }
            else:
                return {
                    'approved': False,
                    'issues': tiebreaker.get('issues', []),
                    'confidence': 'medium',
                    'raw_response': tiebreaker.get('raw_response', ''),
                }

    def _run_final_review_phase(self, run_id: str, family: str) -> Dict[str, Any]:
        """
        Run Phase E: Final LLM Review with structured issue tracking.

        Implements re-review loop up to max_review_attempts if issues are found.
        All reviews and issues are saved to the database for audit trail.

        Args:
            run_id: Run identifier
            family: Family identifier
        """
        stats = {
            'files_reviewed': 0,
            'approved': 0,
            'failed': 0,
            'total_issues': 0,
            'critical_issues': 0,
            'review_attempts': 0,
        }

        # Load final review config
        global_config = self.config_manager.load_global_config()
        final_review_config = global_config.final_review
        max_attempts = final_review_config.max_review_attempts

        # Get updated examples
        examples = self.db.get_examples_by_family(family, ExampleStatus.MD_UPDATED, run_id=run_id)

        # When only_review_llm_fixed is True, only review files containing LLM-fixed examples
        only_review_llm_fixed = getattr(final_review_config, 'only_review_llm_fixed', True)

        # Group by file
        files: Dict[str, List[ExampleRecord]] = {}
        auto_pass_files: Dict[str, List[ExampleRecord]] = {}
        for example in examples:
            file_key = example.file_path
            has_llm_fixed = any(e.example_id in self._llm_fixed_example_ids
                                for e in [example])

            if only_review_llm_fixed and not has_llm_fixed:
                # Check if any example in this file was LLM-fixed (defer grouping)
                if file_key not in auto_pass_files:
                    auto_pass_files[file_key] = []
                auto_pass_files[file_key].append(example)
            else:
                if file_key not in files:
                    files[file_key] = []
                files[file_key].append(example)

        # Merge: if a file has ANY LLM-fixed example, review the whole file
        if only_review_llm_fixed:
            for file_key, file_examples in list(auto_pass_files.items()):
                if file_key in files:
                    # File already has LLM-fixed examples, add remaining to review
                    files[file_key].extend(file_examples)
                    del auto_pass_files[file_key]

            # Auto-pass files with zero LLM-fixed examples
            for file_key, file_examples in auto_pass_files.items():
                for e in file_examples:
                    self.db.update_example_status(
                        e.example_id, ExampleStatus.FINAL_REVIEW_PASSED, run_id=run_id
                    )
                stats['approved'] += 1
                stats['files_reviewed'] += 1
            if auto_pass_files:
                logger.info(
                    f"Auto-passed {len(auto_pass_files)} files with {sum(len(v) for v in auto_pass_files.values())} "
                    f"examples (no LLM fixes, only_review_llm_fixed=True)"
                )

        for file_path, file_examples in files.items():
            stats['files_reviewed'] += 1
            file_approved = False

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Build snippets with example_id for issue tracking
                snippets = [
                    {
                        'code': e.verified_code or e.compilable_code or e.original_code,
                        'example_id': e.example_id,
                        'line': e.location.start_line,
                        'language': e.language,
                    }
                    for e in file_examples
                ]

                # Review loop with retries
                for attempt in range(1, max_attempts + 1):
                    stats['review_attempts'] += 1

                    # Get catalog for this family
                    catalog = self.registry.get_api_catalog(family)

                    # Call consensus review (2 passes for reliability)
                    review_result = self._consensus_review(
                        content, snippets, run_id=run_id, family=family, catalog=catalog
                    )

                    # Create ReviewResult model
                    review_issues = []
                    for issue_data in review_result.get('issues', []):
                        # Map issue_type string to enum
                        try:
                            issue_type = IssueType(issue_data.get('issue_type', 'other'))
                        except ValueError:
                            issue_type = IssueType.OTHER

                        # Map severity string to enum
                        try:
                            severity = IssueSeverity(issue_data.get('severity', 'warning'))
                        except ValueError:
                            severity = IssueSeverity.WARNING

                        review_issue = ReviewIssue(
                            review_id="",  # Will be set after ReviewResult is created
                            example_id=issue_data.get('example_id', 'unknown'),
                            issue_type=issue_type,
                            description=issue_data.get('description', 'No description'),
                            suggestion=issue_data.get('suggestion'),
                            severity=severity,
                        )
                        review_issues.append(review_issue)

                    review_record = ReviewResult(
                        file_path=file_path,
                        run_id=run_id,
                        family=family,
                        approved=review_result.get('approved', True),
                        review_attempt=attempt,
                        issues=review_issues,
                        llm_response=review_result.get('raw_response', ''),
                    )

                    # Set review_id on issues after ReviewResult generates its ID
                    for issue in review_record.issues:
                        issue.review_id = review_record.review_id

                    # Save review result to database
                    self.db.save_review_result(review_record)

                    # Track stats
                    stats['total_issues'] += len(review_issues)
                    critical_count = sum(
                        1 for i in review_issues
                        if i.severity == IssueSeverity.CRITICAL
                    )
                    stats['critical_issues'] += critical_count

                    if review_record.approved:
                        # Review passed
                        file_approved = True
                        stats['approved'] += 1
                        logger.info(f"Final review PASSED for {file_path} on attempt {attempt}")

                        for e in file_examples:
                            self.db.update_example_status(
                                e.example_id, ExampleStatus.FINAL_REVIEW_PASSED, run_id=run_id
                            )
                        break  # Exit retry loop

                    else:
                        # Review failed
                        logger.warning(
                            f"Final review found {len(review_issues)} issues in {file_path} "
                            f"(attempt {attempt}/{max_attempts})"
                        )

                        # Check if we should fail on critical issues
                        if final_review_config.fail_on_critical and critical_count > 0:
                            logger.error(
                                f"Critical issues found in {file_path}, failing review"
                            )
                            break  # Don't retry on critical

                        # Check if auto-remediation is enabled (future feature)
                        if not final_review_config.auto_remediation_enabled:
                            # No auto-remediation, mark as failed after max attempts
                            if attempt >= max_attempts:
                                break
                            # Otherwise, retry (maybe issues were transient)
                            logger.info(f"Retrying review for {file_path} (attempt {attempt + 1})")
                            continue

                        # Future: Auto-remediation would go here
                        # For now, just retry without changes
                        if attempt >= max_attempts:
                            break

                # After review loop
                if not file_approved:
                    stats['failed'] += 1
                    for e in file_examples:
                        self.db.update_example_status(
                            e.example_id, ExampleStatus.FINAL_REVIEW_FAILED, run_id=run_id
                        )

            except Exception as e:
                logger.error(f"Error reviewing {file_path}: {e}")
                stats['failed'] += 1
                # Mark examples as failed on exception
                for ex in file_examples:
                    self.db.update_example_status(
                        ex.example_id,
                        ExampleStatus.FINAL_REVIEW_FAILED,
                        failure_reason=f"Review error: {str(e)}",
                        run_id=run_id,
                    )

        return stats
    
    def _run_finalization_phase(
        self,
        family: str,
        run_id: str,
        dry_run: bool,
        allow_commit: bool = False,
    ) -> Dict[str, Any]:
        """Run Phase F: Persist, Telemetry, Commit."""
        stats = {
            'committed': False,
            'commit_hash': None,
        }

        global_config = self.config_manager.load_global_config()

        # Export telemetry if enabled
        if global_config.telemetry.local_telemetry_enabled:
            try:
                exported_files = export_run_telemetry(
                    self.db,
                    run_id,
                    global_config.telemetry.local_telemetry_path
                )
                if exported_files:
                    stats['telemetry_exported'] = True
                    stats['telemetry_files'] = list(exported_files.values())
                    logger.info(f"Exported {len(exported_files)} telemetry files")
            except Exception as e:
                logger.warning(f"Telemetry export failed: {e}")
                stats['telemetry_export_error'] = str(e)

        # Resolve commit permission: CLI --commit flag OR global config
        commit_enabled = allow_commit or global_config.git.enabled
        if dry_run or not commit_enabled:
            if not dry_run and not commit_enabled:
                logger.info("Git commit skipped (use --commit flag or set git.enabled=true)")
            return stats

        # Family-level gate (only when not using explicit --commit override)
        if not allow_commit:
            family_config = self.config_manager.load_family_config(family)
            if not family_config.auto_commit:
                logger.info(f"Git commit skipped for '{family}' (auto_commit=false in family config)")
                return stats

        # Get candidate files from FINAL_REVIEW_PASSED examples
        # Exclude CS_FILE examples — they are reference-only and live in a different repo
        all_examples = self.db.get_examples_by_family(family, ExampleStatus.FINAL_REVIEW_PASSED, run_id=run_id)
        examples = [e for e in all_examples if e.source_type != SourceType.CS_FILE]
        candidate_files = list(set(e.file_path for e in examples))

        if not candidate_files:
            if all_examples and not examples:
                logger.info(f"Git commit skipped: all {len(all_examples)} FINAL_REVIEW_PASSED examples are CS_FILE (reference-only)")
            return stats

        # Attempt git commit
        try:
            # Resolve absolute paths and find git root
            first_file = Path(candidate_files[0]).resolve()

            # Find git root directory containing the content files
            git_root_result = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                cwd=first_file.parent if first_file.exists() else Path.cwd(),
                capture_output=True,
                text=True,
            )

            if git_root_result.returncode != 0:
                logger.error(f"Could not find git root for {first_file}")
                stats['error'] = "Content files not in a git repository"
                return stats

            git_root = Path(git_root_result.stdout.strip())
            logger.debug(f"Git root for content: {git_root}")

            # Get current branch in content repo
            branch_result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=git_root,
                capture_output=True,
                text=True,
            )
            content_branch = branch_result.stdout.strip() if branch_result.returncode == 0 else "unknown"
            logger.info(f"Committing to branch '{content_branch}' in {git_root}")

            # Stage all candidate files - paths relative to git root
            for file_path in candidate_files:
                abs_path = Path(file_path).resolve()
                try:
                    rel_path = abs_path.relative_to(git_root)
                except ValueError:
                    # File not under git root, use as-is
                    rel_path = file_path

                subprocess.run(
                    ["git", "add", str(rel_path)],
                    cwd=git_root,
                    check=True,
                    capture_output=True,
                )

            # CRITICAL: Query what was ACTUALLY staged (git-verified truth)
            git_status_result = subprocess.run(
                ["git", "diff", "--cached", "--name-only"],
                cwd=git_root,
                capture_output=True,
                text=True,
            )

            if git_status_result.returncode != 0:
                logger.error("Failed to get staged files")
                stats['error'] = "Could not determine staged files"
                return stats

            # Get absolute paths of actually staged files
            staged_relative_paths = git_status_result.stdout.strip().split('\n')
            staged_files = [
                str((git_root / Path(rel_path)).resolve())
                for rel_path in staged_relative_paths
                if rel_path  # Skip empty lines
            ]

            if not staged_files:
                logger.warning("No files were actually staged for commit")
                return stats

            logger.info(f"Git staging verified: {len(staged_files)} files have changes (from {len(candidate_files)} candidates)")

            # Filter examples to only those whose files are actually staged
            committed_examples = [
                ex for ex in examples
                if str(Path(ex.file_path).resolve()) in staged_files
            ]

            if not committed_examples:
                logger.warning("No examples match staged files")
                return stats

            logger.info(f"Commit will include {len(committed_examples)} examples across {len(staged_files)} files")

            # Calculate statistics from COMMITTED examples only (not entire run)
            committed_example_ids = [ex.example_id for ex in committed_examples]

            # Count compilation attempts for committed examples
            compile_attempts = 0
            compile_success = 0
            for example_id in committed_example_ids:
                attempts = self.db.get_compile_attempts(example_id, run_id=run_id)
                if attempts:
                    compile_attempts += len(attempts)
                    compile_success += sum(1 for a in attempts if a.success)

            # LLM fixes = examples that needed multiple compile attempts
            llm_fixes = compile_attempts - len(committed_examples) if compile_attempts > len(committed_examples) else 0

            # Calculate first-try successes
            first_try_success = len(committed_examples) - llm_fixes

            total_examples = len(committed_examples)
            verified_count = len(committed_examples)  # All committed examples are verified by definition

            # Get family config for categorization
            family_config = self.config_manager.load_family_config(family)
            content_roots = family_config.content_roots or []
            content_pattern = family_config.content_pattern or {}

            # Categorize STAGED files by content root (blog, kb, docs, etc.)
            categorized_files = {}
            for category, root in zip(content_pattern.keys(), content_roots):
                categorized_files[category] = []
                norm_root = str(Path(root).resolve())
                for file_path in staged_files:  # Use staged_files, not candidate_files
                    norm_file = str(Path(file_path).resolve())
                    if norm_file.startswith(norm_root):
                        categorized_files[category].append(Path(file_path).name)

            # Build category summaries
            category_lines = []
            for category, files in categorized_files.items():
                if files:
                    # Extract unique topics from filenames (remove extension, take stems)
                    topics = []
                    for f in files[:5]:  # First 5 as sample
                        stem = Path(f).stem
                        # Clean up common patterns (index, etc.)
                        if stem != 'index':
                            topics.append(stem.replace('-', ' ').replace('_', ' '))

                    if topics:
                        topic_list = ', '.join(sorted(set(topics)))
                        category_lines.append(f"{category.title()}: {len(files)} files updated ({topic_list})")
                    else:
                        category_lines.append(f"{category.title()}: {len(files)} files updated")

            # Build commit message with ACCURATE counts
            message_title = f"fix({family}): verify and update {verified_count} C# code examples across {len(staged_files)} markdown files"

            # Build detailed description
            description_lines = [
                f"VFV pipeline run {run_id[:16]}:",
                f"- {total_examples} examples verified and committed",
            ]

            # Add compilation details
            if compile_success > 0:
                if llm_fixes > 0:
                    description_lines.append(f"- {first_try_success} compiled first-try, {llm_fixes} fixed via LLM")
                else:
                    description_lines.append(f"- {compile_success} compiled first-try")

            # Add deterministic fixes mention
            description_lines.append("- Deterministic fixes applied: stream disposal, using directives, context harness")

            # Add blank line before category details
            if category_lines:
                description_lines.append("")
                description_lines.extend(category_lines)

            description = '\n'.join(description_lines)

            # Hardcoded co-author per project policy (NEVER use Claude model name)
            co_author = "Example Reviewer <example-reviewer@aspose.net>"
            full_message = f"{message_title}\n\n{description}\n\nCo-Authored-By: {co_author}"

            result = subprocess.run(
                ["git", "commit", "-m", full_message],
                cwd=git_root,
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                # Get commit hash
                hash_result = subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    cwd=git_root,
                    capture_output=True,
                    text=True,
                )

                stats['committed'] = True
                stats['commit_hash'] = hash_result.stdout.strip()
                stats['git_root'] = str(git_root)
                stats['git_branch'] = content_branch

                # Update example statuses
                for e in examples:
                    self.db.update_example_status(e.example_id, ExampleStatus.COMMITTED, run_id=run_id)

        except Exception as e:
            logger.error(f"Git commit failed: {e}")
            stats['error'] = str(e)
        
        return stats
    
    def _validate_default_usings(self, family: str, family_config: FamilyConfig) -> None:
        """Validate default_usings against the API catalog and remove invalid namespaces.

        Checks each namespace in family_config.code_defaults.default_usings against
        the catalog's known namespace set. BCL prefixes (System, Microsoft, Newtonsoft)
        are always allowed. Invalid namespaces are logged and filtered out.
        """
        try:
            catalog_service = self.registry.get_api_catalog(family) if self.registry else None
        except Exception:
            catalog_service = None

        if not catalog_service or not catalog_service.is_loaded:
            return

        default_usings = family_config.code_defaults.default_usings
        if not default_usings:
            return

        valid_namespaces = catalog_service.get_namespace_set()
        bcl_prefixes = ('System', 'Microsoft', 'Newtonsoft')

        invalid_ns = []
        for ns in default_usings:
            if ns.startswith(bcl_prefixes):
                continue
            if ns not in valid_namespaces:
                invalid_ns.append(ns)

        if invalid_ns:
            logger.warning(
                f"default_usings validation: {len(invalid_ns)} invalid namespace(s) "
                f"for family '{family}': {invalid_ns}"
            )
            # Filter out invalid namespaces from the mutable config object
            family_config.code_defaults.default_usings = [
                ns for ns in default_usings if ns not in invalid_ns
            ]
            logger.info(
                f"Filtered default_usings: {family_config.code_defaults.default_usings}"
            )

    def _check_unfixable_types(self, errors: List[str], catalog_service) -> List[str]:
        """Check if CS0246 errors reference types not in the catalog.

        Returns a list of type names from CS0246 errors that are not present
        in the API catalog and are not well-known BCL types. These represent
        types that cannot be fixed by adding using directives.
        """
        if not catalog_service:
            return []
        unfixable = []
        bcl_types = {
            'String', 'Int32', 'Boolean', 'Object', 'Exception', 'DateTime',
            'TimeSpan', 'Guid', 'Nullable', 'IDisposable', 'IEnumerable',
            'ICollection', 'IList', 'IDictionary', 'Func', 'Action',
            'EventArgs', 'EventHandler', 'Attribute', 'Type',
        }
        for err in errors:
            if 'CS0246' not in err:
                continue
            m = re.search(r"'(\w+)'", err)
            if m:
                type_name = m.group(1)
                if type_name in bcl_types:
                    continue
                if not catalog_service.has_type(type_name):
                    unfixable.append(type_name)
        return unfixable

    def _is_catalog_invalid(self, path: Path) -> bool:
        """Check if catalog file exists but is empty or corrupt."""
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
            return len(data.get("types", {})) == 0
        except Exception:
            return True

    def _capture_and_store_fingerprint(self, run_id: str, family: str) -> None:
        """
        Capture run fingerprint and store to DB.

        Track 1 requirement (C.8): Capture fingerprint at run start with:
        - config_hash
        - vector_db_startup_decision
        - drift_enabled
        - llm_provider_capabilities
        - environment info

        Selection_hash will be updated after discovery phase.

        Args:
            run_id: Run identifier
            family: Family identifier
        """
        from ..core.fingerprint import RunFingerprint
        import subprocess

        global_config = self.config_manager.load_global_config()

        # Compute config hash with CLI overrides included
        config_hash = self.config_manager.compute_config_hash(family, cli_overrides=self.cli_overrides)

        # Try to get dotnet version
        dotnet_version = None
        try:
            result = subprocess.run(
                ["dotnet", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                dotnet_version = result.stdout.strip()
        except Exception:
            pass

        # Build comprehensive LLM capabilities dict for Plan v2.1 Section B
        llm_capabilities = {
            # LLM section
            'provider': global_config.llm.provider,
            'base_url': global_config.llm.base_url,
            'model': global_config.llm.model,
            'model_hash': None,  # Not available from most providers
            'temperature': global_config.llm.temperature,
            'timeout_seconds': global_config.llm.timeout_seconds,
            'seed_supported': True,  # Assume supported unless provider rejects
            'timeout_supported': True,

            # Final review section
            'final_review_enabled': global_config.final_review.enabled,
            'final_review_provider': global_config.final_review.provider,
            'final_review_model': global_config.final_review.model,
            'final_review_timeout': global_config.final_review.timeout_seconds,

            # Vector DB section
            'vector_db_provider': global_config.vector_db.provider,
            'embedding_model': global_config.vector_db.embedding_model,
            'embedding_model_version': None,  # Could be detected at runtime
            'embedding_device': global_config.vector_db.embedding_device,
            'drift_tolerance': global_config.vector_db.drift_tolerance,

            # Environment section
            'dotnet_version': dotnet_version,

            # Content snapshot section (will be updated after discovery)
            'family': family,
            'total_examples_selected': 0,  # Will be updated after discovery
            'content_hash': None,  # Optional: SHA256 of all markdown files
        }

        # Create fingerprint
        fingerprint = RunFingerprint(
            run_id=run_id,
            config_hash=config_hash,
            selection_hash=None,  # Will be updated after discovery
            vector_db_startup_decision=self._vector_db_startup_decision,
            drift_enabled=self._drift_enabled,
            llm_provider_capabilities=llm_capabilities,
            llm_seed=global_config.llm.seed,
            deterministic_mode=global_config.llm.deterministic_mode,
        )

        # Save to database
        try:
            self.db.save_run_fingerprint(fingerprint)
            logger.info(f"Captured run fingerprint for {run_id}")
        except Exception as e:
            logger.warning(f"Failed to save run fingerprint: {e}")

    def _export_run_artifacts(self, run_id: str, family: str) -> None:
        """
        Export run artifacts to files.

        Track 1 requirement (C.8): Export fingerprint.json and results_summary.json
        to runs/{run_id}/ directory for determinism verification.

        Args:
            run_id: Run identifier
            family: Family identifier
        """
        from ..core.fingerprint import RunFingerprint
        from ..core.results_summary import ResultsSummary

        # Create output directory
        run_dir = Path(f"runs/{run_id}")
        run_dir.mkdir(parents=True, exist_ok=True)

        # Update fingerprint with selection_hash and total_examples_selected (after discovery)
        try:
            fingerprint = self.db.get_run_fingerprint(run_id)
            if fingerprint:
                # Compute selection_hash from all examples in this run
                examples = self.db.get_examples_by_family(family, run_id=run_id)
                example_keys = [ex.example_key for ex in examples if ex.example_key]
                selection_hash = self.db.compute_selection_hash(example_keys)

                # Update fingerprint selection_hash and total_examples_selected
                fingerprint.selection_hash = selection_hash
                if fingerprint.llm_provider_capabilities:
                    fingerprint.llm_provider_capabilities['total_examples_selected'] = len(examples)
                self.db.save_run_fingerprint(fingerprint)

                # Export fingerprint.json
                fingerprint_path = run_dir / "fingerprint.json"
                fingerprint.save_to_file(fingerprint_path)
                logger.info(f"Exported fingerprint to {fingerprint_path}")
            else:
                logger.warning(f"No fingerprint found for run {run_id}")
        except Exception as e:
            logger.error(f"Failed to export fingerprint: {e}")

        # Export results_summary.json
        try:
            summary = ResultsSummary.from_run(self.db, run_id)
            summary_path = run_dir / "results_summary.json"
            summary.save_to_file(summary_path)
            logger.info(f"Exported results summary to {summary_path}")
        except Exception as e:
            logger.error(f"Failed to export results summary: {e}")

    def get_status(self, family: Optional[str] = None) -> Dict[str, Any]:
        """Get pipeline status for a family or all families."""
        if family:
            return self.db.get_family_stats(family)
        return self.db.get_all_stats()

    def _get_enrichment_tier(self, attempt: int, max_retries: int) -> str:
        """
        Determine enrichment tier for a retry attempt.

        Track 2: Deterministic progressive enrichment tiers:
        - Tier 1 (attempt 0): minimal - error + targeted API snippet
        - Tier 2 (attempt 1): + top-K similar examples
        - Tier 3+ (attempt 2+): + expanded API context + explicit strategy hint

        Args:
            attempt: Current attempt number (0-indexed)
            max_retries: Maximum retry attempts

        Returns:
            Enrichment tier name
        """
        if attempt == 0:
            return "tier1_minimal"
        elif attempt == 1:
            return "tier2_with_examples"
        else:
            return "tier3_expanded"

    def _apply_progressive_enrichment(
        self,
        enrichment_tier: str,
        base_api_context: Optional[str],
        base_similar_examples: Optional[List[str]],
        error_logs: str,
        family_config: Any,
    ) -> Tuple[Optional[str], Optional[List[str]], List[str]]:
        """
        Apply progressive context enrichment based on retry tier.

        Track 2: Implements deterministic progressive enrichment:
        - Tier 1: Minimal error + targeted API snippet for missing symbols
        - Tier 2: Add top-K similar examples (deterministic ordering)
        - Tier 3+: Expanded API context + explicit strategy hint

        Args:
            enrichment_tier: Enrichment tier (tier1_minimal, tier2_with_examples, tier3_expanded)
            base_api_context: Base API context string
            base_similar_examples: Base list of similar examples
            error_logs: Error log messages
            family_config: Family configuration

        Returns:
            Tuple of (api_context, similar_examples, context_sources)
        """
        context_sources = []

        if enrichment_tier == "tier1_minimal":
            # Tier 1: Minimal - only targeted API snippet for missing symbols
            api_context = self._extract_targeted_api_context(error_logs, base_api_context)
            similar_examples = None  # No examples on first attempt
            context_sources.append("targeted_api_snippet")
            logger.debug(f"Tier 1 enrichment: targeted API context only")

        elif enrichment_tier == "tier2_with_examples":
            # Tier 2: Add top-K similar examples (deterministic K=3)
            api_context = self._extract_targeted_api_context(error_logs, base_api_context)
            context_sources.append("targeted_api_snippet")

            if base_similar_examples:
                # Deterministically select top K examples (already sorted by similarity)
                K = 3  # Stable K value
                similar_examples = base_similar_examples[:K]
                context_sources.append(f"similar_examples_k{K}")
                logger.debug(f"Tier 2 enrichment: targeted API + {len(similar_examples)} similar examples")
            else:
                similar_examples = None
                logger.debug(f"Tier 2 enrichment: targeted API only (no examples available)")

        else:  # tier3_expanded
            # Tier 3+: Expanded API context + strategy hint
            # Use full API context (not just targeted)
            api_context = base_api_context
            if api_context:
                context_sources.append("expanded_api_context")

            # Include all available similar examples
            if base_similar_examples:
                similar_examples = base_similar_examples
                context_sources.append(f"all_similar_examples_{len(similar_examples)}")
            else:
                similar_examples = None

            # Add strategy hint based on error category
            strategy_hint = self._get_strategy_hint_from_errors(error_logs, family_config)
            if strategy_hint and api_context:
                api_context = f"{api_context}\n\n## Strategy Hint:\n{strategy_hint}"
                context_sources.append("strategy_hint")
            elif strategy_hint:
                api_context = f"## Strategy Hint:\n{strategy_hint}"
                context_sources.append("strategy_hint")

            logger.debug(
                f"Tier 3 enrichment: expanded API + {len(similar_examples) if similar_examples else 0} examples + strategy"
            )

        return api_context, similar_examples, context_sources

    def _extract_targeted_api_context(
        self,
        error_logs: str,
        full_api_context: Optional[str],
    ) -> Optional[str]:
        """
        Extract targeted API context for missing symbols in error logs.

        Args:
            error_logs: Error log messages
            full_api_context: Full API context to search

        Returns:
            Targeted API context string or None
        """
        if not full_api_context:
            return None

        # Extract missing type names from errors (CS0246, CS0103, etc.)
        missing_types = set()
        for pattern in [
            r"CS0246.*'(\w+)'",  # Missing type
            r"CS0103.*'(\w+)'",  # Undefined name
            r"CS0117.*'(\w+)'",  # Missing member
        ]:
            for match in re.finditer(pattern, error_logs):
                missing_types.add(match.group(1))

        if not missing_types:
            # No specific missing types found, return truncated API context
            return full_api_context[:2000] if len(full_api_context) > 2000 else full_api_context

        # Search for relevant sections in API context
        targeted_sections = []
        for missing_type in missing_types:
            # Find sections mentioning the missing type
            for line in full_api_context.split('\n'):
                if missing_type in line:
                    # Include surrounding context (up to 10 lines)
                    start_idx = max(0, full_api_context.find(line) - 500)
                    end_idx = min(len(full_api_context), full_api_context.find(line) + 500)
                    targeted_sections.append(full_api_context[start_idx:end_idx])
                    break

        if targeted_sections:
            return "\n\n".join(targeted_sections[:3])  # Limit to 3 sections

        # Fallback to truncated full context
        return full_api_context[:2000] if len(full_api_context) > 2000 else full_api_context

    def _get_strategy_hint_from_errors(
        self,
        error_logs: str,
        family_config: Any,
    ) -> Optional[str]:
        """
        Generate explicit strategy hint based on error category.

        Args:
            error_logs: Error log messages
            family_config: Family configuration

        Returns:
            Strategy hint string or None
        """
        hints = []

        # Categorize errors
        if "CS0246" in error_logs or "could not be found" in error_logs:
            hints.append("Add missing 'using' statements for the namespace containing the missing type.")
            hints.append("Common namespaces: Aspose.Zip, Aspose.Zip.Saving, Aspose.Zip.SevenZip, Aspose.Zip.Rar")

        if "CS8803" in error_logs or "Top-level statements" in error_logs:
            hints.append("Wrap all code in 'class Program { static void Main() { ... } }' structure.")

        if "FileNotFoundException" in error_logs or "DirectoryNotFoundException" in error_logs:
            hints.append("Check file paths - use paths from the available test data list.")
            hints.append("Replace placeholder paths with actual test file names.")

        if "CS0029" in error_logs or "type mismatch" in error_logs.lower():
            hints.append("Check type compatibility - use explicit casting if needed.")

        if "CS1061" in error_logs or "does not contain" in error_logs:
            hints.append("Verify API method/property names against documentation.")
            hints.append("The member may not exist in this API version.")

        if not hints:
            return None

        return "\n".join(f"- {hint}" for hint in hints)

    def _is_code_identical(self, code1: str, code2: str) -> bool:
        """
        Check if two code snippets are identical (ignoring whitespace differences).

        Track 2: No-change loop detection - compares normalized code.

        Args:
            code1: First code snippet
            code2: Second code snippet

        Returns:
            True if code is identical (normalized), False otherwise
        """
        # Normalize: strip, lowercase, remove extra whitespace
        def normalize(code: str) -> str:
            # Remove all whitespace and convert to lowercase for comparison
            return re.sub(r'\s+', '', code.strip().lower())

        return normalize(code1) == normalize(code2)

    def _is_api_mismatch_error(self, error_logs: str) -> bool:
        """
        Task 4: Detect if compile errors are API mismatches.

        API mismatches are:
        - CS0246: Missing type or namespace
        - CS0117: Missing member
        - CS1061: Missing method/property
        - AspNetCore references

        Args:
            error_logs: Compilation error log

        Returns:
            True if error is an API mismatch
        """
        api_mismatch_patterns = [
            r"CS0246",  # Missing type
            r"CS0117",  # Missing member
            r"CS1061",  # Does not contain definition
            r"Microsoft\.AspNetCore",  # AspNetCore (not available)
            r"RarArchive\.Open",  # Specific deprecated API
            r"CompressionLevel",  # Enum mismatch
        ]

        for pattern in api_mismatch_patterns:
            if re.search(pattern, error_logs, re.IGNORECASE):
                return True
        return False

    def _search_example_repo_fallback(
        self,
        code: str,
        family_config: Any,
        error_logs: str,
    ) -> Optional[Tuple[str, str]]:
        """
        Task 4: Search example repo index for matching substitute code.

        Searches the examples index for code using the same primary class names
        that might work as a substitute for the failing snippet.

        Args:
            code: Original failing code
            family_config: Family configuration
            error_logs: Error logs for context

        Returns:
            Tuple of (substitute_code, fix_strategy) or None if no match
        """
        try:
            # Load examples index
            index_path = Path("artifacts/backfill") / family_config.family / "examples-index.json"
            if not index_path.exists():
                logger.debug(f"No examples index at {index_path}")
                return None

            with open(index_path, 'r', encoding='utf-8') as f:
                examples_index = json.load(f)

            if not examples_index.get('examples'):
                return None

            # Extract primary class names from original code
            class_patterns = [
                r'new\s+(\w+Archive)\s*\(',  # new Archive(, new RarArchive(
                r'(\w+Archive)\.',  # Archive., RarArchive.
                r'new\s+(\w+)\s*\(',  # new SomeClass(
            ]

            primary_classes = set()
            for pattern in class_patterns:
                for match in re.finditer(pattern, code):
                    primary_classes.add(match.group(1))

            if not primary_classes:
                logger.debug("No primary classes found in original code")
                return None

            logger.debug(f"Searching for substitutes using classes: {primary_classes}")

            # Search index for matching examples
            examples_dir = Path("artifacts/backfill") / family_config.family / "examples"
            best_match = None
            best_score = 0

            for example in examples_index.get('examples', []):
                example_path = example.get('path', '')
                if not example_path:
                    continue

                # Load example code from file
                example_file = examples_dir / example_path
                if not example_file.exists():
                    continue

                try:
                    example_code = example_file.read_text(encoding='utf-8')
                except Exception:
                    continue

                # Count matching class usages
                score = 0
                for cls in primary_classes:
                    if cls in example_code:
                        score += 1

                if score > best_score:
                    best_score = score
                    best_match = example_code

            if best_match and best_score >= 1:
                logger.info(f"Found example-repo substitute with score {best_score}")
                return (best_match, "example_repo_substitution")

            return None

        except Exception as e:
            logger.debug(f"Error searching example repo fallback: {e}")
            return None
