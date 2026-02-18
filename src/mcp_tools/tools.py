"""
MCP Tools for Example Reviewer Pipeline.
Exposes pipeline functionality as MCP-compatible tools.
"""

import json
import logging
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
    ) -> ToolResult:
        """
        Scan for markdown files containing code examples.
        
        Maps to CLI command: scan
        Maps to phase: A_discovery_extraction (partial)
        
        Args:
            family: Family identifier (required if directory not provided)
            directory: Directory path to scan (required if family not provided)
            max_files: Maximum files to scan
            
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
    ) -> ToolResult:
        """
        Extract code examples from markdown files.
        
        Maps to CLI command: extract
        Maps to phase: A_discovery_extraction
        
        Args:
            family: Family identifier
            max_files: Maximum files to process
            
        Returns:
            ToolResult with extraction statistics
        """
        try:
            family_config = self.orchestrator.config_manager.load_family_config(family)

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
                run_id, family, dry_run, allow_md_write=allow_md_write
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
            )

            return ToolResult(success=results['success'], data=results)

        except Exception as e:
            return ToolResult(success=False, error=str(e))


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
        "name": "md_update",
        "description": "Update markdown files with verified code",
        "inputSchema": {
            "type": "object",
            "properties": {
                "family": {"type": "string", "description": "Product family identifier"},
                "dry_run": {"type": "boolean", "description": "Don't write changes", "default": False},
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
                "dry_run": {"type": "boolean", "description": "Don't write changes", "default": False},
            },
            "required": ["family"],
        },
    },
]
