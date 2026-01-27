"""
Tests for context drift validator.

Tests that ContextDriftValidator correctly detects and prevents
app_context changes during LLM fix attempts.
"""

import pytest
from src.pipeline.context_drift_validator import (
    ContextDriftValidator,
    ContextDriftResult,
    validate_context_drift
)


class TestContextDriftValidator:
    """Test context drift detection and rejection."""

    def test_drift_detected_console_to_aspnet(self):
        """Test drift detection when LLM changes console → ASP.NET"""
        validator = ContextDriftValidator(enabled=True)

        original_code = """
using Aspose.Zip;

var archive = new Archive();
archive.CreateEntry("file.txt", "data.txt");
archive.Save("output.zip");
"""

        fixed_code = """
using Microsoft.AspNetCore.Builder;
using Aspose.Zip;

var builder = WebApplication.CreateBuilder(args);
var app = builder.Build();

app.MapGet("/create-zip", () => {
    var archive = new Archive();
    archive.CreateEntry("file.txt", "data.txt");
    archive.Save("output.zip");
    return Results.Ok();
});

app.Run();
"""

        result = validator.validate(
            original_code=original_code,
            fixed_code=fixed_code,
            original_context="console"
        )

        assert result.drift_detected is True
        assert result.original_context == "console"
        assert result.fixed_context == "aspnet_core_minimal"
        assert result.should_reject is True
        assert result.rejection_reason is not None

    def test_drift_detected_aspnet_to_console(self):
        """Test drift detection when LLM changes ASP.NET → console"""
        validator = ContextDriftValidator(enabled=True)

        original_code = """
using Microsoft.AspNetCore.Builder;

var builder = WebApplication.CreateBuilder(args);
var app = builder.Build();

app.MapGet("/", () => "Hello World!");
app.Run();
"""

        fixed_code = """
using System;

class Program
{
    static void Main(string[] args)
    {
        Console.WriteLine("Hello World!");
    }
}
"""

        result = validator.validate(
            original_code=original_code,
            fixed_code=fixed_code,
            original_context="aspnet_core_minimal"
        )

        assert result.drift_detected is True
        assert result.original_context == "aspnet_core_minimal"
        assert result.fixed_context == "console"
        assert result.should_reject is True

    def test_no_drift_console_to_console(self):
        """Test no drift when context stays console → console"""
        validator = ContextDriftValidator(enabled=True)

        original_code = """
using Aspose.Zip;

var archive = new Archive();
archive.CreateEntry("file.txt", "data.txt");
"""

        fixed_code = """
using Aspose.Zip;
using System;

var archive = new Archive();
archive.CreateEntry("file.txt", "data.txt");
archive.Save("output.zip");
Console.WriteLine("Done");
"""

        result = validator.validate(
            original_code=original_code,
            fixed_code=fixed_code,
            original_context="console"
        )

        assert result.drift_detected is False
        assert result.original_context == "console"
        assert result.fixed_context == "console"
        assert result.should_reject is False
        assert result.rejection_reason is None

    def test_no_drift_aspnet_to_aspnet(self):
        """Test no drift when context stays ASP.NET → ASP.NET"""
        validator = ContextDriftValidator(enabled=True)

        original_code = """
var builder = WebApplication.CreateBuilder(args);
var app = builder.Build();
app.Run();
"""

        fixed_code = """
using Microsoft.AspNetCore.Builder;

var builder = WebApplication.CreateBuilder(args);
var app = builder.Build();

app.MapGet("/", () => "Hello");

app.Run();
"""

        result = validator.validate(
            original_code=original_code,
            fixed_code=fixed_code,
            original_context="aspnet_core_minimal"
        )

        assert result.drift_detected is False
        assert result.original_context == "aspnet_core_minimal"
        assert result.fixed_context == "aspnet_core_minimal"
        assert result.should_reject is False

    def test_drift_allowed_when_disabled(self):
        """Test that drift is allowed when validator is disabled"""
        validator = ContextDriftValidator(enabled=False)

        original_code = "using Aspose.Zip; var archive = new Archive();"
        fixed_code = "var builder = WebApplication.CreateBuilder(args);"

        result = validator.validate(
            original_code=original_code,
            fixed_code=fixed_code,
            original_context="console"
        )

        # When disabled, drift_detected should be False (permissive)
        assert result.drift_detected is False
        assert result.drift_allowed is True
        assert result.should_reject is False

    def test_auto_classification_when_context_not_provided(self):
        """Test that validator classifies original code if context not provided"""
        validator = ContextDriftValidator(enabled=True)

        original_code = """
using Aspose.Zip;

var archive = new Archive();
archive.Save("output.zip");
"""

        fixed_code = """
var builder = WebApplication.CreateBuilder(args);
var app = builder.Build();
app.Run();
"""

        # Don't provide original_context - should auto-classify
        result = validator.validate(
            original_code=original_code,
            fixed_code=fixed_code,
            original_context=None
        )

        # Should detect drift: auto-classified console → aspnet
        assert result.drift_detected is True
        assert result.original_context == "console"
        assert result.fixed_context == "aspnet_core_minimal"
        assert result.should_reject is True

    def test_drift_mvc_to_webapi(self):
        """Test drift detection between MVC and WebAPI contexts"""
        validator = ContextDriftValidator(enabled=True)

        original_code = """
using Microsoft.AspNetCore.Mvc;

public class HomeController : Controller
{
    public IActionResult Index()
    {
        return View();
    }
}
"""

        fixed_code = """
using Microsoft.AspNetCore.Mvc;

[ApiController]
public class HomeController : ControllerBase
{
    [HttpGet]
    public IActionResult GetData()
    {
        return Ok("data");
    }
}
"""

        result = validator.validate(
            original_code=original_code,
            fixed_code=fixed_code,
            original_context="aspnet_core_mvc"
        )

        # MVC → WebAPI is drift
        assert result.drift_detected is True
        assert result.original_context == "aspnet_core_mvc"
        assert result.fixed_context == "aspnet_core_webapi"
        assert result.should_reject is True

    def test_drift_library_to_console(self):
        """Test drift detection from library to console context"""
        validator = ContextDriftValidator(enabled=True)

        original_code = """
public class ZipHelper
{
    public void CreateArchive(string path)
    {
        // Implementation
    }
}
"""

        fixed_code = """
using System;

class Program
{
    static void Main()
    {
        Console.WriteLine("Creating archive...");
    }
}
"""

        result = validator.validate(
            original_code=original_code,
            fixed_code=fixed_code,
            original_context="library"
        )

        # Library → Console is drift
        assert result.drift_detected is True
        assert result.original_context == "library"
        assert result.fixed_context == "console"
        assert result.should_reject is True

    def test_no_drift_library_to_library(self):
        """Test no drift when library context is preserved"""
        validator = ContextDriftValidator(enabled=True)

        original_code = """
public class Helper
{
    public void DoWork() { }
}
"""

        fixed_code = """
using System;

public class Helper
{
    public void DoWork()
    {
        // Implementation added
    }

    public bool Validate()
    {
        return true;
    }
}
"""

        result = validator.validate(
            original_code=original_code,
            fixed_code=fixed_code,
            original_context="library"
        )

        # Library → Library is not drift
        assert result.drift_detected is False
        assert result.original_context == "library"
        assert result.fixed_context == "library"
        assert result.should_reject is False

    def test_get_drift_metadata(self):
        """Test metadata extraction from drift result"""
        validator = ContextDriftValidator(enabled=True)

        result = ContextDriftResult(
            drift_detected=True,
            original_context="console",
            fixed_context="aspnet_core_minimal",
            drift_allowed=False,
            rejection_reason="Context changed from console to aspnet_core_minimal"
        )

        metadata = validator.get_drift_metadata(result)

        assert metadata["drift_detected"] is True
        assert metadata["original_context"] == "console"
        assert metadata["fixed_context"] == "aspnet_core_minimal"
        assert metadata["drift_allowed"] is False
        assert "console" in metadata["rejection_reason"]
        assert "aspnet_core_minimal" in metadata["rejection_reason"]

    def test_convenience_function(self):
        """Test the convenience validate_context_drift function"""
        original_code = "using Aspose.Zip; var archive = new Archive();"
        fixed_code = "var builder = WebApplication.CreateBuilder(args);"

        # Test with enabled=True
        result = validate_context_drift(
            original_code=original_code,
            fixed_code=fixed_code,
            original_context="console",
            enabled=True
        )

        assert result.drift_detected is True
        assert result.should_reject is True

        # Test with enabled=False
        result_disabled = validate_context_drift(
            original_code=original_code,
            fixed_code=fixed_code,
            original_context="console",
            enabled=False
        )

        assert result_disabled.drift_detected is False
        assert result_disabled.should_reject is False

    def test_should_reject_property(self):
        """Test the should_reject computed property"""
        # Case 1: Drift detected, not allowed → should reject
        result1 = ContextDriftResult(
            drift_detected=True,
            original_context="console",
            fixed_context="aspnet_core_minimal",
            drift_allowed=False
        )
        assert result1.should_reject is True

        # Case 2: Drift detected, but allowed → should not reject
        result2 = ContextDriftResult(
            drift_detected=True,
            original_context="console",
            fixed_context="aspnet_core_minimal",
            drift_allowed=True
        )
        assert result2.should_reject is False

        # Case 3: No drift → should not reject
        result3 = ContextDriftResult(
            drift_detected=False,
            original_context="console",
            fixed_context="console",
            drift_allowed=True
        )
        assert result3.should_reject is False

    def test_unknown_context_handling(self):
        """Test handling of unknown context types"""
        validator = ContextDriftValidator(enabled=True)

        # Empty code should result in unknown context
        original_code = ""
        fixed_code = "var builder = WebApplication.CreateBuilder(args);"

        result = validator.validate(
            original_code=original_code,
            fixed_code=fixed_code,
            original_context=None
        )

        # Unknown → aspnet_core_minimal is drift
        assert result.drift_detected is True
        assert result.original_context == "unknown"
        assert result.fixed_context == "aspnet_core_minimal"

    def test_default_enabled_is_false(self):
        """Test that validator defaults to disabled"""
        validator = ContextDriftValidator()

        assert validator.enabled is False

        # When disabled, validation should be permissive
        result = validator.validate(
            original_code="console code",
            fixed_code="aspnet code",
            original_context="console"
        )

        assert result.drift_allowed is True
        assert result.should_reject is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
