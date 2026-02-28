"""Tests for the validate_code_snippet MCP tool."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.mcp_tools.tools import ExampleReviewerTools, ToolResult


@pytest.fixture
def tools_with_catalog():
    """Create ExampleReviewerTools pointing at real config/families for catalog loading."""
    t = ExampleReviewerTools.__new__(ExampleReviewerTools)
    t.config_dir = Path("config/families")
    t.db_path = Path("data/test.db")
    t.prod_db_path = None
    t.workspace_dir = Path("workspace")
    t.cli_overrides = {}
    t.use_workspace_copy = False
    t.sqlite_config = {}
    t._orchestrator = MagicMock()
    # Clear catalog cache between tests
    ExampleReviewerTools._catalog_cache = {}
    return t


class TestValidateCodeSnippetBasics:
    """Basic tool behavior: non-C# early return, missing catalog, etc."""

    def test_non_csharp_returns_valid(self, tools_with_catalog):
        """Non-C# language should return valid immediately (no catalog to check)."""
        result = tools_with_catalog.validate_code_snippet(
            code="import aspose.words",
            family="words",
            language="python",
        )
        assert result.success is True
        assert result.data["valid"] is True
        assert result.data["hallucinated_types"] == []
        assert "No catalog for language" in result.data["catalog_info"]["note"]

    def test_missing_catalog_returns_error(self, tools_with_catalog):
        """Family with no catalog file should return a clear error."""
        result = tools_with_catalog.validate_code_snippet(
            code="using Aspose.Nonexistent;",
            family="nonexistent_family_xyz",
        )
        assert result.success is False
        assert "No API catalog" in result.error

    def test_empty_code_is_valid(self, tools_with_catalog):
        """Empty code has nothing to flag."""
        result = tools_with_catalog.validate_code_snippet(
            code="",
            family="zip",
        )
        assert result.success is True
        assert result.data["valid"] is True
        assert result.data["hallucinated_types"] == []


class TestValidateCodeSnippetZip:
    """Validation against the real ZIP API catalog (138 types, 28 namespaces)."""

    def test_valid_zip_code(self, tools_with_catalog):
        """Code using real Aspose.Zip types should be valid."""
        code = """
using System;
using System.IO;
using Aspose.Zip;

class Program
{
    static void Main()
    {
        using (var archive = new Archive("input.zip"))
        {
            archive.ExtractToDirectory("output");
        }
    }
}
"""
        result = tools_with_catalog.validate_code_snippet(code=code, family="zip")
        assert result.success is True
        assert result.data["valid"] is True
        assert "Archive" in result.data["catalog_matches"]
        assert result.data["hallucinated_types"] == []
        assert result.data["catalog_info"]["family"] == "zip"
        assert result.data["catalog_info"]["total_types"] > 100

    def test_hallucinated_type_flagged(self, tools_with_catalog):
        """A type that doesn't exist in the catalog should be flagged."""
        code = """
using Aspose.Zip;

class Program
{
    static void Main()
    {
        var magic = new ZipMagicProcessor("input.zip");
        magic.AutoFixAll();
    }
}
"""
        result = tools_with_catalog.validate_code_snippet(code=code, family="zip")
        assert result.success is True
        assert "ZipMagicProcessor" in result.data["hallucinated_types"]

    def test_bcl_types_not_flagged(self, tools_with_catalog):
        """Standard .NET types (Console, String, etc.) should not be flagged."""
        code = """
using System;
using System.IO;
using Aspose.Zip;

class Program
{
    static void Main()
    {
        Console.WriteLine("Hello");
        var archive = new Archive("test.zip");
    }
}
"""
        result = tools_with_catalog.validate_code_snippet(code=code, family="zip")
        assert result.success is True
        assert "Console" not in result.data["hallucinated_types"]
        assert "Archive" in result.data["catalog_matches"]

    def test_namespace_violation_detected(self, tools_with_catalog):
        """Using a namespace not in catalog or BCL whitelist should be flagged."""
        code = """
using System;
using Aspose.Zip;
using SixLabors.ImageSharp;

class Program
{
    static void Main()
    {
        var archive = new Archive("test.zip");
    }
}
"""
        result = tools_with_catalog.validate_code_snippet(code=code, family="zip")
        assert result.success is True
        assert "SixLabors.ImageSharp" in result.data["namespace_violations"]

    def test_system_namespaces_allowed(self, tools_with_catalog):
        """All standard System.* namespaces should be allowed."""
        code = """
using System;
using System.IO;
using System.Text;
using System.Linq;
using System.Collections.Generic;
using Aspose.Zip;

class Program
{
    static void Main()
    {
        var archive = new Archive("test.zip");
    }
}
"""
        result = tools_with_catalog.validate_code_snippet(code=code, family="zip")
        assert result.success is True
        assert result.data["namespace_violations"] == []


class TestValidateCodeSnippetWords:
    """Validation against the real Words API catalog."""

    def test_valid_words_code(self, tools_with_catalog):
        """Code using real Aspose.Words types should be valid."""
        code = """
using Aspose.Words;

class Program
{
    static void Main()
    {
        var doc = new Document("input.docx");
        doc.Save("output.pdf", SaveFormat.Pdf);
    }
}
"""
        result = tools_with_catalog.validate_code_snippet(code=code, family="words")
        assert result.success is True
        assert result.data["valid"] is True
        assert "Document" in result.data["catalog_matches"]
        assert "SaveFormat" in result.data["catalog_matches"]

    def test_hallucinated_words_method(self, tools_with_catalog):
        """A type that doesn't exist in Words catalog should be flagged."""
        code = """
using Aspose.Words;

class Program
{
    static void Main()
    {
        var converter = new SmartDocConverter();
        converter.ConvertAll();
    }
}
"""
        result = tools_with_catalog.validate_code_snippet(code=code, family="words")
        assert result.success is True
        assert "SmartDocConverter" in result.data["hallucinated_types"]


class TestValidateCodeSnippetCatalogCaching:
    """Verify catalog instances are cached per family."""

    def test_catalog_cached_across_calls(self, tools_with_catalog):
        """Second call for same family should reuse cached catalog."""
        code = "using Aspose.Zip;\nvar a = new Archive();"

        tools_with_catalog.validate_code_snippet(code=code, family="zip")
        assert "zip" in ExampleReviewerTools._catalog_cache

        # Second call should not reload
        cached = ExampleReviewerTools._catalog_cache["zip"]
        tools_with_catalog.validate_code_snippet(code=code, family="zip")
        assert ExampleReviewerTools._catalog_cache["zip"] is cached

    def test_different_families_separate_caches(self, tools_with_catalog):
        """Each family gets its own cached catalog."""
        tools_with_catalog.validate_code_snippet(
            code="using Aspose.Zip;\nvar a = new Archive();", family="zip"
        )
        tools_with_catalog.validate_code_snippet(
            code="using Aspose.Words;\nvar d = new Document();", family="words"
        )
        assert "zip" in ExampleReviewerTools._catalog_cache
        assert "words" in ExampleReviewerTools._catalog_cache


class TestValidateCodeSnippetCompileVerify:
    """Test the optional compile_verify flag."""

    def test_compile_verify_false_skips_compilation(self, tools_with_catalog):
        """compile_verify=False (default) should not trigger compilation."""
        code = "using Aspose.Zip;\nvar a = new Archive();"
        result = tools_with_catalog.validate_code_snippet(code=code, family="zip")
        assert result.success is True
        assert result.data["compilation_result"] is None
