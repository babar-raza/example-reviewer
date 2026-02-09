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
from typing import Optional, List, Dict, Any, Tuple, TYPE_CHECKING
from dataclasses import dataclass

from ..core.models import ExampleRecord, ExampleStatus, RuntimeAttempt
from ..core.database import Database
from ..core.config import FamilyConfig, RuntimeValidationConfig

if TYPE_CHECKING:
    from ..pipeline.family_service_registry import FamilyServiceRegistry

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
    stack_trace: Optional[str] = None
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


    def __init__(
        self,
        db: Database,
        family: str,
        registry: Optional['FamilyServiceRegistry'] = None,
        workspace_dir: Optional[Path] = None,
        artifacts_dir: Optional[Path] = None,
    ):
        """
        Initialize runtime service.

        Args:
            db: Database instance
            family: Product family identifier (e.g., 'zip', 'words')
            registry: FamilyServiceRegistry for family-aware service access (optional)
            workspace_dir: Working directory for execution
            artifacts_dir: Directory for storing runtime artifacts
        """
        self.db = db
        self.family = family
        self.registry = registry
        self.workspace_dir = workspace_dir or Path(tempfile.gettempdir()) / "example_reviewer"
        self.artifacts_dir = artifacts_dir or self.workspace_dir / "artifacts"

        # Load namespace map from registry if available, else use empty dict
        if registry:
            self.namespace_map = registry.get_namespace_map(family)
            logger.info(f"RuntimeService({family}): loaded {len(self.namespace_map)} types from registry")
            if self.namespace_map:
                # Log first 5 entries for debugging
                sample = list(self.namespace_map.items())[:5]
                logger.info(f"RuntimeService({family}): sample namespace_map entries: {sample}")
            else:
                logger.warning(f"RuntimeService({family}): namespace_map is EMPTY despite registry being provided!")
        else:
            self.namespace_map = {}
            logger.info(f"RuntimeService({family}): no registry provided, using empty namespace map")

        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def find_test_file(
        required_name: str,
        source_dir: Path,
        file_aliases: Dict[str, List[str]],
        inventory: Optional[Dict[str, str]] = None
    ) -> Optional[Path]:
        """
        Find a test file recursively in source_dir.

        Lookup order:
        1. Exact match anywhere under source_dir (recursive)
        2. Alias match anywhere under source_dir (recursive)
        3. Case-insensitive basename match with same extension (recursive)
        4. Inventory mapping (if inventory contains full relative paths)

        Args:
            required_name: Required filename
            source_dir: Root directory to search in
            file_aliases: Alias mappings for files
            inventory: Optional inventory dict mapping canonical names to actual paths

        Returns:
            Path to found file, or None if not found
        """
        if not source_dir.exists():
            return None

        # Tier 1: Exact match (recursive)
        for candidate in source_dir.rglob(required_name):
            if candidate.is_file():
                return candidate

        # Tier 2: Alias lookup (recursive)
        aliases = file_aliases.get(required_name, [])
        for alias in aliases:
            for candidate in source_dir.rglob(alias):
                if candidate.is_file():
                    return candidate

        # Tier 3: Case-insensitive basename match with same extension (recursive)
        required_basename = Path(required_name).stem.lower()
        required_suffix = Path(required_name).suffix.lower()

        for candidate in source_dir.rglob(f"*{required_suffix}"):
            if candidate.is_file() and candidate.stem.lower() == required_basename:
                return candidate

        # Tier 4: Inventory mapping (if provided)
        if inventory and required_name in inventory:
            mapped_path = source_dir / inventory[required_name]
            if mapped_path.exists() and mapped_path.is_file():
                return mapped_path

        return None

    @staticmethod
    def find_test_dir(
        required_name: str,
        source_dir: Path,
        dir_aliases: Dict[str, List[str]],
        inventory: Optional[Dict[str, str]] = None
    ) -> Optional[Path]:
        """
        Find a test directory recursively in source_dir.

        Lookup order:
        1. Exact match anywhere under source_dir (recursive)
        2. Alias match anywhere under source_dir (recursive)
        3. Case-insensitive basename match (recursive)
        4. Inventory mapping (if inventory contains full relative paths)

        Args:
            required_name: Required directory name
            source_dir: Root directory to search in
            dir_aliases: Alias mappings for directories
            inventory: Optional inventory dict mapping canonical names to actual paths

        Returns:
            Path to found directory, or None if not found
        """
        if not source_dir.exists():
            return None

        # Tier 1: Exact match (recursive)
        for candidate in source_dir.rglob(required_name):
            if candidate.is_dir():
                return candidate

        # Tier 2: Alias lookup (recursive)
        aliases = dir_aliases.get(required_name, [])
        for alias in aliases:
            for candidate in source_dir.rglob(alias):
                if candidate.is_dir():
                    return candidate

        # Tier 3: Case-insensitive basename match (recursive)
        required_basename = required_name.lower()

        for candidate in source_dir.rglob("*"):
            if candidate.is_dir() and candidate.name.lower() == required_basename:
                return candidate

        # Tier 4: Inventory mapping (if provided)
        if inventory and required_name in inventory:
            mapped_path = source_dir / inventory[required_name]
            if mapped_path.exists() and mapped_path.is_dir():
                return mapped_path

        return None

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

    def check_test_data_availability(
        self,
        test_data_path: Path,
        runtime_config: RuntimeValidationConfig,
        inventory: Optional[Dict[str, str]] = None,
    ) -> Tuple[bool, List[str]]:
        """
        Check if required test data files and directories are available before runtime execution.

        This performs a pre-flight check to identify missing test data files/dirs
        that would cause runtime failures. If files/dirs are missing, the example
        should be marked as INFRA_MISSING_TEST_DATA rather than attempting
        runtime execution.

        Now uses RECURSIVE search to find files and directories in subdirectories.

        Args:
            test_data_path: Path to test data directory (e.g., test-data/zip/)
            runtime_config: Runtime validation configuration with required_files and required_dirs
            inventory: Optional inventory dict mapping canonical names to actual paths

        Returns:
            Tuple of (all_available, missing_items):
                - all_available: True if all required files and dirs exist
                - missing_items: List of missing file/dir names (empty if all available)
        """
        if not test_data_path.exists():
            # Test data directory doesn't exist - all files/dirs are missing
            all_required = runtime_config.required_files + runtime_config.required_dirs
            return (False, all_required)

        missing = []
        file_aliases = runtime_config.file_aliases

        # Check required files
        for required_file in runtime_config.required_files:
            # Use recursive helper to find file anywhere under test_data_path
            found = self.find_test_file(
                required_file,
                test_data_path,
                file_aliases,
                inventory
            )

            if found is None:
                missing.append(required_file)

        # Check required directories
        for required_dir in runtime_config.required_dirs:
            # Use recursive helper to find directory anywhere under test_data_path
            found = self.find_test_dir(
                required_dir,
                test_data_path,
                file_aliases,  # Reuse file_aliases for dirs (same alias map)
                inventory
            )

            if found is None:
                missing.append(required_dir)

        return (len(missing) == 0, missing)

    def _copy_test_data(
        self,
        source_dir: Path,
        work_dir: Path,
        runtime_config: RuntimeValidationConfig,
        inventory: Optional[Dict[str, str]] = None,
    ) -> None:
        """
        Copy required test data files and directories to workspace.

        Now uses RECURSIVE search to find files and directories in subdirectories,
        then copies them to workspace root under the required name.
        """
        required_files = runtime_config.required_files
        required_dirs = runtime_config.required_dirs
        file_aliases = runtime_config.file_aliases

        # First, copy all TOP-LEVEL files from source that might be needed
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

        # Then handle specific required files with RECURSIVE lookup
        for required_file in required_files:
            # Use recursive helper to find file anywhere under source_dir
            source_found = self.find_test_file(
                required_file,
                source_dir,
                file_aliases,
                inventory
            )

            if source_found:
                # Copy to workspace root under the required name
                # (so snippets referencing simple filenames work)
                dst_path = work_dir / required_file
                if not dst_path.exists():
                    shutil.copy2(source_found, dst_path)

                # Create alias copies (so code using aliases also works)
                aliases = file_aliases.get(required_file, [])
                for alias in aliases:
                    alias_dst = work_dir / alias
                    if not alias_dst.exists():
                        shutil.copy2(source_found, alias_dst)

        # Handle specific required directories with RECURSIVE lookup
        for required_dir in required_dirs:
            # Use recursive helper to find directory anywhere under source_dir
            source_found = self.find_test_dir(
                required_dir,
                source_dir,
                file_aliases,  # Reuse file_aliases for dirs (same alias map)
                inventory
            )

            if source_found:
                # Copy to workspace root under the required name
                dst_path = work_dir / required_dir
                if not dst_path.exists():
                    shutil.copytree(source_found, dst_path)

                # Create alias copies (so code using aliases also works)
                aliases = file_aliases.get(required_dir, [])
                for alias in aliases:
                    alias_dst = work_dir / alias
                    if not alias_dst.exists():
                        shutil.copytree(source_found, alias_dst)
    
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
            stack_trace = None

            if run_result.returncode != 0:
                exception_type, exception_message, stack_trace = self._parse_exception(
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
                stack_trace=stack_trace,
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
        for api_class in self.namespace_map.keys():
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
            if api_class in self.namespace_map:
                namespace = self.namespace_map[api_class]
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

            # If no Main method exists, inject one at the end
            if not analysis['has_main'] and not analysis.get('is_top_level', False):
                lines.append("")
                lines.append("// Injected entry point for runtime execution")
                lines.append("public class Program")
                lines.append("{")
                lines.append("    public static void Main(string[] args)")
                lines.append("    {")
                lines.append("        // Entry point - code executed from namespace classes")
                lines.append("    }")
                lines.append("}")

            return '\n'.join(lines)

        # Strategy 2: Code has class but no namespace
        if analysis['has_class']:
            # Add usings
            all_usings = list(set(self.DEFAULT_USINGS + (family_config.code_defaults.default_usings if family_config.code_defaults else [])))
            if analysis['detected_apis']:
                for api in analysis['detected_apis']:
                    if api in self.namespace_map:
                        all_usings.append(self.namespace_map[api])

            if not analysis['has_usings']:
                for using in sorted(set(all_usings)):
                    lines.append(f"using {using};")
                lines.append("")

            lines.append(code)

            # If no Main method exists, inject Program.Main wrapper
            if not analysis['has_main'] and not analysis.get('is_top_level', False):
                lines.append("")
                lines.append("// Injected entry point for runtime execution")
                lines.append("public class Program")
                lines.append("{")
                lines.append("    public static void Main(string[] args)")
                lines.append("    {")
                lines.append("        // Entry point - instantiate and use classes above")
                lines.append("    }")
                lines.append("}")

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
            if api in self.namespace_map:
                all_usings.add(self.namespace_map[api])

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
            # Sort glob results deterministically (case-normalized for Windows compatibility)
            matches = sorted(work_dir.glob(pattern), key=lambda p: str(p).lower())
            output_files.extend(str(m.relative_to(work_dir)) for m in matches)

        # Sort final output list deterministically
        return sorted(output_files, key=lambda f: f.lower())
    
    def _parse_exception(self, output: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Parse exception information from output including multi-line messages and stack traces.

        Returns:
            Tuple of (exception_type, exception_message, stack_trace)
        """
        # Look for common .NET exception patterns
        import re

        # Pattern 1: Unhandled exception. System.SomeException: Message (with multi-line capture)
        # Use DOTALL to match across lines, stop at "at" for stack trace boundary
        match = re.search(
            r'Unhandled exception[.:]\s*([A-Za-z.]+Exception):\s*(.+?)(?=\n\s+at\s|\Z)',
            output,
            re.DOTALL
        )
        if match:
            exception_type = match.group(1)
            exception_message = match.group(2).strip()

            # Extract stack trace separately
            stack_trace = None
            stack_match = re.search(r'(\n\s+at\s.+)', output[match.start():], re.DOTALL)
            if stack_match:
                # Extract just the first 5 lines of stack trace for brevity
                stack_lines = stack_match.group(1).split('\n')[:5]
                stack_trace = '\n'.join(stack_lines).strip()

            return exception_type, exception_message, stack_trace

        # Pattern 2: System.SomeException: Message (with multi-line capture)
        match = re.search(
            r'([A-Za-z.]+Exception):\s*(.+?)(?=\n\s+at\s|\Z)',
            output,
            re.DOTALL
        )
        if match:
            exception_type = match.group(1)
            exception_message = match.group(2).strip()

            # Extract stack trace separately
            stack_trace = None
            stack_match = re.search(r'(\n\s+at\s.+)', output[match.start():], re.DOTALL)
            if stack_match:
                # Extract just the first 5 lines of stack trace for brevity
                stack_lines = stack_match.group(1).split('\n')[:5]
                stack_trace = '\n'.join(stack_lines).strip()

            return exception_type, exception_message, stack_trace

        return None, None, None
    
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
        run_id: Optional[str] = None,
    ) -> str:
        """
        Record a runtime attempt in the database.

        Args:
            example_id: Example ID
            family: Family identifier
            runtime_result: Runtime execution result
            sample_ref: Test data reference
            scenario: Execution scenario
            retrieved_examples: Retrieved example IDs (optional)
            llm_request: LLM request (optional)
            llm_response: LLM response (optional)
            run_id: Run ID for run-scoped tracking (optional)

        Returns:
            Attempt ID
        """
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

        self.db.save_runtime_attempt(attempt, run_id=run_id)
        return attempt_id
    
    def _store_artifact(self, filename: str, content: str) -> str:
        """Store an artifact file and return its reference."""
        artifact_path = self.artifacts_dir / filename
        artifact_path.write_text(content, encoding='utf-8')
        return str(artifact_path)

    def classify_runtime_error(self, result: RuntimeResult) -> str:
        """
        Task 5: Classify runtime failure into deterministic categories.

        Categories:
        - missing_rar_file: RAR file not found (infra blocked)
        - missing_file: File not found
        - missing_directory: Directory not found
        - disposed_stream: Stream disposed prematurely
        - invalid_password: Password/encryption error
        - unhandled_exception: Other exception

        Args:
            result: Runtime execution result

        Returns:
            Error category string
        """
        error_text = (result.stderr or "") + (result.exception_message or "")
        error_lower = error_text.lower()

        # Task 5: Check for missing RAR file specifically (infra blocked)
        if "filenotfound" in error_lower or "could not find file" in error_lower:
            if ".rar" in error_lower:
                return "missing_rar_file"
            return "missing_file"

        if "directorynotfound" in error_lower or "could not find a part of the path" in error_lower:
            return "missing_directory"

        if "disposed" in error_lower or "cannot access a closed" in error_lower:
            return "disposed_stream"

        if "password" in error_lower or "decrypt" in error_lower or "invalid password" in error_lower:
            return "invalid_password"

        # Task 5: Detect 7z format incompatibility issues
        if "wrong compression method" in error_lower or "encoded header" in error_lower:
            return "sevenz_format_issue"

        return "unhandled_exception"

    def apply_deterministic_fix(
        self,
        code: str,
        error_category: str,
        test_data_files: List[str],
    ) -> Optional[str]:
        """
        Task 5: Apply deterministic patches for common runtime failures.

        Patches:
        - missing_directory: Add Directory.CreateDirectory() calls
        - missing_file: Replace file paths with available test data
        - disposed_stream: Ensure proper using/dispose patterns

        Args:
            code: Original code
            error_category: Classified error category
            test_data_files: Available test data file names

        Returns:
            Patched code or None if no fix applicable
        """
        if error_category == "missing_directory":
            # Add Directory.CreateDirectory for output paths
            patched = code

            # Find all string paths in the code that might be directories
            # Look for patterns that are likely to be output directories
            dir_patterns = [
                r'"([^"]+)"',  # Double-quoted strings
                r'@"([^"]+)"',  # Verbatim strings
            ]

            found_dirs = set()
            for pattern in dir_patterns:
                matches = re.findall(pattern, code)
                for match in matches:
                    # Check if it looks like a directory path
                    # Skip file names (have extension) and URLs
                    if match.startswith("http") or match.startswith("www"):
                        continue
                    # Skip if it has a common file extension
                    if re.search(r'\.(zip|rar|7z|gz|txt|cs|dll|exe|json|xml|png|jpg|pdf|doc)$', match, re.IGNORECASE):
                        continue
                    # If it's a path-like string (contains folder separator or is a folder name)
                    if "_folder" in match.lower() or "_dir" in match.lower() or match.endswith("/") or match.endswith("\\"):
                        found_dirs.add(match)
                    elif "output" in match.lower() or "extracted" in match.lower() or "destination" in match.lower():
                        found_dirs.add(match)
                    elif "source" in match.lower() or "input" in match.lower():
                        # Input directories also need to exist (might be created for copying)
                        found_dirs.add(match)

            # Add CreateDirectory calls for found directories
            if found_dirs:
                create_calls = []
                for dir_path in sorted(found_dirs):  # Sort for determinism
                    create_calls.append(f'        Directory.CreateDirectory(@"{dir_path}");')

                # Find the Main method and insert after the opening brace
                lines = patched.split('\n')
                insert_line_idx = None
                for i, line in enumerate(lines):
                    # Look for Main method signature
                    if re.search(r'\b(?:static\s+)?(?:async\s+)?(?:void|Task|int)\s+Main\s*\(', line):
                        # Find the opening brace
                        for j in range(i, min(i + 5, len(lines))):
                            if '{' in lines[j]:
                                insert_line_idx = j + 1
                                break
                        break

                if insert_line_idx is not None:
                    # Get indentation from the line after brace
                    base_indent = "        "  # Default 2 levels
                    if insert_line_idx < len(lines) and lines[insert_line_idx].strip():
                        # Detect existing indentation
                        existing_line = lines[insert_line_idx]
                        base_indent = existing_line[:len(existing_line) - len(existing_line.lstrip())]

                    # Insert directory creation calls with proper indentation
                    create_block = [base_indent + call.strip() for call in create_calls]
                    create_block.append('')  # Add blank line after creates
                    lines = lines[:insert_line_idx] + create_block + lines[insert_line_idx:]
                    patched = '\n'.join(lines)

            if patched != code:
                return patched

        elif error_category == "missing_file":
            # Replace placeholder file paths with actual test data
            if test_data_files:
                patched = code

                # Find a suitable zip file for substitution
                zip_files = [f for f in test_data_files if f.endswith('.zip')]
                txt_files = [f for f in test_data_files if f.endswith('.txt')]
                gz_files = [f for f in test_data_files if f.endswith('.gz')]
                sevenz_files = [f for f in test_data_files if f.endswith('.7z')]

                # Replace common placeholders based on file type
                replacements = []

                # ZIP file replacements
                if zip_files:
                    zip_sub = zip_files[0]
                    replacements.extend([
                        (r'"sample\.zip"', f'"{zip_sub}"'),
                        (r'"input\.zip"', f'"{zip_sub}"'),
                        (r'"archive\.zip"', f'"{zip_sub}"'),
                        (r'"test\.zip"', f'"{zip_sub}"'),
                    ])

                # Text file replacements
                if txt_files:
                    txt_sub = txt_files[0]
                    replacements.extend([
                        (r'"sample\.txt"', f'"{txt_sub}"'),
                        (r'"input\.txt"', f'"{txt_sub}"'),
                        (r'"data\.txt"', f'"{txt_sub}"'),
                    ])

                # 7z file replacements
                if sevenz_files:
                    sevenz_sub = sevenz_files[0]
                    replacements.extend([
                        (r'"archive\.7z"', f'"{sevenz_sub}"'),
                        (r'"input\.7z"', f'"{sevenz_sub}"'),
                    ])

                # GZ file replacements
                if gz_files:
                    gz_sub = gz_files[0]
                    replacements.extend([
                        (r'"sample\.gz"', f'"{gz_sub}"'),
                        (r'"archive\.gz"', f'"{gz_sub}"'),
                    ])

                for old_pattern, new_val in replacements:
                    if re.search(old_pattern, patched, re.IGNORECASE):
                        patched = re.sub(old_pattern, new_val, patched, flags=re.IGNORECASE)

                if patched != code:
                    return patched

        elif error_category == "disposed_stream":
            # Fix disposed stream issues by ensuring proper using patterns
            patched = code

            # Pattern 1: Stream is used after using block
            # Look for: using (var ms = new MemoryStream()) { ... } followed by ms.usage
            # Fix: Remove using or materialize bytes before disposal

            # Pattern 2: Stream passed to method that disposes it, then reused
            # Look for: stream.CopyTo() or similar, then stream used again
            # Fix: Create new stream from bytes

            # Simple heuristic: If we see MemoryStream with using, suggest removing using
            if "using" in code and "MemoryStream" in code:
                # Try to detect if stream is used after using block
                lines = code.split('\n')
                patched_lines = []
                in_using_block = False
                stream_var_name = None

                for i, line in enumerate(lines):
                    # Detect: using (var ms = new MemoryStream(...))
                    using_match = re.search(r'using\s*\(\s*var\s+(\w+)\s*=\s*new\s+MemoryStream', line)
                    if using_match:
                        stream_var_name = using_match.group(1)
                        # Remove 'using' keyword, keep the rest as variable declaration
                        modified = re.sub(r'using\s*\(\s*', '', line)
                        # Remove closing paren if it's on same line
                        modified = re.sub(r'\)\s*$', ';', modified)
                        patched_lines.append(modified)
                        in_using_block = True
                        continue

                    patched_lines.append(line)

                if stream_var_name and in_using_block:
                    patched = '\n'.join(patched_lines)
                    # Add a comment explaining the fix
                    patched = patched.replace(
                        f"var {stream_var_name} = new MemoryStream",
                        f"// Fixed: Removed 'using' to prevent early disposal\n        var {stream_var_name} = new MemoryStream"
                    )
                    return patched

            # Pattern 3: CopyTo disposes source stream
            # Add .ToArray() before disposal if MemoryStream
            if "CopyTo" in code and "MemoryStream" in code:
                # This is complex, let LLM handle
                return None

            return None  # Let LLM handle complex stream issues

        elif error_category == "unhandled_exception":
            # Check if it's actually an InvalidOperationException
            # This often indicates API misuse - try example substitution instead
            return None  # Let example substitution or LLM handle

        return None  # No fix applicable
