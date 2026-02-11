"""
Context-specific build harness for compiling examples in their native app context.

Phase-2 Gate B: Compiles ASP.NET examples as ASP.NET projects instead of console apps.
"""

import logging
import re
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class ContextHarnessService:
    """
    Provides context-specific project scaffolding for compilation.

    Phase-2 Gate B: When enabled, creates proper ASP.NET projects for ASP.NET code
    instead of wrapping everything in console apps.
    """

    # ASP.NET Web SDK project template
    ASPNET_PROJECT_TEMPLATE = """<Project Sdk="Microsoft.NET.Sdk.Web">
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <ImplicitUsings>enable</ImplicitUsings>
    <Nullable>enable</Nullable>
  </PropertyGroup>
  <ItemGroup>
    <FrameworkReference Include="Microsoft.AspNetCore.App" />
{package_refs}
  </ItemGroup>
</Project>
"""

    # Console Exe project template
    CONSOLE_PROJECT_TEMPLATE = """<Project Sdk="Microsoft.NET.Sdk">
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

    # Library project template
    LIBRARY_PROJECT_TEMPLATE = """<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <ImplicitUsings>enable</ImplicitUsings>
    <Nullable>enable</Nullable>
    <OutputType>Library</OutputType>
  </PropertyGroup>
  <ItemGroup>
{package_refs}
  </ItemGroup>
</Project>
"""

    def __init__(self, enabled: bool = False):
        """
        Initialize context harness service.

        Args:
            enabled: Whether to use context-specific harnesses (default: False)
        """
        self.enabled = enabled

    def get_project_template(self, app_context: Optional[str], code: Optional[str] = None) -> str:
        """
        Get the appropriate project template for the app context.

        Args:
            app_context: Application context (console, aspnet_core_minimal, etc.)
            code: The wrapped code to analyze for controller detection (TASK-R8)

        Returns:
            Project template string
        """
        if not self.enabled or not app_context:
            # Default to console when disabled or context unknown
            return self.CONSOLE_PROJECT_TEMPLATE

        # TASK-R8: Detect controller-only ASP.NET code (no Main, no builder/app refs)
        if app_context and app_context.startswith('aspnet') and code:
            has_class = bool(re.search(r'\bclass\s+\w+', code))
            has_main = 'static void Main' in code or 'static int Main' in code
            has_builder = 'WebApplication.CreateBuilder' in code or 'app.' in code

            # Controller class without entry point -> use Library template
            if has_class and not has_main and not has_builder:
                logger.debug(f"TASK-R8: Detected controller-only code for {app_context}, using Library template")
                return self.LIBRARY_PROJECT_TEMPLATE

        # Map app_context to project template
        if app_context in ['aspnet_core_minimal', 'aspnet_core_mvc', 'aspnet_core_webapi']:
            return self.ASPNET_PROJECT_TEMPLATE
        elif app_context == 'library':
            return self.LIBRARY_PROJECT_TEMPLATE
        else:
            # Default to console for 'console' and 'unknown'
            return self.CONSOLE_PROJECT_TEMPLATE

    def get_code_wrapper_strategy(self, app_context: Optional[str]) -> str:
        """
        Get the code wrapping strategy for the app context.

        Args:
            app_context: Application context

        Returns:
            Strategy name: 'none', 'console', 'aspnet_minimal', 'library'
        """
        if not self.enabled or not app_context:
            return 'console'  # Default behavior

        if app_context in ['aspnet_core_minimal', 'aspnet_core_mvc', 'aspnet_core_webapi']:
            return 'aspnet_minimal'  # No wrapping needed for ASP.NET
        elif app_context == 'library':
            return 'library'  # Library wrapping (class-only)
        else:
            return 'console'  # Console wrapping (Main method)

    def should_add_main_wrapper(self, app_context: Optional[str]) -> bool:
        """
        Determine if code should be wrapped in a Main() method.

        Args:
            app_context: Application context

        Returns:
            True if Main wrapper should be added, False otherwise
        """
        if not self.enabled or not app_context:
            return True  # Default: wrap in Main

        # ASP.NET and library contexts don't need Main wrapper
        return app_context not in [
            'aspnet_core_minimal',
            'aspnet_core_mvc',
            'aspnet_core_webapi',
            'library'
        ]

    def get_additional_packages(self, app_context: Optional[str]) -> list:
        """
        Get additional NuGet packages required for the app context.

        Args:
            app_context: Application context

        Returns:
            List of package dictionaries with 'name' and 'version'
        """
        if not self.enabled or not app_context:
            return []

        # ASP.NET contexts automatically get Microsoft.AspNetCore.App via Web SDK
        # No additional packages needed - Web SDK includes everything
        return []

    def get_project_metadata(self, app_context: Optional[str]) -> Dict[str, Any]:
        """
        Get metadata about the project configuration for the app context.

        Args:
            app_context: Application context

        Returns:
            Dictionary with project metadata
        """
        if not self.enabled or not app_context:
            return {
                'sdk': 'Microsoft.NET.Sdk',
                'output_type': 'Exe',
                'requires_main': True,
                'is_web_project': False
            }

        if app_context in ['aspnet_core_minimal', 'aspnet_core_mvc', 'aspnet_core_webapi']:
            return {
                'sdk': 'Microsoft.NET.Sdk.Web',
                'output_type': None,  # Web SDK doesn't use OutputType
                'requires_main': False,
                'is_web_project': True
            }
        elif app_context == 'library':
            return {
                'sdk': 'Microsoft.NET.Sdk',
                'output_type': 'Library',
                'requires_main': False,
                'is_web_project': False
            }
        else:  # console or unknown
            return {
                'sdk': 'Microsoft.NET.Sdk',
                'output_type': 'Exe',
                'requires_main': True,
                'is_web_project': False
            }

    def wrap_code_for_context(
        self,
        code: str,
        app_context: Optional[str],
        has_usings: bool = False,
        has_namespace: bool = False,
        has_class: bool = False,
        has_main: bool = False
    ) -> str:
        """
        Wrap code appropriately for its app context.

        Args:
            code: Original code snippet
            app_context: Application context
            has_usings: Whether code already has using statements
            has_namespace: Whether code already has namespace
            has_class: Whether code already has class definition
            has_main: Whether code already has Main method

        Returns:
            Wrapped code ready for compilation
        """
        if not self.enabled or not app_context:
            # Default behavior: wrap as console app
            return code

        strategy = self.get_code_wrapper_strategy(app_context)

        if strategy == 'aspnet_minimal':
            has_builder = 'WebApplication.CreateBuilder' in code or 'WebApplicationBuilder' in code
            has_app_ref = 'app.' in code
            if has_builder:
                return code  # Complete snippet, use as-is
            elif has_app_ref:
                # Partial snippet: inject minimal builder boilerplate
                boilerplate = "var builder = WebApplication.CreateBuilder(args);\nvar app = builder.Build();\n\n"
                suffix = ""
                if 'app.Run()' not in code and 'app.Run(' not in code:
                    suffix = "\n\napp.Run();"
                return boilerplate + code + suffix
            else:
                return code  # Classified as ASP.NET but no obvious app refs

        elif strategy == 'library':
            # Library code should be class definitions
            # Minimal wrapping - ensure it's in a namespace if needed
            if has_namespace or has_class:
                return code
            else:
                # Wrap bare code in a class
                return f"""public class GeneratedHelper
{{
    public static void Execute()
    {{
{self._indent_code(code, 8)}
    }}
}}
"""

        else:  # console
            # Default console wrapping (handled by compilation service)
            return code

    def _indent_code(self, code: str, spaces: int) -> str:
        """Indent code by specified number of spaces."""
        indent = ' ' * spaces
        return '\n'.join(indent + line if line.strip() else line
                        for line in code.split('\n'))


def create_context_harness(enabled: bool = False) -> ContextHarnessService:
    """
    Factory function to create a context harness service.

    Args:
        enabled: Whether to enable context-specific harnesses

    Returns:
        ContextHarnessService instance
    """
    return ContextHarnessService(enabled=enabled)
