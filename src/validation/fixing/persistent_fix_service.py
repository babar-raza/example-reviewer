"""
Persistent Fix Service for Example Review System.
Iteratively fixes broken code snippets using LLM with model fallback and context inference.
"""

import re
import time
import hashlib
import uuid
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from pathlib import Path

from src.core.database import Database
from src.core.telemetry import TelemetryClient
from src.llm.ollama_integration import OllamaClient
from src.api_reference.api_reference_service import ApiReferenceService

# Relative imports within validation package
from ..workspace.workspace_manager import WorkspaceManager
from ..analysis.code_pattern_detector import CodePatternDetector, CodePattern


@dataclass
class FixResult:
    """Result of persistent fix attempt."""
    success: bool
    final_code: str
    iterations_used: int
    models_tried: List[str]
    final_model: Optional[str]
    compilation_errors: List[str]
    stopped_reason: str  # 'success', 'max_iterations', 'infinite_loop', 'no_models', 'timeout'
    context_inferred: bool
    version_id: Optional[int]


class PersistentFixService:
    """
    Service for persistent code fixing with iterative LLM correction.

    Features:
    - Up to 10 iterations to fix code
    - Model fallback after 3 consecutive failures
    - Context inference for partial snippets
    - Infinite loop detection
    - Immediate patching callback on success
    """

    def __init__(
        self,
        workspace: WorkspaceManager,
        ollama: OllamaClient,
        db: Database,
        telemetry: TelemetryClient,
        family_config: Dict,
        api_reference: Optional[ApiReferenceService] = None
    ):
        """
        Initialize persistent fix service.

        Args:
            workspace: WorkspaceManager for code compilation
            ollama: OllamaClient for LLM fixes
            db: Database instance
            telemetry: TelemetryClient for metrics
            family_config: Family configuration dict
            api_reference: Optional API reference service for context enrichment
        """
        self.workspace = workspace
        self.ollama = ollama
        self.db = db
        self.telemetry = telemetry
        self.family_config = family_config
        self.api_reference = api_reference
        self.pattern_detector = CodePatternDetector()

        # Configuration from family config (with defaults)
        persistent_config = family_config.get('persistent_fix', {})
        self.max_iterations = persistent_config.get('max_iterations', 10)
        self.iterations_per_model = persistent_config.get('iterations_per_model', 3)
        self.max_time_seconds = persistent_config.get('max_time_seconds', 300)
        self.enable_context_inference = persistent_config.get('enable_context_inference', True)

    def fix_with_persistence(
        self,
        snippet_id: int,
        current_code: str,
        run_id: int,
        on_success_callback=None
    ) -> FixResult:
        """
        Main entry point: Try up to max_iterations to fix code.

        Args:
            snippet_id: Snippet ID
            current_code: Starting code (could be original or pattern-fixed)
            run_id: Current run ID
            on_success_callback: Function to call when fix succeeds (for immediate patching)
                Signature: callback(snippet_id: int, verified_code: str, version_id: int)

        Returns:
            FixResult with status, final code, iterations used, models tried
        """
        # Create fix session
        session_id = str(uuid.uuid4())
        self.db.create_fix_session(
            session_id=session_id,
            snippet_id=snippet_id,
            run_id=run_id,
            total_iterations=0,
            models_tried='[]',
            context_inferred=False
        )

        # Get available models
        available_models = self.ollama.get_available_models()
        if not available_models:
            self.telemetry.increment_metric('persistent_fix_no_models')
            _record_duration()
            return FixResult(
                success=False,
                final_code=current_code,
                iterations_used=0,
                models_tried=[],
                final_model=None,
                compilation_errors=[],
                stopped_reason='no_models',
                context_inferred=False,
                version_id=None
            )

        # Initialize tracking variables
        current_model_index = 0
        current_model = available_models[0]
        iteration = 0
        consecutive_failures = 0
        error_history = []
        context_inferred = False
        last_code = current_code
        start_time = time.time()
        models_tried_set = {current_model}

        def _record_duration() -> None:
            duration_ms = int((time.time() - start_time) * 1000)
            try:
                self.telemetry.record_timing('persistent_fix_duration', duration_ms)
            except Exception:
                pass

        self.telemetry.increment_metric('persistent_fix_attempts')

        # Get original version for tracking
        original_version = self.db.get_latest_snippet_version(snippet_id, 'original')
        before_version_id = original_version.version_id if original_version else None

        # Main iteration loop
        while iteration < self.max_iterations:
            iteration += 1

            # Check timeout
            if time.time() - start_time > self.max_time_seconds:
                self.db.update_fix_session(
                    session_id,
                    total_iterations=iteration,
                    models_tried=str(list(models_tried_set)),
                    final_status='timeout'
                )
                self.telemetry.increment_metric('persistent_fix_timeouts')
                _record_duration()
                return FixResult(
                    success=False,
                    final_code=current_code,
                    iterations_used=iteration,
                    models_tried=list(models_tried_set),
                    final_model=current_model,
                    compilation_errors=error_history[-1].split('\n') if error_history else [],
                    stopped_reason='timeout',
                    context_inferred=context_inferred,
                    version_id=None
                )

            # STEP 1: Check if code needs context inference
            working_code = current_code
            if self.enable_context_inference and self._needs_context(current_code):
                inferred_context = self._infer_context(snippet_id, current_code)
                if inferred_context:
                    working_code = inferred_context
                    context_inferred = True
                    self.telemetry.increment_metric('context_inferences')
                    self.db.log_event(
                        run_id, 'context_inference', 'info',
                        f'Inferred context for snippet {snippet_id}'
                    )

            # STEP 2: Compile current code
            success, output, error_count = self.workspace.validate_code(working_code)

            # Record build attempt
            version_id = self.db.create_snippet_version(
                snippet_id, 'fixed', working_code, f'ollama-{current_model}',
                f'Iteration {iteration} with {current_model}'
            )

            self.db.create_build_attempt(
                snippet_id, version_id, run_id, success, output, error_count,
                model_used=current_model, fix_session_id=session_id
            )

            # STEP 3: Check if compilation succeeded
            if success:
                # SUCCESS PATH

                # If we used context, extract only the fixed snippet portion
                if context_inferred:
                    try:
                        final_code = self._extract_fixed_portion(working_code, current_code)
                    except Exception as e:
                        # Fallback to complete code if extraction fails
                        self.db.log_event(
                            run_id, 'extraction_failure', 'warning',
                            f'Could not extract fixed portion: {e}. Using complete code.'
                        )
                        final_code = working_code
                else:
                    final_code = working_code

                # Mark snippet as verified
                self.db.update_snippet(snippet_id, status='verified')

                # Create final "current" version
                final_version_id = self.db.create_snippet_version(
                    snippet_id, 'current', final_code, 'ollama',
                    f'Fixed after {iteration} iterations using {current_model}'
                )

                # Record successful fix
                self.db.create_fix(
                    snippet_id, 'ollama',
                    f'Persistent fix: {iteration} iterations, model={current_model}',
                    True, None, before_version_id, final_version_id,
                    model_used=current_model,
                    iteration_count=iteration,
                    context_inferred=context_inferred
                )

                # Update fix session
                self.db.update_fix_session(
                    session_id,
                    total_iterations=iteration,
                    models_tried=str(list(models_tried_set)),
                    final_status='success',
                    context_inferred=context_inferred,
                    final_version_id=final_version_id
                )

                # Invoke callback for immediate patching
                if on_success_callback:
                    try:
                        on_success_callback(snippet_id, final_code, final_version_id)
                    except Exception as e:
                        self.db.log_event(
                            run_id, 'immediate_patch_error', 'warning',
                            f'Callback failed for snippet {snippet_id}: {e}'
                        )

                # Return success result
                self.telemetry.increment_metric('persistent_fix_successes')
                _record_duration()

                return FixResult(
                    success=True,
                    final_code=final_code,
                    iterations_used=iteration,
                    models_tried=list(models_tried_set),
                    final_model=current_model,
                    compilation_errors=[],
                    stopped_reason='success',
                    context_inferred=context_inferred,
                    version_id=final_version_id
                )

            # STEP 4: Compilation failed - extract errors
            errors = self.workspace.extract_errors(output)
            error_text = '\n'.join(errors)
            error_history.append(error_text)

            # STEP 5: Check for infinite loop
            if self._detect_infinite_loop(error_history):
                # Log infinite loop detection details
                error_pattern = error_history[-1][:200] if error_history else "N/A"
                self.db.log_event(
                    run_id, 'infinite_loop_detected', 'warning',
                    f'Infinite loop detected for snippet {snippet_id} at iteration {iteration}. '
                    f'Last 7 error messages are identical. Error pattern: {error_pattern}...'
                )

                self.db.update_snippet(snippet_id, status='needs-fix')
                self.db.update_fix_session(
                    session_id,
                    total_iterations=iteration,
                    models_tried=str(list(models_tried_set)),
                    final_status='infinite_loop',
                    context_inferred=context_inferred
                )
                self.telemetry.increment_metric('infinite_loops_detected')
                _record_duration()

                return FixResult(
                    success=False,
                    final_code=working_code,
                    iterations_used=iteration,
                    models_tried=list(models_tried_set),
                    final_model=current_model,
                    compilation_errors=errors,
                    stopped_reason='infinite_loop',
                    context_inferred=context_inferred,
                    version_id=version_id
                )

            # STEP 6: Extract API context from errors (if available)
            api_context = None
            if self.api_reference:
                try:
                    api_context = self.api_reference.get_api_context_for_errors(
                        family=self.family_config['family'],
                        compilation_errors=error_text
                    )
                    self.telemetry.increment_metric('api_context_extracted')
                except Exception as e:
                    self.telemetry.log_event(
                        'api_context_error',
                        'warning',
                        f'Failed to extract API context: {e}',
                        details={'snippet_id': snippet_id, 'error': str(e)}
                    )

            # STEP 7: Ask LLM to fix with current model
            with self.telemetry.track_fix(snippet_id, 'persistent-ollama'):
                fixed_code = self.ollama.fix_code_with_model(
                    code=working_code,
                    errors=error_text,
                    family_config=self.family_config,
                    model=current_model,
                    attempt=iteration,
                    api_context=api_context
                )

            if not fixed_code or fixed_code == last_code:
                consecutive_failures += 1

                # STEP 7: Model fallback after iterations_per_model consecutive failures
                if consecutive_failures >= self.iterations_per_model:
                    current_model_index += 1

                    if current_model_index >= len(available_models):
                        # All models exhausted
                        self.db.update_snippet(snippet_id, status='needs-fix')
                        self.db.update_fix_session(
                            session_id,
                            total_iterations=iteration,
                            models_tried=str(list(models_tried_set)),
                            final_status='no_models',
                            context_inferred=context_inferred
                        )
                        self.telemetry.increment_metric('persistent_fix_no_models')
                        _record_duration()

                        return FixResult(
                            success=False,
                            final_code=working_code,
                            iterations_used=iteration,
                            models_tried=list(models_tried_set),
                            final_model=None,
                            compilation_errors=errors,
                            stopped_reason='no_models',
                            context_inferred=context_inferred,
                            version_id=version_id
                        )

                    # Switch to next model
                    current_model = available_models[current_model_index]
                    models_tried_set.add(current_model)
                    consecutive_failures = 0

                    self.db.log_event(
                        run_id, 'model_fallback', 'info',
                        f'Switched to model {current_model} after {self.iterations_per_model} failures'
                    )
                    self.telemetry.increment_metric('model_fallbacks')

                continue  # Skip to next iteration
            else:
                consecutive_failures = 0  # Reset on successful LLM response

            # STEP 8: Update current_code for next iteration
            last_code = working_code
            current_code = fixed_code

        # MAX ITERATIONS REACHED
        self.db.update_snippet(snippet_id, status='needs-fix')
        self.db.update_fix_session(
            session_id,
            total_iterations=self.max_iterations,
            models_tried=str(list(models_tried_set)),
            final_status='max_iterations',
            context_inferred=context_inferred
        )
        self.telemetry.increment_metric('persistent_fix_max_iterations')
        _record_duration()

        return FixResult(
            success=False,
            final_code=current_code,
            iterations_used=self.max_iterations,
            models_tried=list(models_tried_set),
            final_model=current_model,
            compilation_errors=error_history[-1].split('\n') if error_history else [],
            stopped_reason='max_iterations',
            context_inferred=context_inferred,
            version_id=version_id
        )

    def _needs_context(self, code: str) -> bool:
        """
        Detect if snippet is partial and needs context.

        Uses CodePatternDetector for intelligent pattern detection:
        - COMPLETE_PROGRAM: No context needed
        - TOP_LEVEL_STATEMENTS: No context needed (C# 9+ feature)
        - MINIMAL_API: No context needed (self-contained)
        - CLASS_ONLY: No context needed (complete class)
        - METHOD_ONLY: Needs context (method must be wrapped in class)
        - FRAGMENT: Needs context (incomplete code)

        Args:
            code: Code to analyze

        Returns:
            True if code needs context wrapping
        """
        pattern, confidence = self.pattern_detector.detect(code)

        # Log pattern detection for observability
        self.telemetry.increment_metric(f'pattern_detected_{pattern.value}')

        # Patterns that need context wrapping
        needs_wrapping = pattern in [
            CodePattern.METHOD_ONLY,
            CodePattern.FRAGMENT
        ]

        return needs_wrapping

    def _infer_context(self, snippet_id: int, partial_code: str) -> Optional[str]:
        """
        Infer surrounding context for partial snippets.

        Strategy:
        1. Query database for other snippets on same page
        2. Look for using statements, class declarations in nearby snippets (±2 ordinal positions)
        3. Merge context + partial snippet
        4. Return complete compilable code

        Args:
            snippet_id: Current snippet ID
            partial_code: Partial code that needs context

        Returns:
            Complete code with context, or None if no context found
        """
        snippet = self.db.get_snippet(snippet_id)
        if not snippet:
            return None

        page_snippets = self.db.get_snippets_by_page(snippet.page_id)

        # Find nearby snippets (within ±2 positions)
        nearby = [
            s for s in page_snippets
            if abs(s.snippet_ordinal - snippet.snippet_ordinal) <= 2
            and s.snippet_id != snippet_id
        ]

        # Collect using statements
        using_statements = set()
        namespace_found = None
        class_found = None

        for nearby_snippet in nearby:
            # Get original code
            version = self.db.get_latest_snippet_version(nearby_snippet.snippet_id, 'original')
            if not version:
                continue

            code = version.code_content

            # Extract using statements
            for match in re.finditer(r'using\s+[\w\.]+;', code):
                using_statements.add(match.group(0))

            # Extract namespace (take first found)
            if not namespace_found:
                ns_match = re.search(r'namespace\s+([\w\.]+)', code)
                if ns_match:
                    namespace_found = ns_match.group(1)

            # Extract class declaration (take first found)
            if not class_found:
                class_match = re.search(r'(class|struct)\s+(\w+)', code)
                if class_match:
                    class_found = (class_match.group(1), class_match.group(2))

        # Build context-enriched code
        if not using_statements and not namespace_found and not class_found:
            return None  # No context found

        # Assemble complete code
        lines = []

        # Add using statements
        for using in sorted(using_statements):
            lines.append(using)

        if lines:
            lines.append('')

        # Add namespace wrapper
        if namespace_found:
            lines.append(f'namespace {namespace_found}')
            lines.append('{')

        # Add class wrapper
        if class_found:
            class_type, class_name = class_found
            indent = '    ' if namespace_found else ''
            lines.append(f'{indent}{class_type} {class_name}')
            lines.append(f'{indent}{{')

        # Add partial code (indented)
        base_indent = '        ' if (namespace_found and class_found) else ('    ' if class_found else '')
        for line in partial_code.split('\n'):
            lines.append(base_indent + line)

        # Close wrappers
        if class_found:
            indent = '    ' if namespace_found else ''
            lines.append(f'{indent}}}')

        if namespace_found:
            lines.append('}')

        return '\n'.join(lines)

    def _extract_fixed_portion(self, complete_code: str, original_partial: str) -> str:
        """
        After successful compilation with context, extract only the fixed snippet.

        Strategy:
        1. Use regex to find the innermost code block (class body content)
        2. Remove wrapper indentation
        3. Return extracted section

        Args:
            complete_code: Complete code with context wrappers
            original_partial: Original partial code for reference

        Returns:
            Extracted fixed portion without wrappers

        Raises:
            ValueError: If extraction fails
        """
        # Find class body content (between innermost { })
        # Look for pattern: class Name { ... content ... }
        class_match = re.search(
            r'(class|struct)\s+\w+\s*\{(.*)\}',
            complete_code,
            re.DOTALL
        )

        if not class_match:
            # Fallback: return complete code if can't extract
            raise ValueError("Could not find class body in complete code")

        class_body = class_match.group(2).strip()

        # Remove extra indentation
        lines = class_body.split('\n')

        # Find minimum indentation
        min_indent = min(
            (len(line) - len(line.lstrip()) for line in lines if line.strip()),
            default=0
        )

        # Remove that indent from all lines
        extracted = '\n'.join(
            line[min_indent:] if len(line) >= min_indent else line
            for line in lines
        )

        return extracted.strip()

    def _detect_infinite_loop(self, error_history: List[str]) -> bool:
        """
        Detect if LLM is producing the same errors repeatedly.

        Strategy:
        - Hash last 7 error messages
        - If all identical, infinite loop detected

        Args:
            error_history: List of error strings from each iteration

        Returns:
            True if infinite loop detected
        """
        if len(error_history) < 7:
            return False

        # Hash last 7 error messages
        last_7 = error_history[-7:]
        error_hashes = [hashlib.md5(e.encode()).hexdigest() for e in last_7]

        # If all identical, infinite loop detected
        return len(set(error_hashes)) == 1
