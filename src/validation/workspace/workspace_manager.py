"""
Workspace Manager for Example Review System.
Manages .NET workspaces for compiling code snippets.
"""

import hashlib
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Dict, List, Tuple

from src.core.config_utils import normalize_family_config


class WorkspaceManager:
    """
    Manages .NET workspaces for code compilation.
    """

    def __init__(self, workspaces_root: Path, family_config: Dict):
        """
        Initialize workspace manager.

        Args:
            workspaces_root: Root directory for workspaces
            family_config: Family configuration dictionary (will be normalized)
        """
        self.workspaces_root = workspaces_root
        # Normalize config to ensure canonical format
        self.family_config = normalize_family_config(family_config)
        self.family = self.family_config.get('family', '')
        self.workspace_dir = workspaces_root / self.family
        self.validator_dir = self.workspace_dir / "validator"
        self.nuget_packages_dir = self.workspace_dir / "nuget-packages"
        self.build_cache_dir = self.workspace_dir / "build-cache"
        self.build_stamp_path = self.build_cache_dir / ".build-stamp"

    def setup_workspace(self) -> bool:
        """
        Set up .NET workspace for compilation.

        Returns:
            True if successful, False otherwise
        """
        try:
            # Create workspace directories
            self.workspace_dir.mkdir(parents=True, exist_ok=True)
            self.validator_dir.mkdir(parents=True, exist_ok=True)
            self.nuget_packages_dir.mkdir(parents=True, exist_ok=True)
            self.build_cache_dir.mkdir(parents=True, exist_ok=True)

            # Create .NET project if it doesn't exist
            csproj_path = self.validator_dir / "Validator.csproj"
            if not csproj_path.exists():
                self._create_validator_project()

            # Restore NuGet packages
            self._restore_packages()

            return True

        except Exception as e:
            print(f"[!] Failed to setup workspace: {e}")
            return False

    def _create_validator_project(self):
        """Create validator .NET project."""
        nuget_config = self.family_config.get('nuget_config', {})
        primary_package = nuget_config.get('primary_package', {})
        package_name = primary_package.get('name', 'Aspose.Zip')

        # Determine package version from config
        version_strategy = primary_package.get('version_strategy', 'latest_stable')
        if version_strategy == 'pinned':
            package_version = primary_package.get('pinned_version', '*')
        else:
            package_version = primary_package.get('version', '*')

        target_framework = nuget_config.get('target_frameworks', ['net8.0'])[0]

        # Get additional packages
        additional_packages = nuget_config.get('additional_packages', [])

        # Build package references
        package_refs = f'    <PackageReference Include="{package_name}" Version="{package_version}" />\n'
        for pkg in additional_packages:
            pkg_name = pkg.get('name', '')
            pkg_version = pkg.get('version', '*')
            if pkg_name:
                package_refs += f'    <PackageReference Include="{pkg_name}" Version="{pkg_version}" />\n'

        package_refs += '    <PackageReference Include="Microsoft.CodeAnalysis.CSharp" Version="4.8.0" />'

        csproj_content = f"""<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <OutputType>Exe</OutputType>
    <TargetFramework>{target_framework}</TargetFramework>
    <LangVersion>latest</LangVersion>
    <Nullable>enable</Nullable>
  </PropertyGroup>

  <ItemGroup>
{package_refs}
  </ItemGroup>
</Project>
"""

        csproj_path = self.validator_dir / "Validator.csproj"
        with open(csproj_path, 'w', encoding='utf-8') as f:
            f.write(csproj_content)

        # Create Program.cs with dynamic assembly scanning
        program_content = """using System;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Collections.Generic;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.Emit;

class Program
{
    static int Main(string[] args)
    {
        if (args.Length == 0)
        {
            Console.WriteLine("Usage: Validator <code-file>");
            return 1;
        }

        string codeFile = args[0];
        if (!File.Exists(codeFile))
        {
            Console.WriteLine($"File not found: {codeFile}");
            return 1;
        }

        string code = File.ReadAllText(codeFile);

        bool success = ValidateCode(code);
        return success ? 0 : 1;
    }

    static bool ValidateCode(string code)
    {
        // Wrap code in namespace/class if needed
        string fullCode = WrapCode(code);

        var syntaxTree = CSharpSyntaxTree.ParseText(fullCode);

        // Get references
        var references = new List<MetadataReference>();

        // Add basic references
        references.Add(MetadataReference.CreateFromFile(typeof(object).Assembly.Location));
        references.Add(MetadataReference.CreateFromFile(typeof(Console).Assembly.Location));
        references.Add(MetadataReference.CreateFromFile(typeof(File).Assembly.Location));
        references.Add(MetadataReference.CreateFromFile(Assembly.Load("System.Runtime").Location));
        references.Add(MetadataReference.CreateFromFile(Assembly.Load("System.Collections").Location));
        references.Add(MetadataReference.CreateFromFile(Assembly.Load("netstandard").Location));

        // Scan NuGet packages directory for DLL assemblies
        var nugetPackagesDir = Path.Combine(
            Directory.GetCurrentDirectory(),
            "..", "..", "..", "..", "nuget-packages"
        );

        if (Directory.Exists(nugetPackagesDir))
        {
            var dllFiles = Directory.GetFiles(nugetPackagesDir, "*.dll", SearchOption.AllDirectories)
                .Where(f => f.Contains("\\\\lib\\\\") || f.Contains("/lib/"));

            foreach (var dllPath in dllFiles)
            {
                try
                {
                    references.Add(MetadataReference.CreateFromFile(dllPath));
                }
                catch
                {
                    // Skip invalid DLLs
                }
            }
        }

        // Detect if code has a Main method to determine output kind
        var hasMainMethod = code.Contains("static void Main") ||
                           code.Contains("static int Main") ||
                           code.Contains("static async Task Main") ||
                           code.Contains("static async Task<int> Main");

        var outputKind = hasMainMethod ? OutputKind.ConsoleApplication : OutputKind.DynamicallyLinkedLibrary;

        var compilation = CSharpCompilation.Create(
            "ValidationAssembly",
            syntaxTrees: new[] { syntaxTree },
            references: references,
            options: new CSharpCompilationOptions(outputKind)
        );

        using var ms = new MemoryStream();
        EmitResult result = compilation.Emit(ms);

        if (!result.Success)
        {
            var errors = result.Diagnostics
                .Where(d => d.Severity == DiagnosticSeverity.Error)
                .ToList();

            Console.WriteLine($"ERRORS: {errors.Count}");
            foreach (var error in errors)
            {
                Console.WriteLine($"{error.Id}: {error.GetMessage()}");
            }
            return false;
        }

        Console.WriteLine("SUCCESS");
        return true;
    }

    static string WrapCode(string code)
    {
        // Check if code already has complete structure (namespace + class)
        bool hasNamespace = code.Contains("namespace ");
        bool hasClass = code.Contains("class ") || code.Contains("static class ");

        // If code is a complete library class, just ensure it has using statements
        if (hasClass && !hasNamespace)
        {
            // Library code (class without namespace) - add using statements if missing
            if (!code.Contains("using System;"))
            {
                return $@"using System;
using System.IO;
using System.Collections.Generic;
using System.Linq;
__DEFAULT_USINGS__

{code}";
            }
            return code;
        }

        // If has both namespace and class, return as-is (complete code)
        if (hasNamespace && hasClass)
        {
            return code;
        }

        // Extract using directives from snippet
        var additionalUsings = new System.Collections.Generic.HashSet<string>();
        var codeLines = new System.Collections.Generic.List<string>();

        foreach (var line in code.Split(new[] { '\\r', '\\n' }, System.StringSplitOptions.RemoveEmptyEntries))
        {
            var trimmedLine = line.Trim();

            // Check if line is a using directive (not a using statement)
            if (trimmedLine.StartsWith("using ") && trimmedLine.EndsWith(";") && !trimmedLine.Contains("("))
            {
                // Extract using directive
                additionalUsings.Add(trimmedLine);
            }
            else if (!string.IsNullOrWhiteSpace(trimmedLine))
            {
                // Keep non-using code
                codeLines.Add(line);
            }
        }

        // Build additional usings string
        var additionalUsingsStr = string.Join("\\n", additionalUsings);
        var remainingCode = string.Join("\\n", codeLines);

        // Wrap code with standard usings + extracted usings
        return $@"
using System;
using System.IO;
using System.Collections.Generic;
using System.Linq;
using System.Text;
__DEFAULT_USINGS__
{additionalUsingsStr}

namespace ValidationNamespace
{{
    class ValidationClass
    {{
        static void Main()
        {{
            {remainingCode}
        }}
    }}
}}
";
    }
}
"""

        # Inject default usings from config
        default_usings = self.family_config.get('code_defaults', {}).get('default_usings', [])
        if default_usings:
            using_statements = '\n'.join(f'using {using};' for using in default_usings)
        else:
            using_statements = ''

        program_content = program_content.replace('__DEFAULT_USINGS__', using_statements)

        program_path = self.validator_dir / "Program.cs"
        with open(program_path, 'w', encoding='utf-8') as f:
            f.write(program_content)

    def _restore_packages(self):
        """Restore NuGet packages with per-family isolation."""
        try:
            # Use per-family NuGet packages directory
            result = subprocess.run(
                ["dotnet", "restore", "--packages", str(self.nuget_packages_dir)],
                cwd=str(self.validator_dir),
                capture_output=True,
                text=True,
                timeout=300  # Increased from 120s to 300s for Azure packages
            )

            if result.returncode != 0:
                print(f"[!] NuGet restore failed: {result.stderr}")
                return False

            return True

        except Exception as e:
            print(f"[!] Failed to restore packages: {e}")
            return False

    def _compute_build_stamp(self) -> str:
        """
        Compute build stamp hash from csproj and Program.cs content.

        The build stamp is used to determine if the validator needs to be rebuilt.
        It is computed by hashing the content of both the csproj file and Program.cs.

        Returns:
            SHA256 hash of the build inputs
        """
        csproj_path = self.validator_dir / "Validator.csproj"
        program_path = self.validator_dir / "Program.cs"

        hasher = hashlib.sha256()

        # Hash csproj content
        if csproj_path.exists():
            with open(csproj_path, 'rb') as f:
                hasher.update(f.read())

        # Hash Program.cs content
        if program_path.exists():
            with open(program_path, 'rb') as f:
                hasher.update(f.read())

        return hasher.hexdigest()

    def _needs_rebuild(self) -> bool:
        """
        Check if validator needs to be rebuilt.

        Rebuild is needed if:
        1. Validator exe doesn't exist, OR
        2. Build stamp doesn't exist, OR
        3. Build stamp hash doesn't match current inputs

        Returns:
            True if rebuild is needed, False otherwise
        """
        # Check if validator exe exists
        validator_exe = self.validator_dir / "bin" / "Release" / "net8.0" / "Validator.exe"
        validator_dll = self.validator_dir / "bin" / "Release" / "net8.0" / "Validator.dll"

        if not validator_exe.exists() and not validator_dll.exists():
            return True

        # Check if build stamp exists
        if not self.build_stamp_path.exists():
            return True

        # Read current build stamp
        try:
            with open(self.build_stamp_path, 'r') as f:
                stored_hash = f.read().strip()
        except:
            return True

        # Compare with current inputs
        current_hash = self._compute_build_stamp()
        return stored_hash != current_hash

    def _save_build_stamp(self):
        """Save current build stamp to file."""
        try:
            current_hash = self._compute_build_stamp()
            with open(self.build_stamp_path, 'w') as f:
                f.write(current_hash)
        except Exception as e:
            print(f"[!] Failed to save build stamp: {e}")

    def validate_code(self, code: str) -> Tuple[bool, str, int]:
        """
        Validate code by compiling it.

        Args:
            code: Code to validate

        Returns:
            Tuple of (success, output, error_count)
        """
        # Create temp file for code
        with tempfile.NamedTemporaryFile(mode='w', suffix='.cs', delete=False, encoding='utf-8') as f:
            f.write(code)
            code_file = f.name

        try:
            # Only rebuild validator if necessary (based on build stamp)
            if self._needs_rebuild():
                build_result = subprocess.run(
                    ["dotnet", "build", "-c", "Release"],
                    cwd=str(self.validator_dir),
                    capture_output=True,
                    text=True,
                    timeout=60
                )

                if build_result.returncode != 0:
                    return False, f"Validator build failed: {build_result.stderr}", 1

                # Save build stamp after successful build
                self._save_build_stamp()

            # Run validator
            validator_exe = self.validator_dir / "bin" / "Release" / "net8.0" / "Validator.exe"
            if not validator_exe.exists():
                validator_exe = self.validator_dir / "bin" / "Release" / "net8.0" / "Validator.dll"

            if validator_exe.suffix == '.dll':
                cmd = ["dotnet", str(validator_exe), code_file]
            else:
                cmd = [str(validator_exe), code_file]

            result = subprocess.run(
                cmd,
                cwd=str(validator_exe.parent),
                capture_output=True,
                text=True,
                timeout=30
            )

            # Combine stdout and stderr with clear separation
            output_parts = []
            if result.stdout:
                output_parts.append(result.stdout)
            if result.stderr:
                output_parts.append(f"STDERR:\n{result.stderr}")

            output = '\n'.join(output_parts) if output_parts else ""

            # Parse output
            if "SUCCESS" in output:
                return True, output, 0
            elif "ERRORS:" in output:
                # Extract error count
                lines = output.split('\n')
                error_count = 0
                for line in lines:
                    if line.startswith("ERRORS:"):
                        try:
                            error_count = int(line.split(':')[1].strip())
                        except:
                            error_count = 1
                        break

                return False, output, error_count
            else:
                # No SUCCESS or ERRORS marker - likely a runtime error
                # Ensure we capture whatever output we have
                if not output:
                    output = f"Validation failed with no output. Return code: {result.returncode}"
                return False, output, 1

        except subprocess.TimeoutExpired:
            return False, "Compilation timeout", 1
        except Exception as e:
            return False, f"Validation error: {str(e)}", 1
        finally:
            # Clean up temp file
            try:
                Path(code_file).unlink()
            except:
                pass

    def extract_errors(self, output: str) -> List[str]:
        """
        Extract error messages from compiler output.

        Args:
            output: Compiler output

        Returns:
            List of error messages
        """
        errors = []
        lines = output.split('\n')

        for line in lines:
            line = line.strip()
            if line and not line.startswith('ERRORS:') and not line.startswith('SUCCESS'):
                # Check if it looks like an error message (CS#### format)
                if 'CS' in line or 'error' in line.lower():
                    errors.append(line)

        return errors
