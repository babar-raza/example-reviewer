"""
Tests for context harness service.

Tests that ContextHarnessService provides correct project templates
and build configurations for different app contexts.
"""

import pytest
from src.services.context_harness_service import ContextHarnessService, create_context_harness


class TestContextHarnessService:
    """Test context-specific project template selection."""

    def test_default_enabled_is_false(self):
        """Test that harness defaults to disabled"""
        harness = ContextHarnessService()
        assert harness.enabled is False

    def test_explicit_enabled_flag(self):
        """Test explicit enabled flag"""
        harness_disabled = ContextHarnessService(enabled=False)
        assert harness_disabled.enabled is False

        harness_enabled = ContextHarnessService(enabled=True)
        assert harness_enabled.enabled is True

    def test_console_project_template_when_disabled(self):
        """Test that console template is used when harness is disabled"""
        harness = ContextHarnessService(enabled=False)

        # Even with aspnet context, should return console template when disabled
        template = harness.get_project_template('aspnet_core_minimal')
        assert '<OutputType>Exe</OutputType>' in template
        assert 'Microsoft.NET.Sdk' in template
        assert 'Microsoft.NET.Sdk.Web' not in template

    def test_console_project_template_when_enabled_for_console(self):
        """Test console template for console context"""
        harness = ContextHarnessService(enabled=True)

        template = harness.get_project_template('console')
        assert '<OutputType>Exe</OutputType>' in template
        assert 'Microsoft.NET.Sdk' in template
        assert 'Microsoft.NET.Sdk.Web' not in template

    def test_aspnet_project_template_for_minimal(self):
        """Test ASP.NET Web SDK template for minimal hosting"""
        harness = ContextHarnessService(enabled=True)

        template = harness.get_project_template('aspnet_core_minimal')
        assert 'Microsoft.NET.Sdk.Web' in template
        assert '<OutputType>' not in template  # Web SDK doesn't use OutputType

    def test_aspnet_project_template_for_mvc(self):
        """Test ASP.NET Web SDK template for MVC"""
        harness = ContextHarnessService(enabled=True)

        template = harness.get_project_template('aspnet_core_mvc')
        assert 'Microsoft.NET.Sdk.Web' in template
        assert '<OutputType>' not in template

    def test_aspnet_project_template_for_webapi(self):
        """Test ASP.NET Web SDK template for Web API"""
        harness = ContextHarnessService(enabled=True)

        template = harness.get_project_template('aspnet_core_webapi')
        assert 'Microsoft.NET.Sdk.Web' in template
        assert '<OutputType>' not in template

    def test_library_project_template(self):
        """Test library template for library context"""
        harness = ContextHarnessService(enabled=True)

        template = harness.get_project_template('library')
        assert '<OutputType>Library</OutputType>' in template
        assert 'Microsoft.NET.Sdk' in template
        assert 'Microsoft.NET.Sdk.Web' not in template

    def test_unknown_context_defaults_to_console(self):
        """Test unknown context defaults to console template"""
        harness = ContextHarnessService(enabled=True)

        template = harness.get_project_template('unknown')
        assert '<OutputType>Exe</OutputType>' in template
        assert 'Microsoft.NET.Sdk' in template

    def test_null_context_defaults_to_console(self):
        """Test null context defaults to console template"""
        harness = ContextHarnessService(enabled=True)

        template = harness.get_project_template(None)
        assert '<OutputType>Exe</OutputType>' in template
        assert 'Microsoft.NET.Sdk' in template

    def test_wrapper_strategy_console(self):
        """Test wrapper strategy for console context"""
        harness = ContextHarnessService(enabled=True)

        strategy = harness.get_code_wrapper_strategy('console')
        assert strategy == 'console'

    def test_wrapper_strategy_aspnet_minimal(self):
        """Test wrapper strategy for ASP.NET contexts"""
        harness = ContextHarnessService(enabled=True)

        assert harness.get_code_wrapper_strategy('aspnet_core_minimal') == 'aspnet_minimal'
        assert harness.get_code_wrapper_strategy('aspnet_core_mvc') == 'aspnet_minimal'
        assert harness.get_code_wrapper_strategy('aspnet_core_webapi') == 'aspnet_minimal'

    def test_wrapper_strategy_library(self):
        """Test wrapper strategy for library context"""
        harness = ContextHarnessService(enabled=True)

        strategy = harness.get_code_wrapper_strategy('library')
        assert strategy == 'library'

    def test_wrapper_strategy_when_disabled(self):
        """Test wrapper strategy defaults to console when disabled"""
        harness = ContextHarnessService(enabled=False)

        # Even ASP.NET context should return 'console' when disabled
        strategy = harness.get_code_wrapper_strategy('aspnet_core_minimal')
        assert strategy == 'console'

    def test_should_add_main_wrapper_console(self):
        """Test Main wrapper required for console context"""
        harness = ContextHarnessService(enabled=True)

        assert harness.should_add_main_wrapper('console') is True

    def test_should_add_main_wrapper_aspnet(self):
        """Test Main wrapper not required for ASP.NET contexts"""
        harness = ContextHarnessService(enabled=True)

        assert harness.should_add_main_wrapper('aspnet_core_minimal') is False
        assert harness.should_add_main_wrapper('aspnet_core_mvc') is False
        assert harness.should_add_main_wrapper('aspnet_core_webapi') is False

    def test_should_add_main_wrapper_library(self):
        """Test Main wrapper not required for library context"""
        harness = ContextHarnessService(enabled=True)

        assert harness.should_add_main_wrapper('library') is False

    def test_should_add_main_wrapper_when_disabled(self):
        """Test Main wrapper always added when harness disabled"""
        harness = ContextHarnessService(enabled=False)

        # Even ASP.NET should require Main wrapper when disabled
        assert harness.should_add_main_wrapper('aspnet_core_minimal') is True

    def test_get_project_metadata_console(self):
        """Test project metadata for console context"""
        harness = ContextHarnessService(enabled=True)

        metadata = harness.get_project_metadata('console')
        assert metadata['sdk'] == 'Microsoft.NET.Sdk'
        assert metadata['output_type'] == 'Exe'
        assert metadata['requires_main'] is True
        assert metadata['is_web_project'] is False

    def test_get_project_metadata_aspnet_minimal(self):
        """Test project metadata for ASP.NET minimal context"""
        harness = ContextHarnessService(enabled=True)

        metadata = harness.get_project_metadata('aspnet_core_minimal')
        assert metadata['sdk'] == 'Microsoft.NET.Sdk.Web'
        assert metadata['output_type'] is None  # Web SDK doesn't use OutputType
        assert metadata['requires_main'] is False
        assert metadata['is_web_project'] is True

    def test_get_project_metadata_library(self):
        """Test project metadata for library context"""
        harness = ContextHarnessService(enabled=True)

        metadata = harness.get_project_metadata('library')
        assert metadata['sdk'] == 'Microsoft.NET.Sdk'
        assert metadata['output_type'] == 'Library'
        assert metadata['requires_main'] is False
        assert metadata['is_web_project'] is False

    def test_get_additional_packages_aspnet(self):
        """Test that ASP.NET contexts don't need additional packages"""
        harness = ContextHarnessService(enabled=True)

        # Web SDK includes Microsoft.AspNetCore.App automatically
        packages = harness.get_additional_packages('aspnet_core_minimal')
        assert packages == []

    def test_get_additional_packages_console(self):
        """Test that console contexts don't need additional packages"""
        harness = ContextHarnessService(enabled=True)

        packages = harness.get_additional_packages('console')
        assert packages == []

    def test_wrap_code_for_aspnet_context(self):
        """Test that ASP.NET code is not wrapped (compiled as-is)"""
        harness = ContextHarnessService(enabled=True)

        original_code = """var builder = WebApplication.CreateBuilder(args);
var app = builder.Build();
app.Run();"""

        wrapped = harness.wrap_code_for_context(
            code=original_code,
            app_context='aspnet_core_minimal'
        )

        # ASP.NET code should be returned unchanged
        assert wrapped == original_code

    def test_wrap_code_for_library_with_class(self):
        """Test that library code with class is not wrapped"""
        harness = ContextHarnessService(enabled=True)

        original_code = """public class Helper {
    public void DoWork() { }
}"""

        wrapped = harness.wrap_code_for_context(
            code=original_code,
            app_context='library',
            has_class=True
        )

        # Code with class should be returned unchanged
        assert wrapped == original_code

    def test_wrap_code_for_library_without_class(self):
        """Test that library code without class gets minimal wrapping"""
        harness = ContextHarnessService(enabled=True)

        original_code = "int x = 42;"

        wrapped = harness.wrap_code_for_context(
            code=original_code,
            app_context='library',
            has_class=False
        )

        # Should wrap in a class
        assert 'public class GeneratedHelper' in wrapped
        assert 'public static void Execute()' in wrapped
        assert original_code in wrapped

    def test_wrap_code_when_disabled(self):
        """Test that code is returned unchanged when harness disabled"""
        harness = ContextHarnessService(enabled=False)

        original_code = "var builder = WebApplication.CreateBuilder(args);"

        wrapped = harness.wrap_code_for_context(
            code=original_code,
            app_context='aspnet_core_minimal'
        )

        # When disabled, return code unchanged (default behavior)
        assert wrapped == original_code

    def test_factory_function(self):
        """Test create_context_harness factory function"""
        harness_disabled = create_context_harness(enabled=False)
        assert harness_disabled.enabled is False

        harness_enabled = create_context_harness(enabled=True)
        assert harness_enabled.enabled is True

    def test_indent_code_helper(self):
        """Test code indentation helper"""
        harness = ContextHarnessService(enabled=True)

        code = "line1\nline2\nline3"
        indented = harness._indent_code(code, 4)

        lines = indented.split('\n')
        assert lines[0] == '    line1'
        assert lines[1] == '    line2'
        assert lines[2] == '    line3'

    def test_template_has_package_refs_placeholder(self):
        """Test that all templates have package_refs placeholder"""
        harness = ContextHarnessService(enabled=True)

        # Console template
        console_template = harness.CONSOLE_PROJECT_TEMPLATE
        assert '{package_refs}' in console_template

        # ASP.NET template
        aspnet_template = harness.ASPNET_PROJECT_TEMPLATE
        assert '{package_refs}' in aspnet_template

        # Library template
        library_template = harness.LIBRARY_PROJECT_TEMPLATE
        assert '{package_refs}' in library_template

    def test_all_templates_have_net8_target(self):
        """Test that all templates target .NET 8"""
        harness = ContextHarnessService(enabled=True)

        assert '<TargetFramework>net8.0</TargetFramework>' in harness.CONSOLE_PROJECT_TEMPLATE
        assert '<TargetFramework>net8.0</TargetFramework>' in harness.ASPNET_PROJECT_TEMPLATE
        assert '<TargetFramework>net8.0</TargetFramework>' in harness.LIBRARY_PROJECT_TEMPLATE


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
