"""
Unit tests for context inference fix (Snippet 136).
Tests the _needs_context() method to ensure using-only code is properly detected.
"""

import unittest
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from persistent_fix_service import PersistentFixService
from database import Database
from workspace_manager import WorkspaceManager
from ollama_integration import OllamaClient
from telemetry import TelemetryClient
from unittest.mock import Mock


class TestContextInferenceUsingOnly(unittest.TestCase):
    """Test using-only code detection."""

    def setUp(self):
        """Set up test fixtures."""
        # Create minimal service instance for testing
        # Use mocks for dependencies we don't need
        db = Mock(spec=Database)
        telemetry = Mock(spec=TelemetryClient)
        workspace = Mock(spec=WorkspaceManager)
        ollama = Mock(spec=OllamaClient)

        family_config = {
            'family': 'test',
            'persistent_fix': {
                'enable_context_inference': True
            }
        }

        self.service = PersistentFixService(
            workspace=workspace,
            ollama=ollama,
            db=db,
            telemetry=telemetry,
            family_config=family_config
        )

    def test_using_only_simple(self):
        """Test detection of simple using-only code."""
        code = "using Aspose.Zip;\nusing Aspose.Zip.Saving;"
        result = self.service._needs_context(code)
        self.assertTrue(result, "Simple using-only code should need context")

    def test_using_only_with_inline_comments(self):
        """Test detection of using-only code with inline comments."""
        code = "using Aspose.Zip;  // Archive API\nusing Aspose.Zip.Saving;  // Compression"
        result = self.service._needs_context(code)
        self.assertTrue(result, "Using-only code with inline comments should need context")

    def test_using_only_with_block_comments(self):
        """Test detection of using-only code with block comments."""
        code = """using Aspose.Zip;
/*
 * Additional namespaces
 */
using Aspose.Zip.Saving;"""
        result = self.service._needs_context(code)
        self.assertTrue(result, "Using-only code with block comments should need context")

    def test_using_only_with_whitespace(self):
        """Test detection of using-only code with extra whitespace."""
        code = "\n\n\nusing Aspose.Zip;\n\nusing Aspose.Zip.Saving;\n\n\n"
        result = self.service._needs_context(code)
        self.assertTrue(result, "Using-only code with whitespace should need context")

    def test_using_with_namespace(self):
        """Test that code with namespace does NOT trigger using-only detection."""
        code = "using System;\n\nnamespace MyApp { }"
        result = self.service._needs_context(code)
        self.assertFalse(result, "Code with namespace should not need context")

    def test_using_with_class(self):
        """Test that code with class does NOT need context."""
        code = "using System;\n\npublic class MyClass { }"
        result = self.service._needs_context(code)
        self.assertFalse(result, "Code with class declaration should not need context")

    def test_using_with_method(self):
        """Test that code with method needs context (existing behavior)."""
        code = "using System;\n\nvoid DoWork() { }"
        result = self.service._needs_context(code)
        self.assertTrue(result, "Partial method code should need context")

    def test_using_with_field(self):
        """Test that code with field needs context (existing behavior)."""
        code = "using System;\n\npublic string Name;"
        result = self.service._needs_context(code)
        self.assertTrue(result, "Code with field should need context")

    def test_empty_code(self):
        """Test that empty code does not need context."""
        code = ""
        result = self.service._needs_context(code)
        self.assertFalse(result, "Empty code should not need context")

    def test_whitespace_only(self):
        """Test that whitespace-only code does not need context."""
        code = "   \n\n\t\n   "
        result = self.service._needs_context(code)
        self.assertFalse(result, "Whitespace-only code should not need context")

    def test_complete_code(self):
        """Test that complete code with namespace and class does not need context."""
        code = """using System;

namespace MyApp
{
    public class MyClass
    {
        public void DoWork() { }
    }
}"""
        result = self.service._needs_context(code)
        self.assertFalse(result, "Complete code should not need context")

    def test_snippet_136_original(self):
        """Test actual Snippet 136 code (using-only with comments)."""
        code = """using Aspose.Zip;                 // Archive, ArchiveEntry
using Aspose.Zip.Saving;          // DeflateCompressionSettings, CompressionLevel"""
        result = self.service._needs_context(code)
        self.assertTrue(result, "Snippet 136 original code should need context")


class TestContextInferenceRegression(unittest.TestCase):
    """Test that existing behavior is preserved (no regressions)."""

    def setUp(self):
        """Set up test fixtures."""
        # Use mocks for dependencies we don't need
        db = Mock(spec=Database)
        telemetry = Mock(spec=TelemetryClient)
        workspace = Mock(spec=WorkspaceManager)
        ollama = Mock(spec=OllamaClient)

        family_config = {
            'family': 'test',
            'persistent_fix': {
                'enable_context_inference': True
            }
        }

        self.service = PersistentFixService(
            workspace=workspace,
            ollama=ollama,
            db=db,
            telemetry=telemetry,
            family_config=family_config
        )

    def test_method_without_class_needs_context(self):
        """Test that method without class needs context (existing behavior)."""
        code = """public void ProcessFile(string path)
{
    // Implementation
}"""
        result = self.service._needs_context(code)
        self.assertTrue(result, "Method without class should need context")

    def test_property_without_class_needs_context(self):
        """Test that property without class needs context (existing behavior)."""
        code = "public string Name { get; set; }"
        result = self.service._needs_context(code)
        self.assertTrue(result, "Property without class should need context")

    def test_field_without_class_needs_context(self):
        """Test that field without class needs context (existing behavior)."""
        code = "private readonly string _name;"
        result = self.service._needs_context(code)
        self.assertTrue(result, "Field without class should need context")

    def test_interface_does_not_need_context(self):
        """Test that interface declaration does not need context."""
        code = """public interface IProcessor
{
    void Process();
}"""
        result = self.service._needs_context(code)
        self.assertFalse(result, "Interface should not need context")

    def test_struct_does_not_need_context(self):
        """Test that struct declaration does not need context."""
        code = """public struct Point
{
    public int X;
    public int Y;
}"""
        result = self.service._needs_context(code)
        self.assertFalse(result, "Struct should not need context")

    def test_enum_does_not_need_context(self):
        """Test that enum declaration does not need context."""
        code = """public enum Status
{
    Active,
    Inactive
}"""
        result = self.service._needs_context(code)
        self.assertFalse(result, "Enum should not need context")


class TestContextInferenceEdgeCases(unittest.TestCase):
    """Test edge cases for context inference."""

    def setUp(self):
        """Set up test fixtures."""
        # Use mocks for dependencies we don't need
        db = Mock(spec=Database)
        telemetry = Mock(spec=TelemetryClient)
        workspace = Mock(spec=WorkspaceManager)
        ollama = Mock(spec=OllamaClient)

        family_config = {
            'family': 'test',
            'persistent_fix': {
                'enable_context_inference': True
            }
        }

        self.service = PersistentFixService(
            workspace=workspace,
            ollama=ollama,
            db=db,
            telemetry=telemetry,
            family_config=family_config
        )

    def test_using_statement_in_comment(self):
        """Test that using in comments doesn't trigger false positive."""
        code = """// This shows using statements
// using System;
public class MyClass { }"""
        result = self.service._needs_context(code)
        self.assertFalse(result, "Using in comments should not trigger detection")

    def test_using_directive_for_alias(self):
        """Test using directive for type alias."""
        code = "using StringList = System.Collections.Generic.List<string>;"
        result = self.service._needs_context(code)
        self.assertTrue(result, "Using alias-only should need context")

    def test_using_static_directive(self):
        """Test using static directive."""
        code = "using static System.Math;"
        result = self.service._needs_context(code)
        self.assertTrue(result, "Using static-only should need context")

    def test_multiple_using_types(self):
        """Test mix of regular and static using."""
        code = """using System;
using static System.Math;
using StringDict = System.Collections.Generic.Dictionary<string, string>;"""
        result = self.service._needs_context(code)
        self.assertTrue(result, "Mixed using types should need context")

    def test_using_with_semicolon_in_string(self):
        """Test that semicolons in strings don't break detection."""
        code = """using System;
// Comment with semicolon; inside
using System.IO;"""
        result = self.service._needs_context(code)
        self.assertTrue(result, "Using with semicolons in comments should need context")


def run_tests():
    """Run all tests and print results."""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestContextInferenceUsingOnly))
    suite.addTests(loader.loadTestsFromTestCase(TestContextInferenceRegression))
    suite.addTests(loader.loadTestsFromTestCase(TestContextInferenceEdgeCases))

    # Run tests with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Return exit code
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(run_tests())
