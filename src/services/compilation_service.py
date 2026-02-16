"""
Compilation Service for Example Reviewer Pipeline.
Implements Phase B: Compilation Verification Loop.
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

from ..core.models import (
    ExampleRecord, ExampleStatus, CompileAttempt, LLMFixPayload
)
from ..core.database import Database
from ..core.config import FamilyConfig

# Type hint for FamilyServiceRegistry (avoid circular imports)
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..pipeline.family_service_registry import FamilyServiceRegistry

try:
    from .context_harness_service import ContextHarnessService
except ImportError:
    ContextHarnessService = None

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

    # Error pattern recognition for targeted fixes
    ERROR_PATTERNS = {
        r"CS0246.*type.*'(\w+)'": "missing_type",  # Matches "could not be found" or "not found"
        r"CS0103.*name.*'(\w+)'": "undefined_variable",  # Matches various phrasings
        r"CS1002.*;.*expected": "missing_semicolon",
        r"CS1513.*}.*expected": "missing_brace",
        r"CS0029.*Cannot.*convert": "type_mismatch",
        r"CS0117.*does not contain": "member_not_found",
        r"CS1061.*does not contain.*definition": "member_not_found",
        r"CS0246.*namespace": "missing_namespace",
        r"CS8803.*Top-level statements": "top_level_statements_error",
    }
    
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
        family: str,
        registry: Optional['FamilyServiceRegistry'] = None,
        workspace_dir: Optional[Path] = None,
        artifacts_dir: Optional[Path] = None,
        context_harness: Optional['ContextHarnessService'] = None,
    ):
        """
        Initialize compilation service.

        Args:
            db: Database instance
            family: Product family identifier (e.g., 'zip', 'words')
            registry: FamilyServiceRegistry for family-aware service access (optional)
            workspace_dir: Working directory for compilation
            artifacts_dir: Directory for storing compilation artifacts
            context_harness: Context-specific build harness service (Phase-2 Gate B)
        """
        self.db = db
        self.family = family
        self.registry = registry
        self.workspace_dir = workspace_dir or Path(tempfile.gettempdir()) / "example_reviewer"
        self.artifacts_dir = artifacts_dir or self.workspace_dir / "artifacts"
        self.context_harness = context_harness

        # Load namespace map from registry if available, else use empty dict
        if registry:
            self.namespace_map = registry.get_namespace_map(family)
            logger.info(f"CompilationService({family}): loaded {len(self.namespace_map)} types from registry")
            if self.namespace_map:
                # Log first 5 entries for debugging
                sample = list(self.namespace_map.items())[:5]
                logger.info(f"CompilationService({family}): sample namespace_map entries: {sample}")
            else:
                logger.warning(f"CompilationService({family}): namespace_map is EMPTY despite registry being provided!")
        else:
            self.namespace_map = {}
            logger.info(f"CompilationService({family}): no registry provided, using empty namespace map")

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
            wrapped_code = self._wrap_code(code, family_config, app_context=example.app_context)

            # Write project files (with app_context for Phase-2 Gate B, wrapped_code for TASK-R8)
            self._write_project(work_dir, family_config, app_context=example.app_context, wrapped_code=wrapped_code)

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
    
    @staticmethod
    def _detect_entry_call(code: str) -> str:
        """Detect a public static void method (Run, Execute, etc.) and return a call statement.

        For .cs file examples (e.g. Aspose.PDF with Run(), Aspose.Words with test methods),
        this injects the actual method invocation into the generated Main() body.
        """
        # Find class name and a public static void method that isn't Main
        entry_match = re.search(
            r'(?:public\s+)?class\s+(\w+).*?public\s+static\s+void\s+(\w+)\s*\(\s*\)',
            code, re.DOTALL
        )
        if entry_match and entry_match.group(2) != 'Main':
            return f"        {entry_match.group(1)}.{entry_match.group(2)}();"
        return "        // Entry point"

    def _analyze_code(self, code: str, family_config: FamilyConfig) -> Dict[str, Any]:
        """
        Analyze code to determine its structure and what's missing.

        Returns:
            Dictionary with analysis results including detected APIs and missing elements
        """
        # Check for various code elements
        has_usings = bool(re.search(r'^\s*using\s+[\w\.]+\s*;', code, re.MULTILINE))
        has_namespace = bool(re.search(r'\bnamespace\s+[\w\.]+', code))
        has_class = any(
            re.search(r'\bclass\s+\w+', line.split('//')[0])
            for line in code.split('\n')
        )
        has_main = bool(re.search(r'\bstatic\s+(?:async\s+)?(?:void|Task|Task<int>|int)\s+Main\s*\(', code))
        is_async = bool(re.search(r'\bawait\s+', code)) or bool(re.search(r'\basync\s+', code))

        # Detect API usage by looking for class instantiations and references
        detected_apis = []
        for api_class in self.namespace_map.keys():
            # Look for: new ApiClass, ApiClass., ApiClass<, or just ApiClass as a type
            patterns = [
                rf'\bnew\s+{api_class}\b',
                rf'\b{api_class}\.',
                rf'\b{api_class}<',
                rf'<{api_class}>',
                rf'\({api_class}\s+\w+\)',  # Parameter: (ApiClass param)
            ]
            if any(re.search(pattern, code) for pattern in patterns):
                detected_apis.append(api_class)

        # Infer missing using statements
        missing_usings = self._infer_usings(code, family_config, detected_apis)

        # Check if code is complete (has all necessary structure)
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

    def _wrap_code(self, code: str, family_config: FamilyConfig, app_context: str = None) -> str:
        """
        Intelligently wrap code snippet in a compilable structure based on what's already present.

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

        # Context-aware wrapping: delegate to context_harness for non-console contexts
        if self.context_harness and app_context:
            if not self.context_harness.should_add_main_wrapper(app_context):
                wrapped = self.context_harness.wrap_code_for_context(
                    code, app_context,
                    has_usings=analysis['has_usings'],
                    has_namespace=analysis['has_namespace'],
                    has_class=analysis['has_class'],
                    has_main=analysis['has_main'],
                )
                # Still add missing usings
                if analysis['missing_usings']:
                    using_lines = [f"using {u};" for u in analysis['missing_usings']]
                    return '\n'.join(using_lines) + '\n\n' + wrapped
                return wrapped

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
                lines.append("// Injected entry point for compilation")
                lines.append("public class Program")
                lines.append("{")
                lines.append("    public static void Main(string[] args)")
                lines.append("    {")
                lines.append(self._detect_entry_call(code))
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
                lines.append("// Injected entry point for compilation")
                lines.append("public class Program")
                lines.append("{")
                lines.append("    public static void Main(string[] args)")
                lines.append("    {")
                lines.append(self._detect_entry_call(code))
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
        # Separate using statements from actual code
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
    
    def _write_project(
        self,
        work_dir: Path,
        family_config: FamilyConfig,
        app_context: Optional[str] = None,
        wrapped_code: Optional[str] = None
    ) -> None:
        """
        Write .csproj file for compilation.

        Args:
            work_dir: Working directory
            family_config: Family configuration
            app_context: Application context (Phase-2 Gate B)
            wrapped_code: The wrapped code for controller detection (TASK-R8)
        """
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

        # Phase-2 Gate B: Use context harness for project template if available
        if self.context_harness is not None:
            project_template = self.context_harness.get_project_template(app_context, code=wrapped_code)
            logger.debug(f"Using context-specific project template for app_context={app_context}")
        else:
            project_template = self.PROJECT_TEMPLATE
            logger.debug("Using default console project template")

        # Write project file
        project_content = project_template.format(
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

    def categorize_errors(self, errors: List[str]) -> Dict[str, List[str]]:
        """
        Categorize compilation errors for targeted fixes.

        Args:
            errors: List of error messages

        Returns:
            Dictionary mapping error categories to specific errors
        """
        categorized = {}

        for error in errors:
            categorized_flag = False
            for pattern, category in self.ERROR_PATTERNS.items():
                if re.search(pattern, error, re.IGNORECASE):
                    if category not in categorized:
                        categorized[category] = []
                    categorized[category].append(error)
                    categorized_flag = True
                    break

            # Uncategorized errors
            if not categorized_flag:
                if 'unknown' not in categorized:
                    categorized['unknown'] = []
                categorized['unknown'].append(error)

        return categorized

    def get_error_fix_hints(self, error_categories: Dict[str, List[str]], family_config: FamilyConfig) -> List[str]:
        """
        Get fix hints based on error categories.

        Args:
            error_categories: Categorized errors
            family_config: Family configuration

        Returns:
            List of fix hints
        """
        hints = []

        if 'missing_type' in error_categories:
            # Extract missing types
            missing_types = []
            for error in error_categories['missing_type']:
                match = re.search(r"type.*'(\w+)'", error)
                if match:
                    missing_types.append(match.group(1))

            # Suggest namespaces
            suggested_namespaces = set()
            for missing_type in missing_types:
                if missing_type in self.namespace_map:
                    suggested_namespaces.add(self.namespace_map[missing_type])

            if suggested_namespaces:
                hints.append(f"Add using statements: {', '.join(sorted(suggested_namespaces))}")

        if 'undefined_variable' in error_categories:
            hints.append("Declare variables before use or check for typos")

        if 'missing_semicolon' in error_categories:
            hints.append("Add missing semicolons")

        if 'missing_brace' in error_categories:
            hints.append("Check for missing closing braces")

        if 'type_mismatch' in error_categories:
            hints.append("Use explicit type casting or correct types")

        if 'top_level_statements_error' in error_categories:
            hints.append("Wrap code in class and Main method - top-level statements must come before other declarations")

        return hints
    
    def create_fix_payload(
        self,
        example: ExampleRecord,
        compile_result: CompileResult,
        family_config: Optional[FamilyConfig] = None,
        api_context: Optional[str] = None,
        similar_examples: Optional[List[str]] = None,
    ) -> LLMFixPayload:
        """
        Create payload for LLM-based code fixing with enhanced context.

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
        scaffolding_hints = []

        if family_config:
            if family_config.code_defaults:
                default_usings = family_config.code_defaults.default_usings
            if family_config.nuget_config and family_config.nuget_config.primary_package:
                nuget_package = family_config.nuget_config.primary_package.name

            # Categorize errors and generate hints
            error_categories = self.categorize_errors(compile_result.errors)
            fix_hints = self.get_error_fix_hints(error_categories, family_config)
            scaffolding_hints.extend(fix_hints)

            # Log error categories for debugging
            if error_categories:
                logger.info(f"Error categories for {example.example_id}: {list(error_categories.keys())}")

        return LLMFixPayload(
            code=example.compilable_code or example.original_code,
            errors=errors,
            context_type="compile",
            api_references=[api_context] if api_context else [],
            similar_examples=similar_examples or [],
            scaffolding_hints=scaffolding_hints,
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
        run_id: Optional[str] = None,
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
            run_id: Run ID for run-scoped tracking (optional)

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

        self.db.save_compile_attempt(attempt, run_id=run_id)
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
