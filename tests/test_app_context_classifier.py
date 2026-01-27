"""
Tests for app_context_classifier module.

Tests deterministic classification of C# code by application architecture type.
"""

import pytest
from src.core.app_context import AppContext
from src.pipeline.app_context_classifier import classify_app_context, AppContextClassifier


class TestAppContextClassifier:
    """Test application context classification."""

    def test_minimal_hosting_webapplication_createbuilder(self):
        """Test minimal hosting API with WebApplication.CreateBuilder"""
        code = """
using Microsoft.AspNetCore.Builder;

var builder = WebApplication.CreateBuilder(args);
var app = builder.Build();

app.MapGet("/", () => "Hello World!");

app.Run();
"""
        result = classify_app_context(code)
        assert result == AppContext.ASPNET_CORE_MINIMAL

    def test_minimal_hosting_with_services(self):
        """Test minimal hosting with builder.Services usage"""
        code = """
var builder = WebApplication.CreateBuilder(args);
builder.Services.AddSingleton<IMyService, MyService>();

var app = builder.Build();
app.MapGet("/api/data", () => "Data");
app.Run();
"""
        result = classify_app_context(code)
        assert result == AppContext.ASPNET_CORE_MINIMAL

    def test_mvc_controller_pattern(self):
        """Test MVC controller pattern"""
        code = """
using Microsoft.AspNetCore.Mvc;

public class HomeController : Controller
{
    public IActionResult Index()
    {
        return View();
    }

    [HttpPost]
    public IActionResult Submit(string data)
    {
        return RedirectToAction("Index");
    }
}
"""
        result = classify_app_context(code)
        assert result == AppContext.ASPNET_CORE_MVC

    def test_mvc_viewresult(self):
        """Test MVC with ViewResult"""
        code = """
public class ProductController : Controller
{
    public ViewResult List()
    {
        return View("ProductList");
    }
}
"""
        result = classify_app_context(code)
        assert result == AppContext.ASPNET_CORE_MVC

    def test_webapi_apicontroller(self):
        """Test Web API with ApiController attribute"""
        code = """
using Microsoft.AspNetCore.Mvc;

[ApiController]
[Route("api/[controller]")]
public class UsersController : ControllerBase
{
    [HttpGet]
    public IActionResult GetAll()
    {
        return Ok(new[] { "User1", "User2" });
    }

    [HttpPost]
    public IActionResult Create([FromBody] User user)
    {
        return Created("/api/users/1", user);
    }
}
"""
        result = classify_app_context(code)
        assert result == AppContext.ASPNET_CORE_WEBAPI

    def test_webapi_controllerbase(self):
        """Test Web API with ControllerBase"""
        code = """
public class DataController : ControllerBase
{
    [HttpGet]
    public IActionResult Get([FromQuery] string id)
    {
        return Ok("data");
    }
}
"""
        result = classify_app_context(code)
        assert result == AppContext.ASPNET_CORE_WEBAPI

    def test_console_with_main(self):
        """Test traditional console app with Main"""
        code = """
using System;
using Aspose.Zip;

public class Program
{
    public static void Main(string[] args)
    {
        using (var archive = new Archive())
        {
            archive.CreateEntry("test.txt", "data.txt");
            archive.Save("output.zip");
        }
    }
}
"""
        result = classify_app_context(code)
        assert result == AppContext.CONSOLE

    def test_console_top_level_statements(self):
        """Test console app with top-level statements (no explicit Main)"""
        code = """
using Aspose.Zip;

var archive = new Archive();
archive.CreateEntry("file.txt", "source.txt");
archive.Save("output.zip");
"""
        result = classify_app_context(code)
        assert result == AppContext.CONSOLE

    def test_library_class_only(self):
        """Test class library with no entrypoint"""
        code = """
using System;

public class ZipHelper
{
    public void CreateZipArchive(string inputPath, string outputPath)
    {
        // Implementation
    }

    public bool ValidateArchive(string archivePath)
    {
        return true;
    }
}
"""
        result = classify_app_context(code)
        assert result == AppContext.LIBRARY

    def test_library_interface(self):
        """Test library with interface definition"""
        code = """
public interface IArchiveService
{
    void CreateArchive(string path);
    void ExtractArchive(string path);
}
"""
        result = classify_app_context(code)
        assert result == AppContext.LIBRARY

    def test_library_static_class(self):
        """Test library with static utility class"""
        code = """
public static class ArchiveUtilities
{
    public static string GetArchiveFormat(string filePath)
    {
        return Path.GetExtension(filePath);
    }
}
"""
        result = classify_app_context(code)
        assert result == AppContext.LIBRARY

    def test_unknown_empty_code(self):
        """Test empty code returns unknown"""
        result = classify_app_context("")
        assert result == AppContext.UNKNOWN

    def test_unknown_whitespace_only(self):
        """Test whitespace-only code returns unknown"""
        result = classify_app_context("   \n\n  \t  ")
        assert result == AppContext.UNKNOWN

    def test_priority_minimal_over_console(self):
        """Test that minimal hosting takes priority over console patterns"""
        code = """
using Microsoft.AspNetCore.Builder;

var builder = WebApplication.CreateBuilder(args);
var app = builder.Build();

// This has standalone logic like console, but WebApplication pattern should win
app.MapGet("/", () => "Hello");
app.Run();
"""
        result = classify_app_context(code)
        assert result == AppContext.ASPNET_CORE_MINIMAL

    def test_priority_mvc_over_webapi(self):
        """Test that MVC patterns take priority when both present"""
        code = """
using Microsoft.AspNetCore.Mvc;

public class HybridController : Controller
{
    // Has both MVC View() and API Ok() patterns
    public IActionResult Index()
    {
        return View();  # MVC pattern
    }

    [HttpGet]
    public IActionResult GetData()
    {
        return Ok("data");  # API pattern
    }
}
"""
        result = classify_app_context(code)
        # MVC patterns are checked before WebAPI patterns, so MVC wins
        assert result == AppContext.ASPNET_CORE_MVC

    def test_real_world_zip_console_example(self):
        """Test real-world Aspose.Zip console example"""
        code = """
using Aspose.Zip;
using Aspose.Zip.Saving;

var settings = new ArchiveEntrySettings(new DeflateCompressionSettings());
using (var archive = new Archive(settings))
{
    archive.CreateEntry("document.txt", @"C:\\input\\document.txt");
    archive.CreateEntry("image.png", @"C:\\input\\image.png");
    archive.Save(@"C:\\output\\archive.zip");
}
"""
        result = classify_app_context(code)
        assert result == AppContext.CONSOLE

    def test_aspnet_minimal_with_zip_library(self):
        """Test ASP.NET minimal API using Zip library (shouldn't be classified as console)"""
        code = """
using Microsoft.AspNetCore.Builder;
using Aspose.Zip;

var builder = WebApplication.CreateBuilder(args);
var app = builder.Build();

app.MapPost("/create-zip", () =>
{
    var archive = new Archive();
    archive.CreateEntry("file.txt", "data.txt");
    archive.Save("output.zip");
    return Results.Ok();
});

app.Run();
"""
        result = classify_app_context(code)
        # Should still be minimal hosting, not console
        assert result == AppContext.ASPNET_CORE_MINIMAL

    def test_classifier_method_matches_any_basic(self):
        """Test _matches_any helper method"""
        patterns = [r'\bclass\b', r'\binterface\b']
        code = "public class MyClass { }"
        assert AppContextClassifier._matches_any(code, patterns) is True

    def test_classifier_method_matches_any_no_match(self):
        """Test _matches_any with no matches"""
        patterns = [r'\bfunction\b', r'\bmodule\b']
        code = "public class MyClass { }"
        assert AppContextClassifier._matches_any(code, patterns) is False

    def test_case_insensitive_matching(self):
        """Test that patterns are case-insensitive"""
        # Use uppercase API names
        code = """
var BUILDER = WebApplication.CreateBuilder(args);
var APP = BUILDER.Build();
APP.MapGet("/", () => "Hello");
APP.Run();
"""
        result = classify_app_context(code)
        assert result == AppContext.ASPNET_CORE_MINIMAL


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
