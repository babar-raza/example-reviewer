"""
Compilation Service for Example Reviewer Pipeline.
Implements Phase B: Compilation Verification Loop.
"""

import os
import uuid
import json
import shutil
import logging
import tempfile
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass

from ..core.models import (
    ExampleRecord, ExampleStatus, CompileAttempt, LLMFixPayload
)
from ..core.database import Database
from ..core.config import FamilyConfig

logger = logging.getLogger(__name__)


@dataclass
class CompileResult:
    """Result of a compilation attempt."""
    success: bool
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int
    dll_version: str
    errors: List[str]
    warnings: List[str]


class CompilationService:
    """
    Service for compiling and validating C# code examples.
    Implements the B_compile_verify_fix_loop phase from the spec.
    """
    
    # Default using statements for common scenarios
    DEFAULT_USINGS = [
        "System",
        "System.IO",
        "System.Text",
        "System.Linq",
        "System.Collections.Generic",
        "System.Threading.Tasks",
    ]
    
    # Project template for .NET 8
    PROJECT_TEMPLATE = """<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <ImplicitUsings>enable</ImplicitUsings>
    <Nullable>enable</Nullable>
    <OutputType>Exe</OutputType>
  </PropertyGroup>
  <ItemGroup>
{package_refs}
  </ItemGroup>
</Project>
"""
    
    def __init__(
        self,
        db: Database,
        workspace_dir: Optional[Path] = None,
        artifacts_dir: Optional[Path] = None,
    ):
        """
        Initialize compilation service.
        
        Args:
            db: Database instance
            workspace_dir: Working directory for compilation
            artifacts_dir: Directory for storing compilation artifacts
        """
        self.db = db
        self.workspace_dir = workspace_dir or Path(tempfile.gettempdir()) / "example_reviewer"
        self.artifacts_dir = artifacts_dir or self.workspace_dir / "artifacts"
        
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
    
    def compile_example(
        self,
        example: ExampleRecord,
        family_config: FamilyConfig,
    ) -> Tuple[bool, CompileResult]:
        """
        Attempt to compile a single example.
        
        Args:
            example: Example record to compile
            family_config: Family configuration
            
        Returns:
            Tuple of (success, CompileResult)
        """
        # Create workspace for this compilation
        work_dir = self.workspace_dir / f"compile_{example.example_id}"
        
        try:
            if work_dir.exists():
                shutil.rmtree(work_dir)
            work_dir.mkdir(parents=True)
            
            # Get code to compile (use compilable_code if available, else original)
            code = example.compilable_code or example.original_code
            
            # Wrap code in compilable structure
            wrapped_code = self._wrap_code(code, family_config)
            
            # Write project files
            self._write_project(work_dir, family_config)
            
            # Write code file
            code_path = work_dir / "Program.cs"
            code_path.write_text(wrapped_code, encoding='utf-8')
            
            # Run dotnet build
            result = self._run_build(work_dir, family_config)
            
            return result.success, result
            
        finally:
            # Cleanup workspace
            if work_dir.exists():
                try:
                    shutil.rmtree(work_dir)
                except Exception:
                    pass
    
    def _wrap_code(self, code: str, family_config: FamilyConfig) -> str:
        """
        Wrap code snippet in a compilable Program.cs structure.
        
        Args:
            code: Original code snippet
            family_config: Family configuration
            
        Returns:
            Wrapped code ready for compilation
        """
        # Check if code already has using statements
        has_usings = 'using ' in code and code.strip().startswith('using ')
        
        # Check if code already has a class definition
        has_class = 'class ' in code
        
        # Check if code already has Main method
        has_main = 'static void Main' in code or 'static async Task Main' in code
        
        # Get additional usings from config
        family_usings = family_config.code_defaults.default_usings if family_config.code_defaults else []
        all_usings = list(set(self.DEFAULT_USINGS + family_usings))
        
        # Build the wrapped code
        lines = []
        
        # Add using statements if not present
        if not has_usings:
            for using in sorted(all_usings):
                lines.append(f"using {using};")
            lines.append("")
        
        # If code doesn't have a class, wrap it
        if not has_class:
            lines.append("public class Program")
            lines.append("{")
            
            if not has_main:
                lines.append("    public static void Main(string[] args)")
                lines.append("    {")
                # Indent the code
                for line in code.split('\n'):
                    lines.append(f"        {line}")
                lines.append("    }")
            else:
                lines.append(code)
            
            lines.append("}")
        else:
            # Code has a class, use as-is but add usings if needed
            if has_usings:
                lines = [code]
            else:
                lines.append(code)
        
        return '\n'.join(lines)
    
    def _write_project(self, work_dir: Path, family_config: FamilyConfig) -> None:
        """Write .csproj file for compilation."""
        nuget_config = family_config.nuget_config
        
        # Build package references
        package_refs = []
        
        if nuget_config:
            # Primary package
            primary = nuget_config.primary_package
            if primary and primary.name:
                version = primary.version if primary.version else "*"
                package_refs.append(
                    f'    <PackageReference Include="{primary.name}" Version="{version}" />'
                )
            
            # Additional packages
            for pkg in nuget_config.additional_packages:
                if pkg.name:
                    version = pkg.version if pkg.version else "*"
                    package_refs.append(
                        f'    <PackageReference Include="{pkg.name}" Version="{version}" />'
                    )
        
        # Write project file
        project_content = self.PROJECT_TEMPLATE.format(
            package_refs='\n'.join(package_refs)
        )
        
        (work_dir / "Compilation.csproj").write_text(project_content, encoding='utf-8')
    
    def _run_build(self, work_dir: Path, family_config: FamilyConfig) -> CompileResult:
        """Run dotnet build and collect results."""
        import time
        
        start_time = time.time()
        
        try:
            # Restore packages first
            restore_result = subprocess.run(
                ["dotnet", "restore", "--verbosity", "minimal"],
                cwd=work_dir,
                capture_output=True,
                text=True,
                timeout=120,  # Longer timeout for restore
            )
            
            # Check if restore failed
            if restore_result.returncode != 0:
                duration_ms = int((time.time() - start_time) * 1000)
                combined_output = restore_result.stdout + restore_result.stderr
                return CompileResult(
                    success=False,
                    exit_code=restore_result.returncode,
                    stdout=restore_result.stdout,
                    stderr=restore_result.stderr,
                    duration_ms=duration_ms,
                    dll_version="unknown",
                    errors=self._parse_errors(combined_output) or ["Package restore failed"],
                    warnings=self._parse_warnings(combined_output),
                )
            
            # Build (no-restore since we just restored)
            build_result = subprocess.run(
                ["dotnet", "build", "--no-restore", "--verbosity", "minimal"],
                cwd=work_dir,
                capture_output=True,
                text=True,
                timeout=120,
            )
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Parse errors and warnings
            combined_output = build_result.stdout + build_result.stderr
            errors = self._parse_errors(combined_output)
            warnings = self._parse_warnings(combined_output)
            
            # Get DLL version from nuget config
            dll_version = "latest"
            if family_config.nuget_config and family_config.nuget_config.primary_package:
                dll_version = family_config.nuget_config.primary_package.version or "latest"
            
            return CompileResult(
                success=build_result.returncode == 0,
                exit_code=build_result.returncode,
                stdout=build_result.stdout,
                stderr=build_result.stderr,
                duration_ms=duration_ms,
                dll_version=dll_version,
                errors=errors,
                warnings=warnings,
            )
            
        except subprocess.TimeoutExpired:
            duration_ms = int((time.time() - start_time) * 1000)
            return CompileResult(
                success=False,
                exit_code=-1,
                stdout="",
                stderr="Compilation timed out",
                duration_ms=duration_ms,
                dll_version="unknown",
                errors=["Compilation timed out"],
                warnings=[],
            )
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            return CompileResult(
                success=False,
                exit_code=-1,
                stdout="",
                stderr=str(e),
                duration_ms=duration_ms,
                dll_version="unknown",
                errors=[str(e)],
                warnings=[],
            )
    
    def _parse_errors(self, output: str) -> List[str]:
        """Parse compilation errors from output."""
        errors = []
        for line in output.split('\n'):
            if ': error ' in line or 'error CS' in line:
                errors.append(line.strip())
        return errors
    
    def _parse_warnings(self, output: str) -> List[str]:
        """Parse compilation warnings from output."""
        warnings = []
        for line in output.split('\n'):
            if ': warning ' in line or 'warning CS' in line:
                warnings.append(line.strip())
        return warnings
    
    def create_fix_payload(
        self,
        example: ExampleRecord,
        compile_result: CompileResult,
        family_config: Optional[FamilyConfig] = None,
        api_context: Optional[str] = None,
        similar_examples: Optional[List[str]] = None,
    ) -> LLMFixPayload:
        """
        Create payload for LLM-based code fixing.
        
        Args:
            example: Example that failed compilation
            compile_result: Compilation result with errors
            family_config: Family configuration
            api_context: Relevant API documentation
            similar_examples: Similar working examples
            
        Returns:
            LLMFixPayload for sending to LLM
        """
        # Combine error information
        errors = compile_result.errors + [
            f"Exit code: {compile_result.exit_code}",
            compile_result.stderr,
        ]
        
        default_usings = []
        nuget_package = ""
        
        if family_config:
            if family_config.code_defaults:
                default_usings = family_config.code_defaults.default_usings
            if family_config.nuget_config and family_config.nuget_config.primary_package:
                nuget_package = family_config.nuget_config.primary_package.name
        
        return LLMFixPayload(
            code=example.compilable_code or example.original_code,
            errors=errors,
            context_type="compile",
            api_references=[api_context] if api_context else [],
            similar_examples=similar_examples or [],
            scaffolding_hints=[],
            family=example.family,
            nuget_package=nuget_package,
            default_usings=default_usings,
        )
    
    def record_attempt(
        self,
        example_id: str,
        compile_result: CompileResult,
        input_code: str,
        output_code: Optional[str] = None,
        llm_request: Optional[str] = None,
        llm_response: Optional[str] = None,
    ) -> str:
        """
        Record a compilation attempt in the database.
        
        Args:
            example_id: Example ID
            compile_result: Compilation result
            input_code: Code that was compiled
            output_code: Fixed code (if any)
            llm_request: LLM request (if applicable)
            llm_response: LLM response (if applicable)
            
        Returns:
            Attempt ID
        """
        attempt_id = str(uuid.uuid4())[:8]
        
        # Store artifacts
        input_ref = self._store_artifact(f"{attempt_id}_input.cs", input_code)
        output_ref = None
        if output_code:
            output_ref = self._store_artifact(f"{attempt_id}_output.cs", output_code)
        
        log_ref = self._store_artifact(
            f"{attempt_id}_log.txt",
            f"{compile_result.stdout}\n{compile_result.stderr}"
        )
        
        llm_req_ref = None
        llm_resp_ref = None
        if llm_request:
            llm_req_ref = self._store_artifact(f"{attempt_id}_llm_req.txt", llm_request)
        if llm_response:
            llm_resp_ref = self._store_artifact(f"{attempt_id}_llm_resp.txt", llm_response)
        
        attempt = CompileAttempt(
            attempt_id=attempt_id,
            example_id=example_id,
            family=self.db.get_example(example_id).family if self.db.get_example(example_id) else "",
            dll_version=compile_result.dll_version,
            success=compile_result.success,
            compiler_log_ref=log_ref,
            input_code_ref=input_ref,
            output_code_ref=output_ref or "",
            llm_request_ref=llm_req_ref or "",
            llm_response_ref=llm_resp_ref or "",
            error_messages=compile_result.errors,
            warnings=compile_result.warnings,
        )
        
        self.db.save_compile_attempt(attempt)
        return attempt_id
    
    def _store_artifact(self, filename: str, content: str) -> str:
        """Store an artifact file and return its reference."""
        artifact_path = self.artifacts_dir / filename
        artifact_path.write_text(content, encoding='utf-8')
        return str(artifact_path)


def check_dotnet_available() -> Tuple[bool, str]:
    """Check if .NET SDK is available."""
    try:
        result = subprocess.run(
            ["dotnet", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return True, result.stdout.strip()
        return False, result.stderr
    except Exception as e:
        return False, str(e)
