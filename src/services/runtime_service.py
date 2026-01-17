"""
Runtime Service for Example Reviewer Pipeline.
Implements Phase C: Runtime Verification Loop.
"""

import os
import re
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

    # Default using statements for common scenarios
    DEFAULT_USINGS = [
        "System",
        "System.IO",
        "System.Text",
        "System.Linq",
        "System.Collections.Generic",
        "System.Threading.Tasks",
    ]

    # API class to namespace mapping for intelligent using inference
    # (Same as CompilationService to ensure consistency)
    API_NAMESPACE_MAP = {
        # Aspose.Zip
        'Archive': 'Aspose.Zip',
        'ArchiveEntry': 'Aspose.Zip',
        'ArchiveFactory': 'Aspose.Zip',
        'ArchiveEntrySettings': 'Aspose.Zip.Saving',
        'CompressionSettings': 'Aspose.Zip.Saving',
        'DeflateCompressionSettings': 'Aspose.Zip.Saving',
        'Bzip2CompressionSettings': 'Aspose.Zip.Saving',
        'LzmaCompressionSettings': 'Aspose.Zip.Saving',
        'ParallelCompressionOptions': 'Aspose.Zip.Saving',
        'SevenZipArchive': 'Aspose.Zip.SevenZip',
        'SevenZipArchiveEntry': 'Aspose.Zip.SevenZip',
        'SevenZipCompressionSettings': 'Aspose.Zip.Saving',
        'RarArchive': 'Aspose.Zip.Rar',
        'RarArchiveEntry': 'Aspose.Zip.Rar',
        'TarArchive': 'Aspose.Zip.Tar',
        'GzipArchive': 'Aspose.Zip.Gzip',
        'CabArchive': 'Aspose.Zip.Cab',
        'WimArchive': 'Aspose.Zip.Wim',
        'XarArchive': 'Aspose.Zip.Xar',
        'CpioArchive': 'Aspose.Zip.Cpio',
    }

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
        result = None  # Initialize to avoid reference before assignment
        
        try:
            if work_dir.exists():
                shutil.rmtree(work_dir)
            work_dir.mkdir(parents=True)
            
            # Get code to execute (use verified_code if available, else compilable)
            code = example.verified_code or example.compilable_code or example.original_code
            
            # Copy test data if available
            if test_data_path and test_data_path.exists():
                self._copy_test_data(test_data_path, work_dir, family_config.runtime_validation)
            
            # Build and run the project
            result = self._build_and_run(work_dir, code, family_config)
            
            return result.success, result
            
        except Exception as e:
            logger.exception(f"Error executing example {example.example_id}")
            if result is None:
                result = RuntimeResult(
                    success=False,
                    exit_code=-1,
                    stdout="",
                    stderr=str(e),
                    duration_ms=0,
                    exception_type=type(e).__name__,
                    exception_message=str(e),
                )
            return False, result
            
        finally:
            # Cleanup workspace (keep artifacts if failed for debugging)
            if work_dir.exists() and result is not None and result.success:
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
        
        # First, copy all files from source that might be needed
        # This ensures common test files are available
        for src_file in source_dir.iterdir():
            if src_file.is_file():
                dst_path = work_dir / src_file.name
                if not dst_path.exists():
                    shutil.copy2(src_file, dst_path)
            elif src_file.is_dir() and not src_file.name.startswith('.'):
                dst_path = work_dir / src_file.name
                if not dst_path.exists():
                    shutil.copytree(src_file, dst_path)
        
        # Then handle specific required files with aliases
        for required_file in required_files:
            src_path = source_dir / required_file
            source_found = None

            # Try exact match first
            if src_path.exists():
                source_found = src_path
                dst_path = work_dir / required_file
                if not dst_path.exists():
                    if src_path.is_dir():
                        shutil.copytree(src_path, dst_path)
                    else:
                        shutil.copy2(src_path, dst_path)
            else:
                # Try to find from aliases
                aliases = file_aliases.get(required_file, [])

                # Find a source file from aliases
                for alias in aliases:
                    alias_src = source_dir / alias
                    if alias_src.exists():
                        source_found = alias_src
                        break

                if source_found:
                    # Copy to the required name
                    dst_path = work_dir / required_file
                    if not dst_path.exists():
                        if source_found.is_dir():
                            shutil.copytree(source_found, dst_path)
                        else:
                            shutil.copy2(source_found, dst_path)

            # Create alias copies (whether we found the file directly or through an alias)
            if source_found:
                aliases = file_aliases.get(required_file, [])
                for alias in aliases:
                    alias_dst = work_dir / alias
                    if not alias_dst.exists():
                        if source_found.is_dir():
                            shutil.copytree(source_found, alias_dst)
                        else:
                            shutil.copy2(source_found, alias_dst)
    
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
        timeout = family_config.runtime_validation.timeout_seconds
        
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
                env={**os.environ, **family_config.runtime_validation.env},
            )
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Check for output files
            output_files = self._find_output_files(work_dir, family_config.runtime_validation)
            
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
    
    def _analyze_code(self, code: str, family_config: FamilyConfig) -> Dict[str, Any]:
        """
        Analyze code to determine its structure and what's missing.

        Returns:
            Dictionary with analysis results including detected APIs and missing elements
        """
        # Check for various code elements
        has_usings = bool(re.search(r'^\s*using\s+[\w\.]+\s*;', code, re.MULTILINE))
        has_namespace = bool(re.search(r'\bnamespace\s+[\w\.]+', code))
        has_class = bool(re.search(r'\bclass\s+\w+', code))
        has_main = bool(re.search(r'\bstatic\s+(?:async\s+)?(?:void|Task|Task<int>|int)\s+Main\s*\(', code))
        is_async = bool(re.search(r'\bawait\s+', code)) or bool(re.search(r'\basync\s+', code))

        # Detect API usage
        detected_apis = []
        for api_class in self.API_NAMESPACE_MAP.keys():
            patterns = [
                rf'\bnew\s+{api_class}\b',
                rf'\b{api_class}\.',
                rf'\b{api_class}<',
                rf'<{api_class}>',
                rf'\({api_class}\s+\w+\)',
            ]
            if any(re.search(pattern, code) for pattern in patterns):
                detected_apis.append(api_class)

        # Infer missing using statements
        missing_usings = self._infer_usings(code, family_config, detected_apis)

        # Check if code is complete
        is_complete = has_namespace or (has_class and has_main)

        return {
            'has_usings': has_usings,
            'has_namespace': has_namespace,
            'has_class': has_class,
            'has_main': has_main,
            'is_async': is_async,
            'detected_apis': detected_apis,
            'missing_usings': missing_usings,
            'is_complete': is_complete,
        }

    def _infer_usings(self, code: str, family_config: FamilyConfig, detected_apis: List[str]) -> List[str]:
        """
        Infer required using statements from API usage in code.

        Args:
            code: Code to analyze
            family_config: Family configuration
            detected_apis: List of detected API classes

        Returns:
            List of required using statements
        """
        required_usings = set(self.DEFAULT_USINGS)

        # Add family-specific usings
        if family_config.code_defaults:
            required_usings.update(family_config.code_defaults.default_usings)

        # Add usings based on detected APIs
        for api_class in detected_apis:
            if api_class in self.API_NAMESPACE_MAP:
                namespace = self.API_NAMESPACE_MAP[api_class]
                required_usings.add(namespace)

        # Extract existing using statements
        existing_usings = set()
        using_pattern = r'using\s+([\w\.]+)\s*;'
        for match in re.finditer(using_pattern, code):
            existing_usings.add(match.group(1))

        # Return only missing usings
        missing = required_usings - existing_usings
        return sorted(list(missing))

    def _wrap_code(self, code: str, family_config: FamilyConfig) -> str:
        """
        Intelligently wrap code snippet in a compilable structure based on what's already present.
        Uses the same enhanced logic as CompilationService to avoid build failures.

        Detection rules:
        - Has 'namespace' -> wrap minimally, just add missing usings
        - Has 'class' but no namespace -> add namespace and usings
        - Has 'Main' method -> add class wrapper and usings
        - Raw statements -> full wrapper (usings + class + Main)

        Also handles:
        - Top-level statements (C# 9+)
        - Async Main patterns
        - Multiple class definitions
        - Partial code snippets

        Args:
            code: Original code snippet
            family_config: Family configuration

        Returns:
            Wrapped code ready for compilation
        """
        # Analyze the code
        analysis = self._analyze_code(code, family_config)

        lines = []

        # Strategy 1: Code has namespace - minimal wrapping needed
        if analysis['has_namespace']:
            # Just add missing usings at the top if needed
            if analysis['missing_usings']:
                for using in analysis['missing_usings']:
                    lines.append(f"using {using};")
                lines.append("")
            lines.append(code)
            return '\n'.join(lines)

        # Strategy 2: Code has class but no namespace
        if analysis['has_class']:
            # Add usings
            all_usings = list(set(self.DEFAULT_USINGS + (family_config.code_defaults.default_usings if family_config.code_defaults else [])))
            if analysis['detected_apis']:
                for api in analysis['detected_apis']:
                    if api in self.API_NAMESPACE_MAP:
                        all_usings.append(self.API_NAMESPACE_MAP[api])

            if not analysis['has_usings']:
                for using in sorted(set(all_usings)):
                    lines.append(f"using {using};")
                lines.append("")

            lines.append(code)
            return '\n'.join(lines)

        # Strategy 3: Code has Main method but no class - just add class wrapper
        if analysis['has_main']:
            # Add usings
            if analysis['missing_usings']:
                for using in analysis['missing_usings']:
                    lines.append(f"using {using};")
                lines.append("")

            lines.append("public class Program")
            lines.append("{")
            # Indent existing code
            for line in code.split('\n'):
                lines.append(f"    {line}")
            lines.append("}")
            return '\n'.join(lines)

        # Strategy 4: Raw statements - full wrapper needed
        # CRITICAL: Separate using statements from actual code to avoid putting usings inside Main
        code_lines = code.split('\n')
        using_lines = []
        code_body_lines = []
        in_usings = True

        for line in code_lines:
            stripped = line.strip()
            # Check if this line is a using statement
            if in_usings and (stripped.startswith('using ') and stripped.endswith(';')):
                using_lines.append(line)
            elif in_usings and (not stripped or stripped.startswith('//')):
                # Skip empty lines and comments at the top
                continue
            else:
                # Once we hit non-using code, add all remaining lines to body
                in_usings = False
                code_body_lines.append(line)

        # Add all required usings (combine with existing)
        all_usings = set(self.DEFAULT_USINGS)
        if family_config.code_defaults:
            all_usings.update(family_config.code_defaults.default_usings)
        for api in analysis['detected_apis']:
            if api in self.API_NAMESPACE_MAP:
                all_usings.add(self.API_NAMESPACE_MAP[api])

        # Extract namespaces from existing using statements
        for using_line in using_lines:
            match = re.match(r'using\s+([\w\.]+)\s*;', using_line.strip())
            if match:
                all_usings.add(match.group(1))

        # Write all usings
        for using in sorted(all_usings):
            lines.append(f"using {using};")
        lines.append("")

        lines.append("public class Program")
        lines.append("{")

        # Determine Main signature
        if analysis['is_async']:
            lines.append("    public static async Task Main(string[] args)")
        else:
            lines.append("    public static void Main(string[] args)")

        lines.append("    {")

        # Indent only the actual code body (not the using statements)
        for line in code_body_lines:
            lines.append(f"        {line}")

        lines.append("    }")
        lines.append("}")

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
        family: str,
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
        llm_req_ref = ""
        llm_resp_ref = ""
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
            family=family,
            sample_ref=sample_ref,
            scenario=scenario,
            success=runtime_result.success,
            runtime_log_ref=log_ref,
            exit_code=runtime_result.exit_code,
            stdout=runtime_result.stdout,
            stderr=runtime_result.stderr,
            exception_type=runtime_result.exception_type,
            exception_message=runtime_result.exception_message,
            output_files=runtime_result.output_files or [],
            environment=environment,
            retrieved_examples_refs=retrieved_examples or [],
            llm_request_ref=llm_req_ref,
            llm_response_ref=llm_resp_ref,
        )
        
        self.db.save_runtime_attempt(attempt)
        return attempt_id
    
    def _store_artifact(self, filename: str, content: str) -> str:
        """Store an artifact file and return its reference."""
        artifact_path = self.artifacts_dir / filename
        artifact_path.write_text(content, encoding='utf-8')
        return str(artifact_path)
