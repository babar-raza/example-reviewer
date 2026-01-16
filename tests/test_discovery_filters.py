"""
Unit tests for discovery filtering functionality (CD-02).
Tests line count filtering, content exclusion patterns, and code indicators.
"""

import pytest
from src.core.config import DiscoveryPatternsConfig
from src.services.discovery_service import DiscoveryService
from src.core.database import Database


class TestLineCountFiltering:
    """Test line count filtering."""

    def test_filter_snippet_too_short(self, tmp_path):
        """Test that snippets below min_line_count are filtered out."""
        db = Database(str(tmp_path / "test.db"))
        db.initialize_schema()

        config = DiscoveryPatternsConfig(min_line_count=5, max_line_count=500)
        service = DiscoveryService(db, filtering_config=config)

        # 3-line snippet (below min of 5)
        code = "using System;\nvar x = 1;\nConsole.WriteLine(x);"

        should_include, reason = service.filter_snippet(code)

        assert not should_include
        assert "Too short" in reason
        assert "3 lines < 5" in reason

    def test_filter_snippet_too_long(self, tmp_path):
        """Test that snippets above max_line_count are filtered out."""
        db = Database(str(tmp_path / "test.db"))
        db.initialize_schema()

        config = DiscoveryPatternsConfig(min_line_count=5, max_line_count=10)
        service = DiscoveryService(db, filtering_config=config)

        # 15-line snippet (above max of 10)
        code = "\n".join([f"var x{i} = {i};" for i in range(15)])

        should_include, reason = service.filter_snippet(code)

        assert not should_include
        assert "Too long" in reason
        assert "15 lines > 10" in reason

    def test_filter_snippet_valid_length(self, tmp_path):
        """Test that snippets within line count range pass."""
        db = Database(str(tmp_path / "test.db"))
        db.initialize_schema()

        config = DiscoveryPatternsConfig(min_line_count=5, max_line_count=500)
        service = DiscoveryService(db, filtering_config=config)

        # 10-line C# snippet (within range)
        code = """using System;
using Aspose.Zip;

public class Example
{
    public void Method()
    {
        var archive = new Archive();
    }
}"""

        should_include, reason = service.filter_snippet(code)

        assert should_include
        assert "Passed all filters" in reason


class TestContentExclusionPatterns:
    """Test content exclusion patterns."""

    def test_exclude_json_content(self, tmp_path):
        """Test that JSON content is excluded."""
        db = Database(str(tmp_path / "test.db"))
        db.initialize_schema()

        config = DiscoveryPatternsConfig()
        service = DiscoveryService(db, filtering_config=config)

        # JSON content
        code = """    {
        "name": "test",
        "version": "1.0",
        "dependencies": {
            "package": "^1.0.0"
        }
    }"""

        should_include, reason = service.filter_snippet(code)

        assert not should_include
        assert "exclusion pattern" in reason.lower()

    def test_exclude_xml_content(self, tmp_path):
        """Test that XML content is excluded."""
        db = Database(str(tmp_path / "test.db"))
        db.initialize_schema()

        config = DiscoveryPatternsConfig()
        service = DiscoveryService(db, filtering_config=config)

        # XML content
        code = """<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <appSettings>
        <add key="setting" value="value" />
    </appSettings>
</configuration>"""

        should_include, reason = service.filter_snippet(code)

        assert not should_include
        assert "exclusion pattern" in reason.lower()

    def test_exclude_command_output(self, tmp_path):
        """Test that command output is excluded."""
        db = Database(str(tmp_path / "test.db"))
        db.initialize_schema()

        config = DiscoveryPatternsConfig()
        service = DiscoveryService(db, filtering_config=config)

        # Command output (need at least 5 lines to pass line count check)
        code = """Output:
Successfully created archive.zip
Total files: 5
Total size: 1024 KB
Processing complete."""

        should_include, reason = service.filter_snippet(code)

        assert not should_include
        assert "exclusion pattern" in reason.lower()

    def test_exclude_shell_prompt(self, tmp_path):
        """Test that shell prompts are excluded."""
        db = Database(str(tmp_path / "test.db"))
        db.initialize_schema()

        config = DiscoveryPatternsConfig()
        service = DiscoveryService(db, filtering_config=config)

        # Shell commands (need at least 5 lines)
        code = """$ dotnet build
$ dotnet run
$ dotnet test
$ dotnet publish
$ dotnet clean"""

        should_include, reason = service.filter_snippet(code)

        assert not should_include
        assert "exclusion pattern" in reason.lower()


class TestCodeIndicators:
    """Test code indicator requirements."""

    def test_code_indicators_present(self, tmp_path):
        """Test that code with indicators passes."""
        db = Database(str(tmp_path / "test.db"))
        db.initialize_schema()

        config = DiscoveryPatternsConfig()
        service = DiscoveryService(db, filtering_config=config)

        # Valid C# code with multiple indicators
        code = """using System;
using Aspose.Zip;

namespace Example
{
    public class ZipExample
    {
        public void CreateArchive()
        {
            var archive = new Archive();
            archive.Save("output.zip");
        }
    }
}"""

        should_include, reason = service.filter_snippet(code)

        assert should_include
        assert "Passed all filters" in reason

    def test_code_indicators_missing(self, tmp_path):
        """Test that code without indicators is filtered."""
        db = Database(str(tmp_path / "test.db"))
        db.initialize_schema()

        config = DiscoveryPatternsConfig()
        service = DiscoveryService(db, filtering_config=config)

        # Non-code text (no C# indicators)
        code = """This is some documentation text.
It has multiple lines.
But it does not contain any code.
Just regular text content.
More text here to meet line count."""

        should_include, reason = service.filter_snippet(code)

        assert not should_include
        assert "No C# code indicators found" in reason

    def test_code_indicators_case_insensitive(self, tmp_path):
        """Test that code indicators work case-insensitively."""
        db = Database(str(tmp_path / "test.db"))
        db.initialize_schema()

        config = DiscoveryPatternsConfig()
        service = DiscoveryService(db, filtering_config=config)

        # C# code with mixed case keywords
        code = """Using System;

Public Class Example
{
    Void Method()
    {
        var x = 1;
    }
}"""

        should_include, reason = service.filter_snippet(code)

        assert should_include
        assert "Passed all filters" in reason


class TestFilterStatistics:
    """Test filter statistics tracking."""

    def test_filter_stats_tracking(self, tmp_path):
        """Test that filter statistics are tracked correctly."""
        db = Database(str(tmp_path / "test.db"))
        db.initialize_schema()

        config = DiscoveryPatternsConfig(min_line_count=5)
        service = DiscoveryService(db, filtering_config=config)

        # Filter several snippets
        snippets = [
            "x = 1;\ny = 2;",  # Too short (filtered)
            "{\n  \"test\": \"json\",\n  \"value\": 1\n}\nline5\nline6",  # JSON pattern (filtered)
            "using System;\nusing Aspose.Zip;\n\nclass Test {\n  void M() {}\n}",  # Valid (not filtered - 6 lines)
            "Output:\nSome output\nMore lines\nLine 4\nLine 5",  # Output pattern (filtered)
            "No code indicators\nJust text\nMore text\nLine 4\nLine 5",  # No indicators (filtered)
        ]

        for snippet in snippets:
            service.filter_snippet(snippet)

        stats = service.get_filter_stats()

        assert stats['total_checked'] == 5
        assert stats['filtered_out'] == 4  # 4 out of 5 should be filtered
        assert len(stats['reasons']) > 0


class TestFilterIntegration:
    """Integration tests for filtering in discovery pipeline."""

    def test_filter_integration_with_defaults(self, tmp_path):
        """Test that filtering works with default configuration."""
        db = Database(str(tmp_path / "test.db"))
        db.initialize_schema()

        # Use default config
        service = DiscoveryService(db)

        # Valid C# code
        valid_code = """using System;
using Aspose.Zip;

public class Example
{
    public void CreateZip()
    {
        var archive = new Archive();
        archive.Save("test.zip");
    }
}"""

        should_include, reason = service.filter_snippet(valid_code)

        assert should_include
        assert "Passed all filters" in reason

    def test_filter_allows_valid_code(self, tmp_path):
        """Test that realistic valid code snippets pass all filters."""
        db = Database(str(tmp_path / "test.db"))
        db.initialize_schema()

        config = DiscoveryPatternsConfig()
        service = DiscoveryService(db, filtering_config=config)

        # Realistic C# code snippet from documentation
        code = """using System;
using System.IO;
using Aspose.Zip;

class Program
{
    static void Main()
    {
        using (var archive = new Archive())
        {
            archive.CreateEntry("file.txt", "path/to/source.txt");
            archive.Save("output.zip");
        }
    }
}"""

        should_include, reason = service.filter_snippet(code)

        assert should_include
        stats = service.get_filter_stats()
        assert stats['total_checked'] >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
