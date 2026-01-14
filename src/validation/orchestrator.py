"""
Validation Orchestrator for Example Review System.
Coordinates the 5-stage validation pipeline.
"""

from typing import Dict, Optional, Tuple, List
from pathlib import Path

from src.core.database import Database, Snippet
from src.core.telemetry import TelemetryClient
from src.llm.ollama_integration import OllamaClient
from src.api_reference.api_reference_service import ApiReferenceService

# Relative imports within validation package
from .analysis.pattern_registry import PatternRegistry
from .analysis.namespace_validator import NamespaceValidator
from .fixing.persistent_fix_service import PersistentFixService, FixResult
from .fixing.dependency_resolver import DependencyResolver
from .workspace.workspace_manager import WorkspaceManager


class ValidationOrchestrator:
    """
    Orchestrates the validation pipeline for code snippets.

    Pipeline stages:
    0. Setup workspace
    1. Pattern-based pre-fix
    2. Compile original
    3. Compile with pattern fixes
    4. Ollama auto-fix (up to 3 attempts)
    5. Finalization
    """

    def __init__(self, db: Database, telemetry: TelemetryClient,
                 pattern_registry: PatternRegistry, workspace: WorkspaceManager,
                 ollama: Optional[OllamaClient], family_config: Dict):
        """
        Initialize validation orchestrator.

        Args:
            db: Database instance
            telemetry: Telemetry client
            pattern_registry: Pattern registry
            workspace: Workspace manager
            ollama: Ollama client (optional)
            family_config: Family configuration
        """
        self.db = db
        self.telemetry = telemetry
        self.pattern_registry = pattern_registry
        self.workspace = workspace
        self.ollama = ollama
        self.family_config = family_config

        # Initialize API reference service for enriched LLM prompts
        self.api_reference = ApiReferenceService(db=db, cache_size=128)

        # Initialize namespace validator if policy is defined
        namespace_policy = family_config.get('namespace_policy', {})
        self.namespace_validator = NamespaceValidator(namespace_policy) if namespace_policy else None

        # Initialize dependency resolver (if enabled in config)
        dep_config = family_config.get('dependency_resolution', {})
        if dep_config.get('enabled', False):
            self.dependency_resolver = DependencyResolver(
                db_conn=db._conn,
                workspace_dir=workspace.validator_dir,
                telemetry=telemetry
            )
        else:
            self.dependency_resolver = None

    def validate_snippet(self, snippet_id: int, run_id: int, use_ollama: bool = True) -> Dict:
        """
        Validate a single snippet through the pipeline.

        Args:
            snippet_id: Snippet ID to validate
            run_id: Current run ID
            use_ollama: Whether to use Ollama for fixing

        Returns:
            Validation result dictionary
        """
        snippet = self.db.get_snippet(snippet_id)
        if not snippet:
            return {'status': 'error', 'message': 'Snippet not found'}

        # Get original version
        original_version = self.db.get_latest_snippet_version(snippet_id, 'original')
        if not original_version:
            return {'status': 'error', 'message': 'Original version not found'}

        original_code = original_version.code_content

        result = {
            'snippet_id': snippet_id,
            'status': 'unverified',
            'stages_completed': [],
            'issues_detected': 0,
            'fixes_applied': 0,
            'build_attempts': 0,
            'final_code': original_code
        }

        with self.telemetry.track_validation(snippet_id, self.family_config.get('family', '')):
            # Stage 0: Namespace validation (if enabled)
            if self.namespace_validator:
                is_valid, violations = self.namespace_validator.validate(original_code)
                if not is_valid:
                    # Namespace policy violation detected
                    violation_msg = '; '.join(violations)
                    result['status'] = 'needs-fix'
                    result['message'] = f'Namespace policy violation: {violation_msg}'
                    result['namespace_violations'] = violations

                    # Log violation
                    self.db.log_event(
                        run_id, 'namespace_violation', 'warning',
                        f'Snippet {snippet_id} violates namespace policy: {violation_msg}'
                    )

                    # Mark snippet as needs-fix
                    self.db.update_snippet(snippet_id, status='needs-fix')
                    self.telemetry.increment_metric('namespace_violations')

                    return result

            # Stage 0.5: Dependency Resolution (if enabled)
            if self.dependency_resolver:
                result['stages_completed'].append('dependency_resolution')

                try:
                    success, resolutions = self.dependency_resolver.analyze_and_resolve(
                        snippet_id, original_code, run_id
                    )

                    if not success:
                        result['status'] = 'needs-fix'
                        result['message'] = 'Dependency resolution failed'
                        self.db.update_snippet(snippet_id, status='needs-fix')
                        self.telemetry.increment_metric('dependency_resolution_failed')
                        return result

                    # Log resolved dependencies
                    resolved_count = len([r for r in resolutions if r.status == 'resolved'])
                    if resolved_count > 0:
                        self.db.log_event(
                            run_id, 'dependencies_resolved', 'info',
                            f'Resolved {resolved_count} dependencies for snippet {snippet_id}'
                        )
                        self.telemetry.increment_metric('dependencies_resolved', resolved_count)

                except Exception as e:
                    # Log error but continue - dependency resolution is best-effort
                    self.db.log_event(
                        run_id, 'dependency_resolution_error', 'warning',
                        f'Dependency resolution error for snippet {snippet_id}: {str(e)}'
                    )

            # Stage 1: Pattern-based pre-fix
            fixed_code, pattern_fixes = self.pattern_registry.apply_fixes(original_code, auto_only=True)
            result['stages_completed'].append('pattern_fixes')

            if pattern_fixes:
                result['fixes_applied'] = len([f for f in pattern_fixes if f.applied])
                # Save fixed version
                before_version_id = original_version.version_id
                after_version_id = self.db.create_snippet_version(
                    snippet_id, 'fixed', fixed_code, 'pattern',
                    f"Applied {len(pattern_fixes)} pattern fixes"
                )

                # Record fixes
                for fix in pattern_fixes:
                    if fix.applied:
                        self.db.create_fix(
                            snippet_id, 'pattern', fix.description,
                            True, None, before_version_id, after_version_id
                        )

            # Stage 2: Compile original
            result['stages_completed'].append('compile_original')
            result['build_attempts'] += 1

            # Track verified candidate (which version successfully compiled)
            verified_candidate = None  # Will be ('original', code, version_id) or ('fixed', code, version_id) or ('ollama', code, version_id)

            with self.telemetry.track_compilation(snippet_id, original_version.version_id, 1):
                success, output, error_count = self.workspace.validate_code(original_code)

                self.db.create_build_attempt(
                    snippet_id, original_version.version_id, run_id,
                    success, output, error_count
                )

                if success:
                    # Original code compiles!
                    verified_candidate = ('original', original_code, original_version.version_id)
                    result['status'] = 'verified'
                    result['message'] = 'Original code compiles successfully'
                    # Don't return yet - runtime validation may still need to run

            # Stage 3: Compile with pattern fixes (only if not already verified)
            if verified_candidate is None and fixed_code != original_code:
                result['stages_completed'].append('compile_fixed')
                result['build_attempts'] += 1

                fixed_version = self.db.get_latest_snippet_version(snippet_id, 'fixed')
                if fixed_version:
                    with self.telemetry.track_compilation(snippet_id, fixed_version.version_id, 2):
                        success, output, error_count = self.workspace.validate_code(fixed_code)

                        self.db.create_build_attempt(
                            snippet_id, fixed_version.version_id, run_id,
                            success, output, error_count
                        )

                        if success:
                            # Pattern fixes made it compile!
                            verified_candidate = ('fixed', fixed_code, fixed_version.version_id)
                            result['status'] = 'verified'
                            result['message'] = 'Pattern fixes resolved compilation errors'
                            result['final_code'] = fixed_code
                            # Don't return yet - runtime validation may still need to run

                        # Save errors for Ollama
                        result['compilation_errors'] = self.workspace.extract_errors(output)

            # Stage 4: Persistent Ollama auto-fix (if enabled and available, and not already verified)
            if verified_candidate is None and use_ollama and self.ollama and self.ollama.is_available():
                result['stages_completed'].append('persistent_ollama_fixes')

                current_code = fixed_code if fixed_code != original_code else original_code

                # Check if persistent fix is enabled in config
                persistent_config = self.family_config.get('persistent_fix', {})
                use_persistent_fix = persistent_config.get('enabled', True)

                if use_persistent_fix:
                    # Use PersistentFixService for iterative fixing with model fallback
                    persistent_fix_service = PersistentFixService(
                        db=self.db,
                        workspace=self.workspace,
                        ollama=self.ollama,
                        telemetry=self.telemetry,
                        family_config=self.family_config,
                        api_reference=self.api_reference
                    )

                    # Run persistent fix WITHOUT immediate patching callback
                    # Patching will be deferred until after runtime validation
                    fix_result = persistent_fix_service.fix_with_persistence(
                        snippet_id=snippet_id,
                        current_code=current_code,
                        run_id=run_id,
                        on_success_callback=None  # Defer patching until runtime validation completes
                    )

                    # Update result based on fix outcome
                    result['build_attempts'] += fix_result.iterations_used

                    if fix_result.success:
                        # Persistent fix succeeded!
                        ollama_version = self.db.get_snippet_version(fix_result.final_version_id)
                        verified_candidate = ('ollama', fix_result.final_code, fix_result.final_version_id)
                        result['status'] = 'verified'
                        result['message'] = f'Fixed after {fix_result.iterations_used} iterations using {fix_result.final_model}'
                        result['final_code'] = fix_result.final_code
                        result['fixes_applied'] += 1

                        # Note: snippet already marked as verified in fix_with_persistence
                        self.telemetry.increment_metric('persistent_fix_success')
                        # Don't return yet - runtime validation may still need to run
                    else:
                        # Persistent fix failed - log reason
                        result['message'] = f'Persistent fix stopped: {fix_result.stopped_reason} after {fix_result.iterations_used} iterations'
                        self.telemetry.increment_metric('persistent_fix_failure')
                        self.telemetry.log_event(
                            'persistent_fix_stopped',
                            'warning',
                            f'Persistent fix stopped: {fix_result.stopped_reason}',
                            {
                                'snippet_id': snippet_id,
                                'iterations': fix_result.iterations_used,
                                'models_tried': fix_result.models_tried,
                                'reason': fix_result.stopped_reason
                            }
                        )
                else:
                    # Fallback to original 3-attempt logic if persistent fix is disabled
                    current_version = self.db.get_latest_snippet_version(snippet_id, 'fixed') or original_version

                    for attempt in range(1, 4):  # 3 attempts
                        success, output, error_count = self.workspace.validate_code(current_code)

                        if success:
                            break

                        errors = self.workspace.extract_errors(output)
                        if not errors:
                            break

                        with self.telemetry.track_fix(snippet_id, 'ollama'):
                            ollama_fixed = self.ollama.fix_code(
                                current_code,
                                '\n'.join(errors),
                                self.family_config,
                                attempt
                            )

                            if not ollama_fixed or ollama_fixed == current_code:
                                continue

                            ollama_version_id = self.db.create_snippet_version(
                                snippet_id, 'fixed', ollama_fixed, 'ollama',
                                f"Ollama fix attempt {attempt}"
                            )

                            result['build_attempts'] += 1

                            with self.telemetry.track_compilation(snippet_id, ollama_version_id, attempt + 2):
                                success, output, error_count = self.workspace.validate_code(ollama_fixed)

                                self.db.create_build_attempt(
                                    snippet_id, ollama_version_id, run_id,
                                    success, output, error_count
                                )

                                if success:
                                    verified_candidate = ('ollama', ollama_fixed, ollama_version_id)
                                    result['status'] = 'verified'
                                    result['message'] = f'Ollama fixed on attempt {attempt}'
                                    result['final_code'] = ollama_fixed
                                    result['fixes_applied'] += 1

                                    self.db.create_fix(
                                        snippet_id, 'ollama',
                                        f"Ollama fix attempt {attempt}",
                                        True, None, current_version.version_id, ollama_version_id
                                    )

                                    # Don't mark as verified yet - runtime validation may still need to run
                                    # Don't return yet - runtime validation may still need to run
                                    break  # Exit attempt loop

                                current_code = ollama_fixed
                                current_version = self.db.get_snippet_version(ollama_version_id)

            # Stage 4.5: Runtime Validation (if enabled and we have a verified candidate)
            runtime_config = self.family_config.get('runtime_validation', {})
            runtime_enabled = runtime_config.get('enabled', False)

            if verified_candidate is not None and runtime_enabled:
                result['stages_completed'].append('runtime_validation')

                candidate_type, candidate_code, candidate_version_id = verified_candidate

                # Prepare execution parameters
                exec_params = {
                    'timeout': runtime_config.get('timeout_seconds', 30),
                    'required_files': runtime_config.get('required_files', []),
                    'file_aliases': runtime_config.get('file_aliases', {}),
                    'expected_outputs': runtime_config.get('expected_outputs', []),
                    'env': runtime_config.get('env', {})
                }

                # Execute the code
                self.telemetry.increment_metric('runtime_validation_attempts')
                exec_success, exec_json, raw_output = self.workspace.execute_code(candidate_code, exec_params)

                # Store execution result
                self.db.create_execution_result(
                    snippet_id=snippet_id,
                    run_id=run_id,
                    success=exec_success,
                    exit_code=exec_json.get('ExitCode') or exec_json.get('exit_code'),
                    duration_ms=exec_json.get('DurationMs') or exec_json.get('duration_ms'),
                    stdout=exec_json.get('Stdout') or exec_json.get('stdout'),
                    stderr=exec_json.get('Stderr') or exec_json.get('stderr'),
                    exception_type=exec_json.get('ExceptionType') or exec_json.get('exception_type'),
                    exception_message=exec_json.get('ExceptionMessage') or exec_json.get('exception_message'),
                    stack_trace=exec_json.get('StackTrace') or exec_json.get('stack_trace')
                )

                # Apply strict/lenient mode semantics
                runtime_mode = runtime_config.get('mode', 'strict')

                if not exec_success:
                    if runtime_mode == 'strict':
                        # Strict mode: downgrade to needs-fix
                        result['status'] = 'needs-fix'
                        exception_info = exec_json.get('ExceptionType') or exec_json.get('exception_type') or 'Unknown'
                        result['message'] = f'Runtime validation failed: {exception_info}'
                        self.db.update_snippet(snippet_id, status='needs-fix')
                        self.telemetry.increment_metric('runtime_validation_failed_strict')

                        # Log runtime failure
                        self.db.log_event(
                            run_id, 'runtime_validation_failed', 'warning',
                            f'Snippet {snippet_id} failed runtime validation in strict mode: {exception_info}'
                        )
                    else:
                        # Lenient mode: keep verified but add warning
                        result['runtime_warning'] = f"Runtime validation failed but lenient mode allows verification"
                        result['runtime_exception'] = exec_json.get('ExceptionType') or exec_json.get('exception_type')
                        self.telemetry.increment_metric('runtime_validation_failed_lenient')

                        # Log runtime warning
                        self.db.log_event(
                            run_id, 'runtime_validation_warning', 'info',
                            f'Snippet {snippet_id} failed runtime validation but passed in lenient mode'
                        )
                else:
                    # Runtime validation passed
                    self.telemetry.increment_metric('runtime_validation_success')
                    result['runtime_validated'] = True

            # Stage 4.6: Immediate Patching (if runtime passed or runtime disabled)
            # Only patch if we have a verified candidate and either:
            # 1. Runtime validation is disabled, OR
            # 2. Runtime validation passed (status is still 'verified')
            if verified_candidate is not None:
                candidate_type, candidate_code, candidate_version_id = verified_candidate

                # Check if we should trigger immediate patching
                persistent_config = self.family_config.get('persistent_fix', {})
                should_patch = (
                    persistent_config.get('enable_immediate_patching', True) and
                    result['status'] == 'verified'  # Only patch if still verified (runtime didn't downgrade)
                )

                if should_patch:
                    # Trigger immediate patching
                    try:
                        from src.patching.patching_service import PatchingService

                        # Get snippet to determine content root
                        snippet = self.db.get_snippet(snippet_id)
                        if snippet:
                            page = self.db.get_page(snippet.page_id)
                            if page:
                                # Determine content root from page file_path
                                file_path = Path(page.file_path)
                                content_root = file_path.parent
                                while content_root.name != 'content' and content_root.parent != content_root:
                                    content_root = content_root.parent

                                # Create patcher and patch single snippet
                                patcher = PatchingService(db=self.db, content_root=str(content_root))
                                patch_result = patcher.patch_single_snippet(snippet_id, candidate_code)

                                if not patch_result.success:
                                    # Log warning but don't fail validation
                                    self.telemetry.log_event(
                                        'immediate_patch_warning',
                                        'warning',
                                        f'Failed to patch snippet {snippet_id}: {patch_result.message}',
                                        {'snippet_id': snippet_id}
                                    )
                    except Exception as e:
                        # Log error but don't fail validation
                        self.telemetry.log_event(
                            'immediate_patch_error',
                            'error',
                            f'Error patching snippet {snippet_id}: {e}',
                            {'snippet_id': snippet_id, 'error': str(e)}
                        )

                # Update snippet status if still verified
                if result['status'] == 'verified':
                    self.db.update_snippet(snippet_id, status='verified')
                    self.telemetry.increment_metric('snippets_verified')

            # Stage 5: Finalization
            result['stages_completed'].append('finalization')

            # Mark as needs-fix if we couldn't verify
            if result['status'] == 'unverified':
                result['status'] = 'needs-fix'
                result['message'] = 'Could not verify after all attempts'
                self.db.update_snippet(snippet_id, status='needs-fix')

            # Save current version as 'current'
            self.db.create_snippet_version(
                snippet_id, 'current', result['final_code'], 'system',
                'Final validation state'
            )

            # Update validation tracking
            self.db.update_snippet(
                snippet_id,
                validation_attempts=result['build_attempts'],
                last_validated_at=self.db._conn.execute("SELECT datetime('now')").fetchone()[0]
            )

        return result
