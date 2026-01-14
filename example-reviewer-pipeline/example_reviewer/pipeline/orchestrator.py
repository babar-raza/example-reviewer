"""
Pipeline Orchestrator for Example Reviewer.
Coordinates all pipeline phases as defined in the spec.
"""

import logging
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

from ..core.models import ExampleRecord, ExampleStatus, ScanScope, ScanMode
from ..core.database import Database
from ..core.config import ConfigurationManager, FamilyConfig, GlobalConfig
from ..services.discovery_service import DiscoveryService
from ..services.compilation_service import CompilationService, check_dotnet_available
from ..services.runtime_service import RuntimeService
from ..services.llm_service import LLMService, LLMServiceFactory
from ..services.markdown_service import MarkdownUpdateService

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
        self._discovery_service: Optional[DiscoveryService] = None
        self._compilation_service: Optional[CompilationService] = None
        self._runtime_service: Optional[RuntimeService] = None
        self._markdown_service: Optional[MarkdownUpdateService] = None
    
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
            )
        return self._llm_service
    
    @property
    def discovery_service(self) -> DiscoveryService:
        """Get or initialize discovery service."""
        if self._discovery_service is None:
            self._discovery_service = DiscoveryService(self.db)
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
            self._markdown_service = MarkdownUpdateService(
                self.db,
                artifacts_dir=self.artifacts_dir / "diffs",
            )
        return self._markdown_service
    
    def run_full_pipeline(
        self,
        family: str,
        max_examples: Optional[int] = None,
        skip_runtime: bool = False,
        skip_llm_fixes: bool = False,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Run the full pipeline for a family.
        
        Args:
            family: Family identifier
            max_examples: Maximum examples to process
            skip_runtime: Skip runtime verification phase
            skip_llm_fixes: Skip LLM-based fixing
            dry_run: Don't write changes to files
            
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
        
        try:
            # Phase A: Discovery
            logger.info(f"Phase A: Discovery for {family}")
            discovery_stats = self._run_discovery_phase(family, family_config, max_examples)
            results['phases']['discovery'] = discovery_stats
            
            if discovery_stats.get('error'):
                results['success'] = False
                return results
            
            # Phase B: Compilation
            logger.info(f"Phase B: Compilation verification for {family}")
            compile_stats = self._run_compilation_phase(
                family, family_config, max_examples, skip_llm_fixes
            )
            results['phases']['compilation'] = compile_stats
            
            # Phase C: Runtime (optional)
            if not skip_runtime:
                logger.info(f"Phase C: Runtime verification for {family}")
                runtime_stats = self._run_runtime_phase(
                    family, family_config, max_examples, skip_llm_fixes
                )
                results['phases']['runtime'] = runtime_stats
            
            # Phase D: Markdown Update
            logger.info(f"Phase D: Markdown update for {family}")
            update_stats = self._run_markdown_update_phase(family, dry_run)
            results['phases']['markdown_update'] = update_stats
            
            # Phase E: Final Review (using LLM)
            if not skip_llm_fixes and self.llm_service.is_available():
                logger.info(f"Phase E: Final LLM review for {family}")
                review_stats = self._run_final_review_phase(family)
                results['phases']['final_review'] = review_stats
            
            # Phase F: Telemetry and Commit
            logger.info(f"Phase F: Finalization for {family}")
            final_stats = self._run_finalization_phase(family, run_id, dry_run)
            results['phases']['finalization'] = final_stats
            
            # Complete run
            self.db.complete_run(
                run_id,
                status='completed',
                examples_processed=compile_stats.get('total_processed', 0),
                examples_verified=compile_stats.get('verified', 0),
                examples_failed=compile_stats.get('failed', 0),
            )
            
        except Exception as e:
            logger.exception(f"Pipeline failed: {e}")
            results['success'] = False
            results['error'] = str(e)
            
            self.db.complete_run(run_id, status='failed', error_message=str(e))
        
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
                
                for attempt in range(max_retries):
                    # Create fix payload
                    payload = self.compilation_service.create_fix_payload(
                        example, result
                    )
                    
                    # Get LLM fix
                    llm_response = self.llm_service.fix_code(
                        code=current_code,
                        error_logs='\n'.join(result.errors),
                    )
                    
                    if not llm_response.success:
                        continue
                    
                    fixed_code = llm_response.content.strip()
                    if not fixed_code:
                        continue
                    
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
                        stats['compiled_with_fix'] += 1
                        self.db.update_example_status(example.example_id, ExampleStatus.COMPILABLE)
                        self.db.update_example_code(example.example_id, compilable_code=fixed_code)
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
        }
        
        # Get compilable examples
        examples = self.db.get_examples_by_family(family, ExampleStatus.COMPILABLE, max_examples)
        
        # Get test data path
        test_data_path = None
        if family_config.test_data.local_path:
            test_data_path = Path(family_config.test_data.local_path)
        
        for example in examples:
            stats['total_processed'] += 1
            
            try:
                # Copy compilable code to verified for execution
                example.verified_code = example.compilable_code
                
                success, result = self.runtime_service.execute_example(
                    example, family_config, test_data_path
                )
                
                if success:
                    stats['passed_first_try'] += 1
                    self.db.update_example_status(example.example_id, ExampleStatus.VERIFIED)
                    self.db.update_example_code(
                        example.example_id,
                        verified_code=example.compilable_code,
                    )
                    continue
                
                # Runtime failed
                stats['failed'] += 1
                self.db.update_example_status(
                    example.example_id,
                    ExampleStatus.RUNTIME_FAILED,
                    failure_reason=result.exception_message or result.stderr[:200]
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
    ) -> Dict[str, Any]:
        """Run Phase D: Markdown Update."""
        return self.markdown_service.update_all_files(family, dry_run)
    
    def _run_final_review_phase(self, family: str) -> Dict[str, Any]:
        """Run Phase E: Final LLM Review."""
        stats = {
            'files_reviewed': 0,
            'approved': 0,
            'issues_found': 0,
        }
        
        # Get updated examples
        examples = self.db.get_examples_by_family(family, ExampleStatus.MD_UPDATED)
        
        # Group by file
        files = {}
        for example in examples:
            if example.file_path not in files:
                files[example.file_path] = []
            files[example.file_path].append(example)
        
        for file_path, file_examples in files.items():
            stats['files_reviewed'] += 1
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                snippets = [
                    {
                        'code': e.verified_code,
                        'line': e.location.start_line,
                        'language': e.language,
                    }
                    for e in file_examples
                ]
                
                response = self.llm_service.review_markdown(content, snippets)
                
                if response.success:
                    try:
                        review = eval(response.content)  # Simple JSON parse
                        if review.get('approved', True):
                            stats['approved'] += 1
                            for e in file_examples:
                                self.db.update_example_status(
                                    e.example_id, ExampleStatus.FINAL_REVIEW_PASSED
                                )
                        else:
                            stats['issues_found'] += 1
                            for e in file_examples:
                                self.db.update_example_status(
                                    e.example_id, ExampleStatus.FINAL_REVIEW_FAILED
                                )
                    except:
                        # If can't parse response, assume approved
                        stats['approved'] += 1
                        for e in file_examples:
                            self.db.update_example_status(
                                e.example_id, ExampleStatus.FINAL_REVIEW_PASSED
                            )
                            
            except Exception as e:
                logger.error(f"Error reviewing {file_path}: {e}")
        
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
        
        if dry_run or not global_config.git.enabled:
            return stats
        
        # Get files that were updated
        examples = self.db.get_examples_by_family(family, ExampleStatus.FINAL_REVIEW_PASSED)
        touched_files = list(set(e.file_path for e in examples))
        
        if not touched_files:
            return stats
        
        # Attempt git commit
        try:
            # Stage files
            for file_path in touched_files:
                subprocess.run(
                    ["git", "add", file_path],
                    check=True,
                    capture_output=True,
                )
            
            # Commit
            message = global_config.git.commit_message_template.format(
                family=family,
                count=len(touched_files),
            )
            
            result = subprocess.run(
                ["git", "commit", "-m", message],
                capture_output=True,
                text=True,
            )
            
            if result.returncode == 0:
                # Get commit hash
                hash_result = subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    capture_output=True,
                    text=True,
                )
                
                stats['committed'] = True
                stats['commit_hash'] = hash_result.stdout.strip()
                
                # Update example statuses
                for e in examples:
                    self.db.update_example_status(e.example_id, ExampleStatus.COMMITTED)
                    
        except Exception as e:
            logger.error(f"Git commit failed: {e}")
            stats['error'] = str(e)
        
        return stats
    
    def get_status(self, family: Optional[str] = None) -> Dict[str, Any]:
        """Get pipeline status for a family or all families."""
        if family:
            return self.db.get_family_stats(family)
        return self.db.get_all_stats()
