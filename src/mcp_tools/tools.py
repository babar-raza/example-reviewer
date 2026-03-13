"""
MCP Tools for Example Reviewer Pipeline.
Exposes pipeline functionality as MCP-compatible tools.
"""

import json
import logging
import re
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class ToolResult:
    """Standard result structure for MCP tools."""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


class ExampleReviewerTools:
    """
    MCP-compatible tools for the Example Reviewer Pipeline.
    
    Each tool follows the MCP tool pattern:
    - Takes structured input
    - Returns structured output
    - Is independently executable
    """
    
    def __init__(
        self,
        config_dir: Optional[Path] = None,
        db_path: Optional[Path] = None,
        prod_db_path: Optional[Path] = None,
        workspace_dir: Optional[Path] = None,
        cli_overrides: Optional[Dict[str, Any]] = None,
        use_workspace_copy: bool = False,
        sqlite_config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize MCP tools.

        Args:
            config_dir: Directory containing family configs
            db_path: Path to database
            prod_db_path: Path to production database (optional, enables dual-database mode)
            workspace_dir: Working directory
            cli_overrides: CLI override dictionary for config hash computation
            use_workspace_copy: Enable workspace copy mode (for tests/fixtures/content/ writes)
            sqlite_config: SQLite configuration (busy_timeout_ms, wal_enabled)
        """
        self.config_dir = config_dir or Path("config/families")
        self.db_path = db_path or Path("data/example_reviewer.db")
        self.prod_db_path = prod_db_path  # None by default
        self.workspace_dir = workspace_dir or Path("workspace")
        self.cli_overrides = cli_overrides or {}
        self.use_workspace_copy = use_workspace_copy
        self.sqlite_config = sqlite_config or {}

        # Lazy initialization of orchestrator
        self._orchestrator = None

    @property
    def orchestrator(self):
        """Get or create pipeline orchestrator."""
        if self._orchestrator is None:
            from ..pipeline.orchestrator import PipelineOrchestrator
            self._orchestrator = PipelineOrchestrator(
                config_dir=self.config_dir,
                db_path=self.db_path,
                prod_db_path=self.prod_db_path,
                workspace_dir=self.workspace_dir,
                cli_overrides=self.cli_overrides,
                use_workspace_copy=self.use_workspace_copy,
                sqlite_config=self.sqlite_config,
            )
        return self._orchestrator
    
    # =========================================================================
    # SCAN TOOL (CLI command: scan)
    # =========================================================================
    
    def scan(
        self,
        family: Optional[str] = None,
        directory: Optional[str] = None,
        max_files: Optional[int] = None,
        content_roots: Optional[List[str]] = None,
    ) -> ToolResult:
        """
        Scan for markdown files containing code examples.

        Maps to CLI command: scan
        Maps to phase: A_discovery_extraction (partial)

        Args:
            family: Family identifier (required if directory not provided)
            directory: Directory path to scan (required if family not provided)
            max_files: Maximum files to scan
            content_roots: Override content_roots from family config. Paths to
                directories containing markdown files. Ignored when directory is set.

        Returns:
            ToolResult with file list
        """
        try:
            if directory:
                dir_path = Path(directory)
                if not dir_path.exists():
                    return ToolResult(success=False, error=f"Directory not found: {directory}")

                # Sort glob results deterministically (case-normalized for Windows compatibility)
                files = sorted(dir_path.rglob("*.md"), key=lambda p: str(p).lower())
                if max_files:
                    files = files[:max_files]

                return ToolResult(
                    success=True,
                    data={
                        'mode': 'directory',
                        'directory': directory,
                        'file_count': len(files),
                        'files': [str(f) for f in files],
                    }
                )

            elif family:
                family_config = self.orchestrator.config_manager.load_family_config(family)
                if content_roots:
                    family_config = family_config.model_copy(update={"content_roots": content_roots})

                from ..services.discovery_service import DiscoveryService
                discovery = DiscoveryService(self.orchestrator.db)
                files = discovery._find_markdown_files(family_config)

                if max_files:
                    files = files[:max_files]

                return ToolResult(
                    success=True,
                    data={
                        'mode': 'family',
                        'family': family,
                        'file_count': len(files),
                        'files': files,
                    }
                )

            else:
                return ToolResult(
                    success=False,
                    error="Either 'family' or 'directory' must be provided"
                )

        except Exception as e:
            return ToolResult(success=False, error=str(e))
    
    # =========================================================================
    # EXTRACT TOOL (CLI command: extract)
    # =========================================================================
    
    def extract(
        self,
        family: str,
        max_files: Optional[int] = None,
        content_roots: Optional[List[str]] = None,
    ) -> ToolResult:
        """
        Extract code examples from markdown files.

        Maps to CLI command: extract
        Maps to phase: A_discovery_extraction

        Args:
            family: Family identifier
            max_files: Maximum files to process
            content_roots: Override content_roots from family config. Paths to
                directories containing markdown files.

        Returns:
            ToolResult with extraction statistics
        """
        try:
            family_config = self.orchestrator.config_manager.load_family_config(family)
            if content_roots:
                family_config = family_config.model_copy(update={"content_roots": content_roots})

            stats = self.orchestrator.discovery_service.discover_family(
                family, family_config,
                max_files=max_files,
                max_examples=None  # MCP scan/extract don't use example limits
            )
            
            return ToolResult(
                success=True,
                data={
                    'family': family,
                    'files_found': stats['files_found'],
                    'files_processed': stats['files_processed'],
                    'examples_found': stats['examples_found'],
                    'inline_examples': stats['inline_examples'],
                    'gist_examples': stats['gist_examples'],
                    'errors': stats['errors'],
                }
            )
            
        except Exception as e:
            return ToolResult(success=False, error=str(e))
    
    # =========================================================================
    # COMPILE_VERIFY TOOL (CLI command: compile_verify)
    # =========================================================================
    
    def compile_verify(
        self,
        family: str,
        max_examples: Optional[int] = None,
    ) -> ToolResult:
        """
        Compile and verify code examples.
        
        Maps to CLI command: compile_verify
        Maps to phase: B_compile_verify_fix_loop (without LLM fixes)
        
        Args:
            family: Family identifier
            max_examples: Maximum examples to verify
            
        Returns:
            ToolResult with compilation statistics
        """
        try:
            family_config = self.orchestrator.config_manager.load_family_config(family)
            run_id = self.orchestrator.db.get_latest_run_id(family) or self.orchestrator.db.create_run(family, "compile_verify")

            stats = self.orchestrator._run_compilation_phase(
                run_id, family, family_config, max_examples, skip_llm_fixes=True
            )

            return ToolResult(success=True, data=stats)

        except Exception as e:
            return ToolResult(success=False, error=str(e))

    # =========================================================================
    # COMPILE_FIX TOOL (CLI command: compile_fix)
    # =========================================================================

    def compile_fix(
        self,
        family: str,
        max_examples: Optional[int] = None,
    ) -> ToolResult:
        """
        Fix compilation errors using LLM.

        Maps to CLI command: compile_fix
        Maps to phase: B_compile_verify_fix_loop (with LLM fixes)

        Args:
            family: Family identifier
            max_examples: Maximum examples to fix

        Returns:
            ToolResult with fix statistics
        """
        try:
            family_config = self.orchestrator.config_manager.load_family_config(family)
            run_id = self.orchestrator.db.get_latest_run_id(family) or self.orchestrator.db.create_run(family, "compile_fix")

            stats = self.orchestrator._run_compilation_phase(
                run_id, family, family_config, max_examples, skip_llm_fixes=False
            )

            return ToolResult(success=True, data=stats)

        except Exception as e:
            return ToolResult(success=False, error=str(e))

    # =========================================================================
    # RUNTIME_VERIFY TOOL (CLI command: runtime_verify)
    # =========================================================================

    def runtime_verify(
        self,
        family: str,
        max_examples: Optional[int] = None,
    ) -> ToolResult:
        """
        Execute examples and verify runtime behavior.

        Maps to CLI command: runtime_verify
        Maps to phase: C_runtime_verify_fix_loop (without LLM fixes)

        Args:
            family: Family identifier
            max_examples: Maximum examples to verify

        Returns:
            ToolResult with runtime statistics
        """
        try:
            family_config = self.orchestrator.config_manager.load_family_config(family)
            run_id = self.orchestrator.db.get_latest_run_id(family) or self.orchestrator.db.create_run(family, "runtime_verify")

            stats = self.orchestrator._run_runtime_phase(
                run_id, family, family_config, max_examples, skip_llm_fixes=True
            )

            return ToolResult(success=True, data=stats)

        except Exception as e:
            return ToolResult(success=False, error=str(e))

    # =========================================================================
    # RUNTIME_FIX TOOL (CLI command: runtime_fix)
    # =========================================================================

    def runtime_fix(
        self,
        family: str,
        max_examples: Optional[int] = None,
    ) -> ToolResult:
        """
        Fix runtime errors using LLM.

        Maps to CLI command: runtime_fix
        Maps to phase: C_runtime_verify_fix_loop (with LLM fixes)

        Args:
            family: Family identifier
            max_examples: Maximum examples to fix

        Returns:
            ToolResult with fix statistics
        """
        try:
            family_config = self.orchestrator.config_manager.load_family_config(family)
            run_id = self.orchestrator.db.get_latest_run_id(family) or self.orchestrator.db.create_run(family, "runtime_fix")

            stats = self.orchestrator._run_runtime_phase(
                run_id, family, family_config, max_examples, skip_llm_fixes=False
            )

            return ToolResult(success=True, data=stats)

        except Exception as e:
            return ToolResult(success=False, error=str(e))

    # =========================================================================
    # MD_UPDATE TOOL (CLI command: md_update)
    # =========================================================================
    
    def md_update(
        self,
        family: str,
        dry_run: bool = False,
        allow_md_write: bool = False,
        audit_prose: bool = False,
    ) -> ToolResult:
        """
        Update markdown files with verified code.

        Maps to CLI command: md_update
        Maps to phase: D_markdown_update

        Args:
            family: Family identifier
            dry_run: If True, don't write changes
            allow_md_write: If True, override global config to allow markdown writes

        Returns:
            ToolResult with update statistics
        """
        try:
            # Use the latest completed run to access verified examples
            # (Don't create a new run - we need the run that has the verified examples)
            import sqlite3
            with self.orchestrator.db.get_connection() as conn:
                row = conn.execute("""
                    SELECT run_id FROM run_records
                    WHERE family = ? AND status = 'completed'
                    ORDER BY started_at DESC
                    LIMIT 1
                """, (family,)).fetchone()

            if not row:
                return ToolResult(success=False, error=f"No completed runs found for family {family}")

            run_id = row[0]

            stats = self.orchestrator._run_markdown_update_phase(
                run_id, family, dry_run, allow_md_write=allow_md_write, audit_prose=audit_prose
            )
            return ToolResult(success=True, data=stats)

        except Exception as e:
            return ToolResult(success=False, error=str(e))
    
    # =========================================================================
    # FINAL_REVIEW TOOL (CLI command: final_review)
    # =========================================================================
    
    def final_review(
        self,
        family: str,
    ) -> ToolResult:
        """
        Run final LLM review of updated markdown.
        
        Maps to CLI command: final_review
        Maps to phase: E_final_llm_review
        
        Args:
            family: Family identifier
            
        Returns:
            ToolResult with review statistics
        """
        try:
            # Use the latest completed run
            with self.orchestrator.db.get_connection() as conn:
                row = conn.execute("""
                    SELECT run_id FROM run_records
                    WHERE family = ? AND status = 'completed'
                    ORDER BY started_at DESC
                    LIMIT 1
                """, (family,)).fetchone()

            if not row:
                return ToolResult(success=False, error=f"No completed runs found for family {family}")

            run_id = row[0]
            stats = self.orchestrator._run_final_review_phase(run_id, family)
            return ToolResult(success=True, data=stats)
            
        except Exception as e:
            return ToolResult(success=False, error=str(e))
    
    # =========================================================================
    # COMMIT TOOL (CLI command: commit)
    # =========================================================================
    
    def commit(
        self,
        family: str,
    ) -> ToolResult:
        """
        Commit changes to git.
        
        Maps to CLI command: commit
        Maps to phase: F_persist_telemetry_commit
        
        Args:
            family: Family identifier
            
        Returns:
            ToolResult with commit information
        """
        try:
            # Use the latest completed run
            with self.orchestrator.db.get_connection() as conn:
                row = conn.execute("""
                    SELECT run_id FROM run_records
                    WHERE family = ? AND status = 'completed'
                    ORDER BY started_at DESC
                    LIMIT 1
                """, (family,)).fetchone()

            if not row:
                return ToolResult(success=False, error=f"No completed runs found for family {family}")

            run_id = row[0]
            stats = self.orchestrator._run_finalization_phase(family, run_id, dry_run=False, allow_commit=True)
            return ToolResult(success=True, data=stats)
            
        except Exception as e:
            return ToolResult(success=False, error=str(e))
    
    # =========================================================================
    # BACKFILL TOOL (CLI command: backfill)
    # =========================================================================
    
    def backfill(
        self,
        family: str,
        targets: Optional[List[str]] = None,
        force: bool = False,
    ) -> ToolResult:
        """
        Backfill missing context (API refs, test data, examples).

        Maps to CLI command: backfill

        Args:
            family: Family identifier
            targets: What to backfill (api_reference, test_data, examples)
            force: Force re-download even if data exists

        Returns:
            ToolResult with backfill statistics
        """
        try:
            from ..services.backfill_service import BackfillService

            # Create backfill service
            global_config = self.orchestrator.config_manager.load_global_config()
            backfill_service = BackfillService(
                config_manager=self.orchestrator.config_manager,
                timeout_seconds=global_config.backfill.github_timeout_seconds
            )

            # Determine targets
            if targets is None:
                targets = global_config.backfill.targets

            results = {}

            # Execute backfill for each target
            for target in targets:
                if target == "test_data":
                    result = backfill_service.backfill_test_data(family=family, force=force)
                    results['test_data'] = {
                        'success': result.success,
                        'files_copied': result.files_copied,
                        'skipped': result.skipped,
                        'skip_reason': result.skip_reason,
                        'error': result.error,
                        'duration_seconds': result.duration_seconds
                    }

                elif target == "api_reference":
                    result = backfill_service.backfill_api_reference(family=family, force=force)
                    results['api_reference'] = {
                        'success': result.success,
                        'files_copied': result.files_copied,
                        'skipped': result.skipped,
                        'skip_reason': result.skip_reason,
                        'error': result.error,
                        'duration_seconds': result.duration_seconds
                    }

                elif target == "api_catalog":
                    result = backfill_service.backfill_api_catalog(family=family, force=force)
                    results['api_catalog'] = {
                        'success': result.success,
                        'files_copied': result.files_copied,
                        'source': result.source,
                        'destination': result.destination,
                        'skipped': result.skipped,
                        'skip_reason': result.skip_reason,
                        'error': result.error,
                        'duration_seconds': result.duration_seconds
                    }

                elif target == "examples":
                    # Get vector service if available
                    vector_service = self.orchestrator.vector_db_service
                    result = backfill_service.backfill_examples_to_vector_db(
                        family=family,
                        vector_service=vector_service,
                        force=force
                    )
                    results['examples'] = {
                        'success': result.success,
                        'files_copied': result.files_copied,
                        'skipped': result.skipped,
                        'skip_reason': result.skip_reason,
                        'error': result.error,
                        'duration_seconds': result.duration_seconds
                    }

                elif target == "examples_files":
                    result = backfill_service.backfill_examples_files(
                        family=family,
                        force=force
                    )
                    results['examples_files'] = {
                        'success': result.success,
                        'files_copied': result.files_copied,
                        'skipped': result.skipped,
                        'skip_reason': result.skip_reason,
                        'error': result.error,
                        'duration_seconds': result.duration_seconds
                    }

                elif target == "gist_source_code":
                    result = backfill_service.backfill_gist_source_code(
                        family=family,
                        force=force
                    )
                    results['gist_source_code'] = {
                        'success': result.success,
                        'items_processed': result.items_processed,
                        'items_downloaded': result.items_downloaded,
                        'items_failed': result.items_failed,
                        'skipped': result.skipped,
                        'skip_reason': result.skip_reason,
                        'error': result.error,
                        'duration_seconds': result.duration_seconds
                    }

                else:
                    results[target] = {
                        'success': False,
                        'error': f'Unknown backfill target: {target}'
                    }

            # Determine overall success
            overall_success = all(r.get('success', False) or r.get('skipped', False) for r in results.values())

            return ToolResult(
                success=overall_success,
                data={
                    'family': family,
                    'results': results,
                }
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))
    
    # =========================================================================
    # STATUS TOOL (utility)
    # =========================================================================
    
    def status(
        self,
        family: Optional[str] = None,
    ) -> ToolResult:
        """
        Get pipeline status.
        
        Args:
            family: Family identifier (optional, returns all if not specified)
            
        Returns:
            ToolResult with status information
        """
        try:
            stats = self.orchestrator.get_status(family)
            return ToolResult(success=True, data=stats)
            
        except Exception as e:
            return ToolResult(success=False, error=str(e))
    
    # =========================================================================
    # RUN_PIPELINE TOOL (full pipeline)
    # =========================================================================
    
    def run_pipeline(
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
        content_roots: Optional[List[str]] = None,
        file_list: Optional[List[str]] = None,
        audit_prose: bool = False,
    ) -> ToolResult:
        """
        Run the full pipeline for a family.

        Args:
            family: Family identifier
            max_examples: Maximum examples to process
            skip_runtime: Skip runtime verification
            skip_llm_fixes: Skip LLM-based fixing
            skip_llm_runtime_fixes: Skip LLM fixes for runtime errors only
            dry_run: Don't write changes
            allow_md_write: Override global config to allow markdown writes
            allow_commit: Override global config to allow git commit
            strategy_config: Dict controlling which fix strategies to enable
            content_roots: Override content_roots from family config. Paths to
                directories containing markdown files with code examples.
            file_list: Run on specific .md files (absolute paths). When provided,
                bypasses content_roots discovery entirely.

        Returns:
            ToolResult with full pipeline results
        """
        try:
            results = self.orchestrator.run_full_pipeline(
                family,
                max_examples=max_examples,
                skip_runtime=skip_runtime,
                skip_llm_fixes=skip_llm_fixes,
                skip_llm_runtime_fixes=skip_llm_runtime_fixes,
                dry_run=dry_run,
                allow_md_write=allow_md_write,
                allow_commit=allow_commit,
                strategy_config=strategy_config,
                content_roots=content_roots,
                file_list=file_list,
                audit_prose=audit_prose,
            )

            return ToolResult(success=results['success'], data=results)

        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def validate_articles(
        self,
        family: str,
        file_list: Optional[List[str]] = None,
        content_roots: Optional[List[str]] = None,
        audit_prose: bool = False,
    ) -> ToolResult:
        """Run deterministic article validation outside the full pipeline."""
        try:
            family_config = self.orchestrator.config_manager.load_family_config(family)
            if content_roots:
                family_config = family_config.model_copy(update={"content_roots": content_roots})

            target_files = [str(Path(path).resolve()) for path in (file_list or [])]
            if not target_files:
                target_files = self.orchestrator.discovery_service._find_markdown_files(family_config)

            llm_service = None
            if audit_prose:
                llm_service = self.orchestrator.llm_service if self.orchestrator.llm_service.is_available() else None

            result = self.orchestrator.article_validator.validate_files(
                target_files,
                audit_prose=audit_prose,
                llm_service=llm_service,
            )
            return ToolResult(
                success=True,
                data={
                    "family": family,
                    "audit_prose": audit_prose,
                    **result,
                },
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    # =========================================================================
    # VALIDATE_CODE_SNIPPET TOOL (lightweight catalog validation)
    # =========================================================================

    # Per-family catalog cache (avoids reloading JSON on every call)
    _catalog_cache: Dict[str, Any] = {}

    def validate_code_snippet(
        self,
        code: str,
        family: str,
        language: str = "csharp",
        compile_verify: bool = False,
    ) -> ToolResult:
        """
        Validate a code snippet against the family's API catalog.

        Checks for hallucinated Aspose types/methods and namespace violations.
        This is the primary tool for external agents (e.g. seo-intelligence)
        to verify LLM-generated code uses real Aspose APIs.

        Args:
            code: The code snippet to validate
            family: Product family identifier (e.g. 'words', 'zip', 'cells')
            language: Programming language (default: 'csharp'). Non-C# returns valid.
            compile_verify: If True, also compile the code (requires .NET SDK)

        Returns:
            ToolResult with validation details
        """
        try:
            # Non-C# code: no catalog to check, return early
            if language.lower() != "csharp":
                return ToolResult(
                    success=True,
                    data={
                        "valid": True,
                        "hallucinated_types": [],
                        "namespace_violations": [],
                        "catalog_matches": {},
                        "catalog_info": {"family": family, "note": f"No catalog for language '{language}'"},
                        "compilation_result": None,
                    },
                )

            # Load catalog (cached per family)
            from ..services.api_catalog_service import APICatalogService

            if family not in self._catalog_cache:
                catalog_path = self.config_dir / f"{family}_api_catalog.json"
                if catalog_path.exists():
                    self._catalog_cache[family] = APICatalogService(family, str(catalog_path))
                else:
                    self._catalog_cache[family] = APICatalogService(family)

            catalog = self._catalog_cache[family]
            if not catalog.is_loaded:
                return ToolResult(
                    success=False,
                    error=f"No API catalog found for family '{family}'"
                )

            # Extract Aspose type references from code
            # Matches: new TypeName, TypeName.Method, TypeName variable declarations
            type_pattern = re.compile(
                r'(?:new\s+|:\s*|(?:^|[\s(,<]))'
                r'((?:Aspose\.\w+\.)*(\w+))'
                r'(?:\s*[(<.\[\s;])',
                re.MULTILINE,
            )
            # Also extract types from using directives to cross-check
            using_pattern = re.compile(r'using\s+([\w.]+)\s*;')

            # Collect all referenced type names (simple names after the last dot)
            referenced_types = set()
            for match in type_pattern.finditer(code):
                full_ref = match.group(1)
                simple_name = match.group(2)
                # Only check types that could be Aspose types (capitalized, not keywords)
                if simple_name[0].isupper() and simple_name not in _CSHARP_BUILTIN_TYPES:
                    referenced_types.add(simple_name)

            # Also extract types from 'new X(' pattern more directly
            for match in re.finditer(r'\bnew\s+(\w+)\s*(?:\(|<|\[)', code):
                type_name = match.group(1)
                if type_name[0].isupper() and type_name not in _CSHARP_BUILTIN_TYPES:
                    referenced_types.add(type_name)

            # Validate each type against catalog
            hallucinated_types = []
            catalog_matches = {}

            for type_name in sorted(referenced_types):
                if catalog.has_type(type_name):
                    ns = catalog.get_namespace_for_type(type_name)
                    catalog_matches[type_name] = f"{ns}.{type_name}" if ns else type_name
                elif catalog.find_type_case_insensitive(type_name):
                    # Case mismatch — still valid, note the correct casing
                    correct = catalog.find_type_case_insensitive(type_name)
                    ns = catalog.get_namespace_for_type(correct)
                    catalog_matches[type_name] = f"{ns}.{correct} (case mismatch)" if ns else correct
                else:
                    # Not in catalog — could be BCL type or hallucinated
                    # Only flag as hallucinated if the code also has Aspose usings
                    # (i.e., context suggests this should be an Aspose type)
                    if not _is_known_bcl_type(type_name):
                        hallucinated_types.append(type_name)

            # Namespace validation using NamespaceValidator
            from ..namespace_validator import NamespaceValidator

            policy = {
                "mode": "whitelist",
                "allowed_namespaces": list(_SAFE_BCL_NAMESPACES),
            }
            validator = NamespaceValidator(policy, catalog=catalog)
            ns_valid, namespace_violations = validator.validate(code)

            # Overall validity
            is_valid = len(hallucinated_types) == 0 and ns_valid

            # Optional compilation
            compilation_result = None
            if compile_verify:
                try:
                    compile_result = self.orchestrator.compilation_service.compile_code(
                        code, family
                    )
                    compilation_result = {
                        "success": compile_result.get("success", False),
                        "errors": compile_result.get("errors", []),
                    }
                    if not compilation_result["success"]:
                        is_valid = False
                except Exception as ce:
                    compilation_result = {"success": False, "errors": [str(ce)]}

            return ToolResult(
                success=True,
                data={
                    "valid": is_valid,
                    "hallucinated_types": hallucinated_types,
                    "namespace_violations": namespace_violations,
                    "catalog_matches": catalog_matches,
                    "catalog_info": {
                        "family": family,
                        "total_types": len(catalog.get_all_types()),
                        "total_namespaces": len(catalog.get_all_namespaces()),
                        "has_enrichment": catalog.has_enrichment(),
                    },
                    "compilation_result": compilation_result,
                },
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))


# Standard .NET BCL namespaces that are always allowed
_SAFE_BCL_NAMESPACES = frozenset([
    "System", "System.*",
    "System.IO", "System.IO.*",
    "System.Text", "System.Text.*",
    "System.Linq", "System.Linq.*",
    "System.Collections", "System.Collections.*",
    "System.Collections.Generic", "System.Collections.Generic.*",
    "System.Threading", "System.Threading.*",
    "System.Threading.Tasks", "System.Threading.Tasks.*",
    "System.Drawing", "System.Drawing.*",
    "System.Net", "System.Net.*",
    "System.Net.Http", "System.Net.Http.*",
    "System.Globalization",
    "System.Runtime", "System.Runtime.*",
    "Microsoft.Extensions", "Microsoft.Extensions.*",
])

# C# built-in type names to skip during type extraction
_CSHARP_BUILTIN_TYPES = frozenset([
    "String", "Int32", "Int64", "Boolean", "Double", "Float", "Decimal",
    "Byte", "Char", "Object", "Void", "Console", "Math", "Convert",
    "Array", "List", "Dictionary", "Task", "Action", "Func",
    "Exception", "File", "Path", "Directory", "Stream", "MemoryStream",
    "FileStream", "StreamReader", "StreamWriter", "StringBuilder",
    "Encoding", "Environment", "Guid", "DateTime", "TimeSpan",
    "Uri", "Type", "Activator", "Attribute", "Enum", "Tuple",
    "KeyValuePair", "Nullable", "IDisposable", "IEnumerable",
    "Program", "Main",
])


def _is_known_bcl_type(type_name: str) -> bool:
    """Check if a type is a well-known .NET BCL type (not Aspose-specific)."""
    return type_name in _CSHARP_BUILTIN_TYPES


# Tool definitions for MCP server registration
TOOL_DEFINITIONS = [
    {
        "name": "scan",
        "description": "Scan for markdown files containing code examples",
        "inputSchema": {
            "type": "object",
            "properties": {
                "family": {"type": "string", "description": "Product family identifier"},
                "directory": {"type": "string", "description": "Directory path to scan"},
                "max_files": {"type": "integer", "description": "Maximum files to scan"},
                "content_roots": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Override content_roots from the family config. Paths to directories containing markdown files. Ignored when directory is set.",
                },
            },
        },
    },
    {
        "name": "extract",
        "description": "Extract code examples from markdown files",
        "inputSchema": {
            "type": "object",
            "properties": {
                "family": {"type": "string", "description": "Product family identifier"},
                "max_files": {"type": "integer", "description": "Maximum files to process"},
                "content_roots": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Override content_roots from the family config. Paths to directories containing markdown files.",
                },
            },
            "required": ["family"],
        },
    },
    {
        "name": "compile_verify",
        "description": "Compile and verify code examples",
        "inputSchema": {
            "type": "object",
            "properties": {
                "family": {"type": "string", "description": "Product family identifier"},
                "max_examples": {"type": "integer", "description": "Maximum examples to verify"},
            },
            "required": ["family"],
        },
    },
    {
        "name": "compile_fix",
        "description": "Fix compilation errors using LLM",
        "inputSchema": {
            "type": "object",
            "properties": {
                "family": {"type": "string", "description": "Product family identifier"},
                "max_examples": {"type": "integer", "description": "Maximum examples to fix"},
            },
            "required": ["family"],
        },
    },
    {
        "name": "runtime_verify",
        "description": "Execute examples and verify runtime behavior",
        "inputSchema": {
            "type": "object",
            "properties": {
                "family": {"type": "string", "description": "Product family identifier"},
                "max_examples": {"type": "integer", "description": "Maximum examples to verify"},
            },
            "required": ["family"],
        },
    },
    {
        "name": "runtime_fix",
        "description": "Fix runtime errors using LLM",
        "inputSchema": {
            "type": "object",
            "properties": {
                "family": {"type": "string", "description": "Product family identifier"},
                "max_examples": {"type": "integer", "description": "Maximum examples to fix"},
            },
            "required": ["family"],
        },
    },
    {
        "name": "md_update",
        "description": "Update markdown files with verified code",
        "inputSchema": {
            "type": "object",
            "properties": {
                "family": {"type": "string", "description": "Product family identifier"},
                "dry_run": {"type": "boolean", "description": "Don't write changes", "default": False},
                "allow_md_write": {"type": "boolean", "description": "Override global config to allow markdown writes", "default": False},
                "audit_prose": {"type": "boolean", "description": "Audit and correct adjacent prose when LLM review is available", "default": False},
            },
            "required": ["family"],
        },
    },
    {
        "name": "final_review",
        "description": "Run final LLM review of updated markdown",
        "inputSchema": {
            "type": "object",
            "properties": {
                "family": {"type": "string", "description": "Product family identifier"},
            },
            "required": ["family"],
        },
    },
    {
        "name": "commit",
        "description": "Commit changes to git",
        "inputSchema": {
            "type": "object",
            "properties": {
                "family": {"type": "string", "description": "Product family identifier"},
            },
            "required": ["family"],
        },
    },
    {
        "name": "backfill",
        "description": "Backfill missing API references, test data, examples, and gist source",
        "inputSchema": {
            "type": "object",
            "properties": {
                "family": {"type": "string", "description": "Product family identifier"},
                "targets": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Backfill targets: test_data, api_catalog, examples, gist_source_code",
                },
                "force": {"type": "boolean", "description": "Force re-download even if data exists", "default": False},
            },
            "required": ["family"],
        },
    },
    {
        "name": "status",
        "description": "Get pipeline status",
        "inputSchema": {
            "type": "object",
            "properties": {
                "family": {"type": "string", "description": "Product family identifier (optional)"},
            },
        },
    },
    {
        "name": "run_pipeline",
        "description": "Run the full pipeline for a family",
        "inputSchema": {
            "type": "object",
            "properties": {
                "family": {"type": "string", "description": "Product family identifier"},
                "max_examples": {"type": "integer", "description": "Maximum examples to process"},
                "skip_runtime": {"type": "boolean", "description": "Skip runtime verification", "default": False},
                "skip_llm_fixes": {"type": "boolean", "description": "Skip LLM-based fixing", "default": False},
                "skip_llm_runtime_fixes": {"type": "boolean", "description": "Skip LLM fixes for runtime errors only (keeps compile-fix active)", "default": False},
                "dry_run": {"type": "boolean", "description": "Don't write changes", "default": False},
                "allow_md_write": {"type": "boolean", "description": "Override global config to allow markdown writes", "default": False},
                "allow_commit": {"type": "boolean", "description": "Override global config to allow git commit", "default": False},
                "strategy_config": {"type": "object", "description": "Dict controlling which fix strategies to enable (enable_transformers, enable_retrieval, enable_semantic_microfixes, enable_substitution, enable_learned_patterns)"},
                "content_roots": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Override content_roots from the family config. Paths to directories containing markdown files with code examples.",
                },
                "file_list": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Run on specific .md files (absolute paths). When provided, bypasses content_roots discovery entirely.",
                },
                "audit_prose": {
                    "type": "boolean",
                    "description": "Audit prose adjacent to code blocks using the LLM reviewer when available.",
                    "default": False,
                },
            },
            "required": ["family"],
        },
    },
    {
        "name": "validate_articles",
        "description": "Validate markdown article structure, duplicate content, and optional prose/code alignment for a family.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "family": {"type": "string", "description": "Product family identifier"},
                "file_list": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Specific markdown files to validate. Defaults to the family's discovered content roots.",
                },
                "content_roots": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional content root override when file_list is omitted.",
                },
                "audit_prose": {
                    "type": "boolean",
                    "description": "Audit prose against adjacent code using the LLM reviewer when available.",
                    "default": False,
                },
            },
            "required": ["family"],
        },
    },
    {
        "name": "validate_code_snippet",
        "description": "Validate a code snippet against the family's API catalog. Detects hallucinated Aspose types and namespace violations.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "The code snippet to validate"},
                "family": {"type": "string", "description": "Product family identifier (e.g. 'words', 'zip', 'cells')"},
                "language": {"type": "string", "description": "Programming language (default: 'csharp')", "default": "csharp"},
                "compile_verify": {"type": "boolean", "description": "Also compile the code (requires .NET SDK)", "default": False},
            },
            "required": ["code", "family"],
        },
    },
]
