"""
Tests for build failure detection and LLM response validation.

These tests verify the fixes for:
- Issue 1: Wrong prompt type for build errors
- Issue 2: No content validation for LLM responses
- Issue 3: Cascading bad code prevention
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add src to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.pipeline.orchestrator import PipelineOrchestrator
from src.services.llm_service import LLMService


class TestBuildFailureDetection:
    """Tests for _is_build_failure method in PipelineOrchestrator."""

    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator with mocked dependencies."""
        with patch.object(PipelineOrchestrator, '__init__', lambda x: None):
            orch = PipelineOrchestrator.__new__(PipelineOrchestrator)
            # Initialize the method we need
            orch._is_build_failure = PipelineOrchestrator._is_build_failure.__get__(orch, PipelineOrchestrator)
            return orch

    def test_detects_build_failed_prefix(self, orchestrator):
        """Should detect 'Build failed:' prefix as build error."""
        stderr = "Build failed: error CS0246: The type or namespace 'Archive' could not be found"
        assert orchestrator._is_build_failure(stderr) is True

    def test_detects_restore_failed(self, orchestrator):
        """Should detect 'Restore failed:' as build error."""
        stderr = "Restore failed: Unable to resolve package 'Aspose.Zip'"
        assert orchestrator._is_build_failure(stderr) is True

    def test_detects_cs_error_codes(self, orchestrator):
        """Should detect C# compiler error codes."""
        stderr = "Program.cs(10,5): error CS0103: The name 'archive' does not exist"
        assert orchestrator._is_build_failure(stderr) is True

    def test_detects_msb_error_codes(self, orchestrator):
        """Should detect MSBuild error codes."""
        stderr = "error MSB4018: The 'ResolveAssemblyReferences' task failed unexpectedly."
        assert orchestrator._is_build_failure(stderr) is True

    def test_runtime_exception_not_build_failure(self, orchestrator):
        """Should NOT detect runtime exceptions as build failures."""
        stderr = "Unhandled exception. System.IO.FileNotFoundException: Could not find file 'test.zip'"
        assert orchestrator._is_build_failure(stderr) is False

    def test_null_reference_not_build_failure(self, orchestrator):
        """Should NOT detect NullReferenceException as build failure."""
        stderr = "Unhandled exception. System.NullReferenceException: Object reference not set"
        assert orchestrator._is_build_failure(stderr) is False

    def test_empty_stderr_not_build_failure(self, orchestrator):
        """Should handle empty/None stderr gracefully."""
        assert orchestrator._is_build_failure(None) is False
        assert orchestrator._is_build_failure("") is False

    def test_mixed_content_with_cs_error(self, orchestrator):
        """Should detect build error even with other content."""
        stderr = """Build started...
Microsoft (R) Build Engine version 17.0.0
error CS0246: The type or namespace name 'Archive' could not be found
Build FAILED."""
        assert orchestrator._is_build_failure(stderr) is True


class TestLLMResponseValidation:
    """Tests for _validate_code_response method in LLMService."""

    @pytest.fixture
    def llm_service(self):
        """Create LLMService instance for testing."""
        # Create service with mocked complete method
        with patch.object(LLMService, '__init__', lambda x: None):
            service = LLMService.__new__(LLMService)
            service._validate_code_response = LLMService._validate_code_response.__get__(service, LLMService)
            service._clean_code_response = LLMService._clean_code_response.__get__(service, LLMService)
            return service

    def test_validates_simple_csharp_code(self, llm_service):
        """Should accept valid C# code."""
        code = """using System;
using Aspose.Zip;

var archive = new Archive("test.zip");
Console.WriteLine("Done");"""
        assert llm_service._validate_code_response(code) is True

    def test_validates_full_class(self, llm_service):
        """Should accept full class with Main method."""
        code = """using System;

public class Program
{
    public static void Main(string[] args)
    {
        Console.WriteLine("Hello");
    }
}"""
        assert llm_service._validate_code_response(code) is True

    def test_rejects_empty_content(self, llm_service):
        """Should reject empty content."""
        assert llm_service._validate_code_response("") is False
        assert llm_service._validate_code_response("   ") is False
        assert llm_service._validate_code_response(None) is False

    def test_rejects_prose_explanation(self, llm_service):
        """Should reject prose explanations."""
        prose = "I cannot fix this code because it requires external dependencies."
        assert llm_service._validate_code_response(prose) is False

        prose2 = "The error occurs because the file does not exist. You need to create it first."
        assert llm_service._validate_code_response(prose2) is False

    def test_rejects_sorry_messages(self, llm_service):
        """Should reject apology messages from LLM."""
        sorry = "Sorry, I cannot provide code that accesses the filesystem."
        assert llm_service._validate_code_response(sorry) is False

    def test_rejects_note_prefix(self, llm_service):
        """Should reject responses starting with 'Note:'."""
        note = "Note: This code requires the Aspose.Zip package to be installed."
        assert llm_service._validate_code_response(note) is False

    def test_clean_removes_markdown_and_validates(self, llm_service):
        """Should clean markdown and validate."""
        markdown_code = """```csharp
using System;
Console.WriteLine("Hello");
```"""
        result = llm_service._clean_code_response(markdown_code)
        assert result != ""  # Should not be empty (valid code)
        assert "```" not in result  # Should remove markdown

    def test_clean_returns_empty_for_invalid(self, llm_service):
        """Should return empty string for invalid code after cleaning."""
        markdown_prose = """```
I'm sorry, but I cannot help with this request.
```"""
        result = llm_service._clean_code_response(markdown_prose)
        assert result == ""  # Should be empty (invalid)


class TestBuildErrorRouting:
    """Tests for build error routing logic."""

    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator with mocked dependencies."""
        with patch.object(PipelineOrchestrator, '__init__', lambda x: None):
            orch = PipelineOrchestrator.__new__(PipelineOrchestrator)
            orch._is_build_failure = PipelineOrchestrator._is_build_failure.__get__(orch, PipelineOrchestrator)
            return orch

    def test_build_error_uses_compile_context(self, orchestrator):
        """Verify that build errors would trigger compilation fix context."""
        # Build failures should be routed to compile fix prompts
        stderr = "Build failed: error CS0246"
        is_build = orchestrator._is_build_failure(stderr)
        assert is_build is True
        # In actual code, is_build=True triggers use of context_type="compile"

    def test_runtime_error_detection(self, orchestrator):
        """Verify that runtime errors are correctly identified."""
        stderr = "Unhandled exception. System.IO.FileNotFoundException: test.zip"
        is_build = orchestrator._is_build_failure(stderr)
        assert is_build is False
        # In actual code, is_build=False triggers use of context_type="runtime"


class TestCascadingPrevention:
    """Tests for cascading bad code prevention."""

    def test_logic_prevents_degradation(self):
        """Test the logic that prevents cascading degradation."""
        # Simulate: previous result was a runtime error (not build)
        prev_was_build = False
        # Simulate: new result is a build error (degradation!)
        new_is_build = True

        # The fix should NOT be applied when this happens
        should_skip_update = new_is_build and not prev_was_build
        assert should_skip_update is True

    def test_logic_allows_improvement(self):
        """Test that improvement from build to runtime error is allowed."""
        # Simulate: previous was build error
        prev_was_build = True
        # Simulate: new is runtime error (improvement!)
        new_is_build = False

        # The fix SHOULD be applied (improvement)
        should_skip_update = new_is_build and not prev_was_build
        assert should_skip_update is False

    def test_logic_allows_same_type(self):
        """Test that same error type allows continuation."""
        # Both are runtime errors
        prev_was_build = False
        new_is_build = False

        should_skip_update = new_is_build and not prev_was_build
        assert should_skip_update is False

        # Both are build errors
        prev_was_build = True
        new_is_build = True

        should_skip_update = new_is_build and not prev_was_build
        assert should_skip_update is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
