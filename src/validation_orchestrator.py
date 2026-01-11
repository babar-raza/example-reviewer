"""
Validation Orchestrator for Example Review System.
Coordinates the 5-stage validation pipeline.
"""

from typing import Dict, Optional, Tuple, List
from pathlib import Path

from database import Database, Snippet
from telemetry import TelemetryClient
from pattern_registry import PatternRegistry
from workspace_manager import WorkspaceManager
from ollama_integration import OllamaClient


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

            with self.telemetry.track_compilation(snippet_id, original_version.version_id, 1):
                success, output, error_count = self.workspace.validate_code(original_code)

                self.db.create_build_attempt(
                    snippet_id, original_version.version_id, run_id,
                    success, output, error_count
                )

                if success:
                    # Original code compiles!
                    result['status'] = 'verified'
                    result['message'] = 'Original code compiles successfully'
                    self.db.update_snippet(snippet_id, status='verified')
                    self.telemetry.increment_metric('snippets_verified')
                    return result

            # Stage 3: Compile with pattern fixes
            if fixed_code != original_code:
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
                            result['status'] = 'verified'
                            result['message'] = 'Pattern fixes resolved compilation errors'
                            result['final_code'] = fixed_code
                            self.db.update_snippet(snippet_id, status='verified')
                            self.telemetry.increment_metric('snippets_verified')
                            return result

                        # Save errors for Ollama
                        result['compilation_errors'] = self.workspace.extract_errors(output)

            # Stage 4: Ollama auto-fix (if enabled and available)
            if use_ollama and self.ollama and self.ollama.is_available():
                result['stages_completed'].append('ollama_fixes')

                current_code = fixed_code if fixed_code != original_code else original_code
                current_version = self.db.get_latest_snippet_version(snippet_id, 'fixed') or original_version

                for attempt in range(1, 4):  # 3 attempts
                    # Get current errors
                    success, output, error_count = self.workspace.validate_code(current_code)

                    if success:
                        break  # Shouldn't happen, but just in case

                    errors = self.workspace.extract_errors(output)
                    if not errors:
                        break

                    # Ask Ollama to fix
                    with self.telemetry.track_fix(snippet_id, 'ollama'):
                        ollama_fixed = self.ollama.fix_code(
                            current_code,
                            '\n'.join(errors),
                            self.family_config,
                            attempt
                        )

                        if not ollama_fixed or ollama_fixed == current_code:
                            # Ollama couldn't fix or returned same code
                            continue

                        # Save Ollama version
                        ollama_version_id = self.db.create_snippet_version(
                            snippet_id, 'fixed', ollama_fixed, 'ollama',
                            f"Ollama fix attempt {attempt}"
                        )

                        # Try compiling
                        result['build_attempts'] += 1

                        with self.telemetry.track_compilation(snippet_id, ollama_version_id, attempt + 2):
                            success, output, error_count = self.workspace.validate_code(ollama_fixed)

                            self.db.create_build_attempt(
                                snippet_id, ollama_version_id, run_id,
                                success, output, error_count
                            )

                            if success:
                                # Ollama fixed it!
                                result['status'] = 'verified'
                                result['message'] = f'Ollama fixed on attempt {attempt}'
                                result['final_code'] = ollama_fixed
                                result['fixes_applied'] += 1

                                self.db.create_fix(
                                    snippet_id, 'ollama',
                                    f"Ollama fix attempt {attempt}",
                                    True, None, current_version.version_id, ollama_version_id
                                )

                                self.db.update_snippet(snippet_id, status='verified')
                                self.telemetry.increment_metric('snippets_verified')
                                return result

                            # Update current code for next attempt
                            current_code = ollama_fixed
                            current_version = self.db.get_snippet_version(ollama_version_id)

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
