"""
Runtime Service for Example Reviewer Pipeline.
Implements Phase C: Runtime Verification Loop.
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

from ..core.models import ExampleRecord, ExampleStatus, RuntimeAttempt
from ..core.database import Database
from ..core.config import FamilyConfig, RuntimeValidationConfig

logger = logging.getLogger(__name__)


@dataclass
class RuntimeResult:
    """Result of a runtime execution attempt."""
    success: bool
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int
    exception_type: Optional[str] = None
    exception_message: Optional[str] = None
    output_files: Optional[List[str]] = None


class RuntimeService:
    """
    Service for executing compiled code examples.
    Implements the C_runtime_verify_fix_loop phase from the spec.
    """
    
    def __init__(
        self,
        db: Database,
        workspace_dir: Optional[Path] = None,
        artifacts_dir: Optional[Path] = None,
    ):
        """
        Initialize runtime service.
        
        Args:
            db: Database instance
            workspace_dir: Working directory for execution
            artifacts_dir: Directory for storing runtime artifacts
        """
        self.db = db
        self.workspace_dir = workspace_dir or Path(tempfile.gettempdir()) / "example_reviewer"
        self.artifacts_dir = artifacts_dir or self.workspace_dir / "artifacts"
        
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
    
    def execute_example(
        self,
        example: ExampleRecord,
        family_config: FamilyConfig,
        test_data_path: Optional[Path] = None,
    ) -> Tuple[bool, RuntimeResult]:
        """
        Execute a compiled example with test data.
        
        Args:
            example: Example record to execute
            family_config: Family configuration
            test_data_path: Path to test data directory
            
        Returns:
            Tuple of (success, RuntimeResult)
        """
        # Create workspace for this execution
        work_dir = self.workspace_dir / f"runtime_{example.example_id}"
        
        try:
            if work_dir.exists():
                shutil.rmtree(work_dir)
            work_dir.mkdir(parents=True)
            
            # Get code to execute (use verified_code if available, else compilable)
            code = example.verified_code or example.compilable_code or example.original_code
            
            # Copy test data if available
            if test_data_path and test_data_path.exists():
                self._copy_test_data(test_data_path, work_dir, family_config.runtime)
            
            # Build and run the project
            result = self._build_and_run(work_dir, code, family_config)
            
            return result.success, result
            
        finally:
            # Cleanup workspace (keep artifacts if failed for debugging)
            if work_dir.exists() and result.success:
                try:
                    shutil.rmtree(work_dir)
                except Exception:
                    pass
    
    def _copy_test_data(
        self,
        source_dir: Path,
        work_dir: Path,
        runtime_config: RuntimeValidationConfig,
    ) -> None:
        """Copy required test data files to workspace."""
        required_files = runtime_config.required_files
        file_aliases = runtime_config.file_aliases
        
        for required_file in required_files:
            src_path = source_dir / required_file
            
            # Try exact match first
            if src_path.exists():
                dst_path = work_dir / required_file
                if src_path.is_dir():
                    shutil.copytree(src_path, dst_path)
                else:
                    shutil.copy2(src_path, dst_path)
                continue
            
            # Try aliases
            aliases = file_aliases.get(required_file, [])
            for alias in aliases:
                alias_src = source_dir / alias
                if alias_src.exists():
                    # Copy to both the original name and alias
                    dst_path = work_dir / required_file
                    if alias_src.is_dir():
                        shutil.copytree(alias_src, dst_path)
                    else:
                        shutil.copy2(alias_src, dst_path)
                    break
    
    def _build_and_run(
        self,
        work_dir: Path,
        code: str,
        family_config: FamilyConfig,
    ) -> RuntimeResult:
        """Build and execute code in workspace."""
        import time
        
        # Write project and code files
        self._write_project(work_dir, family_config)
        
        # Wrap code if needed
        wrapped_code = self._wrap_code(code, family_config)
        (work_dir / "Program.cs").write_text(wrapped_code, encoding='utf-8')
        
        start_time = time.time()
        timeout = family_config.runtime.timeout_seconds
        
        try:
            # Restore and build
            restore_result = subprocess.run(
                ["dotnet", "restore", "--verbosity", "quiet"],
                cwd=work_dir,
                capture_output=True,
                text=True,
                timeout=60,
            )
            
            if restore_result.returncode != 0:
                return RuntimeResult(
                    success=False,
                    exit_code=restore_result.returncode,
                    stdout=restore_result.stdout,
                    stderr=f"Restore failed: {restore_result.stderr}",
                    duration_ms=int((time.time() - start_time) * 1000),
                )
            
            build_result = subprocess.run(
                ["dotnet", "build", "--no-restore", "-c", "Release", "--verbosity", "quiet"],
                cwd=work_dir,
                capture_output=True,
                text=True,
                timeout=60,
            )
            
            if build_result.returncode != 0:
                return RuntimeResult(
                    success=False,
                    exit_code=build_result.returncode,
                    stdout=build_result.stdout,
                    stderr=f"Build failed: {build_result.stderr}",
                    duration_ms=int((time.time() - start_time) * 1000),
                )
            
            # Run the executable
            run_result = subprocess.run(
                ["dotnet", "run", "--no-build", "-c", "Release"],
                cwd=work_dir,
                capture_output=True,
                text=True,
                timeout=timeout,
                env={**os.environ, **family_config.runtime.env},
            )
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Check for output files
            output_files = self._find_output_files(work_dir, family_config.runtime)
            
            # Parse exception info from stderr if failed
            exception_type = None
            exception_message = None
            
            if run_result.returncode != 0:
                exception_type, exception_message = self._parse_exception(
                    run_result.stdout + run_result.stderr
                )
            
            return RuntimeResult(
                success=run_result.returncode == 0,
                exit_code=run_result.returncode,
                stdout=run_result.stdout,
                stderr=run_result.stderr,
                duration_ms=duration_ms,
                exception_type=exception_type,
                exception_message=exception_message,
                output_files=output_files,
            )
            
        except subprocess.TimeoutExpired:
            duration_ms = int((time.time() - start_time) * 1000)
            return RuntimeResult(
                success=False,
                exit_code=-1,
                stdout="",
                stderr=f"Execution timed out after {timeout} seconds",
                duration_ms=duration_ms,
                exception_type="TimeoutException",
                exception_message=f"Execution exceeded {timeout}s timeout",
            )
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            return RuntimeResult(
                success=False,
                exit_code=-1,
                stdout="",
                stderr=str(e),
                duration_ms=duration_ms,
                exception_type=type(e).__name__,
                exception_message=str(e),
            )
    
    def _write_project(self, work_dir: Path, family_config: FamilyConfig) -> None:
        """Write .csproj file for execution."""
        nuget_config = family_config.nuget_config
        
        # Build package references
        package_refs = []
        
        primary = nuget_config.get('primary_package', {})
        if primary:
            pkg_name = primary.get('name', '')
            if pkg_name:
                version = primary.get('version', '')
                if version and version != 'latest_stable':
                    package_refs.append(
                        f'    <PackageReference Include="{pkg_name}" Version="{version}" />'
                    )
                else:
                    package_refs.append(
                        f'    <PackageReference Include="{pkg_name}" Version="*" />'
                    )
        
        for pkg in nuget_config.get('additional_packages', []):
            if isinstance(pkg, dict):
                name = pkg.get('name', '')
                version = pkg.get('version', '*')
            else:
                name = pkg
                version = '*'
            
            if name:
                package_refs.append(
                    f'    <PackageReference Include="{name}" Version="{version}" />'
                )
        
        project_content = f"""<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <ImplicitUsings>enable</ImplicitUsings>
    <Nullable>enable</Nullable>
    <OutputType>Exe</OutputType>
  </PropertyGroup>
  <ItemGroup>
{chr(10).join(package_refs)}
  </ItemGroup>
</Project>
"""
        (work_dir / "Runtime.csproj").write_text(project_content, encoding='utf-8')
    
    def _wrap_code(self, code: str, family_config: FamilyConfig) -> str:
        """Wrap code in compilable structure."""
        # Get additional usings from config
        family_usings = family_config.code_defaults.get('default_usings', [])
        
        DEFAULT_USINGS = [
            "System",
            "System.IO",
            "System.Text",
            "System.Linq",
            "System.Collections.Generic",
            "System.Threading.Tasks",
        ]
        
        all_usings = list(set(DEFAULT_USINGS + family_usings))
        
        # Check if code already has structure
        has_usings = code.strip().startswith('using ')
        has_class = 'class ' in code
        has_main = 'static void Main' in code or 'static async Task Main' in code
        
        lines = []
        
        if not has_usings:
            for using in sorted(all_usings):
                lines.append(f"using {using};")
            lines.append("")
        
        if not has_class:
            lines.append("public class Program")
            lines.append("{")
            
            if not has_main:
                lines.append("    public static void Main(string[] args)")
                lines.append("    {")
                for line in code.split('\n'):
                    lines.append(f"        {line}")
                lines.append("    }")
            else:
                lines.append(code)
            
            lines.append("}")
        else:
            if has_usings:
                lines = [code]
            else:
                lines.append(code)
        
        return '\n'.join(lines)
    
    def _find_output_files(
        self,
        work_dir: Path,
        runtime_config: RuntimeValidationConfig,
    ) -> List[str]:
        """Find expected output files in workspace."""
        output_files = []
        
        for pattern in runtime_config.expected_outputs:
            matches = list(work_dir.glob(pattern))
            output_files.extend(str(m.relative_to(work_dir)) for m in matches)
        
        return output_files
    
    def _parse_exception(self, output: str) -> Tuple[Optional[str], Optional[str]]:
        """Parse exception information from output."""
        # Look for common .NET exception patterns
        import re
        
        # Pattern: Unhandled exception. System.SomeException: Message
        match = re.search(
            r'Unhandled exception[.:]\s*([A-Za-z.]+Exception):\s*(.+?)(?:\n|$)',
            output
        )
        if match:
            return match.group(1), match.group(2).strip()
        
        # Pattern: System.SomeException: Message
        match = re.search(
            r'([A-Za-z.]+Exception):\s*(.+?)(?:\n|$)',
            output
        )
        if match:
            return match.group(1), match.group(2).strip()
        
        return None, None
    
    def record_attempt(
        self,
        example_id: str,
        runtime_result: RuntimeResult,
        sample_ref: str,
        scenario: str,
        retrieved_examples: Optional[List[str]] = None,
        llm_request: Optional[str] = None,
        llm_response: Optional[str] = None,
    ) -> str:
        """Record a runtime attempt in the database."""
        attempt_id = str(uuid.uuid4())[:8]
        
        # Store log artifact
        log_content = f"STDOUT:\n{runtime_result.stdout}\n\nSTDERR:\n{runtime_result.stderr}"
        log_ref = self._store_artifact(f"{attempt_id}_runtime.log", log_content)
        
        # Store LLM artifacts if present
        llm_req_ref = None
        llm_resp_ref = None
        if llm_request:
            llm_req_ref = self._store_artifact(f"{attempt_id}_llm_req.txt", llm_request)
        if llm_response:
            llm_resp_ref = self._store_artifact(f"{attempt_id}_llm_resp.txt", llm_response)
        
        # Create environment info
        environment = {
            "os": os.name,
            "framework": "net8.0",
            "exit_code": str(runtime_result.exit_code),
            "duration_ms": str(runtime_result.duration_ms),
        }
        
        attempt = RuntimeAttempt(
            attempt_id=attempt_id,
            example_id=example_id,
            sample_ref=sample_ref,
            scenario=scenario,
            success=runtime_result.success,
            runtime_log_ref=log_ref,
            environment=environment,
            retrieved_examples_refs=retrieved_examples,
            llm_request_ref=llm_req_ref,
            llm_response_ref=llm_resp_ref,
        )
        
        self.db.create_runtime_attempt(attempt)
        return attempt_id
    
    def _store_artifact(self, filename: str, content: str) -> str:
        """Store an artifact file and return its reference."""
        artifact_path = self.artifacts_dir / filename
        artifact_path.write_text(content, encoding='utf-8')
        return str(artifact_path)
