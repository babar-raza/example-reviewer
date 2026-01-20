"""
Pipeline Orchestrator for Example Reviewer.
Coordinates all pipeline phases as defined in the spec.
"""

import logging
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

from ..core.models import (
    ExampleRecord, ExampleStatus, ScanScope, ScanMode,
    ReviewResult, ReviewIssue, IssueType, IssueSeverity
)
from ..core.database import Database
from ..core.config import ConfigurationManager, FamilyConfig, GlobalConfig
from ..core.telemetry import track_phase_timing, export_run_telemetry, log_resource_decision
from ..services.discovery_service import DiscoveryService
from ..services.resource_detection_service import ResourceDetectionService
from ..services.compilation_service import CompilationService, check_dotnet_available
from ..services.runtime_service import RuntimeService
from ..services.llm_service import LLMService, LLMServiceFactory
from ..services.markdown_service import MarkdownUpdateService
from ..services.vector_db_service import VectorDBService
from ..services.telemetry_service import TelemetryService

logger = logging.getLogger(__name__)


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
        workspace_dir: Optional[Path] = None,
        artifacts_dir: Optional[Path] = None,
    ):
        """
        Initialize pipeline orchestrator.
        
        Args:
            config_dir: Directory containing family configs
            db_path: Path to SQLite database
            workspace_dir: Working directory for compilation/runtime
            artifacts_dir: Directory for storing artifacts
        """
        self.config_dir = config_dir or Path("config/families")
        self.db_path = db_path or Path("data/example_reviewer.db")
        self.workspace_dir = workspace_dir or Path("workspace")
        self.artifacts_dir = artifacts_dir or Path("artifacts")
        
        # Create directories
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.config_manager = ConfigurationManager(self.config_dir)
        self.db = Database(self.db_path)
        self.db.initialize_schema()
        
        # Services (initialized lazily)
        self._llm_service: Optional[LLMService] = None
        self._final_review_llm_service: Optional[LLMService] = None  # Separate LLM for final review
        self._discovery_service: Optional[DiscoveryService] = None
        self._compilation_service: Optional[CompilationService] = None
        self._runtime_service: Optional[RuntimeService] = None
        self._markdown_service: Optional[MarkdownUpdateService] = None
        self._vector_db_service: Optional[VectorDBService] = None
        self._resource_detection_service: Optional[ResourceDetectionService] = None
        self._telemetry_service: Optional[TelemetryService] = None

        # VectorDB and DriftDetector startup decision (Track 1: C.2)
        # Make a single decision at startup, never change mid-run
        self._drift_detector: Optional['DriftDetector'] = None
        self._drift_enabled: bool = False
        self._vector_db_startup_decision: Dict[str, Any] = {}
        self._initialize_vector_db_and_drift()
    
    @property
    def llm_service(self) -> LLMService:
        """Get or initialize LLM service."""
        if self._llm_service is None:
            global_config = self.config_manager.load_global_config()
            self._llm_service = LLMService(
                provider=global_config.llm.provider,
                model=global_config.llm.model,
                temperature=global_config.llm.temperature,
                max_retries=global_config.llm.max_retries,
                retry_backoff_seconds=global_config.llm.retry_backoff_seconds,
                timeout_seconds=global_config.llm.timeout_seconds,
                seed=global_config.llm.seed,
                deterministic_mode=global_config.llm.deterministic_mode,
                enforce_timeout=global_config.llm.enforce_timeout,
            )
        return self._llm_service

    @property
    def final_review_llm_service(self) -> LLMService:
        """
        Get or initialize separate LLM service for final review.
        Uses final_review.provider and final_review.model from config.
        """
        if self._final_review_llm_service is None:
            global_config = self.config_manager.load_global_config()

            # Determine API key based on provider (C.6: separate provider)
            provider = global_config.final_review.provider
            if provider == 'anthropic':
                api_key = os.getenv('ANTHROPIC_API_KEY')
            elif provider == 'openai':
                api_key = os.getenv('OPENAI_API_KEY')
            elif provider == 'ollama':
                api_key = 'ollama'  # Placeholder for Ollama
            else:
                # Fallback to main LLM api_key_env_var
                api_key = os.getenv(global_config.llm.api_key_env_var)

            # Determine base_url
            base_url = None
            if provider == 'ollama':
                base_url = global_config.llm.base_url or "http://localhost:11434/v1"
            elif provider == 'anthropic':
                base_url = None  # Use default Anthropic API
            # For other providers, could check if a base_url is configured

            self._final_review_llm_service = LLMService(
                provider=provider,
                model=global_config.final_review.model,
                api_key=api_key,
                base_url=base_url,
                temperature=0.0,  # Final review should be deterministic
                max_retries=1,  # Final review doesn't need retries
                retry_backoff_seconds=5,
                timeout_seconds=global_config.final_review.timeout_seconds,
                seed=None,  # Final review doesn't use seed
                deterministic_mode=False,
                enforce_timeout=True,
            )
            logger.info(
                f"Initialized final review LLM: provider={provider}, "
                f"model={global_config.final_review.model}, "
                f"timeout={global_config.final_review.timeout_seconds}s"
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
    
    @property
    def compilation_service(self) -> CompilationService:
        """Get or initialize compilation service."""
        if self._compilation_service is None:
            self._compilation_service = CompilationService(
                self.db,
                workspace_dir=self.workspace_dir / "compile",
                artifacts_dir=self.artifacts_dir / "compile",
            )
        return self._compilation_service
    
    @property
    def runtime_service(self) -> RuntimeService:
        """Get or initialize runtime service."""
        if self._runtime_service is None:
            self._runtime_service = RuntimeService(
                self.db,
                workspace_dir=self.workspace_dir / "runtime",
                artifacts_dir=self.artifacts_dir / "runtime",
            )
        return self._runtime_service
    
    @property
    def markdown_service(self) -> MarkdownUpdateService:
        """Get or initialize markdown service."""
        if self._markdown_service is None:
            global_config = self.config_manager.load_global_config()
            self._markdown_service = MarkdownUpdateService(
                self.db,
                artifacts_dir=self.artifacts_dir / "diffs",
                allow_markdown_write=global_config.markdown_write.allow_markdown_write,
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

    def _initialize_vector_db_and_drift(self):
        """
        Make a single startup decision for VectorDB and DriftDetector.

        Track 1 requirement (C.2): No lazy initialization.
        Decision is made once at orchestrator startup and recorded in telemetry.
        """
        global_config = self.config_manager.load_global_config()

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

    def _load_api_context(self, family_config: FamilyConfig, max_chars: int = 4000) -> Optional[str]:
        """
        Load API reference context for LLM prompts.

        Args:
            family_config: Family configuration with api_reference settings
            max_chars: Maximum characters to include (to fit in context window)

        Returns:
            API reference text or None if not available
        """
        if not family_config.api_reference.cache_path:
            return None

        cache_path = Path(family_config.api_reference.cache_path)
        if not cache_path.exists():
            logger.debug(f"API reference cache not found at {cache_path}")
            return None

        try:
            # Collect API reference content from cache files
            api_content = []
            # Sort glob results deterministically (case-normalized for Windows compatibility)
            for file_path in sorted(cache_path.glob("**/*.md"), key=lambda p: str(p).lower()):
                try:
                    content = file_path.read_text(encoding='utf-8')
                    api_content.append(f"# {file_path.stem}\n{content}")
                except Exception as e:
                    logger.debug(f"Error reading API file {file_path}: {e}")
                    continue

            if not api_content:
                # Also try .txt files (sorted deterministically)
                for file_path in sorted(cache_path.glob("**/*.txt"), key=lambda p: str(p).lower()):
                    try:
                        content = file_path.read_text(encoding='utf-8')
                        api_content.append(content)
                    except Exception:
                        continue

            if api_content:
                combined = "\n\n".join(api_content)
                # Truncate if too long
                if len(combined) > max_chars:
                    combined = combined[:max_chars] + "\n...[truncated]"
                return combined

        except Exception as e:
            logger.debug(f"Error loading API reference: {e}")

        return None

    def run_full_pipeline(
        self,
        family: str,
        max_examples: Optional[int] = None,
        skip_runtime: bool = False,
        skip_llm_fixes: bool = False,
        dry_run: bool = False,
        allow_md_write: bool = False,
    ) -> Dict[str, Any]:
        """
        Run the full pipeline for a family.

        Args:
            family: Family identifier
            max_examples: Maximum examples to process
            skip_runtime: Skip runtime verification phase
            skip_llm_fixes: Skip LLM-based fixing
            dry_run: Don't write changes to files
            allow_md_write: Override global config to allow markdown writes

        Returns:
            Pipeline results dictionary
        """
        results = {
            'family': family,
            'started_at': datetime.now().isoformat(),
            'phases': {},
            'success': True,
        }
        
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

        try:
            # Phase A: Discovery
            logger.info(f"Phase A: Discovery for {family}")
            with track_phase_timing(self.db, run_id, family, "discovery"):
                discovery_stats = self._run_discovery_phase(family, family_config, max_examples)
            results['phases']['discovery'] = discovery_stats

            if discovery_stats.get('error'):
                results['success'] = False
                return results

            # Phase B: Compilation
            logger.info(f"Phase B: Compilation verification for {family}")
            with track_phase_timing(self.db, run_id, family, "compilation"):
                compile_stats = self._run_compilation_phase(
                    family, family_config, max_examples, skip_llm_fixes
                )
            results['phases']['compilation'] = compile_stats

            # Phase C: Runtime (optional)
            if not skip_runtime:
                logger.info(f"Phase C: Runtime verification for {family}")
                with track_phase_timing(self.db, run_id, family, "runtime"):
                    runtime_stats = self._run_runtime_phase(
                        family, family_config, max_examples, skip_llm_fixes
                    )
                results['phases']['runtime'] = runtime_stats

            # Phase D: Markdown Update
            logger.info(f"Phase D: Markdown update for {family}")
            with track_phase_timing(self.db, run_id, family, "markdown_update"):
                update_stats = self._run_markdown_update_phase(
                    family, dry_run, allow_md_write=allow_md_write
                )
            results['phases']['markdown_update'] = update_stats

            # Phase E: Final Review (using LLM)
            if not skip_llm_fixes and self.llm_service.is_available():
                logger.info(f"Phase E: Final LLM review for {family}")
                with track_phase_timing(self.db, run_id, family, "final_review"):
                    review_stats = self._run_final_review_phase(family)
                results['phases']['final_review'] = review_stats

            # Phase F: Telemetry and Commit
            logger.info(f"Phase F: Finalization for {family}")
            with track_phase_timing(self.db, run_id, family, "finalization"):
                final_stats = self._run_finalization_phase(family, run_id, dry_run)
            results['phases']['finalization'] = final_stats

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
                        )

                    self.telemetry_service.complete_run(
                        telemetry_event_id,
                        status='success',
                        items_discovered=discovery_stats.get('examples_found', 0),
                        items_succeeded=db_stats['verified'],
                        items_failed=db_stats['failed'],
                        output_summary=f"Verified {db_stats['verified']} examples for {family}",
                    )
                    logger.debug(f"Completed telemetry run: {telemetry_event_id}")
                except Exception as e:
                    logger.warning(f"Failed to complete telemetry run: {e}")

        except Exception as e:
            logger.exception(f"Pipeline failed: {e}")
            results['success'] = False
            results['error'] = str(e)

            self.db.complete_run(run_id, status='failed', family=family, error=str(e))

            # Complete telemetry run (failure)
            if telemetry_event_id and global_config.telemetry.internal_enabled:
                try:
                    self.telemetry_service.complete_run(
                        telemetry_event_id,
                        status='failure',
                        error_summary=str(e)[:200],
                        error_details=str(e),
                    )
                except Exception:
                    pass  # Don't fail on telemetry error

        results['completed_at'] = datetime.now().isoformat()
        return results
    
    def _run_discovery_phase(
        self,
        family: str,
        family_config: FamilyConfig,
        max_examples: Optional[int],
    ) -> Dict[str, Any]:
        """Run Phase A: Discovery and Extraction."""
        max_files = None
        if max_examples:
            # Estimate ~5 examples per file
            max_files = max(1, max_examples // 5)
        
        stats = self.discovery_service.discover_family(
            family, family_config, max_files
        )
        
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
        family: str,
        family_config: FamilyConfig,
        max_examples: Optional[int],
        skip_llm_fixes: bool,
    ) -> Dict[str, Any]:
        """Run Phase B: Compilation Verification Loop."""
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
        examples = self.db.get_examples_by_family(family, ExampleStatus.DISCOVERED, max_examples)
        
        global_config = self.config_manager.load_global_config()
        max_retries = global_config.llm.max_retries
        
        for example in examples:
            stats['total_processed'] += 1
            
            try:
                # Try initial compilation
                success, result = self.compilation_service.compile_example(
                    example, family_config
                )
                
                if success:
                    # Compiled on first try
                    stats['compiled_first_try'] += 1
                    self.db.update_example_status(example.example_id, ExampleStatus.COMPILABLE)
                    self.db.update_example_code(
                        example.example_id,
                        compilable_code=example.original_code,
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
                
                if skip_llm_fixes:
                    stats['failed'] += 1
                    self.db.update_example_status(
                        example.example_id,
                        ExampleStatus.COMPILE_FAILED,
                        failure_reason='\n'.join(result.errors[:3])
                    )
                    continue
                
                # Try LLM fixes
                fixed = False
                current_code = example.original_code

                # Load API reference context for LLM (LCE-01)
                api_context = self._load_api_context(family_config)
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

                for attempt in range(max_retries):
                    # Create fix payload with full context (LCE-03)
                    payload = self.compilation_service.create_fix_payload(
                        example, result,
                        family_config=family_config,
                        api_context=api_context,
                        similar_examples=similar_examples,
                    )

                    # Get LLM fix with all context including content context for relevance
                    llm_response = self.llm_service.fix_code(
                        code=current_code,
                        error_logs='\n'.join(result.errors),
                        context_type="compile",
                        api_context=api_context,
                        similar_examples=similar_examples if similar_examples else None,
                        scaffolding_hints=payload.scaffolding_hints,
                        family_config=family_config,
                        section_heading=example.section_heading,
                        description_context=example.description_context,
                        topic=example.topic,
                    )
                    
                    if not llm_response.success:
                        continue
                    
                    fixed_code = llm_response.content.strip()
                    if not fixed_code:
                        continue

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
                                    failure_reason=f"Drift threshold exceeded ({drift_score:.3f} > {global_config.drift.threshold})"
                                )
                                stats['failed'] += 1
                                logger.info(f"Example {example.example_id} marked as compile-failed due to drift")
                                break  # Exit retry loop

                    # Update example and retry compilation
                    example.compilable_code = fixed_code
                    success, result = self.compilation_service.compile_example(
                        example, family_config
                    )
                    
                    # Record attempt
                    self.compilation_service.record_attempt(
                        example.example_id,
                        result,
                        current_code,
                        fixed_code if success else None,
                        payload.to_prompt(),
                        llm_response.content,
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
                                        failure_reason=drift_reason
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
                        self.db.update_example_status(example.example_id, ExampleStatus.COMPILABLE)
                        self.db.update_example_code(example.example_id, compilable_code=fixed_code)

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
                    stats['failed'] += 1
                    self.db.update_example_status(
                        example.example_id,
                        ExampleStatus.COMPILE_FAILED,
                        failure_reason='\n'.join(result.errors[:3])
                    )
                    
            except Exception as e:
                logger.error(f"Error compiling {example.example_id}: {e}")
                stats['errors'] += 1
        
        stats['verified'] = stats['compiled_first_try'] + stats['compiled_with_fix']
        return stats
    
    def _run_runtime_phase(
        self,
        family: str,
        family_config: FamilyConfig,
        max_examples: Optional[int],
        skip_llm_fixes: bool,
    ) -> Dict[str, Any]:
        """Run Phase C: Runtime Verification Loop."""
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
            test_data_path = Path(family_config.test_data.local_path) if family_config.test_data.local_path else None

            # Check if test data is missing
            if test_data_path and not test_data_path.exists():
                logger.info(f"Test data missing for {family}, attempting auto-backfill...")

                try:
                    from ..services.backfill_service import BackfillService

                    backfill_service = BackfillService(
                        config_manager=self.config_manager,
                        timeout_seconds=global_config.backfill.github_timeout_seconds
                    )

                    result = backfill_service.backfill_test_data(family=family, force=False)

                    if result.success and not result.skipped:
                        logger.info(f"Auto-backfilled {result.files_copied} test data files for {family}")
                        stats['backfill_files_copied'] = result.files_copied
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
            examples = self.db.get_examples_by_family(family, ExampleStatus.COMPILABLE, max_examples)
        else:
            # Get both COMPILABLE and RUNTIME_FAILED for LLM fixing
            compilable = self.db.get_examples_by_family(family, ExampleStatus.COMPILABLE, max_examples)
            failed = self.db.get_examples_by_family(family, ExampleStatus.RUNTIME_FAILED, max_examples)
            examples = compilable + failed
        
        # Get test data path and info
        test_data_path = None
        test_data_info = ""
        if family_config.test_data.local_path:
            test_data_path = Path(family_config.test_data.local_path)
            if test_data_path.exists():
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
                        alias_lines.append(f"  {real_file} → replaces: {', '.join(aliases)}")
                    test_data_info += "\n\nFile Aliases (use the real file when you see these placeholder names):\n" + "\n".join(alias_lines)
                    logger.info(f"Added {len(alias_lines)} file aliases to test_data_info for LLM context")
                else:
                    logger.warning("No file aliases configured - LLM will not know about placeholder mappings!")

        max_retries = global_config.llm.max_retries
        
        for example in examples:
            stats['total_processed'] += 1
            
            try:
                # Initialize tracking variable
                last_result = None
                
                # Copy compilable code to verified for execution
                example.verified_code = example.compilable_code

                success, result = self.runtime_service.execute_example(
                    example, family_config, test_data_path
                )
                last_result = result  # Track result for failure reporting

                # Record runtime attempt
                sample_ref = str(test_data_path) if test_data_path else "none"
                self.runtime_service.record_attempt(
                    example_id=example.example_id,
                    family=family,
                    runtime_result=result,
                    sample_ref=sample_ref,
                    scenario="first_try",
                    retrieved_examples=None,
                    llm_request=None,
                    llm_response=None,
                )

                if success:
                    stats['passed_first_try'] += 1
                    self.db.update_example_status(example.example_id, ExampleStatus.VERIFIED)
                    self.db.update_example_code(
                        example.example_id,
                        verified_code=example.compilable_code,
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
                
                # Runtime failed - try LLM fixes if enabled
                if not skip_llm_fixes and self.llm_service.is_available():
                    fixed = False
                    current_code = example.compilable_code

                    # Load API reference context for LLM (LCE-04)
                    api_context = self._load_api_context(family_config)
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

                    for attempt in range(max_retries):
                        stats['llm_fix_attempts'] += 1

                        # Detect if this is a build failure vs runtime failure
                        is_build_error = self._is_build_failure(result.stderr)

                        if is_build_error:
                            # Build failures need compilation fix prompts, not runtime prompts
                            logger.info(f"Build failure detected for {example.example_id}, using compile fix")
                            error_logs = result.stderr or "Build failed"

                            # Get scaffolding hints from compilation service
                            error_categories = self.compilation_service.categorize_errors(error_logs)
                            hints = self.compilation_service.get_error_fix_hints(error_categories, family_config)

                            llm_response = self.llm_service.fix_code(
                                code=current_code,
                                error_logs=error_logs,
                                context_type="compile",  # Use compilation prompts
                                api_context=api_context,  # LCE-04
                                scaffolding_hints=hints,
                                similar_examples=similar_examples if similar_examples else None,
                                family_config=family_config,
                                section_heading=example.section_heading,
                                description_context=example.description_context,
                                topic=example.topic,
                                original_code=example.original_code,
                            )
                        else:
                            # True runtime error - use runtime fix prompts
                            error_context = f"""Exit Code: {result.exit_code}
Exception Type: {result.exception_type or 'Unknown'}
Exception Message: {result.exception_message or 'No message'}
Stderr: {result.stderr[:500] if result.stderr else 'None'}"""

                            llm_response = self.llm_service.fix_code(
                                code=current_code,
                                error_logs=error_context,
                                context_type="runtime",
                                api_context=api_context,  # LCE-04
                                test_data_info=test_data_info,
                                similar_examples=similar_examples if similar_examples else None,
                                family_config=family_config,
                                section_heading=example.section_heading,
                                description_context=example.description_context,
                                topic=example.topic,
                                original_code=example.original_code,
                            )
                        
                        if not llm_response.success or not llm_response.content:
                            logger.warning(f"LLM fix failed for {example.example_id}: {llm_response.error}")
                            break

                        fixed_code = llm_response.content

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
                                        failure_reason=f"Drift threshold exceeded ({drift_score:.3f} > {global_config.drift.threshold})"
                                    )
                                    stats['failed'] += 1
                                    logger.info(f"Example {example.example_id} marked as runtime-failed due to drift")
                                    break  # Exit retry loop

                        example.verified_code = fixed_code

                        # Track previous result for cascading detection
                        prev_result = result

                        # Re-run with fixed code
                        success, result = self.runtime_service.execute_example(
                            example, family_config, test_data_path
                        )
                        last_result = result  # Track last result for error reporting

                        # Record runtime attempt with LLM fix context
                        self.runtime_service.record_attempt(
                            example_id=example.example_id,
                            family=family,
                            runtime_result=result,
                            sample_ref=sample_ref,
                            scenario=f"llm_fix_attempt_{attempt + 1}",
                            retrieved_examples=retrieved_example_ids if retrieved_example_ids else None,
                            llm_request=llm_response.raw_prompt if hasattr(llm_response, 'raw_prompt') else None,
                            llm_response=llm_response.content,
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
                                            failure_reason=drift_reason
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
                            self.db.update_example_status(example.example_id, ExampleStatus.VERIFIED)
                            self.db.update_example_code(
                                example.example_id,
                                verified_code=fixed_code,
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
                # Use last_result for failure reporting (always defined)
                if last_result is not None:
                    failure_reason = (
                        last_result.exception_message 
                        or (last_result.stderr[:200] if last_result.stderr else None)
                        or "Unknown runtime error"
                    )
                else:
                    failure_reason = "Unknown runtime error (no result)"
                self.db.update_example_status(
                    example.example_id,
                    ExampleStatus.RUNTIME_FAILED,
                    failure_reason=failure_reason
                )
                
            except Exception as e:
                logger.error(f"Error running {example.example_id}: {e}")
                stats['errors'] += 1
        
        stats['verified'] = stats['passed_first_try'] + stats['passed_with_fix']
        return stats
    
    def _run_markdown_update_phase(
        self,
        family: str,
        dry_run: bool,
        allow_md_write: bool = False,
    ) -> Dict[str, Any]:
        """
        Run Phase D: Markdown Update.

        Args:
            family: Family identifier
            dry_run: If True, don't write changes
            allow_md_write: If True, override global config to allow markdown writes

        Returns:
            Statistics dictionary
        """
        # If allow_md_write is explicitly True, recreate service with override
        if allow_md_write and not self.markdown_service.allow_markdown_write:
            global_config = self.config_manager.load_global_config()
            self._markdown_service = MarkdownUpdateService(
                self.db,
                artifacts_dir=self.artifacts_dir / "diffs",
                allow_markdown_write=True,  # Override to True
            )
            logger.info("Markdown writes ENABLED via --allow-md-write flag")

        return self.markdown_service.update_all_files(family, dry_run)

    def _consensus_review(
        self,
        content: str,
        snippets: List[Dict[str, Any]],
        num_passes: int = 2,
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
            result = self.final_review_llm_service.review_markdown_structured(content, snippets)
            reviews.append(result)

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
            tiebreaker = self.final_review_llm_service.review_markdown_structured(content, snippets)
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

    def _run_final_review_phase(self, family: str) -> Dict[str, Any]:
        """
        Run Phase E: Final LLM Review with structured issue tracking.

        Implements re-review loop up to max_review_attempts if issues are found.
        All reviews and issues are saved to the database for audit trail.
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

        # Get the current run_id for this pipeline
        # We need to find the most recent run for this family
        run_record = self.db.get_latest_run(family)
        run_id = run_record.run_id if run_record else "unknown"

        # Get updated examples
        examples = self.db.get_examples_by_family(family, ExampleStatus.MD_UPDATED)

        # Group by file
        files: Dict[str, List[ExampleRecord]] = {}
        for example in examples:
            if example.file_path not in files:
                files[example.file_path] = []
            files[example.file_path].append(example)

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

                    # Call consensus review (2 passes for reliability)
                    review_result = self._consensus_review(
                        content, snippets
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
                                e.example_id, ExampleStatus.FINAL_REVIEW_PASSED
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
                            e.example_id, ExampleStatus.FINAL_REVIEW_FAILED
                        )

            except Exception as e:
                logger.error(f"Error reviewing {file_path}: {e}")
                stats['failed'] += 1
                # Mark examples as failed on exception
                for ex in file_examples:
                    self.db.update_example_status(
                        ex.example_id,
                        ExampleStatus.FINAL_REVIEW_FAILED,
                        failure_reason=f"Review error: {str(e)}"
                    )

        return stats
    
    def _run_finalization_phase(
        self,
        family: str,
        run_id: str,
        dry_run: bool,
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

        if dry_run or not global_config.git.enabled:
            return stats

        # Get files that were updated
        examples = self.db.get_examples_by_family(family, ExampleStatus.FINAL_REVIEW_PASSED)
        touched_files = list(set(e.file_path for e in examples))

        if not touched_files:
            return stats

        # Attempt git commit
        try:
            # Resolve absolute paths and find git root
            # File paths are stored relative to content_roots, need to find actual git repo
            first_file = Path(touched_files[0]).resolve()

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

            # Stage files - paths relative to git root
            for file_path in touched_files:
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

            # Build full commit message with description and co-author
            message_title = global_config.git.commit_message_template.format(
                family=family,
                count=len(touched_files),
            )
            description = global_config.git.commit_description_template.format(
                family=family,
                count=len(touched_files),
                run_id=run_id,
            )
            # Hardcoded co-author per project policy
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
                    self.db.update_example_status(e.example_id, ExampleStatus.COMMITTED)

        except Exception as e:
            logger.error(f"Git commit failed: {e}")
            stats['error'] = str(e)
        
        return stats
    
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

        global_config = self.config_manager.load_global_config()

        # Compute config hash
        config_hash = self.config_manager.compute_config_hash(family)

        # Build LLM capabilities
        llm_capabilities = {
            'provider': global_config.llm.provider,
            'model': global_config.llm.model,
            'temperature': global_config.llm.temperature,
            'timeout_seconds': global_config.llm.timeout_seconds,
            'seed_supported': True,  # Assume supported unless provider rejects
            'timeout_supported': True,
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

        # Update fingerprint with selection_hash (after discovery)
        try:
            fingerprint = self.db.get_run_fingerprint(run_id)
            if fingerprint:
                # Compute selection_hash from all examples in family
                examples = self.db.get_examples_by_family(family)
                example_keys = [ex.example_key for ex in examples if ex.example_key]
                selection_hash = self.db.compute_selection_hash(example_keys)

                # Update fingerprint
                fingerprint.selection_hash = selection_hash
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
